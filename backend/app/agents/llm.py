"""
LLM client with two interchangeable backends:

  hf      Hugging Face Inference Providers (cloud, OpenAI-compatible router). Needs HF_TOKEN.
  ollama  Local/EC2 Ollama server.

Configure with environment variables or a `backend/.env` file:

  EVACTIVE_LLM_BACKEND=hf            # or ollama (default: hf if HF_TOKEN is set, else ollama)
  HF_TOKEN=hf_xxx                    # fine-grained token with "Make calls to Inference Providers"
  HF_MODEL=Qwen/Qwen2.5-72B-Instruct # optional; comma-separated list, tried in order
  OLLAMA_URL=http://localhost:11434
  OLLAMA_MODEL=qwen2.5:3b
  EVACTIVE_LLM=1                     # start with AI text ON (default is off, to save credits);
                                     # the dashboard's AI switch (POST /api/llm) turns it on/off
"""
from __future__ import annotations

import os
import re
import time
from pathlib import Path

import httpx


def _load_dotenv():
    """Minimal .env loader (KEY=VALUE lines) so nobody has to `set` variables every session."""
    path = Path(__file__).resolve().parents[2] / ".env"
    if not path.exists():
        return
    raw = path.read_bytes()
    text = None
    # Windows Notepad may save as UTF-8 with BOM or as UTF-16 ("Unicode"); accept all of them
    for enc in ("utf-8-sig", "utf-16"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        print("[evactive] could not read backend/.env - save it as UTF-8 in Notepad")
        return
    for line in text.splitlines():
        line = line.strip().lstrip("﻿")
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN", "")
BACKEND = os.getenv("EVACTIVE_LLM_BACKEND", "hf" if HF_TOKEN else "ollama").lower()
HF_BASE_URL = os.getenv("HF_BASE_URL", "https://router.huggingface.co/v1")
# Models tried in order until one is served by an enabled provider. Anything in HF_MODEL
# (comma-separated) is tried first; these defaults are the fallback (checked live Sept 2026).
HF_DEFAULT_MODELS = ["Qwen/Qwen2.5-72B-Instruct", "meta-llama/Llama-3.3-70B-Instruct", "google/gemma-3-27b-it"]
HF_MODELS = list(dict.fromkeys([m.strip() for m in os.getenv("HF_MODEL", "").split(",") if m.strip()] + HF_DEFAULT_MODELS))
HF_MODEL = HF_MODELS[0]
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
LLM_ENABLED = os.getenv("EVACTIVE_LLM", "0").strip().lower() in ("1", "true", "yes", "on")


class LLMClient:
    def __init__(self, backend: str = BACKEND, enabled: bool = LLM_ENABLED):
        self.backend = backend
        self.enabled = enabled
        if backend == "hf":
            self.url, self.model = HF_BASE_URL.rstrip("/"), HF_MODEL
        else:
            self.url, self.model = OLLAMA_URL.rstrip("/"), OLLAMA_MODEL
        self.online = False
        self.last_error: str | None = None
        self.last_latency_ms: int | None = None
        self.calls = 0
        self.tokens = 0
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=5.0))

    def set_enabled(self, on: bool):
        """Operator switch: when off, no LLM calls are made and agents use templates."""
        self.enabled = bool(on)
        if not self.enabled:
            self.online = False

    # ------------------------------------------------------------------ health
    async def check(self) -> bool:
        if not self.enabled:
            self.online = False
            return False
        if self.backend == "hf":
            return await self._check_hf()
        return await self._check_ollama()

    async def _check_ollama(self) -> bool:
        try:
            r = await self._client.get(f"{self.url}/api/tags")
            r.raise_for_status()
            names = [m.get("name", "") for m in r.json().get("models", [])]
            base = self.model.split(":")[0]
            self.online = any(n == self.model or n.split(":")[0] == base for n in names)
            self.last_error = None if self.online else f"model '{self.model}' not pulled (ollama pull {self.model})"
        except Exception as e:  # noqa: BLE001
            self.online = False
            self.last_error = f"Ollama unreachable at {self.url}: {type(e).__name__}"
        return self.online

    async def _check_hf(self) -> bool:
        # A real (1-token) call only when we don't already know the endpoint works,
        # so the health loop doesn't burn credits.
        if self.online:
            return True
        if not HF_TOKEN:
            self.last_error = "HF_TOKEN not set (add it to backend/.env)"
            return False
        errors = []
        for model in HF_MODELS:
            self.model = model
            try:
                await self.chat("You are a health check.", "Reply OK.", max_tokens=1)
                self.online, self.last_error = True, None
                return True
            except httpx.HTTPStatusError as e:
                errors.append(f"{model.split('/')[-1]}: {self._describe(e)}")
                if e.response.status_code in (401, 402, 403):
                    break  # token/billing problem - another model won't help
            except Exception as e:  # noqa: BLE001
                errors.append(self._describe(e))
                break
        self.model = HF_MODELS[0]
        self.online = False
        self.last_error = " | ".join(errors)[:300]
        return False

    @staticmethod
    def _describe(e: Exception) -> str:
        if isinstance(e, httpx.HTTPStatusError):
            code = e.response.status_code
            hint = {401: "invalid HF token", 403: "token lacks 'Make calls to Inference Providers' permission",
                    402: "Hugging Face credits used up", 404: "model not available on Inference Providers",
                    429: "rate limited"}.get(code, "")
            try:
                detail = e.response.json().get("error", "")
                detail = detail.get("message", "") if isinstance(detail, dict) else str(detail)
            except Exception:  # noqa: BLE001
                detail = ""
            return f"HTTP {code} {hint} {detail}".strip()[:160]
        return f"{type(e).__name__}: {e}"[:200]

    # ------------------------------------------------------------------ chat
    async def chat(self, system: str, user: str, max_tokens: int = 220, temperature: float = 0.3) -> str:
        t0 = time.perf_counter()
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        try:
            if self.backend == "hf":
                r = await self._client.post(
                    f"{self.url}/chat/completions",
                    headers={"Authorization": f"Bearer {HF_TOKEN}"},
                    json={"model": self.model, "messages": messages, "max_tokens": max_tokens,
                          "temperature": temperature, "stream": False},
                )
                r.raise_for_status()
                data = r.json()
                text = data["choices"][0]["message"]["content"] or ""
                self.tokens += int(data.get("usage", {}).get("total_tokens", 0) or 0)
            else:
                r = await self._client.post(f"{self.url}/api/chat", json={
                    "model": self.model, "stream": False, "messages": messages,
                    "options": {"temperature": temperature, "num_predict": max_tokens}, "keep_alive": "30m",
                })
                r.raise_for_status()
                text = r.json()["message"]["content"]
        except Exception as e:
            if self.backend == "hf":
                self.online = False  # health loop will re-check
            self.last_error = self._describe(e)
            raise
        self.calls += 1
        self.last_latency_ms = int((time.perf_counter() - t0) * 1000)
        # some models emit hidden reasoning in <think> tags - never show that to operators
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
        return text.strip()

    def status(self) -> dict:
        short = self.model.split("/")[-1]
        return {"enabled": self.enabled, "online": self.online, "backend": self.backend,
                "model": f"{'HF · ' if self.backend == 'hf' else ''}{short}", "url": self.url,
                "error": self.last_error, "latency_ms": self.last_latency_ms,
                "calls": self.calls, "tokens": self.tokens}

    async def aclose(self):
        await self._client.aclose()

"""
Hugging Face diagnostic for Evactive.  Run from the backend folder:

    python hf_check.py

Prints what your token is allowed to do and which model/provider combinations answer.
Your token itself is never printed.
"""
import httpx

from app.agents.llm import HF_TOKEN

H = {"Authorization": f"Bearer {HF_TOKEN}"}
print(f"Token loaded from .env: {'yes' if HF_TOKEN else 'NO'} (length {len(HF_TOKEN)})\n")

# 1. who am I / what can this token do
try:
    r = httpx.get("https://huggingface.co/api/whoami-v2", headers=H, timeout=20)
    print("whoami:", r.status_code)
    if r.status_code == 200:
        j = r.json()
        tok = j.get("auth", {}).get("accessToken", {})
        fg = tok.get("fineGrained", {}) or {}
        perms = set(fg.get("global", []) or [])
        for s in fg.get("scoped", []) or []:
            perms |= set(s.get("permissions", []))
        print("  user:", j.get("name"), "| pro:", j.get("isPro"), "| canPay (card on file):", j.get("canPay"))
        print("  token type:", tok.get("role"))
        print("  inference permission:", any("inference" in p for p in perms) or tok.get("role") in ("write", "read"))
        print("  permissions:", sorted(perms) if perms else "(classic token)")
    else:
        print("  ", r.text[:200])
except Exception as e:  # noqa: BLE001
    print("whoami failed:", type(e).__name__, e)

# 2. try a few model/provider combinations
TRIES = [
    "Qwen/Qwen2.5-72B-Instruct",
    "Qwen/Qwen2.5-72B-Instruct:novita",
    "Qwen/Qwen2.5-72B-Instruct:deepinfra",
    "meta-llama/Llama-3.3-70B-Instruct:novita",
    "openai/gpt-oss-20b:groq",
    "meta-llama/Llama-3.1-8B-Instruct:novita",
]
print()
for m in TRIES:
    try:
        r = httpx.post("https://router.huggingface.co/v1/chat/completions", headers=H, timeout=60, json={
            "model": m, "max_tokens": 5, "messages": [{"role": "user", "content": "Say OK"}]})
        if r.status_code == 200:
            print(f"OK   {m}  ->  {r.json()['choices'][0]['message']['content']!r}")
        else:
            try:
                err = r.json().get("error")
                err = err.get("message") if isinstance(err, dict) else err
            except Exception:  # noqa: BLE001
                err = r.text
            print(f"{r.status_code}  {m}  ->  {str(err)[:160]}")
    except Exception as e:  # noqa: BLE001
        print(f"ERR  {m}  ->  {type(e).__name__}: {e}")

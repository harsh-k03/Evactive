"""
Evactive API server.

  REST  /api/...   commands (reset, play/pause, hazards, wind, evacuation orders, ask)
  WS    /ws        live frames pushed to every connected dashboard
  /                serves the built dashboard (frontend/dist) when present

Run:  uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .agents.base import system_base
from .agents.llm import LLMClient
from .engine import Engine
from .layouts import LAYOUTS

MAX_FPS = 10


class Hub:
    def __init__(self):
        self.clients: set[WebSocket] = set()

    async def send_all(self, msg: dict):
        if not self.clients:
            return
        data = json.dumps(msg, separators=(",", ":"))
        dead = []
        for ws in list(self.clients):
            try:
                await ws.send_text(data)
            except Exception:  # noqa: BLE001
                dead.append(ws)
        for ws in dead:
            self.clients.discard(ws)


llm = LLMClient()
engine = Engine(llm)
hub = Hub()
lock = asyncio.Lock()


async def push_frame():
    await hub.send_all(engine.frame())


async def push_init():
    await hub.send_all(engine.init_payload())


async def sim_loop():
    loop = asyncio.get_running_loop()
    last_push = 0.0
    while True:
        if engine.running:
            t0 = loop.time()
            async with lock:
                engine.tick()
            now = loop.time()
            if now - last_push >= 1 / MAX_FPS:
                last_push = now
                await push_frame()
            await asyncio.sleep(max(0.001, 1.0 / engine.speed - (loop.time() - t0)))
        else:
            await asyncio.sleep(0.1)


async def llm_watch():
    was = None
    while True:
        await llm.check()
        if llm.online != was:
            was = llm.online
            engine.log("System", f"LLM {'online: ' + llm.model if llm.online else 'offline - agents use rule-based templates'}"
                       + ("" if llm.online or not llm.last_error else f" ({llm.last_error})"),
                       "info" if llm.online else "warn")
            await push_frame()
        await asyncio.sleep(20)


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine.loop = asyncio.get_running_loop()
    tasks = [asyncio.create_task(sim_loop()), asyncio.create_task(llm_watch())]
    yield
    for t in tasks:
        t.cancel()
    await llm.aclose()


app = FastAPI(title="Evactive", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ----------------------------------------------------------------- models
class ResetReq(BaseModel):
    layout_id: str = "float-glass"
    scenario_id: str | None = None
    seed: int | None = None
    autostart: bool = False


class SpeedReq(BaseModel):
    speed: float = Field(2.0, ge=0.25, le=16)


class HazardReq(BaseModel):
    type: str  # fire | leak
    x: int
    y: int
    rate: float = 350
    gas: str = "Natural gas (CH4)"


class WindReq(BaseModel):
    from_deg: float
    speed_mps: float = Field(..., ge=0, le=15)


class EvacReq(BaseModel):
    scope: str  # "site" or a zone id


class IsolateReq(BaseModel):
    leak_ids: list[str] | None = None


class AskReq(BaseModel):
    question: str = Field(..., max_length=500)


# ----------------------------------------------------------------- routes
@app.get("/api/health")
async def health():
    return {"ok": True, "t": engine.t, "running": engine.running, "llm": llm.status()}


@app.get("/api/layouts")
async def layouts():
    return [{"id": k, "name": v["name"], "scenarios": [{"id": s["id"], "name": s["name"]} for s in v["scenarios"]]}
            for k, v in LAYOUTS.items()]


@app.get("/api/state")
async def state():
    return engine.frame(include_log=False)


@app.post("/api/sim/reset")
async def reset(req: ResetReq):
    if req.layout_id not in LAYOUTS:
        raise HTTPException(404, "unknown layout")
    async with lock:
        engine.load(req.layout_id, req.scenario_id, req.seed)
        engine.running = req.autostart
    await push_init()
    return {"ok": True, "seed": engine.seed}


@app.post("/api/sim/play")
async def play():
    engine.running = True
    await push_frame()
    return {"ok": True}


@app.post("/api/sim/pause")
async def pause():
    engine.running = False
    await push_frame()
    return {"ok": True}


@app.post("/api/sim/step")
async def step():
    async with lock:
        engine.tick()
    await push_frame()
    return {"ok": True, "t": engine.t}


@app.post("/api/sim/speed")
async def speed(req: SpeedReq):
    engine.speed = req.speed
    await push_frame()
    return {"ok": True}


@app.post("/api/hazard")
async def hazard(req: HazardReq):
    g = engine.grid
    if not g.in_bounds(req.x, req.y):
        raise HTTPException(400, "out of bounds")
    async with lock:
        if req.type == "fire":
            ok = engine.add_fire(req.x, req.y)
        elif req.type == "leak":
            ok = engine.add_leak(req.x, req.y, req.rate, req.gas)
        else:
            raise HTTPException(400, "type must be fire or leak")
    if not ok:
        raise HTTPException(400, "cannot place hazard there (wall or already burning)")
    await push_frame()
    return {"ok": True}


@app.post("/api/wind")
async def wind(req: WindReq):
    engine.hz.set_wind(req.from_deg, req.speed_mps)
    engine.log("Simulator", f"[operator] Wind set: from {req.from_deg:.0f} deg at {req.speed_mps:.1f} m/s", kind="sim")
    await push_frame()
    return {"ok": True}


@app.post("/api/evacuate")
async def evacuate(req: EvacReq):
    async with lock:
        ok = engine.order_evacuation(req.scope, by="operator")
        if ok:
            what = "FULL SITE" if req.scope == "site" else engine.grid.zone_names.get(req.scope, req.scope)
            engine.log("Commander", f"MANUAL ORDER (control room operator): evacuate {what}.", "critical", kind="decision")
    await push_frame()
    return {"ok": ok}


@app.post("/api/isolate")
async def isolate(req: IsolateReq):
    async with lock:
        done = engine.isolate_leaks(req.leak_ids)
        if done:
            engine.log("Commander", f"MANUAL ESD (control room operator): isolated leak(s) {', '.join(done)}.",
                       "critical", kind="decision")
    await push_frame()
    return {"ok": True, "isolated": done}


@app.post("/api/ask")
async def ask(req: AskReq):
    facts = engine.agents["pre"][1].facts()
    if not llm.online:
        return {"answer": "The language model is offline, so here is the live fact sheet instead:\n"
                          + json.dumps(facts, indent=1), "llm": False}
    sys = system_base(engine) + (" You are the Evactive assistant answering the control-room operator. Answer in at most "
                         "4 sentences using only the live facts. If the facts don't cover the question, say so.")
    try:
        text = await llm.chat(sys, f"LIVE FACTS:\n{json.dumps(facts, indent=1)}\n\nQUESTION: {req.question}", 250)
    except Exception as e:  # noqa: BLE001
        return {"answer": f"LLM error: {type(e).__name__}", "llm": False}
    engine.log("Assistant", f"Q: {req.question} | A: {text}", "info", llm=True, kind="qa")
    return {"answer": text, "llm": True}


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    hub.clients.add(ws)
    try:
        await ws.send_text(json.dumps(engine.init_payload(), separators=(",", ":")))
        while True:
            await ws.receive_text()  # keepalive / ignore
    except WebSocketDisconnect:
        pass
    finally:
        hub.clients.discard(ws)


# ----------------------------------------------------------------- static dashboard
DIST = Path(os.getenv("EVACTIVE_DIST", Path(__file__).resolve().parents[2] / "frontend" / "dist"))
if DIST.exists():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="dashboard")

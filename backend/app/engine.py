"""
Simulation engine: owns the plant state, runs the tick loop, hosts the agents,
and produces frames for the dashboard.
"""
from __future__ import annotations

import asyncio
from typing import Awaitable, Callable

import numpy as np

from .agents import build_agents
from .agents.llm import LLMClient
from .layouts import LAYOUTS
from .sim.grid import build_grid, static_payload
from .sim.hazards import BURNING, BURNT, HazardField, Leak
from .sim.routing import INF, cell_costs, cost_field, next_step, simplify, trace_path
from .sim.sensors import SensorNetwork
from .sim.workers import ALERTED, EVACUATING, INJURED, SAFE, TRAPPED, WORKING, spawn_workers

STAGES = {0: "NORMAL", 1: "ALERT", 2: "ZONE EVACUATION", 3: "SITE EVACUATION"}
MAX_PER_CELL = 3


class Engine:
    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient(enabled=False)
        self.loop: asyncio.AbstractEventLoop | None = None
        self.speed = 2.0
        self.running = False
        self.run_id = 0
        self.load("float-glass")

    # ================================================================ setup
    def load(self, layout_id: str, scenario_id: str | None = None, seed: int | None = None):
        self.run_id += 1
        self.layout_id = layout_id
        self.layout = LAYOUTS[layout_id]
        self.seed = seed if seed is not None else int(np.random.SeedSequence().entropy % 100000)
        self.rng = np.random.default_rng(self.seed)
        self.grid = build_grid(self.layout)
        self.hz = HazardField(self.grid, self.rng)
        dw = self.layout.get("default_wind")
        if dw:
            self.hz.set_wind(dw["from_deg"], dw["speed_mps"])
        self.sensors = SensorNetwork(self.grid, self.rng)
        self.workers = spawn_workers(self.grid, self.rng)
        self.t = 0
        self.running = False
        self.log_entries: list[dict] = []
        self.log_seq = 0
        self.sent_seq = 0
        self.incident = {
            "stage": 0,
            "evac_zones": set(),
            "site_evac": False,
            "alarms": {},            # sensor_id -> dict
            "zone_hazards": {},      # zone_id -> {fire, gas, smoke, ...}
            "unsafe_aps": set(),
            "blocked_exits": set(),
            "sitrep": None,
            "pa": None,
            "sms": [],
            "all_clear_t": None,
            "started_t": None,
        }
        self.safe_aps = [ap["id"] for ap in self.layout["assembly_points"]]
        self.cost = None
        self.dist = None
        self.ap_dist = {}
        self.events = []
        self.scenario = None
        self.leak_n = 0
        self.crowd = np.zeros((self.grid.h, self.grid.w))
        self.hotspots: list[dict] = []
        self.peak_queue = {"n": 0, "label": None, "t": None}
        self.place_names = self._place_names()
        self.capacity = self._capacity()
        if scenario_id:
            self.set_scenario(scenario_id)
        self.agents = build_agents(self)
        self.replan()
        self.log("System", f"Loaded {self.layout['name']} - {len(self.workers)} personnel on shift, "
                           f"{len(self.sensors.sensors)} detectors online.", "info")
        if self.scenario:
            self.log("System", f"Scenario armed: {self.scenario['name']}", "info")

    def set_scenario(self, scenario_id: str):
        sc = next(s for s in self.layout["scenarios"] if s["id"] == scenario_id)
        self.scenario = sc
        self.events = sorted(sc["events"], key=lambda e: e["t"])
        w = sc.get("wind")
        if w:
            self.hz.set_wind(w["from_deg"], w["speed_mps"])

    # ================================================================ logging
    def log(self, agent: str, msg: str, level: str = "info", llm: bool = False, kind: str = "log", **extra):
        self.log_seq += 1
        e = {"seq": self.log_seq, "t": self.t, "agent": agent, "level": level, "msg": msg, "llm": llm, "kind": kind}
        e.update(extra)
        self.log_entries.append(e)
        if len(self.log_entries) > 1500:
            self.log_entries = self.log_entries[-1000:]
        return e

    def spawn_llm(self, coro_factory: Callable[[], Awaitable[str]], on_text: Callable[[str, bool], None],
                  fallback: Callable[[], str]):
        """Run an LLM call without blocking the tick loop. Falls back to a template when offline."""
        if not (self.llm.online and self.loop):
            on_text(fallback(), False)
            return
        run_id = self.run_id

        async def _run():
            try:
                text = await coro_factory()
                ok = bool(text)
            except Exception as e:  # noqa: BLE001
                self.llm.last_error = f"{type(e).__name__}: {e}"[:200]
                text, ok = "", False
            if run_id != self.run_id:
                return  # simulation was reset while we were waiting
            on_text(text if ok else fallback(), ok)

        self.loop.create_task(_run())

    # ================================================================ commands
    def add_fire(self, x: int, y: int, source: str = "operator") -> bool:
        ok = self.hz.ignite(x, y)
        if ok:
            z = self.grid.zone_names.get(self.grid.zone_at(x, y), "open yard")
            self.log("Simulator", f"[{source}] Fire started at ({x},{y}) - {z}", "info", kind="sim")
        return ok

    def add_leak(self, x: int, y: int, rate: float = 350, gas: str = "Natural gas (CH4)", source: str = "operator") -> bool:
        if not self.grid.open_air[y, x]:
            return False
        self.leak_n += 1
        lk = Leak(f"L{self.leak_n}", x, y, rate, gas, self.grid.zone_at(x, y), self.t)
        self.hz.add_leak(lk)
        z = self.grid.zone_names.get(lk.zone, "open yard")
        self.log("Simulator", f"[{source}] {gas} leak ({lk.id}) started at ({x},{y}) - {z}", "info", kind="sim")
        return True

    def isolate_leaks(self, leak_ids: list[str] | None = None, by: str = "operator") -> list[str]:
        done = []
        for lk in self.hz.leaks:
            if not lk.isolated and (leak_ids is None or lk.id in leak_ids):
                lk.isolated_t = self.t
                done.append(lk.id)
        return done

    def order_evacuation(self, scope: str, by: str = "operator", reason: str = ""):
        inc = self.incident
        if scope == "site":
            if not inc["site_evac"]:
                inc["site_evac"] = True
                inc["evac_zones"] |= set(self.grid.zone_ids)
                inc["stage"] = 3
                inc["started_t"] = inc["started_t"] if inc["started_t"] is not None else self.t
                return True
        elif scope in self.grid.zone_ids and scope not in inc["evac_zones"]:
            inc["evac_zones"].add(scope)
            inc["stage"] = max(inc["stage"], 2)
            inc["started_t"] = inc["started_t"] if inc["started_t"] is not None else self.t
            return True
        return False

    # ================================================================ routing
    def replan(self) -> list[tuple]:
        """Recompute the cost-to-safety field. Returns [(worker, old_ap, old_exit)] for changed routes."""
        occ = np.zeros((self.grid.h, self.grid.w))
        for w in self.workers:
            if w.status in (EVACUATING, ALERTED):
                occ[w.y, w.x] += 1
        self.crowd = 0.6 * self.crowd + 0.4 * occ   # smoothed, so routes don't flip every second
        self.cost = cell_costs(self.grid, self.hz, self.crowd)
        self.safe_aps = [ap["id"] for ap in self.layout["assembly_points"] if ap["id"] not in self.incident["unsafe_aps"]]
        if not self.safe_aps:  # everything unsafe: use the least bad rather than none
            self.safe_aps = [ap["id"] for ap in self.layout["assembly_points"]]
        # one cost-to-safety field per open assembly point, so each evacuee can stay committed to theirs
        self.ap_dist = {ap: cost_field(self.grid, self.cost, [ap])[0] for ap in self.safe_aps}
        self.dist = np.minimum.reduce(list(self.ap_dist.values()))
        changed = []
        blocked = self.incident["blocked_exits"]
        for w in self.workers:
            if w.status not in (EVACUATING, ALERTED, TRAPPED):
                w.path = []
                continue
            old_ap, old_exit = w.ap, w.exit
            cands = {ap: float(d[w.y, w.x]) for ap, d in self.ap_dist.items() if np.isfinite(d[w.y, w.x])}
            if not cands:
                w.path, w.ap, w.exit = [], None, None
                continue
            best = min(cands, key=cands.get)
            # hysteresis: keep the current assembly point unless another is clearly better
            if not (w.ap in cands and cands[w.ap] <= 1.15 * cands[best] + 2):
                w.ap = best
            field = self.ap_dist[w.ap]
            path = trace_path(self.grid, field, self.cost, w.x, w.y)
            w.exit = next((self.grid.exit_of_cell[p] for p in path if p in self.grid.exit_of_cell), None)
            w.path = simplify(path)
            if old_ap is not None and (old_ap != w.ap or (old_exit in blocked and w.exit != old_exit)):
                w.reroutes += 1
                changed.append((w, old_ap, old_exit))
        return changed

    def field_for(self, w):
        return self.ap_dist.get(w.ap, self.dist) if w.ap else self.dist

    # ================================================================ tick
    def tick(self):
        self.t += 1
        t = self.t
        while self.events and self.events[0]["t"] <= t:
            ev = self.events.pop(0)
            x, y = ev["pos"]
            if ev["type"] == "fire":
                self.add_fire(x, y, source="scenario")
            elif ev["type"] == "leak":
                self.add_leak(x, y, ev.get("rate", 350), ev.get("gas", "Natural gas (CH4)"), source="scenario")

        self.hz.step(t)
        self.sensors.update(self.hz)
        for ag in self.agents["pre"]:
            ag.step(t)
        self._move_workers(t)
        self._detect_queues(t)
        for ag in self.agents["post"]:
            ag.step(t)

    def _move_workers(self, t: int):
        inc = self.incident
        g, hz = self.grid, self.hz
        n_aps = len(self.layout["assembly_points"])
        fire_d = hz.fire_distance(8) if any(w.status == TRAPPED for w in self.workers) else None
        occ: dict[tuple, int] = {}
        for w in self.workers:
            if w.status != SAFE:
                occ[(w.x, w.y)] = occ.get((w.x, w.y), 0) + 1

        for w in self.workers:
            if w.status == INJURED:
                continue
            if hz.fire[w.y, w.x] in (BURNING, BURNT):
                w.burn_ticks += 1
                if w.burn_ticks >= 6:  # a few seconds to get clear of the flames
                    w.status = INJURED
                    self.log("Accountability", f"{w.id} {w.name} ({w.role}) caught by fire in "
                             f"{g.zone_names.get(w.zone, w.zone)} - casualty, rescue required", "critical")
                    continue
                if w.status in (WORKING, ALERTED):  # flames right here: move now
                    w.status, w.evac_start, w.self_evacuated = EVACUATING, t, True
            else:
                w.burn_ticks = 0

            if w.status == WORKING:
                if w.zone in inc["evac_zones"]:
                    w.status = ALERTED
                    w.alert_at = t + int(self.rng.integers(4, 22))   # pre-movement time
                elif hz.smoke[w.y, w.x] > 0.25:
                    # people react to visible smoke; flammable gases like H2/CH4 can't be seen or smelled
                    w.status = ALERTED
                    w.self_evacuated = True
                    w.alert_at = t + int(self.rng.integers(1, 5))
                    self.log("Accountability", f"{w.id} {w.name} self-evacuating from "
                             f"{g.zone_names.get(w.zone, w.zone)} (saw smoke before any order)", "warn")

            if w.status == ALERTED and t >= (w.alert_at or t):
                w.status = EVACUATING
                w.evac_start = t

            # an assembly point turned unsafe: move on - unless every assembly point is unsafe,
            # in which case people stay put instead of shuttling between them
            if w.status == SAFE and w.ap in inc["unsafe_aps"] and len(inc["unsafe_aps"]) < n_aps:
                w.status = EVACUATING
                w.safe_at = None

            if w.status == TRAPPED and next_step(g, self.field_for(w), self.cost, w.x, w.y) is not None:
                w.status = EVACUATING
                self.log("Accountability", f"{w.id} {w.name} has a way out again - evacuating.", "info")
            if w.status == TRAPPED:
                self._take_refuge(w, occ, fire_d)
                continue

            if w.status != EVACUATING:
                continue

            if not np.isfinite(self.dist[w.y, w.x]) and next_step(g, self.field_for(w), self.cost, w.x, w.y) is None:
                w.status = TRAPPED
                self.log("Accountability", f"{w.id} {w.name} TRAPPED in {g.zone_names.get(w.zone, w.zone)} "
                         f"at ({w.x},{w.y}) - no safe path. Rescue team to be dispatched.", "critical")
                continue

            start_xy = (w.x, w.y)
            slow = 1 - 0.5 * min(1.0, float(hz.smoke[w.y, w.x]))
            # walking speed drops as the crowd gets denser (Fruin-style level-of-service)
            slow *= {1: 1.0, 2: 0.8}.get(occ.get((w.x, w.y), 1), 0.6)
            w.progress += w.speed * slow
            while w.progress >= 1.0:
                nxt = next_step(g, self.field_for(w), self.cost, w.x, w.y)
                if nxt is None:
                    break
                cap = int(self.capacity[nxt[1], nxt[0]]) + (1 if w.waiting >= 6 else 0)  # squeeze past after a while
                if occ.get(nxt, 0) >= cap:
                    w.progress = min(w.progress, 1.0)
                    w.waiting += 1
                    w.blocked_at = nxt
                    break
                w.waiting = 0
                step = 1.414 if (nxt[0] != w.x and nxt[1] != w.y) else 1.0
                occ[(w.x, w.y)] = occ.get((w.x, w.y), 1) - 1
                w.x, w.y = nxt
                occ[nxt] = occ.get(nxt, 0) + 1
                w.progress -= step
                if w.path and len(w.path) > 1 and [w.x, w.y] == w.path[1]:
                    w.path.pop(0)
                reached = next((ap for ap in self.safe_aps if g.ap_mask[ap][w.y, w.x]), None)
                if reached:
                    w.status = SAFE
                    w.ap = reached
                    w.safe_at = t
                    w.path = []
                    w.progress = 0
                    occ[(w.x, w.y)] = occ.get((w.x, w.y), 1) - 1
                    w.x, w.y = self._muster_spot(reached)  # walk into the muster area, clear the entry
                    break
            w.still = w.still + 1 if (w.status == EVACUATING and (w.x, w.y) == start_xy) else 0

    # ================================================================ queues / bottlenecks
    def _place_names(self) -> dict:
        """Human-readable names for door and exit cells, used to describe where queues form."""
        g = self.grid
        names = {}
        for eid, cells in g.exit_cells.items():
            for c in cells:
                names[c] = f"exit {eid}"
        ys, xs = np.nonzero(g.cell == 3)  # DOOR
        for x, y in zip(xs.tolist(), ys.tolist()):
            zs = []
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if g.in_bounds(nx, ny) and g.cell[ny, nx] == 1:
                    z = g.zone_at(nx, ny)
                    if z and g.zone_names[z] not in zs:
                        zs.append(g.zone_names[z])
            names[(x, y)] = "door " + " / ".join(zs) if zs else "doorway"
        return names

    def _capacity(self) -> np.ndarray:
        """People per 2 m cell. A 1-cell-wide doorway is treated as a ~1 m single-leaf door (one at a time);
        wider openings let two through per cell; open floor holds three."""
        g = self.grid
        cap = np.full((g.h, g.w), MAX_PER_CELL, dtype=np.int8)
        opening = (g.cell == 3) | (g.cell == 5)
        ys, xs = np.nonzero(opening)
        for x, y in zip(xs.tolist(), ys.tolist()):
            wide = any(g.in_bounds(x + dx, y + dy) and opening[y + dy, x + dx]
                       for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            cap[y, x] = 2 if wide else 1
        return cap

    def _describe_place(self, x: int, y: int) -> str | None:
        for r in range(0, 3):
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    n = self.place_names.get((x + dx, y + dy))
                    if n:
                        return n
        z = self.grid.zone_at(x, y)
        if z and self.grid.indoor[y, x]:
            return f"inside {self.grid.zone_names[z]}"
        return None  # crowding out in the open yard is not a bottleneck

    def _detect_queues(self, t: int):
        # people who have not been able to advance for 2+ seconds while evacuating = a queue
        waiting = [w for w in self.workers if w.status == EVACUATING and w.still >= 2]
        clusters = []
        for w in waiting:
            bx, by = w.blocked_at or (w.x, w.y)
            for c in clusters:
                if abs(c["x"] - bx) <= 3 and abs(c["y"] - by) <= 3:
                    c["n"] += 1
                    break
            else:
                clusters.append({"x": bx, "y": by, "n": 1})
        self.hotspots = []
        for c in clusters:
            if c["n"] >= 3:
                c["label"] = self._describe_place(c["x"], c["y"])
                if not c["label"]:
                    continue
                self.hotspots.append(c)
                if c["n"] > self.peak_queue["n"]:
                    self.peak_queue = {"n": c["n"], "label": c["label"], "t": t}

    def _take_refuge(self, w, occ: dict, fire_d):
        """No way out: move away from the fire and smoke and wait for the rescue team."""
        if fire_d is None:
            fire_d = self.hz.fire_distance(8)
        w.progress += w.speed * 0.7
        if w.progress < 1.0:
            return
        g, hz = self.grid, self.hz
        def score(x, y):
            return float(fire_d[y, x]) - 4.0 * float(hz.smoke[y, x])
        best, bxy = score(w.x, w.y), None
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = w.x + dx, w.y + dy
            if not g.in_bounds(nx, ny) or not g.walkable[ny, nx] or hz.fire[ny, nx] != 0:
                continue
            if occ.get((nx, ny), 0) >= int(self.capacity[ny, nx]):
                continue
            sc = score(nx, ny)
            if sc > best + 0.05:
                best, bxy = sc, (nx, ny)
        w.progress -= 1.0
        if bxy:
            occ[(w.x, w.y)] = occ.get((w.x, w.y), 1) - 1
            w.x, w.y = bxy
            occ[bxy] = occ.get(bxy, 0) + 1

    def _muster_spot(self, ap_id: str) -> tuple[int, int]:
        taken = {(o.x, o.y) for o in self.workers if o.status == SAFE}
        ys, xs = np.nonzero(self.grid.ap_mask[ap_id])
        cells = [(int(x), int(y)) for x, y in zip(xs, ys) if (int(x), int(y)) not in taken]
        if not cells:
            cells = [(int(x), int(y)) for x, y in zip(xs, ys)]
        return cells[int(self.rng.integers(len(cells)))]

    # ================================================================ outputs
    def headcount(self) -> dict:
        c = {"total": len(self.workers), "safe": 0, "evacuating": 0, "working": 0, "trapped": 0, "injured": 0,
             "by_ap": {ap["id"]: 0 for ap in self.layout["assembly_points"]},
             "in_scope": 0, "in_scope_safe": 0}
        for w in self.workers:
            if w.status == SAFE:
                c["safe"] += 1
                c["by_ap"][w.ap] = c["by_ap"].get(w.ap, 0) + 1
            elif w.status in (EVACUATING, ALERTED):
                c["evacuating"] += 1
            elif w.status == WORKING:
                c["working"] += 1
            elif w.status == TRAPPED:
                c["trapped"] += 1
            elif w.status == INJURED:
                c["injured"] += 1
            if w.zone in self.incident["evac_zones"] or w.self_evacuated or w.status != WORKING:
                c["in_scope"] += 1
                if w.status == SAFE:
                    c["in_scope_safe"] += 1
        return c

    def zone_status(self) -> list[dict]:
        inc = self.incident
        out = []
        for zid in self.grid.zone_ids:
            hzd = inc["zone_hazards"].get(zid)
            if hzd:
                st = "hazard"
            elif zid in inc["evac_zones"]:
                st = "evacuating"
            elif any(a["zone"] == zid for a in inc["alarms"].values()):
                st = "alert"
            else:
                st = "normal"
            people = sum(1 for w in self.workers if self.grid.zone_at(w.x, w.y) == zid)
            out.append({"id": zid, "status": st, "people": people, "hazards": hzd or {}})
        return out

    def init_payload(self) -> dict:
        return {
            "type": "init",
            "layout": static_payload(self.grid),
            "layouts": [{"id": k, "name": v["name"],
                         "scenarios": [{"id": sc["id"], "name": sc["name"]} for sc in v["scenarios"]]}
                        for k, v in LAYOUTS.items()],
            "scenarios": [{"id": s["id"], "name": s["name"], "description": s["description"]}
                          for s in self.layout["scenarios"]],
            "scenario": self.scenario["id"] if self.scenario else None,
            "log": self.log_entries[-300:],
            "frame": self.frame(include_log=False),
        }

    def frame(self, include_log: bool = True) -> dict:
        hz, inc = self.hz, self.incident
        smoke = (hz.smoke * 100).astype(np.int16).flatten()
        gas = np.clip(hz.gas, 0, 150).astype(np.int16).flatten()
        si = np.nonzero(smoke >= 3)[0]
        gi = np.nonzero(gas >= 2)[0]
        fr = {
            "type": "frame",
            "run": self.run_id,
            "layout": self.layout_id,
            "t": self.t,
            "running": self.running,
            "speed": self.speed,
            "wind": {"from_deg": hz.wind_from_deg, "speed_mps": hz.wind_mps},
            "stage": inc["stage"],
            "stage_label": STAGES[inc["stage"]],
            "evac_zones": sorted(inc["evac_zones"]),
            "fire": np.nonzero((hz.fire == BURNING).flatten())[0].tolist(),
            "burnt": np.nonzero((hz.fire == BURNT).flatten())[0].tolist(),
            "smoke": np.stack([si, smoke[si]], 1).tolist() if len(si) else [],
            "gas": np.stack([gi, gas[gi]], 1).tolist() if len(gi) else [],
            "leaks": [{"id": l.id, "x": l.x, "y": l.y, "gas": l.gas, "rate": round(l.current_rate(self.t), 1),
                       "isolated": l.isolated} for l in hz.leaks],
            "workers": [w.payload() for w in self.workers],
            "paths": {w.id: w.path for w in self.workers if w.path and w.status in (EVACUATING, ALERTED)},
            "sensors": self.sensors.payload(),
            "headcount": self.headcount(),
            "zones": self.zone_status(),
            "exits": [{"id": e, "blocked": e in inc["blocked_exits"]} for e in self.grid.exit_cells],
            "aps": [{"id": ap["id"], "safe": ap["id"] not in inc["unsafe_aps"]} for ap in self.layout["assembly_points"]],
            "sitrep": inc["sitrep"],
            "pa": inc["pa"],
            "all_clear_t": inc["all_clear_t"],
            "hotspots": self.hotspots,
            "peak_queue": self.peak_queue,
            "started_t": inc["started_t"],
            "llm": self.llm.status(),
        }
        if include_log:
            fr["log"] = [e for e in self.log_entries if e["seq"] > self.sent_seq]
            self.sent_seq = self.log_seq
        return fr

"""Routing Agent: keeps exits and assembly points under watch and re-plans every
evacuee's route as the hazard picture changes (deterministic Dijkstra, no LLM)."""
from __future__ import annotations

from collections import Counter

import numpy as np

from ..sim.hazards import BURNING, BURNT
from ..sim.workers import ALERTED, EVACUATING, SAFE, TRAPPED
from .base import Agent

AP_GAS_LEL = 10.0
AP_SMOKE = 0.2
AP_FIRE_DIST = 6
EXIT_GAS_LEL = 40.0
EXIT_SMOKE = 0.6


class RoutingAgent(Agent):
    name = "Routing"

    def __init__(self, engine):
        super().__init__(engine)
        self.pending_reroutes: list = []
        self.last_reroute_log = -999
        self.queue_logged: dict[str, int] = {}

    def _check_aps(self):
        e, g, hz = self.e, self.e.grid, self.e.hz
        lel = hz.gas_lel()
        fd = hz.fire_distance(AP_FIRE_DIST)
        changed = False
        for ap in e.layout["assembly_points"]:
            m = g.ap_mask[ap["id"]]
            gmax = float(lel[m].max())
            smax = float(hz.smoke[m].max())
            fmin = int(fd[m].min())
            reason = None
            if gmax >= AP_GAS_LEL:
                reason = f"flammable gas {gmax:.0f}% LEL at the assembly area"
            elif smax >= AP_SMOKE:
                reason = f"smoke {smax * 100:.0f}% drifting over it"
            elif fmin <= AP_FIRE_DIST:
                reason = "fire within ~12 m"
            was = ap["id"] in self.inc["unsafe_aps"]
            if reason and not was:
                self.inc["unsafe_aps"].add(ap["id"])
                n = sum(1 for w in e.workers if w.ap == ap["id"] and w.status in (SAFE, EVACUATING, ALERTED))
                self.log(f"{ap['name']} declared UNSAFE ({reason}). Redirecting {n} people to other assembly points.",
                         "critical", kind="decision")
                changed = True
            elif not reason and was and gmax < AP_GAS_LEL / 2 and smax < AP_SMOKE / 2:
                self.inc["unsafe_aps"].discard(ap["id"])
                self.log(f"{ap['name']} is safe again and back in the routing plan.", "info", kind="decision")
                changed = True
        return changed

    def _check_exits(self):
        e, g, hz = self.e, self.e.grid, self.e.hz
        lel = hz.gas_lel()
        fd = hz.fire_distance(1)
        for eid, cells in g.exit_cells.items():
            reason = None
            for x, y in cells:
                if hz.fire[y, x] in (BURNING, BURNT) or fd[y, x] <= 1:
                    reason = "fire at the exit" if hz.fire[y, x] != BURNT else "exit burnt out / impassable"
                elif lel[y, x] >= EXIT_GAS_LEL:
                    reason = f"gas {lel[y, x]:.0f}% LEL"
                elif hz.smoke[y, x] >= EXIT_SMOKE:
                    reason = f"dense smoke ({hz.smoke[y, x] * 100:.0f}%)"
                if reason:
                    break
            was = eid in self.inc["blocked_exits"]
            if reason and not was:
                self.inc["blocked_exits"].add(eid)
                self.log(f"Exit {eid} BLOCKED ({reason}). Routes through {eid} withdrawn.", "critical", kind="decision")
            elif not reason and was:
                self.inc["blocked_exits"].discard(eid)
                self.log(f"Exit {eid} clear again.", "info", kind="decision")

    def step(self, t: int):
        e = self.e
        active = any(w.status in (EVACUATING, ALERTED, TRAPPED) for w in e.workers)
        if self.inc["stage"] == 0 and not active:
            if t % 10 == 0:
                e.replan()
            return
        self._check_exits()
        ap_changed = self._check_aps()
        if active or ap_changed or t % 3 == 0:
            changed = e.replan()
            self.pending_reroutes.extend(changed)
        for h in e.hotspots:
            if h["n"] >= 5 and t - self.queue_logged.get(h["label"], -999) >= 25:
                self.queue_logged[h["label"]] = t
                self.log(f"Bottleneck at {h['label']}: {h['n']} people queuing. Crowd-aware routing is sending "
                         f"new arrivals to less congested exits.", "warn", kind="decision")
        if self.pending_reroutes and t - self.last_reroute_log >= 5:
            self.last_reroute_log = t
            moves = Counter()
            for w, old_ap, old_exit in self.pending_reroutes:
                if old_ap != w.ap:
                    moves[f"{old_ap}->{w.ap}"] += 1
                elif old_exit != w.exit:
                    moves[f"{old_exit}->{w.exit}"] += 1
            ids = {w.id for w, _, _ in self.pending_reroutes}
            self.pending_reroutes = []
            if moves:
                detail = ", ".join(f"{k} x{v}" for k, v in moves.most_common(4))
                self.log(f"Re-planned routes for {len(ids)} evacuees around hazards ({detail}).", "warn")

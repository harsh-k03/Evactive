"""Hazard Assessment Agent: fuses detector alarms with the hazard picture, zone by zone,
and writes situation reports (LLM, with a deterministic template fallback)."""
from __future__ import annotations

import json

import numpy as np

from ..sim.hazards import BURNING
from .base import Agent, system_base

EVERY = 3              # assess every N ticks
SITREP_PERIOD = 45     # sim-seconds between routine sitreps while incident active
SITREP_MIN_GAP = 12


class AssessmentAgent(Agent):
    name = "Assessment"

    def __init__(self, engine):
        super().__init__(engine)
        self.last_sitrep_t = -999
        self.last_sig = None
        self.pending = False
        self.last_stage = 0

    def _zone_stats(self):
        g, hz = self.e.grid, self.e.hz
        lel = hz.gas_lel()
        burning = hz.fire == BURNING
        area = g.layout["cell_m"] ** 2
        out = {}
        for i, zid in enumerate(g.zone_ids):
            m = g.zone == i
            fire = int(np.count_nonzero(burning & m))
            gmax = float(lel[m].max()) if m.any() else 0.0
            gcloud = int(np.count_nonzero((lel >= 20) & m))
            smax = float(hz.smoke[m].max()) if m.any() else 0.0
            h = {}
            if fire:
                h["fire_m2"] = round(fire * area)
            if gcloud >= 3:  # at least ~12 m2 above 20% LEL
                h["gas_max_lel"] = round(gmax)
                h["gas_cloud_m2"] = round(gcloud * area)
            if smax >= 0.25:
                h["smoke_max_pct"] = round(smax * 100)
            if h:
                out[zid] = h
        return out

    def facts(self) -> dict:
        e, inc = self.e, self.inc
        hc = e.headcount()
        return {
            "sim_time_s": e.t,
            "stage": {0: "NORMAL", 1: "ALERT", 2: "ZONE EVACUATION", 3: "SITE EVACUATION"}[inc["stage"]],
            "affected_zones": {self.zname(z): v for z, v in inc["zone_hazards"].items()},
            "active_alarms": [f"{a['sensor']} {a['state']} {self.zname(a['zone'])}" for a in inc["alarms"].values()],
            "active_leaks": [f"{l.gas} in {self.zname(l.zone)} ({'isolated by ESD' if l.isolated else 'ONGOING'})"
                             for l in e.hz.leaks],
            "evacuating_zones": [self.zname(z) for z in sorted(inc["evac_zones"])],
            "blocked_exits": sorted(inc["blocked_exits"]),
            "unsafe_assembly_points": sorted(inc["unsafe_aps"]),
            "open_assembly_points": [a["id"] for a in e.layout["assembly_points"] if a["id"] not in inc["unsafe_aps"]],
            "all_personnel_accounted": inc["all_clear_t"] is not None,
            "wind": f"from {int(e.hz.wind_from_deg)} deg at {e.hz.wind_mps:.1f} m/s",
            "headcount": {k: hc[k] for k in ("total", "safe", "evacuating", "working", "trapped", "injured")},
        }

    def _template(self, f: dict) -> str:
        hc = f["headcount"]
        if not f["affected_zones"] and not f["active_alarms"]:
            if f["stage"] == "NORMAL":
                return "No active hazards. All detectors normal."
            return (f"Hazards no longer detected; all detectors normal. {hc['safe']}/{hc['total']} at assembly points"
                    + (" - all personnel accounted for." if f["all_personnel_accounted"] else f", {hc['evacuating']} still moving.")
                    + " Keep people at assembly points until the Emergency Response Team declares the site safe.")
        parts = []
        for z, h in f["affected_zones"].items():
            bits = []
            if "fire_m2" in h:
                bits.append(f"fire ~{h['fire_m2']} m2")
            if "gas_max_lel" in h:
                bits.append(f"flammable gas up to {h['gas_max_lel']}% LEL over ~{h['gas_cloud_m2']} m2")
            if "smoke_max_pct" in h:
                bits.append(f"smoke {h['smoke_max_pct']}%")
            parts.append(f"{z}: {', '.join(bits)}")
        s = "; ".join(parts) if parts else "Alarms active: " + ", ".join(f["active_alarms"])
        s += (f". Stage: {f['stage']}. {hc['safe']}/{hc['total']} at assembly points, {hc['evacuating']} moving"
              + (f", {hc['trapped']} trapped" if hc["trapped"] else "") + (f", {hc['injured']} injured" if hc["injured"] else "") + ".")
        if f["blocked_exits"]:
            s += f" Exits blocked: {', '.join(f['blocked_exits'])}."
        if f["unsafe_assembly_points"]:
            s += f" Unsafe assembly points: {', '.join(f['unsafe_assembly_points'])}."
        return s

    def _request_sitrep(self, t: int) -> bool:
        if self.pending:
            return False
        self.pending = True
        self.last_sitrep_t = t
        f = self.facts()
        prompt = ("Write a situation report for the plant incident commander from these CURRENT facts "
                  "(they replace any earlier report; do not mention anything that is not in them). "
                  "Format: 2-3 short sentences on the situation, then a line starting 'Actions:' with 2 recommended "
                  "actions. Max 90 words.\n\nFACTS:\n" + json.dumps(f, indent=1))
        sys = system_base(self.e) + " You are the Hazard Assessment Agent."

        def done(text: str, llm: bool):
            self.pending = False
            self.inc["sitrep"] = {"t": self.e.t, "text": text, "llm": llm}
            self.log("SITREP: " + text, "info", llm=llm, kind="sitrep")

        self.e.spawn_llm(lambda: self.e.llm.chat(sys, prompt, 200), done, lambda: self._template(f))
        return True

    def step(self, t: int):
        if t % EVERY:
            return
        inc = self.inc
        # The system only "knows" about a hazard once a detector has confirmed something.
        # From then on, the hazard picture comes from the detector network + spread model
        # (here: the simulator's fields stand in for that model's output).
        if inc["stage"] == 0 and not inc["alarms"]:
            return
        stats = self._zone_stats()
        prev = inc["zone_hazards"]
        for z, h in stats.items():
            if z not in prev:
                kinds = [k for k in ("fire_m2", "gas_max_lel", "smoke_max_pct") if k in h]
                desc = {"fire_m2": f"fire (~{h.get('fire_m2')} m2)",
                        "gas_max_lel": f"flammable gas cloud (max {h.get('gas_max_lel')}% LEL)",
                        "smoke_max_pct": f"heavy smoke ({h.get('smoke_max_pct')}%)"}
                self.log(f"Hazard confirmed in {self.zname(z)}: " + ", ".join(desc[k] for k in kinds) + ".",
                         "critical" if "fire_m2" in h or "gas_max_lel" in h else "warn")
        for z in prev:
            if z not in stats:
                self.log(f"{self.zname(z)}: hazard no longer detected.", "info")
        inc["zone_hazards"] = stats

        hc = self.e.headcount()
        moving = hc["evacuating"] > 0 or hc["trapped"] > 0
        active = bool(stats or inc["alarms"]) or moving
        # everything that would make the last report wrong if it changed
        sig = (tuple(sorted(stats)), inc["stage"], tuple(sorted(inc["unsafe_aps"])),
               tuple(sorted(inc["blocked_exits"])), inc["all_clear_t"] is not None,
               tuple(l.isolated for l in self.e.hz.leaks))
        if sig != self.last_sig and self.last_sig_or_first(active) and t - self.last_sitrep_t >= SITREP_MIN_GAP:
            if self._request_sitrep(t):
                self.last_sig = sig
        elif active and t - self.last_sitrep_t >= SITREP_PERIOD:
            self._request_sitrep(t)

    def last_sig_or_first(self, active: bool) -> bool:
        return active or self.last_sig is not None

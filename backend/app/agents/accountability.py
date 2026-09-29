"""Accountability Agent: keeps the muster roll (who is where), reports progress
and declares ALL CLEAR once everyone in the evacuation scope is accounted for."""
from __future__ import annotations

from .base import Agent

REPORT_EVERY = 10


class AccountabilityAgent(Agent):
    name = "Accountability"

    def __init__(self, engine):
        super().__init__(engine)
        self.last_sig = None
        self.last_t = -999

    def step(self, t: int):
        inc, e = self.inc, self.e
        if inc["stage"] < 2:
            return
        hc = e.headcount()
        sig = (hc["safe"], hc["evacuating"], hc["trapped"], hc["injured"])
        if sig != self.last_sig and t - self.last_t >= REPORT_EVERY:
            self.last_sig, self.last_t = sig, t
            by_ap = ", ".join(f"{k} {v}" for k, v in hc["by_ap"].items() if v)
            self.log(f"Muster: {hc['safe']}/{hc['total']} accounted at assembly points"
                     + (f" ({by_ap})" if by_ap else "") + f"; {hc['evacuating']} en route; "
                     f"{hc['working']} still at work (outside evacuation scope)"
                     + (f"; {hc['trapped']} TRAPPED" if hc["trapped"] else "")
                     + (f"; {hc['injured']} INJURED" if hc["injured"] else "") + ".",
                     "warn" if hc["trapped"] or hc["injured"] else "info")

        if inc["all_clear_t"] is None and hc["in_scope"] > 0 and hc["evacuating"] == 0 and hc["trapped"] == 0:
            if hc["in_scope_safe"] + hc["injured"] >= hc["in_scope"]:
                inc["all_clear_t"] = t
                dur = t - (inc["started_t"] or t)
                m, s = divmod(dur, 60)
                extra = f" {hc['injured']} casualties need medical attention." if hc["injured"] else ""
                pq = e.peak_queue
                if pq["n"] >= 3:
                    extra += f" Worst bottleneck: {pq['n']} people queued at {pq['label']}."
                self.log(f"ALL CLEAR: all {hc['in_scope_safe']} people in the evacuation scope accounted for "
                         f"in {m}m {s:02d}s.{extra}", "success", kind="decision")
        elif inc["all_clear_t"] is not None and hc["evacuating"] > 0:
            inc["all_clear_t"] = None  # scope grew (e.g. escalation) - not clear any more

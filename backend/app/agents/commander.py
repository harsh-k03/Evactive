"""Incident Commander Agent: applies the site emergency response policy.

Escalation ladder (deterministic, auditable):
  Stage 1 ALERT            any confirmed low-level alarm (gas A1, smoke)
  Stage 2 ZONE EVACUATION  flame alarm, gas A2, 2+ alarms in a zone, or a confirmed hazard
                           -> evacuate the zone and the zones connected to it
  Stage 3 SITE EVACUATION  hazards in 2+ zones, or a large fire
Plus: Emergency Shutdown (ESD) isolation of the gas supply on a confirmed A2 gas alarm.
"""
from __future__ import annotations

from collections import Counter

from .base import Agent

SITE_FIRE_M2 = 300


class CommanderAgent(Agent):
    name = "Commander"

    def __init__(self, engine):
        super().__init__(engine)
        self.esd_done: set[str] = set()

    def _evacuate_zone(self, zid: str, reason: str):
        e, g = self.e, self.e.grid
        targets = [zid] + sorted(z for z in g.adjacency.get(zid, ()) if z not in self.inc["evac_zones"])
        ordered = [z for z in targets if e.order_evacuation(z, by=self.name)]
        if ordered:
            self.log(f"ORDER: evacuate {', '.join(self.zname(z) for z in ordered)} - {reason}.", "critical",
                     kind="decision")

    def step(self, t: int):
        inc, e = self.inc, self.e
        alarms = inc["alarms"]
        hazards = inc["zone_hazards"]

        # ---- stage 1
        if alarms and inc["stage"] == 0:
            inc["stage"] = 1
            zones = sorted({self.zname(a["zone"]) for a in alarms.values()})
            self.log(f"Stage 1 ALERT declared ({', '.join(zones)}). Emergency Response Team to verify; "
                     f"control room on standby.", "warn", kind="decision")

        # ---- stage 2: per-zone triggers
        per_zone = Counter(a["zone"] for a in alarms.values())
        for a in alarms.values():
            z = a["zone"]
            if z is None or z in inc["evac_zones"]:
                continue
            if a["type"] == "flame":
                self._evacuate_zone(z, f"flame detected by {a['sensor']}")
            elif a["type"] == "gas" and a["state"] == "A2":
                self._evacuate_zone(z, f"{a['gas']} at high alarm on {a['sensor']}")
            elif per_zone[z] >= 2:
                self._evacuate_zone(z, f"{per_zone[z]} detectors in alarm (voting logic)")
        for z, h in hazards.items():
            if z not in inc["evac_zones"] and ("fire_m2" in h or "gas_max_lel" in h):
                self._evacuate_zone(z, "hazard confirmed by assessment")

        # ---- ESD on high gas alarms
        for a in alarms.values():
            if a["type"] != "gas" or a["state"] != "A2":
                continue
            s = next(s for s in e.sensors.sensors if s.id == a["sensor"])
            for lk in e.hz.leaks:
                if lk.isolated or lk.id in self.esd_done:
                    continue
                near = lk.zone == a["zone"] or (abs(lk.x - s.x) + abs(lk.y - s.y)) <= 18
                if near:
                    self.esd_done.add(lk.id)
                    e.isolate_leaks([lk.id], by=self.name)
                    self.log(f"ESD triggered: shutdown valve closed on {lk.gas} supply in {self.zname(lk.zone)} "
                             f"(leak {lk.id}). Release will stop in ~{lk.ramp_s}s.", "critical", kind="decision")

        # ---- stage 3
        if not inc["site_evac"]:
            fire_total = sum(h.get("fire_m2", 0) for h in hazards.values())
            serious = [z for z, h in hazards.items() if "fire_m2" in h or "gas_max_lel" in h]
            reason = None
            outdoor_zones = {z["id"] for z in e.layout["zones"] if not z.get("walled", True)}
            open_air_a2 = [a for a in alarms.values() if a["type"] == "gas" and a["state"] == "A2"
                           and (a["zone"] is None or a["zone"] in outdoor_zones)]
            if len(serious) >= 2:
                reason = f"hazards in {len(serious)} zones ({', '.join(self.zname(z) for z in serious)})"
            elif open_air_a2:
                reason = (f"open-air flammable gas release ({open_air_a2[0]['sensor']} at high alarm) can reach "
                          f"ignition sources across the site")
            elif fire_total >= SITE_FIRE_M2:
                reason = f"fire area ~{fire_total} m2 exceeds site-evacuation threshold"
            if reason and e.order_evacuation("site", by=self.name):
                self.log(f"ESCALATION: FULL SITE EVACUATION - {reason}.", "critical", kind="decision")

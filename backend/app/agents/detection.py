"""Detection Agent: watches every field detector, debounces, and raises confirmed alarms."""
from __future__ import annotations

from .base import Agent

RANK = {"normal": 0, "alarm": 2, "A1": 1, "A2": 2}
CONFIRM_TICKS = 2  # alarm must persist this many seconds (filters nuisance trips)


class DetectionAgent(Agent):
    name = "Detection"

    def __init__(self, engine):
        super().__init__(engine)
        self.pending: dict[str, int] = {}      # sensor_id -> consecutive ticks at raw state
        self.confirmed: dict[str, str] = {}    # sensor_id -> confirmed state

    def step(self, t: int):
        alarms = self.inc["alarms"]
        for s in self.e.sensors.sensors:
            prev = self.confirmed.get(s.id, "normal")
            if s.state == prev:
                self.pending.pop(s.id, None)
                continue
            self.pending[s.id] = self.pending.get(s.id, 0) + 1
            if self.pending[s.id] < CONFIRM_TICKS:
                continue
            self.pending.pop(s.id, None)
            self.confirmed[s.id] = s.state
            where = self.zname(s.zone)
            if s.state == "normal":
                alarms.pop(s.id, None)
                self.log(f"{s.id} returned to normal ({where}).", "info")
                continue
            alarms[s.id] = {"sensor": s.id, "type": s.type, "state": s.state, "zone": s.zone,
                            "gas": s.gas, "value": s.value, "t": t}
            escalating = RANK[s.state] > RANK[prev]
            if s.type == "gas":
                lvl = "critical" if s.state == "A2" else "warn"
                verb = "reached" if escalating else "fell to"
                self.log(f"{s.id} {s.gas} {verb} {s.value:.0f}% LEL in {where} -> {s.state} "
                         f"({'high' if s.state == 'A2' else 'low'} alarm).", lvl)
            elif s.type == "flame":
                self.log(f"{s.id} UV/IR flame detector ALARM in {where} ({int(s.value)} flame cells in view).", "critical")
            elif s.type == "smoke":
                self.log(f"{s.id} smoke detector ALARM in {where} (obscuration {s.value:.0f}%).", "warn")

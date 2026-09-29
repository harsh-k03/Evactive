"""Simulated field detectors: UV/IR flame, point smoke, and flammable gas (%LEL)."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .grid import WALL, Grid
from .hazards import BURNING, HazardField

GAS_A1 = 20.0   # %LEL - low alarm
GAS_A2 = 40.0   # %LEL - high alarm
SMOKE_ALARM = 0.12
FLAME_RANGE = 10  # cells (~20 m)


def _los_mask(grid: Grid, x0: int, y0: int, r: int) -> np.ndarray:
    m = np.zeros((grid.h, grid.w), dtype=bool)
    for y in range(max(0, y0 - r), min(grid.h, y0 + r + 1)):
        for x in range(max(0, x0 - r), min(grid.w, x0 + r + 1)):
            if (x - x0) ** 2 + (y - y0) ** 2 > r * r:
                continue
            # walk the line; blocked by walls
            n = max(abs(x - x0), abs(y - y0))
            ok = True
            for i in range(1, n):
                cx = round(x0 + (x - x0) * i / n)
                cy = round(y0 + (y - y0) * i / n)
                if grid.cell[cy, cx] == WALL:
                    ok = False
                    break
            if ok and grid.cell[y, x] != WALL:
                m[y, x] = True
    return m


@dataclass
class Sensor:
    id: str
    type: str                 # flame | smoke | gas
    x: int
    y: int
    zone: str | None
    gas: str | None = None
    value: float = 0.0
    state: str = "normal"     # normal | alarm | A1 | A2
    view: np.ndarray | None = field(default=None, repr=False)

    def unit(self) -> str:
        return {"gas": "%LEL", "smoke": "%obs", "flame": "px"}[self.type]


class SensorNetwork:
    def __init__(self, grid: Grid, rng: np.random.Generator):
        self.g = grid
        self.rng = rng
        self.sensors: list[Sensor] = []
        for s in grid.layout["sensors"]:
            x, y = s["pos"]
            sen = Sensor(s["id"], s["type"], x, y, grid.zone_at(x, y), s.get("gas"))
            if sen.type == "flame":
                sen.view = _los_mask(grid, x, y, FLAME_RANGE)
            self.sensors.append(sen)

    def update(self, hz: HazardField):
        lel = hz.gas_lel()
        burning = hz.fire == BURNING
        for s in self.sensors:
            if s.type == "gas":
                v = float(lel[s.y, s.x])
                v = max(0.0, v + self.rng.normal(0, 0.3)) if v > 0.5 else max(0.0, self.rng.normal(0.2, 0.15))
                s.value = round(v, 1)
                s.state = "A2" if v >= GAS_A2 else "A1" if v >= GAS_A1 else "normal"
            elif s.type == "smoke":
                v = float(hz.smoke[s.y, s.x])
                s.value = round(v * 100, 1)
                s.state = "alarm" if v >= SMOKE_ALARM else "normal"
            elif s.type == "flame":
                v = int(np.count_nonzero(burning & s.view))
                s.value = v
                s.state = "alarm" if v > 0 else "normal"

    def payload(self) -> list[dict]:
        return [{"id": s.id, "v": s.value, "state": s.state} for s in self.sensors]

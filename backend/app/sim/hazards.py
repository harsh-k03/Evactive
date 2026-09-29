"""
Simplified hazard models on the grid (1 tick = 1 simulated second, 1 cell = 2 m).

- Fire: stochastic cellular automaton driven by fuel load; walls stop it.
- Smoke: produced by burning cells, diffuses through open cells, advected by
  wind outdoors, decays faster outdoors.
- Flammable gas: point leaks (in %LEL units) that diffuse through open cells,
  drift with the wind outdoors and dilute over time. Leaks can be isolated
  (ESD valve closure), after which the release rate ramps down to zero.

These are demo-grade models meant to look and behave plausibly, not CFD.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .grid import Grid

NONE, BURNING, BURNT = 0, 1, 2


@dataclass
class Leak:
    id: str
    x: int
    y: int
    rate: float          # %LEL-units added per tick at the source cell
    gas: str
    zone: str | None
    started_t: int
    isolated_t: int | None = None
    ramp_s: int = 40     # seconds for flow to stop after ESD valve closes
    grow_s: int = 25     # seconds for the release to develop to full rate (crack/gasket failure grows)

    def current_rate(self, t: int) -> float:
        r = self.rate * min(1.0, max(0.0, (t - self.started_t + 1) / self.grow_s))
        if self.isolated_t is None:
            return r
        frac = 1 - (t - self.isolated_t) / self.ramp_s
        return r * max(0.0, frac)

    @property
    def isolated(self) -> bool:
        return self.isolated_t is not None


class HazardField:
    D_SMOKE = 0.20
    D_GAS = 0.22
    FIRE_P = 0.045            # base spread probability per burning neighbour per tick

    def __init__(self, grid: Grid, rng: np.random.Generator):
        self.g = grid
        self.rng = rng
        h, w = grid.h, grid.w
        self.fire = np.zeros((h, w), dtype=np.int8)
        self.fire_age = np.zeros((h, w), dtype=np.int32)
        self.burn_time = (120 + 420 * grid.fuel).astype(np.int32)
        self.smoke = np.zeros((h, w), dtype=np.float32)
        self.gas = np.zeros((h, w), dtype=np.float32)
        self.leaks: list[Leak] = []
        self.wind_from_deg = 270.0
        self.wind_mps = 2.0
        # conductance masks between neighbouring open cells
        o = grid.open_air
        self.cE = np.zeros_like(o); self.cE[:, :-1] = o[:, :-1] & o[:, 1:]
        self.cS = np.zeros_like(o); self.cS[:-1, :] = o[:-1, :] & o[1:, :]
        self.outdoor = ~grid.indoor & o
        self.flammable = grid.fuel > 0

    # ------------------------------------------------------------------ events
    def ignite(self, x: int, y: int) -> bool:
        if not self.flammable[y, x] or self.fire[y, x] != NONE:
            return False
        self.fire[y, x] = BURNING
        # a small initial fire cluster so it doesn't fizzle out
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if self.g.in_bounds(nx, ny) and self.flammable[ny, nx] and self.rng.random() < 0.6:
                self.fire[ny, nx] = BURNING
        return True

    def add_leak(self, leak: Leak):
        self.leaks.append(leak)

    def set_wind(self, from_deg: float, speed_mps: float):
        self.wind_from_deg = from_deg % 360
        self.wind_mps = max(0.0, speed_mps)

    # ---------------------------------------------------------------- physics
    def _diffuse(self, f: np.ndarray, D: float) -> np.ndarray:
        dE = np.zeros_like(f); dE[:, :-1] = (f[:, 1:] - f[:, :-1]) * self.cE[:, :-1]
        dS = np.zeros_like(f); dS[:-1, :] = (f[1:, :] - f[:-1, :]) * self.cS[:-1, :]
        lap = dE.copy()
        lap[:, 1:] -= dE[:, :-1]
        lap += dS
        lap[1:, :] -= dS[:-1, :]
        return f + D * lap

    def _advect(self, f: np.ndarray) -> np.ndarray:
        """First-order upwind advection, outdoor cells only."""
        if self.wind_mps <= 0.05:
            return f
        toward = math.radians(self.wind_from_deg + 180)
        speed = self.wind_mps / self.g.layout["cell_m"] * 0.45  # effective plume transport, cells/tick
        u, v = math.sin(toward) * speed, -math.cos(toward) * speed
        steps = max(1, int(math.ceil(max(abs(u), abs(v)) / 0.45)))
        u, v = u / steps, v / steps
        m = self.outdoor
        for _ in range(steps):
            g = f.copy()
            if u > 0:
                up = np.zeros_like(f); up[:, 1:] = f[:, :-1]
                ok = np.zeros_like(m); ok[:, 1:] = m[:, 1:] & m[:, :-1]
            else:
                up = np.zeros_like(f); up[:, :-1] = f[:, 1:]
                ok = np.zeros_like(m); ok[:, :-1] = m[:, :-1] & m[:, 1:]
            g = np.where(ok, g - abs(u) * (f - up), g)
            f2 = g
            if v > 0:
                up = np.zeros_like(f); up[1:, :] = f2[:-1, :]
                ok = np.zeros_like(m); ok[1:, :] = m[1:, :] & m[:-1, :]
            else:
                up = np.zeros_like(f); up[:-1, :] = f2[1:, :]
                ok = np.zeros_like(m); ok[:-1, :] = m[:-1, :] & m[1:, :]
            f = np.where(ok, f2 - abs(v) * (f2 - up), f2)
        return f

    def step(self, t: int):
        g = self.g
        # ---- fire
        burning = self.fire == BURNING
        if burning.any():
            n = np.zeros(self.fire.shape, dtype=np.int8)
            n[1:, :] += burning[:-1, :]
            n[:-1, :] += burning[1:, :]
            n[:, 1:] += burning[:, :-1]
            n[:, :-1] += burning[:, 1:]
            p = 1 - (1 - self.FIRE_P * g.fuel) ** n
            ignite = (self.fire == NONE) & self.flammable & (self.rng.random(self.fire.shape) < p)
            self.fire[ignite] = BURNING
            self.fire_age[self.fire == BURNING] += 1
            done = (self.fire == BURNING) & (self.fire_age > self.burn_time)
            self.fire[done] = BURNT
            burning = self.fire == BURNING

        # ---- smoke
        s = self.smoke
        s[burning] = np.maximum(s[burning], 0.95)
        s = self._diffuse(s, self.D_SMOKE)
        s = self._advect(s)
        s *= np.where(self.outdoor, 0.95, 0.9985)
        s[~g.open_air] = 0
        self.smoke = np.clip(s, 0, 1).astype(np.float32)

        # ---- gas
        c = self.gas
        for lk in self.leaks:
            r = lk.current_rate(t)
            if r > 0:
                c[lk.y, lk.x] += r
        for _ in range(2):
            c = self._diffuse(c, self.D_GAS)
        c = self._advect(c)
        c *= np.where(self.outdoor, 0.965, 0.996)
        c[~g.open_air] = 0
        c[c < 0.05] = 0
        self.gas = c.astype(np.float32)

    # ---------------------------------------------------------------- queries
    def gas_lel(self) -> np.ndarray:
        return np.clip(self.gas, 0, 100)

    def fire_distance(self, max_d: int = 4) -> np.ndarray:
        """Chebyshev distance to nearest burning cell, capped at max_d+1."""
        d = np.full(self.fire.shape, max_d + 1, dtype=np.int16)
        cur = self.fire == BURNING
        d[cur] = 0
        for k in range(1, max_d + 1):
            v = cur.copy()
            v[1:, :] |= cur[:-1, :]
            v[:-1, :] |= cur[1:, :]
            grown = v.copy()
            grown[:, 1:] |= v[:, :-1]
            grown[:, :-1] |= v[:, 1:]
            new = grown & ~cur
            d[new] = np.minimum(d[new], k)
            cur = grown
        return d

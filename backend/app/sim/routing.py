"""
Hazard-aware evacuation routing.

One reverse multi-source Dijkstra from every *safe* assembly point gives a
cost-to-safety field for the whole plant. Each worker simply walks downhill on
that field, so re-planning for all workers costs one Dijkstra, no matter how
many people are on site. Deterministic and auditable by design: the LLM agents
never decide routes.
"""
from __future__ import annotations

import heapq
import math

import numpy as np

from .grid import Grid
from .hazards import BURNING, BURNT, HazardField

INF = float("inf")
SQ2 = math.sqrt(2)
NEIGH = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
         (1, 1, SQ2), (1, -1, SQ2), (-1, 1, SQ2), (-1, -1, SQ2)]


CROWD_W = 2.5  # extra cost per person already in a cell: routes spread across exits instead of piling up


def cell_costs(grid: Grid, hz: HazardField, crowd: np.ndarray | None = None) -> np.ndarray:
    """Cost multiplier for entering each cell. inf = impassable."""
    lel = hz.gas_lel()
    cost = 1.0 + 25.0 * hz.smoke ** 1.5 + 0.6 * lel
    cost = cost + np.where(lel >= 60, 150.0, 0.0)
    fd = hz.fire_distance(3)
    cost = cost + np.select([fd == 1, fd == 2, fd == 3], [60.0, 20.0, 6.0], 0.0)
    if crowd is not None:
        cost = cost + CROWD_W * np.maximum(0.0, crowd - 1.0)
    cost = cost.astype(np.float64)
    blocked = (~grid.walkable) | (hz.fire == BURNING) | (hz.fire == BURNT)
    cost[blocked] = INF
    return cost


def cost_field(grid: Grid, cost: np.ndarray, safe_aps: list[str]):
    """Returns (dist, label) where label[y,x] = index into safe_aps of the AP reached."""
    h, w = grid.h, grid.w
    dist = np.full((h, w), INF)
    label = np.full((h, w), -1, dtype=np.int16)
    pq = []
    for i, ap in enumerate(safe_aps):
        ys, xs = np.nonzero(grid.ap_mask[ap] & np.isfinite(cost))
        for y, x in zip(ys.tolist(), xs.tolist()):
            dist[y, x] = 0.0
            label[y, x] = i
            pq.append((0.0, x, y))
    heapq.heapify(pq)
    walk = np.isfinite(cost)
    cost_l = cost.tolist()
    dist_l = dist.tolist()
    walk_l = walk.tolist()
    label_l = label.tolist()
    while pq:
        d, x, y = heapq.heappop(pq)
        if d > dist_l[y][x]:
            continue
        c_here = cost_l[y][x]  # cost paid to *enter* (x, y) when coming from a neighbour
        lab = label_l[y][x]
        for dx, dy, sl in NEIGH:
            nx, ny = x + dx, y + dy
            if nx < 0 or ny < 0 or nx >= w or ny >= h or not walk_l[ny][nx]:
                continue
            if dx and dy and not (walk_l[y][nx] and walk_l[ny][x]):
                continue  # no corner cutting
            nd = d + c_here * sl
            if nd < dist_l[ny][nx]:
                dist_l[ny][nx] = nd
                label_l[ny][nx] = lab
                heapq.heappush(pq, (nd, nx, ny))
    return np.array(dist_l), np.array(label_l, dtype=np.int16)


def next_step(grid: Grid, dist: np.ndarray, cost: np.ndarray, x: int, y: int):
    """Best neighbour to move to from (x, y), or None if already optimal/stuck."""
    # dist[u] = min over neighbours v of dist[v] + cost[v] * step_len
    best, bx, by = INF, None, None
    for dx, dy, sl in NEIGH:
        nx, ny = x + dx, y + dy
        if not grid.in_bounds(nx, ny) or not np.isfinite(cost[ny, nx]):
            continue
        if dx and dy and not (np.isfinite(cost[y, nx]) and np.isfinite(cost[ny, x])):
            continue
        cand = dist[ny, nx] + cost[ny, nx] * sl
        if cand < best:
            best, bx, by = cand, nx, ny
    if bx is None or not np.isfinite(best):
        return None
    return bx, by


def trace_path(grid: Grid, dist: np.ndarray, cost: np.ndarray, x: int, y: int, limit: int = 400):
    path = [(x, y)]
    for _ in range(limit):
        if dist[y, x] == 0:
            break
        nxt = next_step(grid, dist, cost, x, y)
        if nxt is None:
            break
        x, y = nxt
        path.append((x, y))
    return path


def simplify(path):
    """Keep only corner points for display."""
    if len(path) <= 2:
        return [list(p) for p in path]
    out = [path[0]]
    for i in range(1, len(path) - 1):
        a, b, c = path[i - 1], path[i], path[i + 1]
        if (b[0] - a[0], b[1] - a[1]) != (c[0] - b[0], c[1] - b[1]):
            out.append(b)
    out.append(path[-1])
    return [list(p) for p in out]

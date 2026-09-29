"""Turns a layout dict into numpy grids the simulation works on."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

# cell types
YARD, FLOOR, WALL, DOOR, OBSTACLE, EXIT = 0, 1, 2, 3, 4, 5
CELL_NAMES = {YARD: "yard", FLOOR: "floor", WALL: "wall", DOOR: "door", OBSTACLE: "obstacle", EXIT: "exit"}


@dataclass
class Grid:
    layout: dict
    w: int
    h: int
    cell: np.ndarray            # int8 cell types (h, w)
    walkable: np.ndarray        # bool
    open_air: np.ndarray        # bool: gas/smoke can occupy the cell (everything except walls)
    indoor: np.ndarray          # bool
    zone: np.ndarray            # int16 zone index, -1 = none
    fuel: np.ndarray            # float fire fuel load 0..1
    zone_ids: list = field(default_factory=list)
    zone_names: dict = field(default_factory=dict)
    ap_mask: dict = field(default_factory=dict)       # ap_id -> bool mask
    exit_cells: dict = field(default_factory=dict)    # exit_id -> list[(x, y)]
    exit_of_cell: dict = field(default_factory=dict)  # (x, y) -> exit_id
    adjacency: dict = field(default_factory=dict)     # zone_id -> set(zone_id)

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.w and 0 <= y < self.h

    def zone_at(self, x: int, y: int) -> str | None:
        z = int(self.zone[y, x])
        return self.zone_ids[z] if z >= 0 else None


def _rect_slices(r):
    x0, y0, x1, y1 = r
    return slice(y0, y1 + 1), slice(x0, x1 + 1)


def _draw_walled_rect(cell, r):
    x0, y0, x1, y1 = r
    cell[y0, x0:x1 + 1] = WALL
    cell[y1, x0:x1 + 1] = WALL
    cell[y0:y1 + 1, x0] = WALL
    cell[y0:y1 + 1, x1] = WALL


def build_grid(layout: dict) -> Grid:
    w, h = layout["width"], layout["height"]
    cell = np.full((h, w), YARD, dtype=np.int8)
    indoor = np.zeros((h, w), dtype=bool)
    zone = np.full((h, w), -1, dtype=np.int16)
    fuel = np.full((h, w), 0.05, dtype=np.float32)  # yard: grass/debris, very low

    for b in layout["buildings"]:
        sl = _rect_slices(b["rect"])
        cell[sl] = FLOOR
        indoor[sl] = True
        _draw_walled_rect(cell, b["rect"])

    zone_ids = [z["id"] for z in layout["zones"]]
    zone_names = {z["id"]: z["name"] for z in layout["zones"]}
    for i, z in enumerate(layout["zones"]):
        x0, y0, x1, y1 = z["rect"]
        if z.get("walled", True):
            zone[y0 + 1:y1, x0 + 1:x1] = i
            fuel[y0 + 1:y1, x0 + 1:x1] = z.get("fuel", 0.3)
            _draw_walled_rect(cell, z["rect"])
        else:
            zone[y0:y1 + 1, x0:x1 + 1] = i
            fuel[y0:y1 + 1, x0:x1 + 1] = z.get("fuel", 0.3)

    for x, y in layout["doors"]:
        cell[y, x] = DOOR

    exit_cells, exit_of_cell = {}, {}
    for e in layout["exits"]:
        cells = [tuple(c) for c in e["cells"]]
        exit_cells[e["id"]] = cells
        for x, y in cells:
            cell[y, x] = EXIT
            exit_of_cell[(x, y)] = e["id"]

    for o in layout["obstacles"]:
        sl = _rect_slices(o["rect"])
        cell[sl] = OBSTACLE

    # walls don't burn; doors/exits burn a little so fire can pass slowly
    fuel[cell == WALL] = 0.0
    fuel[(cell == DOOR) | (cell == EXIT)] = 0.1

    # doors/exits belong to the zone of any adjacent floor cell (first found)
    for (x, y) in list(zip(*np.where((cell == DOOR) | (cell == EXIT))[::-1])):
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and zone[ny, nx] >= 0 and cell[ny, nx] not in (DOOR, EXIT):
                zone[y, x] = zone[ny, nx]
                break

    walkable = np.isin(cell, (YARD, FLOOR, DOOR, EXIT))
    open_air = cell != WALL

    ap_mask = {}
    for ap in layout["assembly_points"]:
        m = np.zeros((h, w), dtype=bool)
        m[_rect_slices(ap["rect"])] = True
        ap_mask[ap["id"]] = m & walkable

    # zone adjacency through doors
    adjacency = {zid: set() for zid in zone_ids}
    for (x, y) in zip(*np.where(cell == DOOR)[::-1]):
        near = set()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and zone[ny, nx] >= 0 and cell[ny, nx] == FLOOR:
                near.add(zone_ids[zone[ny, nx]])
        for a in near:
            adjacency[a] |= near - {a}

    return Grid(layout, w, h, cell, walkable, open_air, indoor, zone, fuel, zone_ids, zone_names,
                ap_mask, exit_cells, exit_of_cell, adjacency)


def static_payload(grid: Grid) -> dict:
    """Static layout info sent to the dashboard once."""
    L = grid.layout
    zones = []
    for z in L["zones"]:
        x0, y0, x1, y1 = z["rect"]
        zones.append({"id": z["id"], "name": z["name"], "short": z.get("short", z["name"]).upper(), "rect": z["rect"],
                      "label": [(x0 + x1) / 2, y0 + 1.6 if z.get("walled", True) else y0 + 0.6]})
    return {
        "id": L["id"], "name": L["name"], "width": grid.w, "height": grid.h, "cell_m": L["cell_m"],
        "cells": grid.cell.flatten().tolist(),
        "zones": zones,
        "exits": [{"id": k, "cells": v} for k, v in grid.exit_cells.items()],
        "assembly_points": L["assembly_points"],
        "obstacles": L["obstacles"],
        "sensors": L["sensors"],
        "gases": L.get("gases", ["Natural gas (CH4)"]),
        "industry": L.get("industry", ""),
    }

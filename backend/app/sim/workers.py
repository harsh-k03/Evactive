"""Simulated on-site personnel (employees, contractors, visitors)."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .grid import FLOOR, YARD, Grid

FIRST = ["Rakesh", "Sunil", "Amit", "Pooja", "Vikas", "Neha", "Manoj", "Sanjay", "Deepak", "Anil",
         "Ravi", "Priya", "Arjun", "Kavita", "Rahul", "Suresh", "Meena", "Ajay", "Rohit", "Sunita",
         "Vijay", "Ankit", "Gaurav", "Ritu", "Naveen", "Pankaj", "Shalini", "Mohit", "Imran", "Harpreet",
         "Dinesh", "Asha", "Yogesh", "Sachin", "Nitin", "Farhan", "Kiran", "Lokesh", "Mahesh", "Sneha"]
LAST = ["Kumar", "Sharma", "Singh", "Verma", "Yadav", "Gupta", "Chauhan", "Rawat", "Negi", "Saini",
        "Pal", "Tyagi", "Bisht", "Khan", "Joshi", "Rana", "Tomar", "Arora"]
ROLES = {
    "batch": ["Batch Operator", "Mixer Operator", "Helper"],
    "furnace": ["Furnace Operator", "Hot End Technician", "Shift Engineer"],
    "tinbath": ["Bath Operator", "Hot End Technician"],
    "lehr": ["Lehr Operator", "Process Technician"],
    "coldend": ["Cutting Operator", "Quality Inspector", "Stacker Operator", "Helper"],
    "warehouse": ["Forklift Operator", "Loader", "Dispatch Clerk", "Stores Assistant"],
    "control": ["DCS Operator", "Shift In-charge"],
    "admin": ["HR Executive", "Accountant", "Plant Manager", "Safety Officer", "Visitor"],
    "utility": ["Utility Operator", "Maintenance Fitter"],
    "gasyard": ["Gas Station Operator"],
}

# statuses
WORKING, ALERTED, EVACUATING, SAFE, TRAPPED, INJURED = "working", "alerted", "evacuating", "safe", "trapped", "injured"


@dataclass
class Worker:
    id: str
    name: str
    role: str
    kind: str                    # employee | contractor | visitor
    zone: str
    x: int
    y: int
    speed: float                 # cells per tick
    status: str = WORKING
    alert_at: int | None = None  # tick at which they start moving
    progress: float = 0.0
    ap: str | None = None        # AP currently routed to / reached
    exit: str | None = None      # exit on current route
    evac_start: int | None = None
    safe_at: int | None = None
    reroutes: int = 0
    self_evacuated: bool = False
    burn_ticks: int = 0
    waiting: int = 0
    still: int = 0
    blocked_at: tuple | None = None
    path: list = field(default_factory=list)

    def payload(self) -> dict:
        return {"id": self.id, "x": self.x, "y": self.y, "s": self.status, "ap": self.ap,
                "name": self.name, "role": self.role, "zone": self.zone, "kind": self.kind}


def spawn_workers(grid: Grid, rng: np.random.Generator) -> list[Worker]:
    workers: list[Worker] = []
    taken = set()
    n = 0
    for zid, count in grid.layout["staffing"].items():
        zi = grid.zone_ids.index(zid)
        ys, xs = np.nonzero((grid.zone == zi) & np.isin(grid.cell, (FLOOR, YARD)))
        idx = rng.permutation(len(xs))
        placed = 0
        for i in idx:
            if placed >= count:
                break
            x, y = int(xs[i]), int(ys[i])
            if (x, y) in taken:
                continue
            taken.add((x, y))
            n += 1
            zdef = next((z for z in grid.layout["zones"] if z["id"] == zid), {})
            role = str(rng.choice(zdef.get("roles") or ROLES.get(zid, ["Operator"])))
            kind = "visitor" if role == "Visitor" else ("contractor" if rng.random() < 0.18 else "employee")
            name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
            speed = float(np.clip(rng.normal(0.62, 0.08), 0.4, 0.8))  # ~1.2 m/s on 2 m cells
            workers.append(Worker(f"W-{n:03d}", name, role, kind, zid, x, y, speed))
            placed += 1
    return workers

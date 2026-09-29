"""
Sample plant layouts for the Evactive demo.

Coordinates are grid cells (x = column, y = row, origin top-left).
Rectangles are [x0, y0, x1, y1], inclusive. For walled buildings/zones the
border cells of the rectangle become walls.

These layouts are illustrative and not to scale of any real facility.
"""

FLOAT_GLASS_PLANT = {
    "id": "float-glass",
    "name": "Float Glass Plant - Line 1 (sample)",
    "width": 94,
    "height": 52,
    "cell_m": 2.0,  # 1 cell = 2 m x 2 m
    "buildings": [
        {"id": "main-hall", "rect": [4, 10, 85, 32]},
        {"id": "control-bldg", "rect": [36, 36, 46, 42]},
        {"id": "admin-bldg", "rect": [52, 38, 66, 47]},
        {"id": "utility-bldg", "rect": [72, 38, 82, 46]},
    ],
    # kind -> used for fuel load (fire) and labelling
    "zones": [
        {"id": "batch", "short": "BATCH HOUSE", "name": "Batch House", "rect": [4, 10, 16, 27], "walled": True, "fuel": 0.35},
        {"id": "furnace", "short": "MELTING FURNACE", "name": "Melting Furnace", "rect": [16, 10, 34, 27], "walled": True, "fuel": 0.25},
        {"id": "tinbath", "short": "TIN BATH", "name": "Tin Bath (Float Bath)", "rect": [34, 10, 48, 27], "walled": True, "fuel": 0.25},
        {"id": "lehr", "short": "ANNEALING LEHR", "name": "Annealing Lehr", "rect": [48, 10, 64, 27], "walled": True, "fuel": 0.3},
        {"id": "coldend", "short": "COLD END", "name": "Cold End (Cutting & Inspection)", "rect": [64, 10, 76, 27], "walled": True, "fuel": 0.6},
        {"id": "warehouse", "short": "WAREHOUSE", "name": "Warehouse & Dispatch", "rect": [76, 10, 85, 27], "walled": True, "fuel": 1.0},
        {"id": "corridor", "short": "SERVICE WALKWAY", "name": "Service Walkway", "rect": [4, 27, 85, 32], "walled": True, "fuel": 0.3},
        {"id": "control", "short": "CONTROL ROOM", "name": "Central Control Room", "rect": [36, 36, 46, 42], "walled": True, "fuel": 0.5},
        {"id": "admin", "short": "ADMIN BLOCK", "name": "Admin Block", "rect": [52, 38, 66, 47], "walled": True, "fuel": 0.6},
        {"id": "utility", "short": "N2/H2 PLANT", "name": "N2/H2 Utility Plant", "rect": [72, 38, 82, 46], "walled": True, "fuel": 0.3},
        {"id": "gasyard", "short": "GAS PRS / LPG YARD", "name": "Natural Gas PRS & LPG Yard", "rect": [6, 38, 18, 48], "walled": False, "fuel": 0.2},
    ],
    # internal door openings (cells)
    "doors": [
        # dividing walls along the line: openings in the north & south aisles
        *[[x, y] for x in (16, 34, 48, 64, 76) for y in (12, 13, 24, 25)],
        # zone -> service walkway
        *[[x, 27] for x in (10, 11, 25, 26, 41, 42, 56, 57, 70, 71, 80, 81)],
        # outbuilding doors
        [41, 36], [42, 36],
        [58, 38], [59, 38],
        [76, 38], [77, 38],
    ],
    "exits": [
        {"id": "E1", "cells": [[10, 10], [11, 10]]},
        {"id": "E2", "cells": [[25, 10], [26, 10]]},
        {"id": "E3", "cells": [[56, 10], [57, 10]]},
        {"id": "E4", "cells": [[70, 10], [71, 10]]},
        {"id": "E5", "cells": [[85, y] for y in range(16, 22)]},  # loading dock
        {"id": "E6", "cells": [[4, 29], [4, 30]]},
        {"id": "E7", "cells": [[40, 32], [41, 32]]},
        {"id": "E8", "cells": [[72, 32], [73, 32]]},
    ],
    "assembly_points": [
        {"id": "AP1", "name": "AP1 - Main Gate", "rect": [40, 1, 48, 5]},
        {"id": "AP2", "name": "AP2 - East Parking", "rect": [88, 18, 93, 26]},
        {"id": "AP3", "name": "AP3 - South Lawn", "rect": [22, 44, 30, 50]},
    ],
    # equipment footprints: not walkable, gas/smoke can pass over them
    "obstacles": [
        {"name": "Batch mixers & silos", "rect": [7, 14, 13, 20]},
        {"name": "Melting furnace", "rect": [18, 15, 32, 22]},
        {"name": "Tin bath", "rect": [35, 16, 47, 21]},
        {"name": "Annealing lehr", "rect": [49, 16, 63, 21]},
        {"name": "Cutting line", "rect": [66, 16, 74, 21]},
        {"name": "Rack A", "rect": [78, 13, 83, 14]},
        {"name": "Rack B", "rect": [78, 17, 83, 18]},
        {"name": "Rack C", "rect": [78, 21, 83, 22]},
        {"name": "Compressor skid", "rect": [75, 41, 79, 43]},
        {"name": "LPG bullets", "rect": [8, 43, 11, 46]},
        {"name": "PRS skid", "rect": [13, 40, 16, 42]},
    ],
    "sensors": [
        # UV/IR flame detectors
        {"id": "FD-01", "type": "flame", "pos": [25, 12]},
        {"id": "FD-02", "type": "flame", "pos": [25, 25]},
        {"id": "FD-03", "type": "flame", "pos": [41, 13]},
        {"id": "FD-04", "type": "flame", "pos": [80, 15]},
        {"id": "FD-05", "type": "flame", "pos": [70, 13]},
        {"id": "FD-06", "type": "flame", "pos": [12, 39]},
        # point smoke detectors
        {"id": "SD-01", "type": "smoke", "pos": [10, 12]},
        {"id": "SD-02", "type": "smoke", "pos": [56, 13]},
        {"id": "SD-03", "type": "smoke", "pos": [80, 24]},
        {"id": "SD-04", "type": "smoke", "pos": [30, 29]},
        {"id": "SD-05", "type": "smoke", "pos": [65, 29]},
        {"id": "SD-06", "type": "smoke", "pos": [41, 39]},
        {"id": "SD-07", "type": "smoke", "pos": [59, 42]},
        {"id": "SD-08", "type": "smoke", "pos": [70, 24]},
        # flammable gas detectors (%LEL)
        {"id": "GD-01", "type": "gas", "gas": "Natural gas (CH4)", "pos": [19, 24]},
        {"id": "GD-02", "type": "gas", "gas": "Natural gas (CH4)", "pos": [31, 12]},
        {"id": "GD-03", "type": "gas", "gas": "Hydrogen (H2)", "pos": [36, 13]},
        {"id": "GD-04", "type": "gas", "gas": "Hydrogen (H2)", "pos": [46, 24]},
        {"id": "GD-05", "type": "gas", "gas": "Natural gas (CH4)", "pos": [9, 41]},
        {"id": "GD-06", "type": "gas", "gas": "Flammable gas (LPG/CH4)", "pos": [16, 46]},
        {"id": "GD-07", "type": "gas", "gas": "Hydrogen (H2)", "pos": [74, 40]},
        {"id": "GD-08", "type": "gas", "gas": "Natural gas (CH4)", "pos": [20, 39]},
    ],
    # headcount per zone at shift start
    "staffing": {
        "batch": 5, "furnace": 7, "tinbath": 4, "lehr": 5, "coldend": 10,
        "warehouse": 8, "control": 4, "admin": 8, "utility": 2, "gasyard": 1,
    },
    "scenarios": [
        {
            "id": "furnace-gas-fire",
            "name": "Fuel gas leak at furnace burner -> ignition",
            "description": "Natural gas leak on a furnace burner line. The cloud ignites after ~90 s.",
            "wind": {"from_deg": 270, "speed_mps": 2.0},
            "events": [
                {"t": 3, "type": "leak", "pos": [23, 25], "rate": 220, "gas": "Natural gas (CH4)"},
                {"t": 100, "type": "fire", "pos": [23, 24]},
            ],
        },
        {
            "id": "warehouse-fire",
            "name": "Warehouse fire (packaging material)",
            "description": "Fire starts in the packing/interleaving material store and spreads along the racks.",
            "wind": {"from_deg": 90, "speed_mps": 3.0},
            "events": [{"t": 3, "type": "fire", "pos": [80, 19]}],
        },
        {
            "id": "tinbath-h2",
            "name": "Hydrogen leak at tin bath",
            "description": "H2 leak from the bath atmosphere supply line on the south aisle.",
            "wind": {"from_deg": 0, "speed_mps": 1.5},
            "events": [{"t": 3, "type": "leak", "pos": [40, 23], "rate": 280, "gas": "Hydrogen (H2)"}],
        },
        {
            "id": "gasyard-leak",
            "name": "Natural gas PRS leak, wind toward South Lawn",
            "description": "Large leak at the pressure reducing station. Westerly wind carries the cloud toward AP3.",
            "wind": {"from_deg": 270, "speed_mps": 3.5},
            "events": [{"t": 3, "type": "leak", "pos": [12, 44], "rate": 900, "gas": "Natural gas (CH4)"}],
        },
        {
            "id": "multi-hazard",
            "name": "Cold end fire + H2 leak at utility plant",
            "description": "Two simultaneous incidents that stress exit and assembly-point choices.",
            "wind": {"from_deg": 180, "speed_mps": 2.5},
            "events": [
                {"t": 3, "type": "fire", "pos": [70, 23]},
                {"t": 25, "type": "leak", "pos": [78, 40], "rate": 500, "gas": "Hydrogen (H2)"},
            ],
        },
    ],
}

LAYOUTS = {FLOAT_GLASS_PLANT["id"]: FLOAT_GLASS_PLANT}

# ---------------------------------------------------------------- other sample plants
from .plants.auto import AUTO_COMPONENTS  # noqa: E402
from .plants.pharma import PHARMA_API  # noqa: E402
from .plants.processing import GLASS_PROCESSING  # noqa: E402
from .plants.warehouse import HIGH_BAY_WAREHOUSE  # noqa: E402

FLOAT_GLASS_PLANT.update({
    "industry": "float glass manufacturing plant",
    "default_wind": {"from_deg": 270, "speed_mps": 2.0},
    "gases": ["Natural gas (CH4)", "Hydrogen (H2)", "LPG"],
})

LAYOUTS = {L["id"]: L for L in (FLOAT_GLASS_PLANT, GLASS_PROCESSING, PHARMA_API, HIGH_BAY_WAREHOUSE, AUTO_COMPONENTS)}

"""Glass processing unit (tempering, lamination, IGU).

Bottlenecks by design: one central corridor that almost everyone must use, a canteen with a
single door (crowded at shift break), a lamination clean room with a single door, and a
single-leaf fire door at the east end of the corridor.
"""

GLASS_PROCESSING = {
    "id": "processing",
    "name": "Glass Processing Unit - Tempering & Lamination (sample)",
    "industry": "glass processing unit (tempering, lamination, insulated glass)",
    "width": 76,
    "height": 44,
    "cell_m": 2.0,
    "default_wind": {"from_deg": 225, "speed_mps": 2.5},
    "gases": ["LPG", "Natural gas (CH4)"],
    "buildings": [{"id": "main", "rect": [4, 6, 71, 37]}],
    "zones": [
        {"id": "cutting", "short": "CUTTING & EDGING", "name": "Cutting & Edging", "rect": [4, 6, 25, 19], "fuel": 0.4,
         "roles": ["Cutting Operator", "Edging Operator", "Helper"]},
        {"id": "tempering", "short": "TEMPERING HALL", "name": "Tempering Furnace Hall", "rect": [25, 6, 47, 19], "fuel": 0.3,
         "roles": ["Furnace Operator", "Loader", "Shift Engineer"]},
        {"id": "igu", "short": "IGU LINE", "name": "Insulated Glass (IGU) Line", "rect": [47, 6, 61, 19], "fuel": 0.4,
         "roles": ["IGU Operator", "Sealant Technician"]},
        {"id": "lpgroom", "short": "LPG ROOM", "name": "LPG Vaporiser Room", "rect": [61, 6, 71, 19], "fuel": 0.3,
         "roles": ["Utility Operator"]},
        {"id": "corridor", "short": "CENTRAL CORRIDOR", "name": "Central Corridor", "rect": [4, 19, 71, 23], "fuel": 0.2,
         "roles": ["Helper"]},
        {"id": "cleanroom", "short": "LAMINATION", "name": "Lamination Clean Room (PVB)", "rect": [4, 23, 19, 37], "fuel": 0.7,
         "roles": ["Lamination Operator", "Clean Room Technician"]},
        {"id": "autoclave", "short": "AUTOCLAVE", "name": "Autoclave Bay", "rect": [19, 23, 31, 37], "fuel": 0.3,
         "roles": ["Autoclave Operator"]},
        {"id": "fgstore", "short": "FINISHED GOODS", "name": "Finished Goods Store", "rect": [31, 23, 52, 37], "fuel": 1.0,
         "roles": ["Forklift Operator", "Packer", "Dispatch Clerk"]},
        {"id": "canteen", "short": "CANTEEN", "name": "Canteen & Lockers", "rect": [52, 23, 63, 37], "fuel": 0.6,
         "roles": ["Operator (on break)", "Canteen Staff", "Contract Worker (on break)"]},
        {"id": "office", "short": "QC & OFFICE", "name": "QC & Office", "rect": [63, 23, 71, 37], "fuel": 0.6,
         "roles": ["QC Inspector", "Plant Manager", "Safety Officer", "Visitor"]},
        {"id": "lpgbank", "short": "LPG BULLETS", "name": "LPG Bullet Yard", "rect": [62, 39, 72, 43], "walled": False,
         "fuel": 0.2, "roles": ["Gas Station Operator"]},
    ],
    "doors": [
        [14, 19], [15, 19],                    # cutting -> corridor
        [30, 19], [31, 19], [42, 19], [43, 19],  # tempering -> corridor
        [54, 19], [55, 19],                    # IGU -> corridor
        [66, 19],                              # LPG room -> corridor (single)
        [12, 23],                              # clean room -> corridor (single door)
        [25, 23], [26, 23],                    # autoclave -> corridor
        [36, 23], [37, 23], [47, 23], [48, 23],  # FG store -> corridor
        [57, 23],                              # canteen -> corridor (single door, crowded at break)
        [67, 23], [68, 23],                    # office -> corridor
        [25, 12], [25, 13],                    # cutting <-> tempering (glass flow)
        [47, 12], [47, 13],                    # tempering <-> IGU
        [31, 30], [31, 31],                    # autoclave <-> FG store
    ],
    "exits": [
        {"id": "E1", "cells": [[4, 20], [4, 21], [4, 22]]},
        {"id": "E2", "cells": [[10, 6], [11, 6]]},
        {"id": "E3", "cells": [[71, 21]]},                   # single-leaf fire door
        {"id": "E4", "cells": [[x, 37] for x in range(38, 46)]},  # loading dock
        {"id": "E5", "cells": [[67, 37]]},
    ],
    "assembly_points": [
        {"id": "AP1", "name": "AP1 - Main Gate", "rect": [30, 0, 40, 3]},
        {"id": "AP2", "name": "AP2 - East Lawn", "rect": [73, 12, 75, 26]},
        {"id": "AP3", "name": "AP3 - South Parking", "rect": [8, 40, 22, 43]},
    ],
    "obstacles": [
        {"name": "Cutting table", "rect": [8, 10, 20, 14]},
        {"name": "Tempering furnace", "rect": [28, 10, 44, 14]},
        {"name": "IGU line", "rect": [49, 10, 59, 14]},
        {"name": "Vaporiser", "rect": [64, 9, 68, 13]},
        {"name": "Layup table", "rect": [7, 27, 16, 32]},
        {"name": "Autoclave", "rect": [21, 27, 28, 32]},
        {"name": "Rack", "rect": [33, 26, 41, 27]},
        {"name": "Rack", "rect": [44, 26, 50, 27]},
        {"name": "Rack", "rect": [33, 30, 41, 31]},
        {"name": "Rack", "rect": [44, 30, 50, 31]},
        {"name": "Tables", "rect": [54, 26, 61, 27]},
        {"name": "Tables", "rect": [54, 30, 61, 31]},
        {"name": "Desks", "rect": [65, 26, 69, 27]},
        {"name": "LPG bullets", "rect": [65, 40, 70, 42]},
    ],
    "sensors": [
        {"id": "GD-01", "type": "gas", "gas": "LPG", "pos": [27, 16]},
        {"id": "GD-02", "type": "gas", "gas": "LPG", "pos": [63, 15]},
        {"id": "GD-03", "type": "gas", "gas": "LPG", "pos": [64, 39]},
        {"id": "GD-04", "type": "gas", "gas": "LPG", "pos": [60, 21]},
        {"id": "FD-01", "type": "flame", "pos": [36, 8]},
        {"id": "FD-02", "type": "flame", "pos": [42, 35]},
        {"id": "FD-03", "type": "flame", "pos": [12, 34]},
        {"id": "FD-04", "type": "flame", "pos": [68, 39]},
        {"id": "FD-05", "type": "flame", "pos": [59, 35]},
        {"id": "SD-01", "type": "smoke", "pos": [15, 8]},
        {"id": "SD-02", "type": "smoke", "pos": [54, 8]},
        {"id": "SD-03", "type": "smoke", "pos": [20, 21]},
        {"id": "SD-04", "type": "smoke", "pos": [50, 21]},
        {"id": "SD-05", "type": "smoke", "pos": [57, 34]},
        {"id": "SD-06", "type": "smoke", "pos": [67, 34]},
        {"id": "SD-07", "type": "smoke", "pos": [25, 35]},
        {"id": "SD-08", "type": "smoke", "pos": [42, 24]},
    ],
    "staffing": {"cutting": 8, "tempering": 7, "igu": 6, "lpgroom": 1, "cleanroom": 6, "autoclave": 3,
                 "fgstore": 6, "canteen": 18, "office": 6},
    "scenarios": [
        {"id": "fgstore-fire", "name": "Finished goods store fire next to the corridor",
         "description": "Interleave paper and crates catch fire by the corridor doors; the canteen crowd must find another way out.",
         "wind": {"from_deg": 225, "speed_mps": 2.5},
         "events": [{"t": 3, "type": "fire", "pos": [42, 25]}]},
        {"id": "canteen-lunch-fire", "name": "Canteen kitchen fire during lunch break",
         "description": "LPG cooking fire in the canteen while it is full. Single door + corridor = queue.",
         "wind": {"from_deg": 270, "speed_mps": 2.0},
         "events": [{"t": 3, "type": "fire", "pos": [60, 35]}]},
        {"id": "tempering-lpg", "name": "LPG leak at tempering furnace burner -> ignition",
         "description": "Burner manifold leak in the tempering hall; the cloud ignites after ~80 s.",
         "wind": {"from_deg": 225, "speed_mps": 2.5},
         "events": [{"t": 3, "type": "leak", "pos": [33, 16], "rate": 260, "gas": "LPG"},
                    {"t": 80, "type": "fire", "pos": [33, 17]}]},
        {"id": "cleanroom-fire", "name": "Lamination clean room fire (single door)",
         "description": "PVB interlayer fire in the clean room; everyone inside has one 2 m door to get out.",
         "wind": {"from_deg": 270, "speed_mps": 2.0},
         "events": [{"t": 3, "type": "fire", "pos": [17, 34]}]},
        {"id": "lpg-bank-leak", "name": "LPG bullet yard leak, wind toward East Lawn",
         "description": "Outdoor LPG release drifting north-east onto the East Lawn assembly point.",
         "wind": {"from_deg": 200, "speed_mps": 3.5},
         "events": [{"t": 3, "type": "leak", "pos": [68, 43], "rate": 900, "gas": "LPG"}]},
    ],
}

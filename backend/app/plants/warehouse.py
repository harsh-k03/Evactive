"""High-bay distribution warehouse.

Bottlenecks by design: long single-cell rack aisles that dead-end at the west wall, a
fire wall between the two rack halls with only two openings, and most exits on the dock side.
"""


def _racks(y_rows):
    out = []
    for y in y_rows:
        out.append({"name": "Racks", "rect": [5, y, 26, y + 1]})
        out.append({"name": "Racks", "rect": [29, y, 50, y + 1]})
    return out


HIGH_BAY_WAREHOUSE = {
    "id": "warehouse",
    "name": "High-Bay Distribution Warehouse (sample)",
    "industry": "high-bay distribution warehouse with LPG forklifts",
    "width": 80,
    "height": 46,
    "cell_m": 2.0,
    "default_wind": {"from_deg": 270, "speed_mps": 2.5},
    "gases": ["LPG"],
    "buildings": [{"id": "warehouse", "rect": [4, 6, 75, 38]}],
    "zones": [
        {"id": "rackA", "short": "RACK HALL A", "name": "Rack Hall A", "rect": [4, 6, 58, 22], "fuel": 1.0,
         "roles": ["Picker", "Reach-truck Operator", "Inventory Clerk"]},
        {"id": "rackB", "short": "RACK HALL B", "name": "Rack Hall B", "rect": [4, 22, 58, 38], "fuel": 1.0,
         "roles": ["Picker", "Reach-truck Operator", "Inventory Clerk"]},
        {"id": "dock", "short": "DOCK & STAGING", "name": "Dock & Staging", "rect": [58, 6, 75, 30], "fuel": 0.6,
         "roles": ["Loader", "Dock Supervisor", "Truck Driver (visitor)", "Forklift Operator"]},
        {"id": "charging", "short": "LPG REFUEL", "name": "Forklift Charging / LPG Refuel", "rect": [58, 30, 66, 38],
         "fuel": 0.4, "roles": ["Forklift Technician"]},
        {"id": "office", "short": "OFFICE & CANTEEN", "name": "Office & Canteen", "rect": [66, 30, 75, 38],
         "fuel": 0.6, "roles": ["Warehouse Manager", "Billing Clerk", "Canteen Staff", "Visitor"]},
    ],
    "doors": [
        [27, 22], [28, 22], [53, 22], [54, 22],   # fire-wall openings between the rack halls
        [58, 10], [58, 11], [58, 16], [58, 17],   # rack hall A -> dock
        [58, 26], [58, 27],                       # rack hall B -> dock
        [58, 34],                                 # rack hall B -> charging
        [62, 30],                                 # dock -> charging
        [70, 30], [71, 30],                       # dock -> office
    ],
    "exits": [
        {"id": "E1", "cells": [[40, 6], [41, 6]]},
        {"id": "E2", "cells": [[4, 30], [4, 31]]},
        {"id": "E3", "cells": [[75, 10], [75, 11], [75, 12]]},   # dock shutter
        {"id": "E4", "cells": [[75, 16], [75, 17], [75, 18]]},   # dock shutter
        {"id": "E5", "cells": [[70, 38], [71, 38]]},
        {"id": "E6", "cells": [[30, 38], [31, 38]]},
    ],
    "assembly_points": [
        {"id": "AP1", "name": "AP1 - Main Gate", "rect": [34, 0, 46, 3]},
        {"id": "AP2", "name": "AP2 - Truck Yard", "rect": [77, 26, 79, 40]},
        {"id": "AP3", "name": "AP3 - South-West Ground", "rect": [6, 41, 18, 45]},
    ],
    "obstacles": _racks([8, 11, 14, 17]) + _racks([24, 27, 30, 33]) + [
        {"name": "Staging", "rect": [62, 9, 66, 11]},
        {"name": "Staging", "rect": [62, 14, 66, 16]},
        {"name": "Staging", "rect": [62, 19, 66, 21]},
        {"name": "Chargers", "rect": [60, 34, 62, 36]},
        {"name": "LPG cage", "rect": [64, 35, 65, 37]},
        {"name": "Tables", "rect": [68, 33, 73, 34]},
    ],
    "sensors": [
        {"id": "FD-01", "type": "flame", "pos": [27, 7]},
        {"id": "FD-02", "type": "flame", "pos": [52, 13]},
        {"id": "FD-03", "type": "flame", "pos": [27, 23]},
        {"id": "FD-04", "type": "flame", "pos": [52, 29]},
        {"id": "FD-05", "type": "flame", "pos": [70, 8]},
        {"id": "FD-06", "type": "flame", "pos": [15, 20]},
        {"id": "FD-07", "type": "flame", "pos": [40, 20]},
        {"id": "FD-08", "type": "flame", "pos": [15, 36]},
        {"id": "FD-09", "type": "flame", "pos": [40, 36]},
        {"id": "SD-01", "type": "smoke", "pos": [15, 10]},
        {"id": "SD-02", "type": "smoke", "pos": [40, 16]},
        {"id": "SD-03", "type": "smoke", "pos": [15, 26]},
        {"id": "SD-04", "type": "smoke", "pos": [40, 32]},
        {"id": "SD-05", "type": "smoke", "pos": [70, 25]},
        {"id": "SD-06", "type": "smoke", "pos": [72, 36]},
        {"id": "SD-07", "type": "smoke", "pos": [60, 32]},
        {"id": "GD-01", "type": "gas", "gas": "LPG", "pos": [63, 32]},
        {"id": "GD-02", "type": "gas", "gas": "LPG", "pos": [67, 28]},
    ],
    "staffing": {"rackA": 12, "rackB": 12, "dock": 14, "charging": 3, "office": 10},
    "scenarios": [
        {"id": "rack-fire-deep", "name": "Rack fire deep in Hall A (dead-end aisles)",
         "description": "Fire in a west-end aisle of Rack Hall A; pickers in dead-end aisles must pass the fire zone.",
         "wind": {"from_deg": 270, "speed_mps": 2.5},
         "events": [{"t": 3, "type": "fire", "pos": [12, 13]}]},
        {"id": "rack-fire-exit", "name": "Rack fire blocking the south exit",
         "description": "Fire by exit E6 in Rack Hall B; everyone in Hall B funnels through the fire-wall openings.",
         "wind": {"from_deg": 270, "speed_mps": 2.5},
         "events": [{"t": 3, "type": "fire", "pos": [31, 36]}]},
        {"id": "lpg-refuel-leak", "name": "LPG leak at forklift refuel point",
         "description": "Cylinder change-over leak in the charging bay next to the office and canteen.",
         "wind": {"from_deg": 270, "speed_mps": 2.0},
         "events": [{"t": 3, "type": "leak", "pos": [63, 36], "rate": 320, "gas": "LPG"}]},
        {"id": "dock-fire", "name": "Staging pallet fire at the dock",
         "description": "Shrink-wrapped pallets catch fire in the staging lanes; dock shutters E3/E4 threatened.",
         "wind": {"from_deg": 90, "speed_mps": 3.0},
         "events": [{"t": 3, "type": "fire", "pos": [67, 13]}]},
        {"id": "twin-fire", "name": "Two simultaneous rack fires",
         "description": "Fires in both rack halls at once; tests escalation and load-balancing across exits.",
         "wind": {"from_deg": 270, "speed_mps": 2.5},
         "events": [{"t": 3, "type": "fire", "pos": [20, 19]}, {"t": 20, "type": "fire", "pos": [45, 26]}]},
    ],
}

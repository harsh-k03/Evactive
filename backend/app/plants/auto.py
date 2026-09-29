"""Auto-components plant with two buildings.

Bottlenecks by design: the press shop and the paint/assembly building are linked only by a
narrow covered connector, the canteen (crowded at shift change) has a single external door,
and long assembly conveyors create a maze of aisles.
"""

AUTO_COMPONENTS = {
    "id": "auto",
    "name": "Auto Components Plant - Press, Weld, Paint & Assembly (sample)",
    "industry": "auto components manufacturing plant with a solvent-based paint shop",
    "width": 84,
    "height": 46,
    "cell_m": 2.0,
    "default_wind": {"from_deg": 270, "speed_mps": 2.5},
    "gases": ["Solvent vapour (Xylene)", "Natural gas (CH4)"],
    "buildings": [
        {"id": "bldgA", "rect": [4, 6, 38, 36]},
        {"id": "bldgB", "rect": [46, 6, 79, 36]},
        {"id": "connector", "rect": [38, 14, 46, 17]},
    ],
    "zones": [
        {"id": "press", "short": "PRESS SHOP", "name": "Press Shop", "rect": [4, 6, 38, 20], "fuel": 0.3,
         "roles": ["Press Operator", "Die Setter", "Helper"]},
        {"id": "weld", "short": "WELD SHOP", "name": "Weld Shop (Robotic)", "rect": [4, 20, 26, 36], "fuel": 0.4,
         "roles": ["Welder", "Robot Cell Operator"]},
        {"id": "tooling", "short": "TOOL ROOM", "name": "Tool Room & Stores", "rect": [26, 20, 38, 36], "fuel": 0.6,
         "roles": ["Toolmaker", "Stores Assistant"]},
        {"id": "connector", "short": "", "name": "Covered Connector", "rect": [38, 14, 46, 17], "fuel": 0.2,
         "roles": ["Helper"]},
        {"id": "paint", "short": "PAINT SHOP", "name": "Paint Shop (Solvent)", "rect": [46, 6, 62, 20], "fuel": 0.8,
         "roles": ["Painter", "Paint Shop Supervisor"]},
        {"id": "paintmix", "short": "PAINT MIX", "name": "Paint Mixing Room", "rect": [62, 6, 70, 20], "fuel": 0.9,
         "roles": ["Paint Mixer"]},
        {"id": "canteen", "short": "CANTEEN", "name": "Canteen", "rect": [70, 6, 79, 20], "fuel": 0.6,
         "roles": ["Operator (shift change)", "Canteen Staff", "Contract Worker (shift change)"]},
        {"id": "assembly", "short": "ASSEMBLY LINE", "name": "Assembly Line", "rect": [46, 20, 79, 36], "fuel": 0.5,
         "roles": ["Assembly Operator", "Line Leader", "Quality Inspector", "Visitor"]},
    ],
    "doors": [
        [12, 20], [13, 20], [32, 20], [33, 20],   # press -> weld / tooling
        [26, 28], [26, 29],                       # weld <-> tooling
        [38, 15], [38, 16], [46, 15], [46, 16],   # connector ends
        [52, 20], [53, 20],                       # paint -> assembly
        [62, 12],                                 # paint <-> paint mix (single)
        [66, 20],                                 # paint mix -> assembly (single)
        [74, 20], [75, 20],                       # canteen -> assembly
    ],
    "exits": [
        {"id": "E1", "cells": [[20, 6], [21, 6]]},
        {"id": "E2", "cells": [[4, 28], [4, 29]]},
        {"id": "E3", "cells": [[32, 36]]},
        {"id": "E4", "cells": [[79, 12]]},                      # canteen: single door
        {"id": "E5", "cells": [[60, 36], [61, 36], [62, 36]]},  # dispatch
        {"id": "E6", "cells": [[79, 28], [79, 29]]},
    ],
    "assembly_points": [
        {"id": "AP1", "name": "AP1 - Main Gate", "rect": [38, 0, 48, 3]},
        {"id": "AP2", "name": "AP2 - South Parking", "rect": [52, 40, 64, 45]},
        {"id": "AP3", "name": "AP3 - East Ground", "rect": [81, 18, 83, 34]},
    ],
    "obstacles": [
        {"name": "Press", "rect": [8, 9, 12, 13]}, {"name": "Press", "rect": [16, 9, 20, 13]},
        {"name": "Press", "rect": [24, 9, 28, 13]}, {"name": "Press", "rect": [8, 15, 12, 18]},
        {"name": "Press", "rect": [16, 15, 20, 18]}, {"name": "Press", "rect": [24, 15, 28, 18]},
        {"name": "Robot cell", "rect": [7, 23, 12, 26]}, {"name": "Robot cell", "rect": [15, 23, 20, 26]},
        {"name": "Robot cell", "rect": [7, 30, 12, 33]}, {"name": "Robot cell", "rect": [15, 30, 20, 33]},
        {"name": "Racks", "rect": [28, 23, 36, 24]}, {"name": "Racks", "rect": [28, 31, 36, 32]},
        {"name": "Paint booth 1", "rect": [49, 9, 59, 12]}, {"name": "Paint booth 2", "rect": [49, 15, 59, 17]},
        {"name": "Mixing tanks", "rect": [64, 9, 68, 13]},
        {"name": "Tables", "rect": [72, 9, 77, 10]}, {"name": "Tables", "rect": [72, 13, 77, 14]},
        {"name": "Conveyor 1", "rect": [49, 24, 76, 25]}, {"name": "Conveyor 2", "rect": [49, 29, 76, 30]},
    ],
    "sensors": [
        {"id": "GD-01", "type": "gas", "gas": "Solvent vapour (Xylene)", "pos": [48, 8]},
        {"id": "GD-02", "type": "gas", "gas": "Solvent vapour (Xylene)", "pos": [60, 18]},
        {"id": "GD-03", "type": "gas", "gas": "Solvent vapour (Xylene)", "pos": [63, 15]},
        {"id": "FD-01", "type": "flame", "pos": [54, 14]},
        {"id": "FD-02", "type": "flame", "pos": [69, 15]},
        {"id": "FD-03", "type": "flame", "pos": [13, 28]},
        {"id": "FD-04", "type": "flame", "pos": [32, 34]},
        {"id": "FD-05", "type": "flame", "pos": [62, 33]},
        {"id": "SD-01", "type": "smoke", "pos": [22, 8]},
        {"id": "SD-02", "type": "smoke", "pos": [33, 17]},
        {"id": "SD-03", "type": "smoke", "pos": [22, 34]},
        {"id": "SD-04", "type": "smoke", "pos": [55, 33]},
        {"id": "SD-05", "type": "smoke", "pos": [72, 22]},
        {"id": "SD-06", "type": "smoke", "pos": [74, 16]},
        {"id": "SD-07", "type": "smoke", "pos": [30, 21]},
        {"id": "SD-08", "type": "smoke", "pos": [42, 15]},
    ],
    "staffing": {"press": 10, "weld": 8, "tooling": 4, "paint": 6, "paintmix": 2, "assembly": 16, "canteen": 20},
    "scenarios": [
        {"id": "canteen-shift-fire", "name": "Canteen fire at shift change",
         "description": "Kitchen fire while the canteen is full; one external door, the rest must cross the assembly hall.",
         "wind": {"from_deg": 270, "speed_mps": 2.5},
         "events": [{"t": 3, "type": "fire", "pos": [77, 17]}]},
        {"id": "dispatch-fire", "name": "Assembly fire blocking the dispatch exit",
         "description": "Fire by the main dispatch doors; the assembly crowd reroutes through the conveyor maze.",
         "wind": {"from_deg": 270, "speed_mps": 2.5},
         "events": [{"t": 3, "type": "fire", "pos": [61, 33]}]},
        {"id": "paint-booth-fire", "name": "Paint booth fire",
         "description": "Solvent-laden paint booth fire; smoke spreads into assembly and the connector.",
         "wind": {"from_deg": 270, "speed_mps": 2.5},
         "events": [{"t": 3, "type": "fire", "pos": [54, 13]}]},
        {"id": "paintmix-leak", "name": "Solvent vapour leak in paint mixing room -> ignition",
         "description": "Xylene vapour from an open mixing tank; ignites after ~100 s.",
         "wind": {"from_deg": 270, "speed_mps": 2.0},
         "events": [{"t": 3, "type": "leak", "pos": [66, 17], "rate": 280, "gas": "Solvent vapour (Xylene)"},
                    {"t": 100, "type": "fire", "pos": [66, 16]}]},
        {"id": "weld-fire", "name": "Weld shop fire near the press shop door",
         "description": "Spatter fire in the weld shop close to the door into the press shop.",
         "wind": {"from_deg": 270, "speed_mps": 2.5},
         "events": [{"t": 3, "type": "fire", "pos": [13, 22]}]},
    ],
}

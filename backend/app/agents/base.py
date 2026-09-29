from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..engine import Engine

def system_base(engine) -> str:
    industry = engine.layout.get("industry", "manufacturing plant")
    return (f"You are part of Evactive, an AI emergency-management system for an Indian {industry}. "
            "Be factual, calm and brief. Use ONLY the facts provided; never invent numbers, names, "
            "locations or equipment. Use standard industrial safety terminology.")


class Agent:
    name = "Agent"

    def __init__(self, engine: "Engine"):
        self.e = engine

    @property
    def inc(self) -> dict:
        return self.e.incident

    def log(self, msg: str, level: str = "info", **kw):
        return self.e.log(self.name, msg, level, **kw)

    def zname(self, zid: str | None) -> str:
        if zid is None:
            return "open yard"
        return self.e.grid.zone_names.get(zid, zid)

    def step(self, t: int):  # pragma: no cover - interface
        raise NotImplementedError

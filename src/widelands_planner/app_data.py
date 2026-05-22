"""
streamlit doesnt work well with custom types in the app file itself
because of reloading they will not retain identity
so we define custom types here instead
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from widelands_planner.state import Allocated, BuildingCount, SolutionStatus


@dataclass(frozen=True)
class Solution:
    revision: int
    blocks: list[list[BuildingCount]]
    block_indices: dict[str, int]
    building_indices: dict[str, tuple[int, int]]
    allocated: list[list[Allocated]]
    status: SolutionStatus


@dataclass
class State:
    """all the state that is not tied to widgets"""

    revision: int
    """every state change does +1"""

    blocks: dict[str, str]
    """blocks[name] = uuid"""

    buildings: dict[str, list[str]]
    """buildings[block uuid] = list of building uuids"""

    solution: Solution | None

    @classmethod
    def from_new(cls):
        return cls(1, [], dict(), None)

    @classmethod
    def from_session(cls, data: Any):  # pyright: ignore[reportExplicitAny]
        match data:
            case {
                "revision": int(revision),
                "blocks": dict(blocks),  # pyright: ignore[reportUnknownVariableType]
                "buildings": dict(buildings),  # pyright: ignore[reportUnknownVariableType]
            }:
                return cls(
                    revision=revision,
                    # TODO better to use msgspec or so, to validate
                    blocks=blocks,  # pyright: ignore[reportUnknownArgumentType]
                    buildings=buildings,  # pyright: ignore[reportUnknownArgumentType]
                    solution=None,
                )
            case _:
                assert False, data

    def as_session(self) -> dict[str, int | dict[str, str] | dict[str, list[str]]]:
        return {
            "revision": self.revision,
            "blocks": self.blocks,
            "buildings": self.buildings,
        }

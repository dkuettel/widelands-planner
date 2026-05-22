"""
streamlit doesnt work well with custom types in the app file itself
because of reloading they will not retain identity
so we define custom types here instead
"""

from __future__ import annotations

from dataclasses import dataclass

from widelands_planner.state import Allocated, BuildingCount, SolutionStatus


@dataclass(frozen=True)
class Solution:
    revision: int
    blocks: list[list[BuildingCount]]
    block_indices: dict[str, int]
    building_indices: dict[str, tuple[int, int]]
    allocated: list[list[Allocated]]
    status: SolutionStatus

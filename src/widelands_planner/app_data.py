"""
streamlit doesnt work well with custom types in the app file itself
because of reloading they will not retain identity
so we define custom types here instead
"""

from __future__ import annotations

from dataclasses import dataclass

from widelands_planner.state import (
    Allocated,
    BuildingCount,
    ResumeState,
    SolutionStatus,
)


@dataclass(frozen=True)
class Solution:
    revision: int
    blocks: list[list[BuildingCount]]
    block_indices: dict[str, int]
    building_indices: dict[str, tuple[int, int]]
    allocated: list[list[Allocated]]
    status: SolutionStatus
    resume: ResumeState | None

    @classmethod
    def from_empty(cls):
        return cls(
            revision=0,
            blocks=[],
            block_indices=dict(),
            building_indices=dict(),
            allocated=[],
            status=SolutionStatus(True, 0, 0),
            resume=None,
        )

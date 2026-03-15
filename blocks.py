from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from itertools import chain

import streamlit as st
from streamlit.delta_generator import DeltaGenerator

st.write(datetime.now())


@dataclass(frozen=True)
class Building:
    name: str
    needs: dict[str, float]


@dataclass(frozen=True)
class Block:
    name: str
    # TODO or we list it in needs instead? not sure that is 1:1 always
    exports: dict[str, int]
    buildings: dict[str, int]
    # NOTE same name as for buildings, so we can just handle it uniformly?
    needs: dict[str, int]


def get_buildings() -> dict[str, Building]:
    buildings = [
        Building("forester", {}),
        Building("woodcutter", {"forester": 0.5}),
        # "tavern (fish, fruit)": {
        #     "smokery": 27 / (2 * 37),
        #     "fruit": ((37 + 62) / 2) / (2 * 37),
        # },
        # "tavern (fish, bread)": {
        #     "smokery": 27 / (2 * 37),
        #     "bakery": 44 / (2 * 37),
        # },
        Building("tavern", {}),
        # "coal": {"tavern (fish, fruit)": 37 / (2 * 41)},
        Building("coal", {}),
        # "iron": {"tavern (fish, fruit)": 37 / 69},
        Building("iron", {}),
        # "granite": {"tavern (fish, fruit)": 37 / (2 * 46)},
        Building("granite", {}),
        Building("clay pit", {"water": 0.7}),
        Building("brick kiln", {"clay pit": 2.1, "coal": 0.5, "granite": 0.5}),
        Building(
            "bakery",
            {
                "farm": ((49 + 67) / 2) / 44,
                "water": 44 / 44,
            },
        ),
        Building(
            "smokery",
            {
                "fishery": ((26 + 59) / 2) / (27),
                "woodcutter": ((49 + 89) / 2) / (2 * 27),
            },
        ),
        Building("farm", {}),
        Building("water", {}),
    ]
    buildings = {b.name: b for b in buildings}
    return buildings


def get_blocks() -> dict[str, Block]:
    blocks = [
        Block("wood block", {"forester": 1}, {"forester": 1, "woodcutter": 1}, {}),
        Block(
            "bread block",
            {"tavern": 1},
            {
                "tavern": 1,
                "bakery": 2,
                "farm": 3,
                "water": 2,
            },
            {},
        ),
    ]
    blocks = {block.name: block for block in blocks}
    return blocks


def st_building(building: Building) -> DeltaGenerator:
    with st.container(border=True, width=200):
        # st.session_state.setdefault(name, 0)
        # flag = "" if st.session_state[name] >= 0 else " :warning:"
        flag = ""
        st.number_input(f"{building.name}{flag}", min_value=0, key=building.name)
        return st.empty()


def st_block(block: Block) -> DeltaGenerator:
    st.session_state.setdefault(block.name, 0)
    avail = (
        min(
            [
                st.session_state.get(name, 0) // count
                for name, count in block.buildings.items()
            ]
        )
        - st.session_state[block.name]
    )
    elements = " - ".join(f"{count} {name}" for name, count in block.buildings.items())
    with st.container(border=True):
        st.number_input(
            f"**({avail:+}) {block.name}**: {elements}",
            min_value=0,
            key=block.name,
        )
        return st.empty()


def get_block_totals(
    buildings: dict[str, Building], blocks: dict[str, Block]
) -> dict[str, int]:
    block_totals = {name: 0 for name in buildings}
    for block in blocks.values():
        for name, ratio in block.buildings.items():
            block_totals[name] += st.session_state.get(block.name, 0) * ratio
    return block_totals


def get_direct_needs(buildings: dict[str, Building]) -> dict[str, float]:
    needs: dict[str, float] = dict()
    for building in buildings.values():
        for name, count in building.needs.items():
            needs[name] = (
                needs.get(name, 0) + st.session_state.get(building.name, 0) * count
            )
    return needs


def main():
    buildings: dict[str, Building] = get_buildings()
    blocks: dict[str, Block] = get_blocks()

    building_infos: dict[str, DeltaGenerator] = dict()
    block_infos: dict[str, DeltaGenerator] = dict()

    with st.container(border=False):
        st.title("state")

        st.header("buildings")
        with st.container(horizontal=True, border=False):
            for _, building in sorted(buildings.items()):
                building_infos[building.name] = st_building(building)

        st.header("blocks")
        with st.container(border=False):
            for _name, block in sorted(blocks.items()):
                block_infos[block.name] = st_block(block)

    direct_needs: dict[str, float] = get_direct_needs(buildings)
    block_totals: dict[str, int] = get_block_totals(buildings, blocks)

    for name, g in building_infos.items():
        have = st.session_state.get(name, 0)
        direct_need = direct_needs.get(name, 0)
        block_need = block_totals.get(name, 0)
        flag = ""
        if have == 0:
            usage = "+++"
        else:
            usage = round(100 * direct_need / have)
            if usage > 100:
                flag = ":warning:"
        with g.container(gap=None):
            st.write(f"usage {usage}% or {have}{direct_need - have:+.1f} {flag}")
            if have >= block_need:
                st.write(f"{block_need} for blocks")
            else:
                st.write(f"{have}+{block_need - have} for blocks :warning:")

    # TODO make a summary with clickable "dones"?


if __name__ == "__main__":
    main()

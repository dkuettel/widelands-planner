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


def main():
    buildings = get_buildings()
    blocks = get_blocks()

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

    block_totals = {name: 0 for name in buildings}
    for block in blocks.values():
        for name, ratio in block.buildings.items():
            block_totals[name] += st.session_state.get(block.name, 0) * ratio

    for name, count in block_totals.items():
        have = st.session_state.get(name, 0)
        if count <= have:
            building_infos[name].write(f"{count} for blocks")
        else:
            building_infos[name].write(f"{have}+{count - have} for blocks :warning:")

    # TODO actually compute total direct needs and make diff
    # time to make main() and funcs, and maybe push pyright on a bit more again
    for thing in chain(buildings.values(), blocks.values()):
        # TODO how to handle options? we only go one step, no recursion, so we just list all of then
        # and once one is instantiated, the others disappear?
        for name, count in thing.needs.items():
            diff = st.session_state.get(thing.name, 0) * count - st.session_state.get(
                name, 0
            )
            if diff > 0:
                st.write(f"{thing.name} needs {diff} more {name}")

    # with st.container(border=False):
    #     st.title("totals")
    #     totals = {name: st.session_state.get(name, 0) for name in buildings}
    #     for block, counts in blocks.items():
    #         for name, ratio in counts.items():
    #             totals[name] += st.session_state.get(f"block {block}", 0) * ratio
    #     # st.json(totals)
    #     with st.container(horizontal=True):
    #         for name, count in sorted(totals.items()):
    #             st.write(count, name)
    #             building_infos[name].write(f"usage 80% = {count * 0.8:.1f}/{round(count)}")

    # st.write(st.session_state)


if __name__ == "__main__":
    main()

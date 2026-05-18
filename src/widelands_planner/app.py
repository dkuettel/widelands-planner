from __future__ import annotations

import math
import os
from functools import partial
from typing import Final
from uuid import uuid4

import pandas as pd  # pyright: ignore[reportMissingTypeStubs]
import streamlit as st

from widelands_planner.state import (
    Allocated,
    Bname,
    BuildingCount,
    ConfiguredGenericBuilding,
    Item,
    Ivec,
    building_from_name,
    isum,
    solve,
    summarize_ivec,
)

hcontainer = partial(st.container, horizontal=True)


def run():
    os.execvp(
        "streamlit",
        [
            "streamlit",
            "run",
            # NOTE runOnSave we dont want when deployed
            "--server.runOnSave",
            "True",
            # NOTE must be absolute, but by default it already watches the current folder
            # "--server.folderWatchList",
            # "/path/to/src",
            "src/widelands_planner/app.py",
        ],
    )


def st_ivec(ivec: Ivec):
    df = pd.DataFrame(
        [
            {
                "i/min": 60 * ips,
                "item": name,
            }
            for (name, ips) in sorted(summarize_ivec(ivec).items())
        ]
    )

    # TODO polars is better, but styling doesnt work with st.table
    # but we could just use polars to inject html? more control
    # it just needs some work to fit into the streamlit visual design
    st.table(  # pyright: ignore[reportUnknownMemberType]
        df.style.format(  # pyright: ignore[reportUnknownMemberType]
            {
                "i/min": "{:.1f}",
            }
        ),
        border="horizontal",
    )


def st_select_block():
    block_entries = state_get_block_entries()

    with hcontainer(vertical_alignment="bottom"):
        block_name = st.selectbox(
            "select or create block",
            sorted(block_entries),
            accept_new_options=True,
            key=key_block_name,
            width=300,
        )

        def remove_block():
            block_entries = state_get_block_entries()
            block_entries.pop(block_name or "", "")
            state_set_block_entries(block_entries)
            [new_block_name, *_] = sorted(block_entries) or [None]
            state_set_block_name(new_block_name)

        st.button(
            "remove block",
            key="remove block",
            disabled=block_name is None,
            on_click=remove_block,
        )

    if block_name is None:
        return

    if block_name not in block_entries:
        block_entries[block_name] = uuid4().hex
        state_set_block_entries(block_entries)
        st.rerun()


def keep_state[T](key: str, default: T) -> T:
    # NOTE just reading doesnt make it persist, you have to set it too
    value = st.session_state.get(key, default)
    st.session_state[key] = value
    return value


def state_get_block_entries() -> dict[str, str]:
    """maps a block name to a block uuid"""
    return st.session_state.get("block_entries", dict())


def state_set_block_entries(value: dict[str, str]):
    st.session_state["block_entries"] = value


key_block_name: Final = "block_name"


def state_get_block_name() -> str | None:
    return st.session_state.get(key_block_name, None)


def state_set_block_name(value: str | None):
    """current block uuid to show"""
    st.session_state[key_block_name] = value


def state_get_building_entries(block_uuid: str) -> list[str]:
    return st.session_state.get(f"building_entries[{block_uuid}]", [])


def state_set_building_entries(uuid: str, value: list[str]):
    st.session_state[f"building_entries[{uuid}]"] = value


def state_get_building_name(uuid: str) -> None | Bname:
    value = st.session_state.get(f"building[{uuid}].name", None)
    match value:
        case None:
            return None
        case str():
            if value in Bname:
                return Bname(value)
            return None
        case _:
            return None


def state_set_building_name(uuid: str, value: None | Bname):
    match value:
        case None:
            st.session_state[f"building[{uuid}].name"] = None
        case Bname():
            st.session_state[f"building[{uuid}].name"] = value.value


def state_get_building_count(uuid: str) -> int:
    value = st.session_state.get(f"building[{uuid}].count", 0)
    match value:
        case int():
            return value
        case _:
            return 0


def state_set_building_count(uuid: str, value: int):
    st.session_state[f"building[{uuid}].count"] = value


def state_get_building_takes(uuid: str, name: Bname) -> list[Item]:
    value = st.session_state.get(f"building[{uuid}].settings.{name}.takes", None)
    match value:
        case list():
            value = list(map(str, value))  # pyright: ignore[reportUnknownArgumentType]
            if all((i in Item) for i in value):
                return sorted(Item(i) for i in value)
            building = building_from_name(name)
            return sorted(building.get_take_items())
        case None | _:
            building = building_from_name(name)
            return sorted(building.get_take_items())


def state_set_building_takes(uuid: str, name: Bname, value: list[Item]):
    st.session_state[f"building[{uuid}].settings.{name}.takes"] = [
        i.value for i in value
    ]


def ensure_state():
    # NOTE just reading doesnt make state persist, you have to set it too

    block_entries = state_get_block_entries()

    if len(block_entries) == 0:
        block_entries = {"main": uuid4().hex}
        state_set_block_name("main")

    state_set_block_entries(block_entries)

    for block_uuid in block_entries.values():
        building_entries = state_get_building_entries(block_uuid)
        state_set_building_entries(block_uuid, building_entries)

        for building_uuid in building_entries:
            name = state_get_building_name(building_uuid)
            state_set_building_name(building_uuid, name)

            count = state_get_building_count(building_uuid)
            state_set_building_count(building_uuid, count)

            if name is not None:
                takes = state_get_building_takes(building_uuid, name)
                state_set_building_takes(building_uuid, name, takes)


def st_block(
    blocks: list[list[BuildingCount]],
    block_indices: dict[str, int],
    building_indices: dict[str, tuple[int, int]],
    allocated: list[list[Allocated]],
):
    block_name = state_get_block_name()
    if block_name is None:
        st.warning("No block selected.")
        return

    block_uuid = state_get_block_entries()[block_name]

    meta, buildings = st.columns([1, 4], gap="medium")

    with meta:
        i = block_indices[block_uuid]
        with st.expander("imports", expanded=True):
            st_ivec(
                isum(alloc.take_remote for alloc in allocated[i]),
            )
        with st.expander("local", expanded=True):
            st_ivec(
                isum(alloc.make_local() for alloc in allocated[i]),
            )
        with st.expander("exports", expanded=True):
            st_ivec(
                isum(alloc.make_remote() for alloc in allocated[i]),
            )

    with buildings:
        st_block_buildings(
            block_uuid, blocks, block_indices, building_indices, allocated
        )


def st_block_buildings(
    block_uuid: str,
    blocks: list[list[BuildingCount]],
    block_indices: dict[str, int],
    building_indices: dict[str, tuple[int, int]],
    allocated: list[list[Allocated]],
):
    building_entries = state_get_building_entries(block_uuid)

    with st.container(gap="xxsmall"):
        for building_uuid in building_entries:
            with hcontainer(vertical_alignment="center", border=False):
                st.number_input(
                    "count",
                    key=f"building[{building_uuid}].count",
                    min_value=0,
                    label_visibility="collapsed",
                    width=150,
                )

                with st.container(width=140, horizontal=True):
                    match building_indices.get(building_uuid, None):
                        case None:
                            pass
                        case (int(i), int(j)):
                            building = blocks[i][j]
                            alloc = allocated[i][j]
                            if building.count == 0:
                                st.markdown(":material/warning:")
                            elif (
                                math.ceil(building.count * alloc.stable_usage)
                                < building.count
                            ):
                                st.markdown(":material/remove:")
                            elif alloc.is_infinite:
                                st.markdown(":material/all_inclusive:")
                            elif alloc.stable_usage < 1.0:
                                st.markdown(":material/check:")
                            else:
                                st.markdown(":material/add:")
                            st.markdown(
                                f"**{round(alloc.stable_usage * 100)}%**",
                                width=40,
                                text_alignment="right",
                            )
                            st.markdown(
                                f":small[+{round((alloc.flood_usage - alloc.stable_usage) * 100)}%]",
                                width=40,
                                text_alignment="right",
                            )

                name = st.selectbox(
                    "name",
                    sorted(i.value for i in Bname),
                    index=None,
                    key=f"building[{building_uuid}].name",
                    label_visibility="collapsed",
                    width=250,
                )
                bname = None if name is None else Bname(name)
                building = None if bname is None else building_from_name(bname)

                # TODO lazy eval for speed?
                with st.popover(
                    ":material/settings:",
                    key=f"building[{building_uuid}].settings",
                    disabled=bname is None,
                ):
                    if bname is not None and building is not None:
                        items = sorted(i.value for i in building.get_take_items())
                        st.pills(
                            "takes",
                            items,
                            selection_mode="multi",
                            default=items,
                            key=f"building[{building_uuid}].settings.{bname}.takes",
                        )

                if st.button(
                    ":material/delete:", key=f"remove building[{building_uuid}]"
                ):
                    building_entries.remove(building_uuid)
                    st.session_state[f"building_entries[{block_uuid}]"] = (
                        building_entries
                    )
                    st.rerun()

                if bname is not None and building is not None:
                    items = st.session_state.get(
                        f"building[{building_uuid}].settings.{bname}.takes", []
                    )
                    st.code(
                        " + ".join(items)
                        + " -> "
                        # TODO should do it after the fact, because we dont produce all, depends on what we take
                        + " + ".join(i.value for i in building.get_make_items()),
                        language=None,
                    )

        with st.container(horizontal=True):
            if st.button("add building", key="add building"):
                building_entries.append(uuid4().hex)
                st.session_state[f"building_entries[{block_uuid}]"] = building_entries
                st.rerun()

            i = block_indices[block_uuid]
            block = blocks[i]
            all_take = {item for building in block for item in building.building.takes}
            all_make = {item for building in block for item in building.building.makes}
            missing_items = all_take - all_make
            for bname in Bname:
                building = building_from_name(bname)
                if missing_items & building.get_make_items():
                    if st.button(
                        f":material/add: {bname.value}",
                        key=f"add building {bname}",
                        type="tertiary",
                    ):
                        building_entries = st.session_state.get(
                            f"building_entries[{block_uuid}]", []
                        )
                        uuid = uuid4().hex
                        building_entries.append(uuid)
                        st.session_state[f"building_entries[{block_uuid}]"] = (
                            building_entries
                        )
                        st.session_state[f"building[{uuid}].name"] = bname.value
                        st.session_state[f"building[{uuid}].count"] = 1
                        st.rerun()


def get_blocks() -> tuple[
    list[list[BuildingCount]], dict[str, int], dict[str, tuple[int, int]]
]:
    def count(uuid: str) -> BuildingCount | None:
        name = state_get_building_name(uuid)
        if name is None:
            return None
        count = state_get_building_count(uuid)
        takes = state_get_building_takes(uuid, name)
        building = building_from_name(name)
        return BuildingCount(
            count,
            ConfiguredGenericBuilding(
                building,
                set(takes),
                building.get_make_items(),
                1.0,
            ),
        )

    blocks = {
        block_uuid: {
            building_uuid: count(building_uuid)
            for building_uuid in state_get_building_entries(block_uuid)
        }
        for block_uuid in state_get_block_entries().values()
    }

    blocks = {
        block_uuid: {
            uuid: building for uuid, building in block.items() if building is not None
        }
        for block_uuid, block in blocks.items()
    }

    block_indices = {uuid: i for i, uuid in enumerate(blocks)}

    building_indices = {
        uuid: (i, j)
        for i, block in enumerate(blocks.values())
        for j, uuid in enumerate(block)
    }

    blocks = [list(block.values()) for block in blocks.values()]

    return blocks, block_indices, building_indices


def main():
    st.set_page_config(
        page_icon=":material/table:",
        page_title="widelands planner",
        layout="wide",
    )

    ensure_state()

    blocks, block_indices, building_indices = get_blocks()
    allocated, status = solve(blocks)

    with st.container(border=False, gap="xxsmall"):
        st_select_block()
        st.divider()
        st_block(blocks, block_indices, building_indices, allocated)

    with st.sidebar:
        st.subheader("total exports")
        st_ivec(
            isum(alloc.make_remote() for block in allocated for alloc in block),
        )
        st.divider()
        st.markdown(f":small[{status}]")


# TODO problems
# ordering of buildings, finding them, and not duplicating for those where it doesnt make sense?
# adding tab, or renaming, resets to viewing the first tab
# adding a building doesnt fokus on the name selection, but maybe there are buttons for adding the right one in the first place?
# save all the time, keep a timeline? save version to load old stuff?
# order buildings, by feed-into-order?
# when gaming out a new addition, would be nice to see the diff until "confirmed", or todo add click checkboxes
#    (almost like a new block, and then merge it in when done)
#    and/or a way for the blocks to be repeated, this is how you play it usually
# TODO when buildings are there but with 0 count, then the add/remove/inf indicators are off

if __name__ == "__main__":
    # NOTE this would be better, but streamlit's magic fails to do reloads correctly then
    # from widelands_planner.app import main

    main()

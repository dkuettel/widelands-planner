from __future__ import annotations

import math
import os
from functools import partial
from uuid import uuid4

import pandas as pd  # pyright: ignore[reportMissingTypeStubs]
import streamlit as st
from streamlit.delta_generator import DeltaGenerator

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


def st_select_block() -> None | str:
    block_entries: dict[str, str] = st.session_state.get("block_entries", dict())

    if len(block_entries) == 0:
        block_entries = {"main": uuid4().hex}
        st.session_state["block_entries"] = block_entries
        st.session_state["block_name"] = "main"
        st.rerun()

    with hcontainer(vertical_alignment="bottom"):
        block_name = st.selectbox(
            "select or create block",
            sorted(block_entries),
            index=0,
            accept_new_options=True,
            key="block_name",
            width=300,
        )

        def remove_block():
            block_entries.pop(block_name or "", "")
            st.session_state["block_entries"] = block_entries
            [st.session_state["block_name"], *_] = sorted(block_entries) or [None]

        st.button(
            "remove block",
            key="remove block",
            disabled=block_name is None,
            on_click=remove_block,
        )

    if block_name is None:
        return None

    if block_name not in block_entries:
        block_entries[block_name] = uuid4().hex
        st.session_state["block_entries"] = block_entries
        st.rerun()

    return block_entries[block_name]


def keep_state_alive():
    # NOTE just reading doesnt make it persist, you have to set it too
    block_entries: dict[str, str] = st.session_state.get("block_entries", dict())
    for block_uuid in block_entries.values():
        building_entries: list[str] = st.session_state.get(
            f"building_entries[{block_uuid}]", []
        )
        for building_uuid in building_entries:
            name = st.session_state.get(f"building[{building_uuid}].name", None)
            st.session_state[f"building[{building_uuid}].name"] = name
            st.session_state[f"building[{building_uuid}].count"] = st.session_state.get(
                f"building[{building_uuid}].count", 0
            )
            if name is not None:
                bname = Bname(name)
                st.session_state[
                    f"building[{building_uuid}].settings.{bname}.takes"
                ] = st.session_state.get(
                    # TODO or nothing if None?
                    f"building[{building_uuid}].settings.{bname}.takes",
                    None,
                )


def st_block(
    block_uuid: str | None,
) -> tuple[
    DeltaGenerator | None, str | None, dict[str, DeltaGenerator], DeltaGenerator | None
]:
    if block_uuid is None:
        st.warning("No block selected")
        return None, None, dict(), None

    meta, buildings = st.columns([1, 4], gap="medium")

    meta = meta.empty()

    with buildings:
        st_metrics, st_add_buildings = st_block_buildings(block_uuid)

    return meta, block_uuid, st_metrics, st_add_buildings


def st_block_buildings(
    block_uuid: str,
) -> tuple[dict[str, DeltaGenerator], DeltaGenerator]:
    building_entries: list[str] = st.session_state.get(
        f"building_entries[{block_uuid}]", []
    )

    st_metrics: dict[str, DeltaGenerator] = dict()

    with st.container(gap="small"):
        for building_uuid in building_entries:
            with hcontainer(vertical_alignment="center", border=True):
                st.number_input(
                    "count",
                    key=f"building[{building_uuid}].count",
                    min_value=0,
                    label_visibility="collapsed",
                    width=150,
                )

                st_metrics[building_uuid] = st.empty()

                name = st.selectbox(
                    "name",
                    sorted(i.value for i in Bname),
                    index=None,
                    key=f"building[{building_uuid}].name",
                    label_visibility="collapsed",
                    width=250,
                )
                bname = None if name is None else Bname(name)

                # TODO lazy eval for speed?
                with st.popover(
                    ":material/settings:",
                    key=f"building[{building_uuid}].settings",
                    disabled=bname is None,
                ):
                    if bname is not None:
                        building = building_from_name(bname)
                        items = sorted(i.value for i in building.get_take_items())
                        st.pills(
                            "takes",
                            items,
                            default=items,
                            selection_mode="multi",
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

        with st.container(horizontal=True):
            if st.button("add building", key="add building"):
                building_entries.append(uuid4().hex)
                st.session_state[f"building_entries[{block_uuid}]"] = building_entries
                st.rerun()

            st_add_buildings = st.empty()

    return st_metrics, st_add_buildings


def get_blocks() -> tuple[
    list[list[BuildingCount]], dict[str, int], dict[str, tuple[int, int]]
]:
    def count(building_uuid: str) -> BuildingCount | None:
        match st.session_state.get(f"building[{building_uuid}].name", None):
            case str(name):
                bname = Bname(name)
            case _:
                return None
        match st.session_state.get(f"building[{building_uuid}].count", None):
            case int(count):
                pass
            case _:
                return None
        match st.session_state.get(
            f"building[{building_uuid}].settings.{bname}.takes", None
        ):
            case list() as takes:  # pyright: ignore[reportUnknownVariableType]
                items: set[Item] = {Item(i) for i in takes}  # pyright: ignore[reportUnknownVariableType]
            case _:
                return None
        building = building_from_name(bname)
        return BuildingCount(
            count,
            ConfiguredGenericBuilding(
                building,
                items,
                building.get_make_items(),
                1.0,
            ),
        )

    blocks = {
        block_uuid: {
            building_uuid: count(building_uuid)
            for building_uuid in st.session_state.get(
                f"building_entries[{block_uuid}]", []
            )
        }
        # TODO i guess make functions that are typed for these accessors, and getset for keep alive?
        for block_uuid in st.session_state.get("block_entries", dict()).values()
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


def st_backfill_solution(
    st_meta: DeltaGenerator | None,
    block_uuid: str | None,
    st_metrics: dict[str, DeltaGenerator],
    st_add_buildings: DeltaGenerator | None,
    blocks: list[list[BuildingCount]],
    block_indices: dict[str, int],
    building_indices: dict[str, tuple[int, int]],
    allocated: list[list[Allocated]],
):
    if st_meta is not None and block_uuid in block_indices:
        i = block_indices[block_uuid]
        with st_meta.container():
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

    for uuid, dg in st_metrics.items():
        i, j = building_indices[uuid]
        alloc = allocated[i][j]
        building = blocks[i][j]
        with dg.container(horizontal=True, width="content"):
            if math.ceil(building.count * alloc.stable_usage) < building.count:
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

    if st_add_buildings is not None and block_uuid is not None:
        with st_add_buildings.container(horizontal=True):
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


def main():
    st.set_page_config(
        page_icon=":material/table:",
        page_title="widelands planner",
        layout="wide",
    )

    keep_state_alive()

    with st.container(border=False):
        block_uuid = st_select_block()
        st.divider()
        st_meta, block_uuid, st_metrics, st_add_buildings = st_block(block_uuid)

    blocks, block_indices, building_indices = get_blocks()
    allocated, status = solve(blocks)

    st.markdown(f":small[{status}]")

    st_backfill_solution(
        st_meta,
        block_uuid,
        st_metrics,
        st_add_buildings,
        blocks,
        block_indices,
        building_indices,
        allocated,
    )


if __name__ == "__main__":
    # NOTE this would be better, but streamlit's magic fails to do reloads correctly then
    # from widelands_planner.app import main

    main()

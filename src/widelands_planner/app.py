from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import partial
from typing import override
from uuid import uuid4

import streamlit as st
from streamlit.delta_generator import DeltaGenerator

from widelands_planner.state import (
    Bname,
    BuildingCount,
    ConfiguredBuilding,
    ConfiguredGenericBuilding,
    building_from_name,
    solve,
    solver_update_state,
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
            # TODO must be absolute, but by default it already watches the current folder
            # "--server.folderWatchList",
            # "/path/to/src",
            "src/widelands_planner/app.py",
        ],
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
        st.rerun()  # TODO will that evict later keys?

    return block_entries[block_name]


def main():
    st.set_page_config(
        page_icon=":material/table:",
        page_title="widelands planner",
        # layout="wide",
    )

    with st.container(border=True):
        block_uuid = st_select_block()

        st.divider()

        if block_uuid is None:
            st.warning("No block selected")
            return

        building_entries: list[str] = st.session_state.get(
            f"building_entries[{block_uuid}]", []
        )

        st_metrics: dict[tuple[str, str], DeltaGenerator] = dict()

        for building_uuid in building_entries:
            with hcontainer(vertical_alignment="center"):
                with st.container():
                    _building_name = st.selectbox(
                        "name",
                        sorted(i.value for i in Bname),
                        index=None,
                        key=f"building[{building_uuid}].name",
                        label_visibility="collapsed",
                    )
                    st.number_input(
                        "count",
                        key=f"building[{building_uuid}].count",
                        min_value=0,
                        label_visibility="collapsed",
                    )
                st_metrics[block_uuid, building_uuid] = st.empty()
                if st.button(
                    "remove building", key=f"remove building[{building_uuid}]"
                ):
                    building_entries.remove(building_uuid)
                    st.session_state[f"building_entries[{block_uuid}]"] = (
                        building_entries
                    )
                    st.rerun()

            st.divider()

        if st.button("add building", key="add building"):
            building_entries.append(uuid4().hex)
            st.session_state[f"building_entries[{block_uuid}]"] = building_entries
            st.rerun()

    blocks: list[list[BuildingCount]] = []
    block_entries: dict[str, str] = st.session_state.get("block_entries", dict())

    indices: list[tuple[int, int, str, str]] = []

    for i, block_uuid in enumerate(block_entries.values()):
        blocks.append([])
        for j, building_uuid in enumerate(building_entries):
            match st.session_state.get(f"building[{building_uuid}].name", None):
                case str(name):
                    bname = Bname(name)
                case _:
                    continue
            match st.session_state.get(f"building[{building_uuid}].count", None):
                case int(count):
                    pass
                case _:
                    continue
            building = building_from_name(bname)
            blocks[-1].append(
                BuildingCount(
                    count,
                    ConfiguredGenericBuilding(
                        building,
                        building.get_take_items(),
                        building.get_make_items(),
                        1.0,
                    ),
                )
            )
            if (block_uuid, building_uuid) in st_metrics:
                indices.append((i, j, block_uuid, building_uuid))

    allocated, status = solve(blocks)

    st.markdown(f":small[{status}]")

    for i, j, block_uuid, building_uuid in indices:
        alloc = allocated[i][j]
        st_metrics[block_uuid, building_uuid].metric(
            "usage",
            alloc.stable_usage,
            alloc.flood_usage - alloc.stable_usage,
            format="percent",
            delta_color="off",
            delta_arrow="auto",
            delta_description="potential",
        )


if __name__ == "__main__":
    # NOTE this would be better, but st magic doesnt do reloads correctly then
    # from widelands_planner.app import main

    main()

from __future__ import annotations

from datetime import datetime

import streamlit as st
from streamlit.delta_generator import DeltaGenerator

from widelands_planner import state


def st_building_count(
    block: str, building: state.Building
) -> tuple[state.BuildingCount, DeltaGenerator]:
    with st.container(border=True, width=200):
        name = building.name
        st.write(f"**{name}**")
        match building:
            case state.TavernBuilding():
                count = st.number_input(
                    "count",
                    min_value=0,
                    value=0,
                    key=f"state/{block}/{name}/count",
                    label_visibility="collapsed",
                )
                info = st.empty()
                fruit_vs_bread = 1 - st.slider(
                    label="<- fruit vs bread ->",
                    min_value=0.0,
                    value=0.5,
                    max_value=1.0,
                    step=0.01,
                    key=f"state/{block}/{name}/fruit_vs_bread",
                )
                fish_vs_meat = 1 - st.slider(
                    label="<- fish vs meat ->",
                    min_value=0.0,
                    value=0.5,
                    max_value=1.0,
                    step=0.01,
                    key=f"state/{block}/{name}/fish_vs_meat",
                )
                return state.BuildingCount(
                    count,
                    state.ConfiguredTavernBuilding(
                        building, fruit_vs_bread, fish_vs_meat
                    ),
                ), info

            case state.SmokeryBuilding():
                count = st.number_input(
                    name,
                    min_value=0,
                    value=0,
                    key=f"state/{block}/{name}/count",
                    label_visibility="collapsed",
                )
                info = st.empty()
                fish_vs_meat = 1 - st.slider(
                    label="<- fish vs meat ->",
                    min_value=0.0,
                    value=0.5,
                    max_value=1.0,
                    step=0.01,
                    key=f"state/{block}/{name}/fish_vs_meat",
                )
                return state.BuildingCount(
                    count, state.ConfiguredSmokeryBuilding(building, fish_vs_meat)
                ), info

            case state.PlainBuilding():
                count = st.number_input(
                    name,
                    min_value=0,
                    value=0,
                    key=f"state/{block}/{name}/count",
                    label_visibility="collapsed",
                )
                info = st.empty()
                return state.BuildingCount(count, building), info


def main():
    st.set_page_config(page_title="widelands planner", layout="wide")

    # st.json(state.get_makes(buildings).as_human())
    # st.json(state.get_takes(buildings).as_human())
    # st.json(state.get_balance(buildings).as_human())
    # st.json(state.get_shortages_ips(buildings).as_ipm())
    # st.json(state.get_usage_ratios(buildings).as_percentages())

    blocks: list[str] = st.session_state.setdefault("state/blocks", ["main"])
    blocks = blocks or ["main"]

    with st.container():
        new_tab_name = st.text_input("new tab name", key="input/new tab name")
        if st.button("add block", key="button/add block"):
            if new_tab_name != "" and new_tab_name not in blocks:
                blocks.append(new_tab_name)
                st.session_state["state/blocks"] = blocks
                st.rerun()

    for block, tab in zip(blocks, st.tabs(blocks), strict=True):
        buildings: list[state.BuildingCount] = []
        infos: list[DeltaGenerator] = []

        with tab:
            with st.container(horizontal=True):
                if st.button("delete block", key=f"input/delete block {block}"):
                    blocks.remove(block)
                    blocks = blocks or ["main"]
                    st.session_state["state/blocks"] = blocks
                    st.rerun()
                actions = st.empty()
            with st.container(
                horizontal=True, horizontal_alignment="left", border=False
            ):
                for building in sorted(state.get_buildings(), key=lambda b: b.name):
                    b, i = st_building_count(block, building)
                    buildings.append(b)
                    infos.append(i)
            shortages = state.get_shortages_ips(buildings)
            with actions.container(horizontal=True):
                for b, i in zip(buildings, infos, strict=True):
                    match b.can_fulfill(shortages):
                        case None:
                            i.write("no issues")
                        case str(msg):
                            i.write(f":warning: {msg}")
                            st.write(f"**{b.get_name()}**: {msg}")

    # with st.sidebar:
    #     st.header("shortages")
    #     st.json(shortages.as_ipm())


if __name__ == "__main__":
    main()

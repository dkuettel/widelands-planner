from __future__ import annotations

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


def st_block(block: str):
    with st.expander("config"):
        with st.container(horizontal=True):
            if st.button("delete block", key=f"input/delete block {block}"):
                blocks = st.session_state.get("state/blocks", []) or ["main"]
                blocks.remove(block)
                blocks = blocks or ["main"]
                st.session_state["state/blocks"] = blocks
                st.rerun()
        kinds = st.pills(
            "block kind",
            # TODO this make st.session_state contain the full object, not just the name
            state.get_block_kinds(),
            format_func=lambda s: s.name,
            selection_mode="multi",
            key=f"state/{block}/building kinds",
        )
        kind = state.BlockKind.from_many(kinds)

    st_imports, st_info, st_exports = st.columns([1, 2, 1], border=True)
    st_active = st.container(horizontal=True, horizontal_alignment="left", border=False)
    st_inactive = st.expander("other buildings").container(
        horizontal=True, horizontal_alignment="left", border=False
    )

    building_counts: list[state.BuildingCount] = []
    infos: list[DeltaGenerator] = []
    buildings = state.get_buildings()
    buildings = sorted(buildings, key=lambda b: b.name)
    for building in buildings:
        if building.name in kind.buildings:
            with st_active:
                b, i = st_building_count(block, building)
        else:
            with st_inactive:
                b, i = st_building_count(block, building)
        building_counts.append(b)
        infos.append(i)

    balance = state.get_block_balance(
        state.Block(block, kind.imports, building_counts, kind.exports)
    )

    with st_imports, st.container(gap=None):
        st.write("**imports**")
        st.json(balance.imports.as_ipm())

    with st_info, st.container(gap=None):
        st.write("**info**")
        st.json(balance.local.as_ipm())
        # actions = st.empty()

    with st_exports, st.container(gap=None):
        st.write("**exports**")
        st.json(balance.exports.as_ipm())

    # with actions.container(horizontal=False, gap=None):
    #     for b, i in zip(building_counts, infos, strict=True):
    #         match b.can_fulfill(shortages):
    #             case None:
    #                 i.write("no issues")
    #             case str(msg):
    #                 i.write(f":warning: {msg}")
    #                 st.write(f"**{b.get_name()}**: {msg}")


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
        new_tab_name = st.text_input("new block name", key="input/new block name")
        if st.button("add block", key="button/add block"):
            if new_tab_name != "" and new_tab_name not in blocks:
                blocks.append(new_tab_name)
                st.session_state["state/blocks"] = blocks
                st.rerun()

    for block, tab in zip(blocks, st.tabs(blocks), strict=True):
        with tab:
            st_block(block)

    # with st.sidebar:
    #     st.header("shortages")
    #     st.json(shortages.as_ipm())


if __name__ == "__main__":
    main()

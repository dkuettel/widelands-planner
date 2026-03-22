from __future__ import annotations

import streamlit as st
from streamlit.delta_generator import DeltaGenerator

from widelands_planner import state


def st_building_count(
    block: str, name: str, building: state.Building
) -> tuple[state.BuildingCount, DeltaGenerator]:
    with st.container(border=True, width=200):
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

            case _ as never:  # pyright: ignore[reportUnnecessaryComparison]
                assert False, never  # pyright: ignore[reportUnreachable]


def delete_block(block: str):
    blocks = st.session_state.get("state/blocks", []) or ["main"]
    blocks.remove(block)
    blocks = blocks or ["main"]
    st.session_state["state/blocks"] = blocks
    st.rerun()


def st_ivec(ivec: state.Ivec):
    for i, ips in ivec.sorted():
        counts = state.building_count_from_ips(i, ips)
        rep = " or ".join(f"{c:.1f} {b.value}" for b, c in counts)
        if ips > 0:
            st.write(f"{60 * ips:.1f} {i.value}/min = {rep}")
        else:
            st.write(f"**{60 * ips:.1f} {i.value}/min = {rep}**")


def st_block(block: str) -> state.BlockBalance:
    items = state.get_items()
    buildings = state.get_buildings()

    st_meta, st_buildings = st.columns([1, 2])
    with st_meta:
        with (
            st.expander("block"),
            st.container(border=False, horizontal=True, vertical_alignment="bottom"),
        ):
            # TODO not sure how that works here
            st.text_input("name", value=block, key=f"key/{block}/name")
            if st.button("delete", key=f"key/{block}/delete"):
                delete_block(block)

        with st.container(border=True):
            imports = st.multiselect(
                "imports",
                items,
                format_func=lambda i: i.value,
                key=f"state/{block}/imports",
            )
            st_imports = st.empty()
        with st.container(border=True):
            locals = st.multiselect(
                "locals",
                buildings,
                key=f"state/{block}/locals",
            )
            st_locals = st.empty()
        with st.container(border=True):
            exports = st.multiselect(
                "exports",
                items,
                format_func=lambda i: i.value,
                key=f"state/{block}/exports",
            )
            st_exports = st.empty()

    building_counts: list[state.BuildingCount] = []
    infos: list[DeltaGenerator] = []

    with st_buildings:
        with (
            st.expander("local buildings", expanded=True),
            st.container(horizontal=True),
        ):
            for name in locals:
                b, i = st_building_count(block, name, buildings[name])
                building_counts.append(b)
                infos.append(i)
        with st.expander("more buildings"), st.container(horizontal=True):
            for name in sorted(set(buildings) - set(locals)):
                b, i = st_building_count(block, name, buildings[name])
                building_counts.append(b)
                infos.append(i)

    balance = state.get_block_balance(
        state.Block(block, set(imports), building_counts, set(exports))
    )

    with st_imports.container(gap=None):
        st_ivec(balance.imports)

    with st_locals.container(gap=None):
        st_ivec(balance.local)

    with st_exports.container(gap=None):
        st_ivec(balance.exports)

    return balance


def main():
    st.set_page_config(page_title="widelands planner", layout="wide")

    blocks: list[str] = st.session_state.setdefault("state/blocks", ["main"])
    blocks = blocks or ["main"]

    with st.container():
        new_tab_name = st.text_input("new block name", key="input/new block name")
        if st.button("add block", key="button/add block"):
            if new_tab_name != "" and new_tab_name not in blocks:
                blocks.append(new_tab_name)
                st.session_state["state/blocks"] = blocks
                st.rerun()

    balances: list[state.BlockBalance] = []
    for block, tab in zip(blocks, st.tabs(blocks), strict=True):
        with tab:
            balances.append(st_block(block))

    balance = state.get_global_balance(balances)

    with st.sidebar:
        st.subheader("global balance")
        with st.container(gap=None):
            st_ivec(balance)


if __name__ == "__main__":
    main()

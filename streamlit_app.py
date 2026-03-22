from __future__ import annotations

import json
from pathlib import Path

import streamlit as st
from streamlit.delta_generator import DeltaGenerator

from widelands_planner import state


def save_state(path: Path):
    state = {
        k: v
        for (k, v) in st.session_state.items()
        if isinstance(k, str) and k.startswith("state/")
    }
    path.write_text(json.dumps(state))


def load_state(path: Path):
    state = json.loads(path.read_text())
    st.session_state.update(state)


def get_block_ids() -> list[int]:
    ids: list[int] | None = st.session_state.get("state/block_ids")
    if ids is None:
        st.session_state["state/next_block_id"] = 0
        ids = []
        st.session_state["state/block_ids"] = ids
    if len(ids) == 0:
        next_id = st.session_state["state/next_block_id"]
        ids = [next_id]
        st.session_state["state/block_ids"] = ids
        st.session_state["state/next_block_id"] = next_id + 1
    return ids


def get_block_name_key(id: int) -> str:
    return f"state/blocks/{id}/name"


def get_block_name(id: int) -> str:
    return st.session_state.setdefault(get_block_name_key(id), "unnamed")


def add_block(name: str):
    id = st.session_state.get("state/next_block_id", 1)
    ids = get_block_ids()
    ids.append(id)
    st.session_state["state/block_ids"] = ids
    st.session_state[f"state/blocks/{id}/name"] = name
    st.session_state["state/next_block_id"] = id + 1


def remove_block(block_id: int):
    block_ids = get_block_ids()
    block_ids.remove(block_id)
    st.session_state["state/block_ids"] = block_ids


def st_building_count(
    block_id: int, name: str, building: state.Building
) -> tuple[state.BuildingCount, DeltaGenerator]:
    with st.container(border=True, width=200):
        st.write(f"**{name}**")
        match building:
            case state.TavernBuilding():
                count = st.number_input(
                    "count",
                    min_value=0,
                    value=0,
                    key=f"state/blocks/{block_id}/buildings/{name}/count",
                    label_visibility="collapsed",
                )
                info = st.empty()
                fruit_vs_bread = 1 - st.slider(
                    label="<- fruit vs bread ->",
                    min_value=0.0,
                    value=0.5,
                    max_value=1.0,
                    step=0.01,
                    key=f"state/blocks/{block_id}/buildings/{name}/fruit_vs_bread",
                )
                fish_vs_meat = 1 - st.slider(
                    label="<- fish vs meat ->",
                    min_value=0.0,
                    value=0.5,
                    max_value=1.0,
                    step=0.01,
                    key=f"state/blocks/{block_id}/buildings/{name}/fish_vs_meat",
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
                    key=f"state/blocks/{block_id}/buildings/{name}/count",
                    label_visibility="collapsed",
                )
                info = st.empty()
                fish_vs_meat = 1 - st.slider(
                    label="<- fish vs meat ->",
                    min_value=0.0,
                    value=0.5,
                    max_value=1.0,
                    step=0.01,
                    key=f"state/blocks/{block_id}/buildings/{name}/fish_vs_meat",
                )
                return state.BuildingCount(
                    count, state.ConfiguredSmokeryBuilding(building, fish_vs_meat)
                ), info

            case state.PlainBuilding():
                count = st.number_input(
                    name,
                    min_value=0,
                    value=0,
                    key=f"state/blocks/{block_id}/buildings/{name}/count",
                    label_visibility="collapsed",
                )
                info = st.empty()
                return state.BuildingCount(count, building), info

            case _ as never:  # pyright: ignore[reportUnnecessaryComparison]
                assert False, never  # pyright: ignore[reportUnreachable]


def st_ivec(ivec: state.Ivec):
    for i, ips in ivec.sorted():
        counts = state.building_count_from_ips(i, ips)
        rep = " or ".join(f"{c:.1f} {b.value}" for b, c in counts)
        if ips > 0:
            st.write(f"{60 * ips:.1f} {i.value}/min = {rep}")
        else:
            st.write(f"**{60 * ips:.1f} {i.value}/min = {rep}**")


def st_block(block_id: int) -> state.BlockBalance:
    items = state.get_items()
    buildings = state.get_buildings()

    st_meta, st_buildings = st.columns([1, 2])
    with st_meta:
        with (
            st.expander("edit"),
            st.container(border=False, horizontal=True, vertical_alignment="bottom"),
        ):
            st.text_input("name", key=get_block_name_key(block_id))
            st.button(
                "delete",
                key=f"key/blocks/{block_id}/delete",
                on_click=remove_block,
                args=(block_id,),
            )

        with st.container(border=True):
            imports = st.multiselect(
                "imports",
                items,
                format_func=lambda i: i.value,
                key=f"state/blocks/{block_id}/imports",
            )
            st_imports = st.empty()
        with st.container(border=True):
            locals = st.multiselect(
                "locals",
                buildings,
                key=f"state/blocks/{block_id}/locals",
            )
            st_locals = st.empty()
        with st.container(border=True):
            exports = st.multiselect(
                "exports",
                items,
                format_func=lambda i: i.value,
                key=f"state/blocks/{block_id}/exports",
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
                b, i = st_building_count(block_id, name, buildings[name])
                building_counts.append(b)
                infos.append(i)
        with st.expander("more buildings"), st.container(horizontal=True):
            for name in sorted(set(buildings) - set(locals)):
                b, i = st_building_count(block_id, name, buildings[name])
                building_counts.append(b)
                infos.append(i)

    balance = state.get_block_balance(
        state.Block(set(imports), building_counts, set(exports))
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

    with st.sidebar:
        with st.container(horizontal=True):
            if st.button("save"):
                save_state(Path("./state.json"))
            if st.button("load"):
                load_state(Path("./state.json"))
        with st.expander("add blocks"):
            new_block_name = st.text_input("name", key="key/new block name")
            st.button(
                "add",
                key="key/add new block",
                on_click=add_block,
                args=(new_block_name,),
            )

    block_ids = get_block_ids()
    block_names = [get_block_name(i) for i in block_ids]

    balances: list[state.BlockBalance] = []
    for block_id, tab in zip(block_ids, st.tabs(block_names), strict=True):
        with tab:
            balances.append(st_block(block_id))

    balance = state.get_global_balance(balances)

    with st.sidebar:
        st.subheader("global balance")
        with st.container(gap=None):
            st_ivec(balance)


if __name__ == "__main__":
    main()

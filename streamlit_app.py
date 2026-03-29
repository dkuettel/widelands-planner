from __future__ import annotations

import json
from functools import partial
from pathlib import Path
from typing import override
from uuid import uuid4

import streamlit as st

from widelands_planner import state


def save_state(path: Path):
    state = {
        k: v
        for (k, v) in st.session_state.items()
        if isinstance(k, str) and k.startswith("state.")
    }
    path.write_text(json.dumps(state))


def load_state(path: Path):
    state = json.loads(path.read_text())
    st.session_state.update(state)


class Key:
    def __init__(self, at: tuple[str, ...] = ()):
        self.__at = at

    def __getitem__(self, name: str) -> Key:
        return Key((*self.__at, name))

    def __getattr__(self, name: str) -> Key:
        return self[name]

    @override
    def __str__(self) -> str:
        return ".".join(self.__at)


def st_ivec(ivec: state.Ivec):
    deficit = st.container(gap=None)
    deficit.write("**deficit**")
    surplus = st.container(gap=None)
    surplus.write("**surplus**")
    for i, ips in ivec.sorted():
        counts = state.building_count_from_ips(i, ips)
        rep = " or ".join(f"{c:.1f} {b.value}" for b, c in counts)
        if ips > 0:
            surplus.write(f"- {60 * ips:.1f} {i.value}/min = {rep}")
        else:
            deficit.write(f"- {60 * ips:.1f} {i.value}/min = {rep}")


kstate = Key().state


def get[T](key: Key, ty: type[T], default: T) -> T:
    value = st.session_state.setdefault(str(key), default)
    # TODO check type better
    # assert isinstance(value, ty)
    return value


def get_block_ids() -> list[str]:
    return get(kstate.blocks.ids, list[str], [])


def add_block():
    id = uuid4().hex
    get(kstate.blocks.ids, list[str], []).append(id)


def remove_block(id: str):
    get(kstate.blocks.ids, list[str], []).remove(id)


def get_count_ids(block_id: str) -> list[str]:
    return get(kstate.blocks.items[block_id].counts.ids, list[str], [])


def get_count(block_id: str, count_id: str) -> int:
    # TODO so i guess we could just make Key so that it only has valid keys? if we want it documented?
    return get(kstate.blocks.items[block_id].counts.items[count_id].count, int, 0)


def add_count(block_id: str):
    id = uuid4().hex
    get(kstate.blocks.items[block_id].counts.ids, list[str], []).append(id)


def remove_count(block_id: str, count_id: str):
    get(kstate.blocks.items[block_id].counts.ids, list[str], []).remove(count_id)


def get_bname(block_id: str, count_id: str) -> state.Bname:
    # TODO does this return str or a Bname?
    return get(
        kstate.blocks.items[block_id].counts.items[count_id].bname,
        state.Bname,
        state.Bname.fishers_houses,
    )


def get_takes(
    block_id: str, count_id: str, default: set[state.Item]
) -> set[state.Item]:
    return set(
        get(
            kstate.blocks.items[block_id].counts.items[count_id].takes,
            list[state.Item],
            list(default),
        )
    )


def get_imports(block_id: str) -> set[state.Item]:
    return set(
        get(
            kstate.blocks.items[block_id].imports,
            list[state.Item],
            list(),
        )
    )


def get_exports(block_id: str) -> set[state.Item]:
    return set(
        get(
            kstate.blocks.items[block_id].exports,
            list[state.Item],
            list(),
        )
    )


def get_state(
    buildings: dict[state.Bname, state.Building],
) -> tuple[list[state.BlockBalance], state.Ivec]:
    balances = [get_state_block(buildings, block_id) for block_id in get_block_ids()]
    balance = state.get_global_balance(balances)
    return balances, balance


def get_state_block(
    buildings: dict[state.Bname, state.Building], block_id: str
) -> state.BlockBalance:
    imports = get_imports(block_id)
    counts = [
        get_state_block_count(buildings, block_id, count_id)
        for count_id in get_count_ids(block_id)
    ]
    exports = get_exports(block_id)
    balance = state.get_block_balance(state.Block(imports, counts, exports))
    return balance


def get_state_block_count(
    buildings: dict[state.Bname, state.Building], block_id: str, count_id: str
) -> state.BuildingCount:
    count = get_count(block_id, count_id)
    bname = get_bname(block_id, count_id)
    building = buildings[bname]
    match building:
        case state.TavernBuilding():
            takes = get_takes(block_id, count_id, building.get_take_items())
            return state.BuildingCount(
                count, state.ConfiguredTavernBuilding(building, takes)
            )
        case state.SmokeryBuilding():
            takes = get_takes(block_id, count_id, building.get_take_items())
            return state.BuildingCount(
                count, state.ConfiguredSmokeryBuilding(building, takes)
            )
        case state.PlainBuilding():
            return state.BuildingCount(count, building)


def main():
    st.set_page_config(page_title="widelands planner", layout="wide")

    buildings = state.get_buildings()
    balances, balance = get_state(buildings)
    bnames = sorted(state.Bname)
    items = state.get_items()

    with st.sidebar:
        st.subheader("global balance")
        with st.container(gap=None):
            st_ivec(balance)
        st.divider()
        st.button("add block", on_click=add_block)
        st.divider()
        with st.container(horizontal=True):
            if st.button("save"):
                # TODO do those still work?
                save_state(Path("./state.json"))
            if st.button("load"):
                load_state(Path("./state.json"))

    block_ids = get_block_ids()
    if len(block_ids) == 0:
        st.write("no blocks")
    else:
        block_names = [
            get(kstate.blocks.items[id].name, str, "unnamed block") for id in block_ids
        ]
        tabs = st.tabs(block_names)
        for tab, block_id, block_balance in zip(tabs, block_ids, balances, strict=True):
            with tab:
                meta, counts = st.columns([1, 4])
                with meta:
                    with st.expander("block", expanded=True):
                        st.text_input(
                            "name", key=str(kstate.blocks.items[block_id].name)
                        )
                        st.button(
                            "remove",
                            key=str(kstate.blocks.items[block_id].remove),
                            on_click=partial(remove_block, block_id),
                        )
                    with st.expander("imports", expanded=True):
                        st.multiselect(
                            "imports",
                            items,
                            key=str(kstate.blocks.items[block_id].imports),
                            label_visibility="collapsed",
                        )
                        st_ivec(block_balance.imports)
                    with st.expander("local", expanded=True):
                        st_ivec(block_balance.local)
                    with st.expander("exports", expanded=True):
                        st.multiselect(
                            "exports",
                            items,
                            key=str(kstate.blocks.items[block_id].exports),
                            label_visibility="collapsed",
                        )
                        st_ivec(block_balance.exports)
                with counts, st.container(horizontal=True, border=False):
                    for count_id in get_count_ids(block_id):
                        with st.container(width=250, border=True):
                            st.selectbox(
                                "building",
                                bnames,
                                key=str(
                                    kstate.blocks.items[block_id]
                                    .counts.items[count_id]
                                    .bname
                                ),
                            )
                            st.number_input(
                                "count",
                                key=str(
                                    kstate.blocks.items[block_id]
                                    .counts.items[count_id]
                                    .count
                                ),
                                min_value=0,
                            )
                            bname = get_bname(block_id, count_id)
                            building = buildings[bname]
                            match building:
                                case state.TavernBuilding() | state.SmokeryBuilding():
                                    st.multiselect(
                                        "takes",
                                        sorted(building.get_take_items()),
                                        key=str(
                                            kstate.blocks.items[block_id]
                                            .counts.items[count_id]
                                            .takes
                                        ),
                                    )
                                case _:
                                    pass
                            st.button(
                                "remove",
                                key=str(
                                    kstate.blocks.items[block_id]
                                    .counts.items[count_id]
                                    .remove
                                ),
                                on_click=partial(remove_count, block_id, count_id),
                            )
                    st.button(
                        "add building",
                        key=str(kstate.blocks.items[block_id].add),
                        on_click=partial(add_count, block_id),
                    )


if __name__ == "__main__":
    main()

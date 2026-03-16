from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from typing import Literal

import streamlit as st

type BuildingName = Literal[
    "forester",
    "woodcutter",
    "clay pit",
    "brick kiln",
    "water",
    "coal",
    "granite",
]

buildings: set[BuildingName] = set(BuildingName.__value__.__args__)

requires: dict[BuildingName, dict[BuildingName, float]] = {
    "woodcutter": {"forester": 0.5},
    "clay pit": {"water": 0.7},
    "brick kiln": {"clay pit": 2.1, "coal": 0.5, "granite": 0.5},
}


@dataclass(frozen=True)
class BlockInfo:
    buildings: set[BuildingName]
    # NOTE how to deal with stuff that is exported but also used?
    exports: set[BuildingName]
    imports: set[BuildingName]


block_infos: dict[str, BlockInfo] = {
    "clay works": BlockInfo(
        {"clay pit", "brick kiln", "water"},
        {"brick kiln", "clay pit"},
        {"granite", "coal"},
    ),
    "wood": BlockInfo({"forester", "woodcutter"}, {"woodcutter"}, set()),
    "mining": BlockInfo({"coal", "granite"}, {"coal", "granite"}, set()),
}


def get_block_ids() -> list[int]:
    return st.session_state.setdefault("state/blocks", [])


def add_block():
    blocks = get_block_ids()
    blocks.append(max(blocks, default=0) + 1)


def delete_block(id: int):
    blocks = get_block_ids()
    blocks.remove(id)


def get_block_type(id: int) -> str:
    return st.session_state.setdefault(f"key/block/{id}/type", sorted(block_infos)[0])


def get_block_name(id: int) -> str:
    return st.session_state.setdefault(f"key/block/{id}/name", "")


def get_block_info(id: int) -> BlockInfo:
    return block_infos[get_block_type(id)]


def get_block_building(id: int, name: BuildingName) -> int:
    return st.session_state.get(f"key/block/{id}/buildings/{name}", 0)


def get_direct_needs(block: int) -> dict[BuildingName, float]:
    needs: dict[BuildingName, float] = dict()
    for building in buildings:
        for other, count in requires.get(building, {}).items():
            needs[other] = (
                needs.get(other, 0)
                + st.session_state.get(f"key/block/{block}/buildings/{building}", 0)
                * count
            )
    return needs


def get_block_label(id: int) -> str:
    label = get_block_type(id)
    name = get_block_name(id)
    if name:
        return f'{label} **"{name}"**'
    return label


def key(*names: str | int) -> str:
    assert len(names) > 0
    return "key/" + "/".join(map(str, names))


def st_block(bid: int):
    bkey = partial(key, "block", bid)
    bbkey = partial(key, "block", bid, "buildings")
    bbcount = partial(get_block_building, bid)

    with st.expander(
        label=get_block_label(bid),
        expanded=True,
        key=bkey("expander"),
    ):
        with st.container(horizontal=True, vertical_alignment="bottom"):
            st.selectbox("type", sorted(block_infos), key=bkey("type"))
            st.text_input(f"name for block id {bid}", key=bkey("name"))
            if st.button("delete", key=bkey("delete")):
                delete_block(bid)
                st.rerun()

        with st.container(horizontal=True):
            needs: dict[BuildingName, float] = get_direct_needs(bid)
            for name in sorted(buildings):
                if (
                    name in get_block_info(bid).buildings
                    or bbcount(name) > 0
                    or needs.get(name, 0) > 0
                ):
                    with st.container(border=True, width=200):
                        if name in get_block_info(bid).exports:
                            st.number_input(
                                f"{name} - exported",
                                min_value=0,
                                key=bbkey(name),
                            )
                        elif name in get_block_info(bid).imports:
                            st.number_input(
                                f"{name} - imported",
                                min_value=0,
                                key=bbkey(name),
                                # TODO hmm this could be non-zero from a previous type? and then you cant change it
                                disabled=True,
                            )
                        else:
                            st.number_input(
                                name,
                                min_value=0,
                                key=bbkey(name),
                            )
                        match needs.get(name, None):
                            case None | 0 | 0.0:
                                if (
                                    name in get_block_info(bid).exports
                                    or bbcount(name) == 0
                                ):
                                    st.write("no need")
                                else:
                                    st.write("no need :warning:")
                            case float(c) | int(c):
                                if bbcount(name) < c:
                                    st.write(f"needs {c:.1f} :warning:")
                                else:
                                    st.write(f"needs {c:.1f}")


def main():
    st.title("blocks")
    for bid in get_block_ids():
        st_block(bid)

    with st.container(horizontal=False, horizontal_alignment="right", border=False):
        if st.button("add block", key="key/button/add block"):
            add_block()
            st.rerun()

    st.title("summary")
    with st.container(horizontal=True):
        for building in sorted(buildings):
            count = sum(
                st.session_state.get(f"key/block/{block}/buildings/{building}", 0)
                for block in get_block_ids()
            )
            st.write(count, building)

    exports: dict[str, int] = dict()
    for bid in get_block_ids():
        block_type = st.session_state[f"key/block/{bid}/type"]
        for building in block_infos[block_type].exports:
            exports[building] = exports.get(building, 0) + st.session_state.get(
                f"key/block/{bid}/buildings/{building}", 0
            )

    imports: dict[str, float] = dict()
    for bid in get_block_ids():
        block_type = st.session_state[f"key/block/{bid}/type"]
        needs: dict[BuildingName, float] = get_direct_needs(bid)
        for building in block_infos[block_type].imports:
            imports[building] = imports.get(building, 0) + needs.get(building, 0)

    with st.container(gap=None):
        for building in buildings:
            missing = imports.get(building, 0) - exports.get(building, 0)
            if missing > 0:
                st.write(f"missing {missing} {building}")


if __name__ == "__main__":
    main()

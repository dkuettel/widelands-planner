from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import streamlit as st

# TODO add sanity checks, or typing, that all buildings here and in other places are the same
buildings: set[str] = {
    "forester",
    "woodcutter",
    "clay pit",
    "brick kiln",
    "water",
    "coal",
    "granite",
}

requires: dict[str, dict[str, float]] = {
    "woodcutter": {"forester": 0.5},
    "clay pit": {"water": 0.7},
    "brick kiln": {"clay pit": 2.1, "coal": 0.5, "granite": 0.5},
}


@dataclass(frozen=True)
class BlockInfo:
    buildings: set[str]
    # NOTE how to deal with stuff that is exported but also used?
    exports: set[str]
    imports: set[str]


block_infos: dict[str, BlockInfo] = {
    "clay works": BlockInfo(
        {"clay pit", "brick kiln", "water"},
        {"brick kiln", "clay pit"},
        {"granite", "coal"},
    ),
    "wood": BlockInfo({"forester", "woodcutter"}, {"woodcutter"}, set()),
}


class State:
    def blocks(self) -> list[int]:
        return st.session_state.setdefault("state/blocks", [])

    def add_block(self):
        blocks = self.blocks()
        blocks.append(max(blocks, default=0) + 1)

    def delete_block(self, i: int):
        blocks = self.blocks()
        blocks.remove(i)


def get_direct_needs(block: int) -> dict[str, float]:
    needs: dict[str, float] = dict()
    for building in buildings:
        for other, count in requires.get(building, {}).items():
            needs[other] = (
                needs.get(other, 0)
                + st.session_state.get(f"key/block/{block}/buildings/{building}", 0)
                * count
            )
    return needs


def main():
    st.write(datetime.now())

    state = State()

    st.title("widelands")

    st.header("blocks")
    for block in state.blocks():
        with st.container(border=True):
            with st.container(horizontal=True, vertical_alignment="bottom"):
                st.text_input(
                    f"name for block id {block}", key=f"key/block/{block}/name"
                )
                block_type = st.selectbox(
                    "type", sorted(block_infos), key=f"key/block/{block}/type"
                )
                if st.button("delete", key=f"key/block/{block}/delete"):
                    state.delete_block(block)
                    st.rerun()
            with st.container(horizontal=True):
                needs: dict[str, float] = get_direct_needs(block)
                for name in sorted(buildings):
                    if (
                        name in block_infos[block_type].buildings
                        or st.session_state.get(
                            f"key/block/{block}/buildings/{name}", 0
                        )
                        > 0
                        or needs.get(name, 0) > 0
                    ):
                        with st.container(border=True, width=200):
                            if name in block_infos[block_type].exports:
                                st.number_input(
                                    f"{name} - exported",
                                    min_value=0,
                                    key=f"key/block/{block}/buildings/{name}",
                                )
                            elif name in block_infos[block_type].imports:
                                st.number_input(
                                    f"{name} - imported",
                                    min_value=0,
                                    key=f"key/block/{block}/buildings/{name}",
                                    disabled=True,
                                )
                            else:
                                st.number_input(
                                    name,
                                    min_value=0,
                                    key=f"key/block/{block}/buildings/{name}",
                                )
                            match needs.get(name, None):
                                case None | 0 | 0.0:
                                    if (
                                        name in block_infos[block_type].exports
                                        or st.session_state.get(
                                            f"key/block/{block}/buildings/{name}", 0
                                        )
                                        == 0
                                    ):
                                        st.write("no need")
                                    else:
                                        st.write("no need :warning:")
                                case float(c) | int(c):
                                    if (
                                        st.session_state.get(
                                            f"key/block/{block}/buildings/{name}", 0
                                        )
                                        < c
                                    ):
                                        st.write(f"needs {c:.1f} :warning:")
                                    else:
                                        st.write(f"needs {c:.1f}")

    with st.container(horizontal=False, border=False):
        if st.button("add block"):
            state.add_block()
            st.rerun()

    st.header("totals")
    with st.container(horizontal=True):
        for building in sorted(buildings):
            count = sum(
                st.session_state.get(f"key/block/{block}/buildings/{building}", 0)
                for block in state.blocks()
            )
            st.write(count, building)


if __name__ == "__main__":
    main()

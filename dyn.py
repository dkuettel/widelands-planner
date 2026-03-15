from __future__ import annotations

from datetime import datetime

import streamlit as st

buildings: set[str] = {
    "forester",
    "woodcutter",
    "clay pit",
    "brick kiln",
    "water",
}

block_types: dict[str, set[str]] = {
    "bricks": {"clay pit", "brick kiln", "water"},
    "wood": {"forester", "woodcutter"},
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


def main():
    st.write(datetime.now())

    state = State()

    st.title("widelands")

    for i in state.blocks():
        with st.container(border=True):
            with st.container(horizontal=True, vertical_alignment="bottom"):
                st.text_input(f"name for block id {i}", key=f"key/block/{i}/name")
                block_type = st.selectbox(
                    "type", sorted(block_types), key=f"key/block/{i}/type"
                )
                if st.button("delete", key=f"key/block/{i}/delete"):
                    state.delete_block(i)
                    st.rerun()
            with st.container(horizontal=True):
                for name in sorted(buildings):
                    if (
                        name in block_types[block_type]
                        or st.session_state.get(f"key/block/{i}/buildings/{name}", 0)
                        > 0
                    ):
                        with st.container(border=True, width=200):
                            st.number_input(
                                name, min_value=0, key=f"key/block/{i}/buildings/{name}"
                            )

    with st.container(horizontal=False, border=False):
        if st.button("add block"):
            state.add_block()
            st.rerun()


if __name__ == "__main__":
    main()

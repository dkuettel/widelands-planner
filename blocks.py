from __future__ import annotations

from datetime import datetime

import streamlit as st
from streamlit.delta_generator import DeltaGenerator

st.write(datetime.now())

buildings = sorted(
    {
        "forester",
        "woodcutter",
        "taverns",
        "bakeries",
        "farms",
        "waters",
    }
)

blocks = {
    "bread": {
        "taverns": 1,
        "bakeries": 2,
        "farms": 3,
        "waters": 2,
    }
}

building_infos: dict[str, DeltaGenerator] = dict()


def building(name: str):
    with st.container(border=True, width=200):
        st.session_state.setdefault(name, 0)
        flag = "" if st.session_state[name] >= 0 else " :warning:"
        st.number_input(f"{name}{flag}", value=0, key=name)
        building_infos[name] = st.empty()


def block(name: str):
    st.session_state.setdefault(f"block {name}", 0)

    def callback():
        nonlocal count, name
        change = st.session_state[f"block {name}"] - count
        for name, count in blocks[name].items():
            st.session_state[name] = st.session_state.get(name, 0) - change * count

    avail = min(
        [st.session_state.get(name, 0) // count for name, count in blocks[name].items()]
    )
    elements = " - ".join(f"{count} {name}" for name, count in blocks[name].items())
    count = st.number_input(
        f"**({avail:+}) {name}**: {elements}",
        min_value=0,
        value=0,
        key=f"block {name}",
        on_change=callback,
    )


with st.container(border=False):
    st.title("state")

    st.header("buildings")
    with st.container(horizontal=True, border=False):
        for name in buildings:
            building(name)

    st.header("blocks")
    with st.container(border=False):
        for name in sorted(blocks):
            block(name)

with st.container(border=False):
    st.title("totals")
    totals = {name: st.session_state.get(name, 0) for name in buildings}
    for block, counts in blocks.items():
        for name, ratio in counts.items():
            totals[name] += st.session_state.get(f"block {block}", 0) * ratio
    # st.json(totals)
    with st.container(horizontal=True):
        for name, count in sorted(totals.items()):
            st.write(count, name)
            building_infos[name].write(f"total {count} @80% = {count * 0.8:.1f}")

# st.write(st.session_state)

from __future__ import annotations

import streamlit as st

buildings = {
    "forester",
    "woodcutter",
    "water",
    "clay pit",
    "brick kiln",
    "coal",
    "granite",
    "reed farm",
}

requires = {
    "woodcutter": {"forester": 0.5},
    "clay pit": {"water": 0.7},
    "brick kiln": {"clay pit": 2.1, "coal": 0.5, "granite": 0.5},
}

names = st.data_editor(["main"], num_rows="dynamic")

for name, tab in zip(names, st.tabs(names), strict=True):
    with tab:
        st.title("state")

        with st.container(horizontal=True):
            counts = {
                b: st.number_input(label=b, min_value=0, value=0, key=f"{name}/{b}")
                for b in sorted(buildings)
            }

        needs: dict[str, float] = dict()
        for b, c in counts.items():
            for nb, nc in requires.get(b, dict()).items():
                needs[nb] = needs.get(nb, 0.0) + c * nc
        needs = {
            b: (c - counts.get(b, 0)) for b, c in needs.items() if c > counts.get(b, 0)
        }

        if needs:
            st.title("actions")
            st.write(needs)

from __future__ import annotations

import streamlit as st
from streamlit.delta_generator import DeltaGenerator

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

required: dict[str, set[str]] = dict()
for b, r in requires.items():
    for rb in r:
        required.setdefault(rb, set()).add(b)

names = st.data_editor(["main"], num_rows="dynamic")

for name, tab in zip(names, st.tabs(names), strict=True):
    with tab:
        counts: dict[str, int] = dict()
        actions: dict[str, DeltaGenerator] = dict()
        for b in sorted(buildings):
            col1, col2 = st.columns([0.3, 0.7], border=True)
            with col1:
                counts[b] = st.number_input(
                    label=b, min_value=0, value=0, key=f"{name}/{b}"
                )
            with col2:
                actions[b] = st.empty()

        needs: dict[str, float] = dict()
        for b, c in counts.items():
            for nb, nc in requires.get(b, dict()).items():
                needs[nb] = needs.get(nb, 0.0) + c * nc

        needs = {
            b: (c - counts.get(b, 0)) for b, c in needs.items() if c > counts.get(b, 0)
        }

        for b, n in needs.items():
            actions[b].write(
                f"add {round(n, 1)} for: {','.join(required.get(b, set()))}"
            )

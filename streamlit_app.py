from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path

import streamlit as st
from streamlit.delta_generator import DeltaGenerator

buildings = {
    "brick kiln",
    "clay pit",
    "coal",
    "forester",
    "granite",
    "reed farm",
    "tavern (fish, fruit)",
    "water",
    "woodcutter",
    "smokery",
    "fishery",
    "fruit",
}

requires = {
    "brick kiln": {"clay pit": 2.1, "coal": 0.5, "granite": 0.5},
    "clay pit": {"water": 0.7},
    "coal": {"tavern (fish, fruit)": 37 / (2 * 41)},
    "granite": {"tavern (fish, fruit)": 37 / (2 * 46)},
    "tavern (fish, fruit)": {
        "smokery": 27 / (2 * 37),
        "fruit": ((37 + 62) / 2) / (2 * 37),
    },
    "smokery": {
        "fishery": ((26 + 59) / 2) / (27),
        "woodcutter": ((49 + 89) / 2) / (2 * 27),
    },
    "woodcutter": {"forester": 0.5},
}

required: dict[str, set[str]] = dict()
for b, r in requires.items():
    for rb in r:
        required.setdefault(rb, set()).add(b)


@dataclass
class State:
    names: list[str]
    counts: dict[str, dict[str, int]]

    @classmethod
    def from_defaults(cls):
        return cls(
            names=["main"],
            counts=dict(),
        )


path = Path("state.pickle")
if path.exists():
    state: State = pickle.loads(Path("state.pickle").read_bytes())  # pyright: ignore[reportAny]
else:
    state = State.from_defaults()

# TODO this doesnt quite work, only every second edit works?
state.names = st.data_editor(state.names, num_rows="dynamic")
names = [n for n in state.names if n is not None]  # pyright: ignore[reportUnnecessaryComparison]

for name, tab in zip(names, st.tabs(names), strict=True):
    with tab:
        state.counts.setdefault(name, dict())
        actions: dict[str, DeltaGenerator] = dict()
        for b in sorted(buildings):
            col1, col2, col3 = st.columns([2, 2, 3], border=True)
            with col1:
                state.counts[name][b] = st.number_input(
                    label=b,
                    min_value=0,
                    value=state.counts.get(name, dict()).get(b, 0),
                    key=f"{name}/{b}",
                    label_visibility="collapsed",
                )
            with col2:
                st.write(b)
            with col3:
                actions[b] = st.empty()

        needs: dict[str, float] = dict()
        for b, c in state.counts[name].items():
            for nb, nc in requires.get(b, dict()).items():
                needs[nb] = needs.get(nb, 0.0) + c * nc

        needs = {
            b: (c - state.counts[name].get(b, 0))
            for b, c in needs.items()
            if c > state.counts[name].get(b, 0)
        }

        for b, n in needs.items():
            actions[b].write(
                f"add {round(n, 1)} for: {','.join(required.get(b, set()))}"
            )

path.write_bytes(pickle.dumps(state))

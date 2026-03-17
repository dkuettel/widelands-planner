from __future__ import annotations

from datetime import datetime

import streamlit as st

from widelands_planner import state


def main():
    st.write(datetime.now())

    buildings: list[state.BuildingCount] = [
        state.TavernCount(3, 1, 1),
        state.SmokeryCount(1, 1),
    ]

    # st.json(state.get_makes(buildings).as_human())
    # st.json(state.get_takes(buildings).as_human())
    # st.json(state.get_balance(buildings).as_human())
    st.json(state.get_shortages_ips(buildings).as_ipm())
    # st.json(state.get_usage_ratios(buildings).as_percentages())

    with st.container(border=True):
        count = st.number_input("taverns", min_value=0, value=0, key="taverns/count")
        taverns_info = st.empty()
        fruit_vs_bread = 1 - st.slider(
            label="<- fruit vs bread ->",
            min_value=0.0,
            value=0.5,
            max_value=1.0,
            step=0.01,
            key="taverns/fruit_vs_bread",
        )
        fish_vs_meat = 1 - st.slider(
            label="<- fish vs meat ->",
            min_value=0.0,
            value=0.5,
            max_value=1.0,
            step=0.01,
            key="taverns/fish_vs_meat",
        )
        taverns = state.TavernCount(count, fruit_vs_bread, fish_vs_meat)

    with st.container(border=True):
        count = st.number_input(
            "smokeries", min_value=0, value=0, key="smokeries/count"
        )
        smokeries_info = st.empty()
        fish_vs_meat = 1 - st.slider(
            label="<- fish vs meat ->",
            min_value=0.0,
            value=0.5,
            max_value=1.0,
            step=0.01,
            key="smokeries/fish_vs_meat",
        )
        smokeries = state.SmokeryCount(count, fish_vs_meat)

    with st.container(border=True):
        count = st.number_input(
            "fisher's houses", min_value=0, value=0, key="fishers_houses/count"
        )
        fishers_houses_info = st.empty()
        fishers_houses = state.FishersHouseCount(count)

    buildings = [taverns, smokeries, fishers_houses]
    shortages = state.get_shortages_ips(buildings)
    st.write("shortages", shortages.as_ipm())

    taverns_info.write("no issues")
    if shortages[state.Item.smoked_fish] > 0 or shortages[state.Item.smoked_meat] > 0:
        smokeries_info.write(":warning: could use some")
    else:
        smokeries_info.write("no issues")
    if shortages[state.Item.fish] > 0:
        add = (
            shortages[state.Item.fish]
            / fishers_houses.__replace__(count=1).makes_ips()[state.Item.fish]
        )
        fishers_houses_info.write(f":warning: could use {add:.1f} more")
    else:
        fishers_houses_info.write("no issues")


if __name__ == "__main__":
    main()

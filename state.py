from __future__ import annotations

from datetime import datetime

import streamlit as st
from streamlit.delta_generator import DeltaGenerator

from widelands_planner import state


def st_building_count(
    building: state.Building,
) -> tuple[state.BuildingCount, DeltaGenerator]:
    match building:
        case state.Building.taverns:
            name, cls = building.value
            with st.container(border=True):
                count = st.number_input(name, min_value=0, value=0, key=f"{name}/count")
                info = st.empty()
                fruit_vs_bread = 1 - st.slider(
                    label="<- fruit vs bread ->",
                    min_value=0.0,
                    value=0.5,
                    max_value=1.0,
                    step=0.01,
                    key=f"{name}/fruit_vs_bread",
                )
                fish_vs_meat = 1 - st.slider(
                    label="<- fish vs meat ->",
                    min_value=0.0,
                    value=0.5,
                    max_value=1.0,
                    step=0.01,
                    key=f"{name}/fish_vs_meat",
                )
                return cls(count, fruit_vs_bread, fish_vs_meat), info
        case state.Building.smokeries:
            name, cls = building.value
            with st.container(border=True):
                count = st.number_input(name, min_value=0, value=0, key=f"{name}/count")
                info = st.empty()
                fish_vs_meat = 1 - st.slider(
                    label="<- fish vs meat ->",
                    min_value=0.0,
                    value=0.5,
                    max_value=1.0,
                    step=0.01,
                    key=f"{name}/fish_vs_meat",
                )
                return cls(count, fish_vs_meat), info
        case state.Building.fishers_houses | state.Building.foresters_houses:
            name, cls = building.value
            with st.container(border=True):
                count = st.number_input(name, min_value=0, value=0, key=f"{name}/count")
                info = st.empty()
                return cls(count), info


def main():
    st.write(datetime.now())

    # buildings: list[state.BuildingCount] = [
    #     state.TavernCount(3, 1, 1),
    #     state.SmokeryCount(1, 1),
    # ]

    # st.json(state.get_makes(buildings).as_human())
    # st.json(state.get_takes(buildings).as_human())
    # st.json(state.get_balance(buildings).as_human())
    # st.json(state.get_shortages_ips(buildings).as_ipm())
    # st.json(state.get_usage_ratios(buildings).as_percentages())

    buildings: list[state.BuildingCount] = []
    infos: list[DeltaGenerator] = []
    for building in state.Building:
        b, i = st_building_count(building)
        buildings.append(b)
        infos.append(i)

    shortages = state.get_shortages_ips(buildings)
    st.write("shortages", shortages.as_ipm())

    for b, i in zip(buildings, infos, strict=True):
        match b.can_fulfill(shortages):
            case None:
                i.write("no issues")
            case str(msg):
                i.write(f":warning: {msg}")

    # taverns_info.write("no issues")
    # if shortages[state.Item.smoked_fish] > 0 or shortages[state.Item.smoked_meat] > 0:
    #     smokeries_info.write(":warning: could use some")
    # else:
    #     smokeries_info.write("no issues")
    # if shortages[state.Item.fish] > 0:
    #     add = (
    #         shortages[state.Item.fish]
    #         / fishers_houses.__replace__(count=1).makes_ips()[state.Item.fish]
    #     )
    #     fishers_houses_info.write(f":warning: could use {add:.1f} more")
    # else:
    #     fishers_houses_info.write("no issues")


if __name__ == "__main__":
    main()

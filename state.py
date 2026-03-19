from __future__ import annotations

from datetime import datetime

import streamlit as st
from streamlit.delta_generator import DeltaGenerator

from widelands_planner import state


def st_building_count(
    building: state.Building,
) -> tuple[state.BuildingCount, DeltaGenerator]:
    with st.container(border=True, width=200):
        name = building.name
        st.write(f"**{name}**")
        match building:
            case state.TavernBuilding():
                count = st.number_input(
                    "count",
                    min_value=0,
                    value=0,
                    key=f"{name}/count",
                    label_visibility="collapsed",
                )
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
                return state.BuildingCount(
                    count,
                    state.ConfiguredTavernBuilding(
                        building, fruit_vs_bread, fish_vs_meat
                    ),
                ), info

            case state.SmokeryBuilding():
                count = st.number_input(
                    name,
                    min_value=0,
                    value=0,
                    key=f"{name}/count",
                    label_visibility="collapsed",
                )
                info = st.empty()
                fish_vs_meat = 1 - st.slider(
                    label="<- fish vs meat ->",
                    min_value=0.0,
                    value=0.5,
                    max_value=1.0,
                    step=0.01,
                    key=f"{name}/fish_vs_meat",
                )
                return state.BuildingCount(
                    count, state.ConfiguredSmokeryBuilding(building, fish_vs_meat)
                ), info

            case state.PlainBuilding():
                count = st.number_input(
                    name,
                    min_value=0,
                    value=0,
                    key=f"{name}/count",
                    label_visibility="collapsed",
                )
                info = st.empty()
                return state.BuildingCount(count, building), info


def main():
    st.set_page_config(page_title="widelands planner", layout="wide")
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
    with st.container(horizontal=True, horizontal_alignment="left", border=False):
        for building in sorted(state.get_buildings(), key=lambda b: b.name):
            b, i = st_building_count(building)
            buildings.append(b)
            infos.append(i)

    shortages = state.get_shortages_ips(buildings)

    with st.sidebar:
        st.header("shortages")
        st.json(shortages.as_ipm())

        st.header("actions")
        with st.container(gap=None):
            for b, i in zip(buildings, infos, strict=True):
                match b.can_fulfill(shortages):
                    case None:
                        i.write("no issues")
                    case str(msg):
                        i.write(f":warning: {msg}")
                        st.write(f"**{b.get_name()}**: {msg}")

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

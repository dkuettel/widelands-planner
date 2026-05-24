from __future__ import annotations

import json
import math
import os
import time
import zlib
from base64 import b64decode, b64encode
from collections.abc import Callable
from functools import partial
from typing import Final
from uuid import uuid4

import pandas as pd
import streamlit as st

from widelands_planner.app_data import Solution
from widelands_planner.state import (
    Bname,
    BuildingCount,
    ConfiguredGenericBuilding,
    Item,
    Ivec,
    ResumeState,
    building_from_name,
    isum,
    solve,
    summarize_ivec,
)

hcontainer = partial(st.container, horizontal=True)


def run():
    os.execvp(
        "streamlit",
        [
            "streamlit",
            "run",
            # NOTE runOnSave we dont want when deployed
            "--server.runOnSave",
            "True",
            # NOTE must be absolute, but by default it already watches the current folder
            # "--server.folderWatchList",
            # "/path/to/src",
            "src/widelands_planner/app.py",
        ],
    )


class SessionState:
    @property
    def revision(self) -> int:
        """every state change does +1"""
        return st.session_state.get("state.revision", 0)

    @revision.setter
    def revision(self, v: int):
        st.session_state["state.revision"] = v

    @property
    def blocks(self) -> dict[str, str]:
        """blocks[name] = uuid"""
        return st.session_state.get("state.blocks", dict())

    @blocks.setter
    def blocks(self, v: dict[str, str]):
        st.session_state["state.blocks"] = v

    @property
    def buildings(self) -> dict[str, list[str]]:
        """buildings[block uuid] = list of building uuids"""
        return st.session_state.get("state.buildings", dict())

    @buildings.setter
    def buildings(self, v: dict[str, list[str]]):
        st.session_state["state.buildings"] = v

    key_block_name: Final = "block_name"

    @property
    def block_name(self) -> str | None:
        """current block name to show"""
        return st.session_state.get(self.key_block_name, None)

    @block_name.setter
    def block_name(self, v: str | None):
        st.session_state[self.key_block_name] = v

    def key_building_name(self, uuid: str) -> str:
        return f"state.building[{uuid}].name"

    def get_building_name(self, uuid: str) -> Bname | None:
        match st.session_state.get(self.key_building_name(uuid), None):
            case str(s):
                if s in Bname:
                    return Bname(s)
                return None
            case _:
                return None

    def set_building_name(self, uuid: str, name: Bname | None):
        match name:
            case None:
                st.session_state[self.key_building_name(uuid)] = None
            case Bname():
                st.session_state[self.key_building_name(uuid)] = name.value

    def key_building_count(self, uuid: str) -> str:
        return f"state.building[{uuid}].count"

    def get_building_count(self, uuid: str) -> int:
        return st.session_state.get(self.key_building_count(uuid), 0)

    def set_building_count(self, uuid: str, count: int):
        st.session_state[f"state.building[{uuid}].count"] = count

    def key_building_takes(self, uuid: str, name: Bname) -> str:
        return f"state.building[{uuid}].settings.{name}.takes"

    def get_building_takes(self, uuid: str, name: Bname) -> list[Item]:
        value = st.session_state.get(self.key_building_takes(uuid, name), None)
        match value:
            case list():
                value = list(map(str, value))  # pyright: ignore[reportUnknownArgumentType]
                if all((i in Item) for i in value):
                    return sorted(Item(i) for i in value)
                building = building_from_name(name)
                return sorted(building.get_take_items())
            case _:
                building = building_from_name(name)
                return sorted(building.get_take_items())

    def set_building_takes(self, uuid: str, name: Bname, value: list[Item]):
        st.session_state[self.key_building_takes(uuid, name)] = [i.value for i in value]

    @property
    def render_count(self) -> int:
        return st.session_state.get("render_count", 0)

    @render_count.setter
    def render_count(self, count: int):
        st.session_state["render_count"] = count

    @property
    def loaded(self) -> bool:
        return st.session_state.get("loaded", False)

    @loaded.setter
    def loaded(self, v: bool):
        st.session_state["loaded"] = v

    @property
    def solution(self) -> Solution | None:
        match st.session_state.get("solution", None):
            case Solution() as sol:
                return sol
            case _:
                return None

    @solution.setter
    def solution(self, sol: Solution | None):
        st.session_state["solution"] = sol

    @property
    def delay_refresh(self) -> bool:
        return st.session_state.get("delay_refresh", False)

    @delay_refresh.setter
    def delay_refresh(self, v: bool):
        st.session_state["delay_refresh"] = v

    @property
    def refreshed(self) -> bool:
        return st.session_state.get("refreshed", True)

    @refreshed.setter
    def refreshed(self, v: bool):
        st.session_state["refreshed"] = v

    @property
    def solve_count(self) -> int:
        return st.session_state.get("solve_count", 0)

    @solve_count.setter
    def solve_count(self, c: int):
        st.session_state["solve_count"] = c


ss: Final = SessionState()


def st_ivec(ivec: Ivec):
    df = pd.DataFrame(
        [
            {
                "i/min": 60 * ips,
                "item": name,
            }
            for (name, ips) in sorted(summarize_ivec(ivec).items())
        ]
    )

    # NOTE polars is in general faster, but shouldnt matter much here
    # and polars doesnt seem to work with styling
    st.table(
        df.style.format(
            {
                "i/min": colored("{:.1f}"),
            }
        ),
        border="horizontal",
    )


def callback(fn: Callable[[], None]) -> Callable[[], None]:
    """statically makes sure the callback has no arguments left unset"""
    return fn


def add_building(block_uuid: str, name: Bname | None, count: int | None):
    uuid = uuid4().hex
    ss.buildings.setdefault(block_uuid, []).append(uuid)
    match name, count:
        case Bname(), int():
            ss.set_building_name(uuid, name)
            ss.set_building_count(uuid, count)
        case _:
            pass


def delete_building(block_uuid: str, building_uuid: str):
    ss.buildings.get(block_uuid, []).remove(building_uuid)


def st_select_block():
    with hcontainer(vertical_alignment="bottom"):
        block_name = st.selectbox(
            "select or create block",
            sorted(ss.blocks),
            accept_new_options=True,
            key=ss.key_block_name,
            width=300,
        )

        def remove_block():
            ss.blocks.pop(block_name or "", "")
            [ss.block_name, *_] = sorted(ss.blocks) or [None]

        st.button(
            "remove block",
            key="remove block",
            disabled=block_name is None,
            on_click=callback(remove_block),
        )

    if block_name is None:
        return

    if block_name not in ss.blocks:
        ss.blocks[block_name] = uuid4().hex
        st.rerun()


def ensure_state():
    # NOTE just reading st.session_state doesnt make data persist, you have to set it too

    ss.loaded = True

    ss.revision = ss.revision

    blocks = ss.blocks
    if not blocks:
        blocks = {"main": uuid4().hex}
    ss.blocks = blocks

    buildings = ss.buildings
    ss.buildings = buildings

    for block_uuid in blocks.values():
        for building_uuid in buildings.setdefault(block_uuid, []):
            name = ss.get_building_name(building_uuid)
            ss.set_building_name(building_uuid, name)

            count = ss.get_building_count(building_uuid)
            ss.set_building_count(building_uuid, count)

            if name is not None:
                takes = ss.get_building_takes(building_uuid, name)
                ss.set_building_takes(building_uuid, name, takes)

    ss.render_count = ss.render_count
    ss.loaded = ss.loaded
    ss.solution = ss.solution
    ss.refreshed = ss.refreshed
    ss.solve_count = ss.solve_count


def maybe_get_state_from_url():
    if ss.loaded:
        return

    match st.query_params.get("state", None):
        case None:
            return
        case str(base):
            try:
                compressed = b64decode(base.encode())
                state_json = zlib.decompress(compressed).decode()
                state = json.loads(state_json)
            except Exception:
                st.warning(
                    "Cannot load state from url. The value of `state` is not a valid data."
                )
                return
        case _:
            st.warning("Cannot load state from url. The value of `state` is not `str`.")
            return

    st.session_state.update(state)

    st.toast("Loaded state from url.")


def set_url_from_state():
    state = {
        key: value
        for (key, value) in st.session_state.items()
        if str(key).startswith("state")
    }
    state_json = json.dumps(state)
    compressed = zlib.compress(state_json.encode())
    base = b64encode(compressed).decode()
    st.query_params["state"] = base


def st_meta(block_uuid: str):
    sol = ss.solution
    if sol is None:
        sol = Solution.from_empty()
    match sol.block_indices.get(block_uuid, None):
        case None:
            return
        case int(i):
            pass
    with st.expander("imports", expanded=True):
        st_ivec(
            isum(alloc.take_remote for alloc in sol.allocated[i]),
        )
    with st.expander("local", expanded=True):
        st_ivec(
            isum(alloc.make_local() for alloc in sol.allocated[i]),
        )
    with st.expander("exports", expanded=True):
        st_ivec(
            isum(alloc.make_remote() for alloc in sol.allocated[i]),
        )


def st_block():
    if ss.block_name is None:
        st.warning("No block selected.")
        return

    block_uuid = ss.blocks[ss.block_name]

    meta, buildings = st.columns([1, 4], gap="medium")

    with meta:
        st_meta(block_uuid)

    with buildings:
        st_buildings(block_uuid)


def colored(m: str) -> str:
    if ss.refreshed:
        return m
    return f":gray[{m}]"


# NOTE so far this doesnt seem expensive, but in the end there is really only one global order that we could take a subset of instead of recomputing everytime
def get_topological_order(block_uuid: str) -> list[str]:
    def is_dependency(uuid: str, ouuid: str) -> bool:
        name = ss.get_building_name(uuid)
        if name is None:
            return False
        oname = ss.get_building_name(ouuid)
        if oname is None:
            return False
        takes = set(ss.get_building_takes(uuid, name))
        obuilding = building_from_name(oname)
        omakes = obuilding.get_make_items()
        return bool(takes & omakes)

    uuids = set(ss.buildings[block_uuid])
    dependencies = {
        uuid: {
            ouuid for ouuid in uuids if not ouuid == uuid and is_dependency(uuid, ouuid)
        }
        for uuid in uuids
    }
    # NOTE would be nicer to prefer direct stuff closer, like ->tree and tree->log
    ordered: list[str] = []
    while uuids:
        ready = {uuid for uuid in uuids if not (dependencies[uuid] & uuids)}
        assert ready
        ordered.extend(sorted(ready, key=lambda uuid: ss.get_building_name(uuid) or ""))
        uuids = uuids - ready
    return list(reversed(ordered))


def st_buildings(block_uuid: str):
    match ss.solution:
        case None:
            sol = Solution.from_empty()
        case Solution() as sol:
            pass

    with st.container(gap="xxsmall"):
        for building_uuid in get_topological_order(block_uuid):
            st_building(block_uuid, building_uuid, sol)

        with st.container(horizontal=True):
            st.button(
                "add building",
                key="add building",
                on_click=callback(partial(add_building, block_uuid, None, None)),
            )

            if block_uuid in sol.block_indices:
                i = sol.block_indices[block_uuid]
                block = sol.blocks[i]
                all_take = {
                    item for building in block for item in building.building.takes
                }
                all_make = {
                    item for building in block for item in building.building.makes
                }
                missing_items = all_take - all_make
                for bname in Bname:
                    building = building_from_name(bname)
                    if missing_items & building.get_make_items():
                        st.button(
                            f":material/add: {bname.value}",
                            key=f"add building {bname}",
                            type="tertiary",
                            on_click=callback(
                                partial(add_building, block_uuid, bname, 1)
                            ),
                        )


def st_building(block_uuid: str, building_uuid: str, sol: Solution):
    with hcontainer(vertical_alignment="center", border=False):
        st.number_input(
            "count",
            key=ss.key_building_count(building_uuid),
            min_value=0,
            label_visibility="collapsed",
            width=150,
        )

        with st.container(width=140, horizontal=True):
            match sol.building_indices.get(building_uuid, None):
                case None:
                    st.markdown(colored(":material/more_horiz:"))
                case (int(i), int(j)):
                    building = sol.blocks[i][j]
                    alloc = sol.allocated[i][j]
                    if building.count == 0:
                        st.markdown(colored(":material/warning:"))
                    elif (
                        math.ceil(building.count * alloc.stable_usage) < building.count
                    ):
                        st.markdown(colored(":material/remove:"))
                    elif alloc.is_infinite:
                        st.markdown(colored(":material/all_inclusive:"))
                    elif alloc.stable_usage < 1.0:
                        st.markdown(colored(":material/check:"))
                    else:
                        st.markdown(colored(":material/add:"))
                    st.markdown(
                        colored(f"**{round(alloc.stable_usage * 100)}%**"),
                        width=40,
                        text_alignment="right",
                    )
                    st.markdown(
                        colored(
                            f":small[+{round((alloc.flood_usage - alloc.stable_usage) * 100)}%]"
                        ),
                        width=40,
                        text_alignment="right",
                    )

        name = st.selectbox(
            "name",
            sorted(i.value for i in Bname),
            index=None,
            key=ss.key_building_name(building_uuid),
            label_visibility="collapsed",
            width=250,
        )
        bname = None if name is None else Bname(name)
        building = None if bname is None else building_from_name(bname)

        with st.popover(
            ":material/settings:",
            key=f"building[{building_uuid}].settings",
            disabled=bname is None,
            on_change="rerun",
        ) as c:
            if c.open:
                if bname is not None and building is not None:
                    take_items = sorted(i.value for i in building.get_take_items())
                    st.pills(
                        "takes",
                        take_items,
                        selection_mode="multi",
                        default=take_items,
                        key=f"state.building[{building_uuid}].settings.{bname}.takes",
                    )

        st.button(
            ":material/delete:",
            key=f"remove building[{building_uuid}]",
            on_click=callback(partial(delete_building, block_uuid, building_uuid)),
        )

        if bname is not None and building is not None:
            # TODO should use solution here, we dont always make all of them, or take all of them
            take_items = [i.value for i in ss.get_building_takes(building_uuid, bname)]
            make_items = [i.value for i in building.get_make_items()]
            st.code(
                " + ".join(take_items or ["∅"])
                + " -> "
                + " + ".join(make_items or ["∅"]),
                language=None,
            )


def get_blocks() -> tuple[
    list[list[BuildingCount]],
    dict[str, int],
    dict[str, tuple[int, int]],
    dict[str, Bname],
]:
    def count(uuid: str) -> BuildingCount | None:
        name = ss.get_building_name(uuid)
        if name is None:
            return None
        count = ss.get_building_count(uuid)
        takes = ss.get_building_takes(uuid, name)
        building = building_from_name(name)
        return BuildingCount(
            count,
            ConfiguredGenericBuilding(
                building,
                set(takes),
                building.get_make_items(),
                1.0,
            ),
        )

    blocks = {
        block_uuid: {
            building_uuid: count(building_uuid)
            for building_uuid in ss.buildings[block_uuid]
        }
        for block_uuid in ss.blocks.values()
    }

    blocks = {
        block_uuid: {
            uuid: building for uuid, building in block.items() if building is not None
        }
        for block_uuid, block in blocks.items()
    }

    block_indices = {uuid: i for i, uuid in enumerate(blocks)}

    building_indices = {
        uuid: (i, j)
        for i, block in enumerate(blocks.values())
        for j, uuid in enumerate(block)
    }

    blocks = [list(block.values()) for block in blocks.values()]

    building_names = {
        uuid: blocks[i][j].building.building.name
        for uuid, (i, j) in building_indices.items()
    }

    return blocks, block_indices, building_indices, building_names


def st_totals(sol: Solution):
    with st.container():
        st.subheader("total exports")
        st_ivec(
            isum(alloc.make_remote() for block in sol.allocated for alloc in block),
        )


def maybe_get_resume() -> tuple[
    list[list[BuildingCount]],
    dict[str, int],
    dict[str, tuple[int, int]],
    dict[str, Bname],
    ResumeState | None,
]:
    blocks, block_indices, building_indices, building_names = get_blocks()
    match ss.solution:
        case Solution() as sol:
            if (
                # TODO we should actually check order, not just set-like equality
                # TODO make get_blocks return an opaque signature instead? no its kinda double-purpose
                block_indices == sol.block_indices
                and building_indices == sol.building_indices
                and building_names == sol.building_names
            ):
                resume = sol.resume
            else:
                resume = None
        case None:
            resume = None
    return blocks, block_indices, building_indices, building_names, resume


def get_solution() -> Solution:
    blocks, block_indices, building_indices, building_names, resume = maybe_get_resume()
    allocated, status, resume = solve(blocks, resume)
    # TODO set revision?
    return Solution(
        1,
        blocks,
        block_indices,
        building_indices,
        building_names,
        allocated,
        status,
        resume,
    )


# NOTE a hack that could work: https://gist.github.com/Alyxion/7880aaa0c9f6036c23d94461d3a8fa6c
# but streamlit is working on adding background tasks anyway, lets wait
# and recently async is also possible, if we want to go this way
@st.fragment(run_every=0.1)
def st_refresh():
    if ss.delay_refresh:
        ss.delay_refresh = False
        return
    ss.solution = get_solution()
    ss.refreshed = True
    ss.solve_count += 1
    st.rerun(scope="app")


def recompute_cold_start():
    blocks, block_indices, building_indices, building_names, _resume = (
        maybe_get_resume()
    )
    allocated, status, resume = solve(blocks, None)
    # TODO set revision?
    ss.solution = Solution(
        1,
        blocks,
        block_indices,
        building_indices,
        building_names,
        allocated,
        status,
        resume,
    )
    ss.refreshed = True
    ss.solve_count += 1


def st_main():
    dt = time.perf_counter_ns()

    st.set_page_config(
        page_icon=":material/table:",
        page_title="widelands planner",
        layout="wide",
    )

    maybe_get_state_from_url()
    ensure_state()
    set_url_from_state()

    ss.render_count += 1
    ss.revision = ss.revision + 1  # TODO can we do it only on actual changes?

    match ss.solution:
        case Solution() as sol:
            if ss.refreshed:
                compute_status = "Cold-start solution computed in the background."
            else:
                # TODO _blocks and co could be reused for get_solution, its not doing much anymore
                _blocks, _block_indices, _building_indices, _building_names, resume = (
                    maybe_get_resume()
                )
                if resume is None:
                    compute_status = "Solution computation delayed."
                else:
                    sol = get_solution()
                    ss.solution = sol
                    ss.refreshed = True
                    ss.solve_count += 1
                    compute_status = "Computed warm-start solution"
        case _:
            sol = get_solution()
            ss.solution = sol
            compute_status = "Computed cold-start solution."

    with st.container(border=False, gap="xxsmall"):
        st_select_block()
        st.divider()
        st_block()

    with st.sidebar:
        st_totals(sol)
        st.divider()
        if st.toggle("session statistics", key="stats", value=True):
            with st.container(gap=None):
                st.markdown(f":small[Rendered {ss.render_count} times.]")
                st.markdown(f":small[Solved {ss.solve_count} times.]")
                st.markdown(f":small[On revision {ss.revision}.]")
                dt = time.perf_counter_ns() - dt
                st.markdown(f":small[Rendered in {round(dt / 1e6)}ms]")
                st.markdown(f":small[{sol.status}]")
                st.markdown(f":small[{compute_status}]")
                st.button(
                    ":material/refresh: recompute",
                    key="recompute",
                    help="Usually a warm-start is applied to update the data. Click here to force a cold-start complete recomputation.",
                    on_click=callback(recompute_cold_start),
                    type="tertiary",
                )

    if ss.refreshed:
        ss.refreshed = False
        return

    ss.delay_refresh = True
    st_refresh()


# draft for topological sorting or something like that
# could replace the input output code block with symbols that in total form a matrix
# dots for consume, and below arrows up for giving to? empty arrows for passing thru, dot-arrow or full arrow for start?
# and we sort so that we only need arrows up?
# how to mark what are exceptions?
# symbols: https://symbl.cc/en/unicode-table/#box-drawing
#     ┓
#     ┫
#     ┃
#     ┛

# TODO problems
# ordering of buildings, finding them, and not duplicating for those where it doesnt make sense?
# adding tab, or renaming, resets to viewing the first tab
# adding a building doesnt fokus on the name selection, but maybe there are buttons for adding the right one in the first place?
# order buildings, by feed-into-order?
# when gaming out a new addition, would be nice to see the diff until "confirmed", or todo add click checkboxes
#    (almost like a new block, and then merge it in when done)
#    and/or a way for the blocks to be repeated, this is how you play it usually
# TODO when buildings are there but with 0 count, then the add/remove/inf indicators are off
# TODO we cant rename blocks right now
# TODO we cant copy blocks yet
# TODO could I have used the bind option for all the state i want in the url?

# TODO sometimes its useful to say that we have infinite food or so, early in the campaign you have to follow the script
# TODO a configurable name (like a savegame) will make bookmarking easier, or configurable to add the datetime, so you can just always bookmark into a folder
# TODO could think about buildings that are attached to each other, like forester and woodcutter? otherwise you have to waste the block level for that
# TODO clay is also a bit infinite, its both consumed and used, is there a way to indicate that?
# TODO could also indicate the usage percentage local vs remote? how to know if we need more for local reasons only but we do have enough generally?

if __name__ == "__main__":
    # NOTE this would be better, but streamlit's magic fails to do reloads correctly then
    # from widelands_planner.app import main

    st_main()

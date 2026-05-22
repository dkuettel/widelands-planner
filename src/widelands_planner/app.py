from __future__ import annotations

import json
import math
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial, wraps
from typing import Concatenate, Final, Protocol, override
from uuid import uuid4

import pandas as pd  # pyright: ignore[reportMissingTypeStubs]
import streamlit as st
from streamlit.delta_generator import DeltaGenerator

from widelands_planner.app_data import Solution, State
from widelands_planner.state import (
    Allocated,
    Bname,
    BuildingCount,
    ConfiguredGenericBuilding,
    Item,
    Ivec,
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

    # TODO polars is better, but styling doesnt work with st.table
    # but we could just use polars to inject html? more control
    # it just needs some work to fit into the streamlit visual design
    st.table(  # pyright: ignore[reportUnknownMemberType]
        df.style.format(  # pyright: ignore[reportUnknownMemberType]
            {
                "i/min": colored("{:.1f}"),
            }
        ),
        border="horizontal",
    )


def add_building(block_uuid: str):
    state = get_state()
    state.buildings.setdefault(block_uuid, []).append(uuid4().hex)


def delete_building(block_uuid: str, building_uuid: str):
    state = get_state()
    state.buildings.get(block_uuid, []).remove(building_uuid)


def st_select_block():
    state = get_state()

    with hcontainer(vertical_alignment="bottom"):
        block_name = st.selectbox(
            "select or create block",
            sorted(state.blocks),
            accept_new_options=True,
            key=key_block_name,
            width=300,
        )

        def remove_block():
            state = get_state()
            state.blocks.pop(block_name or "", "")
            [new_block_name, *_] = sorted(state.blocks) or [None]
            state_set_block_name(new_block_name)

        st.button(
            "remove block",
            key="remove block",
            disabled=block_name is None,
            on_click=remove_block,
        )

    if block_name is None:
        return

    if block_name not in state.blocks:
        state.blocks[block_name] = uuid4().hex
        st.rerun()


def get_state() -> State:
    match st.session_state.get("state", None):
        case None:
            return State.from_new()
        case State() as state:
            return state
        case _ as what:
            assert False, what


key_block_name: Final = "block_name"


def state_get_block_name() -> str | None:
    return st.session_state.get(key_block_name, None)


def state_set_block_name(value: str | None):
    """current block uuid to show"""
    st.session_state[key_block_name] = value


def state_get_building_name(uuid: str) -> None | Bname:
    value = st.session_state.get(f"building[{uuid}].name", None)
    match value:
        case None:
            return None
        case str():
            if value in Bname:
                return Bname(value)
            return None
        case _:
            return None


def state_set_building_name(uuid: str, value: None | Bname):
    match value:
        case None:
            st.session_state[f"building[{uuid}].name"] = None
        case Bname():
            st.session_state[f"building[{uuid}].name"] = value.value


def state_get_building_count(uuid: str) -> int:
    value = st.session_state.get(f"building[{uuid}].count", 0)
    match value:
        case int():
            return value
        case _:
            return 0


def state_set_building_count(uuid: str, value: int):
    st.session_state[f"building[{uuid}].count"] = value


def state_get_building_takes(uuid: str, name: Bname) -> list[Item]:
    value = st.session_state.get(f"building[{uuid}].settings.{name}.takes", None)
    match value:
        case list():
            value = list(map(str, value))  # pyright: ignore[reportUnknownArgumentType]
            if all((i in Item) for i in value):
                return sorted(Item(i) for i in value)
            building = building_from_name(name)
            return sorted(building.get_take_items())
        case None | _:
            building = building_from_name(name)
            return sorted(building.get_take_items())


def state_set_building_takes(uuid: str, name: Bname, value: list[Item]):
    st.session_state[f"building[{uuid}].settings.{name}.takes"] = [
        i.value for i in value
    ]


def ensure_state():
    # NOTE just reading st.session_state doesnt make data persist, you have to set it too

    state = get_state()
    st.session_state["state"] = state

    if not state.blocks:
        state.blocks = {"main": uuid4().hex}

    for block_uuid in state.blocks.values():
        for building_uuid in state.buildings.setdefault(block_uuid, []):
            name = state_get_building_name(building_uuid)
            state_set_building_name(building_uuid, name)

            count = state_get_building_count(building_uuid)
            state_set_building_count(building_uuid, count)

            if name is not None:
                takes = state_get_building_takes(building_uuid, name)
                state_set_building_takes(building_uuid, name, takes)


def maybe_get_session_from_url():
    if "state" in st.session_state:
        return

    match st.query_params.get("session", None):
        case None:
            return
        case str(session_str):
            try:
                # TODO check more with msgspec or so
                session = json.loads(session_str)
            except json.decoder.JSONDecodeError:
                st.warning(
                    "Cannot load state from url. The value of `session` is not a valid json."
                )
                return
        case _:
            st.warning(
                "Cannot load state from url. The value of `session` is not `str`."
            )
            return

    st.session_state["state"] = State.from_session(session.pop("state"))

    # TODO is this a security problem that we just allow any state to be updated?
    st.session_state.update(session)


def set_url_from_session():
    # TODO instead make all strings "state...." and then much easier to load and save?
    def is_session(key: str | int) -> bool:
        key = str(key)
        # if key in {"block_entries"}:
        #     return True
        # if key.startswith("building_entries["):
        #     return True
        if key.startswith("building["):
            return True
        return False

    session = {
        key: value for (key, value) in st.session_state.items() if is_session(key)
    }
    session["state"] = get_state().as_session()
    # TODO we could also just make it one big compressed base64 or so
    session_str = json.dumps(session)
    # TODO if this is slow, only do it on a toggle
    st.query_params["session"] = session_str


class Backfill(Protocol):
    def __call__(self, sol: Solution):
        pass


@dataclass(frozen=True)
class BackfillMeta(Backfill):
    block_uuid: str
    meta: DeltaGenerator

    @override
    def __call__(self, sol: Solution):
        with self.meta.container():
            i = sol.block_indices[self.block_uuid]
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


def st_meta(sol: Solution, block_uuid: str):
    with st.container():
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


@dataclass
class Fill:
    sol: Solution
    runs: list[Callable[[Solution], None]]

    def __call__[**P](
        self, container: DeltaGenerator, fn: Callable[Concatenate[Solution, P], None]
    ) -> Callable[P, None]:
        container = container.empty()

        @wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs):
            def run(sol: Solution):
                with container:
                    fn(sol, *args, **kwargs)

            self.runs.append(run)
            run(self.sol)

        return wrapper


def st_block(fill: Fill):
    block_name = state_get_block_name()
    if block_name is None:
        st.warning("No block selected.")
        return

    state = get_state()
    block_uuid = state.blocks[block_name]

    meta, buildings = st.columns([1, 4], gap="medium")

    fill(meta, st_meta)(block_uuid)

    with buildings:
        # TODO this is pretty heavy, widgets are expensive
        # so we could make fragments here? and just use as little as possible
        # use non-eager popovers and stuff like that
        st_block_buildings(
            block_uuid,
            fill.sol.blocks,
            fill.sol.block_indices,
            fill.sol.building_indices,
            fill.sol.allocated,
        )


def colored(m: str) -> str:
    refreshed: bool = st.session_state.get("refreshed", False)
    if refreshed:
        return m
    return f":gray[{m}]"


def st_block_buildings(
    block_uuid: str,
    blocks: list[list[BuildingCount]],
    block_indices: dict[str, int],
    building_indices: dict[str, tuple[int, int]],
    allocated: list[list[Allocated]],
):
    state = get_state()
    building_entries = state.buildings[block_uuid]

    with st.container(gap="xxsmall"):
        for building_uuid in building_entries:
            with hcontainer(vertical_alignment="center", border=False):
                st.number_input(
                    "count",
                    key=f"building[{building_uuid}].count",
                    min_value=0,
                    label_visibility="collapsed",
                    width=150,
                )

                with st.container(width=140, horizontal=True):
                    match building_indices.get(building_uuid, None):
                        case None:
                            st.markdown(colored(":material/more_horiz:"))
                        case (int(i), int(j)):
                            building = blocks[i][j]
                            alloc = allocated[i][j]
                            if building.count == 0:
                                st.markdown(colored(":material/warning:"))
                            elif (
                                math.ceil(building.count * alloc.stable_usage)
                                < building.count
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

                # TODO this one is also slow, not much to do? dont sort everytime?
                name = st.selectbox(
                    "name",
                    sorted(i.value for i in Bname),
                    index=None,
                    key=f"building[{building_uuid}].name",
                    label_visibility="collapsed",
                    width=250,
                )
                bname = None if name is None else Bname(name)
                building = None if bname is None else building_from_name(bname)

                # TODO lazy eval for speed? yes we should, every widget counts
                with st.popover(
                    ":material/settings:",
                    key=f"building[{building_uuid}].settings",
                    disabled=bname is None,
                    on_change="rerun",
                ) as c:
                    if c.open:
                        if bname is not None and building is not None:
                            items = sorted(i.value for i in building.get_take_items())
                            st.pills(
                                "takes",
                                items,
                                selection_mode="multi",
                                default=items,
                                key=f"building[{building_uuid}].settings.{bname}.takes",
                            )

                st.button(
                    ":material/delete:",
                    key=f"remove building[{building_uuid}]",
                    on_click=partial(delete_building, block_uuid, building_uuid),
                )

                if bname is not None and building is not None:
                    items = st.session_state.get(
                        f"building[{building_uuid}].settings.{bname}.takes", []
                    )
                    st.code(
                        " + ".join(items)
                        + " -> "
                        # TODO should do it after the fact, because we dont produce all, depends on what we take
                        + " + ".join(i.value for i in building.get_make_items()),
                        language=None,
                    )

        with st.container(horizontal=True):
            # TODO actually doing the if, and not the callback, requires 2 reruns
            st.button(
                "add building",
                key="add building",
                on_click=partial(add_building, block_uuid),
            )

            if block_uuid in block_indices:
                i = block_indices[block_uuid]
                block = blocks[i]
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
                        if st.button(
                            f":material/add: {bname.value}",
                            key=f"add building {bname}",
                            type="tertiary",
                        ):
                            building_entries = st.session_state.get(
                                f"building_entries[{block_uuid}]", []
                            )
                            uuid = uuid4().hex
                            building_entries.append(uuid)
                            st.session_state[f"building_entries[{block_uuid}]"] = (
                                building_entries
                            )
                            st.session_state[f"building[{uuid}].name"] = bname.value
                            st.session_state[f"building[{uuid}].count"] = 1
                            st.rerun()


def get_blocks() -> tuple[
    list[list[BuildingCount]],
    dict[str, int],
    dict[str, tuple[int, int]],
]:
    def count(uuid: str) -> BuildingCount | None:
        name = state_get_building_name(uuid)
        if name is None:
            return None
        count = state_get_building_count(uuid)
        takes = state_get_building_takes(uuid, name)
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

    state = get_state()

    blocks = {
        block_uuid: {
            building_uuid: count(building_uuid)
            for building_uuid in state.buildings[block_uuid]
        }
        for block_uuid in state.blocks.values()
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

    return blocks, block_indices, building_indices


def st_totals(sol: Solution):
    with st.container():
        st.subheader("total exports")
        st_ivec(
            isum(alloc.make_remote() for block in sol.allocated for alloc in block),
        )
        st.divider()
        st.markdown(f":small[{sol.status}]")


# a hack that could work: https://gist.github.com/Alyxion/7880aaa0c9f6036c23d94461d3a8fa6c
# but streamlit is working on adding background tasks anyway, lets wait
@st.fragment(run_every=0.1)
def st_refresh():
    # TODO this is a very cheap way to get a background process, it only happens once, but is detached
    # if on rapid fire reruns (clicking much) we could hold back somehow, that would be best
    # i think this gets killed maybe? but we could still check at the end if we are still relevant?
    if st.session_state.get("first", False):
        st.session_state["first"] = False
        return
    blocks, block_indices, building_indices = get_blocks()
    allocated, status = solve(blocks)
    sol = Solution(1, blocks, block_indices, building_indices, allocated, status)
    st.session_state["last_solution"] = sol
    st.session_state["refreshed"] = True
    st.session_state["solved"] = st.session_state.get("solved", 0) + 1
    st.rerun(scope="app")


def st_main():
    with st.sidebar:
        count = st.session_state.get("render_count", 0) + 1
        st.session_state["render_count"] = count
        st.markdown(f":small[Rendered {count} times.]")
        solved = st.session_state.get("solved", 0)
        st.markdown(f":small[Solved {solved} times.]")

    dt = time.perf_counter_ns()

    st.set_page_config(
        page_icon=":material/table:",
        page_title="widelands planner",
        layout="wide",
    )

    maybe_get_session_from_url()
    ensure_state()
    set_url_from_session()

    # TODO find a way to resume iterations, most of the time this should be quite cheap?
    # actually wait, first we should see what happens if we keep the last state and solution
    # and compute at the end and rerun if necessary? could be smooth enough? or no rerun but a backfill? is that possible easy and no flickering?
    # reruns by everyone adding to a backfill list, then its the same function applied twice, does st flicker like that?

    # TODO accessor for better typing?
    # TODO also, just have one state class, faster to work with, keep keys only for widgets
    match st.session_state.get("last_solution", None):
        case Solution() as sol:
            # TODO sol.status should say cached or so
            st.info("loaded")
            pass
        case _:
            # TODO repeated code with below
            blocks, block_indices, building_indices = get_blocks()
            allocated, status = solve(blocks)
            sol = Solution(
                1, blocks, block_indices, building_indices, allocated, status
            )
            st.session_state["last_solution"] = sol
            st.warning("computed")

    fill = Fill(sol, [])

    with st.container(border=False, gap="xxsmall"):
        st_select_block()
        st.divider()
        st_block(fill)

    with st.sidebar:
        fill(st.empty(), st_totals)()

        dt = time.perf_counter_ns() - dt
        st.markdown(f":small[Rendered in {round(dt / 1e6)}ms]")

    if st.session_state.get("refreshed", False):
        st.session_state["refreshed"] = False
        return

    # TODO even with a return here it seems a bit slow, how is that possible?
    # ahh no didnt save last state ... or wait? first time we do and then it should be there?
    # see to line profile this function?
    # return

    # TODO more flat structures again
    # trust your intuition when it feels smart but too complicated
    # just make fill(partial(st_meta, todo))
    # so that you can stick with st_meta(sol, todo), no heavy assumptions

    # TODO would st.rerun work better? we would remove old elements because we ended, and then update again when ready?
    #      could be nicer, then just the damn backfill was for nothing :)
    #      well actually, it takes the same as long, so we would need to run the solution in the bg for snappyness
    # TODO iterative?
    # blocks, block_indices, building_indices = get_blocks()
    # allocated, status = solve(blocks)
    # sol = Solution(blocks, block_indices, building_indices, allocated, status)
    # st.session_state["last_solution"] = sol
    # st.session_state["refreshed"] = True
    # st.rerun()

    # TODO the page still seems to not consider things done
    # is there a way for a real background task?
    # run_every detaches it, but the first run still prevents finishing a render
    st.session_state["first"] = True
    st_refresh()

    # TODO also @st.cache_data functions can contain st statements, will that make some static content faster?
    # and @st.cache_data(experimental_allow_widgets=True) if you want interactive ones too, see if it gives a speedup?

    # for run in fill.runs:
    #     run(sol)


# TODO problems
# ordering of buildings, finding them, and not duplicating for those where it doesnt make sense?
# adding tab, or renaming, resets to viewing the first tab
# adding a building doesnt fokus on the name selection, but maybe there are buttons for adding the right one in the first place?
# save all the time, keep a timeline? save version to load old stuff?
# order buildings, by feed-into-order?
# when gaming out a new addition, would be nice to see the diff until "confirmed", or todo add click checkboxes
#    (almost like a new block, and then merge it in when done)
#    and/or a way for the blocks to be repeated, this is how you play it usually
# TODO when buildings are there but with 0 count, then the add/remove/inf indicators are off

if __name__ == "__main__":
    # NOTE this would be better, but streamlit's magic fails to do reloads correctly then
    # from widelands_planner.app import main

    st_main()

from __future__ import annotations

import json
import math
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from enum import StrEnum
from functools import partial
from pathlib import Path
from typing import assert_never
from uuid import uuid4

import pandas as pd
import streamlit as st

from widelands_planner import state


@dataclass(frozen=True)
class StrState:
    key: str
    default: str

    def get(self) -> str:
        return st.session_state.setdefault(self.key, self.default)

    def set(self, value: str):
        st.session_state[self.key] = value


@dataclass(frozen=True)
class IntState:
    key: str
    default: int

    def get(self) -> int:
        return st.session_state.setdefault(self.key, self.default)

    def set(self, value: int):
        st.session_state[self.key] = value


@dataclass(frozen=True)
class FloatState:
    key: str
    default: float

    def get(self) -> float:
        return st.session_state.setdefault(self.key, self.default)

    def set(self, value: float):
        st.session_state[self.key] = value


@dataclass(frozen=True)
class EnumState[T: StrEnum]:
    key: str
    ty: type[T]
    default: T

    def get(self) -> T:
        return st.session_state.setdefault(self.key, self.default)


@dataclass(frozen=True)
class SetState[T: StrEnum]:
    key: str
    ty: type[T]

    def get(self, default: set[T]) -> set[T]:
        return set(st.session_state.setdefault(self.key, list(default)))

    def set(self, value: set[T]):
        st.session_state[self.key] = list(value)


@dataclass(frozen=True)
class CountState:
    parent: BlockCountState
    id: str
    count: IntState
    bname: EnumState[state.Bname]
    takes: SetState[state.Item]
    makes: SetState[state.Item]
    speed: FloatState

    @classmethod
    def from_key(cls, parent: BlockCountState, id: str, key: str):
        return cls(
            parent=parent,
            id=id,
            count=IntState(f"{key}.count", 0),
            # TODO could there be a none building?
            bname=EnumState(f"{key}.bname", state.Bname, state.Bname.fishers_house),
            takes=SetState(f"{key}.takes", state.Item),
            makes=SetState(f"{key}.makes", state.Item),
            speed=FloatState(f"{key}.speed", 1),
        )

    def remove_fn(self):
        return partial(self.parent.ids.remove, self.id)


@dataclass(frozen=True)
class BlockCountState:
    key: str
    ids: StrListState

    def __getitem__(self, id: str) -> CountState:
        return CountState.from_key(self, id, f"{self.key}.items.{id}")

    def __iter__(self) -> Iterator[CountState]:
        for id in self.ids.get():
            yield self[id]

    @classmethod
    def from_key(cls, key: str):
        return cls(
            key=key,
            ids=StrListState(f"{key}.ids"),
        )

    def add_fn(self):
        return self.ids.add


@dataclass(frozen=True)
class BlockState:
    parent: BlocksState
    id: str
    name: StrState
    counts: BlockCountState

    @classmethod
    def from_key(cls, parent: BlocksState, id: str, key: str):
        return cls(
            parent=parent,
            id=id,
            name=StrState(f"{key}.name", "unnamed block"),
            counts=BlockCountState.from_key(key),
        )

    def remove_fn(self):
        return partial(self.parent.ids.remove, self.id)


@dataclass(frozen=True)
class StrListState:
    key: str

    def get(self) -> list[str]:
        return st.session_state.setdefault(self.key, [])

    def add(self):
        id = uuid4().hex
        self.get().append(id)

    def remove(self, value: str):
        self.get().remove(value)


@dataclass(frozen=True)
class BlocksState:
    key: str
    ids: StrListState

    def __getitem__(self, id: str) -> BlockState:
        return BlockState.from_key(self, id, f"{self.key}.items.{id}")

    def __iter__(self) -> Iterator[BlockState]:
        for id in self.ids.get():
            yield self[id]

    @classmethod
    def from_key(cls, key: str):
        return cls(
            key=key,
            ids=StrListState(f"{key}.ids"),
        )


@dataclass(frozen=True)
class SessionState:
    blocks: BlocksState

    @classmethod
    def from_key(cls, key: str = "state"):
        return cls(BlocksState.from_key(f"{key}.blocks"))


def save_state(path: Path | None = None):
    path = Path("./state.json")
    state = {
        k: v
        for (k, v) in st.session_state.items()
        if isinstance(k, str) and k.startswith("state.")
    }
    state = dict(sorted(state.items()))
    path.write_text(json.dumps(state, indent="  "))


def load_state(path: Path | None = None):
    path = Path("./state.json")
    state = json.loads(path.read_text())
    st.session_state.update(state)


def st_ivec(ivec: state.Ivec):
    df = pd.DataFrame(
        [
            {
                "i/min": 60 * ips,
                "item": i.name,
            }
            for (i, ips) in ivec.sorted()
        ]
    )

    # TODO polars is better, but styling doesnt work with st.table
    # but we could just use polars to inject html? more control
    # it just needs some work to fit into the streamlit visual design
    st.table(  # pyright: ignore[reportUnknownMemberType]
        df.style.format(
            {
                "i/min": "{:.1f}",
            }
        ),
        border="horizontal",
    )


def key_block_ids() -> str:
    return "state.blocks.ids"


def key_block_name(block_id: str) -> str:
    return f"state.blocks.items.{block_id}.name"


def key_block_remove(block_id: str) -> str:
    return f"state.blocks.items.{block_id}.remove"


def key_count_ids(block_id: str) -> str:
    return f"state.blocks.items.{block_id}.counts.ids"


def key_count(block_id: str, count_id: str) -> str:
    return f"state.blocks.items.{block_id}.counts.items.{count_id}.count"


def key_count_add(block_id: str) -> str:
    return f"state.blocks.items.{block_id}.add"


def key_count_remove(block_id: str, count_id: str) -> str:
    return f"state.blocks.items.{block_id}.counts.items.{count_id}.remove"


def key_bname(block_id: str, count_id: str) -> str:
    return f"state.blocks.items.{block_id}.counts.items.{count_id}.bname"


def key_takes(block_id: str, count_id: str) -> str:
    return f"state.blocks.items.{block_id}.counts.items.{count_id}.takes"


def key_imports(block_id: str) -> str:
    return f"state.blocks.items.{block_id}.counts.items.imports"


def key_exports(block_id: str) -> str:
    return f"state.blocks.items.{block_id}.counts.items.exports"


def get[T](key: str, _ty: type[T], default: T) -> T:
    value = st.session_state.setdefault(key, default)
    # TODO check type better
    # assert isinstance(value, ty)
    return value


def get_block_ids() -> list[str]:
    return get(key_block_ids(), list[str], [])


def add_block():
    id = uuid4().hex
    get(key_block_ids(), list[str], []).append(id)


def remove_block(id: str):
    get(key_block_ids(), list[str], []).remove(id)


def get_count_ids(block_id: str) -> list[str]:
    return get(key_count_ids(block_id), list[str], [])


def add_count(block_id: str):
    count_id = uuid4().hex
    get(key_count_ids(block_id), list[str], []).append(count_id)


def remove_count(block_id: str, count_id: str):
    get(key_count_ids(block_id), list[str], []).remove(count_id)


def get_count(block_id: str, count_id: str) -> int:
    return get(key_count(block_id, count_id), int, 0)


def get_bname(block_id: str, count_id: str) -> state.Bname:
    # TODO does this return str or a Bname?
    return get(key_bname(block_id, count_id), state.Bname, state.Bname.fishers_house)


def get_takes(
    block_id: str, count_id: str, default: set[state.Item]
) -> set[state.Item]:
    return set(get(key_takes(block_id, count_id), list[state.Item], list(default)))


def get_state(
    session: SessionState,
    buildings: Mapping[state.Bname, state.Building],
) -> tuple[list[state.BlockBalance], state.Ivec]:
    balances = [get_state_block(buildings, block) for block in session.blocks]
    balance = state.get_global_balance(balances)
    return balances, balance


def get_state_block(
    buildings: Mapping[state.Bname, state.Building], block: BlockState
) -> state.BlockBalance:
    counts = [get_state_block_count(buildings, count) for count in block.counts]
    balance = state.get_block_balance(state.Block(counts))
    return balance


def get_state_block_count(
    buildings: Mapping[state.Bname, state.Building], count_state: CountState
) -> state.BuildingCount:
    count = count_state.count.get()
    bname = count_state.bname.get()
    building = buildings[bname]
    match building:
        case state.BaseBuilding():
            takes = count_state.takes.get(building.get_take_items())
            makes = count_state.makes.get(building.get_make_items())
            speed = count_state.speed.get()
            return state.BuildingCount(
                count,
                state.ConfiguredGenericBuilding(building, takes, makes, speed),
            )
        case _ as never:
            assert_never(never)


def fn_change_building_type(count_state: CountState):
    def fn():
        count_state.count.set(0)
        building = state.get_buildings()[count_state.bname.get()]
        match building:
            case state.BaseBuilding():
                count_state.takes.set(building.get_take_items())
                count_state.makes.set(building.get_make_items())
                count_state.speed.set(1)
            case _ as never:
                assert_never(never)

    return fn


def main():
    st.set_page_config(page_title="widelands planner", layout="wide")

    # TODO danger: state you didnt touch will not be defaulted right now
    session = SessionState.from_key()
    buildings = state.get_buildings()
    # balances, balance = get_state(session, buildings)
    bnames = sorted(state.Bname)

    blocks: list[state.Block] = []
    for block in session.blocks:
        counts = [get_state_block_count(buildings, count) for count in block.counts]
        blocks.append(state.Block(counts))

    status, block_allocations = state.fixpoint(blocks)

    with st.sidebar:
        st.subheader("global")
        with st.container(gap=None):
            st_ivec(
                state.isum(
                    alloc.make_remote()
                    for allocations in block_allocations
                    for alloc in allocations
                ),
            )
        st.divider()
        st.button("add block", on_click=add_block)
        st.divider()
        with st.container(horizontal=True):
            st.button("save", on_click=save_state)
            st.button("load", on_click=load_state)
        st.divider()
        st.markdown(f":small[{status}]")

    block_names = [block.name.get() for block in session.blocks]
    if len(block_names) == 0:
        st.write("no blocks")
    else:
        tabs = st.tabs(block_names)
        for tab, block, allocations in state.zips(
            tabs, session.blocks, block_allocations
        ):
            with tab:
                meta, counts = st.columns([1, 4], gap="medium")
                with meta:
                    with st.expander("imports", expanded=True):
                        st_ivec(
                            state.isum(alloc.take_remote for alloc in allocations),
                        )
                    with st.expander("local", expanded=True):
                        st_ivec(
                            state.isum(alloc.make_local() for alloc in allocations),
                        )
                    with st.expander("exports", expanded=True):
                        st_ivec(
                            state.isum(alloc.make_remote() for alloc in allocations),
                        )
                    with st.expander("block", expanded=False):
                        st.text_input("name", key=block.name.key)
                        st.button(
                            "remove",
                            key=f"button.block[{block.id}].remove",
                            on_click=block.remove_fn(),
                        )
                with counts, st.container(horizontal=False, border=False):
                    for count_state, alloc in state.zips(block.counts, allocations):
                        with st.container(
                            horizontal=True, border=True, vertical_alignment="center"
                        ):
                            bname = count_state.bname.get()
                            building = buildings[bname]
                            st.number_input(
                                "count",
                                key=count_state.count.key,
                                min_value=0,
                                label_visibility="collapsed",
                                width=150,
                            )
                            if (
                                math.ceil(alloc.building.count * alloc.stable_usage)
                                < alloc.building.count
                            ):
                                st.markdown(":material/remove:")
                            elif alloc.is_infinite:
                                st.markdown(":material/all_inclusive:")
                            elif alloc.stable_usage < 1.0:
                                st.markdown(":material/check:")
                            else:
                                st.markdown(":material/add:")
                            with st.container(gap=None, width=40):
                                # TODO can we show here also how much overuse in theory if too little produced? so we know how much we should add?
                                # maybe instead a button that goes into planning mode and it just plays thru until a stable situation and shows the target counts?
                                st.markdown(
                                    f"**{round(alloc.stable_usage * 100)}%**",
                                    text_alignment="right",
                                )
                                st.markdown(
                                    f":small[+{round((alloc.flood_usage - alloc.stable_usage) * 100)}%]",
                                    text_alignment="right",
                                )
                            # TODO could give hint here based on local balance?
                            # TODO show here utilization, and a mark if more needed
                            # maybe bold if potentially too much, not if exporting!
                            # utilization is total usage / production, we should have that now
                            # but what if there is more than one producing items of it?
                            # what if it produces more than one item?
                            st.selectbox(
                                "building",
                                bnames,
                                key=count_state.bname.key,
                                on_change=fn_change_building_type(count_state),
                                label_visibility="collapsed",
                                width=250,
                            )
                            with st.popover(""):
                                match building:
                                    case state.BaseBuilding():
                                        st.multiselect(
                                            "takes",
                                            sorted(building.get_take_items()),
                                            key=count_state.takes.key,
                                        )
                                        st.multiselect(
                                            "makes",
                                            sorted(building.get_make_items()),
                                            key=count_state.makes.key,
                                        )
                                    case _ as never:
                                        assert_never(never)
                                st.slider(
                                    "speed",
                                    min_value=0.0,
                                    max_value=1.0,
                                    key=count_state.speed.key,
                                    step=0.1,
                                )
                                st.button(
                                    "remove",
                                    key=f"button.block[{block.id}].count[{count_state.id}].remove",
                                    on_click=count_state.remove_fn(),
                                )
                            with st.container(
                                horizontal=True,
                                gap="small",
                                vertical_alignment="center",
                            ):
                                # TODO this is a bit unreadable still
                                st.code(
                                    ""
                                    + state.str_from_ivec(alloc.take_local.smul(60))
                                    + " + "
                                    + state.str_from_ivec(alloc.take_remote.smul(60))
                                    + " -> "
                                    + state.str_from_ivec(
                                        alloc.make_main_local.smul(60)
                                    )
                                    + "/"
                                    + state.str_from_ivec(alloc.make_aux_local.smul(60))
                                    + " + "
                                    + state.str_from_ivec(
                                        alloc.make_main_remote.smul(60)
                                    )
                                    + "/"
                                    + state.str_from_ivec(
                                        alloc.make_aux_remote.smul(60)
                                    )
                                )
                    # TODO could have buttons for all the likely candidates?
                    # and even the non-configures ones plus 1, other add and plus?
                    # but that could also be in the local meta info right next to it?
                    st.button(
                        "add building",
                        key=f"button.block[{block.id}].add",
                        on_click=block.counts.add_fn(),
                    )


# TODO problems
# ordering of buildings, finding them, and not duplicating for those where it doesnt make sense?
# adding tab, or renaming, resets to viewing the first tab
# adding a building doesnt fokus on the name selection, but maybe there are buttons for adding the right one in the first place?
# save all the time, keep a timeline? save version to load old stuff?
# order buildings, by feed-into-order?
# instead, say what blocks you want to import from? a map would almost be easier :) with a flow
# long sword, in tight production, almost always skipped because it needs 2 iron, unfortunate dynamics
# when gaming out a new addition, would be nice to see the diff until "confirmed", or todo add click checkboxes
#    (almost like a new block, and then merge it in when done)
#    and/or a way for the blocks to be repeated, this is how you play it usually
# the soldier recruitement, and eventually the recycling is harder to model well
#    almost thinking we could also try to solve for a steady state now, instead of a saturated one?
#    yes, the training could use insane amounts, and very uneven
#    or maybe we can say for those buildings what production ratio we expect?
#    for the soldiers, assuming no war, we need every level same thruput, as the first one, obviously
#    and thats partly the same building, so it would naturally just adapt and do whatever?
#    so maybe lets try a forward-wave computation

# TODO tools and weapons could be meta items, almost no use in seeing them listed individually (could that even make the optimization easier?)
# TODO right now i dont see if some things are totally missing, if there is no configured building around, it wont show +/- indicators, and also wont show take/make in the info side

if __name__ == "__main__":
    main()

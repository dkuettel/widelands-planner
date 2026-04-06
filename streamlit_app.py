from __future__ import annotations

import json
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
    usage: FloatState
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
            usage=FloatState(f"{key}.usage", 1),
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
    imports: SetState[state.Item]
    exports: SetState[state.Item]

    @classmethod
    def from_key(cls, parent: BlocksState, id: str, key: str):
        return cls(
            parent=parent,
            id=id,
            name=StrState(f"{key}.name", "unnamed block"),
            counts=BlockCountState.from_key(key),
            imports=SetState(f"{key}.imports", state.Item),
            exports=SetState(f"{key}.exports", state.Item),
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


def st_ivec(ivec: state.Ivec, hints: bool):
    def f(i: state.Item, ips: float) -> dict[str, str | float]:
        counts = state.building_count_from_ips(i, ips)
        # TODO which representative to show?
        [(_name, count), *_] = counts
        if not hints or ips >= 0:
            return {
                "item": f"{i}",
                "i/min": 60 * ips,
                "repr": count * 100,
            }
        return {
            "item": f"{i} :warning:",
            "i/min": 60 * ips,
            "repr": count * 100,
        }

    df = pd.DataFrame([f(i, ips) for (i, ips) in ivec.sorted()])
    # TODO polars is better, but styling doesnt work with st.table
    # but we could just use polars to inject html? more control
    # it just needs some work to fit into the streamlit visual design
    st.table(  # pyright: ignore[reportUnknownMemberType]
        df.style.format(
            {
                "i/min": "{:.1f}",
                "repr": lambda v: (
                    f"{v:.0f}%"
                    if (not hints or v <= 100)  # pyright: ignore[reportOperatorIssue]
                    else f"**{v:.0f}%**"
                ),
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
    imports = block.imports.get(set())
    counts = [get_state_block_count(buildings, count) for count in block.counts]
    exports = block.exports.get(set())
    balance = state.get_block_balance(state.Block(imports, counts, exports))
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
            usage = count_state.usage.get()
            speed = count_state.speed.get()
            return state.BuildingCount(
                count,
                state.ConfiguredGenericBuilding(building, takes, makes, speed),
                usage,
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
                count_state.usage.set(1)
                count_state.speed.set(1)
            case _ as never:
                assert_never(never)

    return fn


def main():
    st.set_page_config(page_title="widelands planner", layout="wide")

    session = SessionState.from_key()
    buildings = state.get_buildings()
    # TODO danger: state you didnt touch will not be defaulted right now
    balances, balance = get_state(session, buildings)
    bnames = sorted(state.Bname)
    items = state.get_items()

    with st.sidebar:
        st.subheader("global balance")
        with st.container(gap=None):
            st_ivec(balance, hints=True)
        st.divider()
        st.button("add block", on_click=add_block)
        st.divider()
        with st.container(horizontal=True):
            st.button("save", on_click=save_state)
            st.button("load", on_click=load_state)

    block_names = [block.name.get() for block in session.blocks]
    if len(block_names) == 0:
        st.write("no blocks")
    else:
        tabs = st.tabs(block_names)
        for tab, block, block_balance in zip(
            tabs, session.blocks, balances, strict=True
        ):
            with tab:
                meta, counts = st.columns([1, 4], gap="large")
                with meta:
                    with st.expander("block", expanded=False):
                        st.text_input("name", key=block.name.key)
                        st.button(
                            "remove",
                            key=f"button.block[{block.id}].remove",
                            on_click=block.remove_fn(),
                        )
                    with st.expander("imports", expanded=True):
                        st.multiselect(
                            "imports",
                            items,
                            key=block.imports.key,
                            label_visibility="collapsed",
                        )
                        st_ivec(block_balance.imports, hints=False)
                    with st.expander("local", expanded=True):
                        st_ivec(block_balance.local, hints=True)
                    with st.expander("exports", expanded=True):
                        st.multiselect(
                            "exports",
                            items,
                            key=block.exports.key,
                            label_visibility="collapsed",
                        )
                        st_ivec(block_balance.exports, hints=False)
                with counts, st.container(horizontal=True, border=False):
                    for count_state in block.counts:
                        with st.container(width=250, border=True):
                            bname = count_state.bname.get()
                            building = buildings[bname]
                            # TODO could give hint here based on local balance?
                            st.selectbox(
                                "building",
                                bnames,
                                key=count_state.bname.key,
                                on_change=fn_change_building_type(count_state),
                                label_visibility="collapsed",
                            )
                            st.number_input(
                                "count",
                                key=count_state.count.key,
                                min_value=0,
                                label_visibility="collapsed",
                            )
                            with st.popover("config"):
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
                                    "usage",
                                    min_value=0.0,
                                    max_value=1.0,
                                    key=count_state.usage.key,
                                    step=0.1,
                                )
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
# long sword, in tight production, almost always skipped because it needs to iron, unfortunate dynamics
# when gaming out a new addition, would be nice to see the diff until "confirmed", or todo add click checkboxes
#    (almost like a new block, and then merge it in when done)
#    and/or a way for the blocks to be repeated, this is how you play it usually

if __name__ == "__main__":
    main()

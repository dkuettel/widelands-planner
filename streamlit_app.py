from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum
from functools import partial
from pathlib import Path
from uuid import uuid4

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
class ButtonState:
    key: str


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


@dataclass(frozen=True)
class CountState:
    parent: BlockCountState
    id: str
    count: IntState
    remove: ButtonState
    bname: EnumState[state.Bname]
    takes: SetState[state.Item]

    @classmethod
    def from_key(cls, parent: BlockCountState, id: str, key: str):
        return cls(
            parent=parent,
            id=id,
            count=IntState(f"{key}.count", 0),
            remove=ButtonState(f"{key}.remove"),
            bname=EnumState(f"{key}.bname", state.Bname, state.Bname.fishers_houses),
            takes=SetState(f"{key}.takes", state.Item),
        )

    def remove_fn(self):
        return partial(self.parent.ids.remove, self.id)


@dataclass(frozen=True)
class BlockCountState:
    key: str
    ids: StrListState
    add: ButtonState

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
            add=ButtonState(f"{key}.add"),
        )

    def add_fn(self):
        return self.ids.add


@dataclass(frozen=True)
class BlockState:
    parent: BlocksState
    id: str
    name: StrState
    remove: ButtonState
    counts: BlockCountState
    imports: SetState[state.Item]
    exports: SetState[state.Item]

    @classmethod
    def from_key(cls, parent: BlocksState, id: str, key: str):
        return cls(
            parent=parent,
            id=id,
            name=StrState(f"{key}.name", "unnamed block"),
            remove=ButtonState(f"{key}.remove"),
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
    add: ButtonState

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
            add=ButtonState(f"{key}.add"),
        )


@dataclass(frozen=True)
class SessionState:
    blocks: BlocksState

    @classmethod
    def from_key(cls, key: str = "state"):
        return cls(BlocksState.from_key(f"{key}.blocks"))


def save_state(path: Path):
    state = {
        k: v
        for (k, v) in st.session_state.items()
        if isinstance(k, str) and k.startswith("state.")
    }
    path.write_text(json.dumps(state))


def load_state(path: Path):
    state = json.loads(path.read_text())
    st.session_state.update(state)


def st_ivec(ivec: state.Ivec):
    deficit = st.container(gap=None)
    deficit.write("**deficit**")
    surplus = st.container(gap=None)
    surplus.write("**surplus**")
    for i, ips in ivec.sorted():
        counts = state.building_count_from_ips(i, ips)
        rep = " or ".join(f"{c:.1f} {b.value}" for b, c in counts)
        if ips > 0:
            surplus.write(f"- {60 * ips:.1f} {i.value}/min = {rep}")
        else:
            deficit.write(f"- {60 * ips:.1f} {i.value}/min = {rep}")


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


def get[T](key: str, ty: type[T], default: T) -> T:
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
    return get(key_bname(block_id, count_id), state.Bname, state.Bname.fishers_houses)


def get_takes(
    block_id: str, count_id: str, default: set[state.Item]
) -> set[state.Item]:
    return set(get(key_takes(block_id, count_id), list[state.Item], list(default)))


def get_state(
    ss: SessionState,
    buildings: dict[state.Bname, state.Building],
) -> tuple[list[state.BlockBalance], state.Ivec]:
    balances = [get_state_block(buildings, block) for block in ss.blocks]
    balance = state.get_global_balance(balances)
    return balances, balance


def get_state_block(
    buildings: dict[state.Bname, state.Building], block: BlockState
) -> state.BlockBalance:
    imports = block.imports.get(set())
    counts = [get_state_block_count(buildings, count) for count in block.counts]
    exports = block.exports.get(set())
    balance = state.get_block_balance(state.Block(imports, counts, exports))
    return balance


def get_state_block_count(
    buildings: dict[state.Bname, state.Building], count_state: CountState
) -> state.BuildingCount:
    count = count_state.count.get()
    bname = count_state.bname.get()
    building = buildings[bname]
    match building:
        case state.TavernBuilding():
            takes = count_state.takes.get(building.get_take_items())
            return state.BuildingCount(
                count, state.ConfiguredTavernBuilding(building, takes)
            )
        case state.SmokeryBuilding():
            takes = count_state.takes.get(building.get_take_items())
            return state.BuildingCount(
                count, state.ConfiguredSmokeryBuilding(building, takes)
            )
        case state.PlainBuilding():
            return state.BuildingCount(count, building)


def main():
    st.set_page_config(page_title="widelands planner", layout="wide")

    ss = SessionState.from_key()
    buildings = state.get_buildings()
    balances, balance = get_state(ss, buildings)
    bnames = sorted(state.Bname)
    items = state.get_items()

    with st.sidebar:
        st.subheader("global balance")
        with st.container(gap=None):
            st_ivec(balance)
        st.divider()
        st.button("add block", on_click=add_block)
        st.divider()
        with st.container(horizontal=True):
            if st.button("save"):
                # TODO do those still work?
                save_state(Path("./state.json"))
            if st.button("load"):
                load_state(Path("./state.json"))

    block_names = [block.name.get() for block in ss.blocks]
    if len(block_names) == 0:
        st.write("no blocks")
    else:
        tabs = st.tabs(block_names)
        for tab, block, block_balance in zip(tabs, ss.blocks, balances, strict=True):
            with tab:
                meta, counts = st.columns([1, 4])
                with meta:
                    with st.expander("block", expanded=True):
                        st.text_input("name", key=block.name.key)
                        st.button(
                            "remove",
                            key=block.remove.key,
                            on_click=block.remove_fn(),
                        )
                    with st.expander("imports", expanded=True):
                        st.multiselect(
                            "imports",
                            items,
                            key=block.imports.key,
                            label_visibility="collapsed",
                        )
                        st_ivec(block_balance.imports)
                    with st.expander("local", expanded=True):
                        st_ivec(block_balance.local)
                    with st.expander("exports", expanded=True):
                        st.multiselect(
                            "exports",
                            items,
                            key=block.exports.key,
                            label_visibility="collapsed",
                        )
                        st_ivec(block_balance.exports)
                with counts, st.container(horizontal=True, border=False):
                    for count_state in block.counts:
                        with st.container(width=250, border=True):
                            st.selectbox("building", bnames, key=count_state.bname.key)
                            st.number_input(
                                "count", key=count_state.count.key, min_value=0
                            )
                            bname = count_state.bname.get()
                            building = buildings[bname]
                            match building:
                                case state.TavernBuilding() | state.SmokeryBuilding():
                                    st.multiselect(
                                        "takes",
                                        sorted(building.get_take_items()),
                                        key=count_state.takes.key,
                                    )
                                case _:
                                    pass
                            st.button(
                                "remove",
                                key=count_state.remove.key,
                                on_click=count_state.remove_fn(),
                            )
                    st.button(
                        "add building",
                        key=block.counts.add.key,
                        on_click=block.counts.add_fn(),
                    )


if __name__ == "__main__":
    main()

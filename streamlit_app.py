from __future__ import annotations

import inspect
import json
import typing
from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass
from enum import StrEnum
from functools import partial
from pathlib import Path
from typing import Annotated, Any, ParamSpec, Protocol, final, override
from uuid import uuid4

import streamlit as st
from streamlit.delta_generator import DeltaGenerator

from widelands_planner import state


def save_state(path: Path):
    state = {
        k: v
        for (k, v) in st.session_state.items()
        if isinstance(k, str) and k.startswith("state/")
    }
    path.write_text(json.dumps(state))


def load_state(path: Path):
    state = json.loads(path.read_text())
    st.session_state.update(state)


def get_block_ids() -> list[int]:
    ids: list[int] | None = st.session_state.get("state/block_ids")
    if ids is None:
        st.session_state["state/next_block_id"] = 0
        ids = []
        st.session_state["state/block_ids"] = ids
    if len(ids) == 0:
        next_id = st.session_state["state/next_block_id"]
        ids = [next_id]
        st.session_state["state/block_ids"] = ids
        st.session_state["state/next_block_id"] = next_id + 1
    return ids


def get_block_name_key(id: int) -> str:
    return f"state/blocks/{id}/name"


def get_block_name(id: int) -> str:
    return st.session_state.setdefault(get_block_name_key(id), "unnamed")


def add_block(name: str):
    id = st.session_state.get("state/next_block_id", 1)
    ids = get_block_ids()
    ids.append(id)
    st.session_state["state/block_ids"] = ids
    st.session_state[f"state/blocks/{id}/name"] = name
    st.session_state["state/next_block_id"] = id + 1


def remove_block(block_id: int):
    block_ids = get_block_ids()
    block_ids.remove(block_id)
    st.session_state["state/block_ids"] = block_ids


class Key:
    def __init__(self, at: tuple[str, ...] = ()):
        self.__at = at

    def __getitem__(self, name: str) -> Key:
        return Key((*self.__at, name))

    def __getattr__(self, name: str) -> Key:
        return self[name]

    @override
    def __str__(self) -> str:
        return ".".join(self.__at)


def save(key: Key, value: int | str | float | list[str]):
    st.session_state[str(key)] = value


def load[T](key: Key, ty: type[T], default: T) -> T:
    value = st.session_state.get(str(key), default)
    # TODO check type
    return value


@dataclass(frozen=True)
class UuidListState:
    key: str

    def get(self) -> list[str]:
        return st.session_state.setdefault(self.key, [])


@dataclass(frozen=True)
class BuildingState:
    pass


rs = Key().state


@dataclass(frozen=True)
class BlockState:
    id: str

    def key(self) -> Key:
        return rs.blocks[self.id]

    def save(self):
        pass

    def st_name(self):
        fn = partial(st.text_input, key=str(rs.block[self.id].name))
        return fn


def set_default(key: Key | str, value: str | int):
    st.session_state.setdefault(str(key), value)


def set_value(key: Key | str, value: str | int):
    st.session_state[str(key)] = value


def get_str(key: Key | str) -> str:
    # TODO check type
    return st.session_state.get(str(key), "")


def get_int(key: Key | str) -> int:
    # TODO check type
    return st.session_state.get(str(key), 0)


def get_str_list(key: Key | str) -> list[str]:
    return st.session_state.get(str(key), [])


def append_str_list(key: Key | str, item: str):
    items = st.session_state.get(str(key), [])
    items.append(item)
    st.session_state[str(key)] = items


def remove_str_list(key: Key | str, item: str):
    # TODO not sure if we need to read and write
    items = st.session_state.get(str(key), [])
    items.remove(item)
    st.session_state[str(key)] = items


@final
class StrState:
    def __init__(self, key: Key, value: str):
        set_default(key, value)
        self.key = str(key)

    @property
    def value(self) -> str:
        return get_str(self.key)

    @property
    def text_input(self):
        return partial(st.text_input, key=self.key)


@final
class ButtonState:
    def __init__(self, key: Key):
        self.key = str(key)

    @property
    def button(self):
        # NOTE if-constructs make keys disappear, its better to use on_click
        return partial(st.button, key=self.key)


@final
class IntState:
    def __init__(self, key: Key, value: int):
        set_default(key, value)
        self.key = str(key)

    @property
    def value(self) -> int:
        return get_int(self.key)

    @property
    def number_input(self):
        return partial(st.number_input, key=self.key)


@final
class EnumState[E: StrEnum]:
    def __init__(self, key: Key, ty: type[E], default: E):
        self.ty = ty
        self.key = str(key)
        st.session_state.setdefault(self.key, default)

    @property
    def value(self) -> E:
        # TODO typing?
        return st.session_state[self.key]

    @property
    def selectbox(self):
        return partial(st.selectbox, options=list(self.ty), key=self.key)


class IdDictValue(Protocol):
    def __init__(self, key: Key):
        pass


@final
class IdDict[V: IdDictValue]:
    def __init__(self, key: Key, ty: type[V]):
        self.key = key
        self.ty = ty

    def __getitem__(self, key: str) -> V:
        return self.ty(self.key.values[key])

    def items(self) -> Iterator[tuple[str, V]]:
        for key in get_str_list(self.key.keys):
            yield (key, self[key])

    def add(self) -> str:
        key = uuid4().hex
        append_str_list(self.key.keys, key)
        return key

    def fn_add(self):
        def fn():
            self.add()

        return fn

    def remove(self, key: str):
        # TODO also clean up data in .values?
        remove_str_list(self.key.keys, key)

    def fn_remove(self, key: str):
        def fn():
            self.remove(key)

        return fn

    @property
    def add_button(self):
        return partial(st.button, key=str(self.key.add_button), on_click=self.fn_add())

    def remove_button(self, key: str):
        return partial(
            st.button,
            key=str(self.key.remove_button[key]),
            on_click=self.fn_remove(key),
        )


@final
class BState:
    def __init__(self, key: Key):
        self.key = key
        self.name = StrState(key.name, "unnamed")
        self.count = IntState(key.count, 0)
        self.remove = ButtonState(key.remove)


@final
class BuildingState:
    def __init__(self, key: Key):
        self.count = IntState(key.count, 0)
        self.name = EnumState(key.name, state.Bname, state.Bname.fishers_houses)


@final
class BlockState:
    def __init__(self, key: Key):
        self.name = StrState(key.name, "unnamed block")
        self.buildings = IdDict(key.buildings, BuildingState)


@final
class OState:
    def __init__(self, key: Key):
        self.name = StrState(key.name, "unnamed")
        self.count = IntState(key.count, 0)
        self.buildings = IdDict(key.buildings, BState)
        self.add = ButtonState(key.add)
        self.blocks = IdDict(key.blocks, BlockState)


@dataclass(frozen=True)
class State:
    blocks: dict[str, BlockState]

    @classmethod
    def from_session(cls):
        ids = load(rs.block_uuids, list[str], [])
        return cls({id: BlockState.from_session(id) for id in ids})

    def save(self):
        key = Key().state
        save(key.block_uuids, list(self.blocks))
        for block in self.blocks.values():
            block.save()

    def call[**P](self, fn: Callable[P, None]):
        def partial(*args: P.args, **kwargs: P.kwargs):
            def baked():
                fn(*args, **kwargs)
                self.save()

            return baked

        return partial

    def add_block(self, name: str):
        id = uuid4().hex
        load(rs.block_uuids, list[str], []).append(id)
        self.blocks[id] = BlockState(id, name)

    def remove_block(self, id: str):
        load(rs.block_uuids, list[str], []).remove(id)
        del self.blocks[id]


def st_building_count(
    block_id: int, name: str, variation: str, building: state.Building
) -> tuple[state.BuildingCount, DeltaGenerator]:
    with st.container(border=True, width=200):
        st.write(f"**{name}** {variation}")
        if st.button(
            "add",
            key=f"key/blocks/{block_id}/buildings/{name}/variations/{variation}/add",
        ):
            st.session_state.setdefault(
                f"state/blocks/{block_id}/buildings/{name}/variation_ids", ["default"]
            ).append(uuid4())
            st.rerun()
        if st.button(
            "rm",
            key=f"key/blocks/{block_id}/buildings/{name}/variations/{variation}/rm",
        ):
            st.session_state.setdefault(
                f"state/blocks/{block_id}/buildings/{name}/variation_ids", ["default"]
            ).remove(variation)
            st.rerun()
        match building:
            case state.TavernBuilding():
                count = st.number_input(
                    "count",
                    min_value=0,
                    value=0,
                    key=f"state/blocks/{block_id}/buildings/{name}/variations/{variation}/count",
                    label_visibility="collapsed",
                )
                info = st.empty()
                items = sorted(building.get_take_items())
                takes = set(
                    st.pills(
                        "takes",
                        items,
                        selection_mode="multi",
                        default=items,
                        label_visibility="collapsed",
                        key=f"state/blocks/{block_id}/buildings/{name}/variations/{variation}/takes",
                    )
                )
                return state.BuildingCount(
                    count, state.ConfiguredTavernBuilding(building, takes)
                ), info

            case state.SmokeryBuilding():
                count = st.number_input(
                    name,
                    min_value=0,
                    value=0,
                    key=f"state/blocks/{block_id}/buildings/{name}/variations/{variation}/count",
                    label_visibility="collapsed",
                )
                info = st.empty()
                items = sorted(building.get_take_items())
                takes = set(
                    st.pills(
                        "takes",
                        items,
                        selection_mode="multi",
                        default=items,
                        label_visibility="collapsed",
                        key=f"state/blocks/{block_id}/buildings/{name}/variations/{variation}/takes",
                    )
                )
                return state.BuildingCount(
                    count, state.ConfiguredSmokeryBuilding(building, takes)
                ), info

            case state.PlainBuilding():
                count = st.number_input(
                    name,
                    min_value=0,
                    value=0,
                    key=f"state/blocks/{block_id}/buildings/{name}/variations/{variation}/count",
                    label_visibility="collapsed",
                )
                info = st.empty()
                return state.BuildingCount(count, building), info

            case _ as never:  # pyright: ignore[reportUnnecessaryComparison]
                assert False, never  # pyright: ignore[reportUnreachable]


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


def st_block(block_id: int) -> state.BlockBalance:
    items = state.get_items()
    buildings = state.get_buildings()

    st_meta, st_buildings = st.columns([1, 2])
    with st_meta:
        with st.expander("config"):
            with st.container(
                border=False, horizontal=True, vertical_alignment="bottom"
            ):
                st.text_input("name", key=get_block_name_key(block_id))
                st.button(
                    "delete",
                    key=f"key/blocks/{block_id}/delete",
                    on_click=remove_block,
                    args=(block_id,),
                )
            imports = st.multiselect(
                "imports",
                items,
                key=f"state/blocks/{block_id}/imports",
            )
            local_bnames: list[state.Bname] = st.multiselect(
                "locals",
                buildings,
                key=f"state/blocks/{block_id}/locals",
            )
            locals: list[tuple[state.Bname, str]] = [
                (b, v)
                for b in sorted(local_bnames)
                for v in st.session_state.setdefault(
                    f"state/blocks/{block_id}/buildings/{b.value}/variation_ids",
                    ["default"],
                )
                or ["default"]
            ]
            exports = st.multiselect(
                "exports",
                items,
                key=f"state/blocks/{block_id}/exports",
                # TODO that actually kinda works, looks ugly, but still, just save a bookmark
                bind="query-params",
            )

        with st.container(border=True):
            st_imports = st.empty()
        with st.container(border=True):
            st_locals = st.empty()
        with st.container(border=True):
            st_exports = st.empty()

    building_counts: list[state.BuildingCount] = []
    infos: list[DeltaGenerator] = []

    with st_buildings:
        with (
            st.expander("local buildings", expanded=True),
            st.container(horizontal=True),
        ):
            for name, variation in locals:
                b, i = st_building_count(block_id, name, variation, buildings[name])
                building_counts.append(b)
                infos.append(i)
        # with st.expander("more buildings"), st.container(horizontal=True):
        #     for name in sorted(set(buildings) - set(locals)):
        #         b, i = st_building_count(block_id, name, buildings[name])
        #         building_counts.append(b)
        #         infos.append(i)

    balance = state.get_block_balance(
        state.Block(set(imports), building_counts, set(exports))
    )

    with st_imports.container(gap=None):
        st_ivec(balance.imports)

    with st_locals.container(gap=None):
        st_ivec(balance.local)

    with st_exports.container(gap=None):
        st_ivec(balance.exports)

    return balance


def main():
    st.set_page_config(page_title="widelands planner", layout="wide")

    s = OState(Key().state)
    s.blocks.add_button("add block")
    tab_names = [block.name.value for _, block in s.blocks.items()]
    if len(tab_names) > 0:
        tabs = st.tabs(tab_names)
        for tab, (key, block) in zip(tabs, s.blocks.items(), strict=True):
            with tab:
                with st.container(horizontal=True, vertical_alignment="bottom"):
                    block.name.text_input("name")
                    s.blocks.remove_button(key)("remove block")
                with st.container(horizontal=True):
                    for key, building in block.buildings.items():
                        with st.container(border=True, width=300):
                            building.name.selectbox("name")
                            building.count.number_input("count", min_value=0)
                            block.buildings.remove_button(key)("remove")
                    block.buildings.add_button("add building")

    return

    a = State.from_session()
    st.write(asdict(a))
    with st.container(horizontal=True):
        for uuid, block in a.blocks.items():
            with st.container(width=200):
                st.write(block.name)
                block.st_name()("name")
                st.write(uuid)
                st.button(
                    "remove",
                    key=f"{uuid}/remove",
                    on_click=a.call(a.remove_block)(uuid),
                )

    st.button("add", key="add", on_click=a.call(a.add_block)("new"))

    with st.sidebar:
        with st.container(horizontal=True):
            if st.button("save"):
                save_state(Path("./state.json"))
            if st.button("load"):
                load_state(Path("./state.json"))
        with st.expander("add blocks"):
            new_block_name = st.text_input("name", key="key/new block name")
            st.button(
                "add",
                key="key/add new block",
                on_click=add_block,
                args=(new_block_name,),
            )

    block_ids = get_block_ids()
    block_names = [get_block_name(i) for i in block_ids]

    balances: list[state.BlockBalance] = []
    for block_id, tab in zip(block_ids, st.tabs(block_names), strict=True):
        with tab:
            balances.append(st_block(block_id))

    balance = state.get_global_balance(balances)

    with st.sidebar:
        st.subheader("global balance")
        with st.container(gap=None):
            st_ivec(balance)


if __name__ == "__main__":
    main()

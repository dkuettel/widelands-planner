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
class BuildingCountState:
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
class PlainBuildingState:
    pass


@final
class BuildingCountState:
    def __init__(self, key: Key):
        self.count = IntState(key.count, 0)
        # TODO how to manage here the Smokery and co configs vs plain?
        # manually we would look at Bname first, and depending on this instantiate something different
        self.building: PlainBuildingState = PlainBuildingState(key.building)


@final
class BlockState:
    def __init__(self, key: Key):
        self.name = StrState(key.name, "unnamed block")
        self.counts = IdDict(key.buildings, BuildingCountState)


@final
class OState:
    def __init__(self, key: Key):
        self.add = ButtonState(key.add)
        self.blocks = IdDict(key.blocks, BlockState)


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


@dataclass(frozen=True)
class BuildingCount:
    count: int


@dataclass(frozen=True)
class Block:
    id: str
    name: str
    counts: list[BuildingCount]

    @classmethod
    def from_session(cls, id: str, key: Key):
        ids: list[str] = st.session_state.setdefault(str(key.counts.ids), [])
        return cls(
            id=id,
            name=st.session_state.setdefault(str(key.name), "unnamed block"),
            counts=[BuildingCount.from_session],
        )


def get_blocks() -> list[Block]:
    key = Key().stat.blocks
    ids = st.session_state.setdefault(str(key.ids), [])
    return [Block.from_session(id, key.values[id]) for id in ids]


kstate = Key().state


def get[T](key: Key, ty: type[T], default: T) -> T:
    value = st.session_state.setdefault(str(key), default)
    # TODO check type better
    # assert isinstance(value, ty)
    return value


def get_block_ids() -> list[str]:
    return get(kstate.blocks.ids, list[str], [])


def add_block():
    id = uuid4().hex
    get(kstate.blocks.ids, list[str], []).append(id)


def remove_block(id: str):
    get(kstate.blocks.ids, list[str], []).remove(id)


def get_count_ids(block_id: str) -> list[str]:
    return get(kstate.blocks.items[block_id].counts.ids, list[str], [])


def get_count(block_id: str, count_id: str) -> int:
    # TODO so i guess we could just make Key so that it only has valid keys? if we want it documented?
    return get(kstate.blocks.items[block_id].counts.items[count_id].count, int, 0)


def add_count(block_id: str):
    id = uuid4().hex
    get(kstate.blocks.items[block_id].counts.ids, list[str], []).append(id)


def remove_count(block_id: str, count_id: str):
    get(kstate.blocks.items[block_id].counts.ids, list[str], []).remove(count_id)


def get_bname(block_id: str, count_id: str) -> state.Bname:
    # TODO does this return str or a Bname?
    return get(
        kstate.blocks.items[block_id].counts.items[count_id].bname,
        state.Bname,
        state.Bname.fishers_houses,
    )


def get_takes(
    block_id: str, count_id: str, default: set[state.Item]
) -> set[state.Item]:
    return set(
        get(
            kstate.blocks.items[block_id].counts.items[count_id].takes,
            list[state.Item],
            list(default),
        )
    )


def get_imports(block_id: str) -> set[state.Item]:
    return set(
        get(
            kstate.blocks.items[block_id].imports,
            list[state.Item],
            list(),
        )
    )


def get_exports(block_id: str) -> set[state.Item]:
    return set(
        get(
            kstate.blocks.items[block_id].exports,
            list[state.Item],
            list(),
        )
    )


def get_state(
    buildings: dict[state.Bname, state.Building],
) -> tuple[list[state.BlockBalance], state.Ivec]:
    balances = [get_state_block(buildings, block_id) for block_id in get_block_ids()]
    balance = state.get_global_balance(balances)
    return balances, balance


def get_state_block(
    buildings: dict[state.Bname, state.Building], block_id: str
) -> state.BlockBalance:
    imports = get_imports(block_id)
    counts = [
        get_state_block_count(buildings, block_id, count_id)
        for count_id in get_count_ids(block_id)
    ]
    exports = get_exports(block_id)
    balance = state.get_block_balance(state.Block(imports, counts, exports))
    return balance


def get_state_block_count(
    buildings: dict[state.Bname, state.Building], block_id: str, count_id: str
) -> state.BuildingCount:
    count = get_count(block_id, count_id)
    bname = get_bname(block_id, count_id)
    building = buildings[bname]
    match building:
        case state.TavernBuilding():
            takes = get_takes(block_id, count_id, building.get_take_items())
            return state.BuildingCount(
                count, state.ConfiguredTavernBuilding(building, takes)
            )
        case state.SmokeryBuilding():
            takes = get_takes(block_id, count_id, building.get_take_items())
            return state.BuildingCount(
                count, state.ConfiguredSmokeryBuilding(building, takes)
            )
        case state.PlainBuilding():
            return state.BuildingCount(count, building)


def main():
    st.set_page_config(page_title="widelands planner", layout="wide")

    buildings = state.get_buildings()
    balances, balance = get_state(buildings)
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

    block_ids = get_block_ids()
    if len(block_ids) > 0:
        block_names = [
            get(kstate.blocks.items[id].name, str, "unnamed block") for id in block_ids
        ]
        tabs = st.tabs(block_names)
        for tab, block_id, block_balance in zip(tabs, block_ids, balances, strict=True):
            with tab:
                meta, counts = st.columns([1, 4])
                with meta:
                    with st.expander("block", expanded=True):
                        st.text_input(
                            "name", key=str(kstate.blocks.items[block_id].name)
                        )
                        st.button(
                            "remove",
                            key=str(kstate.blocks.items[block_id].remove),
                            on_click=partial(remove_block, block_id),
                        )
                    with st.expander("imports", expanded=True):
                        st.multiselect(
                            "imports",
                            items,
                            key=str(kstate.blocks.items[block_id].imports),
                            label_visibility="collapsed",
                        )
                        st_ivec(block_balance.imports)
                    with st.expander("local", expanded=True):
                        st_ivec(block_balance.local)
                    with st.expander("exports", expanded=True):
                        st.multiselect(
                            "exports",
                            items,
                            key=str(kstate.blocks.items[block_id].exports),
                            label_visibility="collapsed",
                        )
                        st_ivec(block_balance.exports)
                with counts, st.container(horizontal=True, border=False):
                    for count_id in get_count_ids(block_id):
                        with st.container(width=250, border=True):
                            st.selectbox(
                                "building",
                                bnames,
                                key=str(
                                    kstate.blocks.items[block_id]
                                    .counts.items[count_id]
                                    .bname
                                ),
                            )
                            st.number_input(
                                "count",
                                key=str(
                                    kstate.blocks.items[block_id]
                                    .counts.items[count_id]
                                    .count
                                ),
                                min_value=0,
                            )
                            bname = get_bname(block_id, count_id)
                            building = buildings[bname]
                            match building:
                                case state.TavernBuilding() | state.SmokeryBuilding():
                                    st.multiselect(
                                        "takes",
                                        sorted(building.get_take_items()),
                                        key=str(
                                            kstate.blocks.items[block_id]
                                            .counts.items[count_id]
                                            .takes
                                        ),
                                    )
                                case _:
                                    pass
                            st.button(
                                "remove",
                                key=str(
                                    kstate.blocks.items[block_id]
                                    .counts.items[count_id]
                                    .remove
                                ),
                                on_click=partial(remove_count, block_id, count_id),
                            )
                    st.button(
                        "add building",
                        key=str(kstate.blocks.items[block_id].add),
                        on_click=partial(add_count, block_id),
                    )


if __name__ == "__main__":
    main()

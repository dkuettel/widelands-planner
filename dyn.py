from __future__ import annotations

import json
import math
from collections.abc import Iterator
from dataclasses import dataclass
from functools import partial
from itertools import product
from pathlib import Path
from typing import Literal

import streamlit as st

type BuildingName = Literal[
    "bakery",
    "brick kiln",
    "clay pit",
    "coal",
    "fishery",
    "forester",
    "fruit",
    "granite",
    "reed",
    "smokery",
    "tavern",
    "water",
    "woodcutter",
    "farm",
]

buildings: set[BuildingName] = set(BuildingName.__value__.__args__)


def rratio(make: float, take: float) -> float:
    return make / take


requires: dict[
    BuildingName,
    dict[BuildingName, float]
    | tuple[dict[BuildingName, float], dict[BuildingName, float]],
] = {
    "woodcutter": {"forester": 0.5},
    "clay pit": {"water": 0.7},
    "brick kiln": {"clay pit": 2.1, "coal": 0.5, "granite": 0.5},
    "coal": {"tavern": rratio(37, 2 * 41)},
    "granite": {"tavern": rratio(37, 2 * 46)},
    "tavern": (
        {
            "smokery": rratio(27, 2 * 37),  # TODO meaning only fish right now
            "fruit": rratio((37 + 62) / 2, 2 * 37),
        },
        {
            "smokery": rratio(27, 2 * 37),  # TODO meaning only fish right now
            "bakery": rratio(44, 2 * 37),
        },
    ),
    "smokery": {
        "fishery": rratio((26 + 59) / 2, 27),
        "woodcutter": rratio((49 + 89) / 2, 2 * 27),
    },
}


# TODO might be nicer to make this numpy or torch with fixed order?
@dataclass(frozen=True)
class Bvecf:
    data: dict[BuildingName, float]

    @classmethod
    def from_zero(cls):
        return cls({name: 0.0 for name in buildings})

    def __getitem__(self, name: BuildingName) -> float:
        return self.data[name]

    def items(self):
        return self.data.items()

    def inc(self, other: dict[BuildingName, float]) -> Bvecf:
        return Bvecf({k: (v + other.get(k, 0.0)) for k, v in self.data.items()})

    def add(self, other: Bvecf) -> Bvecf:
        return Bvecf({k: (v + other[k]) for k, v in self.data.items()})


# TODO rename to block type? better to have name in here or in dict?
@dataclass(frozen=True)
class BlockInfo:
    imports: set[BuildingName]
    local: set[BuildingName]
    exports: set[BuildingName]


block_infos: dict[str, BlockInfo] = {
    "materials": BlockInfo(
        {"granite", "coal"},
        {"water", "forester"},
        {"brick kiln", "clay pit", "reed", "woodcutter"},
    ),
    "wood": BlockInfo(set(), {"forester"}, {"woodcutter"}),
    "mining": BlockInfo(set(), set(), {"coal", "granite"}),
    "rations": BlockInfo(
        set(),
        {
            "forester",
            "woodcutter",
            "farm",
            "water",
            "bakery",
            "smokery",
            "fishery",
            "fruit",
        },
        {"tavern"},
    ),
}


def get_block_ids() -> list[int]:
    return st.session_state.setdefault("state/blocks", [])


def add_block():
    blocks = get_block_ids()
    blocks.append(max(blocks, default=0) + 1)


def delete_block(id: int):
    blocks = get_block_ids()
    blocks.remove(id)


def get_block_type(id: int) -> str:
    return st.session_state.setdefault(f"state/block/{id}/type", sorted(block_infos)[0])


def get_block_name(id: int) -> str:
    return st.session_state.setdefault(f"state/block/{id}/name", "")


def get_block_info(id: int) -> BlockInfo:
    return block_infos[get_block_type(id)]


def get_block_building(id: int, name: BuildingName) -> int:
    return st.session_state.get(f"state/block/{id}/buildings/{name}", 0)


def get_direct_needs(block: int) -> dict[BuildingName, float]:
    names: set[BuildingName]
    names = {name for name in buildings if get_block_building(block, name) > 0}
    names = {name for name in names if name in requires}
    weights: dict[BuildingName, int]
    weights = {name: (1 if isinstance(requires[name], dict) else 2) for name in names}

    def get_combs(
        weights: list[tuple[BuildingName, int]],
    ) -> Iterator[dict[BuildingName, list[float]]]:
        if len(weights) == 0:
            yield dict()
            return
        (name, w), *more = weights
        match w:
            case 1:
                for c in get_combs(more):
                    c[name] = [1.0]
                    yield c
            case 2:
                for i in range(0, 10 + 1):
                    for c in get_combs(more):
                        c[name] = [i / 10, 1 - i / 10]
                        yield c
            case _:
                assert False, w

    combs = list(get_combs(list(weights.items())))

    def get_needs(comb: dict[BuildingName, list[float]]) -> dict[BuildingName, float]:
        needs = {name: 0.0 for name in buildings}
        for name, weights in comb.items():
            match weights:
                case [_]:
                    for other, ratio in requires[name].items():  # pyright: ignore[reportUnknownVariableType, reportAttributeAccessIssue]
                        needs[other] += get_block_building(block, name) * ratio
                case [a, b]:
                    for other, ratio in requires[name][0].items():  # pyright: ignore[reportUnknownVariableType, reportAttributeAccessIssue]
                        needs[other] += a * get_block_building(block, name) * ratio
                    for other, ratio in requires[name][1].items():  # pyright: ignore[reportUnknownVariableType, reportAttributeAccessIssue]
                        needs[other] += b * get_block_building(block, name) * ratio
                case _:
                    assert False
        return needs

    combs = [(comb, get_needs(comb)) for comb in combs]

    def is_fulfilled(needs: dict[BuildingName, float]) -> bool:
        return all(
            get_block_building(block, name) >= need for (name, need) in needs.items()
        )

    fulfilled = [(comb, needs) for (comb, needs) in combs if is_fulfilled(needs)]

    if len(fulfilled) > 0:

        def get_fulfilled_loss(x) -> float:
            comb, _ = x
            return sum(
                (w - 1 / len(weights)) ** 2
                for weights in comb.values()
                for w in weights
            )

        return min(fulfilled, key=get_fulfilled_loss)[1]

    def get_unfulfilled_loss(x) -> float:
        _, needs = x
        return sum(
            (get_block_building(block, name) - count) ** 2
            for name, count in needs.items()
        )

    return min(combs, key=get_unfulfilled_loss)[1]


def get_block_label(id: int) -> str:
    label = get_block_type(id)
    name = get_block_name(id)
    if name:
        return f'{label} **"{name}"**'
    return label


def get_building_totals() -> dict[BuildingName, int]:
    return {
        name: sum(
            (get_block_building(block, name) for block in get_block_ids()), start=0
        )
        for name in sorted(buildings)
    }


def key(*names: str | int) -> str:
    assert len(names) > 0
    return "/".join(map(str, names))


def st_block(
    bid: int, missing: dict[BuildingName, float], total_exports: dict[BuildingName, int]
):
    bkey = partial(key, "state", "block", bid)
    bbkey = partial(key, "state", "block", bid, "buildings")
    bbcount = partial(get_block_building, bid)

    with st.expander(
        # TODO if we compute all up front (a state after all?) then we can have :warning: here if there is at least one
        label=get_block_label(bid),
        expanded=True,
        key=bkey("expander"),
    ):
        with st.container(horizontal=True, vertical_alignment="bottom"):
            st.selectbox("type", sorted(block_infos), key=bkey("type"))
            st.text_input("name", key=bkey("name"))
            if st.button("delete", key=key("key", "block", bid, "delete")):
                delete_block(bid)
                st.rerun()

        bi = get_block_info(bid)
        needs: dict[BuildingName, float] = get_direct_needs(bid)

        with st.container():
            if bi.imports:
                with st.container(horizontal=True):
                    st.write("**imports**:")
                    for name in sorted(bi.imports):
                        st.write(needs[name], name)

            if bi.local:
                st.write("**local**")
                with st.container(horizontal=True):
                    # TODO rename bi.buildings to bi.local and dont overlap?
                    for name in sorted(bi.local):
                        with st.container(border=True, width=200):
                            add = needs[name] - bbcount(name)
                            if math.ceil(add) > 0:
                                label = f"{name} :warning: add {math.ceil(add)}"
                            elif math.ceil(-add) > 1:
                                label = f"{name} :warning: rm {math.ceil(-add) - 1}"
                            else:
                                label = name
                            st.number_input(label, min_value=0, key=bbkey(name))
                            if bbcount(name) > 0:
                                usage = round(100 * needs[name] / bbcount(name))
                                st.text(
                                    f"{usage}% usage = {needs[name]:.1f}/{bbcount(name)}"
                                )
                            else:
                                st.text("no production")

            if bi.exports:
                st.write("**exports**")
                with st.container(horizontal=True):
                    for name in sorted(bi.exports):
                        with st.container(border=True, width=200):
                            add = max(0, missing[name]) + (needs[name] - bbcount(name))
                            if math.ceil(add) > 0:
                                label = f"{name} :warning: add {math.ceil(add)}"
                            elif math.ceil(-add) > 1:
                                label = f"{name} :warning: rm {math.ceil(-add) - 1}"
                            else:
                                label = name
                            st.number_input(label, min_value=0, key=bbkey(name))
                            add = needs[name] - bbcount(name)
                            if bbcount(name) > 0:
                                usage = round(100 * needs[name] / bbcount(name))
                            else:
                                usage = None
                            if total_exports[name] > 0:
                                eusage = round(
                                    100 + 100 * missing[name] / total_exports[name]
                                )
                            else:
                                eusage = None
                            infos = [
                                f"{needs[name]:.1f}/{bbcount(name)} local"
                                + ("" if usage is None else f" ({usage}%)"),
                                f"{bbcount(name) - needs[name]:.1f}/{bbcount(name)} export"
                                + ("" if usage is None else f" ({100 - usage}%)"),
                                f"{total_exports[name] + missing[name]:.1f}/{total_exports[name]} global"
                                + ("" if eusage is None else f" ({eusage}%)"),
                            ]
                            st.text("\n".join(infos))

            misplaced = {
                name
                for name in buildings
                if (bbcount(name) > 0 and name not in (bi.exports | bi.local))
                or (
                    needs[name] > 0 and name not in (bi.exports | bi.local | bi.imports)
                )
            }
            if misplaced:
                st.write("**misplaced** :warning:")
                with st.container(horizontal=True):
                    for name in sorted(misplaced):
                        with st.container(border=True, width=200):
                            st.number_input(name, min_value=0, key=bbkey(name))


def main():
    exports: dict[BuildingName, int] = {name: 0 for name in buildings}
    for bid in get_block_ids():
        for building in get_block_info(bid).exports:
            exports[building] += get_block_building(bid, building)

    imports: dict[BuildingName, float] = {name: 0.0 for name in buildings}
    for bid in get_block_ids():
        needs: dict[BuildingName, float] = get_direct_needs(bid)
        for building in get_block_info(bid).imports:
            imports[building] += needs[building]

    missing: dict[BuildingName, float] = {
        name: (imports[name] - exports[name]) for name in buildings
    }

    with st.container(horizontal=True, vertical_alignment="center"):
        path = Path("state.json")
        if st.button("save", key="key/save"):
            path.write_text(
                json.dumps(
                    {
                        k: v
                        for k, v in st.session_state.to_dict().items()
                        if k.startswith("state/")
                    }
                )
            )
        if st.button("load", key="key/load"):
            for k, v in json.loads(path.read_text()).items():
                st.session_state[k] = v
            st.rerun()
        st.write("from state.json at server root")

    st.title("blocks")
    for bid in get_block_ids():
        st_block(bid, missing, exports)

    with st.container(horizontal=False, horizontal_alignment="right", border=False):
        if st.button("add block", key="key/add block"):
            add_block()
            st.rerun()

    with st.sidebar:
        st.title("issues")
        with st.container(gap=None):
            for building in buildings:
                if missing[building] > 0:
                    st.write("missing", round(missing[building], 1), building)

        with st.container():
            st.title("totals")
            with st.container(gap=None):
                for name, count in sorted(get_building_totals().items()):
                    st.write(count, name)


if __name__ == "__main__":
    main()

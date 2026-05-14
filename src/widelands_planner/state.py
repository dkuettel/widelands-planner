from __future__ import annotations

import math
import re
import time
from collections import Counter, deque
from collections.abc import (
    Callable,
    Generator,
    Iterable,
    Iterator,
    Mapping,
    Sequence,
    Set,
)
from cProfile import Profile
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from functools import cache, partial, wraps
from pathlib import Path
from typing import Final, override

import numpy as np
from tabulate import tabulate

zips = partial(zip, strict=True)

type farray = np.typing.NDArray[np.floating]


def profile[**P, R](fn: Callable[P, R]) -> Callable[P, R]:
    import line_profiler  # pyright: ignore[reportMissingImports]

    fn = line_profiler.profile(fn)  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]

    @wraps(fn)  # pyright: ignore[reportUnknownArgumentType]
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return fn(*args, **kwargs)  # pyright: ignore[reportUnknownVariableType]

    return wrapper


def str_from_usage(alloc: Allocated) -> str:
    return f"{round(alloc.stable_usage * 100)}% + {round((alloc.flood_usage - alloc.stable_usage) * 100)}%"


def str_from_ivec(vec: Ivec) -> str:
    data = [f"{i.name}: {v:.2f}" for i, v in sorted(vec.data.items()) if v != 0.0]
    return "{" + ", ".join(data) + "}"


def print_block(allocated: Sequence[Allocated]):
    data = [
        (
            alloc.building.count,
            str_from_usage(alloc),
            alloc.building.building.building.name,
            (
                str_from_ivec(alloc.take_local.smul(60))
                + " + "
                + str_from_ivec(alloc.take_remote.smul(60))
            ),
            (
                str_from_ivec(alloc.make_main_local.smul(60))
                + "/"
                + str_from_ivec(alloc.make_aux_local.smul(60))
                + " + "
                + str_from_ivec(alloc.make_main_remote.smul(60))
                + "/"
                + str_from_ivec(alloc.make_aux_remote.smul(60))
            ),
        )
        for alloc in allocated
    ]
    print(tabulate(data, headers=["#", "%", "name", "take i/m", "make i/m"]))


def clipped(low: float | None, value: float, high: float | None) -> float:
    assert low is None or high is None or low <= high, (low, high)
    if low is not None:
        value = max(low, value)
    if high is not None:
        value = min(value, high)
    return value


class Item(StrEnum):
    bread = "bread"
    fish = "fish"
    fruit = "fruit"
    log = "log"
    meat = "meat"
    ration = "ration"
    smoked_fish = "smoked fish"
    smoked_meat = "smoked meat"
    tree = "tree"  # what the forester plants, not logs yet
    water = "water"
    barley = "barley"
    coal = "coal"
    granite = "granite"
    clay = "clay"
    brick = "brick"
    reed = "reed"
    berry_bush = "berry bush"  # TODO make fruit bush and honey bush? they coincide
    beer = "beer"
    iron_ore = "iron ore"
    iron = "iron"
    scrap_iron = "scrap iron"
    gold_ore = "gold ore"
    gold = "gold"
    short_sword = "short sword"
    long_sword = "long sword"
    helmet = "helmet"
    pick = "pick"
    felling_axe = "felling axe"
    shovel = "shovel"
    hammer = "hammer"
    hunting_spear = "hunting spear"
    scythe = "scythe"
    bread_paddle = "bread paddle"
    kitchen_tools = "kitchen tools"
    needles = "needles"
    basket = "basket"
    fire_tongs = "fire tongs"
    fishing_net = "fishing net"
    fur_garment = "fur garment"
    old_fur_garment = "old fur garment"
    studded_fur_garment = "studded fur garment"
    golden_fur_garment = "golden fur garment"
    deer = "deer"
    fur = "fur"
    broadsword = "broadsword"
    double_edged_sword = "double-edged sword"
    golden_helmet = "golden helmet"
    mixed_scrap_metal = "mixed scrap metal"
    honey_bread = "honey bread"
    mead = "mead"
    honey = "honey"


def get_items() -> list[Item]:
    return sorted(Item, key=lambda i: i.value)


def np_from_ivec(vec: Ivec) -> np.typing.NDArray[np.floating]:
    return np.array([vec[i] for i in Item])


def ivec_from_np(a: np.typing.NDArray[np.floating]) -> Ivec:
    return ifrom(
        {item: a[index].item() for (index, item) in enumerate(Item) if a[index] != 0.0}
    )


def np_nonzero_items(vec: farray) -> set[Item]:
    return {i for (v, i) in zips(vec, Item) if v > 0.0}


def np_zero_items(vec: farray) -> set[Item]:
    return {i for (v, i) in zips(vec, Item) if v == 0.0}


def np_zeros() -> np.typing.NDArray[np.floating]:
    return np.zeros(len(Item))


# NOTE the name is the widelands lua name, the value is the plural string
# TODO still not sure how robust is st.multiselect and co with enums and round-trips
# TODO hmm when the values are not unique, it seems match statements dont work right then :/
class Bname(StrEnum):
    tavern = "taverns"
    smokery = "smokeries"
    fishers_house = "fisher's houses"
    foresters_house = "forester's houses"
    woodcutters_house = "woodcutter's houses"
    well = "wells"
    farm = "farms"
    reed_farm = "reed farms"
    coalmine = "coal mines"
    rockmine = "rock mines"
    clay_pit = "clay pits"
    brick_kiln = "brick kilns"
    collectors_house = "fruit collector's houses"
    berry_farm = "berry farms"
    beekeepers_house = "beekeeper's houses"
    brewery = "breweries"
    mead_brewery = "mead breweries"
    bakery = "bakeries"
    honey_bread_bakery = "honey bread bakeries"
    ironmine = "iron mines"
    furnace = "furnaces"
    armor_smithy_small = "small armor smithies"
    armor_smithy_large = "large armor smithies"
    blacksmithy = "blacksmithies"
    barracks = "barracks"
    reindeer_farm = "reindeer farms"
    sewing_room = "sewing rooms"
    tailors_shop = "tailor's shops"
    goldmine = "gold mines"
    training_camp = "training camps"
    training_arena = "training arenas"


@dataclass(frozen=True)
class Vec[I]:
    ty: type[I]
    # TODO can we protect this dict from changes to be safe?
    data: dict[I, float]
    # TODO small steps, change backing data to numpy here and make sure still same results
    # could actually make .data a property with getters and setters for easier transition?

    @classmethod
    def from_zeros(cls, ty: type[I]):
        return Vec(ty, dict())

    @classmethod
    def from_sum(cls, ty: type[I], rates: Sequence[Vec[I]]):
        items = {i for r in rates for i in r.data}
        return cls(ty, {i: sum(r[i] for r in rates) for i in items})

    def low_clipped(self, low: float) -> Vec[I]:
        if low == 0.0:
            return Vec(self.ty, {i: v for (i, v) in self.data.items() if v > 0.0})
        # TODO well again, what do do with unset values, if they are 0.0, they should also be changed
        return Vec(self.ty, {i: max(low, v) for (i, v) in self.data.items()})

    def updated(self, updates: Mapping[I, float]) -> Vec[I]:
        v = Vec(self.ty, dict(self.data))
        v.data.update(updates)
        return v

    def sorted(self) -> Iterator[tuple[I, float]]:
        for k, v in sorted(self.data.items()):
            if v != 0:
                yield (k, v)

    def __getitem__(self, i: I) -> float:
        return self.data.get(i, 0)

    def __contains__(self, i: I) -> bool:
        return i in self.data

    def add(self, other: Vec[I]) -> Vec[I]:
        items = self.data.keys() | other.data.keys()
        return Vec(self.ty, {i: (self[i] + other[i]) for i in items})

    def sub(self, other: Vec[I]) -> Vec[I]:
        items = self.data.keys() | other.data.keys()
        return Vec(self.ty, {i: (self[i] - other[i]) for i in items})

    def smul(self, s: float) -> Vec[I]:
        return Vec(self.ty, {i: s * v for (i, v) in self.data.items()})

    def mul(self, other: Vec[I]) -> Vec[I]:
        items = self.data.keys() & other.data.keys()
        return Vec(self.ty, {i: (self[i] * other[i]) for i in items})

    def sdiv(self, s: float) -> Vec[I]:
        return self.smul(1 / s)

    def div(self, other: Vec[I]) -> Vec[I]:
        def div(a: float, b: float) -> float:
            if b == 0:
                return math.inf
            return a / b

        return Vec(
            self.ty, {i: div(v, other[i]) for (i, v) in self.data.items() if v != 0}
        )

    def negate(self) -> Vec[I]:
        return Vec(self.ty, {i: -v for (i, v) in self.data.items()})

    def keep_positives(self) -> Vec[I]:
        return Vec(self.ty, {i: v for (i, v) in self.data.items() if v > 0})

    def nonzero_items(self) -> set[I]:
        return {i for (i, v) in self.data.items() if v != 0}

    def is_zero(self) -> bool:
        return all(v == 0 for v in self.data.values())

    def include(self, items: Set[I]) -> Vec[I]:
        return Vec(self.ty, {i: v for (i, v) in self.data.items() if i in items})

    def exclude(self, items: Set[I]) -> Vec[I]:
        return Vec(self.ty, {i: v for (i, v) in self.data.items() if i not in items})

    def lte(self, other: Vec[I]) -> bool:
        return all(self[i] <= other[i] for i in self.data) and all(
            self[i] <= other[i] for i in other.data
        )

    def neq(self, other: Vec[I]) -> bool:
        return any(self[i] != other[i] for i in self.data) or any(
            self[i] != other[i] for i in other.data
        )

    def almost_equal(self, other: Vec[I], eps: float) -> bool:
        items = set(self.data) | set(other.data)
        return all(abs(self[i] - other[i]) <= eps for i in items)

    def min(self) -> float:
        # TODO very ambigous, and default too
        return min(self.data.values(), default=0)

    def is_nonnegative(self) -> bool:
        return all(v >= 0.0 for v in self.data.values())

    def rounded(self, eps: float) -> Vec[I]:
        # TODO ignoring missing entries
        return Vec(self.ty, {i: (round(v / eps) * eps) for (i, v) in self.data.items()})


type Ivec = Vec[Item]

meta_items: Final[dict[Item, str]] = {
    Item.short_sword: "{small armor}",
    Item.long_sword: "{small armor}",
    Item.helmet: "{small armor}",
    Item.broadsword: "{large armor}",
    Item.double_edged_sword: "{large armor}",
    Item.golden_helmet: "{large armor}",
    Item.pick: "{tools}",
    Item.felling_axe: "{tools}",
    Item.shovel: "{tools}",
    Item.hammer: "{tools}",
    Item.hunting_spear: "{tools}",
    Item.scythe: "{tools}",
    Item.bread_paddle: "{tools}",
    Item.kitchen_tools: "{tools}",
    Item.needles: "{tools}",
    Item.basket: "{tools}",
    Item.fire_tongs: "{tools}",
    Item.fishing_net: "{tools}",
}


def summarize_ivec(ivec: Ivec) -> dict[str, float]:
    sum: dict[str, float] = dict()
    for i, v in ivec.data.items():
        if v == 0.0:
            continue
        name = meta_items.get(i, i.name)
        sum[name] = sum.get(name, 0.0) + v
    return sum


def izeros() -> Ivec:
    return Vec[Item].from_zeros(Item)


def ifrom(data: dict[Item, float]) -> Ivec:
    return Vec[Item](Item, data)


def isum(sequence: Iterable[Ivec]) -> Ivec:
    return Vec[Item].from_sum(Item, list(sequence))


@dataclass(frozen=True)
class TakeMake:
    take: Ivec
    make: Ivec

    @classmethod
    def from_zeros(cls):
        return cls(izeros(), izeros())


@dataclass
class NpCrafting:
    take: farray
    make_main: farray
    make_aux: farray


# @dataclass(frozen=True)
@dataclass
class Crafting:
    take: Ivec
    # experiences back-pressure (meaning "produce only when economy needs")
    make_main: Ivec
    # doesnt experience back-pressure
    make_aux: Ivec
    seconds_range: tuple[float, float]  # (short, long)

    np: NpCrafting = field(init=False)

    def __post_init__(self):
        assert self.seconds_range[0] <= self.seconds_range[1]
        self.np = NpCrafting(
            take=np_from_ivec(self.take),
            make_main=np_from_ivec(self.make_main),
            make_aux=np_from_ivec(self.make_aux),
        )

    def seconds(self, speed: float) -> float:
        assert 0 <= speed <= 1, speed
        short, long = self.seconds_range
        return speed * short + (1 - speed) * long


cached_wants_ips: dict[tuple[Bname, frozenset[Item], frozenset[Item], Item], float] = (
    dict()
)


@dataclass(frozen=True)
class BaseBuilding:
    name: Bname
    # the next level only gets applied after the first one is maximized
    # (eg, the tavern makes 2-input rations before falling back to 1-input rations)
    crafting_levels: list[list[Crafting]]
    pause: float

    @classmethod
    def from_lua(
        cls, take: dict[Item, float], make: dict[Item, float], timings: str, name: Bname
    ):
        path = Path(
            f"widelands/data/tribes/buildings/productionsites/frisians/{timings}/init.lua"
        )
        short, long = extract_plain_timings(path)
        return cls(
            name,
            [
                [
                    Crafting(
                        take=ifrom(take),
                        make_main=ifrom(make),
                        make_aux=izeros(),
                        seconds_range=(short, long),
                    )
                ]
            ],
            0,
        )

    def get_take_items(self) -> set[Item]:
        return {
            item
            for level in self.crafting_levels
            for crafting in level
            for item in crafting.take.nonzero_items()
        }

    # TODO is this needed, should it include aux and main?
    def get_make_items(self) -> set[Item]:
        return {
            item
            for level in self.crafting_levels
            for crafting in level
            for make in [crafting.make_main, crafting.make_aux]
            for item in make.nonzero_items()
        }

    # TODO this is obsolete anyway, removed soon, doesnt respect levels now
    def get_ips(
        self,
        take: Ivec | None,
        make: Ivec | None,
        takes: set[Item],
        makes: set[Item],
        speed: float,
    ) -> TakeMake:
        dt = 0  # cycle duration seconds
        tk = izeros()  # cycle take items
        mk = izeros()  # cycle make items

        for level in self.crafting_levels:
            for c in level:
                if (
                    takes >= c.take.nonzero_items()
                    # and (c.unless is None or not (takes & c.unless))
                    and (c.make_main.is_zero() or makes & c.make_main.nonzero_items())
                ):
                    short, long = c.seconds_range
                    dt += speed * short + (1 - speed) * long
                    tk = tk.add(c.take)
                    mk = mk.add(c.make_main).add(c.make_aux)

        dt += self.pause

        if dt == 0:
            return TakeMake(take=izeros(), make=izeros())

        tk, mk = tk.sdiv(dt), mk.sdiv(dt)

        if take is None and make is None:
            return TakeMake(take=tk, make=mk)

        # TODO easier once it comes in a dataclass
        assert take is not None and make is not None

        take = take.include(tk.nonzero_items())
        make = make.include(tk.nonzero_items())

        if take.lte(make):
            return TakeMake(take=tk, make=mk)

        # TODO very cheap now, just scaling
        # but in reality, Craftings are quite complicated here
        # need to roll it up from there
        # TODO min is ambiguous, unlisted entries are meant to be zero, but we dont want them
        # yet, if one entry becomes explicitely zero, then we do want it (plus, div is problematic anyway)
        # look again at Vec semantics and distinguish between having a number and not? or always full? np then?
        # in that case, going towards a polars dataframe?
        ratio = make.div(take).min()

        return TakeMake(take=tk.smul(ratio), make=mk.smul(ratio))

    def needs_ips(
        self, takes: set[Item], makes: set[Item], speed: float, usage: float
    ) -> Ivec:
        return self.get_ips(None, None, takes, makes, speed).take.smul(usage)

    def get_enabled_crafting_levels(
        self, takes: set[Item], makes: set[Item]
    ) -> list[list[Crafting]]:
        return [
            [
                crafting
                for crafting in level
                if (
                    takes >= crafting.take.nonzero_items()
                    # TODO we will probably remove the unless thing soon and use preferred levels
                    # and (c.unless is None or not (takes & c.unless))
                    # TODO we probably should only define takes anyway
                    # and (c.make.is_zero() or makes & c.make.nonzero_items())
                )
            ]
            for level in self.crafting_levels
        ]

    def take_make_ips_from_craftings(
        self, craftings: Sequence[Crafting], speed: float
    ) -> tuple[Ivec, Ivec, Ivec]:
        if len(craftings) == 0:
            return izeros(), izeros(), izeros()
        dt: float = 0.0
        take: Ivec = izeros()
        make_main: Ivec = izeros()
        make_aux: Ivec = izeros()
        for crafting in craftings:
            dt += crafting.seconds(speed)
            take = take.add(crafting.take)
            make_main = make_main.add(crafting.make_main)
            make_aux = make_aux.add(crafting.make_aux)
        dt += self.pause
        assert dt > 0
        return take.sdiv(dt), make_main.sdiv(dt), make_aux.sdiv(dt)

    def np_take_make_ips_from_craftings(
        self, craftings: Sequence[Crafting], speed: float
    ) -> tuple[farray, farray, farray]:
        take = np.sum([c.np.take for c in craftings], axis=0)
        make_main = np.sum([c.np.make_main for c in craftings], axis=0)
        make_aux = np.sum([c.np.make_aux for c in craftings], axis=0)
        dt = sum(c.seconds(speed) for c in craftings) + self.pause
        assert dt > 0
        return take / dt, make_main / dt, make_aux / dt

    def np_take_make_ips_from_craftings_new(
        self, craftings: Sequence[Crafting], speed: float
    ) -> tuple[farray, farray, farray, farray, float]:
        take = np.stack([c.np.take for c in craftings], dtype=np.float32)
        make_main = np.stack([c.np.make_main for c in craftings], dtype=np.float32)
        make_aux = np.stack([c.np.make_aux for c in craftings], dtype=np.float32)
        dt = np.array([c.seconds(speed) for c in craftings], dtype=np.float32)
        return take, make_main, make_aux, dt, self.pause

    def produces_ips(
        self,
        takes: set[Item],
        makes: set[Item],
        speed: float,
        allocation: Ivec,
    ) -> tuple[Ivec, Ivec]:
        _take, make_main, make_aux, _used = self.allocate_ips(
            takes, makes, speed, allocation
        )
        return make_main, make_aux

    def np_produces_ips(
        self,
        takes: set[Item],
        makes: set[Item],
        speed: float,
        allocation: farray,
    ) -> tuple[farray, farray]:
        _np_total_take_ips, np_total_make_main_ips, np_total_make_aux_ips, _used = (
            self.np_allocate_ips_new_np(takes, makes, speed, allocation, None)
        )
        return np_total_make_main_ips, np_total_make_aux_ips

    def allocate_ips(
        self,
        takes: set[Item],
        makes: set[Item],
        speed: float,
        allocation: Ivec,
        limit: Ivec | None = None,
    ) -> tuple[Ivec, Ivec, Ivec, float]:
        # old = self.allocate_ips_old(takes, makes, speed, allocation, limit)
        new = self.allocate_ips_new(takes, makes, speed, allocation, limit)
        # assert new == old, breakpoint()
        # TODO result is the same now, but new is actually slower
        # probably that we have to move between ivec and numpy
        return new

    def allocate_ips_old(
        self,
        takes: set[Item],
        makes: set[Item],
        speed: float,
        allocation: Ivec,
        limit: Ivec | None = None,
    ) -> tuple[Ivec, Ivec, Ivec, float]:
        # NOTE the limit only affects output that experiences back-pressure, therefore, the final allocated output could be more than the limit
        # NOTE limit is interpreted as limit only when value set unset values are "inf"
        if limit is None:
            limit = ifrom({i: math.inf for i in Item})
        else:
            limit = ifrom(
                {i: (limit[i] if i in limit.data else math.inf) for i in Item}
            )
        assert all(v >= 0.0 for v in limit.data.values()), limit
        # TODO actually we can only control the takes, not the makes, right?
        crafting_levels: list[list[Crafting]] = self.get_enabled_crafting_levels(
            takes, makes
        )
        crafting_levels = [
            [
                crafting
                for crafting in level
                if crafting.take.nonzero_items() <= allocation.nonzero_items()
                and not (
                    crafting.make_main.nonzero_items()
                    & {i for i, v in limit.data.items() if v == 0.0}
                )
            ]
            for level in crafting_levels
        ]
        crafting_levels = [level for level in crafting_levels if len(level) > 0]
        total_take_ips = izeros()
        total_make_main_ips = izeros()
        total_make_aux_ips = izeros()
        used = 0.0
        while used < 1.0 and len(crafting_levels) > 0:
            take_ips, make_main_ips, make_aux_ips = self.take_make_ips_from_craftings(
                crafting_levels[0], speed
            )
            allocation_constraints = (
                (item, allocation[item] / ips)
                for item, ips in take_ips.data.items()
                if ips > 0.0
            )
            allocation_item, allocation_ratio = min(
                allocation_constraints, key=lambda x: x[1], default=(None, 1.0)
            )
            limit_constraints = (
                (item, limit[item] / ips)
                for item, ips in make_main_ips.data.items()
                if ips > 0.0 and item in limit.data
            )
            limit_item, limit_ratio = min(
                limit_constraints, key=lambda x: x[1], default=(None, 1.0)
            )
            ratio = min(allocation_ratio, limit_ratio)
            # TODO will it work when they are both true? or is there a problem when they should be both true but eps makes only one true?
            used_allocation_ratio = ratio == allocation_ratio
            used_limit_ratio = ratio == limit_ratio
            assert 0 <= ratio, (
                allocation_item,
                allocation_ratio,
                limit_item,
                limit_ratio,
            )
            # TODO doesnt this break used_limit_ratio and used_allocation_ratio in some cases?
            old_used, used = used, min(used + ratio, 1.0)
            ratio = used - old_used
            # TODO i think here and limit below are expensive because with inf and min(0, ...) they become dense, np here should help?
            allocation = allocation.sub(take_ips.smul(ratio))
            allocation = allocation.low_clipped(0.0)
            if allocation_item is not None and used_allocation_ratio:
                allocation.data[allocation_item] = 0.0
            assert all(v >= 0.0 for v in allocation.data.values()), allocation
            limit = limit.sub(make_main_ips.smul(ratio))
            limit = limit.low_clipped(0.0)
            if limit_item is not None and used_limit_ratio:
                limit.data[limit_item] = 0.0
            assert all(v >= 0.0 for v in limit.data.values()), limit
            total_take_ips = total_take_ips.add(take_ips.smul(ratio))
            total_make_main_ips = total_make_main_ips.add(make_main_ips.smul(ratio))
            total_make_aux_ips = total_make_aux_ips.add(make_aux_ips.smul(ratio))
            # TODO repeated with code at the beginning
            crafting_levels = [
                [
                    crafting
                    for crafting in level
                    if crafting.take.nonzero_items() <= allocation.nonzero_items()
                    and not (
                        crafting.make_main.nonzero_items()
                        & {i for i, v in limit.data.items() if v == 0.0}
                    )
                ]
                for level in crafting_levels
            ]
            crafting_levels = [level for level in crafting_levels if len(level) > 0]
        assert 0 <= used <= 1.0, used
        return total_take_ips, total_make_main_ips, total_make_aux_ips, used

    def allocate_ips_new(
        self,
        takes: set[Item],
        makes: set[Item],
        speed: float,
        allocation: Ivec,
        limit: Ivec | None = None,
    ) -> tuple[Ivec, Ivec, Ivec, float]:
        np_allocation = np_from_ivec(allocation)
        if limit is None:
            limit = ifrom({i: math.inf for i in Item})
        else:
            limit = ifrom(
                {i: (limit[i] if i in limit.data else math.inf) for i in Item}
            )
        np_limit = np_from_ivec(limit)

        np_total_take_ips, np_total_make_main_ips, np_total_make_aux_ips, used = (
            self.np_allocate_ips_new_np(takes, makes, speed, np_allocation, np_limit)
        )

        return (
            ivec_from_np(np_total_take_ips),
            ivec_from_np(np_total_make_main_ips),
            ivec_from_np(np_total_make_aux_ips),
            used,
        )

    def np_allocate_ips_new_np(
        self,
        takes: set[Item],
        makes: set[Item],
        speed: float,
        np_allocation: farray,
        np_limit: farray | None,
    ) -> tuple[farray, farray, farray, float]:
        np_allocation = np_allocation.astype(np.float32)
        if np_limit is not None:
            np_limit = np_limit.astype(np.float32)

        # TODO actually we can only control the takes, not the makes, right?
        crafting_levels: list[list[Crafting]] = self.get_enabled_crafting_levels(
            takes, makes
        )
        # TODO this might be precomputed or cached?
        crafting_levels = [
            [
                crafting
                for crafting in level
                # TODO costs
                if np.all((crafting.np.take == 0.0) | (np_allocation > 0.0))
                and (
                    np_limit is None
                    or np.all((crafting.np.make_main == 0.0) | (np_limit > 0.0))
                )
            ]
            for level in crafting_levels
        ]
        crafting_levels = [level for level in crafting_levels if len(level) > 0]
        crafting_count = sum(1 for level in crafting_levels for _ in level)

        # TODO hm overall this actually makes it slightly slower :/ maybe once everything is streamlined it will help?
        # could also be that many buildings are so easy, just one item, and we use a full np array for that now?
        # relevant_items = {
        #     item
        #     for level in crafting_levels
        #     for crafting in level
        #     for item in (
        #         crafting.take.nonzero_items()
        #         | crafting.make_main.nonzero_items()
        #         | crafting.make_aux.nonzero_items()
        #     )
        # }
        # item_mask = np.array([(item in relevant_items) for item in Item])

        np_total_take_ips = np_zeros().astype(np.float32)
        np_total_make_main_ips = np_zeros().astype(np.float32)
        np_total_make_aux_ips = np_zeros().astype(np.float32)
        used: float = 0.0

        # np_allocation = np_allocation[item_mask]
        # if np_limit is not None:
        #     np_limit = np_limit[item_mask]

        # np_total_take_ips = np_total_take_ips[item_mask]
        # np_total_make_main_ips = np_total_make_main_ips[item_mask]
        # np_total_make_aux_ips = np_total_make_aux_ips[item_mask]

        count = 0

        while len(crafting_levels) > 0:
            c_take, c_make_main, c_make_aux, c_dt, c_pause = (
                # TODO costs, but actually its hiding a few stacks, so not actually that much
                self.np_take_make_ips_from_craftings_new(crafting_levels.pop(0), speed)
            )
            # c_take = c_take[:, item_mask]
            # c_make_main = c_make_main[:, item_mask]
            # c_make_aux = c_make_aux[:, item_mask]

            while used < 1.0 and len(c_take) > 0:
                dt = np.sum(c_dt, axis=0) + c_pause
                assert dt > 0.0
                np_take_ips = np.sum(c_take, axis=0) / dt
                np_make_main_ips = np.sum(c_make_main, axis=0) / dt
                np_make_aux_ips = np.sum(c_make_aux, axis=0) / dt

                np_allocation_ratios = np.divide(
                    np_allocation,
                    np_take_ips,
                    where=np_take_ips > 0.0,
                    out=np.full_like(np_allocation, np.inf, dtype=np.float32),
                )
                np_allocation_index = np_allocation_ratios.argmin()
                np_allocation_ratio = np_allocation_ratios[np_allocation_index]
                if np.isposinf(np_allocation_ratio):
                    np_allocation_ratio = 1.0
                    has_allocation_item = False
                else:
                    assert np.isfinite(np_allocation_ratio)
                    has_allocation_item = True

                if np_limit is not None:
                    np_limit_ratios = np.divide(
                        np_limit,
                        np_make_main_ips,
                        where=np_make_main_ips > 0.0,
                        out=np.full_like(np_limit, np.inf, dtype=np.float32),
                    )
                    np_limit_index = np_limit_ratios.argmin()
                    np_limit_ratio = np_limit_ratios[np_limit_index]
                    if np.isfinite(np_limit_ratio):
                        has_limit_item = True
                    else:
                        np_limit_ratio = 1.0
                        has_limit_item = False
                else:
                    np_limit_ratio = math.inf
                    has_limit_item = False
                    np_limit_index = None

                np_ratio = min(np_allocation_ratio, np_limit_ratio)

                # TODO will it work when they are both true? or is there a problem when they should be both true but eps makes only one true?
                used_allocation_ratio = np_ratio == np_allocation_ratio
                used_limit_ratio = np_ratio == np_limit_ratio

                # TODO doesnt this break used_limit_ratio and used_allocation_ratio in some cases?
                old_used, used = used, min(used + np_ratio, 1.0)
                np_ratio = used - old_used

                np_allocation = (np_allocation - np_take_ips * np_ratio).clip(0.0, None)
                if has_allocation_item is not None and used_allocation_ratio:
                    np_allocation[np_allocation_index] = 0.0

                if np_limit is not None:
                    np_limit = (np_limit - np_make_main_ips * np_ratio).clip(0.0, None)
                    if (
                        np_limit is not None
                        and has_limit_item is not None
                        and used_limit_ratio
                    ):
                        np_limit[np_limit_index] = 0.0

                np_total_take_ips += np_take_ips * np_ratio
                np_total_make_main_ips += np_make_main_ips * np_ratio
                np_total_make_aux_ips += np_make_aux_ips * np_ratio

                keep_allocation = np.all(c_take[:, np_allocation == 0.0] == 0.0, axis=1)
                if np_limit is not None:
                    keep_limit = np.all(c_make_main[:, np_limit == 0.0] == 0.0, axis=1)
                    keep = keep_allocation & keep_limit
                else:
                    keep = keep_allocation
                c_take = c_take[keep, :]
                c_make_main = c_make_main[keep, :]
                c_make_aux = c_make_aux[keep, :]
                c_dt = c_dt[keep]

                count += 1

        assert 0 <= used <= 1.0, used

        # TODO indeed we do very few iterations, very often just 1
        # so most of the up-front work in the function here is a problem
        assert count <= crafting_count

        assert np_total_take_ips.dtype == np.float32
        assert np_total_make_main_ips.dtype == np.float32
        assert np_total_make_aux_ips.dtype == np.float32

        # dense_total_take_ips = np_zeros()
        # dense_total_take_ips[item_mask] = np_total_take_ips
        # dense_total_make_main_ips = np_zeros()
        # dense_total_make_main_ips[item_mask] = np_total_make_main_ips
        # dense_total_make_aux_ips = np_zeros()
        # dense_total_make_aux_ips[item_mask] = np_total_make_aux_ips

        return (
            np_total_take_ips,
            np_total_make_main_ips,
            np_total_make_aux_ips,
            # dense_total_take_ips,
            # dense_total_make_main_ips,
            # dense_total_make_aux_ips,
            used,
        )

    def wants_ips(
        self, takes: set[Item], makes: set[Item], speed: float, item: Item
    ) -> float:
        assert speed == 1.0
        match cached_wants_ips.get(
            (self.name, frozenset(takes), frozenset(makes), item), None
        ):
            case (float() | int()) as ips:
                # TODO I get almost no cache hits, how can that be?
                # ah no we do now, there was one early return ...
                # just goes to show that layering is better, should have decorated
                # or just write two functions, with a real and a _real, easier to split
                return ips
            case None:
                pass
        # TODO would it converge faster/better if we based it on the previous feasible allocation?
        # TODO this is the most expensive thing here, also might be cached ...
        levels: list[list[Crafting]] = self.get_enabled_crafting_levels(takes, makes)
        craftings: list[Crafting] = [crafting for level in levels for crafting in level]
        craftings = [crafting for crafting in craftings if crafting.take[item] > 0.0]
        enabled: list[bool | None] = [None] * len(craftings)
        while None in enabled:
            for k in range(len(craftings)):
                if enabled[k] is not None:
                    continue
                upper_bound = craftings[k].take[item] * self.pause
                lower_bound = craftings[k].take[item] * self.pause
                for i in range(len(craftings)):
                    if i == k:
                        continue
                    factor = (
                        craftings[k].take[item] * craftings[i].seconds(speed)
                        - craftings[k].seconds(speed) * craftings[i].take[item]
                    )
                    match enabled[i]:
                        case None:
                            upper_bound += clipped(0, factor, None)
                            lower_bound += clipped(None, factor, 0)
                        case True:
                            upper_bound += factor
                            lower_bound += factor
                        case False:
                            pass
                assert lower_bound <= upper_bound, (lower_bound, upper_bound)
                if lower_bound >= 0.0:
                    enabled[k] = True
                    break
                if upper_bound <= 0.0:
                    enabled[k] = False
                    break
            else:
                assert False, (
                    "could not find a single crafting that has become unconditional",
                    craftings,
                    enabled,
                )
        if not any(enabled):
            cached_wants_ips[self.name, frozenset(takes), frozenset(makes), item] = 0.0
            return 0.0
        enabled_craftings = [
            crafting for (enabled, crafting) in zips(enabled, craftings) if enabled
        ]
        ips = sum(crafting.take[item] for crafting in enabled_craftings) / (
            sum(crafting.seconds(speed) for crafting in enabled_craftings) + self.pause
        )
        cached_wants_ips[self.name, frozenset(takes), frozenset(makes), item] = ips
        return ips

    def limit_waste(
        self, takes: set[Item], makes: set[Item], speed: float, allocation: Ivec
    ) -> Ivec:
        take, _make_main, _make_aux, _used = self.allocate_ips(
            takes, makes, speed, allocation
        )
        return take

    def back_pressure(
        self,
        takes: set[Item],
        makes: set[Item],
        speed: float,
        allocation: Ivec,
        limit: Ivec,
    ) -> Ivec:
        take, _make_main, _make_aux, _used = self.allocate_ips(
            takes, makes, speed, allocation, limit
        )
        return take

    def np_back_pressure(
        self,
        takes: set[Item],
        makes: set[Item],
        speed: float,
        allocation: farray,
        limit: farray,
    ):
        take, _make_main, _make_aux, _used = self.np_allocate_ips_new_np(
            takes, makes, speed, allocation, limit
        )
        return take

    def usage_for(
        self,
        allocation: Ivec,
        limit: Ivec,
        takes: set[Item],
        makes: set[Item],
        speed: float,
    ) -> float:
        _take, _make_main, _make_aux, used = self.allocate_ips(
            takes, makes, speed, allocation, limit
        )
        return used

    def get_constraints(
        self,
        usage: Variable,
        takes: set[Item],
        makes: set[Item],
        speed: float,
    ) -> tuple[
        dict[Item, dict[Variable, float]],
        dict[Item, dict[Variable, float]],
        list[Equality],
        dict[Variable, float],  # minimization
    ]:
        # TODO remove
        assert False

    def takes_ips(
        self,
        take: Ivec | None,
        make: Ivec | None,
        takes: set[Item],
        makes: set[Item],
        speed: float,
    ) -> Ivec:
        return self.get_ips(take, make, takes, makes, speed).take

    def makes_ips(
        self,
        take: Ivec | None,
        make: Ivec | None,
        takes: set[Item],
        makes: set[Item],
        speed: float,
    ) -> Ivec:
        return self.get_ips(take, make, takes, makes, speed).make

    def representative_count_from_ips(self, item: Item, ips: float) -> float:
        rep = self.get_ips(None, None, self.get_take_items(), self.get_make_items(), 1)
        match rep.make[item]:
            case 0:
                return 0
            case r:
                return ips / r


@dataclass(frozen=True)
class ConfiguredGenericBuilding:
    building: BaseBuilding
    takes: set[Item]
    makes: set[Item]
    # NOTE this models how well the fields or collectable resources are placed, eg:
    # - farms: are the fields close?
    # - fishers: is the water close?
    speed: float  # 0 -> worst speed, 1 -> best speed

    def needs_ips(self, usage: float) -> Ivec:
        return self.building.needs_ips(self.takes, self.makes, self.speed, usage)

    def produces_ips(self, allocation: Ivec) -> tuple[Ivec, Ivec]:
        return self.building.produces_ips(
            self.takes, self.makes, self.speed, allocation
        )

    def np_produces_ips(self, allocation: farray) -> tuple[farray, farray]:
        return self.building.np_produces_ips(
            self.takes, self.makes, self.speed, allocation
        )

    # TODO instead we could precompute here and have it as a field?
    def wants_ips(self, item: Item) -> float:
        return self.building.wants_ips(self.takes, self.makes, self.speed, item)

    def limit_waste(self, allocation: Ivec) -> Ivec:
        return self.building.limit_waste(self.takes, self.makes, self.speed, allocation)

    def back_pressure(self, allocation: Ivec, limit: Ivec) -> Ivec:
        return self.building.back_pressure(
            self.takes, self.makes, self.speed, allocation, limit
        )

    def np_back_pressure(self, allocation: farray, limit: farray) -> farray:
        return self.building.np_back_pressure(
            self.takes, self.makes, self.speed, allocation, limit
        )

    def usage_for(self, allocation: Ivec, limit: Ivec) -> float:
        return self.building.usage_for(
            allocation, limit, self.takes, self.makes, self.speed
        )

    def takes_ips(self, take: Ivec | None = None, make: Ivec | None = None) -> Ivec:
        return self.building.takes_ips(take, make, self.takes, self.makes, self.speed)

    def makes_ips(self, take: Ivec | None = None, make: Ivec | None = None) -> Ivec:
        return self.building.makes_ips(take, make, self.takes, self.makes, self.speed)

    def get_constraints(
        self, usage: Variable
    ) -> tuple[
        dict[Item, dict[Variable, float]],
        dict[Item, dict[Variable, float]],
        list[Equality],
        dict[Variable, float],  # minimization
    ]:
        takes, makes, equalities, mins = self.building.get_constraints(
            usage, self.takes, self.makes, self.speed
        )
        return takes, makes, equalities, mins


type Building = BaseBuilding
type ConfiguredBuilding = ConfiguredGenericBuilding


@dataclass(frozen=True)
class BuildingCount:
    count: int
    building: ConfiguredBuilding
    # TODO using this to cheat a bit, as cache, but this doesnt really make Self immutable now
    wants: dict[Item, float] = field(default_factory=dict)

    def __post_init__(self):
        assert self.count >= 0

    def needs_ips(self, usage: float) -> Ivec:
        return self.building.needs_ips(usage).smul(self.count)

    def usage_for(self, allocation: Ivec, limit: Ivec) -> float:
        if self.count == 0:
            return 0.0
        return self.building.usage_for(
            allocation.sdiv(self.count), limit.sdiv(self.count)
        )

    def produces_ips(self, allocation: Ivec) -> tuple[Ivec, Ivec]:
        if self.count == 0:
            return izeros(), izeros()
        main, aux = self.building.produces_ips(allocation.sdiv(self.count))
        return main.smul(self.count), aux.smul(self.count)

    def np_produces_ips(self, allocation: farray) -> tuple[farray, farray]:
        if self.count == 0:
            return np_zeros(), np_zeros()
        main, aux = self.building.np_produces_ips(allocation / self.count)
        return main * self.count, aux * self.count

    def np_flooded(self, take_total: farray) -> farray:
        main, aux = self.np_produces_ips(take_total)
        return np.stack([main, aux])
        # return main + aux

    def wants_ips(self, item: Item) -> float:
        match self.wants.get(item, None):
            case None:
                w = self.building.wants_ips(item) * self.count
                self.wants[item] = w
                return w
            case (float() | int()) as w:
                return w

    def limit_waste(self, allocation: Ivec) -> Ivec:
        if self.count == 0:
            return izeros()
        return self.building.limit_waste(allocation.sdiv(self.count)).smul(self.count)

    def back_pressure(self, allocation: Ivec, limit: Ivec) -> Ivec:
        if self.count == 0:
            return izeros()
        return self.building.back_pressure(
            allocation.sdiv(self.count),
            limit.sdiv(self.count),
        ).smul(self.count)

    def np_back_pressure(self, allocation: farray, limit: farray) -> farray:
        if self.count == 0:
            return np_zeros()
        return (
            self.building.np_back_pressure(allocation / self.count, limit / self.count)
            * self.count
        )

    def takes_ips(self, take: Ivec | None = None, make: Ivec | None = None) -> Ivec:
        return self.building.takes_ips(take, make).smul(self.count)

    def makes_ips(self, take: Ivec | None = None, make: Ivec | None = None) -> Ivec:
        return self.building.makes_ips(take, make).smul(self.count)

    def get_constraints(
        self,
    ) -> tuple[
        dict[Item, dict[Variable, float]],
        dict[Item, dict[Variable, float]],
        list[Equality],
        Variable,
        dict[Variable, float],  # minimization
    ]:
        # TODO these descs are not fully unique, but makes it easier to debug the qp
        usage = Variable(f"{self.building.building.name.value}/usage", 0.0, 1.0)
        idle = Variable(f"{self.building.building.name.value}/idle", 0.0, 1.0)

        equations: list[Equality] = []
        equations.append(Equality({usage: 1.0, idle: 1.0}, 1.0))

        takes, makes, equalities, mins = self.building.get_constraints(usage)

        equations.extend(equalities)

        takes = {
            item: {var: (self.count * weight) for (var, weight) in vars.items()}
            for (item, vars) in takes.items()
        }

        makes = {
            item: {var: (self.count * weight) for (var, weight) in vars.items()}
            for (item, vars) in makes.items()
        }

        mins = {v: (self.count * w) for (v, w) in mins.items()}

        return takes, makes, equations, idle, mins


def extract_plain_timings(path: Path) -> tuple[float, float]:
    lua = path.read_text()

    matches = list(
        re.finditer(r"^ *-- time total:.*= (?P<value>[\d.]*) sec$", lua, re.MULTILINE)
    )
    match matches:
        case [m]:
            t = float(m["value"])
            return t, t
        case _:
            pass

    [m_min] = re.finditer(
        r"^ *-- min\. time total:.*= *(?P<value>[\d.]*) sec$", lua, re.MULTILINE
    )
    [m_max] = re.finditer(
        r"^ *-- max\. time total:.*= *(?P<value>[\d.]*) sec$", lua, re.MULTILINE
    )
    return float(m_min["value"]), float(m_max["value"])


# TODO with cache, we need only this, no dictionary from the other function
@cache
def building_from_name(name: Bname) -> Building:
    b = partial(BaseBuilding.from_lua, timings=name.name, name=name)
    # TODO extracting take and make is difficult from the custom lua programs strings
    match name:
        case Bname.foresters_house:
            return b({}, {Item.tree: 1})
        case Bname.fishers_house:
            return b({}, {Item.fish: 1})
        case Bname.woodcutters_house:
            return b({Item.tree: 1}, {Item.log: 1})
        case Bname.well:
            # TODO different when depleted
            return b({}, {Item.water: 1})
        case Bname.farm:
            return b({}, {Item.barley: 2})
        case Bname.reed_farm:
            return b({}, {Item.reed: 1})
        case Bname.coalmine:
            # TODO different when depleted
            return b({Item.ration: 1}, {Item.coal: 2})
        case Bname.rockmine:
            # TODO different when depleted
            return b({Item.ration: 1}, {Item.granite: 2})
        case Bname.ironmine:
            # TODO different when depleted
            return b({Item.ration: 1}, {Item.iron_ore: 1})
        case Bname.goldmine:
            # TODO different when depleted
            return b({Item.ration: 1}, {Item.gold_ore: 1})
        case Bname.clay_pit:
            return b({Item.water: 1}, {Item.clay: 1})
        case Bname.brick_kiln:
            return b({Item.coal: 1, Item.clay: 3, Item.granite: 1}, {Item.brick: 3})
        case Bname.collectors_house:
            return b({Item.berry_bush: 1}, {Item.fruit: 1})
        case Bname.beekeepers_house:
            # TODO not quite, not the same bush as collector, right?
            # hmm they just have to be there, so if the collectors are too
            # many its a problem? not clear, maybe while growing they are good too?
            # workers/frisians/beekeeper/init.lua says "attrib:flowering"
            # flowering seems to be before ripe, so maybe we need 0 berry_bush production
            return b({Item.berry_bush: 0.1}, {Item.honey: 1})
        case Bname.berry_farm:
            return b({}, {Item.berry_bush: 1})
        case Bname.brewery:
            return b({Item.barley: 1, Item.water: 1}, {Item.beer: 1})
        case Bname.mead_brewery:
            # TODO normal bear a bit faster here (10%)
            return BaseBuilding(
                name,
                [
                    [
                        Crafting(
                            ifrom({Item.barley: 1, Item.water: 1, Item.honey: 1}),
                            ifrom({Item.mead: 1}),
                            izeros(),
                            (65.667, 65.667),
                        ),
                        Crafting(
                            ifrom({Item.barley: 1, Item.water: 1}),
                            ifrom({Item.beer: 1}),
                            izeros(),
                            (60.667, 60.667),
                        ),
                        Crafting(
                            ifrom({Item.barley: 1, Item.water: 1, Item.honey: 1}),
                            ifrom({Item.mead: 1}),
                            izeros(),
                            (65.667, 65.667),
                        ),
                    ]
                ],
                10,
            )
        case Bname.bakery:
            return b({Item.barley: 1, Item.water: 1}, {Item.bread: 1})
        case Bname.honey_bread_bakery:
            # TODO normal bread a bit faster here (10%)
            # but it has two workers, does it mean running 2 worker programs?
            return BaseBuilding(
                name,
                [
                    [
                        Crafting(
                            ifrom({Item.barley: 1, Item.water: 1, Item.honey: 1}),
                            ifrom({Item.honey_bread: 1}),
                            izeros(),
                            (45.667, 45.667),
                        ),
                        Crafting(
                            ifrom({Item.barley: 1, Item.water: 1}),
                            ifrom({Item.bread: 1}),
                            izeros(),
                            (40.667, 40.667),
                        ),
                        Crafting(
                            ifrom({Item.barley: 1, Item.water: 1, Item.honey: 1}),
                            ifrom({Item.honey_bread: 1}),
                            izeros(),
                            (45.667, 45.667),
                        ),
                    ]
                ],
                10,
            )
        case Bname.barracks:
            return b({Item.fur_garment: 1, Item.short_sword: 1}, {})
        case Bname.sewing_room:
            return b({Item.fur: 2}, {Item.fur_garment: 1})
        case Bname.tailors_shop:
            return BaseBuilding(
                name,
                [
                    [
                        Crafting(
                            ifrom({Item.fur_garment: 1, Item.iron: 1}),
                            ifrom({Item.studded_fur_garment: 1}),
                            izeros(),
                            (49, 49),
                        ),
                        Crafting(
                            ifrom({Item.fur_garment: 1, Item.iron: 1, Item.gold: 1}),
                            ifrom({Item.golden_fur_garment: 1}),
                            izeros(),
                            (49, 49),
                        ),
                    ]
                ],
                10,
            )
        case Bname.blacksmithy:
            dt = (70.167, 70.167)
            # TODO hm maybe could be extracted? timings at least
            return BaseBuilding(
                name,
                crafting_levels=[
                    [
                        Crafting(
                            ifrom({Item.iron: 1, Item.log: 1}),
                            ifrom({i: 1}),
                            izeros(),
                            dt,
                        )
                        for i in {
                            Item.pick,
                            Item.felling_axe,
                            Item.shovel,
                            Item.hammer,
                            Item.hunting_spear,
                            Item.scythe,
                            Item.bread_paddle,
                            Item.kitchen_tools,
                        }
                    ]
                    + [
                        Crafting(
                            ifrom({Item.iron: 1}),
                            ifrom({Item.needles: 2}),
                            izeros(),
                            dt,
                        ),
                        Crafting(
                            ifrom({Item.reed: 1, Item.log: 1}),
                            ifrom({Item.basket: 1}),
                            izeros(),
                            dt,
                        ),
                        Crafting(
                            ifrom({Item.iron: 1}),
                            ifrom({Item.fire_tongs: 1}),
                            izeros(),
                            dt,
                        ),
                        Crafting(
                            ifrom({Item.reed: 2}),
                            ifrom({Item.fishing_net: 1}),
                            izeros(),
                            dt,
                        ),
                    ]
                ],
                pause=10,
            )
        case Bname.tavern:
            # TODO here we wrote all combinations
            # this part could be coded? but not clear how we model a full cycle
            return BaseBuilding(
                name,
                crafting_levels=[
                    [
                        Crafting(
                            ifrom({Item.fruit: 1, Item.smoked_fish: 1}),
                            ifrom({Item.ration: 2}),
                            izeros(),
                            (74, 74),
                        ),
                        Crafting(
                            ifrom({Item.fruit: 1, Item.smoked_meat: 1}),
                            ifrom({Item.ration: 2}),
                            izeros(),
                            (74, 74),
                        ),
                        Crafting(
                            ifrom({Item.bread: 1, Item.smoked_fish: 1}),
                            ifrom({Item.ration: 2}),
                            izeros(),
                            (74, 74),
                        ),
                        Crafting(
                            ifrom({Item.bread: 1, Item.smoked_meat: 1}),
                            ifrom({Item.ration: 2}),
                            izeros(),
                            (74, 74),
                        ),
                    ],
                    [
                        Crafting(
                            ifrom({Item.fruit: 1}),
                            ifrom({Item.ration: 1}),
                            izeros(),
                            (55, 55),
                        ),
                        Crafting(
                            ifrom({Item.bread: 1}),
                            ifrom({Item.ration: 1}),
                            izeros(),
                            (55, 55),
                        ),
                        Crafting(
                            ifrom({Item.smoked_fish: 1}),
                            ifrom({Item.ration: 1}),
                            izeros(),
                            (55, 55),
                        ),
                        Crafting(
                            ifrom({Item.smoked_meat: 1}),
                            ifrom({Item.ration: 1}),
                            izeros(),
                            (55, 55),
                        ),
                    ],
                ],
                pause=0,
            )
        case Bname.smokery:
            return BaseBuilding(
                name,
                [
                    [
                        Crafting(
                            ifrom({Item.log: 1, Item.fish: 2}),
                            ifrom({Item.smoked_fish: 2}),
                            izeros(),
                            (54, 54),
                        ),
                        Crafting(
                            ifrom({Item.log: 1, Item.meat: 2}),
                            ifrom({Item.smoked_meat: 2}),
                            izeros(),
                            (54, 54),
                        ),
                    ]
                ],
                0,
            )
        case Bname.furnace:
            return BaseBuilding(
                name,
                [
                    [
                        Crafting(
                            ifrom({Item.coal: 1, Item.iron_ore: 1}),
                            ifrom({Item.iron: 1}),
                            izeros(),
                            (64, 64),
                        ),
                        Crafting(
                            ifrom({Item.coal: 1, Item.gold_ore: 1}),
                            ifrom({Item.gold: 1}),
                            izeros(),
                            (66, 66),
                        ),
                        Crafting(
                            ifrom({Item.coal: 1, Item.iron_ore: 1}),
                            ifrom({Item.iron: 1}),
                            izeros(),
                            (64, 64),
                        ),
                    ]
                ],
                0,
            )
        case Bname.armor_smithy_small:
            return BaseBuilding(
                name,
                [
                    [
                        Crafting(
                            ifrom({Item.coal: 1, Item.iron: 1}),
                            ifrom({Item.short_sword: 1}),
                            izeros(),
                            (58, 58),
                        ),
                        Crafting(
                            ifrom({Item.coal: 1, Item.iron: 2}),
                            ifrom({Item.long_sword: 1}),
                            izeros(),
                            (58, 58),
                        ),
                        Crafting(
                            ifrom({Item.coal: 1, Item.iron: 1}),
                            ifrom({Item.helmet: 1}),
                            izeros(),
                            (68, 68),
                        ),
                    ]
                ],
                10,
            )
        case Bname.armor_smithy_large:
            return BaseBuilding(
                name,
                [
                    [
                        Crafting(
                            ifrom({Item.coal: 1, Item.iron: 2, Item.gold: 1}),
                            ifrom({Item.broadsword: 1}),
                            izeros(),
                            (58.8, 58.8),
                        ),
                        Crafting(
                            ifrom({Item.coal: 2, Item.iron: 2, Item.gold: 1}),
                            ifrom({Item.double_edged_sword: 1}),
                            izeros(),
                            (58.8, 58.8),
                        ),
                        Crafting(
                            ifrom({Item.coal: 2, Item.iron: 2, Item.gold: 1}),
                            ifrom({Item.golden_helmet: 1}),
                            izeros(),
                            (68.8, 68.8),
                        ),
                        Crafting(
                            ifrom({Item.coal: 1, Item.iron: 2, Item.gold: 1}),
                            ifrom({Item.broadsword: 1}),
                            izeros(),
                            (58.8, 58.8),
                        ),
                        Crafting(
                            ifrom({Item.coal: 2, Item.iron: 2, Item.gold: 1}),
                            ifrom({Item.double_edged_sword: 1}),
                            izeros(),
                            (58.8, 58.8),
                        ),
                    ]
                ],
                10,
            )
        case Bname.reindeer_farm:
            return BaseBuilding(
                name,
                [
                    [
                        Crafting(
                            ifrom({Item.water: 1, Item.barley: 1}),
                            ifrom({Item.deer: 1}),
                            izeros(),
                            (30, 30),
                        ),
                        Crafting(
                            ifrom({Item.water: 1, Item.barley: 1}),
                            ifrom({Item.fur: 1}),
                            izeros(),
                            (38.6, 38.6),
                        ),
                        Crafting(
                            ifrom({Item.water: 1, Item.barley: 1}),
                            ifrom({Item.deer: 1}),
                            izeros(),
                            (30, 30),
                        ),
                        Crafting(
                            ifrom({Item.water: 1, Item.barley: 1}),
                            ifrom({Item.fur: 1}),
                            izeros(),
                            (38.6, 38.6),
                        ),
                        Crafting(
                            ifrom({Item.water: 1, Item.barley: 1}),
                            ifrom({Item.deer: 1}),
                            izeros(),
                            (30, 30),
                        ),
                        Crafting(
                            ifrom({Item.water: 1, Item.barley: 1}),
                            ifrom({Item.fur: 1}),
                            ifrom({Item.meat: 1}),
                            (42.2, 42.2),
                        ),
                    ]
                ],
                0,
            )
        case Bname.training_camp:
            # TODO timings not quite clear here, or order
            # plus hard to say what is happening when we dont know
            # what level soldiers are available in the queue
            # unless you limit it to only one kind of equipment?
            # but then what if all soldiers are stuck
            # do they leave when max, or when no chance to update more?
            # TODO also not modeling soldier production, how to treat them?
            return BaseBuilding(
                name,
                [
                    [  # attack 1
                        Crafting(
                            # TODO hmm ok just one of many foods ... dont have a good way to model it
                            # and which one would be taken, random uniform, always first?
                            ifrom({Item.long_sword: 1, food: 1}),
                            # TODO technically it backpressures on soldier level needed?
                            izeros(),
                            ifrom({Item.scrap_iron: 1}),
                            (36 + 6, 36 + 6),  # NOTE not sure about the +6
                        )
                        for food in {Item.bread, Item.smoked_fish, Item.smoked_meat}
                    ]
                    + [  # attack 2
                        Crafting(
                            ifrom({Item.broadsword: 1, Item.bread: 1, meat: 1}),
                            izeros(),
                            ifrom({Item.scrap_iron: 2}),
                            (36 + 6, 36 + 6),  # NOTE not sure about the +6
                        )
                        for meat in {Item.smoked_fish, Item.smoked_meat}
                    ]
                    + [  # attack 3
                        Crafting(
                            ifrom({Item.double_edged_sword: 1, Item.beer: 1, meat: 1}),
                            izeros(),
                            ifrom({Item.scrap_iron: 1, Item.mixed_scrap_metal: 1}),
                            (36 + 6, 36 + 6),  # NOTE not sure about the +6
                        )
                        for meat in {Item.smoked_fish, Item.smoked_meat}
                    ]
                    + [  # health 1
                        Crafting(
                            ifrom({Item.helmet: 1, food1: 1, food2: 1}),
                            ifrom({}),
                            izeros(),
                            (36 + 6, 36 + 6),  # NOTE not sure about the +6
                        )
                        for food1 in {Item.bread, Item.beer}
                        for food2 in {Item.smoked_fish, Item.smoked_meat}
                    ]
                    + [  # defense 1
                        Crafting(
                            ifrom({Item.studded_fur_garment: 1, food1: 1, food2: 1}),
                            izeros(),
                            # TODO how does this go with maximization? we might not care for old_* and scrap metal, but we dont want to limit it
                            ifrom({Item.old_fur_garment: 1}),
                            (36 + 6, 36 + 6),  # NOTE not sure about the +6
                        )
                        for food1 in {Item.bread, Item.beer}
                        for food2 in {Item.smoked_fish, Item.smoked_meat}
                    ]
                ],
                0,
            )
        case Bname.training_arena:
            # TODO same as for training camp
            return BaseBuilding(
                name,
                [
                    [  # attack 4
                        Crafting(
                            ifrom({Item.long_sword: 1, food1: 1, food2: 1}),
                            ifrom({}),
                            izeros(),
                            (28.8 + 6, 28.8 + 6),  # NOTE not sure about the +6
                        )
                        for food1 in {Item.honey_bread, Item.mead}
                        for food2 in {Item.smoked_fish, Item.smoked_meat}
                    ]
                    + [  # attack 5
                        Crafting(
                            # TODO not clear of food2 is two of the same, or any two ...
                            ifrom({Item.broadsword: 1, food1: 1, food2: 2}),
                            izeros(),
                            ifrom({Item.scrap_iron: 2}),
                            (28.8 + 6, 28.8 + 6),  # NOTE not sure about the +6
                        )
                        for food1 in {Item.honey_bread, Item.mead}
                        for food2 in {Item.smoked_fish, Item.smoked_meat}
                    ]
                    + [  # attack 6
                        Crafting(
                            ifrom(
                                {
                                    Item.double_edged_sword: 1,
                                    Item.honey_bread: 1,
                                    Item.mead: 1,
                                    food: 1,
                                }
                            ),
                            izeros(),
                            ifrom({Item.scrap_iron: 1, Item.mixed_scrap_metal: 1}),
                            (28.8 + 6, 28.8 + 6),  # NOTE not sure about the +6
                        )
                        for food in {Item.smoked_fish, Item.smoked_meat}
                    ]
                    + [  # defense 2
                        Crafting(
                            ifrom({Item.golden_fur_garment: 1, food1: 1, food2: 1}),
                            izeros(),
                            ifrom({Item.scrap_iron: 1, Item.old_fur_garment: 1}),
                            (36 + 6, 36 + 6),  # NOTE not sure about the +6
                        )
                        for food1 in {Item.honey_bread, Item.mead}
                        for food2 in {Item.smoked_fish, Item.smoked_meat}
                    ]
                    + [  # health 2
                        Crafting(
                            ifrom({Item.golden_helmet: 1, food1: 1, food2: 1}),
                            izeros(),
                            ifrom({Item.scrap_iron: 1}),
                            (32.4 + 6, 32.4 + 6),  # NOTE not sure about the +6
                        )
                        for food1 in {Item.honey_bread, Item.mead}
                        for food2 in {Item.smoked_fish, Item.smoked_meat}
                    ]
                ],
                0,
            )
        case _ as never:
            assert_never(never)


# TODO mutable, maybe dangerous to cache?
@cache
def get_buildings() -> Mapping[Bname, Building]:
    buildings = {name: building_from_name(name) for name in Bname}
    return dict(sorted(buildings.items()))


def get_takes_ips(buildings: list[BuildingCount]) -> Ivec:
    return isum([b.takes_ips() for b in buildings])


def get_makes_ips(buildings: list[BuildingCount]) -> Ivec:
    return isum([b.makes_ips() for b in buildings])


def get_balance_ips(buildings: list[BuildingCount]) -> Ivec:
    return get_makes_ips(buildings).sub(get_takes_ips(buildings))


def get_shortages_ips(buildings: list[BuildingCount]) -> Ivec:
    return get_balance_ips(buildings).negate().keep_positives()


def get_usage_ratios(buildings: list[BuildingCount]) -> Ivec:
    # TODO work with float | something instead of infs?
    return get_takes_ips(buildings).div(get_makes_ips(buildings))


@dataclass(frozen=True)
class Block:
    buildings: list[BuildingCount]


@dataclass(frozen=True)
class BlockBalance:
    imports: Ivec
    local: Ivec
    exports: Ivec


def get_block_balance(block: Block) -> BlockBalance:
    balance = get_balance_ips(block.buildings)
    exports: dict[Item, float] = dict()
    local: dict[Item, float] = dict()
    imports: dict[Item, float] = dict()
    for i, b in balance.data.items():
        if b == 0:
            continue
        local[i] = b
    return BlockBalance(
        imports=ifrom(imports),
        local=ifrom(local),
        exports=ifrom(exports),
    )


def get_global_balance(blocks: list[BlockBalance]) -> Ivec:
    imports = [b.imports.negate() for b in blocks]
    exports = [b.exports for b in blocks]
    return isum(imports + exports)


def building_count_from_ips(item: Item, ips: float) -> list[tuple[Bname, float]]:
    counts: list[tuple[Bname, float]] = []
    # TODO keep around?
    for name, building in get_buildings().items():
        c = building.representative_count_from_ips(item, ips)
        if c != 0:
            counts.append((name, c))
    return counts


def iterative(blocks: list[Block]) -> tuple[Ivec, Ivec]:
    # TODO init with last solution?
    take: Ivec | None = None
    last_take: Ivec | None = None
    make: Ivec | None = None
    last_make: Ivec | None = None

    for _ in range(100):
        if not (
            take is None
            or make is None
            or last_take is None
            or last_make is None
            # TODO 0.1 / 60 ... i want in ipm to be to one digit
            # but that maybe doesnt always make sense?
            or not last_take.almost_equal(take, 0.1 / 60)
            or not last_make.almost_equal(make, 0.1 / 60)
            # TODO there also has to be more logic to stop when no changes left
            # if we try to consume more trees than there are, we go to max iter
        ):
            break
        last_take, last_make = take, make
        take, make = izeros(), izeros()
        for block in blocks:
            for count in block.buildings:
                take = take.add(count.takes_ips(last_take, last_make))
                make = make.add(count.makes_ips(last_take, last_make))
    else:
        print("too many iterations")

    # TODO or close enough
    assert take.lte(make)  # pyright: ignore[reportArgumentType, reportOptionalMemberAccess]

    # TODO really need a dataclass for this, so easy to flip
    return take, make  # pyright: ignore[reportReturnType]


@dataclass(frozen=True)
class Variable:
    desc: str
    lb: None | float
    ub: None | float

    @override
    def __eq__(self, other: object) -> bool:
        return id(self) == id(other)


@dataclass
class Equality:
    """weighted vars == const"""

    vars: dict[Variable, float]
    # TODO are data classes better, or just plain dicts? None could be the key for the constant?
    const: float

    def variables(self) -> set[Variable]:
        return set(self.vars)


@dataclass
class Inequality:
    """weighted vars <= const"""

    vars: dict[Variable, float]
    const: float


# def build_qp(
#     min: dict[Variable, float], equations: Sequence[Equality]
# ) -> tuple[list[Variable], Problem]:
#     vars = set(min) | {var for equation in equations for var in equation.variables()}
#     vars = list(vars)
#     N = len(vars)
#     K = len(equations)
#
#     lb = np.array(
#         [-math.inf if var.lb is None else var.lb for var in vars], dtype=np.float32
#     )
#     ub = np.array(
#         [-math.inf if var.ub is None else var.ub for var in vars], dtype=np.float32
#     )
#
#     P = np.zeros([N, N], dtype=np.float32)
#     for var, w in min.items():
#         i = vars.index(var)
#         P[i, i] = w
#
#     A = np.zeros([K, N], dtype=np.float32)
#     b = np.zeros([K], dtype=np.float32)
#     for i, eq in enumerate(equations):
#         for var, weight in eq.vars.items():
#             A[i, vars.index(var)] = weight
#         b[i] = eq.const
#
#     problem = Problem(
#         P=P,
#         q=np.zeros([N], dtype=np.float32),
#         A=A,
#         b=b,
#         lb=lb,
#         ub=ub,
#     )
#
#     return vars, problem


# def qp(blocks: list[Block]) -> tuple[list[str], Solution] | None:
#     counts = [count for block in blocks for count in block.buildings]
#     if len(counts) == 0:
#         return None
#
#     balances: dict[Item, Equality] = {i: Equality(dict(), 0.0) for i in Item}
#     idles: list[Variable] = []
#     equations: list[Equality] = []
#     mins: dict[Variable, float] = dict()
#
#     for count in counts:
#         take, make, eqs, idle, ms = count.get_constraints()
#         for item, weights in take.items():
#             for var, weight in weights.items():
#                 # TODO there should never be the variable existing already
#                 balances[item].vars[var] = balances[item].vars.get(var, 0.0) - weight
#         for item, weights in make.items():
#             for var, weight in weights.items():
#                 balances[item].vars[var] = balances[item].vars.get(var, 0.0) + weight
#         equations.extend(eqs)
#         idles.append(idle)
#         mins.update(ms)
#
#     def has_consumption(equation: Equality) -> bool:
#         return any(v < 0.0 for v in equation.vars.values())
#
#     balances = {
#         item: equation
#         for (item, equation) in balances.items()
#         # TODO its nice and clean, but we might not want that after all?
#         # adding a building could bring everything to zero, maybe have options
#         # anyway options for exploring the solution space and seeing how much is needed?
#         if has_consumption(equation)
#     }
#
#     vars, problem = build_qp(mins, list(balances.values()) + equations)
#     # TODO clarabel likes scipy.sparse.csc_matrix for speed, and no warnings
#     # TODO also, if it fails with numerical error, how do we see that?
#     solution = solve_problem(problem, solver="clarabel")
#
#     return [var.desc for var in vars], solution


def consumption_from_allocated(allocated: list[Allocated]) -> Ivec:
    return isum(alloc.take_total() for alloc in allocated)


def full_production_from_allocated(allocated: list[Allocated]) -> Ivec:
    return isum(alloc.make_full_total() for alloc in allocated)


def np_flood_forward(state: SolverState) -> SolverState:
    index = state.index

    aproduction = np.sum(state.production, axis=2)
    last_aproduction = None

    aconsumption = np.sum(state.consumption, axis=2)
    last_aconsumption = None

    wants = np.zeros_like(aconsumption)
    for i, b in enumerate(state.buildings):
        wants[*index[i], :] = [b.wants_ips(item) for item in Item]

    count = 0

    while (
        last_aconsumption is None
        or last_aproduction is None
        or (
            np.any(np.abs(last_aconsumption - aconsumption) > ips_eps)
            or np.any(np.abs(last_aproduction - aproduction) > ips_eps)
        )
    ):
        last_last_aconsumption = last_aconsumption
        last_aconsumption = aconsumption
        last_aproduction = aproduction

        total_production = np.sum(aproduction, axis=(0, 1, 2))
        total_consumption = np.sum(aconsumption, axis=(0, 1))
        surplus = (total_production - total_consumption).clip(0.0, None)
        demands = (wants - aconsumption).clip(0.0, None)
        total_demands = np.sum(demands, axis=(0, 1))
        ratios = np.divide(
            surplus,
            total_demands,
            where=total_demands > 0.0,
            out=np.full_like(total_demands, 0.0),
        ).clip(0.0, 1.0)

        aconsumption = aconsumption + demands * ratios[None, None, :]

        def maybe_flood(i: int, b: BuildingCount) -> farray:
            ii = index[i]
            # TODO this could be vectorized then? we should actually cheaply know from above what might have changed
            if last_last_aconsumption is not None and np.all(
                last_last_aconsumption[*ii, :] == aconsumption[*ii, :]
            ):
                # TODO or return nothing and initialize aproduction with old data?
                return aproduction[*ii, :, :]
            return b.np_flooded(aconsumption[*ii, :])

        aproduction = np.zeros_like(aproduction)
        for i, b in enumerate(state.buildings):
            aproduction[*index[i], :, :] = maybe_flood(i, b)

        count += 1

    consumption = state.consumption.copy()
    consumption[:, :, 0, :] = 0.0
    consumption[:, :, 1, :] = aconsumption

    production = state.production.copy()
    production[:, :, 0, :, :] = 0.0
    # TODO not sure why we cant use aproduction from the last iteration here
    # production[:, :, 1, :, :] = aproduction
    for i, b in enumerate(state.buildings):
        production[*index[i], 1, :, :] = b.np_flooded(aconsumption[*index[i], :])

    print(f"{count} flooding iterations")

    return SolverState(state.buildings, index, production, consumption)


def np_allocated(
    allocated: list[Allocated],
) -> tuple[farray, farray, list[tuple[int, int]]]:
    block_ids = list({id(alloc.block) for alloc in allocated})

    B: Final = len(block_ids)
    N: Final = max(Counter(id(alloc.block) for alloc in allocated).values())
    I: Final = len(Item)

    counts = [0] * B
    index: list[tuple[int, int]] = []
    for alloc in allocated:
        b = block_ids.index(id(alloc.block))
        counts[b] += 1
        index.append((b, counts[b] - 1))
    assert all(c <= N for c in counts), (N, counts)

    # [block, building, local/remote, main/aux, item]
    production = np.zeros([B, N, 2, 2, I])

    # [block, building, local/remote, item]
    consumption = np.zeros([B, N, 2, I])

    for i, alloc in enumerate(allocated):
        production[*index[i], 0, 0, :] = np_from_ivec(alloc.make_main_local)
        production[*index[i], 1, 0, :] = np_from_ivec(alloc.make_main_remote)
        production[*index[i], 0, 1, :] = np_from_ivec(alloc.make_aux_local)
        production[*index[i], 1, 1, :] = np_from_ivec(alloc.make_aux_remote)
        consumption[*index[i], 0, :] = np_from_ivec(alloc.take_local)
        consumption[*index[i], 1, :] = np_from_ivec(alloc.take_remote)

    return production, consumption, index


def np_unallocated(
    allocated: list[Allocated],
    production: farray,
    consumption: farray,
    index: list[tuple[int, int]],
) -> list[Allocated]:
    return [
        alloc.__replace__(
            take_local=ivec_from_np(consumption[*index[i], 0, :]),
            take_remote=ivec_from_np(consumption[*index[i], 1, :]),
            make_main_local=ivec_from_np(production[*index[i], 0, 0, :]),
            make_main_remote=ivec_from_np(production[*index[i], 1, 0, :]),
            make_aux_local=ivec_from_np(production[*index[i], 0, 1, :]),
            make_aux_remote=ivec_from_np(production[*index[i], 1, 1, :]),
        )
        for i, alloc in enumerate(allocated)
    ]


def np_prefer_local(state: SolverState) -> SolverState:
    anywhere_production = np.sum(state.production, axis=2)
    anywhere_consumption = np.sum(state.consumption, axis=2)

    block_production = np.sum(anywhere_production, axis=(1, 2))
    block_consumption = np.sum(anywhere_consumption, axis=1)

    ratio_take = np.divide(
        block_production,
        block_consumption,
        where=block_consumption > 0.0,
        out=np.full_like(block_production, 0.0),
    ).clip(0.0, 1.0)

    ratio_make = np.divide(
        block_consumption,
        block_production,
        where=block_production > 0.0,
        out=np.full_like(block_consumption, 0.0),
    ).clip(0.0, 1.0)

    consumption = np.stack(
        [
            anywhere_consumption * ratio_take[:, None, :],
            anywhere_consumption * (1.0 - ratio_take[:, None, :]),
        ],
        axis=2,
    )

    production = np.stack(
        [
            anywhere_production * ratio_make[:, None, None, :],
            anywhere_production * (1.0 - ratio_make[:, None, None, :]),
        ],
        axis=2,
    )

    return SolverState(state.buildings, state.index, production, consumption)


def np_back_reallocated(
    remote_consumption: np.typing.NDArray[np.floating],
    local_consumption: np.typing.NDArray[np.floating],
    limit: np.typing.NDArray[np.floating],
) -> tuple[np.typing.NDArray[np.floating], np.typing.NDArray[np.floating]]:
    local_consumption = np.minimum(local_consumption, limit)
    remote_consumption = limit - local_consumption
    return remote_consumption, local_consumption


def np_back_pressure(state: SolverState) -> tuple[SolverState, set[Item]]:
    last_production = None
    last_consumption = None

    index = state.index
    production = state.production.copy()
    consumption = state.consumption.copy()

    # TODO always the same
    leaf_items = set(Item) - {
        item for b in state.buildings for item in b.building.takes
    }
    leaves = np_from_ivec(ifrom({i: 1.0 for i in leaf_items})) > 0

    count = 0

    while (
        last_production is None
        or last_consumption is None
        or (
            np.any(np.abs(last_production - production) > ips_eps)
            or np.any(np.abs(last_consumption - consumption) > ips_eps)
        )
    ):
        last_last_production = last_production
        last_last_consumption = last_consumption

        last_production = production.copy()
        last_consumption = consumption.copy()

        total_production = np.sum(production[:, :, 0, :, :], axis=1)
        total_consumption = np.sum(consumption[:, :, 0, :], axis=1)
        keep_ratio = np.divide(
            total_consumption - total_production[:, 1, :],
            total_production[:, 0, :],
            where=total_production[:, 0, :] > 0.0,
            out=np.ones_like(total_consumption),
        )
        keep_ratio = keep_ratio.clip(0.0, 1.0)
        # TODO precompute? or better way for broadcasting? could do in where of np.divide
        keep_ratio[np.broadcast_to(leaves[None, :], keep_ratio.shape)] = 1.0

        global_production = np.sum(production[:, :, 1, :, :], axis=(0, 1))
        global_consumption = np.sum(consumption[:, :, 1, :], axis=(0, 1))
        global_keep_ratio = np.divide(
            global_consumption - global_production[1, :],
            global_production[0, :],
            where=global_production[0, :] > 0.0,
            out=np.ones_like(global_consumption),
        )
        global_keep_ratio = global_keep_ratio.clip(0.0, 1.0)
        global_keep_ratio[leaves] = 1.0

        # TODO better broadcasting?
        # TODO curious that we dont change aux here ever in the iterations
        production[:, :, 0, 0, :] = production[:, :, 0, 0, :] * keep_ratio[:, None, :]
        production[:, :, 1, 0, :] = (
            production[:, :, 1, 0, :] * global_keep_ratio[None, None, :]
        )

        for i, b in enumerate(state.buildings):
            # TODO this can be done cheaper now
            # TODO why last_last? might be suboptimal, try when everything else is fine again
            if (
                last_last_consumption is not None
                and last_last_production is not None
                and np.all(
                    np.sum(consumption[*index[i], :, :], axis=0)
                    == np.sum(last_last_consumption[*index[i], :, :], axis=0)
                )
                and np.all(
                    np.sum(production[*index[i], :, :, :], axis=(0, 1))
                    == np.sum(last_last_production[*index[i], :, :, :], axis=(0, 1))
                )
            ):
                continue
            new_consumption = b.np_back_pressure(
                np.sum(consumption[*index[i], :, :], axis=0),
                # TODO hm should we pass aux as limit?
                np.sum(production[*index[i], :, :, :], axis=(0, 1)),
            )
            new_remote, new_local = np_back_reallocated(
                consumption[*index[i], 1, :],
                consumption[*index[i], 0, :],
                new_consumption,
            )
            consumption[*index[i], 1, :] = new_remote
            consumption[*index[i], 0, :] = new_local

        count += 1

    print(f" {count} pressure iterations")

    return SolverState(
        state.buildings, state.index, production, consumption
    ), leaf_items


# TODO a value here that is lower will make it much faster too
# best would be something that is within percent ranges, because this is what you really see
ips_eps: Final = 0.01 / 4 / 60


# TODO assumes those two are parallel and zip
def have_allocations_converged(a: list[Allocated] | None, b: list[Allocated]) -> bool:
    if a is None:
        return False
    return all(
        i.take_local.almost_equal(j.take_local, ips_eps)
        and i.take_remote.almost_equal(j.take_remote, ips_eps)
        and i.make_main_local.almost_equal(j.make_main_local, ips_eps)
        and i.make_aux_local.almost_equal(j.make_aux_local, ips_eps)
        and i.make_main_remote.almost_equal(j.make_main_remote, ips_eps)
        and i.make_aux_remote.almost_equal(j.make_aux_remote, ips_eps)
        for i, j in zips(a, b, strict=True)
    )


def rounded_allocations(allocations: Sequence[Allocated]) -> list[Allocated]:
    return [alloc.rounded(ips_eps) for alloc in allocations]


@dataclass(frozen=True)
class Allocated:
    block: Block
    building: BuildingCount

    take_local: Ivec
    take_remote: Ivec

    make_main_local: Ivec
    make_aux_local: Ivec
    make_main_remote: Ivec
    make_aux_remote: Ivec

    flood_usage: float
    stable_usage: float
    is_infinite: bool  # if all production are leaf items, we are never limited

    @classmethod
    def from_init(cls, block: Block, building: BuildingCount):
        return cls(
            block=block,
            building=building,
            take_local=izeros(),
            take_remote=izeros(),
            make_main_local=izeros(),
            make_aux_local=izeros(),
            make_main_remote=izeros(),
            make_aux_remote=izeros(),
            flood_usage=0.0,
            stable_usage=0.0,
            is_infinite=False,
        )

    def take_total(self) -> Ivec:
        return isum([self.take_local, self.take_remote])

    def make_full_total(self) -> Ivec:
        return isum(
            [
                self.make_main_local,
                self.make_aux_local,
                self.make_main_remote,
                self.make_aux_remote,
            ]
        )

    def make_main_total(self) -> Ivec:
        return isum([self.make_main_local, self.make_main_remote])

    def make_local(self) -> Ivec:
        return isum([self.make_main_local, self.make_aux_local])

    def make_remote(self) -> Ivec:
        return isum([self.make_main_remote, self.make_aux_remote])

    def make_aux_total(self) -> Ivec:
        return isum([self.make_aux_local, self.make_aux_remote])

    def rounded(self, eps: float) -> Allocated:
        return self.__replace__(
            take_local=self.take_local.rounded(eps),
            take_remote=self.take_remote.rounded(eps),
            make_main_local=self.make_main_local.rounded(eps),
            make_aux_local=self.make_aux_local.rounded(eps),
            make_main_remote=self.make_main_remote.rounded(eps),
            make_aux_remote=self.make_aux_remote.rounded(eps),
        )


@dataclass(frozen=True)
class SolverState:
    buildings: list[BuildingCount]
    index: list[tuple[int, int]]
    production: farray
    consumption: farray


def solver_state_from_blocks(
    blocks: list[Block],
) -> tuple[SolverState, list[Allocated]]:
    allocated = [
        Allocated.from_init(block=block, building=building)
        for block in blocks
        for building in block.buildings
    ]
    buildings = [alloc.building for alloc in allocated]
    production, consumption, index = np_allocated(allocated)
    return SolverState(buildings, index, production, consumption), allocated


@profile
def solver_update_state(
    state: SolverState,
) -> tuple[SolverState, SolverState, set[Item]]:
    # TODO actually we should look at warmstarting, most of the time you just change one count or building!

    flooded_state = np_flood_forward(state)
    state = np_prefer_local(flooded_state)
    state, leaf_items = np_back_pressure(state)

    return state, flooded_state, leaf_items


def solve(blocks: list[Block]) -> tuple[list[Allocated], int]:
    prev_state = None
    state, allocated = solver_state_from_blocks(blocks)
    flooded_state = state
    leaf_items: set[Item] = set()

    count = 0
    while (
        prev_state is None
        or np.any(np.abs(prev_state.production - state.production) > ips_eps)
        or np.any(np.abs(prev_state.consumption - state.consumption) > ips_eps)
    ):
        prev_state = state
        state, flooded_state, leaf_items = solver_update_state(state)
        count += 1

    # TODO we need that only in the very end, and/or if we make an accessor interface, we dont have to do that here anymore
    flooded = np_unallocated(
        allocated,
        flooded_state.production,
        flooded_state.consumption,
        flooded_state.index,
    )

    allocated = np_unallocated(
        allocated, state.production, state.consumption, state.index
    )

    allocated = [
        alloc.__replace__(
            flood_usage=alloc.building.usage_for(
                flood.take_remote, flood.make_full_total()
            ),
            stable_usage=alloc.building.usage_for(
                alloc.take_total(), alloc.make_full_total()
            ),
            is_infinite=alloc.building.building.makes <= leaf_items,
        )
        for alloc, flood in zips(allocated, flooded)
    ]

    allocated = rounded_allocations(allocated)

    return allocated, count


def solver_has_converged(
    prev: None | list[Allocated], allocated: list[Allocated]
) -> bool:
    return have_allocations_converged(prev, allocated)


# def pyinstrument_fixpoint(blocks: list[Block]) -> tuple[str, list[list[Allocated]]]:
#     from pyinstrument import Profiler
#
#     with Profiler() as p:
#         result = fixpoint(blocks)
#
#     time.sleep(5)
#     p.open_in_browser()
#
#     return result

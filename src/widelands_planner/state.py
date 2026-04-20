from __future__ import annotations

import math
import re
from collections import defaultdict
from collections.abc import Iterable, Iterator, Mapping, Sequence, Set
from dataclasses import dataclass
from enum import StrEnum
from functools import cache, partial
from pathlib import Path
from typing import final, override

import numpy as np
import torch
from qpsolvers import (
    Solution,
    solve_problem,  # pyright: ignore[reportUnknownVariableType]
)
from qpsolvers.problem import Problem
from torch import Tensor, nn


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

    @classmethod
    def from_zeros(cls, ty: type[I]):
        return Vec(ty, dict())

    @classmethod
    def from_sum(cls, ty: type[I], rates: Sequence[Vec[I]]):
        items = {i for r in rates for i in r.data}
        return cls(ty, {i: sum(r[i] for r in rates) for i in items})

    def sorted(self) -> Iterator[tuple[I, float]]:
        for k, v in sorted(self.data.items()):
            if v != 0:
                yield (k, v)

    def __getitem__(self, i: I) -> float:
        return self.data.get(i, 0)

    def add(self, other: Vec[I]) -> Vec[I]:
        items = self.data.keys() | other.data.keys()
        return Vec(self.ty, {i: (self[i] + other[i]) for i in items})

    def sub(self, other: Vec[I]) -> Vec[I]:
        items = self.data.keys() | other.data.keys()
        return Vec(self.ty, {i: (self[i] - other[i]) for i in items})

    def smul(self, s: float) -> Vec[I]:
        return Vec(self.ty, {i: s * v for (i, v) in self.data.items()})

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


type Ivec = Vec[Item]


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


@dataclass(frozen=True)
class Crafting:
    take: Ivec
    make: Ivec
    seconds: tuple[float, float]  # (short, long)
    # TODO this also doesnt quite model if one entry is a bit lower than needed
    # then we will flip flop between the two modes
    # TODO probably not needed anymore? hopefully no weird one there that we cant optimize by input maximization
    unless: None | set[Item] = None  # skip this crafting when these items are available

    def __post_init__(self):
        assert self.seconds[0] <= self.seconds[1]


@dataclass(frozen=True)
class BaseBuilding:
    name: Bname
    craftings: list[Crafting]
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
                Crafting(
                    take=ifrom(take),
                    make=ifrom(make),
                    seconds=(short, long),
                )
            ],
            0,
        )

    def get_take_items(self) -> set[Item]:
        return {i for c in self.craftings for i in c.take.nonzero_items()}

    def get_make_items(self) -> set[Item]:
        return {i for c in self.craftings for i in c.make.nonzero_items()}

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

        for c in self.craftings:
            if (
                takes >= c.take.nonzero_items()
                and (c.unless is None or not (takes & c.unless))
                and (c.make.is_zero() or makes & c.make.nonzero_items())
            ):
                short, long = c.seconds
                dt += speed * short + (1 - speed) * long
                tk = tk.add(c.take)
                mk = mk.add(c.make)

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

    def get_enabled_craftings(
        self, takes: set[Item], makes: set[Item]
    ) -> list[Crafting]:
        return [
            c
            for c in self.craftings
            if (
                takes >= c.take.nonzero_items()
                # TODO we will probably remove the unless thing soon and use preferred levels
                # and (c.unless is None or not (takes & c.unless))
                # TODO we probably should only define takes anyway
                # and (c.make.is_zero() or makes & c.make.nonzero_items())
            )
        ]

    def take_make_ips_from_craftings(
        self, craftings: Sequence[Crafting], speed: float
    ) -> tuple[Ivec, Ivec]:
        if len(craftings) == 0:
            return izeros(), izeros()
        dt: float = 0.0
        take: Ivec = izeros()
        make: Ivec = izeros()
        for crafting in craftings:
            short, long = crafting.seconds
            dt += speed * short + (1 - speed) * long
            take = take.add(crafting.take)
            make = make.add(crafting.make)
        dt += self.pause
        assert dt > 0
        return take.sdiv(dt), make.sdiv(dt)

    def produces_ips(
        self,
        takes: set[Item],
        makes: set[Item],
        speed: float,
        allocation: Ivec,
    ) -> Ivec:
        _take, make = self.allocate_ips(takes, makes, speed, allocation)
        return make

    def allocate_ips(
        self,
        takes: set[Item],
        makes: set[Item],
        speed: float,
        allocation: Ivec,
        limit: Ivec | None = None,
    ) -> tuple[Ivec, Ivec]:
        # NOTE limit is interpreted as limit only when value set
        # unset values are "inf"
        if limit is None:
            limit = izeros()
        # TODO make preferences, two level, fill first level first, like in the bakery
        # TODO actually we can only control the takes, not the makes, right?
        craftings: list[Crafting] = self.get_enabled_craftings(takes, makes)
        craftings = [
            c
            for c in craftings
            if c.take.nonzero_items() <= allocation.nonzero_items()
            and not (
                c.make.nonzero_items() & {i for i, v in limit.data.items() if v == 0.0}
            )
        ]
        total_take_ips = izeros()
        total_make_ips = izeros()
        used = 0.0
        while used < 1.0 and len(craftings) > 0:
            take_ips, make_ips = self.take_make_ips_from_craftings(craftings, speed)
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
                for item, ips in make_ips.data.items()
                if ips > 0.0 and item in limit.data
            )
            limit_item, limit_ratio = min(
                limit_constraints, key=lambda x: x[1], default=(None, 1.0)
            )
            ratio = min(allocation_ratio, limit_ratio)
            old_used, used = used, min(used + ratio, 1.0)
            ratio = used - old_used
            allocation = allocation.sub(take_ips.smul(ratio))
            if allocation_item is not None:
                allocation.data[allocation_item] = 0.0
            if limit_item is not None:
                limit.data[limit_item] = 0.0
            total_take_ips = total_take_ips.add(take_ips.smul(ratio))
            total_make_ips = total_make_ips.add(make_ips.smul(ratio))
            craftings = [
                c
                for c in craftings
                if c.take.nonzero_items() <= allocation.nonzero_items()
                and not (
                    c.make.nonzero_items()
                    & {i for i, v in limit.data.items() if v == 0.0}
                )
            ]
        return total_take_ips, total_make_ips

    def wants_ips(
        self, takes: set[Item], makes: set[Item], speed: float, item: Item
    ) -> float:
        # TODO should it be based on current allocation?
        craftings: list[Crafting] = self.get_enabled_craftings(takes, makes)
        candidates = (
            self.take_make_ips_from_craftings([c], speed)[0][item] for c in craftings
        )
        return max(candidates, default=0.0)

    def limit_waste(
        self, takes: set[Item], makes: set[Item], speed: float, allocation: Ivec
    ) -> Ivec:
        take, _make = self.allocate_ips(takes, makes, speed, allocation)
        return take

    def back_pressure(
        self,
        takes: set[Item],
        makes: set[Item],
        speed: float,
        allocation: Ivec,
        item: Item,
        ratio: float,
    ) -> Ivec:
        # TODO almost the same as allocate_ips?
        # move up until something hits a ceiling? and then rest, until locked?
        # could we generalize that into allocate? not just allocate is a constraint
        # but also and/or produce? might be easier to just write 2 version of this
        # ah no allocation is always a constraint, but produce only sometimes
        # might fit into one function then? or maybe even use easy infs, seems to work
        # keep all on inf, except the make of item, put to ratio, run again
        # easy first try
        _take, make = self.allocate_ips(takes, makes, speed, allocation)
        # TODO limit is a bit weird, only values that are set are true, others are "inf"
        # TODO eventually we could do the full limit from the start? not just on one item?
        limit = ifrom({item: make[item] * ratio})
        take, _make = self.allocate_ips(takes, makes, speed, allocation, limit)
        return take

    def usage_for(
        self,
        allocation: Ivec,
        takes: set[Item],
        makes: set[Item],
        speed: float,
    ) -> float:
        # TODO approx for now
        wants = self.get_ips(None, None, takes, makes, speed).take
        return min(
            (allocation[i] / w for i, w in wants.data.items() if w > 0.0), default=1.0
        )

    # TODO would be easier to say wants total? not sure how much it depends on state really
    def wants_extra_ips(
        self,
        usage: float,
        item: Item,
        allocation: Ivec,
        takes: set[Item],
        makes: set[Item],
        speed: float,
    ):
        # TODO also very approx
        take = self.get_ips(None, None, takes, makes, speed).take.smul(usage)[item]
        return take - allocation[item]

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
        craftings = [
            c
            for c in self.craftings
            if (
                takes >= c.take.nonzero_items()
                # TODO this is not quite correct, it should be based on whats available, not whats set
                # and then prefer some over others too (two rations instead of single rations)
                # or we do that with a min/max? that could be more exact, and possible
                # and (c.unless is None or not (takes & c.unless))
                and (c.make.is_zero() or makes & c.make.nonzero_items())
            )
        ]

        users = [Variable("user", 0.0, 1.0) for _ in craftings]
        equations = [Equality({usage: 1.0} | {u: -1.0 for u in users}, 0.0)]

        take: dict[Item, dict[Variable, float]] = dict()
        make: dict[Item, dict[Variable, float]] = dict()

        for user, crafting in zip(users, craftings, strict=True):
            short, long = crafting.seconds
            seconds = speed * short + (1 - speed) * long + self.pause
            for i in crafting.take.nonzero_items():
                # TODO every user should only appear once, right?
                take.setdefault(i, dict())[user] = crafting.take[i] / seconds
            for i in crafting.make.nonzero_items():
                # TODO some makes need to be soft and dont require balance? usually when there is more than one output
                # is that output just lost? or still built but doesnt back-pressure?
                # back-pressure only depends on "if economy needs", but im not sure if the rest is still produced and stored?
                # reindeer has a step to make fur, and one to make fur and meat
                # both do when fur is needed, but the optimization doesnt balance it out probably?
                # in this case, make it one step combined so they always happen?
                # so we connect output only to the balance equation in a hard way if it is part of "economy needs"? or at least semantically? because we do it for woodcutters too
                # otherwise, how to connect it so that it is used, but okay if overflow if nothing else?
                make.setdefault(i, dict())[user] = crafting.make[i] / seconds

        mins: dict[Variable, float] = dict()
        for item, vars in take.items():
            m = max(vars.values())
            unused = Variable(f"{item.value}/unused", 0.0, m)
            equations.append(Equality(vars | {unused: 1.0}, m))
            mins[unused] = 1.0

        return take, make, equations, mins

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

    def produces_ips(self, allocation: Ivec) -> Ivec:
        return self.building.produces_ips(
            self.takes, self.makes, self.speed, allocation
        )

    def wants_ips(self, item: Item) -> float:
        return self.building.wants_ips(self.takes, self.makes, self.speed, item)

    def limit_waste(self, allocation: Ivec) -> Ivec:
        return self.building.limit_waste(self.takes, self.makes, self.speed, allocation)

    def back_pressure(self, allocation: Ivec, item: Item, ratio: float) -> Ivec:
        return self.building.back_pressure(
            self.takes, self.makes, self.speed, allocation, item, ratio
        )

    def usage_for(self, allocation: Ivec) -> float:
        return self.building.usage_for(allocation, self.takes, self.makes, self.speed)

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

    def __post_init__(self):
        assert self.count >= 0

    def needs_ips(self, usage: float) -> Ivec:
        return self.building.needs_ips(usage).smul(self.count)

    def produces_ips(self, allocation: Ivec) -> Ivec:
        if self.count == 0:
            return izeros()
        return self.building.produces_ips(allocation.sdiv(self.count)).smul(self.count)

    def wants_ips(self, item: Item) -> float:
        return self.building.wants_ips(item) * self.count

    def limit_waste(self, allocation: Ivec) -> Ivec:
        if self.count == 0:
            return izeros()
        return self.building.limit_waste(allocation.sdiv(self.count)).smul(self.count)

    def back_pressure(self, allocation: Ivec, item: Item, ratio: float) -> Ivec:
        if self.count == 0:
            return izeros()
        return self.building.back_pressure(
            allocation.sdiv(self.count), item, ratio
        ).smul(self.count)

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
                    Crafting(
                        ifrom({Item.barley: 1, Item.water: 1, Item.honey: 1}),
                        ifrom({Item.mead: 1}),
                        (65.667, 65.667),
                    ),
                    Crafting(
                        ifrom({Item.barley: 1, Item.water: 1}),
                        ifrom({Item.beer: 1}),
                        (60.667, 60.667),
                    ),
                    Crafting(
                        ifrom({Item.barley: 1, Item.water: 1, Item.honey: 1}),
                        ifrom({Item.mead: 1}),
                        (65.667, 65.667),
                    ),
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
                    Crafting(
                        ifrom({Item.barley: 1, Item.water: 1, Item.honey: 1}),
                        ifrom({Item.honey_bread: 1}),
                        (45.667, 45.667),
                    ),
                    Crafting(
                        ifrom({Item.barley: 1, Item.water: 1}),
                        ifrom({Item.bread: 1}),
                        (40.667, 40.667),
                    ),
                    Crafting(
                        ifrom({Item.barley: 1, Item.water: 1, Item.honey: 1}),
                        ifrom({Item.honey_bread: 1}),
                        (45.667, 45.667),
                    ),
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
                    Crafting(
                        ifrom({Item.fur_garment: 1, Item.iron: 1}),
                        ifrom({Item.studded_fur_garment: 1}),
                        (49, 49),
                    ),
                    Crafting(
                        ifrom({Item.fur_garment: 1, Item.iron: 1, Item.gold: 1}),
                        ifrom({Item.golden_fur_garment: 1}),
                        (49, 49),
                    ),
                ],
                10,
            )
        case Bname.blacksmithy:
            dt = (70.167, 70.167)
            # TODO hm maybe could be extracted? timings at least
            return BaseBuilding(
                name,
                craftings=[
                    Crafting(ifrom({Item.iron: 1, Item.log: 1}), ifrom({i: 1}), dt)
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
                    Crafting(ifrom({Item.iron: 1}), ifrom({Item.needles: 2}), dt),
                    Crafting(
                        ifrom({Item.reed: 1, Item.log: 1}),
                        ifrom({Item.basket: 1}),
                        dt,
                    ),
                    Crafting(ifrom({Item.iron: 1}), ifrom({Item.fire_tongs: 1}), dt),
                    Crafting(ifrom({Item.reed: 2}), ifrom({Item.fishing_net: 1}), dt),
                ],
                pause=10,
            )
        case Bname.tavern:
            # TODO here we wrote all combinations
            # does it really model the right thing in a total cycle?
            # if consumed uniformly?
            # this part could be coded? but not clear how we model a full cycle
            return BaseBuilding(
                name,
                craftings=[
                    Crafting(
                        ifrom({Item.fruit: 1}),
                        ifrom({Item.ration: 1}),
                        (55, 55),
                        # TODO how does that work with maximization? that we prefer the two-input solution?
                        # not just prefer, the mechanics require it when both are available
                        unless={Item.smoked_fish, Item.smoked_meat},
                    ),
                    Crafting(
                        ifrom({Item.bread: 1}),
                        ifrom({Item.ration: 1}),
                        (55, 55),
                        unless={Item.smoked_fish, Item.smoked_meat},
                    ),
                    Crafting(
                        ifrom({Item.smoked_fish: 1}),
                        ifrom({Item.ration: 1}),
                        (55, 55),
                        unless={Item.fruit, Item.bread},
                    ),
                    Crafting(
                        ifrom({Item.smoked_meat: 1}),
                        ifrom({Item.ration: 1}),
                        (55, 55),
                        unless={Item.fruit, Item.bread},
                    ),
                    Crafting(
                        ifrom({Item.fruit: 1, Item.smoked_fish: 1}),
                        ifrom({Item.ration: 2}),
                        (74, 74),
                    ),
                    Crafting(
                        ifrom({Item.fruit: 1, Item.smoked_meat: 1}),
                        ifrom({Item.ration: 2}),
                        (74, 74),
                    ),
                    Crafting(
                        ifrom({Item.bread: 1, Item.smoked_fish: 1}),
                        ifrom({Item.ration: 2}),
                        (74, 74),
                    ),
                    Crafting(
                        ifrom({Item.bread: 1, Item.smoked_meat: 1}),
                        ifrom({Item.ration: 2}),
                        (74, 74),
                    ),
                ],
                pause=0,
            )
        case Bname.smokery:
            return BaseBuilding(
                name,
                [
                    Crafting(
                        ifrom({Item.log: 1, Item.fish: 2}),
                        ifrom({Item.smoked_fish: 2}),
                        (54, 54),
                    ),
                    Crafting(
                        ifrom({Item.log: 1, Item.meat: 2}),
                        ifrom({Item.smoked_meat: 2}),
                        (54, 54),
                    ),
                ],
                0,
            )
        case Bname.furnace:
            return BaseBuilding(
                name,
                [
                    Crafting(
                        ifrom({Item.coal: 1, Item.iron_ore: 1}),
                        ifrom({Item.iron: 1}),
                        (64, 64),
                    ),
                    Crafting(
                        ifrom({Item.coal: 1, Item.gold_ore: 1}),
                        ifrom({Item.gold: 1}),
                        (66, 66),
                    ),
                    Crafting(
                        ifrom({Item.coal: 1, Item.iron_ore: 1}),
                        ifrom({Item.iron: 1}),
                        (64, 64),
                    ),
                ],
                0,
            )
        case Bname.armor_smithy_small:
            return BaseBuilding(
                name,
                [
                    Crafting(
                        ifrom({Item.coal: 1, Item.iron: 1}),
                        ifrom({Item.short_sword: 1}),
                        (58, 58),
                    ),
                    Crafting(
                        ifrom({Item.coal: 1, Item.iron: 2}),
                        ifrom({Item.long_sword: 1}),
                        (58, 58),
                    ),
                    Crafting(
                        ifrom({Item.coal: 1, Item.iron: 1}),
                        ifrom({Item.helmet: 1}),
                        (68, 68),
                    ),
                ],
                10,
            )
        case Bname.armor_smithy_large:
            return BaseBuilding(
                name,
                [
                    Crafting(
                        ifrom({Item.coal: 1, Item.iron: 2, Item.gold: 1}),
                        ifrom({Item.broadsword: 1}),
                        (58.8, 58.8),
                    ),
                    Crafting(
                        ifrom({Item.coal: 2, Item.iron: 2, Item.gold: 1}),
                        ifrom({Item.double_edged_sword: 1}),
                        (58.8, 58.8),
                    ),
                    Crafting(
                        ifrom({Item.coal: 2, Item.iron: 2, Item.gold: 1}),
                        ifrom({Item.golden_helmet: 1}),
                        (68.8, 68.8),
                    ),
                    Crafting(
                        ifrom({Item.coal: 1, Item.iron: 2, Item.gold: 1}),
                        ifrom({Item.broadsword: 1}),
                        (58.8, 58.8),
                    ),
                    Crafting(
                        ifrom({Item.coal: 2, Item.iron: 2, Item.gold: 1}),
                        ifrom({Item.double_edged_sword: 1}),
                        (58.8, 58.8),
                    ),
                ],
                10,
            )
        case Bname.reindeer_farm:
            # TODO it actually makes meat, even when only fur is needed
            # maybe after all this part needs to just be code?
            return BaseBuilding(
                name,
                [
                    Crafting(
                        ifrom({Item.water: 1, Item.barley: 1}),
                        ifrom({Item.deer: 1}),
                        (30, 30),
                    ),
                    Crafting(
                        ifrom({Item.water: 1, Item.barley: 1}),
                        ifrom({Item.fur: 1}),
                        (38.6, 38.6),
                    ),
                    Crafting(
                        ifrom({Item.water: 1, Item.barley: 1}),
                        ifrom({Item.deer: 1}),
                        (30, 30),
                    ),
                    Crafting(
                        ifrom({Item.water: 1, Item.barley: 1}),
                        ifrom({Item.fur: 1}),
                        (38.6, 38.6),
                    ),
                    Crafting(
                        ifrom({Item.water: 1, Item.barley: 1}),
                        ifrom({Item.deer: 1}),
                        (30, 30),
                    ),
                    Crafting(
                        ifrom({Item.water: 1, Item.barley: 1}),
                        # TODO this one makes when fur is needed, meat is extra and could be over
                        ifrom({Item.fur: 1, Item.meat: 1}),
                        (42.2, 42.2),
                    ),
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
                [  # attack 1
                    Crafting(
                        # TODO hmm ok just one of many foods ... dont have a good way to model it
                        # and which one would be taken, random uniform, always first?
                        ifrom({Item.long_sword: 1, food: 1}),
                        ifrom({Item.scrap_iron: 1}),
                        (36 + 6, 36 + 6),  # NOTE not sure about the +6
                    )
                    for food in {Item.bread, Item.smoked_fish, Item.smoked_meat}
                ]
                + [  # attack 2
                    Crafting(
                        ifrom({Item.broadsword: 1, Item.bread: 1, meat: 1}),
                        ifrom({Item.scrap_iron: 2}),
                        (36 + 6, 36 + 6),  # NOTE not sure about the +6
                    )
                    for meat in {Item.smoked_fish, Item.smoked_meat}
                ]
                + [  # attack 3
                    Crafting(
                        ifrom({Item.double_edged_sword: 1, Item.beer: 1, meat: 1}),
                        ifrom({Item.scrap_iron: 1, Item.mixed_scrap_metal: 1}),
                        (36 + 6, 36 + 6),  # NOTE not sure about the +6
                    )
                    for meat in {Item.smoked_fish, Item.smoked_meat}
                ]
                + [  # health 1
                    Crafting(
                        ifrom({Item.helmet: 1, food1: 1, food2: 1}),
                        ifrom({}),
                        (36 + 6, 36 + 6),  # NOTE not sure about the +6
                    )
                    for food1 in {Item.bread, Item.beer}
                    for food2 in {Item.smoked_fish, Item.smoked_meat}
                ]
                + [  # defense 1
                    Crafting(
                        ifrom({Item.studded_fur_garment: 1, food1: 1, food2: 1}),
                        # TODO how does this go with maximization? we might not care for old_* and scrap metal, but we dont want to limit it
                        ifrom({Item.old_fur_garment: 1}),
                        (36 + 6, 36 + 6),  # NOTE not sure about the +6
                    )
                    for food1 in {Item.bread, Item.beer}
                    for food2 in {Item.smoked_fish, Item.smoked_meat}
                ],
                0,
            )
        case Bname.training_arena:
            # TODO same as for training camp
            return BaseBuilding(
                name,
                [  # attack 4
                    Crafting(
                        ifrom({Item.long_sword: 1, food1: 1, food2: 1}),
                        ifrom({}),
                        (28.8 + 6, 28.8 + 6),  # NOTE not sure about the +6
                    )
                    for food1 in {Item.honey_bread, Item.mead}
                    for food2 in {Item.smoked_fish, Item.smoked_meat}
                ]
                + [  # attack 5
                    Crafting(
                        # TODO not clear of food2 is two of the same, or any two ...
                        ifrom({Item.broadsword: 1, food1: 1, food2: 2}),
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
                        ifrom({Item.scrap_iron: 1, Item.mixed_scrap_metal: 1}),
                        (28.8 + 6, 28.8 + 6),  # NOTE not sure about the +6
                    )
                    for food in {Item.smoked_fish, Item.smoked_meat}
                ]
                + [  # defense 2
                    Crafting(
                        ifrom({Item.golden_fur_garment: 1, food1: 1, food2: 1}),
                        ifrom({Item.scrap_iron: 1, Item.old_fur_garment: 1}),
                        (36 + 6, 36 + 6),  # NOTE not sure about the +6
                    )
                    for food1 in {Item.honey_bread, Item.mead}
                    for food2 in {Item.smoked_fish, Item.smoked_meat}
                ]
                + [  # health 2
                    Crafting(
                        ifrom({Item.golden_helmet: 1, food1: 1, food2: 1}),
                        ifrom({Item.scrap_iron: 1}),
                        (32.4 + 6, 32.4 + 6),  # NOTE not sure about the +6
                    )
                    for food1 in {Item.honey_bread, Item.mead}
                    for food2 in {Item.smoked_fish, Item.smoked_meat}
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
    # TODO how to check that this is consistent? no overlaps?
    imports: set[Item]
    buildings: list[BuildingCount]
    exports: set[Item]


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
        if i in block.imports:
            if b > 0:
                imports[i] = 0
            else:
                imports[i] = -b
        elif i in block.exports:
            if b > 0:
                exports[i] = b
            else:
                local[i] = b
        else:
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


# def get_balance(blocks: list[Block]) -> None:
#     # NOTE probably assuming no cycles in the production graph (frisians might have one eventually)
#
#     takes: dict[int | None, Ivec] = defaultdict(Ivec.from_zeros)
#     makes: dict[int | None, Ivec] = defaultdict(Ivec.from_zeros)
#     # TODO initialize with last solution
#     takes, makes = None, None
#
#     while todo(takes, makes):
#         last_takes, last_makes = takes, makes
#
#         takes: dict[int | None, Ivec] = defaultdict(Ivec.from_zeros)
#         makes: dict[int | None, Ivec] = defaultdict(Ivec.from_zeros)
#
#         for block in blocks:
#             for count in block.buildings:
#                 # TODO an Ivec on (block|None, Item) would be easier now? flat and full?
#                 # TODO also, a block is not really isolated, so we cant just half-ass produce there :/ it wont happen
#                 # this only goes for global stuff, arrrg
#                 # what if we compute everything global, but warn about non-local leaking, except for the ones we import/export?
#                 lt = last_takes[id(block)].add(last_takes[None].include(block.imports))
#                 mt = last_makes[id(block)].add(last_makes[None].include(block.exports))
#
#                 t = count.takes_ips(lt, lm)
#                 takes[None].add(t.include(block.imports))
#                 takes[id(block)].add(t.exclude(block.imports))
#
#                 m = count.makes_ips(lt, lm)
#                 makes[None].add(m.include(block.exports))
#                 makes[id(block)].add(m.exclude(block.exports))


@final
class Model(nn.Module):
    def __init__(self, counts: list[BuildingCount]):
        super().__init__()
        self.counts = counts
        self.usage_logits = nn.ParameterList(torch.tensor(0.0) for _ in counts)

    @override
    def forward(self):
        takes: dict[Item, list[Tensor]] = defaultdict(list)
        makes: dict[Item, list[Tensor]] = defaultdict(list)

        for count, usage_logit in zip(self.counts, self.usage_logits, strict=True):
            u = torch.sigmoid(usage_logit)
            ts = {i: u * v for (i, v) in count.takes_ips().data.items()}
            ms = {i: u * v for (i, v) in count.makes_ips().data.items()}
            for i, v in ts.items():
                takes[i].append(v)
            for i, v in ms.items():
                makes[i].append(v)

        take: dict[Item, Tensor] = {
            i: torch.sum(torch.stack(vs)) for i, vs in takes.items() if len(vs) > 0
        }
        make: dict[Item, Tensor] = {
            i: torch.sum(torch.stack(vs)) for i, vs in makes.items() if len(vs) > 0
        }

        balances = [
            (take.get(i, torch.tensor(0.0)) - make.get(i, torch.tensor(0.0))).pow(2.0)
            for i in Item
            if i in take
        ]
        loss_balances = torch.mean(torch.stack(balances))

        # TODO could be nicer to make it a loss that can be zero, so subtract from the max? also more balanced with other loss
        dangles = [
            -make.get(i, torch.tensor(0.0)).pow(2.0) for i in Item if i not in take
        ]
        loss_dangles = torch.mean(torch.stack(dangles))

        loss_usage = torch.mean(
            torch.stack(
                [
                    torch.tensor(1.0) - torch.sigmoid(usage_logit)
                    for usage_logit in self.usage_logits
                ]
            )
        )

        return loss_balances + loss_dangles, loss_balances, loss_usage, loss_dangles


def opt(
    blocks: list[Block],
) -> Iterator[tuple[tuple[float, ...], list[tuple[BuildingCount, float]]]]:
    counts = [count for block in blocks for count in block.buildings]
    if len(counts) == 0:
        return
    model = Model(counts)

    # TODO wait, how does a >1 lr make sense again?
    optim = torch.optim.SGD(params=model.parameters(), lr=1000, maximize=False)
    # optim = torch.optim.Adam(params=model.parameters(), maximize=False)
    model.train()

    for i in range(10000):
        optim.zero_grad()
        [loss, *more] = model()
        loss.backward()
        optim.step()  # pyright: ignore[reportUnknownMemberType]

        if i % 1000 == 0:
            with torch.no_grad():
                yield (
                    (loss.item(), *(i.item() for i in more)),
                    [
                        (count, torch.sigmoid(logit).item())
                        for (count, logit) in zip(
                            counts, model.usage_logits, strict=True
                        )
                    ],
                )


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


def build_qp(
    min: dict[Variable, float], equations: Sequence[Equality]
) -> tuple[list[Variable], Problem]:
    vars = set(min) | {var for equation in equations for var in equation.variables()}
    vars = list(vars)
    N = len(vars)
    K = len(equations)

    lb = np.array(
        [-math.inf if var.lb is None else var.lb for var in vars], dtype=np.float32
    )
    ub = np.array(
        [-math.inf if var.ub is None else var.ub for var in vars], dtype=np.float32
    )

    P = np.zeros([N, N], dtype=np.float32)
    for var, w in min.items():
        i = vars.index(var)
        P[i, i] = w

    A = np.zeros([K, N], dtype=np.float32)
    b = np.zeros([K], dtype=np.float32)
    for i, eq in enumerate(equations):
        for var, weight in eq.vars.items():
            A[i, vars.index(var)] = weight
        b[i] = eq.const

    problem = Problem(
        P=P,
        q=np.zeros([N], dtype=np.float32),
        A=A,
        b=b,
        lb=lb,
        ub=ub,
    )

    return vars, problem


def qp(blocks: list[Block]) -> tuple[list[str], Solution] | None:
    counts = [count for block in blocks for count in block.buildings]
    if len(counts) == 0:
        return None

    balances: dict[Item, Equality] = {i: Equality(dict(), 0.0) for i in Item}
    idles: list[Variable] = []
    equations: list[Equality] = []
    mins: dict[Variable, float] = dict()

    for count in counts:
        take, make, eqs, idle, ms = count.get_constraints()
        for item, weights in take.items():
            for var, weight in weights.items():
                # TODO there should never be the variable existing already
                balances[item].vars[var] = balances[item].vars.get(var, 0.0) - weight
        for item, weights in make.items():
            for var, weight in weights.items():
                balances[item].vars[var] = balances[item].vars.get(var, 0.0) + weight
        equations.extend(eqs)
        idles.append(idle)
        mins.update(ms)

    def has_consumption(equation: Equality) -> bool:
        return any(v < 0.0 for v in equation.vars.values())

    balances = {
        item: equation
        for (item, equation) in balances.items()
        # TODO its nice and clean, but we might not want that after all?
        # adding a building could bring everything to zero, maybe have options
        # anyway options for exploring the solution space and seeing how much is needed?
        if has_consumption(equation)
    }

    vars, problem = build_qp(mins, list(balances.values()) + equations)
    # TODO clarabel likes scipy.sparse.csc_matrix for speed, and no warnings
    # TODO also, if it fails with numerical error, how do we see that?
    solution = solve_problem(problem, solver="clarabel")

    return [var.desc for var in vars], solution


def get_production(counts: list[BuildingCount], allocations: list[Ivec]) -> Ivec:
    production: Ivec = izeros()
    for count, allocation in zip(counts, allocations, strict=True):
        production = production.add(count.produces_ips(allocation))
    return production


def get_consumption(counts: list[BuildingCount], usages: list[float]) -> Ivec:
    consumption = izeros()
    for count, usage in zip(counts, usages, strict=True):
        consumption = consumption.add(count.takes_ips().smul(usage))
    return consumption


def boost(counts: list[BuildingCount], allocations: list[Ivec]) -> list[Ivec]:
    for _ in range(20):
        previous_allocations = allocations
        consumption = isum(allocations)
        production = isum(
            count.produces_ips(allocation)
            for count, allocation in zip(counts, allocations, strict=True)
        )
        for item in Item:
            surplus = production[item] - consumption[item]
            if surplus <= 0.0:
                continue
            demands = [
                count.wants_ips(item) - allocation[item]
                for count, allocation in zip(counts, allocations, strict=True)
            ]
            demand = sum(demands)
            if demand <= 0.0:
                continue
            can = min(surplus / demand, 1.0)
            allocations = [
                allocation.add(ifrom({item: demand * can}))
                for allocation, demand in zip(allocations, demands, strict=True)
            ]
        convergence = all(
            a.almost_equal(b, 0.01 / 60)
            for a, b in zip(previous_allocations, allocations, strict=True)
        )
        if convergence:
            return allocations
    print("boosting didnt converge")
    return allocations


def back_pressure(counts: list[BuildingCount], allocations: list[Ivec]) -> list[Ivec]:
    for _ in range(20):
        previous_allocations = allocations
        # TODO this might have to happen only once? not sure with nonlinear craftings
        # should we combine this into backpressure?
        allocations = [
            count.limit_waste(allocation)
            for count, allocation in zip(counts, allocations, strict=True)
        ]
        consumption = isum(allocations)
        production = isum(
            count.produces_ips(allocation)
            for count, allocation in zip(counts, allocations, strict=True)
        )
        for item in Item:
            # TODO here, how to manage roots where we dont want to limit? like with opt
            # if item is Item.log or item not in consumption.data:
            if item not in consumption.data:
                continue
            surplus = production[item] - consumption[item]
            if surplus <= 0.0:
                continue
            ratio = consumption[item] / production[item]
            allocations = [
                count.back_pressure(allocation, item, ratio)
                for count, allocation in zip(counts, allocations, strict=True)
            ]
        convergence = all(
            a.almost_equal(b, 0.01 / 60)
            for a, b in zip(previous_allocations, allocations, strict=True)
        )
        if convergence:
            return allocations
    print("pressure didnt converge")
    return allocations


def fixpoint(
    blocks: list[Block],
) -> Iterator[tuple[bool | str, list[tuple[BuildingCount, Ivec]]]]:
    counts = [count for block in blocks for count in block.buildings]
    if len(counts) == 0:
        yield True, []
        return

    # TODO need to introduce blocks, and fulfil locally first
    # backpressure similar? its a bit messy. and allocations need to be local vs global too
    # btw, whats a good way to identify a block vs describing it?
    # pass the desc and have a .id? just for fun its interesting, when to use handle, when to use thing
    allocations = [izeros() for _ in counts]

    for _ in range(20):
        # TODO convert allocations into a kind of usage?
        yield False, list(zip(counts, allocations, strict=True))
        previous_allocations = allocations
        allocations = boost(counts, allocations)
        allocations = back_pressure(counts, allocations)
        convergence = all(
            a.almost_equal(b, 0.01 / 60)
            for a, b in zip(previous_allocations, allocations, strict=True)
        )
        if convergence:
            # TODO ah but we dont see the productions, so thats why we dont see water, doesnt mean its broken at that point
            # maybe still bakery is the problem?
            yield str(_), list(zip(counts, allocations, strict=True))
            return

    yield False, list(zip(counts, allocations, strict=True))

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Literal


class Item(Enum):
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


@dataclass(frozen=True)
class Ivec:
    # TODO can we protect this dict from changes to be safe?
    data: dict[Item, float]

    @classmethod
    def from_zeros(cls):
        return cls(dict())

    @classmethod
    def from_sum(cls, rates: list[Ivec]):
        items = {i for r in rates for i in r.data}
        return cls({i: sum(r[i] for r in rates) for i in items})

    # TODO doesnt make so much sense, have smul(60).round().as_json() done by user?
    def as_ipm(self) -> dict[str, float]:
        """in items per minute, rounded, 0s removed"""
        return {str(i): round(v * 60, 1) for (i, v) in self.data.items() if v != 0}

    def as_percentages(self) -> dict[str, float]:
        def f(v: float) -> float:
            if math.isfinite(v):
                return round(v * 100)
            return v

        return {str(i): f(v) for (i, v) in self.data.items() if v != 0}

    def __getitem__(self, i: Item) -> float:
        return self.data.get(i, 0)

    def add(self, other: Ivec) -> Ivec:
        items = self.data.keys() | other.data.keys()
        return Ivec({i: (self[i] + other[i]) for i in items})

    def sub(self, other: Ivec) -> Ivec:
        items = self.data.keys() | other.data.keys()
        return Ivec({i: (self[i] - other[i]) for i in items})

    def smul(self, s: float) -> Ivec:
        return Ivec({i: s * v for (i, v) in self.data.items()})

    def div(self, other: Ivec) -> Ivec:
        def div(a: float, b: float) -> float:
            if b == 0:
                return math.inf
            return a / b

        return Ivec({i: div(v, other[i]) for (i, v) in self.data.items() if v != 0})

    def negate(self) -> Ivec:
        return Ivec({i: -v for (i, v) in self.data.items()})

    def keep_positives(self) -> Ivec:
        return Ivec({i: v for (i, v) in self.data.items() if v > 0})


@dataclass(frozen=True)
class PlainBuilding:
    name: str
    takes: Ivec
    rate: float  # "takes" into "makes" per second
    makes: Ivec

    @classmethod
    def from_seconds(cls, name: str, short: float, long: float, count: int, item: Item):
        # TODO do we want to adjust this? arent we often in the more optimal case?
        return cls(
            name, Ivec.from_zeros(), 1 / ((short + long) / 2), Ivec({item: count})
        )

    def __post_init__(self):
        assert self.name
        assert self.rate >= 0

    def takes_ips(self) -> Ivec:
        return self.takes.smul(self.rate)

    def makes_ips(self) -> Ivec:
        return self.makes.smul(self.rate)

    def can_fulfill(self, shortages: Ivec) -> None | str:
        items = {i for i, v in self.makes.data.items() if v > 0}
        s = {i: shortages[i] for i in items if shortages[i] > 0}
        if not s:
            return None
        m = self.makes_ips()
        adds = {i: (ips / m[i]) for i, ips in s.items()}
        add = max(adds.values())
        who = ", ".join(i.value for i in adds.keys())
        return f"add {add:.1f} for {who}"


# TODO only models two-input ration production, not the slower one-input possibility
@dataclass(frozen=True)
class TavernBuilding:
    name: Literal["taverns"] = "taverns"
    rate: float = 1 / 37
    item: Item = Item.ration

    def __post_init__(self):
        assert self.name

    def takes_ips(self, fruit_vs_bread: float, fish_vs_meat: float) -> Ivec:
        r = self.rate / 2  # we make two rations from two inputs (one of each type)
        return Ivec(
            {
                Item.fruit: r * fruit_vs_bread,
                Item.bread: r * (1 - fruit_vs_bread),
                Item.smoked_fish: r * fish_vs_meat,
                Item.smoked_meat: r * (1 - fish_vs_meat),
            }
        )

    def makes_ips(self) -> Ivec:
        return Ivec({self.item: self.rate})

    def can_fulfill(self, shortages: Ivec) -> None | str:
        s = shortages[self.item]
        if s == 0:
            return None
        return f"add {s / self.rate:.1f} for {self.item}"


@dataclass(frozen=True)
class ConfiguredTavernBuilding:
    building: TavernBuilding
    fruit_vs_bread: float
    fish_vs_meat: float
    name: Literal["taverns"] = "taverns"

    def __post_init__(self):
        assert self.name
        assert 0 <= self.fruit_vs_bread <= 1
        assert 0 <= self.fish_vs_meat <= 1

    def takes_ips(self) -> Ivec:
        return self.building.takes_ips(self.fruit_vs_bread, self.fish_vs_meat)

    def makes_ips(self) -> Ivec:
        return self.building.makes_ips()

    def can_fulfill(self, shortages: Ivec) -> None | str:
        return self.building.can_fulfill(shortages)


@dataclass(frozen=True)
class SmokeryBuilding:
    name: Literal["smokeries"] = "smokeries"
    rate: float = 1 / 27

    def __post_init__(self):
        assert self.name

    def takes_ips(self, fish_vs_meat: float) -> Ivec:
        return Ivec(
            {
                Item.log: 0.5 * self.rate,
                Item.fish: self.rate * fish_vs_meat,
                Item.meat: self.rate * (1 - fish_vs_meat),
            }
        )

    def makes_ips(self, fish_vs_meat: float) -> Ivec:
        return Ivec(
            {
                Item.smoked_fish: self.rate * fish_vs_meat,
                Item.smoked_meat: self.rate * (1 - fish_vs_meat),
            }
        )

    def can_fulfill(self, fish_vs_meat: float, shortages: Ivec) -> None | str:
        s_fish = fish_vs_meat * shortages[Item.smoked_fish]
        s_meat = (1 - fish_vs_meat) * shortages[Item.smoked_meat]
        s = s_fish + s_meat
        if s == 0:
            return None
        who: list[str] = []
        if s_fish > 0:
            who.append(Item.smoked_fish.value)
        if s_meat > 0:
            who.append(Item.smoked_meat.value)
        who_str = " and ".join(who)
        return f"add {s / self.rate:.1f} for {who_str}"


@dataclass(frozen=True)
class ConfiguredSmokeryBuilding:
    building: SmokeryBuilding
    fish_vs_meat: float
    name: Literal["smokeries"] = "smokeries"

    def __post_init__(self):
        assert 0 <= self.fish_vs_meat <= 1
        assert self.name

    def takes_ips(self) -> Ivec:
        return self.building.takes_ips(self.fish_vs_meat)

    def makes_ips(self) -> Ivec:
        return self.building.makes_ips(self.fish_vs_meat)

    def can_fulfill(self, shortages: Ivec) -> None | str:
        return self.building.can_fulfill(self.fish_vs_meat, shortages)


type Building = PlainBuilding | TavernBuilding | SmokeryBuilding
type ConfiguredBuilding = (
    PlainBuilding | ConfiguredTavernBuilding | ConfiguredSmokeryBuilding
)


@dataclass(frozen=True)
class BuildingCount:
    count: int
    building: ConfiguredBuilding

    def __post_init__(self):
        assert self.count >= 0

    def get_name(self) -> str:
        return self.building.name

    def takes_ips(self) -> Ivec:
        return self.building.takes_ips().smul(self.count)

    def makes_ips(self) -> Ivec:
        return self.building.makes_ips().smul(self.count)

    def can_fulfill(self, shortages: Ivec) -> None | str:
        return self.building.can_fulfill(shortages)


def rate_from_seconds(seconds: float | tuple[float, float]) -> float:
    match seconds:
        case [a, b]:
            return 1 / ((a + b) / 2)
        case t:
            return 1 / t


def get_buildings() -> list[Building]:
    return [
        TavernBuilding(),
        SmokeryBuilding(),
        PlainBuilding.from_seconds("fisher's houses", 26, 59, 1, Item.fish),
        PlainBuilding.from_seconds("forester's houses", 24, 46, 1, Item.tree),
        PlainBuilding(
            "woodcutter's houses",
            Ivec({Item.tree: 1}),
            rate_from_seconds((49, 89)),
            Ivec({Item.log: 1}),
        ),
        PlainBuilding.from_seconds("wells", 44, 44, 1, Item.water),
        PlainBuilding.from_seconds("farms", 49, 67, 1, Item.barley),
        PlainBuilding.from_seconds("reed farms", 52, 67, 1, Item.reed),
        PlainBuilding(
            "coal mines",
            Ivec({Item.ration: 1}),
            rate_from_seconds(2 * 41),
            Ivec({Item.coal: 2}),
        ),
        PlainBuilding(
            "rock mines",
            Ivec({Item.ration: 1}),
            rate_from_seconds(2 * 46),
            Ivec({Item.granite: 2}),
        ),
        PlainBuilding(
            "clay pits",
            Ivec({Item.water: 1}),
            rate_from_seconds((55, 73)),
            Ivec({Item.clay: 1}),
        ),
        PlainBuilding(
            "brick kilns",
            Ivec({Item.coal: 1, Item.clay: 3, Item.granite: 1}),
            rate_from_seconds(3 * 30),
            Ivec({Item.brick: 3}),
        ),
        PlainBuilding(
            "fruit collector's houses",
            Ivec({Item.berry_bush: 1}),
            rate_from_seconds((37, 62)),
            Ivec({Item.fruit: 1}),
        ),
        PlainBuilding.from_seconds("berry farms", 33, 51, 1, Item.berry_bush),
        PlainBuilding(
            "breweries",
            Ivec({Item.water: 1, Item.barley: 1}),
            rate_from_seconds(64),
            Ivec({Item.beer: 1}),
        ),
    ]


def get_takes_ips(buildings: list[BuildingCount]) -> Ivec:
    return Ivec.from_sum([b.takes_ips() for b in buildings])


def get_makes_ips(buildings: list[BuildingCount]) -> Ivec:
    return Ivec.from_sum([b.makes_ips() for b in buildings])


def get_balance_ips(buildings: list[BuildingCount]) -> Ivec:
    return get_makes_ips(buildings).sub(get_takes_ips(buildings))


def get_shortages_ips(buildings: list[BuildingCount]) -> Ivec:
    return get_balance_ips(buildings).negate().keep_positives()


def get_usage_ratios(buildings: list[BuildingCount]) -> Ivec:
    # TODO work with float | something instead of infs?
    return get_takes_ips(buildings).div(get_makes_ips(buildings))

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Literal


class Item(Enum):
    fruit = "fruit"
    bread = "bread"
    smoked_meat = "smoked meat"
    smoked_fish = "smoked fish"
    ration = "ration"
    log = "log"
    fish = "fish"
    meat = "meat"
    tree = "tree"  # what the forester plants, not logs yet


@dataclass(frozen=True)
class Ivec:
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
    rate: float
    item: Item

    @classmethod
    def from_seconds(cls, name: str, short: float, long: float, count: int, item: Item):
        # TODO do we want to adjust this? arent we often in the more optimal case?
        return cls(name, count / ((short + long) / 2), item)

    def __post_init__(self):
        assert self.name
        assert self.rate >= 0

    def takes_ips(self) -> Ivec:
        return Ivec.from_zeros()

    def makes_ips(self) -> Ivec:
        return Ivec({self.item: self.rate})

    def can_fulfill(self, shortages: Ivec) -> None | str:
        s = shortages[self.item]
        if s == 0:
            return None
        return f"add {s / self.rate:.1f} for {self.item.value}"


# TODO only models two-input ration production, not the slower one-input possibility
@dataclass(frozen=True)
class TavernBuilding:
    name: Literal["taverns"] = "taverns"

    def __post_init__(self):
        assert self.name

    def takes_ips(self, fruit_vs_bread: float, fish_vs_meat: float) -> Ivec:
        r = 1 / (2 * 37)  # two rations from two inputs (one of each)
        return Ivec(
            {
                Item.fruit: r * fruit_vs_bread,
                Item.bread: r * (1 - fruit_vs_bread),
                Item.smoked_fish: r * fish_vs_meat,
                Item.smoked_meat: r * (1 - fish_vs_meat),
            }
        )

    def makes_ips(self) -> Ivec:
        r = 1 / (2 * 37)  # two rations from two inputs (one of each)
        return Ivec({Item.bread: 2 * r})

    def can_fulfill(self, shortages: Ivec) -> None | str:
        # TODO todo
        return None


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

    def __post_init__(self):
        assert self.name

    def takes_ips(self, fish_vs_meat: float) -> Ivec:
        r = 1 / 27  # one smoked thing from one raw thing and half a log
        return Ivec(
            {
                Item.log: 0.5 * r,
                Item.fish: r * fish_vs_meat,
                Item.meat: r * (1 - fish_vs_meat),
            }
        )

    def makes_ips(self, fish_vs_meat: float) -> Ivec:
        r = 1 / 27  # one smoked thing from one raw thing and half a log
        return Ivec(
            {
                Item.smoked_fish: r * fish_vs_meat,
                Item.smoked_meat: r * (1 - fish_vs_meat),
            }
        )

    def can_fulfill(self, shortages: Ivec) -> None | str:
        s = shortages[Item.smoked_fish] + shortages[Item.smoked_meat]
        if s == 0:
            return None
        r = 1 / 27  # one smoked thing from one raw thing and half a log
        # TODO use fish_vs_meat ?
        return f"add {s / r:.1f} for smoked fish and/or smoked_meat"


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
        return self.building.can_fulfill(shortages)


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

    def takes_ips(self) -> Ivec:
        return self.building.takes_ips().smul(self.count)

    def makes_ips(self) -> Ivec:
        return self.building.makes_ips().smul(self.count)

    def can_fulfill(self, shortages: Ivec) -> None | str:
        return self.building.can_fulfill(shortages)


def get_buildings() -> list[Building]:
    return [
        TavernBuilding(),
        SmokeryBuilding(),
        PlainBuilding.from_seconds("fisher's houses", 26, 59, 1, Item.fish),
        PlainBuilding.from_seconds("forester's houses", 24, 46, 1, Item.tree),
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

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum


class Item(Enum):
    fruit = "fruit"
    bread = "bread"
    smoked_meat = "smoked meat"
    smoked_fish = "smoked fish"
    ration = "ration"
    log = "log"
    fish = "fish"
    meat = "meat"


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
class TavernCount:
    count: int
    # TODO only models two-input ration production, not the slower one-input possibility
    fruit_vs_bread: float
    fish_vs_meat: float

    def __post_init__(self):
        assert 0 <= self.count
        assert 0 <= self.fruit_vs_bread <= 1
        assert 0 <= self.fish_vs_meat <= 1

    def takes_ips(self) -> Ivec:
        r = 1 / (2 * 37)  # two rations from two inputs (one of each)
        return Ivec(
            {
                Item.fruit: r * self.count * self.fruit_vs_bread,
                Item.bread: r * self.count * (1 - self.fruit_vs_bread),
                Item.smoked_fish: r * self.count * self.fish_vs_meat,
                Item.smoked_meat: r * self.count * (1 - self.fish_vs_meat),
            }
        )

    def makes_ips(self) -> Ivec:
        r = 1 / (2 * 37)  # two rations from two inputs (one of each)
        return Ivec({Item.bread: 2 * r * self.count})

    def can_fulfill(self, shortages: Ivec) -> None | str:
        return None


@dataclass(frozen=True)
class SmokeryCount:
    count: int
    fish_vs_meat: float

    def __post_init__(self):
        assert 0 <= self.count
        assert 0 <= self.fish_vs_meat <= 1

    def takes_ips(self) -> Ivec:
        r = 1 / 27  # one smoked thing from one raw thing and half a log
        return Ivec(
            {
                Item.log: 0.5 * r * self.count,
                Item.fish: r * self.count * self.fish_vs_meat,
                Item.meat: r * self.count * (1 - self.fish_vs_meat),
            }
        )

    def makes_ips(self) -> Ivec:
        r = 1 / 27  # one smoked thing from one raw thing and half a log
        return Ivec(
            {
                Item.smoked_fish: r * self.count * self.fish_vs_meat,
                Item.smoked_meat: r * self.count * (1 - self.fish_vs_meat),
            }
        )

    def can_fulfill(self, shortages: Ivec) -> None | str:
        s = shortages[Item.smoked_fish] + shortages[Item.smoked_meat]
        if s == 0:
            return None
        r = 1 / 27  # one smoked thing from one raw thing and half a log
        # TODO use self.fish_vs_meat ?
        return f"add {s / r:.1f} for smoked fish and/or smoked_meat"


@dataclass(frozen=True)
class FishersHouseCount:
    count: int

    def __post_init__(self):
        assert 0 <= self.count

    def takes_ips(self) -> Ivec:
        return Ivec.from_zeros()

    def makes_ips(self) -> Ivec:
        # TODO do we want to adjust this? arent we often in the more optimal case?
        t = (26 + 59) / 2
        r = 1 / t
        return Ivec({Item.fish: r * self.count})

    def can_fulfill(self, shortages: Ivec) -> None | str:
        s = shortages[Item.fish]
        if s == 0:
            return None
        t = (26 + 59) / 2
        r = 1 / t
        return f"add {s / r:.1f} for fish"


class Building(Enum):
    taverns = "taverns", TavernCount
    smokeries = "smokeries", SmokeryCount
    fishers_houses = "fisher's houses", FishersHouseCount


type BuildingCount = TavernCount | SmokeryCount | FishersHouseCount


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

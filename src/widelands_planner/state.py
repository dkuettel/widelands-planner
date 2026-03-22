from __future__ import annotations

import math
from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal


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


class Bname(StrEnum):
    taverns = "taverns"
    smokeries = "smokeries"
    fishers_houses = "fisher's houses"
    foresters_houses = "forester's houses"
    woodcutters_houses = "woodcutter's houses"
    wells = "wells"
    farms = "farms"
    reed_farms = "reed farms"
    coal_mines = "coal mines"
    rock_mines = "rock mines"
    clay_pits = "clay pits"
    brick_kilns = "brick kilns"
    fruit_collectors_houses = "fruit collector's houses"
    berry_farms = "berry farms"
    breweries = "breweries"
    bakeries = "bakeries"


@dataclass(frozen=True)
class BlockKind:
    name: str
    imports: set[Item]
    buildings: set[Bname]
    exports: set[Item]

    @classmethod
    def from_many(cls, kinds: list[BlockKind]):
        return cls(
            name=",".join(sorted(k.name for k in kinds)),
            imports={i for k in kinds for i in k.imports},
            buildings={b for k in kinds for b in k.buildings},
            exports={i for k in kinds for i in k.exports},
        )


def get_block_kinds() -> list[BlockKind]:
    return [
        BlockKind(
            name="materials",
            imports=set(),
            buildings={
                Bname.wells,
                Bname.reed_farms,
                Bname.clay_pits,
                Bname.brick_kilns,
                Bname.foresters_houses,
                Bname.woodcutters_houses,
            },
            exports={Item.brick, Item.clay, Item.reed, Item.log},
        ),
        BlockKind(
            name="rations",
            imports={Item.log},
            buildings={
                Bname.taverns,
                Bname.smokeries,
                Bname.fishers_houses,
                Bname.wells,
                Bname.farms,
                Bname.fruit_collectors_houses,
                Bname.berry_farms,
                Bname.bakeries,
            },
            exports={Item.ration},
        ),
    ]


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

    def sorted(self) -> Iterator[tuple[Item, float]]:
        for k, v in sorted(self.data.items()):
            if v != 0:
                yield (k, v)

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
    name: Bname
    takes: Ivec
    rate: float  # "takes" into "makes" per second
    makes: Ivec

    @classmethod
    def from_seconds(
        cls, name: Bname, short: float, long: float, count: int, item: Item
    ):
        # TODO do we want to adjust this? arent we often in the more optimal case?
        return cls(
            name, Ivec.from_zeros(), 1 / ((short + long) / 2), Ivec({item: count})
        )

    def __post_init__(self):
        assert self.rate >= 0

    def takes_ips(self) -> Ivec:
        return self.takes.smul(self.rate)

    def makes_ips(self) -> Ivec:
        return self.makes.smul(self.rate)

    def representative_count_from_ips(self, item: Item, ips: float) -> float:
        m = self.makes[item]
        if m == 0:
            return 0
        return ips / (m * self.rate)


# TODO only models two-input ration production, not the slower one-input possibility
@dataclass(frozen=True)
class TavernBuilding:
    name: Literal[Bname.taverns] = Bname.taverns
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

    def representative_count_from_ips(self, item: Item, ips: float) -> float:
        match item:
            case Item.ration:
                return ips / self.rate
            case _:
                return 0


@dataclass(frozen=True)
class ConfiguredTavernBuilding:
    building: TavernBuilding
    fruit_vs_bread: float
    fish_vs_meat: float
    name: Literal[Bname.taverns] = Bname.taverns

    def __post_init__(self):
        assert self.name
        assert 0 <= self.fruit_vs_bread <= 1
        assert 0 <= self.fish_vs_meat <= 1

    def takes_ips(self) -> Ivec:
        return self.building.takes_ips(self.fruit_vs_bread, self.fish_vs_meat)

    def makes_ips(self) -> Ivec:
        return self.building.makes_ips()


@dataclass(frozen=True)
class SmokeryBuilding:
    name: Literal[Bname.smokeries] = Bname.smokeries
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

    def representative_count_from_ips(self, item: Item, ips: float) -> float:
        match item:
            case Item.smoked_fish | Item.smoked_meat:
                return ips / self.rate
            case _:
                return 0


@dataclass(frozen=True)
class ConfiguredSmokeryBuilding:
    building: SmokeryBuilding
    fish_vs_meat: float
    name: Literal[Bname.smokeries] = Bname.smokeries

    def __post_init__(self):
        assert 0 <= self.fish_vs_meat <= 1
        assert self.name

    def takes_ips(self) -> Ivec:
        return self.building.takes_ips(self.fish_vs_meat)

    def makes_ips(self) -> Ivec:
        return self.building.makes_ips(self.fish_vs_meat)


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


def rate_from_seconds(seconds: float | tuple[float, float]) -> float:
    match seconds:
        case [a, b]:
            return 1 / ((a + b) / 2)
        case t:
            return 1 / t


def get_buildings() -> list[Building]:
    buildings = [
        TavernBuilding(),
        SmokeryBuilding(),
        PlainBuilding.from_seconds(Bname.fishers_houses, 26, 59, 1, Item.fish),
        PlainBuilding.from_seconds(Bname.foresters_houses, 24, 46, 1, Item.tree),
        PlainBuilding(
            Bname.woodcutters_houses,
            Ivec({Item.tree: 1}),
            rate_from_seconds((49, 89)),
            Ivec({Item.log: 1}),
        ),
        PlainBuilding.from_seconds(Bname.wells, 44, 44, 1, Item.water),
        PlainBuilding.from_seconds(Bname.farms, 49, 67, 1, Item.barley),
        PlainBuilding.from_seconds(Bname.reed_farms, 52, 67, 1, Item.reed),
        PlainBuilding(
            Bname.coal_mines,
            Ivec({Item.ration: 1}),
            rate_from_seconds(2 * 41),
            Ivec({Item.coal: 2}),
        ),
        PlainBuilding(
            Bname.rock_mines,
            Ivec({Item.ration: 1}),
            rate_from_seconds(2 * 46),
            Ivec({Item.granite: 2}),
        ),
        PlainBuilding(
            Bname.clay_pits,
            Ivec({Item.water: 1}),
            rate_from_seconds((55, 73)),
            Ivec({Item.clay: 1}),
        ),
        PlainBuilding(
            Bname.brick_kilns,
            Ivec({Item.coal: 1, Item.clay: 3, Item.granite: 1}),
            rate_from_seconds(3 * 30),
            Ivec({Item.brick: 3}),
        ),
        PlainBuilding(
            Bname.fruit_collectors_houses,
            Ivec({Item.berry_bush: 1}),
            rate_from_seconds((37, 62)),
            Ivec({Item.fruit: 1}),
        ),
        PlainBuilding.from_seconds(Bname.berry_farms, 33, 51, 1, Item.berry_bush),
        PlainBuilding(
            Bname.breweries,
            Ivec({Item.water: 1, Item.barley: 1}),
            rate_from_seconds(64),
            Ivec({Item.beer: 1}),
        ),
        PlainBuilding(
            Bname.bakeries,
            Ivec({Item.barley: 1, Item.water: 1}),
            rate_from_seconds(44),
            Ivec({Item.bread: 1}),
        ),
    ]
    assert len(buildings) == len({b.name for b in buildings})
    return buildings


def get_building_by_names(names: set[Bname]) -> list[Building]:
    buildings = get_buildings()
    buildings = [b for b in buildings if b.name in names]
    return buildings


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


@dataclass(frozen=True)
class Block:
    name: str
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
        imports=Ivec(imports),
        local=Ivec(local),
        exports=Ivec(exports),
    )


def get_global_balance(blocks: list[BlockBalance]) -> Ivec:
    imports = [b.imports.negate() for b in blocks]
    exports = [b.exports for b in blocks]
    return Ivec.from_sum(imports + exports)


def building_count_from_ips(item: Item, ips: float) -> list[tuple[Bname, float]]:
    counts: list[tuple[Bname, float]] = []
    for building in get_buildings():
        c = building.representative_count_from_ips(item, ips)
        if c != 0:
            counts.append((building.name, c))
    return counts

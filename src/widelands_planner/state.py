from __future__ import annotations

import math
from collections.abc import Iterator, Set
from dataclasses import dataclass
from enum import StrEnum


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


def get_items() -> list[Item]:
    return sorted(Item, key=lambda i: i.value)


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
    iron_mines = "iron mines"
    furnaces = "furnaces"


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
    takes: Ivec
    rate: float  # "takes" into "makes" per second
    makes: Ivec

    @classmethod
    def from_seconds(cls, short: float, long: float, count: int, item: Item):
        # TODO do we want to adjust this? arent we often in the more optimal case?
        return cls(Ivec.from_zeros(), 1 / ((short + long) / 2), Ivec({item: count}))

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


def take_ratio(item: Item, takes: Set[Item]) -> float:
    return len({item} & takes) / len(takes)


@dataclass(frozen=True)
class TakeMake:
    take: Ivec
    make: Ivec

    @classmethod
    def from_zeros(cls):
        return cls(Ivec.from_zeros(), Ivec.from_zeros())


@dataclass(frozen=True)
class TavernBuilding:
    def get_take_items(self) -> set[Item]:
        return {Item.fruit, Item.bread, Item.smoked_fish, Item.smoked_meat}

    def get_ips(self, takes: Set[Item]) -> TakeMake:
        tr = take_ratio

        in1 = {Item.fruit, Item.bread} & takes
        in2 = {Item.smoked_fish, Item.smoked_meat} & takes
        if in1 and in2:  # with both inputs, we produce 2 for 2 at a faster rate
            r = 1 / 37
            return TakeMake(
                Ivec(
                    {
                        Item.fruit: r / 2 * tr(Item.fruit, in1),
                        Item.bread: r / 2 * tr(Item.bread, in1),
                        Item.smoked_fish: r / 2 * tr(Item.smoked_fish, in2),
                        Item.smoked_meat: r / 2 * tr(Item.smoked_meat, in2),
                    }
                ),
                Ivec({Item.ration: r}),
            )

        ins = {Item.fruit, Item.bread, Item.smoked_fish, Item.smoked_meat} & takes
        if ins:  # with just one input we produce 1 for 1 but slower
            r = 1 / 55
            return TakeMake(
                Ivec({i: (r * tr(i, ins)) for i in ins}),
                Ivec({Item.ration: r}),
            )

        return TakeMake.from_zeros()

    def takes_ips(self, takes: Set[Item]) -> Ivec:
        return self.get_ips(takes).take

    def makes_ips(self, takes: Set[Item]) -> Ivec:
        return self.get_ips(takes).make

    def representative_count_from_ips(self, item: Item, ips: float) -> float:
        match item:
            case Item.ration:
                r = 1 / 37
                return ips / r
            case _:
                return 0


@dataclass(frozen=True)
class ConfiguredTavernBuilding:
    building: TavernBuilding
    takes: set[Item]

    def takes_ips(self) -> Ivec:
        return self.building.takes_ips(self.takes)

    def makes_ips(self) -> Ivec:
        return self.building.makes_ips(self.takes)


@dataclass(frozen=True)
class SmokeryBuilding:
    def get_take_items(self) -> set[Item]:
        return {Item.fish, Item.meat}

    def get_ips(self, takes: set[Item]) -> TakeMake:
        tr = take_ratio
        ins = {Item.fish, Item.meat} & takes
        if ins:
            r = 1 / 27
            return TakeMake(
                Ivec(
                    {
                        Item.log: 0.5 * r,
                        Item.fish: r * tr(Item.fish, takes),
                        Item.meat: r * tr(Item.meat, takes),
                    }
                ),
                Ivec(
                    {
                        Item.smoked_fish: r * tr(Item.fish, takes),
                        Item.smoked_meat: r * tr(Item.meat, takes),
                    }
                ),
            )
        return TakeMake.from_zeros()

    def takes_ips(self, takes: set[Item]) -> Ivec:
        return self.get_ips(takes).take

    def makes_ips(self, takes: set[Item]) -> Ivec:
        return self.get_ips(takes).make

    def representative_count_from_ips(self, item: Item, ips: float) -> float:
        match item:
            case Item.smoked_fish | Item.smoked_meat:
                r = 1 / 27
                return ips / r
            case _:
                return 0


@dataclass(frozen=True)
class ConfiguredSmokeryBuilding:
    building: SmokeryBuilding
    takes: set[Item]

    def takes_ips(self) -> Ivec:
        return self.building.takes_ips(self.takes)

    def makes_ips(self) -> Ivec:
        return self.building.makes_ips(self.takes)


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


def rate_from_seconds(seconds: float | tuple[float, float]) -> float:
    match seconds:
        case [a, b]:
            return 1 / ((a + b) / 2)
        case t:
            return 1 / t


def get_buildings() -> dict[Bname, Building]:
    buildings = {
        Bname.taverns: TavernBuilding(),
        Bname.smokeries: SmokeryBuilding(),
        Bname.fishers_houses: PlainBuilding.from_seconds(26, 59, 1, Item.fish),
        Bname.foresters_houses: PlainBuilding.from_seconds(24, 46, 1, Item.tree),
        Bname.woodcutters_houses: PlainBuilding(
            Ivec({Item.tree: 1}),
            rate_from_seconds((49, 89)),
            Ivec({Item.log: 1}),
        ),
        Bname.wells: PlainBuilding.from_seconds(44, 44, 1, Item.water),
        Bname.farms: PlainBuilding.from_seconds(49, 67, 1, Item.barley),
        Bname.reed_farms: PlainBuilding.from_seconds(52, 67, 1, Item.reed),
        Bname.coal_mines: PlainBuilding(
            Ivec({Item.ration: 1}),
            rate_from_seconds(2 * 41),
            Ivec({Item.coal: 2}),
        ),
        Bname.rock_mines: PlainBuilding(
            Ivec({Item.ration: 1}),
            rate_from_seconds(2 * 46),
            Ivec({Item.granite: 2}),
        ),
        Bname.iron_mines: PlainBuilding(
            Ivec({Item.ration: 1}),
            rate_from_seconds(69),
            Ivec({Item.iron_ore: 1}),
        ),
        Bname.clay_pits: PlainBuilding(
            Ivec({Item.water: 1}),
            rate_from_seconds((55, 73)),
            Ivec({Item.clay: 1}),
        ),
        Bname.brick_kilns: PlainBuilding(
            Ivec({Item.coal: 1, Item.clay: 3, Item.granite: 1}),
            rate_from_seconds(3 * 30),
            Ivec({Item.brick: 3}),
        ),
        Bname.fruit_collectors_houses: PlainBuilding(
            Ivec({Item.berry_bush: 1}),
            rate_from_seconds((37, 62)),
            Ivec({Item.fruit: 1}),
        ),
        Bname.berry_farms: PlainBuilding.from_seconds(33, 51, 1, Item.berry_bush),
        Bname.breweries: PlainBuilding(
            Ivec({Item.water: 1, Item.barley: 1}),
            rate_from_seconds(64),
            Ivec({Item.beer: 1}),
        ),
        Bname.bakeries: PlainBuilding(
            Ivec({Item.barley: 1, Item.water: 1}),
            rate_from_seconds(44),
            Ivec({Item.bread: 1}),
        ),
        # TODO hm it doesnt make sense with the timings
        # 1+1 vs 2 doesnt add up
        # until we can test it go with the iron only?
        # allow more than one variation, and only configure mixed or pure, no slider
        # Bname.furnaces: ...,
    }
    return dict(sorted(buildings.items()))


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
    # TODO keep around?
    for name, building in get_buildings().items():
        c = building.representative_count_from_ips(item, ips)
        if c != 0:
            counts.append((name, c))
    return counts

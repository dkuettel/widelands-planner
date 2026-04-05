from __future__ import annotations

import math
import re
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from functools import cache, partial
from pathlib import Path


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
    deer = "deer"
    fur = "fur"


def get_items() -> list[Item]:
    return sorted(Item, key=lambda i: i.value)


# NOTE the name is the widelands lua name, the value is the plural string
# TODO still not sure how robust is st.multiselect and co with enums and round-trips
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
    brewery = "breweries"
    bakery = "bakeries"
    ironmine = "iron mines"
    furnace = "furnaces"
    small_armor_smithy = "small armor smithies"
    blacksmithy = "blacksmithies"
    barracks = "barracks"
    reindeer_farm = "reindeer farms"
    sewing_room = "sewing room"


@dataclass(frozen=True)
class Ivec:
    # TODO can we protect this dict from changes to be safe?
    data: dict[Item, float]

    @classmethod
    def from_zeros(cls):
        return cls(dict())

    @classmethod
    def from_sum(cls, rates: Sequence[Ivec]):
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

    def sdiv(self, s: float) -> Ivec:
        return self.smul(1 / s)

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

    def nonzero_items(self) -> set[Item]:
        return {i for (i, v) in self.data.items() if v != 0}

    def is_zero(self) -> bool:
        return all(v == 0 for v in self.data.values())


@dataclass(frozen=True)
class TakeMake:
    take: Ivec
    make: Ivec

    @classmethod
    def from_zeros(cls):
        return cls(Ivec.from_zeros(), Ivec.from_zeros())


@dataclass(frozen=True)
class Crafting:
    take: Ivec
    make: Ivec
    seconds: tuple[float, float]  # (short, long)
    unless: None | set[Item] = None  # skip this crafting when these items are available

    def __post_init__(self):
        assert self.seconds[0] <= self.seconds[1]


@dataclass(frozen=True)
class BaseBuilding:
    craftings: list[Crafting]
    pause: float

    @classmethod
    def from_lua(cls, take: dict[Item, float], make: dict[Item, float], timings: str):
        path = Path(
            f"widelands/data/tribes/buildings/productionsites/frisians/{timings}/init.lua"
        )
        short, long = extract_plain_timings(path)
        return cls(
            [
                Crafting(
                    take=Ivec(take),
                    make=Ivec(make),
                    seconds=(short, long),
                )
            ],
            0,
        )

    def get_take_items(self) -> set[Item]:
        return {i for c in self.craftings for i in c.take.nonzero_items()}

    def get_make_items(self) -> set[Item]:
        return {i for c in self.craftings for i in c.make.nonzero_items()}

    def get_ips(self, takes: set[Item], makes: set[Item], speed: float) -> TakeMake:
        dt = 0  # cycle duration seconds
        tk = Ivec.from_zeros()  # cycle take items
        mk = Ivec.from_zeros()  # cycle make items

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

        if dt > 0:
            return TakeMake(take=tk.sdiv(dt), make=mk.sdiv(dt))

        return TakeMake(take=Ivec.from_zeros(), make=Ivec.from_zeros())

    def takes_ips(self, takes: set[Item], makes: set[Item], speed: float) -> Ivec:
        return self.get_ips(takes, makes, speed).take

    def makes_ips(self, takes: set[Item], makes: set[Item], speed: float) -> Ivec:
        return self.get_ips(takes, makes, speed).make

    def representative_count_from_ips(self, item: Item, ips: float) -> float:
        rep = self.get_ips(self.get_take_items(), self.get_make_items(), 1)
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
    speed: float  # 0 -> worst speed, 1 -> best speed

    def takes_ips(self) -> Ivec:
        return self.building.takes_ips(self.takes, self.makes, self.speed)

    def makes_ips(self) -> Ivec:
        return self.building.makes_ips(self.takes, self.makes, self.speed)


type Building = BaseBuilding
type ConfiguredBuilding = ConfiguredGenericBuilding


@dataclass(frozen=True)
class BuildingCount:
    count: int
    building: ConfiguredBuilding
    usage: float

    def __post_init__(self):
        assert self.count >= 0
        assert 0 <= self.usage <= 1

    def takes_ips(self) -> Ivec:
        return self.building.takes_ips().smul(self.count * self.usage)

    def makes_ips(self) -> Ivec:
        return self.building.makes_ips().smul(self.count * self.usage)


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
    b = partial(BaseBuilding.from_lua, timings=name.name)
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
        case Bname.clay_pit:
            return b({Item.water: 1}, {Item.clay: 1})
        case Bname.brick_kiln:
            return b({Item.coal: 1, Item.clay: 3, Item.granite: 1}, {Item.brick: 3})
        case Bname.collectors_house:
            return b({Item.berry_bush: 1}, {Item.fruit: 1})
        case Bname.berry_farm:
            return b({}, {Item.berry_bush: 1})
        case Bname.brewery:
            return b({Item.barley: 1, Item.water: 1}, {Item.beer: 1})
        case Bname.bakery:
            return b({Item.barley: 1, Item.water: 1}, {Item.bread: 1})
        case Bname.barracks:
            return b({Item.fur_garment: 1, Item.short_sword: 1}, {})
        case Bname.sewing_room:
            return b({Item.fur: 2}, {Item.fur_garment: 1})
        case Bname.blacksmithy:
            dt = (70.167, 70.167)
            # TODO hm maybe could be extracted? timings at least
            return BaseBuilding(
                craftings=[
                    Crafting(Ivec({Item.iron: 1, Item.log: 1}), Ivec({i: 1}), dt)
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
                    Crafting(Ivec({Item.iron: 1}), Ivec({Item.needles: 2}), dt),
                    Crafting(
                        Ivec({Item.reed: 1, Item.log: 1}),
                        Ivec({Item.basket: 1}),
                        dt,
                    ),
                    Crafting(Ivec({Item.iron: 1}), Ivec({Item.fire_tongs: 1}), dt),
                    Crafting(Ivec({Item.reed: 2}), Ivec({Item.fishing_net: 1}), dt),
                ],
                pause=10,
            )
        case Bname.tavern:
            return BaseBuilding(
                craftings=[
                    Crafting(
                        Ivec({Item.fruit: 1}),
                        Ivec({Item.ration: 1}),
                        (55, 55),
                        unless={Item.smoked_fish, Item.smoked_meat},
                    ),
                    Crafting(
                        Ivec({Item.bread: 1}),
                        Ivec({Item.ration: 1}),
                        (55, 55),
                        unless={Item.smoked_fish, Item.smoked_meat},
                    ),
                    Crafting(
                        Ivec({Item.smoked_fish: 1}),
                        Ivec({Item.ration: 1}),
                        (55, 55),
                        unless={Item.fruit, Item.bread},
                    ),
                    Crafting(
                        Ivec({Item.smoked_meat: 1}),
                        Ivec({Item.ration: 1}),
                        (55, 55),
                        unless={Item.fruit, Item.bread},
                    ),
                    Crafting(
                        Ivec({Item.fruit: 1, Item.smoked_fish: 1}),
                        Ivec({Item.ration: 2}),
                        (74, 74),
                    ),
                    Crafting(
                        Ivec({Item.fruit: 1, Item.smoked_meat: 1}),
                        Ivec({Item.ration: 2}),
                        (74, 74),
                    ),
                    Crafting(
                        Ivec({Item.bread: 1, Item.smoked_fish: 1}),
                        Ivec({Item.ration: 2}),
                        (74, 74),
                    ),
                    Crafting(
                        Ivec({Item.bread: 1, Item.smoked_meat: 1}),
                        Ivec({Item.ration: 2}),
                        (74, 74),
                    ),
                ],
                pause=0,
            )
        case Bname.smokery:
            return BaseBuilding(
                [
                    Crafting(
                        Ivec({Item.log: 1, Item.fish: 2}),
                        Ivec({Item.smoked_fish: 2}),
                        (54, 54),
                    ),
                    Crafting(
                        Ivec({Item.log: 1, Item.meat: 2}),
                        Ivec({Item.smoked_meat: 2}),
                        (54, 54),
                    ),
                ],
                0,
            )
        case Bname.furnace:
            return BaseBuilding(
                [
                    Crafting(
                        Ivec({Item.coal: 1, Item.iron_ore: 1}),
                        Ivec({Item.iron: 1}),
                        (64, 64),
                    ),
                    Crafting(
                        Ivec({Item.coal: 1, Item.gold_ore: 1}),
                        Ivec({Item.gold: 1}),
                        (66, 66),
                    ),
                    Crafting(
                        Ivec({Item.coal: 1, Item.iron_ore: 1}),
                        Ivec({Item.iron: 1}),
                        (64, 64),
                    ),
                ],
                0,
            )
        case Bname.small_armor_smithy:
            return BaseBuilding(
                [
                    Crafting(
                        Ivec({Item.coal: 1, Item.iron: 1}),
                        Ivec({Item.short_sword: 1}),
                        (58, 58),
                    ),
                    Crafting(
                        Ivec({Item.coal: 1, Item.iron: 2}),
                        Ivec({Item.long_sword: 1}),
                        (58, 58),
                    ),
                    Crafting(
                        Ivec({Item.coal: 1, Item.iron: 1}),
                        Ivec({Item.helmet: 1}),
                        (68, 68),
                    ),
                ],
                10,
            )
        case Bname.reindeer_farm:
            # TODO it actually makes meat, even when only fur is needed
            # maybe after all this part needs to just be code?
            return BaseBuilding(
                [
                    Crafting(
                        Ivec({Item.water: 1, Item.barley: 1}),
                        Ivec({Item.deer: 1}),
                        (30, 30),
                    ),
                    Crafting(
                        Ivec({Item.water: 1, Item.barley: 1}),
                        Ivec({Item.fur: 1}),
                        (38.6, 38.6),
                    ),
                    Crafting(
                        Ivec({Item.water: 1, Item.barley: 1}),
                        Ivec({Item.deer: 1}),
                        (30, 30),
                    ),
                    Crafting(
                        Ivec({Item.water: 1, Item.barley: 1}),
                        Ivec({Item.fur: 1}),
                        (38.6, 38.6),
                    ),
                    Crafting(
                        Ivec({Item.water: 1, Item.barley: 1}),
                        Ivec({Item.deer: 1}),
                        (30, 30),
                    ),
                    Crafting(
                        Ivec({Item.water: 1, Item.barley: 1}),
                        Ivec({Item.fur: 1, Item.meat: 1}),
                        (42.2, 42.2),
                    ),
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

from __future__ import annotations

import math
import re
from collections.abc import Iterator, Mapping, Sequence, Set
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
        return all(abs(self[i] - other[i]) <= eps for i in self.data) or all(
            abs(self[i] - other[i]) <= eps for i in other.data
        )

    def min(self) -> float:
        # TODO very ambigous, and default too
        return min(self.data.values(), default=0)


type Ivec = Vec[Item]


def izeros() -> Ivec:
    return Vec[Item].from_zeros(Item)


def ifrom(data: dict[Item, float]) -> Ivec:
    return Vec[Item](Item, data)


def isum(sequence: Sequence[Ivec]) -> Ivec:
    return Vec[Item].from_sum(Item, sequence)


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
    speed: float  # 0 -> worst speed, 1 -> best speed

    def takes_ips(self, take: Ivec | None = None, make: Ivec | None = None) -> Ivec:
        return self.building.takes_ips(take, make, self.takes, self.makes, self.speed)

    def makes_ips(self, take: Ivec | None = None, make: Ivec | None = None) -> Ivec:
        return self.building.makes_ips(take, make, self.takes, self.makes, self.speed)


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

    def takes_ips(self, take: Ivec | None = None, make: Ivec | None = None) -> Ivec:
        return self.building.takes_ips(take, make).smul(self.count * self.usage)

    def makes_ips(self, take: Ivec | None = None, make: Ivec | None = None) -> Ivec:
        return self.building.makes_ips(take, make).smul(self.count * self.usage)


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
                craftings=[
                    Crafting(
                        ifrom({Item.fruit: 1}),
                        ifrom({Item.ration: 1}),
                        (55, 55),
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


def wip(blocks: list[Block]) -> tuple[Ivec, Ivec]:
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
    assert take.lte(make)

    # TODO really need a dataclass for this, so easy to flip
    return take, make


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

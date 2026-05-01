from __future__ import annotations

from widelands_planner.state import (
    Block,
    Bname,
    BuildingCount,
    ConfiguredBuilding,
    ConfiguredGenericBuilding,
    Item,
    building_from_name,
    fixpoint,
    get_buildings,
    ifrom,
    izeros,
    print_block,
)


def setup1() -> list[Block]:
    buildings = get_buildings()
    block = Block(
        buildings=[
            BuildingCount(
                1,
                ConfiguredGenericBuilding(
                    buildings[Bname.foresters_house],
                    takes=set(),
                    makes={Item.tree},
                    speed=1.0,
                ),
            ),
            BuildingCount(
                3,
                ConfiguredGenericBuilding(
                    buildings[Bname.woodcutters_house],
                    takes={Item.tree},
                    makes={Item.log},
                    speed=1.0,
                ),
            ),
        ],
    )

    return [block]


def setup2() -> list[Block]:
    buildings = get_buildings()
    block1 = Block(
        buildings=[
            BuildingCount(
                1,
                ConfiguredGenericBuilding(
                    buildings[Bname.foresters_house],
                    takes=set(),
                    makes={Item.tree},
                    speed=1.0,
                ),
            ),
            BuildingCount(
                3,
                ConfiguredGenericBuilding(
                    buildings[Bname.woodcutters_house],
                    takes={Item.tree},
                    makes={Item.log},
                    speed=1.0,
                ),
            ),
        ],
    )
    block2 = Block(
        buildings=[
            BuildingCount(
                1,
                ConfiguredGenericBuilding(
                    buildings[Bname.foresters_house],
                    takes=set(),
                    makes={Item.tree},
                    speed=1.0,
                ),
            ),
        ],
    )

    return [block1, block2]


def setup3() -> list[Block]:
    buildings = get_buildings()
    block1 = Block(
        buildings=[
            BuildingCount(
                3,
                ConfiguredGenericBuilding(
                    buildings[Bname.foresters_house],
                    takes=set(),
                    makes={Item.tree},
                    speed=1.0,
                ),
            ),
            BuildingCount(
                3,
                ConfiguredGenericBuilding(
                    buildings[Bname.woodcutters_house],
                    takes={Item.tree},
                    makes={Item.log},
                    speed=1.0,
                ),
            ),
        ],
    )
    block2 = Block(
        buildings=[
            BuildingCount(
                4,
                ConfiguredGenericBuilding(
                    buildings[Bname.fishers_house],
                    takes=set(),
                    makes={Item.fish},
                    speed=1.0,
                ),
            ),
            BuildingCount(
                2,
                ConfiguredGenericBuilding(
                    buildings[Bname.smokery],
                    takes={Item.fish, Item.log},
                    makes={Item.smoked_fish},
                    speed=1.0,
                ),
            ),
            BuildingCount(
                1,
                ConfiguredGenericBuilding(
                    buildings[Bname.farm],
                    takes=set(),
                    makes={Item.barley},
                    speed=1.0,
                ),
            ),
            BuildingCount(
                1,
                ConfiguredGenericBuilding(
                    buildings[Bname.bakery],
                    takes={Item.barley, Item.water},
                    makes={Item.bread},
                    speed=1.0,
                ),
            ),
            BuildingCount(
                1,
                ConfiguredGenericBuilding(
                    buildings[Bname.well],
                    takes=set(),
                    makes={Item.water},
                    speed=1.0,
                ),
            ),
            BuildingCount(
                6,
                ConfiguredGenericBuilding(
                    buildings[Bname.tavern],
                    takes={Item.smoked_fish, Item.bread},
                    makes={Item.ration},
                    speed=1.0,
                ),
            ),
        ],
    )

    return [block1, block2]


def setup4() -> list[Block]:
    buildings = get_buildings()
    blocks: list[Block] = []
    for _ in range(2):
        blocks.append(
            Block(
                buildings=[
                    BuildingCount(
                        3,
                        ConfiguredGenericBuilding(
                            buildings[Bname.foresters_house],
                            takes=set(),
                            makes={Item.tree},
                            speed=1.0,
                        ),
                    ),
                    BuildingCount(
                        3,
                        ConfiguredGenericBuilding(
                            buildings[Bname.woodcutters_house],
                            takes={Item.tree},
                            makes={Item.log},
                            speed=1.0,
                        ),
                    ),
                    BuildingCount(
                        40,
                        ConfiguredGenericBuilding(
                            buildings[Bname.fishers_house],
                            takes=set(),
                            makes={Item.fish},
                            speed=1.0,
                        ),
                    ),
                    BuildingCount(
                        2,
                        ConfiguredGenericBuilding(
                            buildings[Bname.smokery],
                            takes={Item.fish, Item.log},
                            makes={Item.smoked_fish},
                            speed=1.0,
                        ),
                    ),
                    BuildingCount(
                        1,
                        ConfiguredGenericBuilding(
                            buildings[Bname.farm],
                            takes=set(),
                            makes={Item.barley},
                            speed=1.0,
                        ),
                    ),
                    BuildingCount(
                        1,
                        ConfiguredGenericBuilding(
                            buildings[Bname.bakery],
                            takes={Item.barley, Item.water},
                            makes={Item.bread},
                            speed=1.0,
                        ),
                    ),
                    BuildingCount(
                        1,
                        ConfiguredGenericBuilding(
                            buildings[Bname.well],
                            takes=set(),
                            makes={Item.water},
                            speed=1.0,
                        ),
                    ),
                    BuildingCount(
                        6,
                        ConfiguredGenericBuilding(
                            buildings[Bname.tavern],
                            takes={Item.smoked_fish, Item.bread},
                            makes={Item.ration},
                            speed=1.0,
                        ),
                    ),
                ],
            )
        )

    return blocks


def setup5() -> list[Block]:
    buildings = get_buildings()
    block = Block(
        buildings=[
            BuildingCount(
                20,
                ConfiguredGenericBuilding(
                    buildings[Bname.well],
                    takes=set(),
                    makes={Item.water},
                    speed=1.0,
                ),
            ),
            BuildingCount(
                20,
                ConfiguredGenericBuilding(
                    buildings[Bname.farm],
                    takes=set(),
                    makes={Item.barley},
                    speed=1.0,
                ),
            ),
            BuildingCount(
                20,
                ConfiguredGenericBuilding(
                    buildings[Bname.reindeer_farm],
                    takes={Item.water, Item.barley},
                    makes={Item.deer, Item.fur, Item.meat},
                    speed=1.0,
                ),
            ),
            BuildingCount(
                1,
                ConfiguredGenericBuilding(
                    buildings[Bname.foresters_house],
                    takes=set(),
                    makes={Item.tree},
                    speed=1.0,
                ),
            ),
            BuildingCount(
                1,
                ConfiguredGenericBuilding(
                    buildings[Bname.woodcutters_house],
                    takes={Item.tree},
                    makes={Item.log},
                    speed=1.0,
                ),
            ),
            BuildingCount(
                1,
                ConfiguredGenericBuilding(
                    buildings[Bname.smokery],
                    takes={Item.meat, Item.log},
                    makes={Item.smoked_meat},
                    speed=1.0,
                ),
            ),
            BuildingCount(
                1,
                ConfiguredGenericBuilding(
                    buildings[Bname.tavern],
                    takes={Item.smoked_meat},
                    makes={Item.ration},
                    speed=1.0,
                ),
            ),
        ],
    )

    return [block]


def setup6() -> list[Block]:
    buildings = get_buildings()
    block = Block(
        buildings=[
            BuildingCount(
                2,
                ConfiguredGenericBuilding(
                    buildings[Bname.berry_farm],
                    takes=set(),
                    makes={Item.berry_bush},
                    speed=1.0,
                ),
            ),
            BuildingCount(
                2,
                ConfiguredGenericBuilding(
                    buildings[Bname.collectors_house],
                    takes={Item.berry_bush},
                    makes={Item.fruit},
                    speed=1.0,
                ),
            ),
            BuildingCount(
                2,
                ConfiguredGenericBuilding(
                    buildings[Bname.tavern],
                    takes={Item.fruit},
                    makes={Item.ration},
                    speed=1.0,
                ),
            ),
            BuildingCount(
                1,
                ConfiguredGenericBuilding(
                    buildings[Bname.coalmine],
                    takes={Item.ration},
                    makes={Item.coal},
                    speed=1.0,
                ),
            ),
            BuildingCount(
                1,
                ConfiguredGenericBuilding(
                    buildings[Bname.ironmine],
                    takes={Item.ration},
                    makes={Item.iron_ore},
                    speed=1.0,
                ),
            ),
            BuildingCount(
                1,
                ConfiguredGenericBuilding(
                    buildings[Bname.furnace],
                    takes={Item.coal, Item.iron_ore},
                    makes={Item.iron},
                    speed=1.0,
                ),
            ),
            BuildingCount(
                1,
                ConfiguredGenericBuilding(
                    buildings[Bname.blacksmithy],
                    takes={Item.iron, Item.coal},
                    makes={Item.needles},
                    speed=1.0,
                ),
            ),
        ],
    )

    return [block]


def examples():
    # blocks = setup1()
    # blocks = setup2()
    # blocks = setup3()
    # blocks = setup4()
    # blocks = setup5()
    blocks = setup6()

    status, blocked_allocated = fixpoint(blocks)

    print(status)

    for i, allocated in enumerate(blocked_allocated):
        print()
        print(f"block {i}:")
        print_block(allocated)


def wants():
    building = building_from_name(Bname.tavern)
    count = BuildingCount(
        1,
        ConfiguredGenericBuilding(
            building,
            building.get_take_items(),
            building.get_make_items(),
            1.0,
        ),
    )
    w = count.building.wants_ips(Item.fruit)
    print(w)


def test():
    examples()
    # wants()

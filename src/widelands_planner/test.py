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


def usage():
    count = BuildingCount(
        1,
        ConfiguredGenericBuilding(
            building_from_name(Bname.blacksmithy),
            {Item.iron},
            {Item.fire_tongs, Item.needles},
            1.0,
        ),
    )
    # u = count.usage_for(
    #     ifrom({i: 0.0 for i in Item}).updated({Item.iron: 0.012473960607232402}),
    #     ifrom({i: 0.0 for i in Item}).updated(
    #         {Item.fire_tongs: 0.006236980303616201, Item.needles: 0.012473960607232402},
    #     ),
    # )
    w = count.building.wants_ips(Item.iron)
    print(w)
    # TODO this only gives 94% ... but wants didnt want more? we give exactly what it wanted
    # ok wants ips and usage_for dont agree, which one is wrong?
    # u = count.usage_for(
    #     ifrom({Item.iron: 0.012473960607232402}),
    #     ifrom(
    #         {Item.fire_tongs: 0.006236980303616201, Item.needles: 0.012473960607232402},
    #     ),
    # )
    # w = w / 0.93
    u = count.usage_for(
        ifrom({Item.iron: w}),
        ifrom(
            {Item.fire_tongs: w / 2, Item.needles: w},
        ),
    )
    print(u)


def test():
    examples()
    # usage()

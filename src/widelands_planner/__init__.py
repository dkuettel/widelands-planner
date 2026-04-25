from widelands_planner.state import (
    Block,
    Bname,
    BuildingCount,
    ConfiguredGenericBuilding,
    Item,
    Ivec,
    fixpoint,
    get_buildings,
)


def setup1() -> list[Block]:
    buildings = get_buildings()
    block = Block(
        imports=set(),
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
        exports=set(),
    )

    return [block]


def setup2() -> list[Block]:
    buildings = get_buildings()
    block1 = Block(
        imports=set(),
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
        exports=set(),
    )
    block2 = Block(
        imports=set(),
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
        exports=set(),
    )

    return [block1, block2]


def setup3() -> list[Block]:
    buildings = get_buildings()
    block1 = Block(
        imports=set(),
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
        exports=set(),
    )
    block2 = Block(
        imports=set(),
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
        exports=set(),
    )

    return [block1, block2]


def setup4() -> list[Block]:
    buildings = get_buildings()
    blocks: list[Block] = []
    for _ in range(2):
        blocks.append(
            Block(
                imports=set(),
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
                exports=set(),
            )
        )

    return blocks


def test():
    # blocks = setup1()
    # blocks = setup2()
    # blocks = setup3()
    blocks = setup4()

    for opt, solution in fixpoint(blocks):
        pass

    print(opt)

    def str_from_ivec(vec: Ivec) -> str:
        data = [f"{i.name}: {v:.2f}" for i, v in vec.data.items() if v != 0.0]
        return "{" + ", ".join(data) + "}"

    for count, (local, remote) in solution:
        name = count.building.building.name
        print(name, str_from_ivec(local), str_from_ivec(remote))

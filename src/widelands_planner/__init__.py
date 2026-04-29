from __future__ import annotations

from collections import deque
from collections.abc import Iterable

from tabulate import tabulate

from widelands_planner.state import (
    Allocated,
    Block,
    Bname,
    BuildingCount,
    ConfiguredGenericBuilding,
    Item,
    Ivec,
    fixpoint,
    get_buildings,
    isum,
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
                exports=set(),
            )
        )

    return blocks


def setup5() -> list[Block]:
    buildings = get_buildings()
    block = Block(
        imports=set(),
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
        exports=set(),
    )

    return [block]


def str_from_ivec(vec: Ivec) -> str:
    data = [f"{i.name}: {v:.1f}" for i, v in vec.data.items() if v != 0.0]
    return "{" + ", ".join(data) + "}"


def str_from_usage(alloc: Allocated) -> str:
    return f"{round(alloc.stable_usage * 100)}% + {round((alloc.flood_usage - alloc.stable_usage) * 100)}%"


def test():
    # blocks = setup1()
    # blocks = setup2()
    # blocks = setup3()
    # blocks = setup4()
    blocks = setup5()

    converged, allocated = fixpoint(blocks)

    if not converged:
        print("did not converge")

    for i, block in enumerate(blocks):
        ids = {id(building) for building in block.buildings}
        data = [
            (
                alloc.building.count,
                str_from_usage(alloc),
                alloc.building.building.building.name,
                (
                    str_from_ivec(alloc.take_local.smul(60))
                    + " + "
                    + str_from_ivec(alloc.take_remote.smul(60))
                ),
                (
                    str_from_ivec(alloc.make_main_local.smul(60))
                    + "/"
                    + str_from_ivec(alloc.make_aux_local.smul(60))
                    + " + "
                    + str_from_ivec(alloc.make_main_remote.smul(60))
                    + "/"
                    + str_from_ivec(alloc.make_aux_remote.smul(60))
                ),
            )
            for alloc in allocated
            if id(alloc.building) in ids
        ]
        print()
        print(f"block {i}:")
        print(tabulate(data, headers=["#", "%", "name", "take i/m", "make i/m"]))

from __future__ import annotations

import pickle
from cProfile import Profile
from pathlib import Path

from widelands_planner.state import (
    Block,
    Bname,
    BuildingCount,
    ConfiguredGenericBuilding,
    Item,
    building_from_name,
    fixpoint,
    get_buildings,
    have_allocations_converged,
    print_block,
    rounded_allocations,
    solver_has_converged,
    solver_state_from_blocks,
    solver_update_state,
)


def make(count: int, name: Bname) -> BuildingCount:
    buildings = get_buildings()
    b = buildings[name]
    return BuildingCount(
        count,
        ConfiguredGenericBuilding(
            b,
            takes=b.get_take_items(),
            makes=b.get_make_items(),
            speed=1.0,
        ),
    )


def setup1() -> list[Block]:
    block = Block(
        buildings=[
            make(1, Bname.foresters_house),
            make(3, Bname.woodcutters_house),
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


def setup7() -> list[Block]:
    materials = Block(
        buildings=[
            make(2, Bname.reed_farm),
            make(2, Bname.woodcutters_house),
            make(2, Bname.foresters_house),
            make(4, Bname.clay_pit),
            make(2, Bname.brick_kiln),
            make(4, Bname.well),
        ],
    )
    food = Block(
        buildings=[
            make(2, Bname.tavern),
            make(2, Bname.smokery),
            make(2, Bname.fishers_house),
            make(1, Bname.collectors_house),
            make(1, Bname.berry_farm),
            make(2, Bname.tavern),
            make(2, Bname.bakery),
            make(3, Bname.farm),
            make(2, Bname.well),
        ],
    )
    mines = Block(
        buildings=[
            make(3, Bname.coalmine),
            make(1, Bname.rockmine),
            make(3, Bname.ironmine),
        ],
    )
    ironworks = Block(
        buildings=[
            make(2, Bname.furnace),
            make(1, Bname.blacksmithy),
            make(1, Bname.armor_smithy_small),
        ],
    )
    soldiers = Block(
        buildings=[
            make(1, Bname.barracks),
            make(1, Bname.sewing_room),
            make(2, Bname.reindeer_farm),
            make(3, Bname.farm),
            make(3, Bname.well),
        ],
    )
    wood = Block(
        buildings=[
            make(3, Bname.foresters_house),
            make(5, Bname.woodcutters_house),
        ],
    )
    food2 = Block(
        buildings=[
            make(4, Bname.tavern),
            make(2, Bname.smokery),
            make(2, Bname.fishers_house),
            make(2, Bname.woodcutters_house),
            make(2, Bname.foresters_house),
        ],
    )
    return [materials, food, mines, ironworks, soldiers, wood, food2]


def examples():
    # blocks = setup1()
    # blocks = setup2()
    # blocks = setup3()
    # blocks = setup4()
    # blocks = setup5()
    # blocks = setup6()
    blocks = setup7()

    status, blocked_allocated = fixpoint(blocks)

    print(status)

    for i, allocated in enumerate(blocked_allocated):
        print()
        print(f"block {i}:")
        print_block(allocated)


def bench():
    blocks = setup7()

    with Profile() as p:
        prev = None
        state = solver_state_from_blocks(blocks)
        while not solver_has_converged(prev, state):
            prev, state = state, solver_update_state(state)
        allocated = rounded_allocations(state)
    p.dump_stats("data.prof")

    gt = pickle.loads(Path("./solution.pickle").read_bytes())
    gt = [alloc for block in gt for alloc in block]

    assert have_allocations_converged(gt, allocated)
    print("solution is correct")

    # import os; os.system("uv tool run tuna data.prof")


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
    # examples()
    bench()
    # wants()

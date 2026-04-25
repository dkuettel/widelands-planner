from widelands_planner import state


def test():
    buildings = state.get_buildings()
    block = state.Block(
        imports=set(),
        buildings=[
            state.BuildingCount(
                1,
                state.ConfiguredGenericBuilding(
                    buildings[state.Bname.foresters_house],
                    takes=set(),
                    makes={state.Item.tree},
                    speed=1.0,
                ),
            ),
            state.BuildingCount(
                1,
                state.ConfiguredGenericBuilding(
                    buildings[state.Bname.woodcutters_house],
                    takes={state.Item.tree},
                    makes={state.Item.log},
                    speed=1.0,
                ),
            ),
        ],
        exports=set(),
    )

    blocks = [block]

    for opt, solution in state.fixpoint(blocks):
        pass

    print(opt)

    def str_from_ivec(vec: state.Ivec) -> str:
        data = [f"{i.name}: {v:.2f}" for i, v in vec.data.items() if v != 0.0]
        return "{" + ", ".join(data) + "}"

    for count, (local, remote) in solution:
        name = count.building.building.name
        print(name, str_from_ivec(local), str_from_ivec(remote))

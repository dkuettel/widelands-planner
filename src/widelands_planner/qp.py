from __future__ import annotations

import itertools
from collections.abc import Mapping, Sequence, Set
from dataclasses import dataclass
from typing import Any, override
from uuid import uuid4

import clarabel  # pyright: ignore[reportMissingTypeStubs]
import numpy as np
import rich
from scipy import sparse
from typer import Typer

type farray = np.typing.NDArray[np.floating]

app = Typer(no_args_is_help=True, rich_markup_mode=None, pretty_exceptions_enable=False)


class Var:
    uuid: str
    name: str
    lb: float | None
    ub: float | None

    def __init__(self, name: str, lb: float | None = None, ub: float | None = None):
        self.uuid = uuid4().hex
        self.name = name
        self.lb = lb
        self.ub = ub

    @override
    def __hash__(self) -> int:
        return hash(self.uuid)

    @override
    def __eq__(self, other: object) -> bool:
        match other:
            case Var():
                return self.uuid == other.uuid
            case _:
                return False

    @override
    def __str__(self) -> str:
        return self.name

    @override
    def __repr__(self) -> str:
        return f"'{self.name}'"


@dataclass(frozen=True)
class Eq:
    vars: dict[Var, float]
    const: float


@dataclass(frozen=True)
class Lt:
    vars: dict[Var, float]
    const: float


def get_vars(eqs: Sequence[Eq], lts: Sequence[Lt]) -> set[Var]:
    return {v for c in itertools.chain(eqs, lts) for v in c.vars.keys()}


def get_bounds(
    n: int, index: Mapping[Var, int], vars: Set[Var]
) -> tuple[farray, farray, list[Any]]:  # pyright: ignore[reportExplicitAny]
    assert n == len(vars)
    A = np.zeros((n, 2, n))
    b = np.zeros((n, 2))
    keep = np.full((n, 2), False)
    for i, var in enumerate(vars):
        if var.lb is not None:
            A[i, 0, index[var]] = -1
            b[i, 0] = -var.lb
            keep[i, 0] = True
        if var.ub is not None:
            A[i, 1, index[var]] = 1
            b[i, 1] = var.ub
            keep[i, 1] = True
    A = A[keep, :]  # pyright: ignore[reportConstantRedefinition]
    b = b[keep]
    cones = [clarabel.NonnegativeConeT(len(b))]  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType, reportAttributeAccessIssue]
    return A, b, cones  # pyright: ignore[reportUnknownVariableType]


def get_eqs(
    n: int, index: Mapping[Var, int], eqs: Sequence[Eq]
) -> tuple[farray, farray, list[Any]]:  # pyright: ignore[reportExplicitAny]
    A = np.zeros((len(eqs), n))
    b = np.zeros(len(eqs))
    cones = [clarabel.ZeroConeT(len(eqs))]  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType, reportAttributeAccessIssue]
    for i, eq in enumerate(eqs):
        for v, c in eq.vars.items():
            A[i, index[v]] = c
        b[i] = eq.const
    return A, b, cones  # pyright: ignore[reportUnknownVariableType]


def get_lts(
    n: int, index: Mapping[Var, int], lts: Sequence[Lt]
) -> tuple[farray, farray, list[Any]]:  # pyright: ignore[reportExplicitAny]
    A = np.zeros((len(lts), n))
    b = np.zeros(len(lts))
    cones = [clarabel.NonnegativeConeT(len(lts))]  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType, reportAttributeAccessIssue]
    for i, lt in enumerate(lts):
        for v, c in lt.vars.items():
            A[i, index[v]] = c
        b[i] = lt.const
    return A, b, cones  # pyright: ignore[reportUnknownVariableType]


def solve(
    eqs: Sequence[Eq],
    lts: Sequence[Lt],
    P_vars: Mapping[Var, float],
    q_vars: Mapping[Var, float],
) -> dict[Var, float]:
    vars = get_vars(eqs, lts) | set(P_vars) | set(q_vars)
    ordered_vars = sorted(vars, key=lambda v: (v.name, v.uuid))
    index = {v: i for (i, v) in enumerate(ordered_vars)}
    # var_from_index = {i: v for (i, v) in enumerate(ordered_vars)}
    n = len(ordered_vars)

    constraints = [
        get_bounds(n, index, vars),
        get_eqs(n, index, eqs),
        get_lts(n, index, lts),
    ]

    A = np.vstack([A for A, _, _ in constraints])
    b = np.concat([b for _, b, _ in constraints])
    cones = [c for _, _, cc in constraints for c in cc]

    P = np.zeros((n, n))
    for v, f in P_vars.items():
        i = index[v]
        P[i, i] = f

    q = np.zeros(n)
    for v, f in q_vars.items():
        q[index[v]] = f

    A = sparse.csc_matrix(A)  # pyright: ignore[reportConstantRedefinition]
    P = sparse.csc_matrix(P)  # pyright: ignore[reportConstantRedefinition]
    # TODO make sure we are not losing stuff?
    P = sparse.triu(P).tocsc()  # pyright: ignore[reportConstantRedefinition]

    settings = clarabel.DefaultSettings()  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType, reportAttributeAccessIssue]
    settings.verbose = False
    settings.time_limit = 5.0

    solver = clarabel.DefaultSolver(P, q, A, b, cones, settings)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType, reportAttributeAccessIssue]
    sol = solver.solve()  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
    assert sol.status == clarabel.SolverStatus.Solved  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]

    # TODO more info about the solution?
    return {v: sol.x[i] for (v, i) in index.items()}  # pyright: ignore[reportUnknownMemberType]


def rounded(v: Mapping[Var, float]) -> dict[Var, float]:
    return {v: round(f, 2) for (v, f) in v.items()}


@app.command()
def eco():
    eqs: list[Eq] = []
    lts: list[Lt] = []

    fish = Var("fish production", 0, 1)
    meat = Var("meat production", 0, 1)
    log = Var("log production", 0, 1)

    a = Var("crafting a", 0, 1)
    b = Var("crafting b", 0, 1)
    c = Var("crafting c", 0, 1)

    A = Var("crafting A", 0, 1)
    B = Var("crafting B", 0, 1)
    C = Var("crafting C", 0, 1)

    eqs.append(Eq({fish: 1, a: -1 / 3, b: -1 / 2, A: -1 / 3 * 2, B: -1 / 2 * 2}, 0))
    eqs.append(Eq({meat: 1, a: -1 / 3, c: -1 / 2, A: -1 / 3 * 2, C: -1 / 2 * 2}, 0))
    eqs.append(
        Eq(
            {
                log: 1,
                a: -2 / 3,
                b: -1 / 2,
                c: -1 / 2,
                A: -2 / 3 * 2,
                B: -1 / 2 * 2,
                C: -1 / 2 * 2,
            },
            0,
        )
    )

    # TODO waste is idle, and we min squares to distribute
    # but we use linear to prefer some crafting over others, does that always work?
    # waste1 = Var("waste1", 0, 1)
    # eqs.append(Eq({fish: 1, meat: 1, log: 1, waste: 1}, 1 / 2 + 1 / 2 + 2 / 3))
    # eqs.append(Eq({a: 1, b: 1, c: 1, waste1: 1}, 1))
    bal1_fish = Var("bal1_fish")
    eqs.append(Eq({fish: 1 / 3, a: -1 / 3, b: -1 / 2, bal1_fish: -1}, 0))
    bal1_meat = Var("bal1_meat")
    eqs.append(Eq({meat: 1 / 3, a: -1 / 3, c: -1 / 2, bal1_meat: -1}, 0))
    bal1_log = Var("bal1_log")
    eqs.append(Eq({log: 1 / 3, a: -2 / 3, b: -1 / 2, c: -1 / 2, bal1_log: -1}, 0))

    # waste2 = Var("waste2", 0, 1)
    # eqs.append(Eq({A: 1, B: 1, C: 1, waste2: 1}, 1))
    bal2_fish = Var("bal2_fish")
    eqs.append(Eq({fish: 1 / 3, a: -1 / 3 * 2, b: -1 / 2 * 2, bal2_fish: -1}, 0))
    bal2_meat = Var("bal2_meat")
    eqs.append(Eq({meat: 1 / 3, a: -1 / 3 * 2, c: -1 / 2 * 2, bal2_meat: -1}, 0))
    bal2_log = Var("bal2_log")
    eqs.append(
        Eq({log: 1 / 3, a: -2 / 3 * 2, b: -1 / 2 * 2, c: -1 / 2 * 2, bal2_log: -1}, 0)
    )

    lts.append(Lt({a: 1, b: 1, c: 1}, 1))
    lts.append(Lt({A: 1, B: 1, C: 1}, 1))

    f = 1
    sol = solve(
        eqs,
        lts,
        # TODO why dont I get equal waste? ah because the sum can still be worse
        # its cheaper to make waste1 small, because waste2 is expensive to fulfill
        # so we need to measure it in the same unit if we want balance
        # but I guess the other question is: is that what the game is approximating?
        # and then, why does the linear part throw it off? same? one is too cheap to use? yes :)
        # what does it mean to measure in the same unit? here its easy, exact same inputs
        # but what if only overlapping? feels like you might first solve another matrix to find those weights?
        # assuming there are two that use the same set, but with different factors, then there isnt a nice balanced solution anyway?
        # is there a way to measure in item space, and per item?
        # we could measure it against the production/count distribution? and since it is a square it doesnt matter if below or above
        # {waste1: 1, waste2: 1 * f},
        {
            bal1_fish: 1,
            bal1_meat: 1,
            bal1_log: 1,
            bal2_fish: 1,
            bal2_meat: 1,
            bal2_log: 1,
        },
        # dict(),
        # TODO this is still difficult, but do we ever have that? two exact same but one is strictly better?
        # and what really would the game do then? the better one would probably get more as it consumes faster?
        # cant we make that part of the item balance somehow? it wouldnt get all, but somehow rate-adjusted
        # we compute the distance to a weighted balance instead?
        {a: -2, b: -1, c: -1, A: -2 * f, B: -1 * f, C: -1 * f},
    )
    sol = rounded(sol)
    rich.print(sol)

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


def solve(eqs: Sequence[Eq], lts: Sequence[Lt], q_min: Set[Var]) -> dict[Var, float]:
    vars = get_vars(eqs, lts)
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
    for v in q_min:
        i = index[v]
        P[i, i] = 1

    q = np.zeros(n)

    A = sparse.csc_matrix(A)  # pyright: ignore[reportConstantRedefinition]
    P = sparse.csc_matrix(P)  # pyright: ignore[reportConstantRedefinition]
    # TODO make sure we are not losing stuff?
    P = sparse.triu(P).tocsc()  # pyright: ignore[reportConstantRedefinition]

    settings = clarabel.DefaultSettings()  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType, reportAttributeAccessIssue]
    settings.verbose = False
    settings.time_limit = 5.0

    solver = clarabel.DefaultSolver(P, q, A, b, cones, settings)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType, reportAttributeAccessIssue]
    sol = solver.solve()  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    # TODO more info about the solution?
    return {v: sol.x[i] for (v, i) in index.items()}  # pyright: ignore[reportUnknownMemberType]


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

    eqs.append(Eq({fish: 1, a: -1 / 3, b: -1 / 2}, 0))
    eqs.append(Eq({meat: 1, a: -1 / 3, c: -1 / 2}, 0))
    eqs.append(Eq({log: 1, a: -2 / 3, b: -1 / 2, c: -1 / 2}, 0))

    # TODO still not totally sure this waste min is what we want
    waste = Var("waste")
    eqs.append(Eq({fish: 1, meat: 1, log: 1, waste: 1}, 1 / 2 + 1 / 2 + 2 / 3))

    lts.append(Lt({a: 1, b: 1, c: 1}, 1))

    sol = solve(eqs, lts, {waste})
    rich.print(sol)

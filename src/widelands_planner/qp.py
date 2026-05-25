from __future__ import annotations

import clarabel  # pyright: ignore[reportMissingTypeStubs]
import numpy as np
from scipy import sparse
from typer import Typer

app = Typer(no_args_is_help=True, rich_markup_mode=None, pretty_exceptions_enable=False)


def main():
    P = sparse.csc_matrix([[3.0, 1.0, -1.0], [1.0, 4.0, 2.0], [-1.0, 2.0, 5.0]])

    P = sparse.triu(P).tocsc()

    q = np.array([1.0, 2.0, -3.0])

    # equality constraint
    Aeq = sparse.csc_matrix([1.0, 1.0, -1])

    beq = np.array([1.0])

    # equality constraint
    Aineq = sparse.csc_matrix([[0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])

    bineq = np.array([2.0, 2.0])

    # SOC constraint
    Asoc = -sparse.identity(3)

    bsoc = np.array([0.0, 0.0, 0.0])

    # Clarabel constraint data
    A = sparse.vstack([Aeq, Aineq, Asoc]).tocsc()

    b = np.concatenate([beq, bineq, bsoc])

    cones = [
        clarabel.ZeroConeT(1),
        clarabel.NonnegativeConeT(2),
        clarabel.SecondOrderConeT(3),
    ]

    settings = clarabel.DefaultSettings()
    settings.verbose = False
    settings.time_limit = 5.0

    solver = clarabel.DefaultSolver(P, q, A, b, cones, settings)

    solution = solver.solve()
    solution.x  # primal solution
    solution.z  # dual solution
    solution.s  # primal slacks

    print(solution)


@app.command()
def eco():
    eq = np.array(
        [
            [1, 0, 0, -1 / 3, -1 / 2, 0, 0],  # fish production == consumption
            [0, 1, 0, -1 / 3, 0, -1 / 2, 0],  # meat production == consumption
            [0, 0, 1, -2 / 3, -1 / 2, -1 / 2, 0],  # log production == consumption
            # TODO still not totally sure this waste min is what we want
            [1, 1, 1, 0, 0, 0, 1],  # waste variable
        ]
    )
    eq_b = np.array([0, 0, 0, 1 / 2 + 1 / 2 + 2 / 3])

    uneq = np.array(
        [
            [1, 0, 0, 0, 0, 0, 0],  # production
            [-1, 0, 0, 0, 0, 0, 0],  # production
            [0, 1, 0, 0, 0, 0, 0],  # production
            [0, -1, 0, 0, 0, 0, 0],  # production
            [0, 0, 1, 0, 0, 0, 0],  # production
            [0, 0, -1, 0, 0, 0, 0],  # production
            [0, 0, 0, 1, 1, 1, 0],  # at most 100% total usage
            [0, 0, 0, -1, -1, -1, 0],  # not less than 0% total usage
            [0, 0, 0, 1, 0, 0, 0],  # at most 100% usage
            [0, 0, 0, -1, 0, 0, 0],  # not less than 0% usage
            [0, 0, 0, 0, 1, 0, 0],  # at most 100% usage
            [0, 0, 0, 0, -1, 0, 0],  # not less than 0% usage
            [0, 0, 0, 0, 0, 1, 0],  # at most 100% usage
            [0, 0, 0, 0, 0, -1, 0],  # not less than 0% usage
        ]
    )
    uneq_b = np.array(
        [
            1,
            0,
            1,
            0,
            1,
            0,
            1,
            0,
            1,
            0,
            1,
            0,
            1,
            0,
        ]
    )

    A = np.vstack([eq, uneq])
    b = np.concat([eq_b, uneq_b])

    P = np.zeros((7, 7))
    P[6, 6] = 1
    P = sparse.csc_matrix(P)
    P = sparse.triu(P).tocsc()

    q = np.zeros(7)

    cones = [
        clarabel.ZeroConeT(4),
        clarabel.NonnegativeConeT(14),
    ]

    settings = clarabel.DefaultSettings()
    settings.verbose = False
    settings.time_limit = 5.0

    # q = sparse.csc_matrix(q)
    A = sparse.csc_matrix(A)
    # b = sparse.csc_matrix(b)

    solver = clarabel.DefaultSolver(P, q, A, b, cones, settings)

    solution = solver.solve()
    solution.x  # primal solution
    solution.z  # dual solution
    solution.s  # primal slacks

    print(solution)
    print(solution.x)

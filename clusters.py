from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import NewType

import polars as pl
import streamlit as st

st.write(datetime.now())

BuildingName = NewType("BuildingName", str)
ClusterName = NewType("ClusterName", str)


@dataclass
class Bvec:
    data: dict[BuildingName, float]

    @staticmethod
    def from_args(**kwargs: float):
        return {BuildingName(name): value for name, value in kwargs.items()}

    def mul(self, vec: Bvec) -> Bvec:
        buildings = self.data.keys() & vec.data.keys()
        return Bvec({b: (self.data[b] * vec.data[b]) for b in buildings})


@dataclass
class Cluster:
    local: set[BuildingName]
    counts: Bvec


clusters: dict[ClusterName, Cluster] = dict()


@dataclass(frozen=True)
class SituatedBuilding:
    building: BuildingName
    cluster: ClusterName | None

# TODO the new way
# - global plain spreadsheet
# - but tetris-like you can turn "full blocks" into isolated things, just like you would have manually, they dont leak anymore
# - and again we can embrace linear fashion most likely

needs = pl.DataFrame(
    [
        {
            "building": "woodcutter",
            "needs": "forester",
            "ratio": 0.5,
        },
        {
            "building": "forester",
            "needs": "office",
            "ratio": 0.25,
        },
    ]
)
st.title("needs")
st.write(needs)

counts = pl.DataFrame(
    [
        {"building": "woodcutter", "count": 2.0},
    ]
)
st.title("counts")
st.write(counts)
# st.write(df.group_by(pl.col("building")).agg(pl.col("count").sum().alias("total")))

st.title("iterating")

iterations = [counts]
for i in range(10):
    last = iterations[-1]
    if last.is_empty():
        break
    st.write(f"iteration {i} has {len(last)} entries")
    iterations.append(
        last.join(needs, on="building", how="inner").select(
            pl.col("needs").alias("building"),
            pl.col("count").mul(pl.col("ratio")).alias("count"),
        )
    )
else:
    st.write("warning: did not converge.")

st.title("result")
totals = pl.concat(iterations, how="vertical")
st.write(
    totals.join(
        counts.select(
            pl.col("building"),
            pl.col("count").alias("have"),
        ),
        on="building",
        how="left",
    )
)

# i1 = counts.join(needs, on="building", how="left").select(
#     pl.col("needs").alias("building"),
#     pl.col("count").mul(pl.col("ratio")).alias("count"),
# )
# st.write(
#     i1
#     # .group_by("needs")
#     # .agg((pl.col("count") * pl.col("ratio")).alias("total"))
# )

# i2 = i1.join(needs, on="building", how="left").select(
#     pl.col("needs").alias("building"),
#     pl.col("count").mul(pl.col("ratio")).alias("count"),
# )
# st.write(i2)

# i3 = i2.join(needs, on="building", how="left").select(
#     pl.col("needs").alias("building"),
#     pl.col("count").mul(pl.col("ratio")).alias("count"),
# )
# st.write(i3)

# st.write(pl.col("weight") / (pl.col("height") ** 2))
#
# result = df.select(
#     pl.col("name"),
#     pl.col("birthdate").dt.year().alias("birth_year"),
#     (pl.col("weight") / (pl.col("height") ** 2)).alias("bmi"),
# )
# st.write(result)

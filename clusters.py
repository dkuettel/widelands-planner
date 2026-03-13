from __future__ import annotations

from datetime import datetime

import polars as pl
import streamlit as st

st.write(datetime.now())

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

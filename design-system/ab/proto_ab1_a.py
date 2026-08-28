"""
A/B #1 candidate A: `tbl-lens-ranked` with `st.column_config.ProgressColumn`
for the score column (min 0, max 100, formatted as a percent). Renders
University of Gdansk (I40413290) L1 top-30 from the live engine.
VIZ_SPEC.md §3 A/B #1.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from _common import SEED, load_rankings
from lib import engine as E

st.set_page_config(layout="wide")
DEPTH = 30

ctx, r = load_rankings()
rows = E.build_rows(r["L1"], ctx, DEPTH, r)

df = pd.DataFrame([{
    "rank": row["rank"],
    "institution": row["display_name"],
    "country": str(row["country_code"]),
    "type": str(row["type"]),
    "size": row["total_full_2020_2024"],
    "score_pct": round(row["lens_score"] * 100, 1),
} for row in rows])

st.title("A/B #1 -- candidate A: ProgressColumn score")
st.caption(f"University of Gdansk ({SEED}), L1, top-{len(df)} of the full ranking")

st.dataframe(
    df,
    hide_index=True,
    use_container_width=True,
    column_config={
        "rank": st.column_config.NumberColumn("Rank"),
        "institution": st.column_config.TextColumn("Institution"),
        "size": st.column_config.NumberColumn("Size", format="%d"),
        "score_pct": st.column_config.ProgressColumn(
            "Score", min_value=0, max_value=100, format="%.0f%%"
        ),
    },
)

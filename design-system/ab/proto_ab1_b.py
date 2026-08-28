"""
A/B #1 candidate B: `tbl-lens-ranked` WITHOUT a score column, plus a Plotly
ranked-dot chart beside it -- one dot per row at its score, row order = rank,
zero-baseline x-axis 0-1, dots in `palette.COMPARISON` (the seed is
self-excluded so FOCAL never appears here, per the brief). Renders University
of Gdansk (I40413290) L1 top-30 from the live engine. VIZ_SPEC.md §3 A/B #1.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from _common import SEED, load_rankings
from lib import engine as E
from lib import palette

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
} for row in rows])
scores = [row["lens_score"] for row in rows]
ranks = [row["rank"] for row in rows]

st.title("A/B #1 -- candidate B: Plotly ranked-dot chart")
st.caption(f"University of Gdansk ({SEED}), L1, top-{len(df)} of the full ranking")

col_table, col_chart = st.columns([2, 1])
with col_table:
    st.dataframe(
        df, hide_index=True, use_container_width=True,
        column_config={
            "rank": st.column_config.NumberColumn("Rank"),
            "institution": st.column_config.TextColumn("Institution"),
            "size": st.column_config.NumberColumn("Size", format="%d"),
        },
    )
with col_chart:
    y_positions = list(range(len(scores), 0, -1))  # rank 1 at the top
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=scores, y=y_positions, mode="markers",
        marker=dict(color=palette.COMPARISON, size=10),
        hovertext=[f"rank {rk}: {sc:.3f}" for rk, sc in zip(ranks, scores)],
    ))
    fig.update_xaxes(range=[0, 1], zeroline=True, zerolinecolor="#333333", title="Score")
    fig.update_yaxes(tickmode="array", tickvals=y_positions,
                      ticktext=[str(rk) for rk in ranks], title="Rank")
    table_row_height = 35
    table_header_height = 38
    fig.update_layout(
        height=table_header_height + DEPTH * table_row_height,
        margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
    )
    st.plotly_chart(fig, use_container_width=True)

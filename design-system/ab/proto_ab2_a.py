"""
A/B #2 candidate A: k-count table with hit-lens chips (VIZ_SPEC.md §2.3
proposed default) -- candidate, k-of-n column, a text column listing hit
lenses with each one's own rank, country/type/size. Renders the concordance
overview for University of Gdansk (I40413290) at the 8 default lenses, N=30.
VIZ_SPEC.md §3 A/B #2.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from _common import SEED, load_rankings
from lib import engine as E

st.set_page_config(layout="wide")
N = 30
LENSES = E.DEFAULT_LENSES

ctx, r = load_rankings()
conc = E.concordance(ctx, r, LENSES, N)

df = pd.DataFrame([{
    "institution": row["display_name"],
    "country": str(row["country_code"]),
    "type": str(row["type"]),
    "k_of_n": f"{row['k']} of {row['n']}",
    "hit_lenses": ", ".join(
        f"{ln} #{r[ln]['rmap'].get(row['institution_id'], '?')}" for ln in row["hit_lenses"]
    ),
    "size": row["total_full_2020_2024"],
} for row in conc])

st.title("A/B #2 -- candidate A: k-count table with hit-lens chips")
st.caption(f"University of Gdansk ({SEED}), {len(LENSES)} default lenses, N={N}, "
           f"{len(df)} candidates found by 2 or more lenses")

st.dataframe(
    df, hide_index=True, use_container_width=True,
    column_config={
        "institution": st.column_config.TextColumn("Institution"),
        "k_of_n": st.column_config.TextColumn("k of n"),
        "hit_lenses": st.column_config.TextColumn("Hit lenses (rank)", width="large"),
        "size": st.column_config.NumberColumn("Size", format="%d"),
    },
)

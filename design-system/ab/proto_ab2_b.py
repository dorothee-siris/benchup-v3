"""
A/B #2 candidate B: full rank matrix, candidates x the 8 default lenses, cell
= the candidate's rank within that lens's tie-inclusive top-N, or "--" meaning
"not in this lens's top-N" (Studio RULES.md §9.12 -- never blank, never 0:
a blank/0 cell would read as "not computed" instead of "not found here").
Renders the same concordance candidate pool for University of Gdansk
(I40413290) at the 8 default lenses, N=30. VIZ_SPEC.md §3 A/B #2.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from _common import SEED, load_rankings
from lib import engine as E

st.set_page_config(layout="wide")
N = 30
LENSES = E.DEFAULT_LENSES
NOT_IN_TOPN = "--"  # distinct from palette.NA_MARK ("n/a" = lens undefined for the seed)

ctx, r = load_rankings()

defined = [ln for ln in LENSES if ln in r and not r[ln]["undefined"]]
top_sets = {ln: set(E.cut_with_ties(r[ln]["sorted_ids"], r[ln]["sorted_scores"], N)[0])
            for ln in defined}

conc = E.concordance(ctx, r, LENSES, N)  # reuse its (k desc, mean-rank) row order
order_ids = [row["institution_id"] for row in conc]

matrix_rows = []
for cid in order_ids:
    idx_row = ctx["index_by_id"].loc[cid]
    rec = {"institution": idx_row["display_name"], "country": str(idx_row["country_code"])}
    for ln in LENSES:
        if ln in defined and cid in top_sets[ln]:
            rec[ln] = r[ln]["rmap"][cid]
        else:
            rec[ln] = None  # rendered as NOT_IN_TOPN below, kept as int col otherwise
    matrix_rows.append(rec)

df = pd.DataFrame(matrix_rows)
for ln in LENSES:
    # None upcasts a numeric column to float64/NaN (pandas), not object/None --
    # check pd.isna, not `is None` (WT-style gotcha, same family as the
    # category-dtype .map() trap in the Streamlit gotcha list).
    df[ln] = df[ln].apply(lambda v: NOT_IN_TOPN if pd.isna(v) else str(int(v)))

st.title("A/B #2 -- candidate B: full rank matrix")
st.caption(f"University of Gdansk ({SEED}), {len(LENSES)} default lenses, N={N}, "
           f"{len(df)} candidates found by 2 or more lenses; '{NOT_IN_TOPN}' = not in that "
           f"lens's top-{N}")

st.dataframe(df, hide_index=True, use_container_width=True)

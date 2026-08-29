"""
R1 stream R-D2 -- render the SHIPPED `lib/charts.py` builders (not the A/B
prototypes) in a real browser, so the verdict's implementation is looked at and
not merely unit-tested. Throwaway, `design-system/ab/**` only.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

AB = Path(__file__).resolve().parent
APP = AB.parent.parent
for p in (str(APP), str(AB)):
    if p not in sys.path:
        sys.path.insert(0, p)

from _common_r1 import GDANSK, fields_table, resolve_strasbourg, top_subfields  # noqa: E402
from lib import charts as C  # noqa: E402
from lib import palette as P  # noqa: E402

st.set_page_config(page_title="R1 shipped builders", layout="wide")
DATA = APP / "data"
STRAS = resolve_strasbourg()

dim = pd.read_parquet(DATA / "topics_dim.parquet")
st.markdown("**Fields -- fig_share_si(family=oa, sort=volume, gutter=True)**")
st.plotly_chart(C.fig_share_si(fields_table(STRAS)), width="stretch")

st.markdown("**Top subfields -- fig_share_si (Gdansk, n/a SI below the floor)**")
st.plotly_chart(C.fig_share_si(top_subfields(GDANSK, 20)), width="stretch")

t = pd.read_parquet(DATA / "topics_all.parquet",
                    columns=["institution_id", "topic_id", "share_frac", "vol_frac", "vol_full"])
t = t[t["institution_id"] == STRAS].merge(dim, on="topic_id", how="left")
t["share"] = t["share_frac"]
top = t.sort_values("share", ascending=False).head(20).reset_index(drop=True)
st.markdown("**Top topics -- fig_topics (catch-all rows glyphed + muted)**")
st.plotly_chart(C.fig_topics(top), width="stretch")

st.markdown("**Frontier -- fig_frontier (top-quartile outlined, quadrants at the origin)**")
st.plotly_chart(C.fig_frontier(t.sort_values("share", ascending=False).head(200)), width="stretch")

sdg = pd.read_parquet(DATA / "sdg.parquet")
sdg = sdg[sdg["institution_id"] == STRAS].copy()
sdg["sdg_number"] = sdg["sdg_idx"].astype(int) + 1
sdg["sdg_label"] = ["SDG" + C.THIN_SPACE + str(n) for n in sdg["sdg_number"]]
st.markdown("**SDG -- fig_sdg (UN colours, fixed goal order, ESI dots)**")
st.plotly_chart(C.fig_sdg(sdg), width="stretch")

erc = pd.read_parquet(DATA / "erc.parquet")
erc = erc[erc["institution_id"] == STRAS].copy().reset_index(drop=True)
order = [("PE", i) for i in range(11)] + [("LS", i) for i in range(9)] + [("SH", i) for i in range(8)]
erc["erc_domain"] = [order[i][0] for i in erc["panel_idx"]]
erc["panel_label"] = [f"{d}{n + 1}" for d, n in (order[i] for i in erc["panel_idx"])]
st.markdown("**ERC -- fig_erc (three ERC hues, PE/LS/SH blocks)**")
st.plotly_chart(C.fig_erc(erc), width="stretch")

labels = {1: "Life Sciences", 2: "Social Sciences", 3: "Physical Sciences", 4: "Health Sciences"}
tot = {d: [float(x) for x in (900, 950, 1000, 1050, 1100, 400)] for d in P.OA_DOMAIN_ORDER}
years = [str(y) for y in range(2020, 2026)]
st.markdown("**Breakdown pair -- fig_breakdown_global | fig_breakdown_yearly + chip legend**")
st.markdown(C.chip_legend_html([(labels[d], P.OA_DOMAIN_COLORS[d]) for d in P.OA_DOMAIN_ORDER]),
            unsafe_allow_html=True)
a, b = st.columns(2)
with a:
    st.plotly_chart(C.fig_breakdown_global([labels[d] for d in P.OA_DOMAIN_ORDER],
                                           [sum(tot[d]) for d in P.OA_DOMAIN_ORDER],
                                           [P.OA_DOMAIN_COLORS[d] for d in P.OA_DOMAIN_ORDER]),
                    width="stretch")
with b:
    st.plotly_chart(C.fig_breakdown_yearly(years, list(P.OA_DOMAIN_ORDER), labels,
                                           {d: P.OA_DOMAIN_COLORS[d] for d in P.OA_DOMAIN_ORDER},
                                           tot), width="stretch")

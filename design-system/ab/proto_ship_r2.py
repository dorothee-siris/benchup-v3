"""
R2 stream R2-D -- render the SHIPPED `lib/charts.py` builders AFTER the
L34/L35/L36 changes: `wrap_label` (full names, two-line wrap, no ellipsis),
`si_status` solid/hollow/none marks, the SI unit grid, numbered SDG labels.
Throwaway, `design-system/ab/**` only, never imported by anything shipped.

`si_status` is built INLINE here from the real `vol_frac`/`mass` column with
the 10/30 rule (harmonised across subfields/ERC), exactly as
`tests/test_charts.py` does and exactly as stream R2-P's shipped column will --
this script does not import `profile_data`, so it renders standalone even if
that module lands after this one.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

AB = Path(__file__).resolve().parent
APP = AB.parent.parent
for p in (str(APP), str(AB)):
    if p not in sys.path:
        sys.path.insert(0, p)

from _common_r1 import GDANSK, resolve_strasbourg, subfields_table  # noqa: E402
from lib import charts as C  # noqa: E402

st.set_page_config(page_title="R2 shipped builders", layout="wide")
DATA = APP / "data"
STRAS = resolve_strasbourg()


def _si_status(mass: pd.Series) -> pd.Series:
    return pd.Series(np.select([mass >= 30, mass >= 10], ["solid", "thin"], default="none"),
                      index=mass.index)


st.markdown("## R2 shipped builders -- si_status marks, unit grid, wrap_label, numbered SDG labels")

# ---------------------------------------------------------------------------
# 1a. Top-30 subfields (Gdansk, the REAL shipped cut, real long subfield
#     names). On THIS seed the top 30 by volume all clear the 30-mass solid
#     floor (measured below) -- a true, worth-showing fact about Gdansk, not a
#     script bug -- so it renders alone first, then 1b demonstrates the hollow
#     mechanism on a slice built to straddle the floor.
# ---------------------------------------------------------------------------
top30 = subfields_table(GDANSK).sort_values("vol_frac", ascending=False).head(30).reset_index(drop=True)
top30["si_status"] = _si_status(top30["vol_frac"])
counts_top = top30["si_status"].value_counts().to_dict()
st.markdown(f"**Top 30 subfields, the real shipped cut (si_status counts {counts_top} -- "
            f"all solid on THIS seed) -- fig_share_si(family=oa, sort=volume)**")
st.plotly_chart(C.fig_share_si(top30, family="oa", sort="volume"), width="stretch")

# ---------------------------------------------------------------------------
# 1b. A thin/solid MIX, deliberately: the 30 subfields straddling the 10/30
#     mass boundary (ranks 41-70 by volume) rather than the top 30, so the
#     render proof actually exercises the hollow-mark mechanism §2.16 added --
#     the real G6 floor is also 30, so mass in [10, 30) is NaN `si` in shipped
#     data today (stream P's job is widening that computation); a deterministic
#     substitute proves the CHART's response to the status column, not the
#     numeric value's provenance.
# ---------------------------------------------------------------------------
all_sub = subfields_table(GDANSK).sort_values("vol_frac", ascending=False).reset_index(drop=True)
mix = all_sub.iloc[40:70].reset_index(drop=True)
mix["si_status"] = _si_status(mix["vol_frac"])
thin_undefined = mix["si_status"].eq("thin") & mix["si"].isna()
mix.loc[thin_undefined, "si"] = 1.4
counts_mix = mix["si_status"].value_counts().to_dict()
st.markdown(f"**Subfields ranked 41-70 by volume, chosen to straddle the floor "
            f"(si_status counts {counts_mix}) -- fig_share_si(family=oa, sort=volume)**")
st.plotly_chart(C.fig_share_si(mix, family="oa", sort="volume"), width="stretch")

# ---------------------------------------------------------------------------
# 2. ERC panels (Strasbourg) -- LONG fabricated labels (erc_panels.csv, the
#    real long-label source, is stream R2-P's file) + solid/thin/none mix +
#    one ZERO-VOLUME synthetic row with si_status="solid" and a defined si --
#    the exact ERC display bug the user saw, proving the override still wins.
# ---------------------------------------------------------------------------
erc = pd.read_parquet(DATA / "erc.parquet")
erc = erc[erc["institution_id"] == STRAS].copy().reset_index(drop=True)
order = [("PE", i) for i in range(11)] + [("LS", i) for i in range(9)] + [("SH", i) for i in range(8)]
erc["erc_domain"] = [order[i][0] for i in erc["panel_idx"]]
# Two rows get a fabricated LONG description appended to their REAL panel
# code (erc_panels.csv, the real long-label source, is stream R2-P's file) --
# built from each row's own (d, n), never a hardcoded guess, so the label
# always names the panel it is actually attached to.
LONG_TEXT = {
    0: "Mathematical foundations, methods and their interconnection with other fields",
    1: "Universe sciences, astrophysics and astronomy across every observable scale",
}
codes = [f"{d}{n + 1}" for d, n in (order[j] for j in erc["panel_idx"])]
erc["panel_label"] = [f"{c} {LONG_TEXT[i]}" if i in LONG_TEXT else c
                      for i, c in enumerate(codes)]
erc["si_status"] = _si_status(erc["mass"])
thin_e = erc["si_status"].eq("thin") & erc["si"].isna()
erc.loc[thin_e, "si"] = 1.3

zero_row = erc.iloc[[0]].copy()
zero_row["mass"] = 0.0
zero_row["si"] = 2.5
zero_row["si_status"] = "solid"
zero_row["panel_label"] = "ZZ-synthetic zero-volume panel (bug check)"
erc_aug = pd.concat([erc, zero_row], ignore_index=True)

counts_e = erc_aug["si_status"].value_counts().to_dict()
st.markdown(f"**ERC panels (n={len(erc_aug)}, si_status counts {counts_e}, "
            f"long labels + one zero-volume synthetic row) -- fig_erc**")
st.plotly_chart(C.fig_erc(erc_aug), width="stretch")

# ---------------------------------------------------------------------------
# 3. SDG panel -- numbered labels (L36) instead of the plain sdg_label.
# ---------------------------------------------------------------------------
sdg = pd.read_parquet(DATA / "sdg.parquet")
sdg = sdg[sdg["institution_id"] == STRAS].copy()
sdg["sdg_number"] = sdg["sdg_idx"].astype(int) + 1
SDG_SHORT = {
    1: "No poverty", 2: "Zero hunger", 3: "Good health and well-being",
    4: "Quality education", 5: "Gender equality", 6: "Clean water and sanitation",
    7: "Affordable and clean energy", 8: "Decent work and economic growth",
    9: "Industry, innovation and infrastructure", 10: "Reduced inequalities",
    11: "Sustainable cities and communities", 12: "Responsible consumption and production",
    13: "Climate action", 14: "Life below water", 15: "Life on land",
    16: "Peace, justice and strong institutions",
}
sdg["sdg_label_numbered"] = [f"SDG {n} . {SDG_SHORT[n]}" for n in sdg["sdg_number"]]
st.markdown("**SDG panel -- fig_sdg with sdg_label_numbered (L36)**")
st.plotly_chart(C.fig_sdg(sdg), width="stretch")

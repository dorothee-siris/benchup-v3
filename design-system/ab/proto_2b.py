"""
Phase 2B (stream V) A/B prototypes + the shipped-builder render. THROWAWAY --
`design-system/ab/**` only, never imported by the app, never a page.

One Streamlit script, five variants selected by `?variant=`:
  ab5_a  Fields mirror, DOT ROWS          (the shipped `charts_compare.fig_mirror_dots`)
  ab5_b  Fields mirror, SMALL MULTIPLES   (the rival, built here and nowhere else)
  ab6_a  Frontier, OVERLAY scatter        (the shipped `fig_frontier_overlay`)
  ab6_b  Frontier, SMALL MULTIPLES        (the rival, built here and nowhere else)
  2b_shipped_builders  every shipped builder on the six real institutions

The rivals are deliberately given every advantage the shipped form has: the same
real data, the same palette, the same institution slots, the same 1280 px page.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

AB_DIR = Path(__file__).resolve().parent
APP_ROOT = AB_DIR.parent.parent
for pth in (str(APP_ROOT), str(AB_DIR)):
    if pth not in sys.path:
        sys.path.insert(0, pth)

import _common_2b as F                      # noqa: E402
from lib import charts as C                 # noqa: E402
from lib import charts_compare as X         # noqa: E402
from lib import palette as P                # noqa: E402

st.set_page_config(layout="wide", page_title="benchup ab 2b")
variant = st.query_params.get("variant", "ab5_a")
SLOTS, NAMES = F.slots_and_names()


def legend():
    st.markdown(X.institution_legend_html(NAMES, SLOTS), unsafe_allow_html=True)


# --------------------------------------------------------------------------
# The A/B #5 rival: one small panel per institution, horizontal share bars
# --------------------------------------------------------------------------
def fields_small_multiples(df, slots, names, n_cols=3):
    rows = (df.groupby(["field_id", "field_name"], as_index=False)["share"].sum()
              .sort_values("share", ascending=False))
    order = rows["field_id"].tolist()
    labels = dict(zip(rows["field_id"], rows["field_name"]))
    ids = sorted(slots, key=lambda i: slots[i])
    n_rows = int(np.ceil(len(ids) / n_cols))
    xmax = float(df["share"].max()) * 1.02
    fig = make_subplots(rows=n_rows, cols=n_cols, shared_xaxes=True,
                        subplot_titles=[C.wrap_label(str(names.get(i, i)), width=28) for i in ids],
                        horizontal_spacing=0.02, vertical_spacing=0.06)
    for k, iid in enumerate(ids):
        r, c = k // n_cols + 1, k % n_cols + 1
        mine = df[df["institution_id"] == iid].set_index("field_id").reindex(order)
        cats = [C.wrap_label(str(labels[f]), width=30) for f in order]
        fig.add_trace(go.Bar(
            x=mine["share"].fillna(0.0).to_numpy(dtype=float), y=cats, orientation="h",
            marker_color=P.institution_color(slots[iid]),
            marker_line_color=P.SURFACE, marker_line_width=1,
            hovertemplate="%{y}<extra></extra>", showlegend=False), row=r, col=c)
        fig.update_yaxes(autorange="reversed", showgrid=False,
                         showticklabels=(c == 1), automargin=True, row=r, col=c)
        fig.update_xaxes(range=[0, xmax], tickformat=C._AXIS_PCT_FMT,
                         gridcolor=P.GRID, linecolor=P.BORDER, row=r, col=c)
    fig.update_layout(height=n_rows * 420 + 60, bargap=0.25, showlegend=False,
                      paper_bgcolor=P.SURFACE, plot_bgcolor=P.SURFACE,
                      margin=dict(t=40, l=8, r=16, b=60),
                      font=dict(color=P.INK, size=C.FONT_PX))
    fig.update_annotations(font=dict(size=C.GUTTER_FONT_PX, color=P.INK_SECONDARY))
    return fig


# --------------------------------------------------------------------------
# The A/B #6 rival: one frontier panel per institution
# --------------------------------------------------------------------------
def frontier_small_multiples(df, slots, names, n_cols=3):
    ids = sorted(slots, key=lambda i: slots[i])
    n_rows = int(np.ceil(len(ids) / n_cols))
    fig = make_subplots(rows=n_rows, cols=n_cols, shared_xaxes=True, shared_yaxes=True,
                        subplot_titles=[C.wrap_label(str(names.get(i, i)), width=28) for i in ids],
                        horizontal_spacing=0.04, vertical_spacing=0.09)
    mass = df["vol_full"].astype(float)
    mmax = float(mass.max()) or 1.0
    for k, iid in enumerate(ids):
        r, c = k // n_cols + 1, k % n_cols + 1
        mine = df[df["institution_id"] == iid]
        sizes = C.BUBBLE_MIN_PX + (C.BUBBLE_MAX_PX - C.BUBBLE_MIN_PX) * np.sqrt(
            mine["vol_full"].astype(float) / mmax)
        fig.add_trace(go.Scatter(
            x=mine["expansion_latest"], y=mine["acceleration_latest"], mode="markers",
            marker=dict(color=P.institution_color(slots[iid]), size=sizes,
                        opacity=X.OVERLAY_OPACITY,
                        line=dict(color=P.SURFACE, width=1)),
            hovertemplate="%{x}<extra></extra>", showlegend=False), row=r, col=c)
        fig.add_vline(x=0, line=dict(color=P.GRID, width=1), row=r, col=c)
        fig.add_hline(y=0, line=dict(color=P.GRID, width=1), row=r, col=c)
        fig.update_xaxes(gridcolor=P.GRID, linecolor=P.BORDER, row=r, col=c)
        fig.update_yaxes(gridcolor=P.GRID, linecolor=P.BORDER, row=r, col=c)
    fig.update_layout(height=n_rows * 300 + 60, showlegend=False,
                      paper_bgcolor=P.SURFACE, plot_bgcolor=P.SURFACE,
                      margin=dict(t=40, l=8, r=16, b=60),
                      font=dict(color=P.INK, size=C.FONT_PX))
    fig.update_annotations(font=dict(size=C.GUTTER_FONT_PX, color=P.INK_SECONDARY))
    return fig


# --------------------------------------------------------------------------
def top_by_summed_share(df, key, n):
    keep = df.groupby(key)["share"].sum().sort_values(ascending=False).head(n).index
    return df[df[key].isin(keep)]


if variant == "ab5_a":
    st.subheader("A/B five A - fields mirror, dot rows")
    legend()
    st.plotly_chart(X.fig_mirror_dots(F.fields_long(), family="oa", slots=SLOTS,
                                      names=NAMES, sort="volume"),
                    use_container_width=True, config={"displayModeBar": False})

elif variant == "ab5_b":
    st.subheader("A/B five B - fields mirror, small multiples")
    legend()
    st.plotly_chart(fields_small_multiples(F.fields_long(), SLOTS, NAMES),
                    use_container_width=True, config={"displayModeBar": False})

elif variant.startswith("ab6_a"):
    # ab6_a = all six; ab6_a2 / ab6_a3 = the same overlay at k = 2 / k = 3, to
    # find where the form stops carrying institution identity
    k = {"ab6_a2": 2, "ab6_a3": 3}.get(variant, 6)
    ids = sorted(SLOTS, key=lambda i: SLOTS[i])[:k]
    fp = F.frontier_points()
    if variant == "ab6_aq":   # the 2B-3 top-quartile mode: far fewer points
        fp = fp[fp["top25pct_frontier"].fillna(False)]
    st.subheader("A/B six A - frontier overlay")
    legend()
    st.plotly_chart(X.fig_frontier_overlay(fp[fp["institution_id"].isin(ids)],
                                           SLOTS, names=NAMES),
                    use_container_width=True, config={"displayModeBar": False})

elif variant == "ab6_b":
    st.subheader("A/B six B - frontier small multiples")
    legend()
    st.plotly_chart(frontier_small_multiples(F.frontier_points(), SLOTS, NAMES),
                    use_container_width=True, config={"displayModeBar": False})

else:
    st.subheader("Phase two B - every shipped builder, six real institutions")
    legend()
    cfg = {"displayModeBar": False}

    st.caption("fields mirror - dot rows, share and specialisation")
    st.plotly_chart(X.fig_mirror_dots(F.fields_long(), family="oa", slots=SLOTS, names=NAMES),
                    use_container_width=True, config=cfg)

    st.caption("subfields mirror - top by summed share across the set")
    st.plotly_chart(X.fig_mirror_dots(top_by_summed_share(F.subfields_long(top_n=12),
                                                          "subfield_id", 12),
                                      family="oa", slots=SLOTS, names=NAMES),
                    use_container_width=True, config=cfg)

    st.caption("ERC panel mirror - taxonomy order")
    st.plotly_chart(X.fig_mirror_dots(top_by_summed_share(F.erc_long(), "panel_idx", 12),
                                      family="erc", slots=SLOTS, names=NAMES, sort="taxonomy"),
                    use_container_width=True, config=cfg)

    st.caption("SDG mirror - numbered labels, goal order")
    st.plotly_chart(X.fig_mirror_dots(F.sdg_long(), family="sdg", slots=SLOTS,
                                      names=NAMES, sort="taxonomy"),
                    use_container_width=True, config=cfg)

    st.caption("frontier quadrant mix - five segments, not-scored included")
    st.plotly_chart(X.fig_quadrant_mix(F.frontier_mix(), SLOTS, names=NAMES),
                    use_container_width=True, config=cfg)

    st.caption("frontier - small multiples, the A/B six winner")
    st.plotly_chart(X.fig_frontier_small_multiples(F.frontier_points(), SLOTS, names=NAMES),
                    use_container_width=True, config=cfg)

    st.caption("frontier overlay - the secondary mode, one plane")
    st.plotly_chart(X.fig_frontier_overlay(F.frontier_points(), SLOTS, names=NAMES),
                    use_container_width=True, config=cfg)

    st.caption("impact - index level, point estimate and interval")
    st.plotly_chart(X.fig_impact_intervals(F.impact_index(), SLOTS, names=NAMES),
                    use_container_width=True, config=cfg)

    st.caption("impact - per subfield, the union, missing cells left blank")
    isf = F.impact_subfields()
    keep = (isf.groupby("subfield_id")["institution_id"].nunique()
              .sort_values(ascending=False).head(8).index)
    st.plotly_chart(X.fig_impact_subfields(isf[isf["subfield_id"].isin(keep)],
                                           SLOTS, names=NAMES),
                    use_container_width=True, config=cfg)

    st.caption("trends - small multiples, final year dotted and hollow")
    subs = F.top_shared_subfields()
    tr = F.trends_subfields(subfield_ids=subs)
    tot = tr.groupby(["institution_id", "year"])["vol_full"].transform("sum")
    tr = tr.assign(share_year=tr["vol_full"] / tot.replace(0, np.nan))
    frames = {i: tr[tr["institution_id"] == i] for i in F.IDS}
    st.plotly_chart(X.fig_trends_small_multiples(frames, SLOTS, subs, names=NAMES,
                                                 value_col="share_year",
                                                 bonus_year=F.BONUS_YEAR),
                    use_container_width=True, config=cfg)

    st.caption("coverage strip - the one stacked bar, six exhaustive states")
    st.plotly_chart(X.fig_coverage_strip(F.coverage(), SLOTS, names=NAMES),
                    use_container_width=True, config=cfg)

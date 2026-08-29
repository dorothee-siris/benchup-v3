"""
R1 (stream R-D2) A/B prototypes -- ONE throwaway Streamlit app, four variants
selected by the `--variant` argument run_ab_r1.py passes through. Throwaway:
`design-system/ab/**` only, never imported by anything shipped. The winners are
re-implemented properly in `lib/charts.py`; this file exists to be photographed.

Variants
  ab3_a  share + SI as TWO ALIGNED PANELS of one figure (shared y), SI as a
         lollipop from the SI = 1 reference, dashed reference line, no mark
         where SI is n/a.
  ab3_b  share + SI on ONE ROW, single axis: the bar is the share, a tick on
         the same row marks the EXPECTED share (share / SI), so SI is read as
         the ratio of two lengths on one scale. (The literal "secondary marker
         on the same row" reading of the brief; a second x-scale would be a
         dual axis, which the dataviz non-negotiables forbid outright, so this
         is that idea's strongest legal form.)
  ab4_a  volume in a LEFT TEXT GUTTER (BenchUp V2/Streamlit `left_pad_px`).
  ab4_b  volume as RIGHT-OF-BAR annotations (BenchUp V1/my_app; Lorraine
         plot_global_breakdown_h `xanchor="left", xshift=8`).

Both A/Bs run on real deployed data: Universite de Strasbourg fields (n = 25)
and University of Gdansk top-20 subfields (which carries n/a SI values below
the G6 floor, the case ab3 has to render honestly).
"""
from __future__ import annotations

import sys

import numpy as np
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from _common_r1 import GDANSK, fields_table, resolve_strasbourg, top_subfields

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent.parent))
from lib import palette as P  # noqa: E402

VARIANT = st.query_params.get("variant", "ab3_a")

st.set_page_config(page_title="R1 A/B", layout="wide")

STRAS = resolve_strasbourg()
GUTTER_FRACTION = 0.16   # of the x range, the left text gutter (ab4_a)
RIGHT_HEADROOM = 1.18    # x-range multiplier the right annotations need (ab4_b)


def _h(n: int) -> int:
    return max(300, 22 * n + 60)


def _colors(df):
    return [P.domain_color(d) for d in df["domain_id"]]


def _labels(df, col):
    return list(df[col].astype(str))


# ---------------------------------------------------------------------------
# A/B #3 -- variant A: two aligned panels, shared y
# ---------------------------------------------------------------------------
def fig_ab3_a(df, label_col):
    df = df.sort_values("share", ascending=False).reset_index(drop=True)
    names, cols = _labels(df, label_col), _colors(df)
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True,
                        column_widths=[0.66, 0.34], horizontal_spacing=0.03,
                        subplot_titles=("Share of output", "Specialisation index"))
    fig.add_trace(go.Bar(
        x=df["share"], y=names, orientation="h", marker_color=cols,
        marker_line_color=P.SURFACE, marker_line_width=1,
        hovertemplate="%{y}<br>share %{x:.1%}<extra></extra>", showlegend=False,
    ), row=1, col=1)
    si = df["si"].to_numpy(dtype=float)
    ok = ~np.isnan(si)
    for i, (nm, c) in enumerate(zip(names, cols)):
        if not ok[i]:
            continue
        fig.add_trace(go.Scatter(
            x=[1.0, si[i]], y=[nm, nm], mode="lines",
            line=dict(color=c, width=2), hoverinfo="skip", showlegend=False,
        ), row=1, col=2)
    fig.add_trace(go.Scatter(
        x=si[ok], y=[n for n, k in zip(names, ok) if k], mode="markers",
        marker=dict(color=[c for c, k in zip(cols, ok) if k], size=10,
                    line=dict(color=P.SURFACE, width=2)),
        hovertemplate="%{y}<br>SI %{x:.2f}<extra></extra>", showlegend=False,
    ), row=1, col=2)
    fig.add_vline(x=1.0, line=dict(color=P.INK_SECONDARY, width=1, dash="dash"), row=1, col=2)
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(gridcolor=P.GRID, zerolinecolor=P.GRID)
    fig.update_xaxes(tickformat=".0%", row=1, col=1)
    fig.update_layout(height=_h(len(df)), bargap=0.3,
                      paper_bgcolor=P.SURFACE, plot_bgcolor=P.SURFACE,
                      margin=dict(t=44, l=8, r=16, b=40),
                      font=dict(color=P.INK, size=12))
    return fig


# ---------------------------------------------------------------------------
# A/B #3 -- variant B: one row, one axis, expected-share tick
# ---------------------------------------------------------------------------
def fig_ab3_b(df, label_col):
    df = df.sort_values("share", ascending=False).reset_index(drop=True)
    names, cols = _labels(df, label_col), _colors(df)
    si = df["si"].to_numpy(dtype=float)
    share = df["share"].to_numpy(dtype=float)
    expected = np.where(np.isnan(si) | (si <= 0), np.nan, share / si)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=share, y=names, orientation="h", marker_color=cols,
        marker_line_color=P.SURFACE, marker_line_width=1,
        customdata=np.stack([np.where(np.isnan(si), -1.0, si)], axis=-1),
        hovertemplate="%{y}<br>share %{x:.1%}<br>SI %{customdata[0]:.2f}<extra></extra>",
        showlegend=False,
    ))
    for i, nm in enumerate(names):
        if np.isnan(expected[i]):
            continue
        fig.add_shape(type="line", x0=expected[i], x1=expected[i],
                      y0=i - 0.38, y1=i + 0.38, xref="x", yref="y",
                      line=dict(color=P.INK, width=2))
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(gridcolor=P.GRID, zerolinecolor=P.GRID, tickformat=".0%",
                     title="Share of output; the tick marks the expected share")
    fig.update_layout(height=_h(len(df)), bargap=0.3,
                      paper_bgcolor=P.SURFACE, plot_bgcolor=P.SURFACE,
                      margin=dict(t=44, l=8, r=16, b=52),
                      font=dict(color=P.INK, size=12))
    return fig


# ---------------------------------------------------------------------------
# A/B #4 -- volume placement, on the same plain share-bar chart
# ---------------------------------------------------------------------------
def fig_ab4(df, label_col, gutter: bool):
    df = df.sort_values("share", ascending=False).reset_index(drop=True)
    names, cols = _labels(df, label_col), _colors(df)
    share = df["share"].to_numpy(dtype=float)
    vol = df["vol_full"].to_numpy()
    xmax = float(share.max()) if len(share) else 1.0
    fig = go.Figure(go.Bar(
        x=share, y=names, orientation="h", marker_color=cols,
        marker_line_color=P.SURFACE, marker_line_width=1,
        hovertemplate="%{y}<br>share %{x:.1%}<extra></extra>", showlegend=False,
    ))
    if gutter:
        pad = xmax * GUTTER_FRACTION
        for nm, v in zip(names, vol):
            fig.add_annotation(x=-pad * 0.94, y=nm, text=f"{int(v):,}".replace(",", " "),
                               showarrow=False, xanchor="left", yanchor="middle",
                               font=dict(size=11, color=P.INK_SECONDARY))
        fig.add_shape(type="line", x0=0, x1=0, y0=-0.5, y1=len(names) - 0.5,
                      line=dict(color=P.BORDER, width=1))
        fig.update_xaxes(range=[-pad, xmax * 1.02])
    else:
        for nm, v, s in zip(names, vol, share):
            fig.add_annotation(x=s, y=nm, text=f"{int(v):,}".replace(",", " "),
                               showarrow=False, xanchor="left", xshift=8, yanchor="middle",
                               font=dict(size=11, color=P.INK_SECONDARY))
        fig.update_xaxes(range=[0, xmax * RIGHT_HEADROOM])
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(gridcolor=P.GRID, zerolinecolor=P.GRID, tickformat=".0%",
                     title="Share of output")
    fig.update_layout(height=_h(len(df)), bargap=0.3,
                      paper_bgcolor=P.SURFACE, plot_bgcolor=P.SURFACE,
                      margin=dict(t=30, l=8, r=16, b=52),
                      font=dict(color=P.INK, size=12))
    return fig


# ---------------------------------------------------------------------------
st.markdown(f"### {VARIANT}")
fields = fields_table(STRAS)
subs = top_subfields(GDANSK, n=20)

if VARIANT == "ab3_a":
    st.markdown("**Universite de Strasbourg -- fields**")
    st.plotly_chart(fig_ab3_a(fields, "field_name"), width="stretch")
    st.markdown("**University of Gdansk -- top subfields (n/a SI below the floor)**")
    st.plotly_chart(fig_ab3_a(subs, "subfield_name"), width="stretch")
elif VARIANT == "ab3_b":
    st.markdown("**Universite de Strasbourg -- fields**")
    st.plotly_chart(fig_ab3_b(fields, "field_name"), width="stretch")
    st.markdown("**University of Gdansk -- top subfields (n/a SI below the floor)**")
    st.plotly_chart(fig_ab3_b(subs, "subfield_name"), width="stretch")
elif VARIANT == "ab4_a":
    st.markdown("**Universite de Strasbourg -- fields, volume in a LEFT gutter**")
    st.plotly_chart(fig_ab4(fields, "field_name", gutter=True), width="stretch")
elif VARIANT == "ab4_b":
    st.markdown("**Universite de Strasbourg -- fields, volume RIGHT of the bar**")
    st.plotly_chart(fig_ab4(fields, "field_name", gutter=False), width="stretch")
else:
    st.error(f"unknown variant {VARIANT}")

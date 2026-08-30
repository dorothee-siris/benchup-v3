"""Phase 2B-R (stream VS) A/B prototype -- THROWAWAY, `design-system/ab/**` only.

One Streamlit page, one variant per `?variant=`, every frame built from the
DEPLOYED parquet files in `app/data/`. Never imported by anything shipped.

The three compared institutions are the ones the VS brief names, and the slot
order below is the one `palette.institution_slots` actually produces from their
`inst_key`s (ascending, never click order):

    slot 1  I161046081  University of Freiburg      inst_key    876   DE
    slot 2  I39804081   Sorbonne Universite         inst_key  2 922   FR
    slot 3  I68947357   Universite de Strasbourg    inst_key 13 085   FR

Variants
  ab7_a  fields x metric=share, GROUPED BARS       (the 2B-R-5 candidate)
  ab7_b  the same frame as DOT ROWS                (the 2B shipped mirror)
  ab8_a  frontier map (pooled) + diverging shared  (the 2B-R-9 pair)
  ab8_b  the same shared topics as ONE gradient chart (the alternative)
  ab9_a  fields x metric=si, OUTER-END value labels (the 2B-R-13 candidate)
  ab9_b  the same figure with POOLED-CENTRE labels  (the alternative)
  ship   every new builder on the real trio, one page (the render proof)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

AB_DIR = Path(__file__).resolve().parent
APP_ROOT = AB_DIR.parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from lib import charts as C          # noqa: E402
from lib import charts_compare as X  # noqa: E402
from lib import palette as P         # noqa: E402

DATA = APP_ROOT / "data"
IDS = ["I161046081", "I39804081", "I68947357"]
TREE = "bestfit"
YEARS = ("2020", "2021", "2022", "2023", "2024", "2025")
BONUS_YEAR = "2025"


# --------------------------------------------------------------------- data
@st.cache_data(show_spinner=False)
def index_rows() -> pd.DataFrame:
    ix = pd.read_parquet(DATA / "index.parquet")
    return ix[ix["institution_id"].isin(IDS)].reset_index(drop=True)


def slots_and_names():
    ix = index_rows()
    slots = P.institution_slots(dict(zip(ix["institution_id"], ix["inst_key"])))
    names = dict(zip(ix["institution_id"], ix["display_name"]))
    return slots, names


@st.cache_data(show_spinner=False)
def dim() -> pd.DataFrame:
    return pd.read_parquet(DATA / "topics_dim.parquet")


@st.cache_data(show_spinner=False)
def fields_metric(metric: str) -> pd.DataFrame:
    """`compare_data.metric_frame(level="field")`, reproduced by hand from the
    deployed parquet exactly as BUILD_PLAN_2BR section 4 declares it."""
    d = dim().drop_duplicates("field_id")[["field_id", "field_name", "domain_id"]]
    f = pd.read_parquet(DATA / "fields.parquet")
    f = f[f["institution_id"].isin(IDS) & (f["tree"].astype(str) == TREE)]
    out = f.merge(d, on="field_id", how="left")
    out = out.rename(columns={"field_id": "taxon_id", "field_name": "taxon_label"})
    out["value"] = out["share_frac"] if metric == "share" else out["si"]
    out["denominator"] = out["vol_frac"]
    if metric == "si":
        out["ref_value"] = C.SI_NEUTRAL
    # rank by the value SUMMED across the compared set -- the caller owns the
    # order (2B-R-5 removed the toggles), so the prototype ranks here.
    rank = out.groupby("taxon_id")["value"].sum().sort_values(ascending=False)
    out["_r"] = out["taxon_id"].map({k: i for i, k in enumerate(rank.index)})
    return out.sort_values("_r", kind="mergesort").reset_index(drop=True)


def fields_mirror() -> pd.DataFrame:
    """The same rows in the shape `fig_mirror_dots` takes (A/B #7 variant B)."""
    d = fields_metric("share").copy()
    d["share"] = d["value"]
    d["si"] = fields_metric("si")["value"].to_numpy()
    d["si_status"] = np.where(d["vol_frac"].fillna(0) > 0, "solid", "none")
    return d.rename(columns={"taxon_id": "field_id", "taxon_label": "field_name"})


@st.cache_data(show_spinner=False)
def frontier_pooled(top_n: int = 120) -> pd.DataFrame:
    """`compare_data.frontier_pooled`: ONE row per topic, `owner` naming the
    single institution that holds it or `shared` when more than one does.

    "Holds it" = the topic is in the global top-quartile frontier set AND the
    institution has non-zero volume on it. Pooling in the DATA is what makes
    cross-institution occlusion impossible in the map."""
    d = dim()
    d = d[d["top25pct_frontier"].fillna(False)
          & np.isfinite(pd.to_numeric(d["expansion_latest"], errors="coerce"))]
    keep = ["topic_id", "topic_name", "expansion_latest", "acceleration_latest",
            "top25pct_frontier", "is_excluded"]
    t = pd.read_parquet(DATA / "topics_all.parquet",
                        columns=["institution_id", "topic_id", "vol_full"],
                        filters=[("institution_id", "in", IDS)])
    t = t[t["vol_full"].fillna(0) > 0]
    t = t.merge(d[keep], on="topic_id", how="inner")
    wide = t.pivot_table(index="topic_id", columns="institution_id",
                         values="vol_full", aggfunc="sum").fillna(0.0)
    for i in IDS:
        if i not in wide.columns:
            wide[i] = 0.0
    held = (wide[IDS] > 0).sum(axis=1)
    owner = np.where(held > 1, X.SHARED_OWNER,
                     wide[IDS].idxmax(axis=1).to_numpy())
    meta = d[keep].drop_duplicates("topic_id").set_index("topic_id")
    out = pd.DataFrame({
        "topic_id": wide.index,
        "name": meta.loc[wide.index, "topic_name"].to_numpy(),
        "x": meta.loc[wide.index, "expansion_latest"].to_numpy(),
        "y": meta.loc[wide.index, "acceleration_latest"].to_numpy(),
        "combined_vol": wide[IDS].sum(axis=1).to_numpy(),
        "owner": owner,
        "top25pct_frontier": True,
    })
    for i in IDS:
        out[i] = wide[i].to_numpy()
    out = out.sort_values("combined_vol", ascending=False).head(top_n)
    return out.reset_index(drop=True)


def shared_long(ids, top_n: int = 14) -> pd.DataFrame:
    """`compare_data.shared_frontier` in LONG form: the shared topics with each
    side's own volume."""
    p = frontier_pooled(top_n=400)
    p = p[p["owner"] == X.SHARED_OWNER]
    p = p[(p[list(ids)] > 0).all(axis=1)]
    p = p.assign(_c=p[list(ids)].sum(axis=1)).sort_values("_c", ascending=False).head(top_n)
    rows = []
    for _, r in p.iterrows():
        for i in ids:
            rows.append(dict(institution_id=i, topic_id=r["topic_id"],
                             name=r["name"], vol=float(r[i])))
    return pd.DataFrame(rows)


def pulse_frame() -> pd.DataFrame:
    """SYNTHETIC, and labelled as such wherever it is shown: `collab_pairs`
    does not exist until pipeline stream P2 lands. The pulse builder's geometry
    is what this render proves; its numbers prove nothing."""
    return pd.DataFrame({"year": list(YEARS),
                         "co_pubs": [131.0, 148.0, 152.0, 171.0, 190.0, 96.0]})


# ------------------------------------------------------------------ variants
def pooled_centre_labels(fig: go.Figure, xfrac: float = 0.55) -> go.Figure:
    """A/B #9 variant B: strip the outer-end labels off the bars and pool them
    into ONE column at a fixed x, in lane order -- the classic "value column"
    alternative to a direct label."""
    out = go.Figure(fig)
    texts = []
    for tr in out.data:
        if getattr(tr, "text", None) is None:
            continue
        for y, t in zip(tr.y, tr.text):
            texts.append((float(y), str(t)))
        tr.text = None
        tr.textposition = None
    lo, hi = out.layout.xaxis.range
    x = float(lo) + (float(hi) - float(lo)) * xfrac
    for y, t in texts:
        out.add_annotation(x=x, y=y, text=t, showarrow=False, xanchor="left",
                           yanchor="middle",
                           font=dict(size=C.GUTTER_FONT_PX, color=P.INK_SECONDARY))
    return out


def gradient_chart(ids) -> go.Figure:
    """A/B #8 variant B: ONE chart for the shared frontier -- every shared topic
    a bubble in the same plane, its colour a DIVERGING ramp between the two
    institutions' hues with a NEUTRAL midpoint, keyed on the first side's share
    of the joint volume. The imbalance is a hue, not a length."""
    p = frontier_pooled(top_n=400)
    p = p[p["owner"] == X.SHARED_OWNER]
    p = p[(p[list(ids)] > 0).all(axis=1)].copy()
    tot = p[list(ids)].sum(axis=1)
    p["_f"] = p[ids[0]] / tot.replace(0, np.nan)
    slots, names = slots_and_names()
    scale = [[0.0, P.institution_color(slots[ids[1]])],
             [0.5, P.NEUTRAL],
             [1.0, P.institution_color(slots[ids[0]])]]
    mmax = float(p["combined_vol"].max()) or 1.0
    sizes = X.MAP_BUBBLE_MIN_PX + (X.MAP_BUBBLE_MAX_PX - X.MAP_BUBBLE_MIN_PX) * np.sqrt(
        p["combined_vol"].to_numpy(dtype=float) / mmax)
    fig = go.Figure(go.Scatter(
        x=p["x"], y=p["y"], mode="markers",
        marker=dict(color=p["_f"], colorscale=scale, cmin=0.0, cmax=1.0,
                    size=sizes, sizemode="diameter", opacity=X.OVERLAY_OPACITY,
                    line=dict(color=P.SURFACE, width=C.HAIRLINE_PX),
                    showscale=True),
        customdata=[[n] for n in p["name"]],
        hovertemplate="%{customdata[0]}<extra></extra>", showlegend=False))
    fig.add_vline(x=C.FRONTIER_ORIGIN, line=dict(color=P.INK, width=X.BOLD_AXIS_PX))
    fig.add_hline(y=C.FRONTIER_ORIGIN, line=dict(color=P.INK, width=X.BOLD_AXIS_PX))
    fig.update_xaxes(title_text=C.AX_EXPANSION, gridcolor=P.GRID, linecolor=P.BORDER)
    fig.update_yaxes(title_text=C.AX_ACCELERATION, gridcolor=P.GRID, linecolor=P.BORDER)
    return C._base_layout(fig, X.MAP_HEIGHT_PX,
                          margin=dict(t=C.BASE_PX // 2, l=8, r=16, b=C.BASE_PX))


def probe_pairs(ids) -> dict:
    """The two topics A/B #8 asks about: the MOST lopsided shared topic and the
    most BALANCED one. Reported so the measurement names real rows rather than
    an invented example."""
    long = shared_long(ids, top_n=400)
    w = long.pivot_table(index="topic_id", columns="institution_id", values="vol").fillna(0.0)
    w = w[(w > 0).all(axis=1)]
    ratio = w[ids[0]] / w[ids[1]].replace(0, np.nan)
    lop = ratio.idxmax() if len(ratio.dropna()) else None
    bal = (ratio - 1.0).abs().idxmin() if len(ratio.dropna()) else None
    return {"lopsided": (lop, float(w.loc[lop, ids[0]]), float(w.loc[lop, ids[1]])),
            "balanced": (bal, float(w.loc[bal, ids[0]]), float(w.loc[bal, ids[1]]))}


# ---------------------------------------------------------------------- page
st.set_page_config(page_title="2B-R A/B", layout="wide")
variant = st.query_params.get("variant", "ship")
slots, names = slots_and_names()
pair = [IDS[1], IDS[2]]          # Sorbonne + Strasbourg, the N = 2 pair

if variant == "ab7_a":
    st.markdown(X.legend_strip(IDS, slots=slots, names=names), unsafe_allow_html=True)
    st.plotly_chart(X.fig_metric_bars(fields_metric("share"), "share", IDS,
                                      slots=slots, names=names, level="field"),
                    use_container_width=True)
elif variant == "ab7_b":
    st.markdown(X.legend_strip(IDS, slots=slots, names=names), unsafe_allow_html=True)
    st.plotly_chart(X.fig_mirror_dots(fields_mirror(), family="oa", slots=slots,
                                      names=names, sort="volume"),
                    use_container_width=True)
elif variant == "ab8_a":
    st.markdown(X.legend_strip(pair, slots=slots, names=names, shared=True),
                unsafe_allow_html=True)
    st.plotly_chart(X.fig_frontier_map(frontier_pooled(), 120, slots=slots, names=names),
                    use_container_width=True)
    st.plotly_chart(X.fig_diverging_shared(shared_long(pair), pair, slots=slots,
                                           names=names, top_n=14),
                    use_container_width=True)
elif variant.startswith("ab8_n"):
    # the 2B-R-9 slider, measured: does top-N actually buy occlusion back?
    st.plotly_chart(X.fig_frontier_map(frontier_pooled(), int(variant.split("n")[-1]),
                                       slots=slots, names=names),
                    use_container_width=True)
elif variant == "ab8_b":
    st.plotly_chart(gradient_chart(pair), use_container_width=True)
elif variant == "ab9_a":
    st.plotly_chart(X.fig_metric_bars(fields_metric("si"), "si", IDS, slots=slots,
                                      names=names, level="field"),
                    use_container_width=True)
elif variant == "ab9_b":
    st.plotly_chart(pooled_centre_labels(
        X.fig_metric_bars(fields_metric("si"), "si", IDS, slots=slots,
                          names=names, level="field")), use_container_width=True)
elif variant == "probe":
    st.write(probe_pairs(pair))
else:
    st.markdown(X.legend_strip(IDS, slots=slots, names=names), unsafe_allow_html=True)
    st.plotly_chart(X.fig_metric_bars(fields_metric("share"), "share", IDS,
                                      slots=slots, names=names, level="field"),
                    use_container_width=True)
    st.plotly_chart(X.fig_metric_bars(fields_metric("si"), "si", IDS, slots=slots,
                                      names=names, level="field"),
                    use_container_width=True)
    st.markdown(X.legend_strip(IDS, slots=slots, names=names, shared=True),
                unsafe_allow_html=True)
    st.plotly_chart(X.fig_frontier_map(frontier_pooled(), 120, slots=slots, names=names),
                    use_container_width=True)
    st.markdown(X.legend_strip(pair, slots=slots, names=names), unsafe_allow_html=True)
    st.plotly_chart(X.fig_diverging_shared(shared_long(pair), pair, slots=slots,
                                           names=names, top_n=14),
                    use_container_width=True)
    st.plotly_chart(X.fig_diverging_shared(shared_long(IDS), IDS, slots=slots,
                                           names=names, top_n=14),
                    use_container_width=True)
    st.caption("pulse frame is SYNTHETIC -- collab_pairs lands with pipeline P2")
    st.plotly_chart(X.fig_pulse(pulse_frame(), bonus_year=BONUS_YEAR),
                    use_container_width=True)

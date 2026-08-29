"""BenchUp v3 -- pure Plotly figure builders for the profile section.

NO Streamlit import lives in this module (the same rule the engine package
follows): every function takes a plain DataFrame or plain sequences and returns
a `plotly.graph_objects.Figure`, so it can be unit-tested headless and reused
outside the app. `lib/views_find.py` is the only place that puts a figure on a
page.

Two hard house rules this module is written to satisfy, and the mechanics that
make them true rather than aspirational:

1.  **No colour literal.** Every hue comes from `lib.palette`; `tests/test_palette.py`
    fails the build on a `#RRGGBB` anywhere under `lib/` except `palette.py`.
    That includes the chart surface (`palette.SURFACE`), the gridlines
    (`palette.GRID`), the annotation ink (`palette.INK_SECONDARY`) and the
    hairlines (`palette.BORDER`).

2.  **No digit in any string.** `tests/test_charts.py` scans this file's source
    for a digit inside a string literal, using the SAME allowlist as the
    narrative digit-ban (`tests/digit_allowlist.txt`, read-only -- the allowlist
    is full at its cap and this module adds nothing to it). Consequences that
    are easy to undo by accident:
      * number formats are COMPOSED from int constants
        (`f".{SHARE_DECIMALS}%"`), never typed as `".1%"`;
      * hover text is PRE-FORMATTED in Python and passed through `customdata`
        with `hovertemplate="%{customdata}<extra></extra>"` (Lorraine's idiom),
        so no `%{x:.1%}` and no `%{customdata[0]}` -- both of which carry a
        digit -- ever appears in this file;
      * the SI reference is a LINE at the neutral value, never a text label
        naming that value; the caller writes any such sentence into `copy.py`
        with a `{placeholder}`.
    Anything parametric (counts, thresholds, the year window) is a caller-filled
    `{placeholder}` in a title/caption string the caller owns -- this module
    only accepts already-composed text.

Grammar decided by the R1 A/Bs on real data (`design-system/ab/AB_VERDICT.md`):
  * A/B #3 -> the share + SI pair is TWO ALIGNED PANELS of one figure sharing a
    y-axis: share bars on the left, SI as a lollipop from a dashed reference at
    the neutral value on the right. The rejected rival encoded SI as a tick on
    the share row itself, which put SI on a per-row scale (not comparable
    across rows) and stretched the share axis to fit the tick, degrading the
    primary measure.
  * A/B #4 -> volume sits in a LEFT TEXT GUTTER, right-aligned against the
    zero baseline, not as a right-of-bar annotation. The rival clipped at the
    narrow width and scattered the numbers across the full plot width.
  * Both from Lorraine Phase 2 / BenchUp V1+V2 lineage; the grouped-bar
    geometry below is Lorraine's `_series_offset_width` verbatim, because
    `offsetgroup` is BROKEN on the pinned plotly 5.24.1.
"""
from __future__ import annotations

from typing import Mapping, Sequence

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from lib import palette as P

# ---------------------------------------------------------------------------
# Numeric + geometric constants (ints/floats -- never inside a string literal)
# ---------------------------------------------------------------------------
SHARE_DECIMALS = 1          # a share is shown to one decimal of a percent IN HOVER
AXIS_DECIMALS = 0           # ...but the share AXIS ticks carry none: a tick is a
                            # scale marker, not a measurement, and a column of
                            # ".0%" suffixes is noise the reader has to filter
                            # (one precision level PER ROLE, RULES section 5)
SI_DECIMALS = 2             # SI / ESI to two decimals (they cluster near the neutral value)
FRONTIER_DECIMALS = 2

ROW_PX = 22                 # one category row's vertical budget
BASE_PX = 60                # axes + margins
MIN_HEIGHT = 300
SCATTER_HEIGHT = 520

GUTTER_FRACTION = 0.16      # of the x range, reserved left of zero for the volume gutter
GUTTER_INSET = 0.06         # of the gutter, the padding between the number and the baseline
BAR_GAP = 0.3
MARKER_PX = 10
LINE_PX = 2
HAIRLINE_PX = 1
FONT_PX = 12
GUTTER_FONT_PX = 11
BUBBLE_MIN_PX = 6
BUBBLE_MAX_PX = 34

DEFAULT_GROUP_SPAN = 0.8    # Lorraine VIZ_SPEC_pass6 S1.5 geometry, verbatim
DEFAULT_GROUP_FILL = 0.9

SI_NEUTRAL = 1.0            # SI/ESI reference: at the neutral value the institution's
                            # share equals the reference population's share
FRONTIER_ORIGIN = 0.0       # the quadrant split on BOTH frontier axes (verified on
                            # topics_dim: `quadrant` flips sign at zero on expansion
                            # and on acceleration)

THIN_SPACE = "\N{NARROW NO-BREAK SPACE}"
EXCLUDED_GLYPH = "\N{ASTERISK OPERATOR}"   # catch-all / out-of-scope topic marker

# ---------------------------------------------------------------------------
# Axis + hover vocabulary. Digit-free by construction. A caller that wants
# different wording passes it in; nothing here is a sentence, only a label.
# ---------------------------------------------------------------------------
AX_SHARE = "Share of output"
AX_SI = "Specialisation index"
AX_ESI = "Specialisation index (SDG)"
AX_WORKS = "Works"
AX_YEAR = "Year"
AX_EXPANSION = "Expansion"
AX_ACCELERATION = "Acceleration"

HOVER_SHARE = "share"
HOVER_SI = "SI"
HOVER_ESI = "ESI"
HOVER_VOL_FULL = "works (full counting)"
HOVER_VOL_FRAC = "works (fractional)"
HOVER_MASS = "classified mass"
HOVER_EXPANSION = "expansion"
HOVER_ACCELERATION = "acceleration"
HOVER_EXCLUDED = "catch-all / out-of-scope topic"

FAMILIES = ("oa", "erc", "sdg", "doctype")
SORTS = ("volume", "taxonomy")

_PCT_FMT = f".{SHARE_DECIMALS}%"
_AXIS_PCT_FMT = f".{AXIS_DECIMALS}%"
_SI_FMT = f".{SI_DECIMALS}f"
_FRONTIER_FMT = f".{FRONTIER_DECIMALS}f"

# Column-name candidates, in preference order, for the frames of section 9.4.
_LABEL_COLS = ("topic_name", "subfield_name", "field_name", "panel_label",
               "sdg_label", "doc_type", "label", "domain_name")
_VOLUME_COLS = ("vol_full", "vol_frac", "mass", "total")


# ---------------------------------------------------------------------------
# Small pure helpers
# ---------------------------------------------------------------------------
def row_height(n: int, minimum: int = MIN_HEIGHT) -> int:
    """Figure height for `n` category rows -- the shared idiom, one place."""
    return max(minimum, ROW_PX * int(n) + BASE_PX)


def _fmt_pct(v: float) -> str:
    return P.NA_MARK if v is None or (isinstance(v, float) and np.isnan(v)) else format(float(v), _PCT_FMT)


def _fmt_si(v: float) -> str:
    return P.NA_MARK if v is None or (isinstance(v, float) and np.isnan(v)) else format(float(v), _SI_FMT)


def _fmt_frontier(v: float) -> str:
    return P.NA_MARK if v is None or (isinstance(v, float) and np.isnan(v)) else format(float(v), _FRONTIER_FMT)


def _fmt_vol(v) -> str:
    """Volumes print with a narrow no-break space thousands separator (Lorraine
    `fr_int` convention). A fractional volume keeps one decimal; a full count
    prints as an integer."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return P.NA_MARK
    v = float(v)
    if abs(v - round(v)) < 1e-9:
        return format(int(round(v)), ",").replace(",", THIN_SPACE)
    return format(v, f",.{SHARE_DECIMALS}f").replace(",", THIN_SPACE)


def _first_col(df: pd.DataFrame, candidates: Sequence[str]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _nice_ticks(vmax: float, target: int = 5) -> list[float]:
    """Non-negative tick positions for an axis whose RANGE starts below zero
    (the volume gutter). Without explicit `tickvals`, plotly would label the
    gutter with negative percentages -- a number the chart does not mean."""
    if not np.isfinite(vmax) or vmax <= 0:
        return [0.0]
    raw = vmax / max(target, 1)
    mag = 10.0 ** np.floor(np.log10(raw))
    for mult in (1, 2, 2.5, 5, 10):
        step = mult * mag
        if raw <= step:
            break
    n = int(np.floor(vmax / step)) + 1
    return [round(i * step, 12) for i in range(n)]


def _colors_for(df: pd.DataFrame, family: str) -> list[str]:
    """The ONE place a family maps to hues. Coexistence rule (palette.py
    docstring): a figure uses exactly one family, so this returns one list and
    nothing merges two."""
    if family == "oa":
        col = _first_col(df, ("domain_id",))
        return [P.domain_color(v) for v in df[col]] if col else [P.COMPARISON] * len(df)
    if family == "erc":
        col = _first_col(df, ("erc_domain",))
        return [P.erc_color(v) for v in df[col]] if col else [P.COMPARISON] * len(df)
    if family == "sdg":
        col = _first_col(df, ("sdg_number", "sdg_idx"))
        if col is None:
            return [P.COMPARISON] * len(df)
        offset = 1 if col == "sdg_idx" else 0
        return [P.sdg_color(int(v) + offset) for v in df[col]]
    if family == "doctype":
        col = _first_col(df, ("doc_type", "type"))
        return [P.doctype_color(v) for v in df[col]] if col else [P.COMPARISON] * len(df)
    raise ValueError(f"family must be one of {FAMILIES}, got {family!r}")


def _taxonomy_keys(df: pd.DataFrame, family: str) -> list[str]:
    if family == "erc":
        return [c for c in ("erc_domain_rank", "panel_idx", "panel_code") if c in df.columns]
    if family == "sdg":
        return [c for c in ("sdg_number", "sdg_idx") if c in df.columns]
    if family == "doctype":
        return [c for c in ("doctype_rank", "doc_type") if c in df.columns]
    return [c for c in ("domain_id", "field_id", "subfield_id", "topic_id") if c in df.columns]


def _ordered(df: pd.DataFrame, family: str, sort: str, value_col: str) -> pd.DataFrame:
    if sort not in SORTS:
        raise ValueError(f"sort must be one of {SORTS}, got {sort!r}")
    out = df.copy()
    if sort == "volume":
        return out.sort_values(value_col, ascending=False, kind="mergesort").reset_index(drop=True)
    if family == "erc" and "erc_domain" in out.columns and "erc_domain_rank" not in out.columns:
        rank = {d: i for i, d in enumerate(P.ERC_DOMAIN_ORDER)}
        out["erc_domain_rank"] = out["erc_domain"].astype(str).str.upper().map(rank).fillna(len(rank))
    if family == "doctype" and "doc_type" in out.columns and "doctype_rank" not in out.columns:
        rank = {d: i for i, d in enumerate(P.DOCTYPE_ORDER)}
        out["doctype_rank"] = out["doc_type"].astype(str).str.lower().map(rank).fillna(len(rank))
    keys = _taxonomy_keys(out, family)
    if not keys:
        return out.reset_index(drop=True)
    return out.sort_values(keys, kind="mergesort").reset_index(drop=True)


def _base_layout(fig: go.Figure, height: int, *, margin: dict) -> go.Figure:
    fig.update_layout(
        height=height,
        bargap=BAR_GAP,
        showlegend=False,
        paper_bgcolor=P.SURFACE,
        plot_bgcolor=P.SURFACE,
        margin=margin,
        font=dict(color=P.INK, size=FONT_PX),
        hoverlabel=dict(bgcolor=P.SURFACE, font=dict(color=P.INK, size=FONT_PX)),
    )
    return fig


# ---------------------------------------------------------------------------
# 1. share + SI -- the paired form (A/B #3 winner), with the volume gutter
#    (A/B #4 winner). Used by the Fields, Top subfields, SDG and ERC panels.
# ---------------------------------------------------------------------------
def fig_share_si(
    df: pd.DataFrame,
    *,
    family: str = "oa",
    sort: str = "volume",
    gutter: bool = True,
    si_col: str = "si",
    share_col: str = "share",
    label_col: str | None = None,
    volume_col: str | None = None,
    si_axis_title: str = AX_SI,
    si_hover_label: str = HOVER_SI,
    stacked: bool = False,
) -> go.Figure:
    """Two aligned panels of ONE figure, sharing the y (category) axis.

    LEFT   horizontal share bars, coloured by `family`; with `gutter=True` the
           volume prints right-aligned in a fixed gutter left of the zero
           baseline, so every number sits in one column (A/B #4).
    RIGHT  the SI lollipop: a stem from the neutral reference to the value and
           a dot at the value, on ONE scale shared by every row, with a dashed
           vertical reference line. A row whose `si_col` is NaN (below the G6
           floor) gets NO MARK AT ALL -- never a dot at zero, never a dot at
           the neutral value -- and its hover says so with `palette.NA_MARK`.

    `stacked=True` puts the SI panel BELOW the share panel instead of beside it,
    same row order, for the narrow breakpoint: side by side at 390 px each panel
    measures 61 px of plot area, which is not a chart (VIZ_SPEC section 1.8, the
    measured cost of the A/B #3 winner). Streamlit cannot read the viewport width
    server-side, so the caller decides when to pass it -- the builder only makes
    the layout available.

    `sort="volume"` orders by the share descending; `sort="taxonomy"` orders by
    the family's own hierarchy (domain -> field -> subfield -> topic; ERC domain
    then panel; SDG number). Colours never move with the sort: they follow the
    entity (dataviz non-negotiable "colour follows the entity, never its rank").
    """
    if share_col not in df.columns:
        raise ValueError(f"missing column {share_col!r}")
    d = _ordered(df, family, sort, share_col)
    n = len(d)
    label_col = label_col or _first_col(d, _LABEL_COLS)
    if label_col is None:
        raise ValueError("no label column found; pass label_col=")
    volume_col = volume_col or _first_col(d, _VOLUME_COLS)

    names = [str(v) for v in d[label_col]]
    colors = _colors_for(d, family)
    share = d[share_col].to_numpy(dtype=float)
    si = (d[si_col].to_numpy(dtype=float) if si_col in d.columns
          else np.full(n, np.nan, dtype=float))
    has_si = bool(np.isfinite(si).any())

    # No defined SI anywhere in the frame (every row below the G6 floor) ->
    # ONE panel, not a two-panel figure with an empty right half. The share
    # read is unaffected and the caller's caption says why the column is gone.
    if not has_si:
        fig = make_subplots(rows=1, cols=1)
        si_row, si_col = 1, 1
    elif stacked:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=False,
                            row_heights=[0.5, 0.5], vertical_spacing=0.08)
        si_row, si_col = 2, 1
    else:
        fig = make_subplots(rows=1, cols=2, shared_yaxes=True,
                            column_widths=[0.62, 0.38], horizontal_spacing=0.03)
        si_row, si_col = 1, 2

    vol = d[volume_col].to_numpy() if volume_col else None
    bar_hover = []
    for i in range(n):
        parts = [names[i], f"{HOVER_SHARE}{THIN_SPACE}{_fmt_pct(share[i])}"]
        if vol is not None:
            lab = HOVER_VOL_FULL if volume_col == "vol_full" else (
                HOVER_VOL_FRAC if volume_col == "vol_frac" else HOVER_MASS)
            parts.append(f"{lab}{THIN_SPACE}{_fmt_vol(vol[i])}")
        parts.append(f"{si_hover_label}{THIN_SPACE}{_fmt_si(si[i])}")
        bar_hover.append("<br>".join(parts))

    fig.add_trace(go.Bar(
        x=share, y=names, orientation="h",
        marker_color=colors, marker_line_color=P.SURFACE, marker_line_width=HAIRLINE_PX,
        customdata=bar_hover, hovertemplate="%{customdata}<extra></extra>",
        showlegend=False,
    ), row=1, col=1)

    xmax = float(np.nanmax(share)) if n and np.isfinite(share).any() else 1.0
    xmax = xmax if xmax > 0 else 1.0
    if gutter and vol is not None:
        pad = xmax * GUTTER_FRACTION
        for i, nm in enumerate(names):
            fig.add_annotation(
                x=-pad * GUTTER_INSET, y=nm, xref="x", yref="y",
                text=_fmt_vol(vol[i]), showarrow=False,
                xanchor="right", yanchor="middle",
                font=dict(size=GUTTER_FONT_PX, color=P.INK_SECONDARY),
            )
        fig.add_shape(type="line", x0=0, x1=0, y0=-0.5, y1=n - 0.5,
                      xref="x", yref="y", line=dict(color=P.BORDER, width=HAIRLINE_PX))
        fig.update_xaxes(range=[-pad, xmax * 1.02], tickvals=_nice_ticks(xmax), row=1, col=1)

    if has_si:
        ok = np.isfinite(si)
        for i, nm in enumerate(names):
            if not ok[i]:
                continue
            fig.add_trace(go.Scatter(
                x=[SI_NEUTRAL, si[i]], y=[nm, nm], mode="lines",
                line=dict(color=colors[i], width=LINE_PX),
                hoverinfo="skip", showlegend=False,
            ), row=si_row, col=si_col)
        fig.add_trace(go.Scatter(
            x=si[ok], y=[nm for nm, k in zip(names, ok) if k], mode="markers",
            marker=dict(color=[c for c, k in zip(colors, ok) if k], size=MARKER_PX,
                        line=dict(color=P.SURFACE, width=LINE_PX)),
            customdata=[h for h, k in zip(bar_hover, ok) if k],
            hovertemplate="%{customdata}<extra></extra>", showlegend=False,
        ), row=si_row, col=si_col)
        fig.add_vline(x=SI_NEUTRAL, row=si_row, col=si_col,
                      line=dict(color=P.INK_SECONDARY, width=HAIRLINE_PX, dash="dash"))
        fig.update_xaxes(title_text=si_axis_title, row=si_row, col=si_col)

    fig.update_yaxes(autorange="reversed", showgrid=False, automargin=True)
    fig.update_xaxes(gridcolor=P.GRID, zerolinecolor=P.GRID, linecolor=P.BORDER)
    fig.update_xaxes(title_text=AX_SHARE, tickformat=_AXIS_PCT_FMT, row=1, col=1)
    height = row_height(n) * (2 if (has_si and stacked) else 1)
    return _base_layout(fig, height, margin=dict(t=BASE_PX // 2, l=8, r=16, b=BASE_PX))


# ---------------------------------------------------------------------------
# 2. Top topics -- share bars, catch-all topics flagged (glyph + muted fill)
# ---------------------------------------------------------------------------
def fig_topics(
    df: pd.DataFrame,
    *,
    sort: str = "volume",
    gutter: bool = True,
    share_col: str = "share",
    label_col: str = "topic_name",
    volume_col: str | None = None,
) -> go.Figure:
    """Horizontal share bars for topics, coloured by the topic's DOMAIN (topics
    inherit; `palette.domain_color`). A row flagged `is_excluded` (the catch-all
    / out-of-scope topics) keeps its domain hue at `palette.MUTED_OPACITY`, is
    prefixed with `EXCLUDED_GLYPH` on the axis, and says why on hover -- it is
    shown and counted, never silently dropped."""
    d = _ordered(df, "oa", sort, share_col)
    n = len(d)
    volume_col = volume_col or _first_col(d, _VOLUME_COLS)
    excluded = (d["is_excluded"].fillna(False).to_numpy(dtype=bool)
                if "is_excluded" in d.columns else np.zeros(n, dtype=bool))
    colors = _colors_for(d, "oa")
    names = [f"{EXCLUDED_GLYPH}{THIN_SPACE}{v}" if excluded[i] else str(v)
             for i, v in enumerate(d[label_col])]
    share = d[share_col].to_numpy(dtype=float)
    vol = d[volume_col].to_numpy() if volume_col else None

    hover = []
    for i in range(n):
        parts = [str(d[label_col].iloc[i]), f"{HOVER_SHARE}{THIN_SPACE}{_fmt_pct(share[i])}"]
        if vol is not None:
            parts.append(f"{HOVER_VOL_FULL if volume_col == 'vol_full' else HOVER_VOL_FRAC}"
                         f"{THIN_SPACE}{_fmt_vol(vol[i])}")
        if excluded[i]:
            parts.append(HOVER_EXCLUDED)
        hover.append("<br>".join(parts))

    fig = go.Figure(go.Bar(
        x=share, y=names, orientation="h",
        marker=dict(color=colors, opacity=[P.MUTED_OPACITY if e else 1.0 for e in excluded],
                    line=dict(color=P.SURFACE, width=HAIRLINE_PX)),
        customdata=hover, hovertemplate="%{customdata}<extra></extra>", showlegend=False,
    ))
    xmax = float(np.nanmax(share)) if n and np.isfinite(share).any() else 1.0
    xmax = xmax if xmax > 0 else 1.0
    if gutter and vol is not None:
        pad = xmax * GUTTER_FRACTION
        for i, nm in enumerate(names):
            fig.add_annotation(x=-pad * GUTTER_INSET, y=nm, text=_fmt_vol(vol[i]),
                               showarrow=False, xanchor="right", yanchor="middle",
                               font=dict(size=GUTTER_FONT_PX, color=P.INK_SECONDARY))
        fig.add_shape(type="line", x0=0, x1=0, y0=-0.5, y1=n - 0.5,
                      line=dict(color=P.BORDER, width=HAIRLINE_PX))
        fig.update_xaxes(range=[-pad, xmax * 1.02], tickvals=_nice_ticks(xmax))
    fig.update_yaxes(autorange="reversed", showgrid=False, automargin=True)
    fig.update_xaxes(title_text=AX_SHARE, tickformat=_AXIS_PCT_FMT,
                     gridcolor=P.GRID, zerolinecolor=P.GRID, linecolor=P.BORDER)
    return _base_layout(fig, row_height(n), margin=dict(t=BASE_PX // 2, l=8, r=16, b=BASE_PX))


# ---------------------------------------------------------------------------
# 3. Frontier positioning -- topics scatter, Expansion x Acceleration
# ---------------------------------------------------------------------------
def fig_frontier(
    df: pd.DataFrame,
    *,
    x_col: str = "expansion_latest",
    y_col: str = "acceleration_latest",
    size_col: str | None = None,
    label_col: str = "topic_name",
) -> go.Figure:
    """One bubble per SCORED topic: x = expansion, y = acceleration, area = the
    topic's mass on the current basis, colour = its domain. The two quadrant
    lines sit at the origin on both axes (verified against `topics_dim.quadrant`,
    which flips sign exactly there). A top-quartile frontier topic
    (`top25pct_frontier`) carries an INK outline -- a shape signal on top of its
    family colour, never a new hue.

    Rows with no score (`x_col`/`y_col` NaN) are DROPPED here and must be
    counted in the caller's caption: the panel states what it could not place
    rather than letting it vanish."""
    size_col = size_col or _first_col(df, _VOLUME_COLS)
    d = df.copy()
    d = d[np.isfinite(pd.to_numeric(d[x_col], errors="coerce"))
          & np.isfinite(pd.to_numeric(d[y_col], errors="coerce"))].reset_index(drop=True)
    n = len(d)
    x = d[x_col].to_numpy(dtype=float)
    y = d[y_col].to_numpy(dtype=float)
    colors = _colors_for(d, "oa")
    mass = (pd.to_numeric(d[size_col], errors="coerce").fillna(0.0).to_numpy(dtype=float)
            if size_col else np.ones(n))
    mmax = float(mass.max()) if n and mass.max() > 0 else 1.0
    sizes = BUBBLE_MIN_PX + (BUBBLE_MAX_PX - BUBBLE_MIN_PX) * np.sqrt(mass / mmax)
    top = (d["top25pct_frontier"].fillna(False).to_numpy(dtype=bool)
           if "top25pct_frontier" in d.columns else np.zeros(n, dtype=bool))

    hover = []
    for i in range(n):
        parts = [str(d[label_col].iloc[i]),
                 f"{HOVER_EXPANSION}{THIN_SPACE}{_fmt_frontier(x[i])}",
                 f"{HOVER_ACCELERATION}{THIN_SPACE}{_fmt_frontier(y[i])}"]
        if size_col:
            parts.append(f"{HOVER_MASS}{THIN_SPACE}{_fmt_vol(mass[i])}")
        hover.append("<br>".join(parts))

    fig = go.Figure(go.Scatter(
        x=x, y=y, mode="markers",
        marker=dict(color=colors, size=sizes, sizemode="diameter",
                    line=dict(color=[P.INK if t else P.SURFACE for t in top],
                              width=[P.OUTLINE_WIDTH if t else HAIRLINE_PX for t in top])),
        customdata=hover, hovertemplate="%{customdata}<extra></extra>", showlegend=False,
    ))
    fig.add_vline(x=FRONTIER_ORIGIN, line=dict(color=P.GRID, width=HAIRLINE_PX))
    fig.add_hline(y=FRONTIER_ORIGIN, line=dict(color=P.GRID, width=HAIRLINE_PX))
    fig.update_xaxes(title_text=AX_EXPANSION, gridcolor=P.GRID,
                     zerolinecolor=P.GRID, linecolor=P.BORDER)
    fig.update_yaxes(title_text=AX_ACCELERATION, gridcolor=P.GRID,
                     zerolinecolor=P.GRID, linecolor=P.BORDER)
    return _base_layout(fig, SCATTER_HEIGHT, margin=dict(t=BASE_PX // 2, l=8, r=16, b=BASE_PX))


# ---------------------------------------------------------------------------
# 4. SDG profile -- share bars in goal order + ESI dots (UN colours)
# ---------------------------------------------------------------------------
def fig_sdg(df: pd.DataFrame, *, sort: str = "taxonomy", gutter: bool = True) -> go.Figure:
    """The SDG panel. Delegates to `fig_share_si` with `esi` presented in the SI
    slot, so the reader learns ONE form and reuses it (Lorraine VIZ_SPEC
    `same-read-same-form`).

    The share denominator is SDG-TAGGED fractional mass and the labelling is
    MULTI-LABEL -- one work can carry several goals, so these shares do NOT sum
    to one. The caller's caption must say so; this builder deliberately draws no
    total and no stack that would imply a partition."""
    d = df.copy()
    if "esi" in d.columns and "si" not in d.columns:
        d = d.rename(columns={"esi": "si"})
    if "sdg_number" not in d.columns and "sdg_idx" in d.columns:
        d["sdg_number"] = pd.to_numeric(d["sdg_idx"], errors="coerce") + 1
    return fig_share_si(d, family="sdg", sort=sort, gutter=gutter,
                        si_axis_title=AX_ESI, si_hover_label=HOVER_ESI)


# ---------------------------------------------------------------------------
# 5. ERC profile -- panels grouped by ERC domain, share + SI
# ---------------------------------------------------------------------------
def fig_erc(df: pd.DataFrame, *, sort: str = "taxonomy", gutter: bool = True) -> go.Figure:
    """The ERC panel view: one row per ERC evaluation panel, coloured by its ERC
    DOMAIN (three hues -- `palette.ERC_DOMAIN_COLORS`), share on the left and SI
    on the right, `sort="taxonomy"` grouping the panels by domain in the fixed
    PE -> LS -> SH order. The weak-panel caveat (some panels are thinly
    populated) is the caller's caption, not a mark on the chart."""
    return fig_share_si(df, family="erc", sort=sort, gutter=gutter)


# ---------------------------------------------------------------------------
# 6. The yearly-breakdown PAIR: global horizontal bars + per-year GROUPED bars
# ---------------------------------------------------------------------------
def fig_breakdown_global(
    labels: Sequence[str],
    totals: Sequence[float],
    colors: Sequence[str],
) -> go.Figure:
    """LEFT panel of the pair: one horizontal bar per series, sorted by volume
    descending, with a DIRECT END LABEL and no legend (the y-axis names the
    series; the shared chip legend serves the pair).

    Why the direct end label here and a left gutter in `fig_share_si`: there the
    number is a SECOND measure sitting beside a share bar, and A/B #4 showed it
    belongs in an aligned column; here the number IS the bar's own value, which
    is the textbook direct-label case (dataviz marks-and-anatomy, "selective
    direct labels"). Same pattern as Lorraine `plot_global_breakdown_h`."""
    order = sorted(range(len(labels)), key=lambda i: float(totals[i]), reverse=True)
    cats = [str(labels[i]) for i in order]
    tot = [float(totals[i]) for i in order]
    cols = [colors[i] for i in order]
    hover = [f"{c}<br>{AX_WORKS.lower()}{THIN_SPACE}{_fmt_vol(t)}" for c, t in zip(cats, tot)]

    fig = go.Figure(go.Bar(
        x=tot, y=cats, orientation="h",
        marker_color=cols, marker_line_color=P.SURFACE, marker_line_width=HAIRLINE_PX,
        customdata=hover, hovertemplate="%{customdata}<extra></extra>", showlegend=False,
    ))
    for c, t in zip(cats, tot):
        fig.add_annotation(x=t, y=c, text=_fmt_vol(t), showarrow=False,
                           xanchor="left", xshift=8, yanchor="middle",
                           font=dict(size=GUTTER_FONT_PX, color=P.INK_SECONDARY))
    tmax = max(tot) if tot else 1.0
    fig.update_xaxes(title_text=AX_WORKS, range=[0, tmax * 1.18],
                     gridcolor=P.GRID, zerolinecolor=P.GRID, linecolor=P.BORDER)
    fig.update_yaxes(autorange="reversed", showgrid=False, automargin=True)
    return _base_layout(fig, row_height(len(cats), minimum=260),
                        margin=dict(t=BASE_PX // 2, l=8, r=70, b=BASE_PX))


def _series_offset_width(n: int, k: int, group_span: float, group_fill: float) -> tuple[float, float]:
    """Lorraine VIZ_SPEC_pass6 S1.5 geometry, VERBATIM.

    `offsetgroup` is BROKEN on the pinned plotly (5.24.1) -- under every
    `barmode` it stacks or overlaps instead of grouping -- so every grouped bar
    is positioned with an EXPLICIT `offset`/`width` under `barmode="overlay"`.
    Do not "simplify" this back to `offsetgroup`."""
    slot = group_span / n
    bar_w = slot * group_fill
    offset = -group_span / 2 + k * slot + (slot - bar_w) / 2
    return offset, bar_w


def fig_breakdown_yearly(
    years: Sequence[str],
    series: Sequence[str],
    labels: Mapping[str, str],
    colors: Mapping[str, str],
    totals: Mapping[str, Sequence[float]],
    *,
    group_span: float = DEFAULT_GROUP_SPAN,
    group_fill: float = DEFAULT_GROUP_FILL,
    y_title: str = AX_WORKS,
) -> go.Figure:
    """RIGHT panel of the pair: category x year GROUPED bars.

    GROUPED, never stacked -- Lorraine's standing rule, "a bar chart may never
    stack a second categorical dimension" (a stack would make the year total the
    figure and hide every series' own trajectory, which is the claim here).

    `years` must be STRINGS (a numeric x-axis autoranges and ticks differently
    from every other chart in the app). `series` is the FIXED semantic order --
    `palette.OA_DOMAIN_ORDER` for domains, `palette.DOCTYPE_ORDER` for document
    types -- never a data-dependent sort, and a series that is zero across every
    year is KEPT, never dropped, so the reader sees the absence.

    Both panels of the pair render `showlegend=False`: `chip_legend_html` is the
    ONE legend for the two figures."""
    if not all(isinstance(g, str) for g in years):
        raise ValueError("years must be strings")
    if len(series) == 0:
        raise ValueError("series must not be empty")
    missing = [k for k in series if k not in labels or k not in colors or k not in totals]
    if missing:
        raise ValueError(f"series key(s) missing from labels/colors/totals: {missing}")
    n_groups = len(years)
    for k in series:
        if len(totals[k]) != n_groups:
            raise ValueError(f"totals[{k!r}] must have one value per year")

    fig = go.Figure()
    for k, key in enumerate(series):
        offset, bar_w = _series_offset_width(len(series), k, group_span, group_fill)
        vals = [float(v) for v in totals[key]]
        hover = [f"{labels[key]}<br>{AX_YEAR.lower()}{THIN_SPACE}{g}"
                 f"<br>{AX_WORKS.lower()}{THIN_SPACE}{_fmt_vol(v)}"
                 for g, v in zip(years, vals)]
        fig.add_trace(go.Bar(
            x=list(years), y=vals, offset=offset, width=bar_w,
            marker_color=colors[key],
            marker_line_color=P.SURFACE, marker_line_width=HAIRLINE_PX,
            name=labels[key], legendgroup=key,
            customdata=hover, hovertemplate="%{customdata}<extra></extra>",
        ))
    fig.update_layout(barmode="overlay")
    fig.update_xaxes(type="category", gridcolor=P.GRID, linecolor=P.BORDER)
    fig.update_yaxes(title_text=y_title, gridcolor=P.GRID,
                     zerolinecolor=P.GRID, linecolor=P.BORDER)
    fig = _base_layout(fig, SCATTER_HEIGHT - BASE_PX * 2,
                       margin=dict(t=BASE_PX // 2, l=8, r=16, b=BASE_PX))
    fig.update_layout(bargap=0)   # explicit offsets already own the spacing
    return fig


# ---------------------------------------------------------------------------
# 7. The shared chip legend -- ONE legend for the breakdown pair
# ---------------------------------------------------------------------------
CHIP_PX = 12
CHIP_RADIUS_PX = 3
CHIP_GAP_PX = 6
CHIP_MARGIN_PX = 14
NO_PX = 0            # a literal zero belongs in an int, never inside a CSS string


def chip_legend_html(items: Sequence[tuple[str, str]]) -> str:
    """HTML chip strip (Lorraine `render_chip_legend`, de-Streamlit-ed: this
    module returns the markup and `views_find.py` is the only caller that hands
    it to `st.markdown(..., unsafe_allow_html=True)`).

    ONE legend serves BOTH figures of the breakdown pair, which is why both are
    built with `showlegend=False`; the strip is rebuilt whenever the segmented
    control swaps the identity family, so a legend never mixes two families
    (palette.py coexistence rule)."""
    def esc(s: str) -> str:
        return (str(s).replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))

    chips = "".join(
        f'<span style="display:inline-flex;align-items:center;'
        f'margin-right:{CHIP_MARGIN_PX}px;">'
        f'<span style="width:{CHIP_PX}px;height:{CHIP_PX}px;background:{esc(hexcol)};'
        f'border-radius:{CHIP_RADIUS_PX}px;margin-right:{CHIP_GAP_PX}px;"></span>'
        f'<span style="font-size:{FONT_PX}px;color:{P.INK_SECONDARY};">{esc(label)}</span>'
        f'</span>'
        for label, hexcol in items
    )
    return (f'<div style="display:flex;flex-wrap:wrap;gap:{HAIRLINE_PX}px;'
            f'margin:{CHIP_GAP_PX}px {NO_PX}px;">{chips}</div>')

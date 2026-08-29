"""BenchUp v3 -- pure Plotly figure builders for COMPARE and COLLABORATE
(Phase 2B, stream V).

Same contract as `lib/charts.py` and enforced by the same tests: NO Streamlit
import, NO `#RRGGBB` literal (every hue comes from `lib.palette`), NO digit
inside a string literal (`tests/test_charts_compare.py`, using the shared
read-only allowlist and the same "a deployed parquet column name is a data key,
not copy" exemption). Every function takes plain DataFrames / mappings and
returns a `plotly.graph_objects.Figure`; `lib/views_compare.py` and
`lib/views_collab.py` are the only places a figure reaches a page.

WHAT MAKES A COMPARE CHART DIFFERENT FROM A PROFILE CHART
---------------------------------------------------------
One rule, and everything below follows from it (2B-1): **the institution is the
only identity in the figure.** The categorical axis names the field, subfield,
panel, goal, quadrant or grey state; the COLOUR names the institution
(`palette.INSTITUTION_COLORS`, slots assigned by `palette.institution_slots`
from ascending `inst_key`, never from click order). A Compare figure therefore
never carries an OA-domain, ERC, SDG or document-type hue -- which is exactly
the disposition `palette_validation.txt` run 10 records, where the six
institution hues and the four OA hues FAIL as one ten-slot set.

THE FORM, AND WHY IT IS NOT GROUPED BARS
----------------------------------------
The obvious mirror of a profile panel is a grouped bar chart, N bars per
category. It was MEASURED and refused (wind-tunnel 2B claim #16, absorbed as
BUILD_PLAN_2B.md A4): at the shipped row pitch, 26 fields x 6 institutions is
2.6 px per bar. A bar thinner than its own outline is not a bar.

So the Compare mirror is a **dot row**: one row per category, one coloured dot
per institution on the share axis, the mass-paired specialisation dots in an
aligned second panel, and the volumes in the hover -- a gutter cannot hold six
numbers side by side, which is why A/B #4's volume gutter (the profile form)
does not carry over.

THE DODGE -- the mechanism that makes six dots in one row legible
-----------------------------------------------------------------
Six dots on one line collide whenever two institutions have a similar share.
The acceptance A4 sets is measurable: every mark at least `MIN_MARK_PX`, and no
two marks of one row overlapping by more than half. This module satisfies it BY
CONSTRUCTION rather than by hoping:

  * dots are `DOT_PX` across, above the >= 8 px marker floor of the dataviz mark
    specs, and carry the 2 px SURFACE ring that spec asks for on overlapping
    marks;
  * when any row of the frame would put two marks closer than `OVERLAP_MAX` x
    `DOT_PX`, EVERY row splits into LANES -- one lane per institution, in slot
    order, `LANE_PITCH_PX` apart -- and the row's own band grows to hold them
    (`compare_row_height`);
  * a lane is the SAME lane in every row. That is the whole reason the split is
    all-or-nothing rather than per-row: a greedy per-row dodge is more compact,
    but then institution 3 sits second from the top here and fourth there, and a
    vertical position that changes meaning row by row is worse than the overlap
    it fixed. With a fixed lane the reader can also scan ONE institution down
    the panel, which the single-line form does not allow at all;
  * a frame that needs no dodge keeps the single line and is then exactly as
    tall as the profile panel it mirrors.

Because a builder cannot know the pixel width of a Streamlit column, the
collision test converts data units to pixels at a REFERENCE width,
`REF_PLOT_WIDTH_PX`, taken from the R1 render measurements of this very app.
The render proof measures the real thing.

WHAT IS DELIBERATELY *NOT* CARRIED OVER FROM `charts.py`
--------------------------------------------------------
  * the volume gutter (A/B #4) -- six numbers do not fit in one gutter column;
    volumes move to the hover, and the panel's own CSV/xlsx export carries them
    for the reader who wants the numbers (2B-13);
  * the SI lollipop STEM -- one stem per institution per row is a hairball at
    k = 6; the dashed reference at the neutral value and the unit grid stay,
    because they are what makes a dot's position readable without a stem;
  * `showlegend` -- every figure here is legend-free and `institution_legend_html`
    is the ONE legend for a whole view, exactly as `charts.chip_legend_html`
    serves the breakdown pair. That legend is not optional: it is the secondary
    encoding the validator's deutan 7.6 WARN obliges (palette_validation.txt
    run 9).
"""
from __future__ import annotations

import math
from typing import Mapping, Sequence

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from lib import charts as C
from lib import palette as P

# ---------------------------------------------------------------------------
# Geometry. Ints and floats only -- never a digit inside a string literal.
# ---------------------------------------------------------------------------
DOT_PX = 12                 # institution mark diameter. Above the >= 8 px marker
                            # floor of the dataviz mark specs even after the 2 px
                            # SURFACE ring eats into the visible disc.
MIN_MARK_PX = 8             # the A4 acceptance floor, kept as a constant so the
                            # test and the render harness assert the same number
OVERLAP_MAX = 0.5           # A4: no two marks of one row may overlap by more
                            # than half their own diameter
MIN_SEP_PX = DOT_PX * OVERLAP_MAX
LANE_PITCH_PX = 10          # vertical distance between two lanes. Above the
                            # MIN_SEP_PX acceptance floor with margin: two marks
                            # in adjacent lanes at the SAME share are 10 px
                            # apart, i.e. they overlap by (DOT_PX - 10) / DOT_PX,
                            # a sixth of a dot -- a third of what the acceptance
                            # allows, and the 2 px SURFACE ring keeps both
                            # outlines whole.
REF_PLOT_WIDTH_PX = 880     # reference plot-area width for the collision test.
                            # MEASURED, not guessed: the R1 A/B render of the
                            # two-panel share + SI figure reported a 549 px share
                            # sub-panel inside a 1120 px figure at a 1280 px
                            # viewport (design-system/ab/AB_VERDICT.md), and
                            # 880 x SHARE_PANEL_FRAC = 546.
SHARE_PANEL_FRAC = 0.62     # the two-panel split, same proportions as
SI_PANEL_FRAC = 0.38        # `charts.fig_share_si`, so the two forms line up
PANEL_GAP = 0.04

INTERVAL_PX = 2             # dot-interval whisker thickness (dataviz: 2 px line)
TRENDS_COLS = 3             # small-multiples grid width
TRENDS_PANEL_PX = 190       # one trends small-multiple panel's height
TRENDS_ROW_GAP = 0.16       # vertical space between two rows of panels. Measured
                            # need, not taste: a wrapped two-line panel title is
                            # drawn ABOVE its panel, and at the plotly default it
                            # landed on the frame of the panel above it.
FRONTIER_PANEL_PX = 260     # one frontier small-multiple panel's height -- taller
                            # than a trends panel because a scatter needs its
                            # vertical range, where a line only needs its shape
TRENDS_LINE_PX = 2
TRENDS_MARKER_PX = 7
OVERLAY_BUBBLE_MIN_PX = MIN_MARK_PX   # the smallest topic bubble. `charts`
                            # uses 6 px for the single-institution frontier
                            # plot; an overlay of six institutions is denser and
                            # its smallest mark still has to clear the A4 floor,
                            # so this module raises its own minimum instead of
                            # editing a builder it does not own.
OVERLAY_OPACITY = 0.72      # scatter marks overlap by nature; a wash lets a
                            # dense cluster still show its parts. A float, so it
                            # composites over SURFACE and stays inside the
                            # one-family rule (same argument as MUTED_OPACITY).
ZEBRA_OPACITY = 0.55        # alternate-row band, drawn only when a frame needs
                            # more than one lane (it is what makes a lane read as
                            # "still the same row")
STRIP_ROW_MIN_PX = 200

MIRROR_FAMILIES = ("oa", "erc", "sdg")
NOT_SCORED = "not_frontier_scored"

# ---------------------------------------------------------------------------
# Vocabulary. Digit-free by construction; a caller that wants different wording
# passes `labels=` (stream N owns the page copy, this is only the fallback).
# ---------------------------------------------------------------------------
AX_PP = "Publications in the world top decile"
AX_INSTITUTION = "Institution"
AX_QUADRANT = "Frontier quadrant"
AX_STATE = "Share of fractional output"

HOVER_INTERVAL = "interval"
RANGE_SEP = "\N{EN DASH}"   # between the two ends of a rendered interval
HOVER_QUADRANT = "quadrant"
HOVER_NOT_ALL = "not held by every compared institution"

QUADRANT_ORDER = ("accelerating_expansion", "decelerating_expansion",
                  "accelerating_contraction", "decelerating_contraction",
                  NOT_SCORED)
QUADRANT_LABELS = {
    "accelerating_expansion": "Accelerating expansion",
    "decelerating_expansion": "Decelerating expansion",
    "accelerating_contraction": "Accelerating contraction",
    "decelerating_contraction": "Decelerating contraction",
    NOT_SCORED: "Not frontier-scored",
}

STATE_LABELS = {
    "classified_eligible": "Classified, eligible",
    "title_only": "Title only, no abstract",
    "lang_uncertain": "Language uncertain",
    "untranslated_grey": "Untranslated",
    "unusable": "Unusable text",
    "retracted_excluded": "Retracted",
}

_KEY_COLS = {
    "oa": ("subfield_id", "field_id", "topic_id"),
    "erc": ("panel_idx", "panel_code"),
    "sdg": ("sdg_idx", "sdg_number"),
}
_VOLUME_COLS = ("vol_full", "vol_frac", "mass", "n_works_full")


# ---------------------------------------------------------------------------
# Small pure helpers
# ---------------------------------------------------------------------------
def compare_row_height(n_rows: int, lanes: int = 1, n_wrapped: int = 0,
                       minimum: int = C.MIN_HEIGHT) -> int:
    """`charts.row_height` extended for the lane dodge.

    One lane reproduces the profile pitch EXACTLY (so an undodged mirror is the
    same height as the profile panel it mirrors). A dodged frame grows by the
    SHORTFALL between the profile pitch and what the lane stack actually needs,
    per row -- never by a multiple of the whole row budget, which is what made
    the first draft of this a 2,852 px Fields panel."""
    base = C.row_height(n_rows, minimum=minimum, n_wrapped=n_wrapped)
    lanes = max(int(lanes), 1)
    if lanes == 1:
        return base
    shortfall = max(0, lanes * LANE_PITCH_PX - C.ROW_PX)
    return int(base + shortfall * int(n_rows))


def _slot_of(slots: Mapping, iid) -> int:
    try:
        return int(slots[iid])
    except (KeyError, TypeError, ValueError):
        return len(P.INSTITUTION_COLORS)   # -> COMPARISON grey, never a cycle


def _name_of(names: Mapping | None, iid) -> str:
    if names and iid in names:
        return str(names[iid])
    return str(iid)


def _ordered_ids(df: pd.DataFrame, slots: Mapping) -> list:
    """The compared institutions in SLOT order -- the one order every figure,
    legend and hover in this module uses, so a colour always sits in the same
    position of a legend and of a lane stack."""
    ids = list(dict.fromkeys(df["institution_id"].tolist()))
    return sorted(ids, key=lambda i: (_slot_of(slots, i), str(i)))


def _sep_units(vmin: float, vmax: float, panel_frac: float) -> float:
    """`MIN_SEP_PX` converted into the panel's own data units at the reference
    width. A degenerate range (every value identical) collapses to "everything
    collides", which is the safe answer: the dodge then gives each institution
    its own lane."""
    span = float(vmax) - float(vmin)
    width = REF_PLOT_WIDTH_PX * panel_frac
    if not np.isfinite(span) or span <= 0 or width <= 0:
        return math.inf
    return MIN_SEP_PX * span / width


def _needs_dodge(values_by_row: Sequence[Sequence[Sequence[float]]],
                 seps: Sequence[float]) -> bool:
    """Does ANY row of this frame put two marks closer than the acceptance
    allows? All-or-nothing on purpose (see the module docstring): the answer
    decides whether the WHOLE figure is single-line or lane-split, so a lane
    means the same thing in every row of the figure."""
    for row in values_by_row:
        for i in range(len(row)):
            for j in range(i + 1, len(row)):
                if _conflicts(row[i], row[j], seps):
                    return True
    return False


def _conflicts(a: Sequence[float], b: Sequence[float], seps: Sequence[float]) -> bool:
    for va, vb, sep in zip(a, b, seps):
        if not (np.isfinite(va) and np.isfinite(vb)):
            continue
        if not np.isfinite(sep) or abs(float(va) - float(vb)) < sep:
            return True
    return False


def _mark_state(row: pd.Series, volume_col: str | None) -> str:
    """solid / thin / none -- the profile's own `si_status` rule (L34), with the
    zero-volume override that fixed the ERC display bug: a panel with no
    publications cannot have a specialisation reading, whatever the status
    column says."""
    if volume_col and volume_col in row.index:
        vol = pd.to_numeric(pd.Series([row[volume_col]]), errors="coerce").iloc[0]
        if np.isfinite(vol) and np.isclose(float(vol), 0.0):
            return "none"
    status = str(row["si_status"]).strip().lower() if "si_status" in row.index else "solid"
    if status in ("solid", "thin", "none"):
        return status
    return "solid"


def _first_col(df: pd.DataFrame, candidates: Sequence[str]) -> str | None:
    return C._first_col(df, candidates)


def _num(v) -> float:
    """Anything -> a PYTHON float (NaN when it will not convert).

    `charts._fmt_*` test `isinstance(v, float)` before deciding a value is
    missing, and `np.float32('nan')` is not an instance of `float` -- it would
    print as a formatted NaN instead of `palette.NA_MARK`. Every value this
    module hands to a formatter goes through here first."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return float("nan")
    return f


def _fmt_pct(v) -> str:
    return C._fmt_pct(_num(v))


def _fmt_si(v) -> str:
    return C._fmt_si(_num(v))


def _fmt_vol(v) -> str:
    return C._fmt_vol(_num(v))


def _fmt_frontier(v) -> str:
    return C._fmt_frontier(_num(v))


def _zebra(fig: go.Figure, n_rows: int, x0: float, x1: float, *, row=None, col=None) -> None:
    for i in range(0, n_rows, 2):
        fig.add_shape(type="rect", x0=x0, x1=x1, y0=i - 0.5, y1=i + 0.5,
                      xref="x domain", line=dict(width=0), fillcolor=P.NEUTRAL,
                      opacity=ZEBRA_OPACITY, layer="below", row=row, col=col)


def _y_axis(fig: go.Figure, n_rows: int, ticktext: Sequence[str], **kw) -> None:
    fig.update_yaxes(tickmode="array", tickvals=list(range(n_rows)),
                     ticktext=list(ticktext), range=[n_rows - 0.5, -0.5],
                     showgrid=False, automargin=True, **kw)


# ---------------------------------------------------------------------------
# 1. The mirror -- fields / subfields / ERC panels / SDG goals (3.2-3.5)
# ---------------------------------------------------------------------------
def fig_mirror_dots(
    df: pd.DataFrame,
    *,
    family: str = "oa",
    slots: Mapping,
    sort: str = "volume",
    si: bool = True,
    names: Mapping | None = None,
    share_col: str = "share",
    si_col: str = "si",
    label_col: str | None = None,
    key_col: str | None = None,
    volume_col: str | None = None,
    si_axis_title: str | None = None,
    si_hover_label: str | None = None,
) -> go.Figure:
    """The Compare mirror of a profile share + SI panel, for N institutions.

    LEFT   one row per field / subfield / ERC panel / SDG goal; one dot per
           institution at its share, coloured by the institution's slot.
    RIGHT  the same rows, the same lanes, one dot per institution at its
           specialisation index, against the dashed neutral reference and the
           unit grid the profile panel uses (2B-2: an SI mark never appears
           without its mass, and it sits in the row its share sits in).

    `family` chooses the label column, the taxonomy sort keys and the SI
    vocabulary -- it does NOT choose a colour. Colour is the institution and
    only the institution (2B-1).

    Mark rules, inherited unchanged from the profile so the two sections read as
    one system: `si_status == "solid"` -> filled dot; `"thin"` -> hollow dot
    (SURFACE fill, institution-coloured outline), disclosing a below-the-floor
    cell instead of erasing it; `"none"`, a NaN value, or a ZERO volume -> no
    mark at all and `palette.NA_MARK` in that institution's hover line.
    """
    if family not in MIRROR_FAMILIES:
        raise ValueError(f"family must be one of {MIRROR_FAMILIES}, got {family!r}")
    if sort not in C.SORTS:
        raise ValueError(f"sort must be one of {C.SORTS}, got {sort!r}")
    for required in ("institution_id", share_col):
        if required not in df.columns:
            raise ValueError(f"missing column {required!r}")

    d = df.copy()
    label_col = label_col or _first_col(d, C._LABEL_COLS)
    if label_col is None:
        raise ValueError("no label column found; pass label_col=")
    key_col = key_col or _first_col(d, _KEY_COLS[family]) or label_col
    volume_col = volume_col or _first_col(d, _VOLUME_COLS)
    si_axis_title = si_axis_title or (C.AX_ESI if family == "sdg" else C.AX_SI)
    si_hover_label = si_hover_label or (C.HOVER_ESI if family == "sdg" else C.HOVER_SI)

    ids = _ordered_ids(d, slots)
    rows = _row_order(d, family, sort, key_col, label_col, share_col)
    n = len(rows)
    if n == 0:
        raise ValueError("no rows to draw")

    cells = {(r[key_col], r["institution_id"]): r for _, r in d.iterrows()}

    share_max = float(pd.to_numeric(d[share_col], errors="coerce").max())
    share_max = share_max if np.isfinite(share_max) and share_max > 0 else 1.0
    si_vals = pd.to_numeric(d[si_col], errors="coerce") if si_col in d.columns else pd.Series(dtype=float)
    si_max = float(si_vals.max()) if len(si_vals) and np.isfinite(si_vals.max()) else C.SI_NEUTRAL
    si_max = max(si_max, C.SI_NEUTRAL)

    seps = [_sep_units(0.0, share_max, SHARE_PANEL_FRAC),
            _sep_units(0.0, si_max, SI_PANEL_FRAC)]

    # --- one pass over the grid: marks, hovers, then ONE dodge decision ------
    grid: list[list[list[float]]] = []
    marks: list[dict] = []           # one dict per (row, institution) with a mark
    for ri, key in enumerate(rows[key_col].tolist()):
        vals = []
        for i, iid in enumerate(ids):
            row = cells.get((key, iid))
            if row is None:
                vals.append([np.nan, np.nan])
                continue
            sh = _num(row[share_col])
            sv = _num(row[si_col]) if si_col in row.index else float("nan")
            state = _mark_state(row, volume_col)
            show_si = bool(si and state != "none" and np.isfinite(sv))
            vals.append([sh, sv if show_si else float("nan")])
            marks.append(dict(ri=ri, slot_index=i, share=sh, si=sv, state=state,
                              show_si=show_si,
                              hover=_mirror_hover(row, iid, names, label_col, share_col,
                                                  si_col, volume_col, si_hover_label)))
        grid.append(vals)

    lane_count = len(ids) if _needs_dodge(grid, seps) else 1
    has_si = any(m["show_si"] for m in marks)

    if has_si:
        fig = make_subplots(rows=1, cols=2, shared_yaxes=True,
                            column_widths=[SHARE_PANEL_FRAC, SI_PANEL_FRAC],
                            horizontal_spacing=PANEL_GAP)
    else:
        fig = make_subplots(rows=1, cols=1)

    if lane_count > 1:
        _zebra(fig, n, 0.0, 1.0, row=1, col=1)
        if has_si:
            _zebra(fig, n, 0.0, 1.0, row=1, col=2)

    # ALL the share traces first, THEN all the SI traces: `fig.data[:k]` is the
    # share panel and `fig.data[k:]` is the specialisation panel, in slot order
    # both times. Interleaving them would work on screen and be a trap for every
    # test and every future reader.
    for i, iid in enumerate(ids):
        _add_dot_trace(fig, [m for m in marks if m["slot_index"] == i],
                       color=P.institution_color(_slot_of(slots, iid)),
                       lanes=lane_count, lane=i, value="share", row=1, col=1)
    if has_si:
        for i, iid in enumerate(ids):
            _add_dot_trace(fig, [m for m in marks if m["slot_index"] == i and m["show_si"]],
                           color=P.institution_color(_slot_of(slots, iid)),
                           lanes=lane_count, lane=i, value="si", row=1, col=2)

    pairs = [C._tick_display(str(v), None) for v in rows[label_col].tolist()]
    plain = [p for p, _ in pairs]
    styled = [s for _, s in pairs]
    n_wrapped = sum(1 for s in styled if "<br>" in s)
    _y_axis(fig, n, styled)

    fig.update_xaxes(range=[0, share_max * 1.02], tickvals=C._nice_ticks(share_max),
                     title_text=C.AX_SHARE, tickformat=C._AXIS_PCT_FMT, row=1, col=1)
    if has_si:
        si_ceil = max(int(C.SI_NEUTRAL), int(math.ceil(si_max)))
        fig.update_xaxes(title_text=si_axis_title, tickmode="array",
                         tickvals=[float(v) for v in range(1, si_ceil + 1)],
                         range=[0, si_max * 1.05], row=1, col=2)
        fig.add_vline(x=C.SI_NEUTRAL, row=1, col=2,
                      line=dict(color=P.INK_SECONDARY, width=C.HAIRLINE_PX, dash="dash"))
    fig.update_xaxes(gridcolor=P.GRID, zerolinecolor=P.GRID, linecolor=P.BORDER)

    height = compare_row_height(n, lane_count, n_wrapped=n_wrapped)
    return C._base_layout(fig, height,
                          margin=dict(t=C.BASE_PX // 2, l=C._gutter_margin_px(plain),
                                      r=16, b=C.BASE_PX))


def _row_order(d: pd.DataFrame, family: str, sort: str, key_col: str,
               label_col: str, share_col: str) -> pd.DataFrame:
    """One row per category, ordered.

    `sort="volume"` ranks by the share SUMMED ACROSS THE COMPARED SET, which is
    A3's ruling: the INTERSECTION of per-institution top lists yields one
    subfield at k = 6 (measured), so "shared" has to mean "large in the set as a
    whole", not "in everybody's own top". `sort="taxonomy"` uses the family's
    own hierarchy and never moves with the data."""
    first = d.drop_duplicates(subset=[key_col]).set_index(key_col)
    summed = (d.assign(_v=pd.to_numeric(d[share_col], errors="coerce").fillna(0.0))
                .groupby(key_col, sort=False)["_v"].sum())
    out = pd.DataFrame({key_col: summed.index, "_summed": summed.to_numpy()})
    out[label_col] = [first.loc[k, label_col] for k in out[key_col]]
    if sort == "volume":
        return out.sort_values("_summed", ascending=False, kind="mergesort").reset_index(drop=True)
    keys = C._taxonomy_keys(d, family)
    keys = [k for k in keys if k in d.columns]
    if not keys:
        return out.reset_index(drop=True)
    order = (d.drop_duplicates(subset=[key_col])
              .sort_values(keys, kind="mergesort")[key_col].tolist())
    rank = {k: i for i, k in enumerate(order)}
    out["_rank"] = [rank.get(k, len(rank)) for k in out[key_col]]
    return out.sort_values("_rank", kind="mergesort").drop(columns="_rank").reset_index(drop=True)


def _mirror_hover(row: pd.Series, iid, names, label_col, share_col, si_col,
                  volume_col, si_hover_label) -> str:
    parts = [_name_of(names, iid), str(row[label_col]),
             f"{C.HOVER_SHARE}{C.THIN_SPACE}{_fmt_pct(row[share_col])}"]
    if volume_col and volume_col in row.index:
        lab = (C.HOVER_VOL_FULL if volume_col == "vol_full"
               else C.HOVER_VOL_FRAC if volume_col == "vol_frac" else C.HOVER_MASS)
        parts.append(f"{lab}{C.THIN_SPACE}{_fmt_vol(row[volume_col])}")
    if si_col in row.index:
        parts.append(f"{si_hover_label}{C.THIN_SPACE}{_fmt_si(row[si_col])}")
    return "<br>".join(parts)


def _lane_offset(lane: int, lanes: int) -> float:
    """Where institution `lane` sits inside its category band, in category
    units. The band is one unit tall, the lanes are centred in it, and the
    institution's lane index is its SLOT position -- so slot 1 is always the top
    lane of every row and slot 6 always the bottom one.

    This is `charts._series_offset_width`'s geometry with a dot instead of a
    bar: same reason (an explicit offset, because plotly's own grouping is
    broken on the pinned version), same fixed series order."""
    if lanes <= 1:
        return 0.0
    return (lane - (lanes - 1) / 2.0) / lanes


def _add_dot_trace(fig, marks, *, color: str, lanes: int, lane: int,
                   value: str, row: int, col: int) -> None:
    """ONE trace per institution per panel -- a mirror's trace count is exactly
    (number of institutions) x (number of panels), which is what
    `tests/test_charts_compare.py` pins.

    Solid / hollow is per POINT inside the one trace (per-point `marker.color`
    and `marker.line.color` arrays, the idiom `charts.fig_share_si` already
    uses), so a below-the-floor cell is disclosed without a second legend
    entry."""
    offset = _lane_offset(lane, lanes)
    xs, ys, fills, lines, hovers = [], [], [], [], []
    for m in marks:
        v = m[value]
        if not np.isfinite(v):
            continue
        hollow = m["state"] == "thin"
        xs.append(v)
        ys.append(m["ri"] + offset)
        fills.append(P.SURFACE if hollow else color)
        lines.append(color if hollow else P.SURFACE)
        hovers.append(m["hover"])
    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode="markers",
        marker=dict(color=fills, size=DOT_PX,
                    line=dict(color=lines, width=P.OUTLINE_WIDTH)),
        customdata=hovers, hovertemplate="%{customdata}<extra></extra>",
        showlegend=False,
    ), row=row, col=col)


# ---------------------------------------------------------------------------
# 2. Frontier quadrant mix (3.6a)
# ---------------------------------------------------------------------------
def fig_quadrant_mix(df: pd.DataFrame, slots: Mapping, *, names: Mapping | None = None,
                     labels: Mapping | None = None, share_col: str = "share") -> go.Figure:
    """The frontier mix, one row per quadrant, one dot per institution.

    FIVE rows, not four (A2): the four quadrant shares sum to a median of 0.967
    and a minimum of 0.128, so a four-part figure would silently drop between
    3 % and 87 % of an institution's mass. The fifth row, "not frontier-scored",
    is the residual `frontier_excluded_share + frontier_unscored_share`; it is
    synthesised here from the residual when the frame does not already carry it,
    which is exactly the verified identity (quadrants + excluded + unscored = 1
    for all 7,557 institutions).

    A quadrant MISSING from an institution's packed string is drawn at zero and
    says so on hover -- one institution really does ship only three quadrants,
    and an absent row would read as "not measured" rather than "none"."""
    d = df.copy()
    if share_col not in d.columns or "quadrant" not in d.columns:
        raise ValueError("frame needs institution_id, quadrant and a share column")
    labels = dict(QUADRANT_LABELS, **(labels or {}))
    ids = _ordered_ids(d, slots)

    filled = []
    for iid in ids:
        mine = d[d["institution_id"] == iid]
        have = dict(zip(mine["quadrant"].astype(str),
                        pd.to_numeric(mine[share_col], errors="coerce").fillna(0.0)))
        scored = sum(v for k, v in have.items() if k != NOT_SCORED)
        residual = have.get(NOT_SCORED, max(0.0, 1.0 - scored))
        for q in QUADRANT_ORDER:
            filled.append({"institution_id": iid, "quadrant": q,
                           share_col: residual if q == NOT_SCORED else have.get(q, 0.0),
                           "_missing": q != NOT_SCORED and q not in have})
    grid_source = pd.DataFrame(filled)

    xmax = float(pd.to_numeric(grid_source[share_col], errors="coerce").max())
    xmax = xmax if np.isfinite(xmax) and xmax > 0 else 1.0
    sep = [_sep_units(0.0, xmax, 1.0)]

    fig = go.Figure()
    cells, grid = {}, []
    for ri, q in enumerate(QUADRANT_ORDER):
        vals = []
        for iid in ids:
            hit = grid_source[(grid_source["institution_id"] == iid)
                              & (grid_source["quadrant"] == q)]
            v = _num(hit.iloc[0][share_col]) if len(hit) else float("nan")
            vals.append([v])
            cells[(ri, iid)] = (v, bool(hit.iloc[0]["_missing"]) if len(hit) else False)
        grid.append(vals)
    lane_count = len(ids) if _needs_dodge(grid, sep) else 1

    if lane_count > 1:
        _zebra(fig, len(QUADRANT_ORDER), 0.0, 1.0)
    for i, iid in enumerate(ids):
        color = P.institution_color(_slot_of(slots, iid))
        offset = _lane_offset(i, lane_count)
        xs, ys, hovers = [], [], []
        for ri, q in enumerate(QUADRANT_ORDER):
            v, missing = cells[(ri, iid)]
            if not np.isfinite(v):
                continue
            xs.append(v)
            ys.append(ri + offset)
            parts = [_name_of(names, iid), labels[q],
                     f"{C.HOVER_SHARE}{C.THIN_SPACE}{_fmt_pct(v)}"]
            if missing:
                parts.append(f"{HOVER_QUADRANT}{C.THIN_SPACE}{P.NA_MARK}")
            hovers.append("<br>".join(parts))
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="markers",
            marker=dict(color=color, size=DOT_PX,
                        line=dict(color=P.SURFACE, width=P.OUTLINE_WIDTH)),
            customdata=hovers, hovertemplate="%{customdata}<extra></extra>",
            showlegend=False))

    styled = [C.wrap_label(labels[q]) for q in QUADRANT_ORDER]
    _y_axis(fig, len(QUADRANT_ORDER), styled)
    fig.update_xaxes(range=[0, xmax * 1.02], tickvals=C._nice_ticks(xmax),
                     title_text=C.AX_SHARE, tickformat=C._AXIS_PCT_FMT,
                     gridcolor=P.GRID, zerolinecolor=P.GRID, linecolor=P.BORDER)
    plain = [s.replace("<br>", "\n") for s in styled]
    height = compare_row_height(len(QUADRANT_ORDER), lane_count, minimum=STRIP_ROW_MIN_PX)
    return C._base_layout(fig, height,
                          margin=dict(t=C.BASE_PX // 2, l=C._gutter_margin_px(plain),
                                      r=16, b=C.BASE_PX))


# ---------------------------------------------------------------------------
# 3. Frontier overlay scatter (3.6b)
# ---------------------------------------------------------------------------
def fig_frontier_overlay(
    df: pd.DataFrame,
    slots: Mapping,
    *,
    names: Mapping | None = None,
    x_col: str = "expansion_latest",
    y_col: str = "acceleration_latest",
    size_col: str | None = None,
    label_col: str = "topic_name",
) -> go.Figure:
    """Every compared institution's topics in one Expansion x Acceleration
    plane, one trace (and one colour) per institution.

    **SECONDARY MODE, not the default.** A/B #6 measured this form against
    `fig_frontier_small_multiples` on the six real institutions at 1280 px and
    the overlay LOST: 90.7 % of its marks have their centre covered by a mark of
    a different institution (62.6 % at k = 2, 78.0 % at k = 3, 85.7 % even in the
    sparser top-quartile mode), against 0.0 % faceted. The dataviz series ladder
    predicted exactly this -- an all-pairs form caps at three series -- and the
    render confirms it. It is kept because the single plane answers one question
    the facets cannot ("whose topics sit furthest out, over everybody"), and
    because opacity plus the per-mark hover still make an individual bubble
    identifiable on demand; the caller's caption carries the occlusion figure so
    the reader is told what the picture is hiding.

    Rows with no frontier score are DROPPED and must be counted in the caller's
    caption -- the panel states what it could not place. A top-quartile topic
    keeps its institution colour and takes an INK outline: a SHAPE signal, never
    a second hue."""
    size_col = size_col or _first_col(df, _VOLUME_COLS)
    d = df.copy()
    d = d[np.isfinite(pd.to_numeric(d[x_col], errors="coerce"))
          & np.isfinite(pd.to_numeric(d[y_col], errors="coerce"))].reset_index(drop=True)
    mass_all = (pd.to_numeric(d[size_col], errors="coerce").fillna(0.0)
                if size_col else pd.Series(np.ones(len(d))))
    mmax = float(mass_all.max()) if len(mass_all) and mass_all.max() > 0 else 1.0

    fig = go.Figure()
    for iid in (_ordered_ids(d, slots) if len(d) else []):
        fig.add_trace(_frontier_trace(d[d["institution_id"] == iid], iid, slots, names,
                                      x_col, y_col, size_col, label_col, mmax))
    fig.add_vline(x=C.FRONTIER_ORIGIN, line=dict(color=P.GRID, width=C.HAIRLINE_PX))
    fig.add_hline(y=C.FRONTIER_ORIGIN, line=dict(color=P.GRID, width=C.HAIRLINE_PX))
    fig.update_xaxes(title_text=C.AX_EXPANSION, gridcolor=P.GRID,
                     zerolinecolor=P.GRID, linecolor=P.BORDER)
    fig.update_yaxes(title_text=C.AX_ACCELERATION, gridcolor=P.GRID,
                     zerolinecolor=P.GRID, linecolor=P.BORDER)
    return C._base_layout(fig, C.SCATTER_HEIGHT,
                          margin=dict(t=C.BASE_PX // 2, l=8, r=16, b=C.BASE_PX))


def _frontier_trace(mine: pd.DataFrame, iid, slots, names, x_col, y_col,
                    size_col, label_col, mmax: float) -> go.Scatter:
    """One institution's topic cloud. Area = mass on the current basis, on the
    SAME scale for every institution (`mmax` is the whole frame's maximum, not
    the panel's), so a small institution's panel is not silently magnified."""
    color = P.institution_color(_slot_of(slots, iid))
    mass = (pd.to_numeric(mine[size_col], errors="coerce").fillna(0.0).to_numpy(dtype=float)
            if size_col else np.ones(len(mine)))
    sizes = OVERLAY_BUBBLE_MIN_PX + (C.BUBBLE_MAX_PX - OVERLAY_BUBBLE_MIN_PX) * np.sqrt(mass / mmax)
    top = (mine["top25pct_frontier"].fillna(False).to_numpy(dtype=bool)
           if "top25pct_frontier" in mine.columns else np.zeros(len(mine), dtype=bool))
    hovers = []
    for _, r in mine.iterrows():
        parts = [_name_of(names, iid), str(r[label_col]),
                 f"{C.HOVER_EXPANSION}{C.THIN_SPACE}{_fmt_frontier(r[x_col])}",
                 f"{C.HOVER_ACCELERATION}{C.THIN_SPACE}{_fmt_frontier(r[y_col])}"]
        if size_col:
            parts.append(f"{C.HOVER_MASS}{C.THIN_SPACE}{_fmt_vol(r[size_col])}")
        hovers.append("<br>".join(parts))
    return go.Scatter(
        x=mine[x_col].to_numpy(dtype=float), y=mine[y_col].to_numpy(dtype=float),
        mode="markers",
        marker=dict(color=color, size=sizes, sizemode="diameter",
                    opacity=OVERLAY_OPACITY,
                    line=dict(color=[P.INK if t else P.SURFACE for t in top],
                              width=[P.OUTLINE_WIDTH if t else C.HAIRLINE_PX for t in top])),
        customdata=hovers, hovertemplate="%{customdata}<extra></extra>",
        showlegend=False)


def fig_frontier_small_multiples(
    df: pd.DataFrame,
    slots: Mapping,
    *,
    names: Mapping | None = None,
    x_col: str = "expansion_latest",
    y_col: str = "acceleration_latest",
    size_col: str | None = None,
    label_col: str = "topic_name",
    n_cols: int = TRENDS_COLS,
) -> go.Figure:
    """The SHIPPED default for the frontier view -- A/B #6's winner, on measured
    grounds and not on taste (VIZ_SPEC section 6).

    One panel per institution, all panels on the SAME expansion x acceleration
    axes and the same bubble scale, so the panels are comparable as shapes: a
    cloud that sits further right really is further right.

    Why it beats the overlay: in the overlay, 90.7 % of marks have their centre
    covered by a mark of a DIFFERENT institution at k = 6 (measured on the six
    real institutions at 1280 px, 1,145 topic bubbles). The figure that carries
    institution identity by colour cannot afford to bury nine marks in ten
    behind another institution's. Faceting takes that number to 0.0 by
    construction, and it stays 0.0 at any k.

    The overlay is kept (`fig_frontier_overlay`) as an explicitly secondary
    mode for the reader who wants the single plane, with the occlusion figure
    in its caption."""
    size_col = size_col or _first_col(df, _VOLUME_COLS)
    d = df.copy()
    d = d[np.isfinite(pd.to_numeric(d[x_col], errors="coerce"))
          & np.isfinite(pd.to_numeric(d[y_col], errors="coerce"))].reset_index(drop=True)
    ids = _ordered_ids(d, slots) if len(d) else []
    if not ids:
        raise ValueError("no scored topics to draw")
    mass_all = (pd.to_numeric(d[size_col], errors="coerce").fillna(0.0)
                if size_col else pd.Series(np.ones(len(d))))
    mmax = float(mass_all.max()) if len(mass_all) and mass_all.max() > 0 else 1.0

    n_rows = int(math.ceil(len(ids) / max(n_cols, 1)))
    fig = make_subplots(rows=n_rows, cols=n_cols, shared_xaxes=True, shared_yaxes=True,
                        subplot_titles=[C.wrap_label(_name_of(names, i), width=C.WRAP_WIDTH // 2)
                                        for i in ids],
                        horizontal_spacing=0.04, vertical_spacing=0.09)
    for k, iid in enumerate(ids):
        r, c = k // n_cols + 1, k % n_cols + 1
        fig.add_trace(_frontier_trace(d[d["institution_id"] == iid], iid, slots, names,
                                      x_col, y_col, size_col, label_col, mmax), row=r, col=c)
        fig.add_vline(x=C.FRONTIER_ORIGIN, line=dict(color=P.GRID, width=C.HAIRLINE_PX),
                      row=r, col=c)
        fig.add_hline(y=C.FRONTIER_ORIGIN, line=dict(color=P.GRID, width=C.HAIRLINE_PX),
                      row=r, col=c)
    fig.update_xaxes(gridcolor=P.GRID, zerolinecolor=P.GRID, linecolor=P.BORDER,
                     tickfont=dict(size=C.GUTTER_FONT_PX))
    fig.update_yaxes(gridcolor=P.GRID, zerolinecolor=P.GRID, linecolor=P.BORDER,
                     tickfont=dict(size=C.GUTTER_FONT_PX))
    # same trap as the trends grid: `shared_*axes` links a row / a column, not
    # the whole grid, and two frontier panels on different scales would put the
    # same topic in two different places
    fig.update_xaxes(matches="x")
    fig.update_yaxes(matches="y")
    fig.update_xaxes(title_text=C.AX_EXPANSION, row=n_rows, col=1)
    fig.update_yaxes(title_text=C.AX_ACCELERATION, row=n_rows, col=1)
    fig.update_annotations(font=dict(size=C.GUTTER_FONT_PX, color=P.INK_SECONDARY))
    return C._base_layout(fig, n_rows * FRONTIER_PANEL_PX + C.BASE_PX * 2,
                          margin=dict(t=C.BASE_PX // 2, l=8, r=16, b=C.BASE_PX))


# ---------------------------------------------------------------------------
# 4. Impact -- index level (3.7a)
# ---------------------------------------------------------------------------
def fig_impact_intervals(
    df: pd.DataFrame,
    slots: Mapping,
    *,
    names: Mapping | None = None,
    value_col: str = "pp",
    low_col: str = "ci_low",
    high_col: str = "ci_high",
    sort: str = "volume",
) -> go.Figure:
    """One dot-interval row per institution: the point estimate with its
    rendered bootstrap interval.

    The interval is the point of the panel, not decoration -- a PP difference
    smaller than the overlap of two intervals is not a finding, and drawing the
    dots without them would invite exactly that read. `sort="volume"` ranks by
    the estimate, `sort="taxonomy"` keeps the stable slot order; the COLOUR
    never moves with the sort."""
    if sort not in C.SORTS:
        raise ValueError(f"sort must be one of {C.SORTS}, got {sort!r}")
    d = df.copy()
    d["_slot"] = [_slot_of(slots, i) for i in d["institution_id"]]
    d["_v"] = pd.to_numeric(d[value_col], errors="coerce")
    d = (d.sort_values("_v", ascending=False, kind="mergesort") if sort == "volume"
         else d.sort_values("_slot", kind="mergesort")).reset_index(drop=True)
    n = len(d)

    fig = go.Figure()
    for ri, r in d.iterrows():
        color = P.institution_color(int(r["_slot"]))
        lo = pd.to_numeric(pd.Series([r.get(low_col, np.nan)]), errors="coerce").iloc[0]
        hi = pd.to_numeric(pd.Series([r.get(high_col, np.nan)]), errors="coerce").iloc[0]
        hover = _impact_hover(r, r["institution_id"], names, value_col, low_col, high_col)
        if np.isfinite(lo) and np.isfinite(hi):
            fig.add_trace(go.Scatter(x=[lo, hi], y=[ri, ri], mode="lines",
                                     line=dict(color=color, width=INTERVAL_PX),
                                     hoverinfo="skip", showlegend=False))
        if np.isfinite(r["_v"]):
            fig.add_trace(go.Scatter(
                x=[float(r["_v"])], y=[ri], mode="markers",
                marker=dict(color=color, size=DOT_PX,
                            line=dict(color=P.SURFACE, width=P.OUTLINE_WIDTH)),
                customdata=[hover], hovertemplate="%{customdata}<extra></extra>",
                showlegend=False))

    styled = [C.wrap_label(_name_of(names, i)) for i in d["institution_id"]]
    n_wrapped = sum(1 for t in styled if "<br>" in t)
    _y_axis(fig, n, styled)
    hi_all = pd.to_numeric(d.get(high_col, d["_v"]), errors="coerce")
    xmax = float(np.nanmax([hi_all.max(), d["_v"].max()]))
    xmax = xmax if np.isfinite(xmax) and xmax > 0 else 1.0
    fig.update_xaxes(range=[0, xmax * 1.08], tickvals=C._nice_ticks(xmax),
                     title_text=AX_PP, tickformat=C._AXIS_PCT_FMT,
                     gridcolor=P.GRID, zerolinecolor=P.GRID, linecolor=P.BORDER)
    plain = [s.replace("<br>", "\n") for s in styled]
    return C._base_layout(fig, compare_row_height(n, 1, n_wrapped=n_wrapped, minimum=STRIP_ROW_MIN_PX),
                          margin=dict(t=C.BASE_PX // 2, l=C._gutter_margin_px(plain),
                                      r=16, b=C.BASE_PX))


def _impact_hover(r, iid, names, value_col, low_col, high_col) -> str:
    parts = [_name_of(names, iid), f"{AX_PP.lower()}{C.THIN_SPACE}{_fmt_pct(r.get(value_col))}"]
    lo, hi = r.get(low_col), r.get(high_col)
    if lo is not None and hi is not None:
        parts.append(f"{HOVER_INTERVAL}{C.THIN_SPACE}{_fmt_pct(lo)}"
                     f"{C.THIN_SPACE}{RANGE_SEP}{C.THIN_SPACE}{_fmt_pct(hi)}")
    for col, lab in (("pp_denominator_frac", C.HOVER_MASS), ("n_works_full", C.HOVER_VOL_FULL)):
        if col in getattr(r, "index", []):
            parts.append(f"{lab}{C.THIN_SPACE}{_fmt_vol(r[col])}")
    return "<br>".join(parts)


# ---------------------------------------------------------------------------
# 5. Impact -- per subfield, the UNION (3.7b)
# ---------------------------------------------------------------------------
def fig_impact_subfields(
    df: pd.DataFrame,
    slots: Mapping,
    *,
    names: Mapping | None = None,
    value_col: str = "pp",
    low_col: str = "ci_low",
    high_col: str = "ci_high",
    label_col: str = "subfield_name",
    key_col: str = "subfield_id",
    sort: str = "volume",
) -> go.Figure:
    """Per-subfield impact as dot-interval rows, over the UNION of the subfields
    any compared institution clears (A1, which refuted the intersection: only
    3,342 of 7,557 institutions have ANY floor-30 cell, the median is 2, and
    40 of 40 random four-tuples intersect to zero).

    A missing cell is therefore the NORMAL case, not an error, and it is drawn
    as NO MARK -- never a dot at zero, which would read as "no top-decile
    output" when the truth is "too few publications to estimate".

    Every institution gets its OWN lane here, unconditionally: an interval
    occupies a stretch of the axis rather than a point, so two intervals of one
    row overlap far more often than two dots do, and a collision test on the
    point estimates alone would not see it."""
    if sort not in C.SORTS:
        raise ValueError(f"sort must be one of {C.SORTS}, got {sort!r}")
    d = df.copy()
    d["_v"] = pd.to_numeric(d[value_col], errors="coerce")
    ids = _ordered_ids(d, slots)

    agg = d.groupby(key_col, sort=False)["_v"].mean()
    first = d.drop_duplicates(subset=[key_col]).set_index(key_col)
    rows = pd.DataFrame({key_col: agg.index, "_m": agg.to_numpy()})
    rows[label_col] = [first.loc[k, label_col] for k in rows[key_col]]
    rows = (rows.sort_values("_m", ascending=False, kind="mergesort") if sort == "volume"
            else rows.sort_values(key_col, kind="mergesort")).reset_index(drop=True)
    n = len(rows)
    lanes = max(len(ids), 1)

    cells = {(r[key_col], r["institution_id"]): r for _, r in d.iterrows()}
    fig = go.Figure()
    _zebra(fig, n, 0.0, 1.0)
    xmax = 0.0
    for i, iid in enumerate(ids):
        color = P.institution_color(_slot_of(slots, iid))
        xs, ys, hovers = [], [], []
        for ri, key in enumerate(rows[key_col].tolist()):
            r = cells.get((key, iid))
            if r is None:
                continue
            v = pd.to_numeric(pd.Series([r[value_col]]), errors="coerce").iloc[0]
            if not np.isfinite(v):
                continue
            y = ri + _lane_offset(i, lanes)
            lo = pd.to_numeric(pd.Series([r.get(low_col, np.nan)]), errors="coerce").iloc[0]
            hi = pd.to_numeric(pd.Series([r.get(high_col, np.nan)]), errors="coerce").iloc[0]
            if np.isfinite(lo) and np.isfinite(hi):
                fig.add_trace(go.Scatter(x=[lo, hi], y=[y, y], mode="lines",
                                         line=dict(color=color, width=INTERVAL_PX),
                                         hoverinfo="skip", showlegend=False))
                xmax = max(xmax, float(hi))
            xs.append(float(v))
            ys.append(y)
            xmax = max(xmax, float(v))
            hovers.append(str(r[label_col]) + "<br>"
                          + _impact_hover(r, iid, names, value_col, low_col, high_col))
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="markers",
            marker=dict(color=color, size=DOT_PX,
                        line=dict(color=P.SURFACE, width=P.OUTLINE_WIDTH)),
            customdata=hovers, hovertemplate="%{customdata}<extra></extra>",
            showlegend=False))

    pairs = [C._tick_display(str(v), None) for v in rows[label_col].tolist()]
    styled = [s for _, s in pairs]
    plain = [p for p, _ in pairs]
    _y_axis(fig, n, styled)
    xmax = xmax if xmax > 0 else 1.0
    fig.update_xaxes(range=[0, xmax * 1.05], tickvals=C._nice_ticks(xmax),
                     title_text=AX_PP, tickformat=C._AXIS_PCT_FMT,
                     gridcolor=P.GRID, zerolinecolor=P.GRID, linecolor=P.BORDER)
    n_wrapped = sum(1 for s in styled if "<br>" in s)
    return C._base_layout(fig, compare_row_height(n, lanes, n_wrapped=n_wrapped),
                          margin=dict(t=C.BASE_PX // 2, l=C._gutter_margin_px(plain),
                                      r=16, b=C.BASE_PX))


# ---------------------------------------------------------------------------
# 6. Trends -- subfield x year small multiples (3.8)
# ---------------------------------------------------------------------------
def fig_trends_small_multiples(
    frames_by_inst,
    slots: Mapping,
    subfields: Sequence,
    *,
    names: Mapping | None = None,
    value_col: str = "vol_full",
    label_col: str = "subfield_name",
    key_col: str = "subfield_id",
    year_col: str = "year",
    bonus_year: str | None = None,
    n_cols: int = TRENDS_COLS,
    shared_y: bool = True,
) -> go.Figure:
    """One small panel per subfield, one line per institution inside it.

    Small multiples is the RIGHT form here and a dot row is not: the reader's
    question is "who is growing in this subfield", which is a change-over-time
    read, and change over time is a line. The comparison across institutions
    then happens INSIDE a panel, where the lines share an axis.

    `shared_y=True` (the default) puts every panel on one scale, because
    unlinked panel scales are the classic small-multiples lie -- a flat panel
    and a steep panel would look alike. The consequence is real and is the
    caller's to handle: with raw volumes, a small institution's line hugs zero,
    so the caller is expected to pass an institution-normalised measure
    (`value_col`) rather than a raw count whenever institution SIZES differ by
    an order of magnitude, and to say which it passed in the caption.

    `bonus_year` names the partial final year (2B-5): its segment is drawn
    DOTTED and its point HOLLOW, so it is visibly not the same kind of
    observation as the years before it. The year itself is a caller-supplied
    string -- this module never names a year."""
    frames = (dict(frames_by_inst) if hasattr(frames_by_inst, "items")
              else {k: v for k, v in frames_by_inst})
    ids = sorted(frames, key=lambda i: (_slot_of(slots, i), str(i)))
    keys = list(subfields)
    n = len(keys)
    if n == 0:
        raise ValueError("no subfields to draw")
    n_rows = int(math.ceil(n / max(n_cols, 1)))

    titles, years = [], []
    for k in keys:
        title = str(k)
        for f in frames.values():
            hit = f[f[key_col] == k]
            if len(hit):
                title = str(hit.iloc[0][label_col])
                break
        titles.append(C.wrap_label(title, width=C.WRAP_WIDTH // 2))
    for f in frames.values():
        years.extend([str(y) for y in f[year_col].tolist()])
    years = sorted(dict.fromkeys(years))

    fig = make_subplots(rows=n_rows, cols=n_cols, subplot_titles=titles,
                        shared_xaxes=True, shared_yaxes=shared_y,
                        vertical_spacing=TRENDS_ROW_GAP, horizontal_spacing=0.06)

    for pi, key in enumerate(keys):
        r, c = pi // n_cols + 1, pi % n_cols + 1
        panel_title = titles[pi].replace("<br>", " ")
        for iid in ids:
            f = frames[iid]
            mine = f[f[key_col] == key].copy()
            if not len(mine):
                continue
            mine["_y"] = [str(v) for v in mine[year_col]]
            # sum, then reindex: a frame with two rows for one (subfield, year)
            # must not raise, and the only sensible reading of two rows is one
            # value -- never a silent drop of the second.
            series = (mine.assign(_v=pd.to_numeric(mine[value_col], errors="coerce"))
                          .groupby("_y", sort=False)["_v"].sum().reindex(years))
            vals = series.to_numpy(dtype=float)
            color = P.institution_color(_slot_of(slots, iid))
            split = years.index(bonus_year) if (bonus_year and bonus_year in years) else len(years)
            hovers = [f"{_name_of(names, iid)}<br>{panel_title}"
                      f"<br>{C.AX_YEAR.lower()}{C.THIN_SPACE}{y}"
                      f"<br>{C.AX_WORKS.lower()}{C.THIN_SPACE}{_fmt_vol(v)}"
                      for y, v in zip(years, vals)]
            fig.add_trace(go.Scatter(
                x=years[:split], y=list(vals[:split]), mode="lines+markers",
                line=dict(color=color, width=TRENDS_LINE_PX),
                marker=dict(color=color, size=TRENDS_MARKER_PX,
                            line=dict(color=P.SURFACE, width=C.HAIRLINE_PX)),
                customdata=hovers[:split], hovertemplate="%{customdata}<extra></extra>",
                showlegend=False), row=r, col=c)
            if split < len(years):
                lo = max(split - 1, 0)
                fig.add_trace(go.Scatter(
                    x=years[lo:], y=list(vals[lo:]), mode="lines+markers",
                    line=dict(color=color, width=TRENDS_LINE_PX, dash="dot"),
                    marker=dict(color=P.SURFACE, size=TRENDS_MARKER_PX,
                                line=dict(color=color, width=P.OUTLINE_WIDTH)),
                    customdata=hovers[lo:], hovertemplate="%{customdata}<extra></extra>",
                    showlegend=False), row=r, col=c)

    fig.update_xaxes(type="category", gridcolor=P.GRID, linecolor=P.BORDER,
                     tickfont=dict(size=C.GUTTER_FONT_PX))
    fig.update_yaxes(gridcolor=P.GRID, zerolinecolor=P.GRID, linecolor=P.BORDER,
                     rangemode="tozero", tickfont=dict(size=C.GUTTER_FONT_PX))
    if shared_y:
        # `shared_yaxes=True` links the panels of ONE ROW only; a small-multiples
        # grid whose second row has its own scale is the exact lie the form is
        # supposed to avoid (a flat panel and a steep panel looking alike), so
        # every y axis is matched to the first explicitly.
        fig.update_yaxes(matches="y")
    fig.update_annotations(font=dict(size=C.GUTTER_FONT_PX, color=P.INK_SECONDARY))
    height = n_rows * TRENDS_PANEL_PX + C.BASE_PX
    return C._base_layout(fig, height, margin=dict(t=C.BASE_PX // 2, l=8, r=16, b=C.BASE_PX))


# ---------------------------------------------------------------------------
# 7. Coverage strip (3.9) -- the ONE stacked bar in the app
# ---------------------------------------------------------------------------
def fig_coverage_strip(
    df: pd.DataFrame,
    slots: Mapping,
    *,
    names: Mapping | None = None,
    labels: Mapping | None = None,
    state_col: str = "state",
    share_col: str = "share",
) -> go.Figure:
    """One stacked, exhaustive strip per institution: the classified-eligible
    mass in the institution's OWN colour, then the five grey states in the
    ordinal ramp (`palette.GREY_STATE_COLORS`), light to dark.

    A stacked bar is legal here and nowhere else in this module because the
    segments really are the parts of one whole: the six `mass_*` columns sum to
    `total_frac` EXACTLY for all 7,557 institutions (A9). Everywhere else in
    Compare the categories are not a partition, so a stack would assert a total
    that does not exist -- which is why the frontier mix, whose four quadrants
    sum to a MEDIAN of 0.967, is drawn as dot rows instead.

    The colour split is the whole point: one coloured segment is the answer
    (how much text the classifiers could actually read), and the muted ordered
    ramp behind it accounts for the rest without competing. That also keeps the
    coexistence rule intact -- the only identity in the figure is still the
    institution."""
    labels = dict(STATE_LABELS, **(labels or {}))
    d = df.copy()
    ids = _ordered_ids(d, slots)
    n = len(ids)
    ticks = [C.wrap_label(_name_of(names, i)) for i in ids]
    n_wrapped = sum(1 for t in ticks if "<br>" in t)

    fig = go.Figure()
    for state in P.GREY_STATE_ORDER:
        xs, colors, hovers = [], [], []
        for iid in ids:
            hit = d[(d["institution_id"] == iid) & (d[state_col].astype(str) == state)]
            v = float(pd.to_numeric(hit[share_col], errors="coerce").iloc[0]) if len(hit) else 0.0
            v = v if np.isfinite(v) else 0.0
            xs.append(v)
            colors.append(P.institution_color(_slot_of(slots, iid))
                          if state == P.CLASSIFIED_ELIGIBLE_STATE else P.grey_state_color(state))
            hovers.append(f"{_name_of(names, iid)}<br>{labels.get(state, state)}"
                          f"<br>{C.HOVER_SHARE}{C.THIN_SPACE}{_fmt_pct(v)}")
        fig.add_trace(go.Bar(
            x=xs, y=ticks, orientation="h", marker=dict(
                color=colors, line=dict(color=P.SURFACE, width=P.OUTLINE_WIDTH)),
            customdata=hovers, hovertemplate="%{customdata}<extra></extra>",
            showlegend=False))

    fig.update_layout(barmode="stack")
    fig.update_yaxes(autorange="reversed", showgrid=False, automargin=True)
    fig.update_xaxes(range=[0, 1], title_text=AX_STATE, tickformat=C._AXIS_PCT_FMT,
                     gridcolor=P.GRID, zerolinecolor=P.GRID, linecolor=P.BORDER)
    plain = [t.replace("<br>", "\n") for t in ticks]
    return C._base_layout(fig, C.row_height(n, minimum=STRIP_ROW_MIN_PX,
                                            n_wrapped=n_wrapped),
                          margin=dict(t=C.BASE_PX // 2, l=C._gutter_margin_px(plain),
                                      r=16, b=C.BASE_PX))


# ---------------------------------------------------------------------------
# 8. The ONE legend of a Compare view
# ---------------------------------------------------------------------------
def institution_legend_html(names, slots: Mapping) -> str:
    """Chip strip naming every compared institution, in SLOT order.

    It is `charts.chip_legend_html` with the institution family plugged in --
    same markup, same escaping, same one-legend-per-view discipline -- so a
    Compare page and a Find page wear the same legend. Mandatory, not optional:
    the palette's deutan 7.6 WARN (palette_validation.txt run 9) is only legal
    WITH a secondary encoding, and this strip plus the axis labels plus the
    hover are it.

    `names` may be a mapping identifier -> display name, or a plain sequence of
    names already in slot order."""
    if hasattr(names, "items"):
        items = sorted(names.items(), key=lambda kv: (_slot_of(slots, kv[0]), str(kv[0])))
        return C.chip_legend_html([(str(v), P.institution_color(_slot_of(slots, k)))
                                   for k, v in items])
    return C.chip_legend_html([(str(v), P.institution_color(i))
                               for i, v in enumerate(names)])

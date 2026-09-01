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

PHASE 2B-R AMENDMENT (2026-08-30, stream VS) -- THE CAP CHANGED, SO THE FORM DID
--------------------------------------------------------------------------------
Everything above was written for a basket of SIX. 2B-R-4 caps Compare at THREE,
and that single number reopens the form question the 2B wind tunnel closed: the
"2.6 px per bar" arithmetic that killed grouped bars was 26 fields x 6
institutions, and at k = 3 the same pitch gives a bar an order of magnitude more
room. A/B #7 (VIZ_SPEC section 7) re-ran the contest on real data at k = 3 and
the grouped bar WON, on the one thing the dot row cannot do: put the NUMBER on
the mark. So the 2B-R views take `fig_metric_bars`, and `fig_mirror_dots` is
retained for the frames that still want a two-panel share + SI read.

The one rule (2B-1) survives intact and is narrowed in exactly one place: colour
on a MARK still means the institution and only the institution, and 2B-R-8 lets
the taxonomy's OFFICIAL colour appear as a glyph in the ROW LABEL of the ERC and
SDG views -- axis furniture, never a mark, never a legend chip, and never the
other way round (an institution colour on a label accent is forbidden outright).
The doctrine, the direction and the single resolver live in `palette.py`'s
LABEL ACCENTS section.

`palette.SHARED_FRONTIER` is the one new hue: it is NOT a fourth institution but
the intersection -- the pooled frontier map's "every compared institution holds
this topic" bubbles, and the Collaborate pulse, whose subject is likewise the
JOINT corpus rather than either side.
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
        return _chip_strip([(str(v), P.institution_color(_slot_of(slots, k)),
                             P.institution_ink(_slot_of(slots, k)))
                            for k, v in items])
    return _chip_strip([(str(v), P.institution_color(i), P.institution_ink(i))
                        for i, v in enumerate(names)])


# ===========================================================================
# PHASE 2B-R (stream VS, 2026-08-30) -- the Compare/Collaborate redesign
# ===========================================================================
# Geometry and vocabulary for the new builders. Same two scans apply: no hex
# literal (every hue comes from `lib.palette`), no digit inside a string
# literal (every number is an int/float constant or a caller-filled value).
# ---------------------------------------------------------------------------
COMPARE_MAX_SERIES = 3      # 2B-R-4, the HARD cap. It is not a preference: the
                            # bar geometry below is sized from it, and the k = 3
                            # institution prefix is the set validator run 13
                            # measured warning-free.
BAR_PX = 13                 # target thickness of ONE institution's bar in a
                            # grouped row. Well above the MIN_MARK_PX floor, and
                            # the number `metric_row_height` sizes the row band
                            # from -- so a bar can never be thinner than this by
                            # arithmetic, whatever the row count.
BAR_GROUP_SPAN = C.DEFAULT_GROUP_SPAN   # 2C CHROME-F (progress/2C_CHROME-F.md
BAR_GROUP_FILL = C.DEFAULT_GROUP_FILL   # S2): single-sourced from charts.py --
                            # the two constant pairs (this module's and the
                            # Find profile panels') are now IDENTICAL values
                            # read from one place, never two literals that can
                            # drift apart again. The share of a row band the
                            # bar group occupies / the share of a group slot
                            # one bar occupies (the remainder is the SURFACE
                            # gap the dataviz mark specs ask for between bars).
AXIS_PAD_FRAC = 0.20        # x-range headroom so an outer-end label never
                            # collides with the plot frame (measured need, A/B #9)
ROW_RULE_PX = 1             # hairline between two category rows
REF_HALF_BAND = 0.40        # half-height of a per-row reference dash, in category units
BOLD_AXIS_PX = 2            # the BOLD BLACK 0/0 axes (2B-R-9 / 2B-R-13). INK on a
                            # RULE, not on a mark -- the quadrant split is the
                            # figure's own frame of reference, so it is the one
                            # line that may out-weigh the grid.
MAP_BUBBLE_MIN_PX = 9       # pooled frontier map: the smallest topic bubble
MAP_BUBBLE_MAX_PX = 40      # ...and the largest (combined volume, area-scaled)
MAP_HEIGHT_PX = 560
PULSE_HEIGHT_PX = 320
PULSE_BAR_SPAN = 0.62       # one pulse bar's share of its year slot

ACCENT_GLYPH = "\N{BLACK VERTICAL RECTANGLE}"
# The row-label accent (2B-R-8). A GLYPH, drawn in the taxonomy's official hue
# through plotly's tick pseudo-html, sitting to the left of a label that names
# the taxon in full -- so the colour is recognition and the text is the
# encoding. Never a mark; see palette.LABEL_ACCENT_FAMILIES.
ACCENT_GAP = "\N{NO-BREAK SPACE}"

PARTIAL_YEAR_GLYPH = "\N{ASTERISK}"
# 2B-R-12: the partial final year is labelled `<year>*` on every x axis and the
# footnote lives in the section tooltip. The YEAR itself is always a
# caller-supplied string -- this module never names one.

SHARED_OWNER = "shared"
# The `owner` value that means "every compared institution holds this topic"
# (contract section 4, `frontier_pooled`). Its colour is `palette.SHARED_FRONTIER`,
# which is deliberately not an institution slot.

METRICS = ("share", "vol_top10", "pp", "sdg_share", "dynamics", "si", "vol", "fwci")
# EVERY metric `fig_metric_bars` accepts. 2C (Stream VC, D2): `fwci` joins at
# ALL FOUR levels (CD5 ships `fwci_mean`/`ref_value` on every grain's frame).
# `vol` is 2B-R2-1b's fix: the selector
# offered it, `views_compare.METRIC_LABELS` named it, and this tuple did not --
# so `vol x erc` and `vol x sdg` raised `ValueError` on a path no test drove
# (wind tunnel 2BR2 claim #18 enumerated exactly those two crashes out of a
# 7 x 4 truth table). The lesson is in the test, not in this comment:
# `test_every_metric_level_renders` drives the WHOLE table.
#
# `vol_top10` stays ACCEPTED here although 2B-R2-3 retires it as a TAB -- the
# builder refusing a metric the page can still ask for is precisely the class of
# bug above. What the selector offers is `SELECTOR_METRICS`.

SELECTOR_METRICS = ("share", "si", "pp", "sdg_share", "dynamics", "vol", "fwci")
# 2B-R2-3's ruled selector ORDER: Share, Specialisation, PP(top10%), SDG-tagged,
# Dynamics, Volume-where-defined, and (2C, D2) FWCI last. `vol_top10` is absent
# by ruling (its mass moved into the PP view's gutter); the page hides the
# rest per level through its own availability map, and this tuple is what its
# sweep iterates.

LEVELS = ("field", "subfield", "erc", "sdg")

REF_METRICS = ("pp", "sdg_share", "dynamics", "fwci")
# 2B-R2-4: a reference line is drawn for these ONLY -- PP/SDG-tagged share/
# Dynamics reference the population mean among institutions with nonzero mass,
# per taxon x tree. Share and Volume get none (there is no "expected share":
# the shares of a partition sum to one by construction, so a mean share is an
# artefact of how many taxa exist, not a benchmark). `si` is not in the list
# because its reference is not data at all (see `_METRIC_DEFAULT_REF`). A
# frame may carry `ref_value` for any metric; a metric outside this tuple
# simply does not draw it.
#
# 2C (Stream VC, D3): `fwci` joins with a DIFFERENT reference semantics than
# the other three -- the European corpus-level MEDIAN work-FWCI per taxon
# (never an institution mean), so its hover line is never the generic
# `HOVER_REFERENCE` text (see `fig_metric_bars`'s `ref_label` parameter and
# `_metric_hover`). A 0.0 reference (27 taxa, WT_2C.md claim 2) is real data
# and draws exactly like any other value -- `_add_reference` already tests
# `np.isfinite`, never truthiness, so this needed no fix here.

SORT_MODES = ("taxonomy", "value")
# 2B-R2-5. `taxonomy` (the default) groups the rows under their domains in the
# taxonomy's own fixed order, so the row order is STABLE across metric tabs --
# switch from Share to Dynamics and every row stays where it was, which is what
# makes the tabs comparable at all. `value` is the per-section toggle.

LOW_VOLUME_FLOOR = 10.0
# 2B-R2-4: a cell whose mean annual FULL volume is below this is drawn HOLLOW
# and daggered. Not a data filter -- the value is still true, it is just built
# on so few publications that a reader should not race it against a neighbour.
#
# 2C AMENDMENT (D6, decisions log 2026-09-01, WT_2C.md claim 4): the
# ONE-SENTENCE user-facing rule stays "a bar hatches when it rests on fewer
# than `palette.RATIO_HATCH_FLOOR` works over the counted window" for EVERY
# metric -- `LOW_VOLUME_FLOOR * N_CORE_YEARS` (10/yr x 5 yr) already equals
# `palette.RATIO_HATCH_FLOOR` (50), so the two mechanisms below are the SAME
# threshold in different units, never two different floors. The
# IMPLEMENTATION still forks by metric family (`_is_low_volume`): PP and FWCI
# carry a genuinely per-row `denom_value` (n_works_full / n_covered) and hatch
# on THAT directly against `palette.RATIO_HATCH_FLOOR`; every other metric
# keeps hatching on `low_vol_col` (`vol_full_annual_mean`) against this
# constant -- their own `denom_value` is an INSTITUTION-CONSTANT column
# (share's own total mass), and re-keying it would silently disable hatching
# for those families entirely (measured: share denominators run 400-1,200,
# never below 50).

RATIO_HATCH_METRICS = ("pp", "fwci")
# The metrics whose `denom_value` is a genuinely per-row, diagnostic count
# (2C D6 amendment) -- these hatch on `denom_value < palette.RATIO_HATCH_FLOOR`
# instead of on `low_vol_col`. See `LOW_VOLUME_FLOOR`'s own docstring above.

CAPTION_FONT_WEIGHT = 400   # D5 (CHROME_CONTRACT.md §7): the basis caption is
                            # NEVER bold, in either its normal or warning
                            # colour state -- an int constant so the literal
                            # never has to sit inside a banned string digit.

LOW_VOLUME_GLYPH = "\N{DAGGER}"
# The visible half of the low-volume marker (the hatched bar, below, is the
# other half). A DAGGER rather than the warning sign the plan sketches: a
# dagger is the typographic convention for "see the note", renders as text in
# every font this app ships, and cannot arrive as a colour emoji -- which would
# put a hue in the figure that no palette owns.

LOW_VOLUME_PATTERN_SHAPE = "/"
LOW_VOLUME_PATTERN_SOLIDITY = 0.35
# 2B-R3 (user ruling 5, WT_2BR3.md): a below-floor bar is HATCHED, not hollow --
# a diagonal `marker.pattern` in the bar's OWN colour (`fgcolor=color`) over a
# SURFACE ground, at the same DAGGER + hover disclosure as before. Retires the
# SURFACE-fill-plus-outline "hollow" idiom for every below-floor BAR this module
# draws; the SI/mirror-dot below-floor MARKER stays hollow (plotly's pattern
# fill is a Bar-family feature, not a Scatter-marker one).

DOMAIN_RULE_PX = 2          # the separator BETWEEN two taxonomy domains
NOTE_MAX_CHARS = 160        # `chart_note`'s hard cap -- see its docstring
DOT_HTML_PX = 10            # the KPI card's best-value dot
DOT_GAP_PX = 6

POOLS = ("volume", "frontier")
COLOR_BY = ("owner", "domain")

AX_TOP_DECILE_VOL = "Publications in the world top decile"
AX_TOP_DECILE_SHARE = "Share of publications in the world top decile"
AX_SDG_TAGGED = "Share of publications tagged to a goal"
AX_DYNAMICS = "Change in mean annual volume"
AX_COPUBS = "Joint publications"
AX_JOINT_VOLUME = "Joint publications on the topic"
AX_FWCI = "FWCI (median)"
# 2C (D2): the FWCI axis/metric-label fallback. `views_compare.METRIC_LABELS`
# always passes its own `copy.COMPARE["METRIC_FWCI"]` string explicitly, so
# this constant is the safety net for a caller (a test, a future page) that
# does not -- same role `AX_SI`/`AX_WORKS` already play for their metrics.

HOVER_REFERENCE = "index reference"
HOVER_DENOMINATOR = "denominator"
HOVER_OWNER = "held by"
HOVER_COMBINED = "combined volume"
HOVER_MEAN = "mean"
# 2C (D2): the FWCI hover's second statistic, beside the median bar value --
# `_metric_hover`'s `fwci_mean_col` param renders this line ONLY when that
# column is present and non-null, which (v5 metric_frame contract) is true on
# the `fwci` frame alone.
HOVER_LOW_VOLUME = "rests on fewer than {floor} works over the counted window, read with care"
# 2C AMENDMENT (D6): ONE sentence for every hatched bar, whichever mechanism
# triggered it (see `LOW_VOLUME_FLOOR`'s own docstring) -- `{floor}` is filled
# at hover-build time from `palette.RATIO_HATCH_FLOOR` (never a digit literal
# in this module, per its own digit-ban). Never says "a year on average" any
# more: PP/FWCI hatch on a window TOTAL, not an annual mean, so the old
# per-year framing was already wrong for them and is now dropped for every
# metric in favour of the one true number every reader can check.
HOVER_DOMAIN = "domain"
LABEL_SHARED = "shared"
NOTE_HELP_GLYPH = "?"

_METRIC_AXIS = {
    "share": C.AX_SHARE,
    "vol_top10": AX_TOP_DECILE_VOL,
    "pp": AX_TOP_DECILE_SHARE,
    "sdg_share": AX_SDG_TAGGED,
    "dynamics": AX_DYNAMICS,
    "si": C.AX_SI,
    "vol": C.AX_WORKS,
    "fwci": AX_FWCI,
}
_METRIC_KIND = {"share": "pct", "vol_top10": "vol", "pp": "pct",
                "sdg_share": "pct", "dynamics": "pct", "si": "si",
                "vol": "vol", "fwci": "fwci"}
# `vol` takes the INTEGER branch (2B-R2-1b): `charts._fmt_vol` prints a whole
# number with thin-space thousands separators and no decimal, because a count
# of publications has none. It is the same branch `vol_top10` has always used --
# the crash was never about formatting, only about the metric never being
# admitted to `METRICS`.
_SIGNED_METRICS = ("dynamics",)
_METRIC_DEFAULT_REF = {"si": C.SI_NEUTRAL}
# `si` is the one metric whose reference is a CONSTANT of the indicator itself
# (specialisation is defined against the index mean, so the neutral value is
# one). Every other reference -- the index PP, the index share -- is DATA and
# arrives in the frame's `ref_value` column; this module never invents one.

_ACCENT_COLS = {"erc": ("erc_domain",), "sdg": ("sdg_number", "sdg_idx"),
                "field": ("domain_id",), "subfield": ("domain_id",)}
_LEVEL_ACCENT_FAMILY = {"erc": "erc", "sdg": "sdg", "field": "oa", "subfield": "oa"}
# 2B-R3 (user ruling 5): field/subfield rows now carry the OA-domain chip too
# -- the label accent is the ONLY visual cue for a field's domain once the bar
# itself is institution-coloured, and the reader already knows this exact
# palette from the OA-coloured Find panels.


DYNAMICS_CLAMP_PCT = 999
# 2B-R3 (user ruling 5, plan section 2.5): dynamics is a %-CHANGE, unbounded
# in principle -- a collaboration going from one publication a year to twenty
# is a real, valid four-digit swing, not a data error, so the underlying
# number is NEVER clamped. Only the DISPLAY text is, past this many percent
# either direction, so one runaway row cannot stretch the bar's own value
# label or blow out the axis scale the other rows share.


def _fmt_dynamics_pct(v) -> str:
    """The dynamics metric's display clamp: `> +999 %` / `< -999 %` past
    `DYNAMICS_CLAMP_PCT`, `_fmt_pct` unchanged inside it. `v` is the same
    fraction every other `pct`-kind metric takes (`_fmt_pct` multiplies by a
    hundred), so the clamp compares against the fraction form of the limit."""
    f = _num(v)
    if not np.isfinite(f):
        return P.NA_MARK
    limit = DYNAMICS_CLAMP_PCT / 100.0
    if f > limit:
        return f"> +{DYNAMICS_CLAMP_PCT}{C.THIN_SPACE}%"
    if f < -limit:
        return f"< \N{MINUS SIGN}{DYNAMICS_CLAMP_PCT}{C.THIN_SPACE}%"
    return _fmt_pct(f)


def _fmt_metric(v, metric: str) -> str:
    kind = _METRIC_KIND.get(metric, "vol")
    if kind == "pct":
        if metric == "dynamics":
            return _fmt_dynamics_pct(v)
        return _fmt_pct(v)
    if kind == "si":
        return _fmt_si(v)
    if kind == "fwci":
        # 2C (D2): same two-decimal, NA-safe convention as SI (both cluster
        # near the neutral value), reused rather than a new format function --
        # matches `views_collab.FWCI_FORMAT = "%.2f"`, the CHROME_CONTRACT
        # D9-compliant precedent for this exact number.
        return _fmt_si(v)
    return _fmt_vol(v)


def metric_row_height(n_rows: int, n_series: int, n_wrapped: int = 0,
                      minimum: int = C.MIN_HEIGHT) -> int:
    """Figure height for `n_rows` grouped-bar rows -- the twin of
    `compare_row_height`, sized from `BAR_PX` instead of from a lane pitch.

    The profile pitch is kept whenever it already gives every bar its target
    thickness; when it does not, the row band grows to exactly what the bar
    stack needs and no further. That is what makes "no bar is thinner than
    `BAR_PX`" an arithmetic property of the builder rather than a hope about the
    row count -- the 2B wind tunnel's 2.6 px bars were the same picture drawn
    into a band sized for dots."""
    n_rows = max(int(n_rows), 1)
    base = C.row_height(n_rows, minimum=minimum, n_wrapped=n_wrapped)
    chrome = C.BASE_PX + C.BASE_PX // 2
    need = BAR_PX * max(int(n_series), 1) / (BAR_GROUP_SPAN * BAR_GROUP_FILL)
    have = max(base - chrome, 0) / n_rows
    if have >= need:
        return base
    return int(round(need * n_rows)) + chrome


def _series_ids(d: pd.DataFrame, slots: Mapping, ids: Sequence | None) -> list:
    """The compared institutions, in SLOT order, capped at `COMPARE_MAX_SERIES`.

    Refusing rather than truncating is deliberate: a builder that silently drew
    three of four institutions would produce a figure whose caption, legend and
    export all disagree with it. `lib/selection.py` owns the truncation, once,
    with a copy line (2B-R-4)."""
    out = list(ids) if ids is not None else _ordered_ids(d, slots)
    out = sorted(dict.fromkeys(out), key=lambda i: (_slot_of(slots, i), str(i)))
    if len(out) > COMPARE_MAX_SERIES:
        raise ValueError(f"at most {COMPARE_MAX_SERIES} institutions per compare "
                         f"figure, got {len(out)}")
    if not out:
        raise ValueError("no institutions to draw")
    return out


def _accent_ticktext(rows: pd.DataFrame, level: str, label_col: str,
                     accent_col: str | None) -> tuple[list[str], list[str]]:
    """`(plain, styled)` tick strings, with the 2B-R-8 taxonomy accent.

    `plain` is what `_gutter_margin_px` measures; `styled` is what plotly
    draws. When the level has no official palette, or the frame carries no
    accent key, no accent is invented.

    2B-R3: the volume gutter that used to be CRAMMED into this tick string
    (one line, every drawn institution's number concatenated) moved to each
    bar's OWN text (`fig_metric_bars`'s per-bar vertical gutter) -- illegible
    past two institutions on one line, legible at any count when each number
    sits at its own bar's end instead. This function carries the taxonomy
    accent only now."""
    family = _LEVEL_ACCENT_FAMILY.get(level)
    plain, styled = [], []
    for _, r in rows.iterrows():
        text_plain, text_styled = C._tick_display(str(r[label_col]), None)
        if family and accent_col and accent_col in rows.index.names + list(rows.columns):
            hexcol = P.label_accent_color(family, r[accent_col])
            text_plain = f"{ACCENT_GLYPH}{ACCENT_GAP}{text_plain}"
            text_styled = (f'<span style="color:{hexcol}">{ACCENT_GLYPH}</span>'
                           f"{ACCENT_GAP}{text_styled}")
        plain.append(text_plain)
        styled.append(text_styled)
    return plain, styled


def _metric_rows(d: pd.DataFrame, key_col: str, keep: Sequence[str], sort: str,
                 value_col: str, domain_col: str, domain_order_col: str,
                 ) -> tuple[pd.DataFrame, list[int]]:
    """One row per taxon, ordered (2B-R2-5), plus the domain BOUNDARIES.

    `taxonomy` keeps the frame's own arrival order INSIDE each domain and sorts
    the domains by `domain_order_col` -- the producer owns the taxonomy order,
    this builder owns only the grouping. A frame with no domain key is left
    exactly as it arrived, which is what every pre-2B-R2 caller gets for free.

    `value` ranks by the value summed across the compared institutions and
    returns NO boundaries: a domain separator under a value ranking would draw a
    grouping the rows no longer have.

    Both sorts are stable (`mergesort`), so two taxa with the same key keep the
    order the producer gave them rather than an arbitrary one."""
    rows = d.drop_duplicates(subset=[key_col])[list(keep)].reset_index(drop=True)
    rows["_arrival"] = range(len(rows))
    if sort == "value":
        agg = (d.assign(_v=pd.to_numeric(d[value_col], errors="coerce").fillna(0.0))
                .groupby(key_col, sort=False)["_v"].sum())
        rows["_rank"] = [-float(agg.get(k, 0.0)) for k in rows[key_col]]
        rows = rows.sort_values(["_rank", "_arrival"], kind="mergesort")
        return rows.drop(columns=["_rank", "_arrival"]).reset_index(drop=True), []
    if domain_order_col in rows.columns:
        rows["_dom"] = pd.to_numeric(rows[domain_order_col], errors="coerce")
        rows["_dom"] = rows["_dom"].fillna(float(len(rows)))
        rows = rows.sort_values(["_dom", "_arrival"], kind="mergesort").drop(columns="_dom")
    rows = rows.drop(columns="_arrival").reset_index(drop=True)
    edge_col = domain_col if domain_col in rows.columns else domain_order_col
    if edge_col not in rows.columns:
        return rows, []
    marks = [str(v) for v in rows[edge_col].tolist()]
    return rows, [i for i in range(len(marks) - 1) if marks[i] != marks[i + 1]]


def _gutter_value(v) -> str:
    """One gutter cell. A NUMBER is formatted as a volume (thin-space thousands,
    no decimals); anything else is printed as the producer wrote it, which is
    how 2B-R2-4's raw-delta gutter ("two point one to nought point four a year")
    reaches the axis without this module composing a sentence it does not own."""
    f = _num(v)
    if np.isfinite(f):
        return _fmt_vol(f)
    text = str(v).strip()
    return text if text and text.lower() != "nan" else P.NA_MARK


def _domain_key(v) -> str:
    """A domain id as a STRING key, tolerant of the float a parquet join leaves
    behind (`1.0` and `1` must be one group, not two)."""
    f = _num(v)
    return str(int(f)) if np.isfinite(f) else str(v)


def _is_low_volume(r: pd.Series, metric: str, low_vol_col: str, denom_value_col: str) -> bool:
    """2B-R2-4's marker test, PER-METRIC forked by the 2C D6 amendment
    (`RATIO_HATCH_METRICS`'s own docstring): PP and FWCI hatch on their own
    per-row `denom_value` (n_works_full / n_covered) against
    `palette.RATIO_HATCH_FLOOR`; every other metric keeps hatching on
    `low_vol_col` (mean annual FULL volume) against `LOW_VOLUME_FLOOR` -- the
    same numeric threshold in different units (WT_2C.md claim 4). A frame
    missing the relevant column, or a cell with no value in it, is NOT low
    volume -- an unmeasured thing is never flagged, the same direction as
    `n/a` never being zero."""
    index = getattr(r, "index", [])
    if metric in RATIO_HATCH_METRICS:
        if denom_value_col not in index:
            return False
        v = _num(r[denom_value_col])
        return bool(np.isfinite(v) and v < P.RATIO_HATCH_FLOOR)
    if low_vol_col not in index:
        return False
    v = _num(r[low_vol_col])
    return bool(np.isfinite(v) and v < LOW_VOLUME_FLOOR)


def _row_rules(fig: go.Figure, n_rows: int, boundaries: Sequence[int] = ()) -> None:
    """A hairline BETWEEN two rows -- not a zebra band.

    A grouped row is already a visual block (two or three touching bars); a
    filled band behind it would fight the bars for the same ink, where a rule
    only says where one row stops. `_zebra` stays the right answer for the
    lane-split dot mirrors, whose rows hold nothing but whitespace.

    `boundaries` (2B-R2-5) names the row indices AFTER which a taxonomy DOMAIN
    ends. Those get the same line one step heavier and one step darker -- GRID
    rather than BORDER, `DOMAIN_RULE_PX` rather than `ROW_RULE_PX`. Subtle on
    purpose: the grouping is already carried by the ORDER, so the rule only has
    to confirm it. A domain LABEL or a coloured band would be a second identity
    family in an institution-coloured figure, which the coexistence rule
    forbids outright."""
    edges = set(int(b) for b in boundaries)
    for i in range(n_rows - 1):
        domain_edge = i in edges
        fig.add_shape(type="line", x0=0, x1=1, xref="x domain",
                      y0=i + 0.5, y1=i + 0.5,
                      line=dict(color=P.GRID if domain_edge else P.BORDER,
                                width=DOMAIN_RULE_PX if domain_edge else ROW_RULE_PX),
                      layer="below")


def _bold_axes(fig: go.Figure, *, x: float = C.FRONTIER_ORIGIN,
               y: float | None = C.FRONTIER_ORIGIN) -> None:
    """The bold black origin lines (2B-R-9 / 2B-R-13)."""
    fig.add_vline(x=x, line=dict(color=P.INK, width=BOLD_AXIS_PX))
    if y is not None:
        fig.add_hline(y=y, line=dict(color=P.INK, width=BOLD_AXIS_PX))


# ---------------------------------------------------------------------------
# 9. The metric selector's chart -- horizontal grouped bars (2B-R-5 / 2B-R-8)
# ---------------------------------------------------------------------------
def fig_metric_bars(
    frame: pd.DataFrame,
    metric: str,
    ids: Sequence | None = None,
    *,
    slots: Mapping,
    names: Mapping | None = None,
    level: str = "field",
    sort: str = "taxonomy",
    value_col: str = "value",
    label_col: str | None = None,
    key_col: str | None = None,
    ref_col: str = "ref_value",
    ref_value: float | None = None,
    denominator_col: str = "denominator",
    denom_value_col: str = "denom_value",
    accent_col: str | None = None,
    metric_label: str | None = None,
    gutter: bool = True,
    gutter_col: str = "vol_display",
    low_vol_col: str = "vol_full_annual_mean",
    domain_col: str = "domain_id",
    domain_order_col: str = "domain_order",
    fwci_mean_col: str = "fwci_mean",
    ref_label: str | None = None,
) -> go.Figure:
    """ONE metric, one taxonomy level, up to three institutions: horizontal
    grouped bars, one row per taxon, the value written on the mark.

    This is 2B-R-5's form and A/B #7's measured winner (VIZ_SPEC section 7). The
    thing it does that the dot mirror could not is put the NUMBER on the mark:
    at k = 6 a row held six values and had nowhere to write them, so they went
    to the hover; at k = 3 they fit on the bars, and a comparison the reader can
    read without hovering is a different chart.

    ROW ORDER (2B-R2-5, which reopened 2B-R-5's "the frame arrives ranked").
    The DEFAULT is `sort="taxonomy"`: rows grouped under their domains, in the
    taxonomy's own fixed order, with a heavier separator where one domain ends
    (`domain_order_col` supplies the grouping, `_row_rules` the separator). That
    order does not move when the reader switches metric tab, which is the whole
    point -- a row that stays put between Share and Dynamics can be compared
    across the two. `sort="value"` is the per-section toggle and ranks by the
    value SUMMED over the compared institutions, the same "large in the set as a
    whole" rule `_row_order` uses. Colour follows the entity either way, so
    nothing repaints when the reader flips the toggle.

    THE GUTTER (2B-R2-3: raw volume on EVERY metric, not just the volume tab;
    2B-R3: moved from the tick label onto each institution's OWN bar). Every
    drawn bar carries its own institution's raw volume as PART OF ITS OWN bar
    text (plotly `text`, `textposition="outside"`, `cliponaxis=False`) --
    `"{value} ({volume})"`, written in that institution's DARK TWIN, right at
    that bar's own end. This REPLACES the pre-2B-R3 mechanism, which crammed
    every drawn institution's number onto ONE line of the row's tick label --
    legible at two institutions, a wall of digits at three. A per-bar label is
    legible at any count, because each number sits where its own bar is,
    vertically, rather than competing for one line of text. It answers the
    question every share chart provokes and no share chart answers: forty per
    cent of how many?

    LOW VOLUME (2B-R2-4; 2B-R3: hatched, not hollow). A cell whose
    `low_vol_col` (mean annual FULL volume) is under `LOW_VOLUME_FLOOR` is
    drawn with a diagonal `marker.pattern` in the bar's OWN colour over a
    SURFACE ground (`LOW_VOLUME_PATTERN_SHAPE`/`_SOLIDITY`, replacing the old
    hollow SURFACE-fill-plus-outline), and its value label carries
    `LOW_VOLUME_GLYPH`, with the reason in the hover. Disclosure, never
    suppression: the number is real, it is just built on too little to race
    against its neighbour. `fig_mirror_dots` keeps the hollow-means-thin dot
    for a below-floor SI cell (plotly patterns are a Bar-family feature, not a
    Scatter-marker one), so the two sections still read as one system, texture
    substituting for outline-only where a bar has real area to hatch.

    ENCODING. Bar = institution (`palette.institution_slots`, ascending
    `inst_key`). Row label = the taxon, and for ERC and SDG ONLY it carries a
    glyph in the taxonomy's official colour (2B-R-8). The direction is one-way
    and routed through `palette.label_accent_color`: taxonomy colour on labels,
    institution colour on marks, never the reverse.

    REFERENCE (2B-R2-4). Only `REF_METRICS` draw one -- PP, SDG-tagged share and
    Dynamics, whose reference is the population mean among institutions with
    nonzero mass. `si` defaults to the neutral value, which is a constant of the
    indicator rather than data. Share and Volume draw none even when the frame
    carries `ref_col`. A reference that is the SAME for every row is drawn as
    one dashed rule across the panel; one that VARIES by row is drawn as a short
    dash inside each row band, because a single line would be a lie about a
    per-taxon index mean.

    EMPTY STATE (n/a never zero, BUILD_PLAN_2A L11). An institution with no row
    for a taxon gets NO bar and NO label. A GENUINE zero gets no visible bar
    either -- a zero-length bar cannot be drawn -- but it does get its value
    label at the origin, so "measured, and it is zero" and "not measured" look
    different rather than identical.

    2C ADDITIONS for `metric="fwci"` (D2/D3/D6, Stream VC):
      * bar = the frame's `value` (the MEDIAN, D2); `fwci_mean_col` adds a
        "mean" hover line beside it -- never a second bar, never the axis.
      * `ref_label` overrides the generic `HOVER_REFERENCE` text for the
        reference line (`fwci` is in `REF_METRICS`) -- pass
        `compare_data.fwci_ref_label(level)`, never hand-typed, so the hover
        says "European median work in this field" and never "average".
      * a 0.0 `ref_value` (27 taxa, WT_2C.md claim 2) is real data and draws
        exactly like any other row -- `_add_reference` tests `np.isfinite`,
        never truthiness.
      * hatching keys off `denom_value` (`n_covered`), same mechanism as `pp`
        (`RATIO_HATCH_METRICS`), NOT off `low_vol_col` -- see
        `LOW_VOLUME_FLOOR`'s own docstring for why the two families cannot
        share one column.
    """
    if metric not in METRICS:
        raise ValueError(f"metric must be one of {METRICS}, got {metric!r}")
    if level not in LEVELS:
        raise ValueError(f"level must be one of {LEVELS}, got {level!r}")
    if sort not in SORT_MODES:
        raise ValueError(f"sort must be one of {SORT_MODES}, got {sort!r}")
    if "institution_id" not in frame.columns or value_col not in frame.columns:
        raise ValueError(f"frame needs institution_id and {value_col!r}")

    d = frame.copy()
    label_col = label_col or _first_col(d, ("taxon_label",) + C._LABEL_COLS)
    if label_col is None:
        raise ValueError("no label column found; pass label_col=")
    key_col = key_col or _first_col(d, ("taxon_id",) + _KEY_COLS.get(level, ())) or label_col
    accent_col = accent_col or _first_col(d, _ACCENT_COLS.get(level, ()))
    series = _series_ids(d, slots, ids)

    # 2B-R3: dict.fromkeys dedupes -- `accent_col` and `domain_col` are now
    # the SAME column name at OA level ("domain_id" is both the accent source
    # and the domain-boundary key), and a duplicate name in a DataFrame column
    # selection returns a 2-column sub-frame instead of a Series downstream.
    keep = list(dict.fromkeys(c for c in (key_col, label_col, ref_col, accent_col,
                                          domain_col, domain_order_col)
                              if c and c in d.columns))
    rows, boundaries = _metric_rows(d, key_col, keep, sort, value_col,
                                    domain_col, domain_order_col)
    n = len(rows)
    if n == 0:
        raise ValueError("no rows to draw")

    cells = {(r[key_col], r["institution_id"]): r for _, r in d.iterrows()}
    vals = pd.to_numeric(d[value_col], errors="coerce")
    vmax = float(vals.max()) if len(vals) and np.isfinite(vals.max()) else 0.0
    vmin = float(vals.min()) if len(vals) and np.isfinite(vals.min()) else 0.0
    signed = metric in _SIGNED_METRICS or vmin < 0

    keys = rows[key_col].tolist()

    fig = go.Figure()
    _row_rules(fig, n, boundaries)
    for k, iid in enumerate(series):
        offset, bar_w = C._series_offset_width(len(series), k, BAR_GROUP_SPAN,
                                               BAR_GROUP_FILL)
        slot = _slot_of(slots, iid)
        color = P.institution_color(slot)
        ink = P.institution_ink(slot)
        xs, ys, texts, hovers, fills, widths, patterns = [], [], [], [], [], [], []
        for ri, key in enumerate(keys):
            r = cells.get((key, iid))
            if r is None:
                continue
            v = _num(r[value_col])
            if not np.isfinite(v):
                continue
            low = _is_low_volume(r, metric, low_vol_col, denom_value_col)
            xs.append(v)
            ys.append(ri)
            text = _fmt_metric(v, metric) + (LOW_VOLUME_GLYPH if low else "")
            # 2B-R3 (user ruling 5): the PER-BAR vertical gutter -- each
            # institution's own raw volume at ITS OWN bar end, one bar text per
            # institution rather than three numbers crammed onto one tick-label
            # line (illegible past two institutions; see git history for the
            # retired `_accent_ticktext` gutter_cells mechanism this replaces).
            if gutter and gutter_col in r.index:
                text = f"{text}{C.TICK_LABEL_GAP}({_gutter_value(r[gutter_col])})"
            texts.append(text)
            # 2B-R3: hatched, not hollow -- see LOW_VOLUME_PATTERN_SHAPE above.
            fills.append(P.SURFACE if low else color)
            widths.append(P.OUTLINE_WIDTH if low else C.HAIRLINE_PX)
            patterns.append(LOW_VOLUME_PATTERN_SHAPE if low else "")
            hovers.append(_metric_hover(r, iid, names, label_col, value_col,
                                        metric, ref_col, denom_value_col,
                                        metric_label, gutter_col, low,
                                        fwci_mean_col=fwci_mean_col,
                                        ref_label=ref_label))
        fig.add_trace(go.Bar(
            x=xs, y=ys, orientation="h", offset=offset, width=bar_w,
            marker=dict(color=fills, line=dict(color=color, width=widths),
                        pattern=dict(shape=patterns, fgcolor=color,
                                    solidity=LOW_VOLUME_PATTERN_SOLIDITY)),
            text=texts, textposition="outside", cliponaxis=False,
            textfont=dict(size=C.GUTTER_FONT_PX, color=ink),
            customdata=hovers, hovertemplate="%{customdata}<extra></extra>",
            showlegend=False))

    fig.update_layout(barmode="overlay", bargap=0)
    if metric in REF_METRICS or ref_value is not None or metric in _METRIC_DEFAULT_REF:
        _add_reference(fig, rows, ref_col, ref_value, _METRIC_DEFAULT_REF.get(metric))

    plain, styled = _accent_ticktext(rows, level, label_col, accent_col)
    _y_axis(fig, n, styled)
    n_wrapped = sum(1 for s in styled if "<br>" in s)
    lo = min(vmin, 0.0)
    hi = max(vmax, 0.0)
    span = (hi - lo) or (abs(hi) or 1.0)
    pad = span * AXIS_PAD_FRAC
    fig.update_xaxes(range=[lo - (pad if signed else 0.0), hi + pad],
                     title_text=metric_label or _METRIC_AXIS[metric],
                     gridcolor=P.GRID, zerolinecolor=P.GRID, linecolor=P.BORDER)
    if _METRIC_KIND[metric] == "pct":
        fig.update_xaxes(tickformat=C._AXIS_PCT_FMT)
    if signed:
        _bold_axes(fig, y=None)
    plain_lines = [s.replace("<br>", "\n") for s in plain]
    return C._base_layout(fig, metric_row_height(n, len(series), n_wrapped=n_wrapped),
                          margin=dict(t=C.BASE_PX // 2,
                                      l=C._gutter_margin_px(plain_lines),
                                      r=C.BASE_PX, b=C.BASE_PX))


def _metric_hover(r, iid, names, label_col, value_col, metric, ref_col,
                  denom_value_col, metric_label, gutter_col: str | None = None,
                  low: bool = False, *, fwci_mean_col: str | None = None,
                  ref_label: str | None = None) -> str:
    """2B-R3 (user ruling 5, §2.5): the hover's `denominator` line prints
    `denom_value_col` -- a NUMBER, formatted with `_fmt_vol` -- and NEVER the
    old `denominator` NOTE STRING (a sentence like "articles+reviews,
    2020-2024"), which is the exact root cause of the "denominator: n/a" bug:
    a sentence is not `None` and not a NaN float, so `_fmt_vol` did not treat
    it as missing, it tried to coerce it as a number and lost. The note string
    itself moves to a tooltip/collapsible OUTSIDE this hover (the caller's
    page copy, not this chart) -- it never reaches `_fmt_vol` again.

    2C (D2/D3): `fwci_mean_col` adds ONE extra line -- the metric's mean,
    beside its median bar value -- rendered ONLY when that column exists AND
    is non-null on this row (v5 contract: null on every metric except `fwci`,
    so this is a no-op for every other caller with no per-metric branch
    needed here). `ref_label`, when given, REPLACES the generic
    `HOVER_REFERENCE` ("index reference") text for the reference line -- FWCI's
    reference is a European corpus-level MEDIAN work-FWCI, a different
    aggregation than the institution-mean reference PP/SDG-share/Dynamics
    draw, and WT_2C.md claim 1 rules the hover must say so explicitly rather
    than reuse the generic wording (which would misread as "average" and be
    mistaken for a neutral 1.0 baseline)."""
    title = (metric_label or _METRIC_AXIS[metric]).lower()
    parts = [_name_of(names, iid), str(r[label_col]),
             f"{title}{C.THIN_SPACE}{_fmt_metric(r[value_col], metric)}"]
    index = list(getattr(r, "index", []))
    if fwci_mean_col and fwci_mean_col in index and pd.notna(r[fwci_mean_col]):
        parts.append(f"{HOVER_MEAN}{C.THIN_SPACE}{_fmt_metric(r[fwci_mean_col], metric)}")
    if gutter_col and gutter_col in index:
        parts.append(f"{C.AX_WORKS.lower()}{C.THIN_SPACE}{_gutter_value(r[gutter_col])}")
    if ref_col in index and metric in REF_METRICS:
        label = ref_label or HOVER_REFERENCE
        parts.append(f"{label}{C.THIN_SPACE}{_fmt_metric(r[ref_col], metric)}")
    if denom_value_col in index:
        # `_fmt_vol` already turns a genuinely nullable denom_value into
        # NA_MARK -- that is honest disclosure ("no denominator for this
        # row"), not the bug. The bug was a NOTE STRING reaching this branch;
        # `denom_value` is a number by contract (§2.5), so this is now safe.
        parts.append(f"{HOVER_DENOMINATOR}{C.THIN_SPACE}{_fmt_vol(_num(r[denom_value_col]))}")
    if low:
        # the other half of the low-volume marker: the hatched bar says THAT,
        # the hover says WHY (2B-R2-4). Never a reason to hide the value.
        reason = HOVER_LOW_VOLUME.format(floor=_fmt_vol(P.RATIO_HATCH_FLOOR))
        parts.append(f"{LOW_VOLUME_GLYPH}{C.THIN_SPACE}{reason}")
    return "<br>".join(parts)


def _add_reference(fig: go.Figure, rows: pd.DataFrame, ref_col: str,
                   ref_value: float | None, default_ref: float | None) -> None:
    """One dashed rule for a CONSTANT reference, a per-row dash for a VARYING
    one. The distinction is the whole point: an index PP is a different number
    in every field, and drawing one line across the panel would assert a single
    benchmark that does not exist."""
    if ref_value is not None:
        _ref_line(fig, float(ref_value))
        return
    if ref_col in rows.columns:
        series = pd.to_numeric(rows[ref_col], errors="coerce")
        finite = series[np.isfinite(series)]
        if len(finite):
            if float(finite.max()) - float(finite.min()) <= 1e-12:
                _ref_line(fig, float(finite.iloc[0]))
            else:
                for ri, v in enumerate(series.tolist()):
                    if not np.isfinite(v):
                        continue
                    fig.add_shape(type="line", x0=float(v), x1=float(v),
                                  y0=ri - REF_HALF_BAND, y1=ri + REF_HALF_BAND,
                                  line=dict(color=P.INK_SECONDARY,
                                            width=C.HAIRLINE_PX, dash="dash"))
            return
    if default_ref is not None:
        _ref_line(fig, float(default_ref))


def _ref_line(fig: go.Figure, x: float) -> None:
    fig.add_vline(x=x, line=dict(color=P.INK_SECONDARY, width=C.HAIRLINE_PX,
                                 dash="dash"))


# ---------------------------------------------------------------------------
# 10. The pooled frontier map (2B-R-9, chart 1)
# ---------------------------------------------------------------------------
def fig_frontier_map(
    points: pd.DataFrame,
    top_n: int | None = None,
    *,
    slots: Mapping,
    names: Mapping | None = None,
    x_col: str = "x",
    y_col: str = "y",
    size_col: str = "combined_vol",
    owner_col: str = "owner",
    label_col: str = "name",
    labels: Mapping | None = None,
    pool: str = "volume",
    score_col: str = "frontier_score_latest",
    color_by: str = "owner",
    domain_col: str = "domain_id",
    domain_labels: Mapping | None = None,
) -> go.Figure:
    """ONE Expansion x Acceleration plane over the compared institutions' top
    frontier topics, POOLED: each topic appears once, sized by the volume the
    compared set puts into it and coloured by who holds it.

    This answers A/B #6's problem rather than re-running it. The 2B overlay drew
    each institution's own cloud, so the SAME topic appeared k times and 90.7 %
    of marks were occluded by a different institution's. Here the pooling
    happens in the DATA (contract section 4, `frontier_pooled`): one bubble per
    topic, `owner` naming either the single institution that holds it or
    `SHARED_OWNER`. Cross-institution occlusion is therefore not reduced, it is
    impossible -- two institutions never draw the same topic twice.

    ENCODING. Area = combined volume, one scale for the whole plane. Colour =
    the exclusive holder's institution hue, or `palette.SHARED_FRONTIER` for a
    topic every compared institution holds. Bold black rules at the origin on
    both axes: the quadrant split is the figure's frame of reference, so it is
    the one line allowed to out-weigh the grid. A top-quartile topic takes an
    INK outline -- a shape flag, never a new hue.

    2C D7 -- the shared-frontier HALO. `palette.FRONTIER_SHARED_HALO` (a
    slightly heavier SURFACE ring) marks EVERY shared-frontier mark, on BOTH
    `color_by` modes: in "owner" mode `SHARED_FRONTIER`'s dark red already
    names it, but WT_2C.md measured the real complaint as LUMINANCE, not hue
    (two dark marks read as "similarly dark blobs" even though they are
    colorimetrically distinct) -- the halo is the non-colour compensating
    signal palette.py's own re-measurement asks for. In "domain" mode a
    shared topic's FILL carries no ownership information at all (colour is
    the topic's OA domain there), so the halo is the ONLY visual cue that
    survives the toggle. A mark that is both shared and top-quartile keeps
    its INK outline (the stronger flag) at `OUTLINE_WIDTH`; a merely-shared,
    non-top mark gets the halo's own width, which sits strictly between
    `HAIRLINE_PX` and `OUTLINE_WIDTH` so the two flags never read as one.

    AUTOSCALED, with the origin forced inside the range. A pooled top-N set can
    sit entirely in one quadrant, and a quadrant plot whose quadrant lines are
    off-screen is not a quadrant plot.

    `top_n` keeps the largest bubbles by combined volume -- the slider 2B-R-9
    puts on the panel. Rows with no frontier score are DROPPED and must be
    counted in the caller's caption.

    POOL (2B-R2-10). `pool="volume"` (the default) is the form above: the
    compared set's top frontier topics ranked by the volume they put into them,
    so the map is about where the mass is. `pool="frontier"` ranks by
    `score_col` instead -- the topics that are most frontier, whatever their
    volume -- and the two answer genuinely different questions, which is why
    this is a selector and not a sort. Only the RANKING that `top_n` cuts
    changes: the bubble AREA is combined volume in both modes, because area
    means one thing in this app and a pool switch must not silently redefine it.
    The pool itself (which topics are eligible at all) is the producer's;
    2B-R2-10 rules that cut GLOBAL, so it does not move when the basket does.

    COLOUR (2B-R2-10). `color_by="owner"` is the ownership reading above.
    `color_by="domain"` REPLACES it with the OpenAlex domain of each topic --
    the same question asked of the same picture in the taxonomy's own colours,
    for a reader who wants to know what KIND of science sits in the expanding
    quadrant rather than whose it is. The two are mutually exclusive by
    construction, never blended, and the legend is rebuilt on the swap
    (`map_legend_strip`): one identity family per figure, the coexistence rule
    satisfied the same way the Find yearly-breakdown pair satisfies it."""
    if pool not in POOLS:
        raise ValueError(f"pool must be one of {POOLS}, got {pool!r}")
    if color_by not in COLOR_BY:
        raise ValueError(f"color_by must be one of {COLOR_BY}, got {color_by!r}")
    labels = dict({SHARED_OWNER: LABEL_SHARED}, **(labels or {}))
    d = points.copy()
    for col in (x_col, y_col, owner_col):
        if col not in d.columns:
            raise ValueError(f"missing column {col!r}")
    if color_by == "domain" and domain_col not in d.columns:
        raise ValueError(f"missing column {domain_col!r}")
    d = d[np.isfinite(pd.to_numeric(d[x_col], errors="coerce"))
          & np.isfinite(pd.to_numeric(d[y_col], errors="coerce"))].copy()
    d["_m"] = (pd.to_numeric(d[size_col], errors="coerce").fillna(0.0)
               if size_col in d.columns else 1.0)
    rank = ("_m" if pool == "volume" or score_col not in d.columns else "_s")
    if rank == "_s":
        d["_s"] = pd.to_numeric(d[score_col], errors="coerce").fillna(-np.inf)
    d = d.sort_values(rank, ascending=False, kind="mergesort")
    if top_n is not None:
        d = d.head(int(top_n))
    d = d.sort_values("_m", ascending=False, kind="mergesort").reset_index(drop=True)
    if not len(d):
        raise ValueError("no scored topics to draw")
    mmax = float(d["_m"].max()) or 1.0

    if color_by == "domain":
        d["_group"] = [_domain_key(v) for v in d[domain_col]]
        groups = [g for g in (str(k) for k in P.OA_DOMAIN_ORDER) if g in set(d["_group"])]
        groups += [g for g in dict.fromkeys(d["_group"].tolist()) if g not in groups]
    else:
        d["_group"] = d[owner_col]
        exclusive = [o for o in dict.fromkeys(d[owner_col].tolist()) if o != SHARED_OWNER]
        groups = _series_ids(d, slots, exclusive) if exclusive else []
        # the shared cloud is drawn LAST, i.e. on top: it is the answer the panel
        # exists for, and it is the one colour no institution owns.
        if (d[owner_col] == SHARED_OWNER).any():
            groups = groups + [SHARED_OWNER]

    fig = go.Figure()
    for owner in groups:
        mine = d[d["_group"] == owner]
        if not len(mine):
            continue
        shared = color_by == "owner" and owner == SHARED_OWNER
        if color_by == "domain":
            color = P.domain_color(owner)
            who = str((domain_labels or {}).get(owner, owner))
            who_label = HOVER_DOMAIN
        else:
            color = P.SHARED_FRONTIER if shared else P.institution_color(_slot_of(slots, owner))
            who = labels.get(owner, _name_of(names, owner))
            who_label = HOVER_OWNER
        top = (mine["top25pct_frontier"].fillna(False).to_numpy(dtype=bool)
               if "top25pct_frontier" in mine.columns else np.zeros(len(mine), dtype=bool))
        # 2C D7: the shared-frontier HALO -- a per-ROW flag off `owner_col`
        # itself, independent of `color_by`. In "owner" mode every mark of
        # this trace already IS shared (the whole `shared` boolean above); in
        # "domain" mode a shared topic's FILL carries no ownership signal at
        # all (colour is the domain there), so the halo is the only thing
        # that still says "held by more than one" on that toggle -- palette.py's
        # own docstring calls this out explicitly ("apply to every shared mark,
        # not just the owner-coloured ones").
        is_shared_row = (mine[owner_col] == SHARED_OWNER).to_numpy()
        halo_w = P.FRONTIER_SHARED_HALO["width"]
        sizes = MAP_BUBBLE_MIN_PX + (MAP_BUBBLE_MAX_PX - MAP_BUBBLE_MIN_PX) * np.sqrt(
            mine["_m"].to_numpy(dtype=float) / mmax)
        hovers = ["<br>".join([
            str(r[label_col]), f"{who_label}{C.THIN_SPACE}{who}",
            f"{C.HOVER_EXPANSION}{C.THIN_SPACE}{_fmt_frontier(r[x_col])}",
            f"{C.HOVER_ACCELERATION}{C.THIN_SPACE}{_fmt_frontier(r[y_col])}",
            f"{HOVER_COMBINED}{C.THIN_SPACE}{_fmt_vol(r['_m'])}"])
            for _, r in mine.iterrows()]
        fig.add_trace(go.Scatter(
            x=mine[x_col].to_numpy(dtype=float), y=mine[y_col].to_numpy(dtype=float),
            mode="markers",
            marker=dict(color=color, size=sizes, sizemode="diameter",
                        opacity=OVERLAY_OPACITY,
                        line=dict(color=[P.INK if t else P.SURFACE for t in top],
                                  width=[P.OUTLINE_WIDTH if t else
                                        (halo_w if sh else C.HAIRLINE_PX)
                                        for t, sh in zip(top, is_shared_row)])),
            customdata=hovers, hovertemplate="%{customdata}<extra></extra>",
            showlegend=False))

    _bold_axes(fig)
    fig.update_xaxes(title_text=C.AX_EXPANSION, range=_origin_range(d[x_col]),
                     gridcolor=P.GRID, zerolinecolor=P.GRID, linecolor=P.BORDER)
    fig.update_yaxes(title_text=C.AX_ACCELERATION, range=_origin_range(d[y_col]),
                     gridcolor=P.GRID, zerolinecolor=P.GRID, linecolor=P.BORDER,
                     automargin=True, title_standoff=6)
    return C._base_layout(fig, MAP_HEIGHT_PX,
                          margin=dict(t=C.BASE_PX // 2, l=8, r=16, b=C.BASE_PX))


def _origin_range(values) -> list:
    """Autoscale that always contains the origin, with room at the edges for the
    largest bubble's radius."""
    v = pd.to_numeric(values, errors="coerce")
    v = v[np.isfinite(v)]
    lo = min(float(v.min()), C.FRONTIER_ORIGIN) if len(v) else -1.0
    hi = max(float(v.max()), C.FRONTIER_ORIGIN) if len(v) else 1.0
    span = (hi - lo) or 1.0
    pad = span * AXIS_PAD_FRAC / 2.0
    return [lo - pad, hi + pad]


# ---------------------------------------------------------------------------
# 11. Who holds the shared frontier (2B-R-9, chart 2)
# ---------------------------------------------------------------------------
def fig_diverging_shared(
    rows: pd.DataFrame,
    ids: Sequence | None = None,
    *,
    slots: Mapping,
    names: Mapping | None = None,
    label_col: str = "name",
    key_col: str = "topic_id",
    value_col: str = "vol",
    top_n: int | None = None,
) -> go.Figure:
    """The shared frontier topics, ranked by combined volume, with each
    institution's own contribution drawn.

    TWO institutions -> a DIVERGING pair: one bar left of a bold zero, one
    right, so the IMBALANCE is the shape of the row and a reader recovers a
    twenty-to-one split by comparing two LENGTHS rather than two colours
    (A/B #8's measurement, VIZ_SPEC section 7). The axis ticks carry ABSOLUTE
    values, because a negative count would be a lie about the data -- the sign
    is a direction, not a magnitude.

    THREE institutions -> GROUPED rows, all on one side. A diverging bar has no
    second direction to give a third series, and stacking would turn three
    per-institution volumes into a total nobody asked for.

    The frame is LONG (institution_id, key, label, value) -- the same shape
    every other builder in this module takes."""
    d = rows.copy()
    for col in ("institution_id", key_col, value_col):
        if col not in d.columns:
            raise ValueError(f"missing column {col!r}")
    series = _series_ids(d, slots, ids)
    d["_v"] = pd.to_numeric(d[value_col], errors="coerce").fillna(0.0)
    combined = d.groupby(key_col, sort=False)["_v"].sum().sort_values(
        ascending=False, kind="mergesort")
    if top_n is not None:
        combined = combined.head(int(top_n))
    first = d.drop_duplicates(subset=[key_col]).set_index(key_col)
    order = list(combined.index)
    n = len(order)
    if n == 0:
        raise ValueError("no shared topics to draw")

    cells = {(r[key_col], r["institution_id"]): r for _, r in d.iterrows()}
    diverging = len(series) == 2
    fig = go.Figure()
    _row_rules(fig, n)
    vmax = 0.0
    for k, iid in enumerate(series):
        color = P.institution_color(_slot_of(slots, iid))
        if diverging:
            offset, bar_w = -BAR_GROUP_SPAN / 2.0, BAR_GROUP_SPAN
            sign = -1.0 if k == 0 else 1.0
        else:
            offset, bar_w = C._series_offset_width(len(series), k, BAR_GROUP_SPAN,
                                                   BAR_GROUP_FILL)
            sign = 1.0
        xs, ys, texts, hovers = [], [], [], []
        for ri, key in enumerate(order):
            r = cells.get((key, iid))
            if r is None:
                continue
            v = _num(r["_v"])
            if not np.isfinite(v):
                continue
            vmax = max(vmax, abs(v))
            xs.append(sign * v)
            ys.append(ri)
            texts.append(_fmt_vol(v))
            hovers.append("<br>".join([
                _name_of(names, iid), str(first.loc[key, label_col]),
                f"{AX_JOINT_VOLUME.lower()}{C.THIN_SPACE}{_fmt_vol(v)}",
                f"{HOVER_COMBINED}{C.THIN_SPACE}{_fmt_vol(combined.loc[key])}"]))
        fig.add_trace(go.Bar(
            x=xs, y=ys, orientation="h", offset=offset, width=bar_w,
            marker=dict(color=color, line=dict(color=P.SURFACE, width=C.HAIRLINE_PX)),
            text=texts, textposition="outside", cliponaxis=False,
            textfont=dict(size=C.GUTTER_FONT_PX, color=P.INK_SECONDARY),
            customdata=hovers, hovertemplate="%{customdata}<extra></extra>",
            showlegend=False))

    fig.update_layout(barmode="overlay", bargap=0)
    styled = [C.wrap_label(str(first.loc[k, label_col])) for k in order]
    _y_axis(fig, n, styled)
    n_wrapped = sum(1 for s in styled if "<br>" in s)
    vmax = vmax or 1.0
    pad = vmax * AXIS_PAD_FRAC
    if diverging:
        _bold_axes(fig, y=None)
        ticks = [t for t in C._nice_ticks(vmax) if t > 0]
        fig.update_xaxes(
            range=[-vmax - pad, vmax + pad], tickmode="array",
            tickvals=[-t for t in reversed(ticks)] + [0.0] + ticks,
            ticktext=([_fmt_vol(t) for t in reversed(ticks)] + [_fmt_vol(0.0)]
                      + [_fmt_vol(t) for t in ticks]))
    else:
        fig.update_xaxes(range=[0, vmax + pad], tickvals=C._nice_ticks(vmax))
    fig.update_xaxes(title_text=AX_JOINT_VOLUME, gridcolor=P.GRID,
                     zerolinecolor=P.GRID, linecolor=P.BORDER)
    plain = [s.replace("<br>", "\n") for s in styled]
    return C._base_layout(fig,
                          metric_row_height(n, 1 if diverging else len(series),
                                            n_wrapped=n_wrapped),
                          margin=dict(t=C.BASE_PX // 2,
                                      l=C._gutter_margin_px(plain),
                                      r=C.BASE_PX, b=C.BASE_PX))


# ---------------------------------------------------------------------------
# 12. Collaborate -- the relationship pulse (2B-R-10, section 1)
# ---------------------------------------------------------------------------
def fig_pulse(
    per_year: pd.DataFrame,
    *,
    year_col: str = "year",
    value_col: str = "co_pubs",
    bonus_year: str | None = None,
    axis_title: str | None = None,
) -> go.Figure:
    """Joint publications per year for ONE pair -- the Collaborate opener.

    ONE series, and it belongs to neither side: a co-publication is the PAIR's,
    so it wears `palette.JOINT_COLOR` rather than either institution's hue --
    2B-R3 (user ruling 5): NOT `SHARED_FRONTIER` any more, because the topic
    table on this same Collaborate page renders an ERC-SH/momentum-down
    vermillion chip, and `SHARED_FRONTIER` was re-measured to fail outright
    against that exact hue (WT_2BR3.md task 2.8). `JOINT_COLOR` is a dark
    ink-navy, never a
    red, so the two can never collide on this page again. This is also why this
    is the one figure on these two pages whose colour carries no institution
    identity at all -- there is nothing here to tell apart, which is what makes
    a single-series chart legal with no legend of its own (the page's
    institution strip still names both sides for the figures below it).

    `bonus_year` names the PARTIAL final year (2B-R-12): its bar is HATCHED
    (2B-R3: a `JOINT_COLOR` diagonal pattern on a SURFACE ground, replacing the
    old hollow SURFACE-fill-plus-outline) and its tick reads `<year>*`, the
    same partial-disclosure idiom `fig_trends_small_multiples` uses (there, on
    a hollow DOT -- a scatter marker cannot take a pattern fill, so that one
    stays hollow). The year itself is always the caller's string; this module
    never names one.

    A year with no joint publications is a REAL zero and keeps its place on the
    axis with a zero-height bar and its own value label; a year absent from the
    frame is absent from the chart. Two different facts, two different pictures.
    """
    d = per_year.copy()
    for col in (year_col, value_col):
        if col not in d.columns:
            raise ValueError(f"missing column {col!r}")
    years = [str(y) for y in d[year_col].tolist()]
    vals = [_num(v) for v in d[value_col].tolist()]
    if not years:
        raise ValueError("no years to draw")

    fig = go.Figure()
    for is_bonus in (False, True):
        xs, ys, texts, hovers = [], [], [], []
        for y, v in zip(years, vals):
            if (y == bonus_year) != is_bonus:
                continue
            xs.append(y)
            ys.append(0.0 if not np.isfinite(v) else v)
            texts.append(_fmt_vol(v))
            hovers.append(f"{C.AX_YEAR.lower()}{C.THIN_SPACE}{y}"
                          f"<br>{AX_COPUBS.lower()}{C.THIN_SPACE}{_fmt_vol(v)}")
        if not xs:
            continue
        fig.add_trace(go.Bar(
            x=xs, y=ys, width=PULSE_BAR_SPAN,
            marker=dict(color=P.SURFACE if is_bonus else P.JOINT_COLOR,
                        pattern=dict(shape=LOW_VOLUME_PATTERN_SHAPE if is_bonus else "",
                                    fgcolor=P.JOINT_COLOR,
                                    solidity=LOW_VOLUME_PATTERN_SOLIDITY),
                        line=dict(color=P.JOINT_COLOR,
                                  width=P.OUTLINE_WIDTH if is_bonus
                                  else C.HAIRLINE_PX)),
            text=texts, textposition="outside", cliponaxis=False,
            textfont=dict(size=C.GUTTER_FONT_PX, color=P.INK_SECONDARY),
            customdata=hovers, hovertemplate="%{customdata}<extra></extra>",
            showlegend=False))

    ticktext = [f"{y}{PARTIAL_YEAR_GLYPH}" if y == bonus_year else y for y in years]
    fig.update_layout(barmode="overlay", bargap=0)
    fig.update_xaxes(type="category", categoryorder="array", categoryarray=years,
                     tickmode="array", tickvals=years, ticktext=ticktext,
                     gridcolor=P.GRID, linecolor=P.BORDER)
    fig.update_yaxes(title_text=axis_title or AX_COPUBS, rangemode="tozero",
                     gridcolor=P.GRID, zerolinecolor=P.GRID, linecolor=P.BORDER,
                     automargin=True, title_standoff=6)
    return C._base_layout(fig, PULSE_HEIGHT_PX,
                          margin=dict(t=C.BASE_PX // 2, l=8, r=16, b=C.BASE_PX))


# ---------------------------------------------------------------------------
# 13. The legend strip -- rendered above EVERY compare chart (2B-R-12)
# ---------------------------------------------------------------------------
def legend_strip(ids: Sequence, *, slots: Mapping, names: Mapping | None = None,
                 shared: bool = False, shared_label: str = LABEL_SHARED,
                 extra: Sequence | None = None) -> str:
    """The institution chip strip, in slot order, for the ids actually drawn.

    2B-R-12 makes it mandatory ABOVE EVERY Compare chart rather than once per
    view: the page now scrolls through a metric selector, two frontier charts
    and a trends grid, and a legend the reader has scrolled past is not a
    legend. It is also still the secondary encoding the palette's warnings
    oblige (palette_validation.txt runs 9 and 16).

    `shared=True` appends the `palette.SHARED_FRONTIER` chip -- the pooled
    frontier map and the "who holds the shared frontier" bar are the two
    figures this names. 2B-R3: the Collaborate PULSE chart is NOT this chip any
    more (it moved to `palette.JOINT_COLOR`, never a red, so it can never be
    confused with the `SHARED_FRONTIER`/momentum-down vermillion collision
    WT_2BR3.md task 2.8 measured); a caller building the pulse page's legend
    drops the joint chip rather than asking this function for one, since
    `JOINT_COLOR` is never chip-adjacent to an institution chip.

    `extra` takes further `(label, hex)` chips for a caller that needs one; the
    hex must still come from `lib.palette`, which the app-wide hex scan enforces
    on every caller anyway."""
    order = sorted(dict.fromkeys(ids), key=lambda i: (_slot_of(slots, i), str(i)))
    items = [(_name_of(names, i), P.institution_color(_slot_of(slots, i)),
              P.institution_ink(_slot_of(slots, i))) for i in order]
    if shared:
        items.append((shared_label, P.SHARED_FRONTIER, P.SHARED_FRONTIER))
    items.extend([(str(a), str(b), P.INK_SECONDARY) for a, b in (extra or [])])
    return _chip_strip(items)


def _chip_strip(items: Sequence[tuple[str, str, str]]) -> str:
    """`charts.chip_legend_html` with a THIRD column: the ink each label is
    written in (2B-R2-2).

    Everything else is identical -- same markup, same escaping, same one-legend
    discipline -- and the fork exists for one measured reason: the institution
    fills now sit at L 0.77 / about 2:1 contrast, so a legend that painted its
    swatch in the fill and its text in the shared secondary ink would give the
    reader two things to match up by shape alone. Writing the NAME in that
    institution's dark twin (4.5:1, same hue) makes the chip and its label one
    object. `charts.py` keeps its own two-column helper untouched: the Find
    families have no twins, and nothing there needs one."""
    def esc(s: str) -> str:
        return (str(s).replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))

    chips = "".join(
        f'<span style="display:inline-flex;align-items:center;'
        f'margin-right:{C.CHIP_MARGIN_PX}px;">'
        f'<span style="width:{C.CHIP_PX}px;height:{C.CHIP_PX}px;background:{esc(hexcol)};'
        f'border-radius:{C.CHIP_RADIUS_PX}px;margin-right:{C.CHIP_GAP_PX}px;"></span>'
        f'<span style="font-size:{C.FONT_PX}px;color:{esc(ink)};">{esc(label)}</span>'
        f'</span>'
        for label, hexcol, ink in items
    )
    return (f'<div style="display:flex;flex-wrap:wrap;gap:{C.HAIRLINE_PX}px;'
            f'margin:{C.CHIP_GAP_PX}px {C.NO_PX}px;">{chips}</div>')


def map_legend_strip(ids: Sequence, *, slots: Mapping, names: Mapping | None = None,
                     color_by: str = "owner", shared: bool = True,
                     shared_label: str = LABEL_SHARED,
                     domain_items: Sequence[tuple] = ()) -> str:
    """The frontier map's legend, REBUILT on the colour-by swap (2B-R2-10).

    `color_by="owner"` returns the institution strip plus the shared chip;
    `color_by="domain"` returns the OpenAlex domain chips instead and NOTHING
    else -- not the institution chips, not the shared chip, because in that mode
    no mark carries either meaning and a legend that named them would be a
    legend for a figure that is not on screen. That swap is what keeps the
    coexistence rule true across the toggle.

    `domain_items` is a sequence of `(domain_id, label)` from the caller: the
    hue is resolved here through `palette.domain_color`, the WORDS stay with the
    page's copy module, which is the only place allowed to name a domain."""
    if color_by not in COLOR_BY:
        raise ValueError(f"color_by must be one of {COLOR_BY}, got {color_by!r}")
    if color_by == "domain":
        return _chip_strip([(str(label), P.domain_color(did), P.INK_SECONDARY)
                            for did, label in domain_items])
    return legend_strip(ids, slots=slots, names=names, shared=shared,
                        shared_label=shared_label)


# ---------------------------------------------------------------------------
# 14. Presentation primitives (2B-R2-8) -- the reading line and the KPI dot
# ---------------------------------------------------------------------------
def chart_note(reading: str, tooltip: str | None = None) -> str:
    """ONE short reading line under a chart, with the methodology folded into a
    `?` the reader can hover.

    THE PROBLEM IT SOLVES (2B-R2-8): every panel had grown a grey paragraph
    above it and another below -- window definitions, counting bases, floors,
    caveats -- and a reader who must read four lines of prose before a chart
    reads neither. The split this helper enforces is: what the chart SAYS stays
    visible; what the chart IS made of goes behind the `?`.

    IT REFUSES A WALL OF PROSE, on purpose. A `reading` longer than
    `NOTE_MAX_CHARS`, or one containing a line break, raises `ValueError`. A
    silent truncation would let the wall back in one release later, and a
    soft-wrapped three-line "note" is the exact thing 2B-R2-8 deletes. The
    tooltip has no cap -- it is the place the long text is SUPPOSED to go.

    Returns markup (this module never imports Streamlit); the page hands it to
    `st.markdown(..., unsafe_allow_html=True)`. The `?` carries its payload in
    `title=`, so it works with no script and reads out as text to a screen
    reader, and it is a `<span>` rather than an emoji so it inherits the ink."""
    text = " ".join(str(reading).split())
    if not text:
        raise ValueError("a chart note needs a reading line")
    if "\n" in str(reading).strip() or len(text) > NOTE_MAX_CHARS:
        raise ValueError(f"a chart note is ONE short line of at most "
                         f"{NOTE_MAX_CHARS} characters; put the rest in the "
                         f"tooltip (got {len(text)})")

    def esc(s: str) -> str:
        return (str(s).replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))

    help_span = ""
    if tooltip:
        payload = " ".join(str(tooltip).split())
        help_span = (
            f'<span title="{esc(payload)}" role="note" '
            f'style="display:inline-flex;align-items:center;justify-content:center;'
            f'width:{C.FONT_PX}px;height:{C.FONT_PX}px;margin-left:{DOT_GAP_PX}px;'
            f'border:{C.HAIRLINE_PX}px solid {P.BORDER};border-radius:{C.FONT_PX}px;'
            f'font-size:{C.GUTTER_FONT_PX}px;color:{P.INK_SECONDARY};'
            f'cursor:help;">{NOTE_HELP_GLYPH}</span>')
    return (f'<div style="display:flex;align-items:center;'
            f'font-size:{C.FONT_PX}px;color:{P.INK_SECONDARY};'
            f'margin:{C.CHIP_GAP_PX}px {C.NO_PX}px;">'
            f'<span>{esc(text)}</span>{help_span}</div>')


def basis_caption(text: str, *, warn: bool = False) -> str:
    """D5 (CHROME_CONTRACT.md §7, 2C Stream VC): the ratio-chart basis/floor/
    coverage line -- ONE per chart, directly under the section title, ABOVE
    the legend and the chart. Same visual family as `chart_note`'s reading
    line (`INK_SECONDARY`, `FONT_PX`, weight 400) in its normal state; this is
    a SEPARATE `<div>`, never merged into `chart_note`'s own 160-character
    cap, because it states a fact about the DATA (basis, floor, how many taxa
    are unscored) where `chart_note` states how to READ the chart -- keeping
    the two apart is what keeps `chart_note` short.

    `warn=True` (a floor bites, or a taxon is unscored) switches the colour to
    `palette.WARNING_CAPTION_COLOR` -- D5's own wording: red, NEVER bold
    (weight stays 400), NEVER a `st.warning`/`st.error` banner (those carry an
    icon+box chrome this contract does not otherwise use for a one-line
    caption). The normal state never uses this colour."""
    def esc(s: str) -> str:
        return (str(s).replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))

    color = P.WARNING_CAPTION_COLOR if warn else P.INK_SECONDARY
    return (f'<div style="font-size:{C.FONT_PX}px;font-weight:{CAPTION_FONT_WEIGHT};'
            f'color:{color};margin:{C.CHIP_GAP_PX}px {C.NO_PX}px;">{esc(text)}</div>')


def best_value_dot(slot, label: str | None = None) -> str:
    """The Compare overview card's leader mark (2B-R2-9): a small dot in the
    LEADING institution's colour, optionally followed by that institution's name
    in its dark twin.

    Why a dot and not a tint. A tinted card would paint a large area in a hue
    that is 2:1 against the surface -- unreadable as identity, and it would put
    the institution's colour behind the card's own numbers, which belong to
    every compared institution rather than to the leader. The dot is a MARK: it
    sits beside the value, it is the same object the chart below draws, and the
    card's numbers stay in ink. Measured in A/B `2br2_dot_{a,b}` and read.

    `slot` is the zero-based slot (`palette.institution_slots`), so the dot on a
    card and the bar in the chart below it cannot disagree. An unknown slot
    yields COMPARISON grey and INK_SECONDARY text, the module-wide convention."""
    def esc(s: str) -> str:
        return (str(s).replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))

    dot = (f'<span style="display:inline-block;width:{DOT_HTML_PX}px;'
           f'height:{DOT_HTML_PX}px;border-radius:{DOT_HTML_PX}px;'
           f'background:{P.institution_color(slot)};'
           f'border:{P.OUTLINE_WIDTH}px solid {P.SURFACE};"></span>')
    if not label:
        return dot
    return (f'<span style="display:inline-flex;align-items:center;'
            f'gap:{DOT_GAP_PX}px;font-size:{C.GUTTER_FONT_PX}px;'
            f'color:{P.institution_ink(slot)};">{dot}'
            f'<span>{esc(label)}</span></span>')

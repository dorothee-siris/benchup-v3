"""
app/lib/views_collab.py -- render functions for the Collaborate page
(BUILD_PLAN_2BR3.md, Phase 2B-R3, stream VL; rulings 3/4/6 and the
ruled-without-grill Collaborate list in
SIRIS/brainstorms/2026-08-31-benchup-gate2br3-refinement.md).

COMPOSITION ONLY, same rule as lib/views_find.py: every frame comes from
`lib/collab_data.py`, every id/pair/basket rule from `lib/selection.py` and
`lib/state.py`, every URL from `lib/links.py`, every string from
`lib/copy.py`, every colour from `lib/palette.py`. Nothing here recomputes a
number and nothing here types one into a rendered string (BUILD_PLAN_2A.md
L10, enforced by tests/test_narrative.py, which globs lib/views_*.py).

PAGE SHAPE (2BR3 VL), a reader meets the pair immediately, not after a
multi-step picker:

  0. title + one-line promise -> the shared sidebar search/basket
     (`selection.render_sidebar()`) -> `selection.slots_row("collab", 2)`,
     the ONE picker this page owns (two selectboxes over the basket, no
     free-text search of its own -- SEL's fence).
  1. the TWO institution identity cards, each rendered the moment ITS OWN
     slot is filled (never gated on the pair being complete), with the pair
     MOMENTUM headline above them once BOTH slots are filled: a big
     coloured glyph+text from `collab_data.momentum_display` (via
     `collab_data.pair_momentum`), then the evidence block in small grey
     type -- both window shares, the raw co-publication counts and the
     significance test, every number and every window off `collab_pairs.
     parquet` v2 / `collab_facts.json` / `compare_data.DYNAMICS_W1`/`W2`,
     never hardcoded here;
  2. "The relationship, year by year" -- the pulse chart, legend = the
     JOINT chip ONLY (2BR3 task 2: the bars are the pair's, not either
     side's, so the strip no longer carries the two institution chips that
     used to sit beside a joint-only series);
  3. "The joint corpus, field by field" -- ONE domain-coloured bar chart
     (the Find idiom: a mark's colour names its OpenAlex domain, same as
     `charts.fig_topics`/`fig_share_si(family="oa")`); the field TABLE is
     gone, the chart IS the field-level view (`collab_data.field_breakdown`
     the DATA function is unchanged, only this page's table renderer died);
  4. "Strategic reciprocity by field" -- a bubble scatter, ported from the
     Lorraine "Zoom partenaire" page (see the brainstorm file above): x =
     a field's share of B's OWN portfolio, y = the same field's share of
     A's OWN portfolio (both `collab_data.reciprocity_frame`, the HONEST
     both-sides variant), area = the pair's joint volume in that field,
     colour = OpenAlex domain, squared axes, one dotted equal-weight
     diagonal;
  5. the topic deep dive -- a native, sortable `st.dataframe` (Topic,
     Domain, Joint publications, In the world top decile, SDG-tagged,
     Median FWCI, Momentum, a link to OpenAlex per row), 20 rows by default
     with a "Show all" button (no slider -- a slider was a performance
     device, not a control the reader meant to turn);
  6. untapped potential -- the same 20-then-show-all dataframe treatment,
     same fixed gap-descending ranking (2C VL: the "Adjacent topics in the
     same subfields" expander that used to sit beside it is REMOVED -- D8, a
     grill ruling -- the untapped table itself is unchanged);
  7. bottom meta, collapsed by default: the page's own method note, the
     "not shown here, and why" block, and the shareable link
     (`lib.links.share_link_block`).

DELETED THIS ROUND (2BR3 VL, all binding user asks): the old free-text
"add a comparator" flow and the two-selectbox A/B picker with its swap
button (replaced end to end by `selection.slots_row`); the field TABLE
(the chart is now the whole of section 3); every row slider (replaced by
the 20-then-show-all pattern); the "Read the publications on OpenAlex"
closing section (per-row OpenAlex links already sit on every topic and
gap row; the two whole-corpus and one co-publication link buttons this
section used to carry are gone with it).

DELETED THIS ROUND (2C VL, D8): "Adjacent topics in the same subfields",
the one hand-built HTML table this page still carried -- its own expander,
its own data-layer output (`collab_data.untapped` produced an extra frame
for exactly this table, now gone from that function entirely) and every
render helper that existed only to draw it (the table builder itself, its
row-building helper, and the small canvas-table primitives underneath both --
a chip span, a taxon-name-plus-chip cell and a sticky header cell --
unreferenced once the table above them is gone). Both surviving tables (the
topic deep dive and untapped) were already native, sortable `st.dataframe`
grids before this round and needed no rework for the removal itself.

WHY A SMALL NEW CHART BUILDER LIVES HERE, TWICE, RATHER THAN IN
`lib/charts.py`. `charts.fig_topics`/`fig_share_si` colour marks by OpenAlex
domain exactly the way section 3's chart needs -- but both hard-code a SHARE
axis (a percent tick format, a "Share of output" title): this page's field
chart is a raw joint-publication COUNT, not a share, so neither builder fits
without editing `charts.py` (outside this stream's fence). Section 4's
reciprocity scatter has no analogue anywhere in the app at all (squared
axes, an equal-weight diagonal, two independent share axes). Both builders
below are small, reuse `charts.py`'s own layout/margin/height helpers for a
consistent look, and touch no other file.

SIDEBAR: counting & taxonomy (the SAME widget keys `tree`/`basis` the Find
page uses, so the scenario carries across pages) + the ONE shared
sidebar search/basket (`selection.render_sidebar()`) every page now calls.

PERFORMANCE (2B-14: warm rerun < 1.5 s)
  `views_find._bundle`/`_subs` are reused BY IMPORT, not copied, so the
  engine context and each (tree, basis) substrate load once per process and
  are shared with the Find page rather than paid again here. The frames are
  `@st.cache_data` keyed on (a, b, tree, basis) -- ctx/subs are unhashable
  and are never cache_data arguments -- so moving either toggle re-renders
  the tables without recomputing anything.
"""
from __future__ import annotations

from urllib.parse import quote

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib import charts as C
from lib import charts_compare as X
from lib import collab_data, copy, countries, links, profile_data, selection, state
from lib import palette as P
from lib.app_config import CFG
from lib.compare_data import DYNAMICS_W1, DYNAMICS_W2
from lib.palette import NA_MARK
from lib.ranked import PCT_PROGRESS_FORMAT
from lib.views_find import BONUS_STAR, SEP, _bundle, _sidebar_scenario, _subs

# The en dash between the two ends of a window label ("2020-2025" rendered
# with a real dash) and the rightwards arrow the momentum evidence line
# draws between its two co-publication counts -- module constants, composed
# at render time, never baked into a copy.py string (the same idiom `SEP`,
# imported above, already follows).
DASH = "\N{EN DASH}"
ARROW = "\N{RIGHTWARDS ARROW}"

# D4/D5 (Phase 2C): the CORE-AR window every section on this page reads
# EXCEPT the pulse (`copy.COLLAB["PULSE_BASIS_CAPTION"]` states that one
# exception explicitly, in its own caption, never silently).
WINDOW_START, WINDOW_END = CFG["window"]

# A pulse difference smaller than this reads as "the same annual rate"
# rather than as a direction: the two windows are 3 and 2 years long, so a
# few papers of noise on a small pair would otherwise be rendered as a
# trend. Stated on the page through `COLLAB["PULSE_TREND_NOTE"]`, never
# typed into a caption.
TREND_BAND = 0.10

# --- the pair momentum headline (section 1) ---------------------------------
MOMENTUM_TEXT_PX = 28     # the "big coloured text" the brief asks for
MOMENTUM_WEIGHT = 700
PVAL_FLOOR = 0.001        # below this, the significance line reads "< 0.001"
                          # rather than a rounded-to-zero p

# Field/topic-grain momentum carries CLASS ONLY, never a percentage (SS2.3:
# "class only (no % chip)" -- `collab_pair_fields`/`collab_pair_topics` v2
# carry no mom_rr/mom_p at this grain, only `mom_class`). This is why the
# per-row cell below is its OWN small word map rather than a call into
# `collab_data.momentum_display` (the PAIR-grain 9-case ladder): that
# function's up/down/stable branch needs a real `mom_rr` to format a
# percentage, and with none supplied it would silently read a genuine "up"
# row as the null case. Colour and glyph still come from `lib.palette`, the
# one source for both.
MOMENTUM_CLASS_WORD = {
    "up": "up", "down": "down", "stable": "stable", "ns": "n.s.",
    "new": "new", "dormant": "dormant", "weak": "weak base",
}

# --- the field chart (section 3) --------------------------------------------
AXIS_PAD_MULT = 1.02      # a little headroom past the longest bar

# --- the reciprocity scatter (section 4) ------------------------------------
RECIP_AXIS_PAD_MULT = 1.1   # squared axes [0, max * 1.1] both, per the brief
RECIP_DIAGONAL_DASH = "dot"
BUBBLE_OUTLINE_PX = 0.5     # the white outline the brief asks for

# --- the topic deep dive / untapped tables (sections 5-6) -------------------
ROWS_DEFAULT = 20           # rows shown before a reader asks for the rest
VOL_FORMAT = "%d"           # a whole joint-publication count
FRAC_VOL_FORMAT = "%.1f"    # untapped's own fractional-volume grain
FWCI_FORMAT = "%.2f"
# D9 (Phase 2C, CHROME-F): `format="percent"` is BANNED (locale-dependent,
# confirmed rendering comma-decimals live) -- `lib.ranked.PCT_PROGRESS_FORMAT`
# is the ONE shared printf-style spec every such column in the app uses, so
# this page's own progress columns render identically to the rest of the
# tool rather than inventing a second convention. Its contract: the
# CALLER'S OWN dataframe column carries the value already scaled 0-100 (see
# `_topics_display_frame`'s `top10_share`/`sdg_share`), never the raw 0-1
# fraction `PROGRESS_MIN`/`PROGRESS_MAX` used to describe before this fix.
PROGRESS_MIN, PROGRESS_MAX = 0, 100

# D10/CHROME_CONTRACT.md S8: the app's ONE canonical row-link idiom
# (`ranked.py`'s A10 fragment trick) -- a `#<urlencoded name>` fragment on an
# already-built URL, read back by `LinkColumn`'s `display_text=` regex so the
# row's own subject becomes the clickable link. Mirrored here (2C VL,
# chrome-audit L8) so the topic/untapped tables' link column stops being a
# second, different idiom from every other ranked table in the app.
NAME_LINK_DISPLAY_RE = r"#(.*)$"


# ------------------------------------------------------------- frames -------
# One @st.cache_data per table, keyed on the HASHABLE scenario identity
# (a, b, tree, basis) -- ctx/subs are never cache_data arguments. `st.dataframe`
# and every widget touch reruns the whole script, so an uncached frame would
# be recomputed on every click.

@st.cache_data(show_spinner=False, max_entries=48)
def _pulse_frame(a: str, b: str) -> dict | None:
    """`pulse` needs no substrate (it reads one row of `collab_pairs` plus
    the index), so it is keyed on the pair alone and survives a tree/basis
    flip."""
    return collab_data.pulse(_bundle()["ctx"], a, b)


@st.cache_data(show_spinner=False, max_entries=48)
def _momentum_frame(a: str, b: str) -> dict | None:
    """Same reasoning as `_pulse_frame`: momentum reads `collab_pairs` and
    `index` alone, no substrate."""
    return collab_data.pair_momentum(_bundle()["ctx"], a, b)


@st.cache_data(show_spinner=False, max_entries=48)
def _fields_frame(a: str, b: str) -> pd.DataFrame:
    """The pair x field breakdown. Best-fit only by construction (the
    shipped table carries one tree), so this frame -- alone on the page --
    is NOT keyed on the tree, and the section's tooltip says so."""
    return collab_data.field_breakdown(_bundle()["ctx"], a, b)


@st.cache_data(show_spinner=False, max_entries=24)
def _reciprocity_frame(a: str, b: str, tree: str, basis: str) -> pd.DataFrame:
    return collab_data.reciprocity_frame(_bundle()["ctx"], _subs(tree, basis), a, b)


@st.cache_data(show_spinner=False, max_entries=24)
def _joint_frame(a: str, b: str, tree: str, basis: str) -> dict | None:
    """`None` means BELOW THE TOPIC FLOOR (or never co-published) -- the
    page renders the honest notice rather than an empty table."""
    return collab_data.joint_profile(_bundle()["ctx"], _subs(tree, basis), a, b)


@st.cache_data(show_spinner=False, max_entries=24)
def _untapped_frame(a: str, b: str, tree: str, basis: str) -> dict:
    return collab_data.untapped(_bundle()["ctx"], _subs(tree, basis), a, b)


# --------------------------------------------------------- formatting -------

def _pct(value) -> str:
    if value is None or pd.isna(value):
        return NA_MARK
    return f"{float(value):.1%}"


def _count(value) -> str:
    if value is None or pd.isna(value):
        return NA_MARK
    return f"{value:,.0f}"


def _named_link(url: str, name) -> str:
    """The app's ONE canonical row-link idiom (`NAME_LINK_DISPLAY_RE`'s own
    docstring above): appends a `#<urlencoded name>` fragment to an
    already-built OpenAlex URL -- inert for OpenAlex itself (a fragment
    never reaches the server) -- so a `LinkColumn`'s `display_text=
    NAME_LINK_DISPLAY_RE` renders the row's own subject, here a topic name,
    as the clickable text instead of a separate trailing "Open" column."""
    return f"{url}#{quote(str(name), safe='')}"


def _band(value) -> str:
    """The arrow deadband as a plain number for a caption."""
    return f"{float(value):g}"


def _pval(value) -> str:
    if value is None or pd.isna(value):
        return NA_MARK
    v = float(value)
    return f"{v:.3f}" if v >= PVAL_FLOOR else f"< {PVAL_FLOOR:.3f}"


def _name(ctx: dict, iid: str) -> str:
    return str(ctx["index_by_id"].loc[iid, "display_name"])


def _window(years) -> str:
    """"first{dash}last" for a window handed in as a (start, end) pair or as
    a list of years. The years come from `collab_data.PULSE_YEARS` and
    `lib.compare_data`'s dynamics constants, so no window is ever typed
    here."""
    ys = list(years)
    return f"{ys[0]}{DASH}{ys[-1]}"


def _window_mean(yearly: pd.DataFrame, window) -> float:
    """Mean annual joint volume over an inclusive (start, end) year window,
    read off the pulse frame the chart itself draws."""
    by_year = dict(zip(yearly["year"], yearly["copubs"]))
    years = range(window[0], window[1] + 1)
    return float(sum(float(by_year.get(y, 0.0)) for y in years) / len(list(years)))


def _trend_line(yearly: pd.DataFrame) -> str:
    """The one plain-language pulse sentence. It is a DATA question,
    answered by comparing the two dynamics windows the rest of the tool
    already uses (`compare_data.DYNAMICS_W1`/`W2`, partial year excluded),
    and phrased in neutral vocabulary: a direction and a size, never a
    judgement about the relationship."""
    w1 = _window_mean(yearly, DYNAMICS_W1)
    w2 = _window_mean(yearly, DYNAMICS_W2)
    words = {"w1": _window(DYNAMICS_W1), "w2": _window(DYNAMICS_W2)}
    if not w1 > 0:
        return copy.COLLAB["PULSE_TREND_NA"].format(**words)
    change = (w2 - w1) / w1
    if abs(change) < TREND_BAND:
        key = "PULSE_TREND_FLAT"
    else:
        key = "PULSE_TREND_UP" if change > 0 else "PULSE_TREND_DOWN"
    return copy.COLLAB[key].format(pct=_pct(abs(change)), **words)


def _momentum_cell(mom_class) -> tuple[str, str, str]:
    """Field/topic-grain momentum: CLASS ONLY, never a percentage (see the
    MOMENTUM_CLASS_WORD note above). Returns (text, hex, glyph)."""
    if mom_class is None or (isinstance(mom_class, float) and pd.isna(mom_class)):
        return collab_data.MOMENTUM_NULL_TEXT, P.momentum_color(None), P.momentum_glyph(None)
    word = MOMENTUM_CLASS_WORD.get(str(mom_class), collab_data.MOMENTUM_NULL_TEXT)
    return word, P.momentum_color(mom_class), P.momentum_glyph(mom_class)


def _domain_order(domain_id) -> int:
    """The taxonomy's OWN fixed domain order (`palette.OA_DOMAIN_ORDER`),
    which is what the field chart and the reciprocity legend group by. An
    unknown or unclassified domain sorts last rather than first."""
    order = list(P.OA_DOMAIN_ORDER)
    try:
        return order.index(int(domain_id))
    except (TypeError, ValueError):
        return len(order)


def _domain_items(frame: pd.DataFrame) -> list[tuple]:
    """`(domain_id, domain_name)` for the domains a frame actually carries,
    in the taxonomy's own order -- the legend the field chart and the
    reciprocity scatter are both read against. The WORDS are the
    taxonomy's own, off the frame."""
    seen = {}
    for did, dname in zip(frame["domain_id"], frame["domain_name"]):
        if pd.isna(did):
            continue
        seen.setdefault(int(did), str(dname))
    return [(d, seen[d]) for d in P.OA_DOMAIN_ORDER if d in seen]


def _erc_panel_label(ctx: dict, panel_code) -> str:
    """The ERC panel's readable name for the code the pair table carries
    (`erc_top_panel`), read off the same `resources/erc_panels.csv` the
    profile's own ERC table joins."""
    if panel_code is None or (not isinstance(panel_code, str) and pd.isna(panel_code)):
        return NA_MARK
    panels = profile_data._erc_panels(ctx)
    hit = panels[panels["panel_code"].astype(str) == str(panel_code)]
    if hit.empty:
        return str(panel_code)
    return f"{panel_code} {SEP} {hit.iloc[0]['panel_label']}"


def _esc(value) -> str:
    return (str(value).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _note(reading: str, tooltip: str | None = None) -> None:
    """ONE short reading line, the methodology behind its `?`."""
    st.markdown(X.chart_note(reading, tooltip), unsafe_allow_html=True)


def _basis_caption(text: str, *, warning: bool = False) -> None:
    """D5's new one-line disclosure (CHROME_CONTRACT.md S7): corpus basis
    (and, where it applies, a floor or a coverage gap), sitting ABOVE the
    legend/chart -- a NEW line, never merged into `_note`'s single reading
    line, since the two say different things (this states a fact about the
    DATA, `_note` states how to read the chart). Same small type as `_note`'s
    own reading line in the normal state (`INK_SECONDARY`, `FONT_PX`, regular
    weight); switches to PAL's frontier red -- never bold, no icon box -- when
    the fact itself is a warning (a below-floor or coverage caveat)."""
    color = P.WARNING_CAPTION_COLOR if warning else P.INK_SECONDARY
    st.markdown(
        f'<div style="font-size:{C.FONT_PX}px;color:{color};'
        f'margin:{C.CHIP_GAP_PX}px {C.NO_PX}px;">{_esc(text)}</div>',
        unsafe_allow_html=True)


def _rows_note(n_shown: int, n_total: int) -> None:
    st.caption(copy.COLLAB["TABLE_ROWS_NOTE"].format(
        n_shown=_count(n_shown), n_total=_count(n_total)))


def _visible_row_count(n_total: int, show_all: bool) -> int:
    """Pure: how many of `n_total` rows to show. Split out from the
    Streamlit-touching functions below so the 20-default/show-all RULE is
    unit-testable with no Streamlit runtime (the same split
    `selection.resolve_slot_hydration` uses against `slots_row`)."""
    return n_total if (show_all or n_total <= ROWS_DEFAULT) else ROWS_DEFAULT


def _show_all_flag(n_total: int, key: str) -> bool:
    """Read-only: has this table already been expanded this session? A
    table with nothing to hide behind the default is always 'expanded'."""
    if n_total <= ROWS_DEFAULT:
        return True
    st.session_state.setdefault(key, False)
    return bool(st.session_state[key])


def _show_all_button(n_total: int, key: str) -> None:
    """The ONE 'Show all N' button (2BR3 tasks 5/6: sliders retired -- a
    performance device, not a control). Renders nothing once expanded, or
    when there is nothing to expand into."""
    if n_total <= ROWS_DEFAULT or st.session_state.get(key):
        return
    if st.button(copy.COLLAB["SHOW_ALL_BUTTON"].format(n=_count(n_total)), key=f"{key}_btn"):
        st.session_state[key] = True
        st.rerun()


# ------------------------------------------------------------- sidebar ------
# `selection.render_sidebar()` (called from `render()` below) is the ONE
# shared sidebar search + basket every page now calls -- this page adds
# nothing of its own.


# ---------------------------------------------------------- 0. header -------

def _header() -> None:
    """Title and one-line promise -- nothing else. The dataset line, the
    method notes and the share link move to the bottom meta section
    (`_render_meta`, 2BR3 layout ruling: 'title + slots/content
    IMMEDIATELY')."""
    st.title(copy.NAV["COLLAB_LABEL"])
    st.caption(copy.NAV["COLLAB_LEAD"])


# ------------------------------------------------- 1. identity + momentum ---

def _swatches(ctx: dict, ids: list[str]) -> dict:
    """`{institution_id: css colour}` by SLOT position (2BR3 plan item 6,
    manager merge fix, same rule as Compare's `_slots`): slot 1 = the darkest
    navy, the order the reader's own slot pickers show on screen -- never an
    internal key. `ids` arrives in picker order."""
    if not (hasattr(P, "INSTITUTION_COLORS") and hasattr(P, "institution_color")):
        return {}
    try:
        return {i: P.institution_color(pos) for pos, i in enumerate(ids)}
    except Exception:  # a palette shape this page does not know: show no swatch
        return {}


SWATCH_MARK = "\N{BLACK CIRCLE}"


def _identity(col, ctx: dict, iid: str, colour: str | None) -> None:
    row = ctx["index_by_id"].loc[iid]
    # A coloured GLYPH, not a styled box: an inline box would need pixel
    # lengths, i.e. typed digits inside a string a Streamlit call renders,
    # which is exactly what the digit-ban forbids. The only value
    # interpolated here is the palette's own colour.
    dot = f'<span style="color:{colour}">{SWATCH_MARK}</span> ' if colour else ""
    col.markdown(f"{dot}**{_name(ctx, iid)}**", unsafe_allow_html=True)
    col.caption(f"{str(row['type'])} {SEP} {countries.name(str(row['country_code']))}")
    col.caption(f"{copy.FIND['COL_SIZE_FULL']}: {_count(row['total_full_2020_2024'])} {SEP} "
                f"{copy.FIND['COL_SIZE_FRAC']}: {_count(row['total_frac_2020_2024'])}")


def _momentum_block(ctx: dict, mom: dict) -> None:
    """The pair momentum headline (2BR3 task 1): a big coloured glyph+text
    from `collab_data.pair_momentum`, then the Lorraine evidence block in
    small grey type -- both window shares (with their window labels), the
    raw co-publication counts and the significance test. Every number and
    every window comes from `mom` (itself `collab_pairs` v2 + `index`'s own
    CORE-AR window totals) or `collab_facts.json`'s own `alpha` -- nothing
    here is hardcoded."""
    facts = collab_data._load_collab_facts(ctx)
    with st.container(key="collab_momentum"):
        # 2C chrome-audit fix (L5): a real `st.subheader`, not a `st.caption`
        # label -- this headline is a SECTION, the same level as every other
        # section on the page, not a small aside above one. The three
        # evidence lines that used to stack as separate `st.caption`s below
        # the big number are folded into ONE `_note` reading+tooltip instead
        # (the SAME fold this file's own `chart_note` already gives every
        # other section) -- exactly the "grey paragraph" pattern 2B-R2-8
        # deleted from Compare, now deleted here too.
        st.subheader(copy.COLLAB["MOMENTUM_LABEL"])
        st.markdown(
            f'<div style="font-size:{MOMENTUM_TEXT_PX}px;font-weight:{MOMENTUM_WEIGHT};'
            f'color:{mom["color"]};">{_esc(mom["glyph"])} {_esc(mom["text"])}</div>',
            unsafe_allow_html=True)
        w1_share = (mom["c1"] / mom["d1"]) if mom["d1"] else float("nan")
        w2_share = (mom["c2"] / mom["d2"]) if mom["d2"] else float("nan")
        # Annual means (windows are 3y vs 2y -- raw totals always read as a
        # drop); year counts derived from the window tuples, never typed.
        n1 = DYNAMICS_W1[1] - DYNAMICS_W1[0] + 1
        n2 = DYNAMICS_W2[1] - DYNAMICS_W2[0] + 1
        tooltip = " ".join([
            copy.COLLAB["MOMENTUM_EVIDENCE_SHARE"].format(
                w1=_window(DYNAMICS_W1), share1=_pct(w1_share),
                w2=_window(DYNAMICS_W2), share2=_pct(w2_share), sep=SEP) + ".",
            copy.COLLAB["MOMENTUM_EVIDENCE_COPUBS"].format(
                c1=_count(mom["c1"] / n1), c2=_count(mom["c2"] / n2), arrow=ARROW) + ".",
            copy.COLLAB["MOMENTUM_EVIDENCE_SIGNIFICANCE"].format(
                p=_pval(mom["mom_p"]), alpha=_pct(facts["alpha"])) + ".",
        ])
        _note(copy.COLLAB["MOMENTUM_READING"], tooltip)


def _render_header_block(bundle: dict, a: str | None, b: str | None) -> None:
    """Section 1: each identity card renders the moment ITS OWN slot is
    filled, never gated on the pair being complete; the momentum headline
    sits above the two cards and appears only once both are."""
    ctx = bundle["ctx"]
    present = [i for i in (a, b) if i]
    if a and b:
        mom = _momentum_frame(a, b)
        if mom is not None:
            _momentum_block(ctx, mom)
    with st.container(key="collab_header", border=True):
        colours = _swatches(ctx, present) if present else {}
        cols = st.columns(2)
        if a:
            _identity(cols[0], ctx, a, colours.get(a))
        if b:
            _identity(cols[1], ctx, b, colours.get(b))


def _below_floor_notice(n_copubs) -> None:
    """The shared below-floor wording, at the floor the pair tables actually
    ship with (`collab_data.PAIR_TOPICS_FLOOR`), never a floor typed here or
    in copy.py."""
    st.info(copy.SHARED["BELOW_FLOOR_NOTICE"].format(
        item=copy.COLLAB["BELOW_FLOOR_ITEM"], n=_count(n_copubs),
        floor=collab_data.PAIR_TOPICS_FLOOR))


# ------------------------------------------- 2. the relationship pulse ------

def _render_pulse(bundle: dict, a: str, b: str) -> dict | None:
    """Section 2: the pair's joint publications per year, each side's joint
    share of its OWN output with both denominators named, the two ranks in
    their two directions, and one plain-language line about the movement.
    Returns the pulse frame so the sections below can reuse the joint total
    rather than read the same row twice.

    LEGEND (2BR3 task 2): the joint chip ONLY. The bars are the pair's, not
    either side's, so a strip that also carried both institution chips beside
    a joint-only series was reading as a contradiction -- `legend_strip([],
    ...)` with `shared=True` returns exactly the one chip."""
    ctx = bundle["ctx"]
    st.subheader(copy.COLLAB["PULSE_HEADER"])
    row = _pulse_frame(a, b)
    if row is None:
        st.info(copy.COLLAB["EMPTY_PULSE"].format(a=_name(ctx, a), b=_name(ctx, b)))
        return None

    # D4/D5 chrome-audit fix (L7): the pulse's own basis EXCEPTION, stated
    # ABOVE the legend, before a reader can mistake this chart's window for
    # the CORE-AR one every section below it uses.
    _basis_caption(copy.COLLAB["PULSE_BASIS_CAPTION"].format(
        w1=_window(collab_data.PULSE_YEARS), y0=WINDOW_START, y1=WINDOW_END))
    with st.container(key="collab_legend"):
        st.markdown(X.legend_strip([], slots={}, shared=True,
                                   shared_label=copy.COLLAB["LEGEND_JOINT"]),
                    unsafe_allow_html=True)
    st.plotly_chart(X.fig_pulse(row["yearly"], value_col="copubs",
                                bonus_year=str(CFG["bonus_year"]),
                                axis_title=copy.COLLAB["PULSE_AXIS"]),
                    width="stretch", key="fig_pulse")
    _note(copy.COLLAB["PULSE_CHART_READING"],
          copy.COLLAB["PULSE_CHART_CAPTION"].format(bonus_year=CFG["bonus_year"],
                                                    star=BONUS_STAR))

    names = {a: _name(ctx, a), b: _name(ctx, b)}
    cols = st.columns(3)
    cols[0].metric(copy.COLLAB["PULSE_TOTAL_LABEL"], _count(row["copubs_total"]))
    cols[1].metric(copy.COLLAB["PULSE_SHARE_LABEL"].format(name=names[a]), _pct(row["share_of_a"]))
    cols[2].metric(copy.COLLAB["PULSE_SHARE_LABEL"].format(name=names[b]), _pct(row["share_of_b"]))
    st.caption(copy.COLLAB["PULSE_SHARE_DENOM"].format(
        window=_window(collab_data.PULSE_YEARS), name_a=names[a], name_b=names[b],
        vol_a=_count(row["denominator_a"]), vol_b=_count(row["denominator_b"])))
    # DIRECTION: `rank_in_a` is where B sits among A's OWN partners, so it is
    # rendered as B's rank, never as A's.
    st.markdown(copy.COLLAB["PULSE_RANK_LINE"].format(
        name_a=names[a], name_b=names[b],
        rank_of_b=_count(row["rank_in_a"]), rank_of_a=_count(row["rank_in_b"])))
    st.markdown(_trend_line(row["yearly"]))
    st.caption(copy.COLLAB["PULSE_TREND_NOTE"].format(
        w1=_window(DYNAMICS_W1), w2=_window(DYNAMICS_W2), band=_pct(TREND_BAND),
        bonus_year=CFG["bonus_year"], star=BONUS_STAR))
    return row


# --------------------------------- 3. the joint corpus, field by field ------

def _fields_chart(fields: pd.DataFrame):
    """One horizontal bar per field, coloured by its OpenAlex DOMAIN -- the
    Find idiom (module docstring: no builder in `charts.py` fits a raw
    joint-publication COUNT, so this small one lives here). Rows are
    grouped under their domain in the taxonomy's own fixed order, largest
    first inside each domain."""
    d = fields.copy()
    d["domain_order"] = [_domain_order(v) for v in d["domain_id"]]
    d = d.sort_values(["domain_order", "vol"], ascending=[True, False],
                      kind="mergesort").reset_index(drop=True)
    n = len(d)
    names = [str(v) for v in d["field_name"]]
    colors = [P.domain_color(v) for v in d["domain_id"]]
    vals = pd.to_numeric(d["vol"], errors="coerce").to_numpy(dtype=float)
    axis_label = copy.COLLAB["PULSE_AXIS"].lower()
    hover = [f"{names[i]}<br>{axis_label}{C.THIN_SPACE}{_count(vals[i])}" for i in range(n)]

    fig = go.Figure(go.Bar(
        x=vals, y=names, orientation="h",
        marker=dict(color=colors, line=dict(color=P.SURFACE, width=C.HAIRLINE_PX)),
        text=[_count(v) for v in vals], textposition="outside", cliponaxis=False,
        textfont=dict(size=C.GUTTER_FONT_PX, color=P.INK_SECONDARY),
        customdata=hover, hovertemplate="%{customdata}<extra></extra>", showlegend=False))
    fig.update_yaxes(tickmode="array", tickvals=names, ticktext=names,
                     autorange="reversed", showgrid=False, automargin=True)
    xmax = float(np.nanmax(vals)) if n and np.isfinite(vals).any() else 1.0
    xmax = xmax if xmax > 0 else 1.0
    fig.update_xaxes(range=[0, xmax * AXIS_PAD_MULT], title_text=copy.COLLAB["PULSE_AXIS"],
                     gridcolor=P.GRID, zerolinecolor=P.GRID, linecolor=P.BORDER)
    margin_l = C._gutter_margin_px(names)
    return C._base_layout(fig, C.row_height(n),
                          margin=dict(t=C.BASE_PX // 2, l=margin_l, r=16, b=C.BASE_PX))


def _render_fields(bundle: dict, a: str, b: str, pulse_row: dict | None) -> None:
    """Section 3 (2BR3 task 3): the field breakdown of the joint corpus, as
    ONE domain-coloured chart -- the field TABLE is gone, the chart is the
    whole of this section. Below the topic floor the section is the honest
    notice and nothing else -- no empty chart, no zero."""
    st.subheader(copy.COLLAB["FIELDS_HEADER"])
    fields = _fields_frame(a, b)
    if fields.empty:
        _below_floor_notice(pulse_row["copubs_total"] if pulse_row else 0)
        return

    # D4/D5 chrome-audit basis chip: this chart, like every other CORE-AR
    # section on this page, is pinned to articles and reviews, full counting.
    _basis_caption(copy.COLLAB["BASIS_CAPTION_CORE_AR"].format(y0=WINDOW_START, y1=WINDOW_END))
    st.markdown(X.map_legend_strip([], slots={}, color_by="domain",
                                   domain_items=_domain_items(fields)),
                unsafe_allow_html=True)
    st.plotly_chart(_fields_chart(fields), width="stretch", key="fig_fields")
    _note(copy.COLLAB["FIELDS_CHART_READING"], copy.COLLAB["FIELDS_CHART_TOOLTIP"])


# -------------------------------------- 4. strategic reciprocity by field ---

def _reciprocity_chart(df: pd.DataFrame, name_a: str, name_b: str):
    """Bubble scatter, ported from the Lorraine "Zoom partenaire" reciprocity
    chart (see the module docstring): x = a field's share of B's OWN
    portfolio, y = the same field's share of A's OWN portfolio, area = the
    pair's joint volume in that field (area-true: `sizemode="area"`, one
    `sizeref` shared by every bubble), colour = OpenAlex domain, one dotted
    45-degree "equal weight" diagonal, squared axes (same [0, max] range on
    both, `scaleanchor` locking the aspect ratio so the square is real, not
    just numerically equal ranges)."""
    x = df["x"].to_numpy(dtype=float)
    y = df["y"].to_numpy(dtype=float)
    vol = df["joint_vol"].to_numpy(dtype=float)
    n = len(df)
    colors = [P.domain_color(v) for v in df["domain_id"]]
    names = df["field_name"].astype(str).tolist()
    vmax = float(vol.max()) if n and vol.max() > 0 else 1.0

    hover = [
        f"{names[i]}<br>"
        f"{copy.COLLAB['RECIPROCITY_HOVER_X'].format(name=name_b)}{C.THIN_SPACE}{_pct(x[i])}<br>"
        f"{copy.COLLAB['RECIPROCITY_HOVER_Y'].format(name=name_a)}{C.THIN_SPACE}{_pct(y[i])}<br>"
        f"{copy.COLLAB['RECIPROCITY_HOVER_JOINT']}{C.THIN_SPACE}{_count(vol[i])}"
        for i in range(n)
    ]
    fig = go.Figure(go.Scatter(
        x=x, y=y, mode="markers",
        marker=dict(color=colors, size=vol, sizemode="area",
                    sizeref=(2.0 * vmax / (C.BUBBLE_MAX_PX ** 2)),
                    sizemin=C.BUBBLE_MIN_PX,
                    line=dict(color=P.SURFACE, width=BUBBLE_OUTLINE_PX)),
        customdata=hover, hovertemplate="%{customdata}<extra></extra>", showlegend=False))

    axis_max = max(float(np.nanmax(x)) if n else 0.0, float(np.nanmax(y)) if n else 0.0)
    axis_max = (axis_max or 1.0) * RECIP_AXIS_PAD_MULT
    fig.add_shape(type="line", x0=0, y0=0, x1=axis_max, y1=axis_max,
                 line=dict(color=P.INK_SECONDARY, width=C.HAIRLINE_PX, dash=RECIP_DIAGONAL_DASH))
    fig.update_xaxes(range=[0, axis_max], tickformat=C._AXIS_PCT_FMT,
                     title_text=copy.COLLAB["RECIPROCITY_AXIS_X"].format(name=name_b),
                     gridcolor=P.GRID, zerolinecolor=P.GRID, linecolor=P.BORDER,
                     constrain="domain")
    fig.update_yaxes(range=[0, axis_max], tickformat=C._AXIS_PCT_FMT,
                     title_text=copy.COLLAB["RECIPROCITY_AXIS_Y"].format(name=name_a),
                     gridcolor=P.GRID, zerolinecolor=P.GRID, linecolor=P.BORDER,
                     # `constrain="domain"` (not the "range" default): the PLOT
                     # AREA shrinks to a visual square within the wider figure
                     # canvas, leaving the explicit [0, axis_max] range on BOTH
                     # axes untouched. Without it plotly's default behaviour
                     # EXPANDS the shorter axis's range to fill the (much
                     # wider than tall) canvas at 1:1 scale -- measured on the
                     # real render: the x-axis grew a large, meaningless
                     # negative extent to match the y-axis's pixel height.
                     scaleanchor="x", scaleratio=1, constrain="domain")
    return C._base_layout(fig, C.SCATTER_HEIGHT,
                          margin=dict(t=C.BASE_PX // 2, l=C.BASE_PX, r=16, b=C.BASE_PX))


def _render_reciprocity(bundle: dict, a: str, b: str, scenario: dict) -> None:
    """Section 4 (2BR3 task 4): renders nothing at all when the frame is
    empty -- section 3 already carries the one below-floor notice, and this
    frame is empty for exactly the same pairs (both read `field_breakdown`),
    so repeating the notice would read as two failures.

    2C chrome-audit fix (L6): the two full, always-visible paragraphs this
    section used to carry ("How to read" above the chart, "Why this figure"
    below it) are folded into ONE reading line + tooltip (`_note`, the SAME
    fold every Compare section already uses), in the contract's own order --
    subheader -> basis caption -> legend -> chart -> note -- the legend
    moves ABOVE the chart to match (it used to sit between chart and the old
    "Why" paragraph)."""
    ctx = bundle["ctx"]
    df = _reciprocity_frame(a, b, scenario["tree"], scenario["basis"])
    if df.empty:
        return
    name_a, name_b = _name(ctx, a), _name(ctx, b)
    st.subheader(copy.COLLAB["RECIPROCITY_HEADER"])
    _basis_caption(copy.COLLAB["BASIS_CAPTION_CORE_AR"].format(y0=WINDOW_START, y1=WINDOW_END))
    st.markdown(X.map_legend_strip([], slots={}, color_by="domain",
                                   domain_items=_domain_items(df)),
                unsafe_allow_html=True)
    st.plotly_chart(_reciprocity_chart(df, name_a, name_b), width="stretch", key="fig_reciprocity")
    tooltip = " ".join([
        copy.COLLAB["RECIPROCITY_HOW_TO_READ"].format(name_a=name_a, name_b=name_b),
        copy.COLLAB["RECIPROCITY_WHY"],
    ])
    _note(copy.COLLAB["RECIPROCITY_READING"], tooltip)


# ------------------------------------------------- 5. the topic deep dive ---

def _topics_display_frame(topics: pd.DataFrame) -> pd.DataFrame:
    """Technical column names (the `st.dataframe`/`column_config` idiom
    `lib/ranked.py`/`lib/views_find.py` already use): the DISPLAYED header
    text is `column_config`'s own `label=`, sourced from copy.py at the call
    site below, never from these keys."""
    vol = pd.to_numeric(topics["vol"], errors="coerce")
    safe_vol = vol.replace(0.0, np.nan)
    mom = [_momentum_cell(c) for c in topics["mom_class"]]
    return pd.DataFrame({
        # 2C chrome-audit fix (L8): the topic NAME is the clickable link (the
        # app's ONE canonical row-link idiom, `_named_link`/`NAME_LINK_
        # DISPLAY_RE`), not a separate trailing "Open" column.
        "topic_name": [_named_link(u, n) for u, n in
                      zip(topics["url"].astype(str), topics["topic_name"].astype(str))],
        "domain_name": topics["domain_name"].astype(str).to_numpy(),
        "vol": vol.to_numpy(),
        # D9: pre-scaled 0-100 for `PCT_PROGRESS_FORMAT` (see PROGRESS_MIN/MAX).
        "top10_share": ((pd.to_numeric(topics["n_top10"], errors="coerce") / safe_vol) * 100.0).to_numpy(),
        "sdg_share": ((pd.to_numeric(topics["n_sdg"], errors="coerce") / safe_vol) * 100.0).to_numpy(),
        "sdg_n": pd.to_numeric(topics["n_sdg"], errors="coerce").to_numpy(),
        "fwci_median": pd.to_numeric(topics["fwci_median"], errors="coerce").to_numpy(),
        "momentum": [f"{glyph} {text}" for text, _color, glyph in mom],
    })


def _topics_column_config() -> dict:
    return {
        "topic_name": st.column_config.LinkColumn(
            copy.COLLAB["JOINT_COL_TOPIC"], help=copy.COLLAB["COL_LINK_HELP"],
            display_text=NAME_LINK_DISPLAY_RE),
        "domain_name": st.column_config.TextColumn(copy.COLLAB["DF_COL_DOMAIN"]),
        "vol": st.column_config.NumberColumn(copy.COLLAB["JOINT_COL_VOL"], format=VOL_FORMAT),
        "top10_share": st.column_config.ProgressColumn(
            copy.COLLAB["COL_TOP10"], help=copy.COLLAB["COL_TOP10_DF_HELP"],
            min_value=PROGRESS_MIN, max_value=PROGRESS_MAX, format=PCT_PROGRESS_FORMAT),
        "sdg_share": st.column_config.ProgressColumn(
            copy.COLLAB["JOINT_COL_SDG"], help=copy.COLLAB["COL_SDG_DF_HELP"],
            min_value=PROGRESS_MIN, max_value=PROGRESS_MAX, format=PCT_PROGRESS_FORMAT),
        "sdg_n": st.column_config.NumberColumn(copy.COLLAB["JOINT_COL_SDG_RAW"], format=VOL_FORMAT),
        "fwci_median": st.column_config.NumberColumn(
            copy.COLLAB["DF_COL_FWCI"], help=copy.COLLAB["COL_FWCI_HELP"], format=FWCI_FORMAT),
        "momentum": st.column_config.TextColumn(
            copy.COLLAB["DF_COL_MOMENTUM"], help=copy.COLLAB["DF_COL_MOMENTUM_HELP"]),
    }


def _render_topics(bundle: dict, a: str, b: str, scenario: dict, pulse_row: dict | None) -> None:
    """Section 5 (2BR3 task 5): a native, sortable `st.dataframe`, 20 rows
    by default with a "Show all N" button (no slider). Below the floor this
    section renders nothing at all -- section 3 already carries the one
    honest notice, and repeating it would read as two failures."""
    ctx = bundle["ctx"]
    prof = _joint_frame(a, b, scenario["tree"], scenario["basis"])
    if prof is None:
        return
    st.subheader(copy.COLLAB["TOPICS_HEADER"])
    _basis_caption(copy.COLLAB["BASIS_CAPTION_CORE_AR"].format(y0=WINDOW_START, y1=WINDOW_END))
    all_topics = prof["topics"]
    key = "topics_show_all"
    show_all = _show_all_flag(len(all_topics), key)
    n = _visible_row_count(len(all_topics), show_all)
    topics = all_topics.head(n)
    st.dataframe(_topics_display_frame(topics), hide_index=True, width="stretch",
                column_config=_topics_column_config(), key="df_topics")
    _show_all_button(len(all_topics), key)
    _note(copy.COLLAB["TOPICS_READING"],
          copy.COLLAB["TOPICS_TOOLTIP"].format(cap=prof["meta"]["top_n_cap"],
                                               floor=prof["meta"]["floor"]))
    _rows_note(len(topics), len(all_topics))

    shown = float(pd.to_numeric(topics["vol"], errors="coerce").sum())
    tagged = int(pd.to_numeric(topics["n_sdg"], errors="coerce").sum())
    st.caption(copy.COLLAB["JOINT_SDG_LINE"].format(
        n_tagged=_count(tagged), n_shown=_count(shown),
        share=_pct(tagged / shown if shown > 0 else None)))

    erc = prof["erc"]
    labelled, panel_n = erc["labelled_n"], erc["panel_n"]
    if labelled > 0:
        st.markdown(copy.COLLAB["JOINT_ERC_LINE"].format(
            panel=_erc_panel_label(ctx, erc["panel_idx"]), n_panel=_count(panel_n),
            n_labelled=_count(labelled), share=_pct(panel_n / labelled)))
        total = pulse_row["copubs_total"] if pulse_row else 0
        st.caption(copy.COLLAB["JOINT_ERC_CAPTION"].format(
            pct=_pct(labelled / total if total else None)))
    else:
        st.caption(copy.COLLAB["EMPTY_JOINT_ERC"])


# ------------------------------------------------- 6. untapped potential ----

def _untapped_display_frame(topics: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        # 2C chrome-audit fix (L8): same name-as-link convention as the topic
        # deep dive above -- one idiom for the same affordance on both tables.
        "topic_name": [_named_link(u, n) for u, n in
                      zip(topics["url"].astype(str), topics["topic_name"].astype(str))],
        "subfield_name": topics["subfield_name"].astype(str).to_numpy(),
        "vol_a": pd.to_numeric(topics["vol_a"], errors="coerce").to_numpy(),
        "vol_b": pd.to_numeric(topics["vol_b"], errors="coerce").to_numpy(),
        "joint_observed": pd.to_numeric(topics["joint_observed"], errors="coerce").to_numpy(),
        "joint_expected": pd.to_numeric(topics["joint_expected"], errors="coerce").to_numpy(),
        "gap": pd.to_numeric(topics["gap"], errors="coerce").to_numpy(),
    })


def _untapped_column_config(name_a: str, name_b: str) -> dict:
    return {
        "topic_name": st.column_config.LinkColumn(
            copy.COLLAB["UNTAPPED_COL_TOPIC"], help=copy.COLLAB["COL_LINK_HELP"],
            display_text=NAME_LINK_DISPLAY_RE),
        "subfield_name": st.column_config.TextColumn(copy.COLLAB["UNTAPPED_COL_SUBFIELD"]),
        "vol_a": st.column_config.NumberColumn(
            copy.COLLAB["UNTAPPED_COL_VOL_SIDE"].format(name=name_a), format=FRAC_VOL_FORMAT),
        "vol_b": st.column_config.NumberColumn(
            copy.COLLAB["UNTAPPED_COL_VOL_SIDE"].format(name=name_b), format=FRAC_VOL_FORMAT),
        "joint_observed": st.column_config.NumberColumn(
            copy.COLLAB["UNTAPPED_COL_OBSERVED"], format=FRAC_VOL_FORMAT),
        "joint_expected": st.column_config.NumberColumn(
            copy.COLLAB["UNTAPPED_COL_EXPECTED"], format=FRAC_VOL_FORMAT),
        "gap": st.column_config.NumberColumn(copy.COLLAB["UNTAPPED_COL_GAP"], format=FRAC_VOL_FORMAT),
    }


def _render_untapped(bundle: dict, a: str, b: str, scenario: dict) -> None:
    """Section 6: topics both institutions hold where the joint output is
    below what the pair's OWN overall collaboration rate would predict. This
    section does NOT depend on the topic floor -- it is built on the
    shared-topic substrate. Ranking is fixed in the data (gap descending on
    the TRUE, uncapped observed volume, `collab_data.untapped`'s own
    `collab_topic_vols` fix) -- this page adds no ranking control of its
    own. (D8, 2C: the "Adjacent topics in the same subfields" expander that
    used to sit below this table is REMOVED -- see the module docstring.)"""
    ctx = bundle["ctx"]
    name_a, name_b = _name(ctx, a), _name(ctx, b)
    st.subheader(copy.COLLAB["UNTAPPED_HEADER"])
    res = _untapped_frame(a, b, scenario["tree"], scenario["basis"])
    all_topics = res["topics"]
    if all_topics.empty:
        st.info(copy.COLLAB["EMPTY_UNTAPPED"])
    else:
        _basis_caption(copy.COLLAB["BASIS_CAPTION_CORE_AR"].format(y0=WINDOW_START, y1=WINDOW_END))
        key = "untapped_show_all"
        show_all = _show_all_flag(len(all_topics), key)
        n = _visible_row_count(len(all_topics), show_all)
        topics = all_topics.head(n)
        st.dataframe(_untapped_display_frame(topics), hide_index=True, width="stretch",
                    column_config=_untapped_column_config(name_a, name_b), key="df_untapped")
        _show_all_button(len(all_topics), key)
        # The formula itself is the METHOD, so it goes behind the mark with
        # the window the rate is measured over; what stays visible is the
        # one line that says what the table is.
        _note(copy.COLLAB["UNTAPPED_READING"],
              copy.COLLAB["UNTAPPED_CAPTION"].format(k=_pct(res["k"])) + " "
              + copy.COLLAB["UNTAPPED_RATE_NOTE"].format(
                  window=_window(collab_data.PULSE_YEARS)))
        _rows_note(len(topics), len(all_topics))


# ------------------------------------------------------- 7. bottom meta -----

def _render_not_offered() -> None:
    """What this page does NOT show, in plain language, one line per measure
    and no internal reference of any kind."""
    with st.container(key="collab_not_offered"):
        st.markdown(f"**{copy.SHARED['NOT_OFFERED_HEADER']}**")
        for feature, reason in (
                (copy.COLLAB["NOT_OFFERED_GAPS"], copy.COLLAB["NOT_OFFERED_GAPS_REASON"]),
                (copy.COLLAB["NOT_OFFERED_BREADTH"], copy.COLLAB["NOT_OFFERED_BREADTH_REASON"]),
                (copy.COLLAB["NOT_OFFERED_SUBFIELDS"], copy.COLLAB["NOT_OFFERED_SUBFIELDS_REASON"])):
            st.caption(copy.SHARED["NOT_OFFERED_LINE"].format(feature=feature, reason=reason))


def _render_meta(bundle: dict, a: str, b: str) -> None:
    """Bottom meta, collapsed by default (2BR3 layout ruling): the dataset
    line and method note, what this page does not show and why, and the
    shareable link -- moved down here from where a picker used to sit."""
    with st.expander(copy.COLLAB["META_EXPANDER"], expanded=False):
        st.caption(copy.COLLAB["PAGE_INTRO_PAIR"])
        st.caption(copy.FIND["SNAPSHOT_CAPTION"].format(
            n_institutions=f"{len(bundle['index_df']):,}"))
        _render_not_offered()
        selection.share_link_block("pair", [a, b], caption=copy.COLLAB["DEEPLINK_LABEL"])


# -------------------------------------------------------------- render ------

def render() -> None:
    """The whole Collaborate page (2BR3 VL). Order: sidebar scenario + the
    shared search/basket -> title + promise -> the two slots -> identity
    cards + momentum headline -> the relationship pulse -> the joint corpus
    field by field -> strategic reciprocity by field -> the topic deep dive
    -> untapped potential -> bottom meta."""
    bundle = _bundle()
    scenario = _sidebar_scenario()
    selection.render_sidebar()
    _header()

    a, b = selection.slots_row("collab", state.COLLAB_CAP)
    if a and b and a == b:
        st.info(copy.COLLAB["EMPTY_SAME"])
        return
    _render_header_block(bundle, a, b)
    if not (a and b):
        return

    # A tree/basis flip pays build_substrates ONCE (cached, at most three
    # scenarios live); every other rerun finds it warm.
    with st.spinner(copy.COMPARE["SPINNER_SCENARIO"]):
        _subs(scenario["tree"], scenario["basis"])

    pulse_row = _render_pulse(bundle, a, b)
    _render_fields(bundle, a, b, pulse_row)
    _render_reciprocity(bundle, a, b, scenario)
    _render_topics(bundle, a, b, scenario, pulse_row)
    _render_untapped(bundle, a, b, scenario)
    _render_meta(bundle, a, b)

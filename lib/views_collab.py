"""
app/lib/views_collab.py -- render functions for the Collaborate page (Sprint 2
Phase 2B-R2, stream LP3; decisions 2B-R2-11 (a) to (g), 2B-R2-8 presentation and
2B-R2-13 plain language, over the pair frames stream CD3 publishes in
`lib/collab_data.py`).

COMPOSITION ONLY, same rule as lib/views_find.py: every frame comes from
`lib/collab_data.py`, every id/pair rule from `lib/selection.py`, every URL from
`lib/links.py`, every string from `lib/copy.py`, every colour from
`lib/palette.py`. Nothing here recomputes a number and nothing here types one
into a rendered string (BUILD_PLAN_2A.md L10, enforced by
tests/test_narrative.py, which globs lib/views_*.py).

PAGE SHAPE (2B-R2-11a), five sections over the pair A <-> B:

  1. the relationship pulse -- joint publications per year, each side's joint
     share of its OWN output with both denominators named, the two ranks in
     their two directions, one plain-language movement line (unchanged from
     2B-R, except that a pair under the topic floor now meets the SHARED
     below-floor wording at the floor the pair tables actually ship with);
  2. NEW: the joint corpus FIELD BY FIELD, as a chart -- horizontal bars, one
     row per field, grouped under the four OpenAlex domains, drawn in ONE
     neutral hue because the corpus belongs to the pair rather than to either
     institution, with the domain's own colour on the field LABEL and on the
     chip beside every field name in the table under it (the coexistence rule
     runs one way: taxonomy colour on labels and chips, never on a mark that
     could be read as an institution). Volumes, the world-top-decile pair and
     mean citations come from the uncapped pair x field table, which is
     best-fit only and says so in its tooltip;
  3. the shared topics the pair publishes most on, up to the shipped cap with a
     slider, each row carrying its domain chips, its "x of y covered" impact
     pair, a direction arrow and a live OpenAlex link restricted to that topic;
  4. untapped potential -- shared topics where the pair's own overall
     collaboration rate predicts more joint work than there is, same chips and
     links, with the adjacent-topic list kept beside it;
  5. the link-outs, and then one plain-language block naming what this page
     does NOT show and why (2B-R2-8) -- the two directional "what X does not
     publish in" tables are DELETED this round (2B-R2-11f), not hidden.

WHY THE THREE TABLES ARE HAND-BUILT HTML AND NOT `st.dataframe`. Three things
2B-R2-11 asks for are impossible in Streamlit's grid: a coloured domain chip
beside a taxon name (the grid paints cells on a CANVAS, so no per-cell markup),
a per-row link (the grid's LinkColumn takes ONE fixed label for a whole column,
Wind Tunnel A10) and a read-back-able value for the acceptance probe (canvas
text is not in the DOM at all -- ops/_probe_collab.py used to have to check
those tables through their CSV instead of through what a reader sees). One
scrollable HTML table gives all three, keeps the page body from ever scrolling
sideways (each table scrolls inside its OWN wrapper) and is verified end to end
in the probe. The CSV download stays beside every table, unchanged.

The pair picker, the swap button, the `?pair=` deep link and the hand-off from
Compare are UNCHANGED from 2B.

SIDEBAR: counting & taxonomy (the SAME widget keys `tree` / `basis` the Find
page uses, so the scenario carries across pages) + a READ-ONLY basket with a
link back to Find (the add/remove affordances stay on Find, which owns them).

PERFORMANCE (2B-14: warm rerun < 1.5 s)
  `views_find._bundle` / `views_find._subs` are reused BY IMPORT, not copied, so
  the engine context and each (tree, basis) substrate load once per process and
  are shared with the Find page rather than paid again here. The frames are
  `@st.cache_data` keyed on (a, b, tree, basis) -- ctx/subs are unhashable and
  are never cache_data arguments -- so moving either slider re-renders the
  tables without recomputing anything.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from lib import charts as C
from lib import charts_compare as X
from lib import collab_data, copy, countries, links, profile_data, selection, state
from lib import palette as P
from lib.app_config import CFG
from lib.compare_data import DYNAMICS_W1, DYNAMICS_W2
from lib.palette import NA_MARK
from lib.search import search
from lib.views_find import BONUS_STAR, SEP, _bundle, _hit_label, _sidebar_scenario, _subs

# The en dash between the two ends of a window label ("2020-2025" rendered with
# a real dash). The YEARS themselves are never typed here: they come from
# `collab_data.PULSE_YEARS`, `lib.compare_data`'s dynamics windows and CFG.
DASH = "\N{EN DASH}"

# A pulse difference smaller than this reads as "the same annual rate" rather
# than as a direction: the two windows are 3 and 2 years long, so a few papers
# of noise on a small pair would otherwise be rendered as a trend. Stated on the
# page through `COLLAB["PULSE_TREND_NOTE"]`, never typed into a caption.
TREND_BAND = 0.10

# Frontier flag rendering: a glyph, its absence, or n/a for a topic that carries
# no frontier score at all (BUILD_PLAN_2A.md L11 -- n/a is never 0 and never a
# silent False).
FRONTIER_MARK = "▲"      # black up-pointing triangle
FRONTIER_BLANK = ""

# The institution-identity swatch (2B-1 / A8), shown only when the palette's
# institution additions exist at runtime -- see `_swatches`.
SWATCH_MARK = "●"        # black circle, tinted by the palette colour

# The plain (non-widget) session key holding institutions added by name on THIS
# page: the basket belongs to Find (2A L-basket rule), and a Collaborate reader
# must be able to pull in a second institution without editing it.
EXTRA_KEY = "collab_extra"

FIND_PAGE = "pages/1_\U0001F50E_Find.py"

# --- the hand-built tables (see the module docstring) ------------------------
CHIP_PX = 10             # the domain chip beside a taxon name
TABLE_MAX_PX = 520       # a table's body height before it scrolls in its own box
CELL_PAD_PX = 6
ARROW_GLYPHS = {collab_data.ARROW_UP: "\N{UPWARDS ARROW}",
                collab_data.ARROW_DOWN: "\N{DOWNWARDS ARROW}",
                collab_data.ARROW_FLAT: "\N{RIGHTWARDS ARROW}"}
LINK_GLYPH = "\N{NORTH EAST ARROW}"
ALIGN_LEFT, ALIGN_RIGHT, ALIGN_CENTER = "left", "right", "center"

# The one "institution" the field chart draws: a co-publication belongs to the
# pair, not to either side, so this key is deliberately absent from every
# palette slot map -- `palette.institution_color` answers an unknown slot with
# COMPARISON grey and `institution_ink` with the secondary ink, which is exactly
# the neutral single hue 2B-R2-11(a) asks the bars to wear.
PAIR_SERIES_KEY = "pair"

# How many rows each slider opens on. The cap is the shipped table's own
# (`collab_data.PAIR_TOPICS_TOP_N`) and the step keeps the control coarse enough
# to drag: both are module constants, never digits inside a rendered string.
ROWS_DEFAULT = 20
ROWS_STEP = 10


# ------------------------------------------------------------- frames -------
# One @st.cache_data per table, keyed on the HASHABLE scenario identity
# (a, b, tree, basis). `st.expander` bodies execute even when collapsed and every
# widget touch reruns the whole script, so an uncached frame would be recomputed
# on every keystroke in the search box and on every drag of a slider.

@st.cache_data(show_spinner=False, max_entries=48)
def _pulse_frame(a: str, b: str) -> dict | None:
    """`pulse` needs no substrate (it reads one row of `collab_pairs` plus the
    index), so it is keyed on the pair alone and survives a tree/basis flip."""
    return collab_data.pulse(_bundle()["ctx"], a, b)


@st.cache_data(show_spinner=False, max_entries=48)
def _fields_frame(a: str, b: str) -> pd.DataFrame:
    """2B-R2-11(a): the pair x field breakdown. Best-fit only by construction
    (the shipped table carries one tree), so this frame -- alone on the page --
    is NOT keyed on the tree, and the section's tooltip says so."""
    return collab_data.field_breakdown(_bundle()["ctx"], a, b)


@st.cache_data(show_spinner=False, max_entries=24)
def _joint_frame(a: str, b: str, tree: str, basis: str) -> dict | None:
    """`None` means BELOW THE TOPIC FLOOR (or never co-published) -- the page
    renders the honest notice rather than an empty table."""
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


def _vol(value) -> str:
    """A FRACTIONAL volume keeps one decimal (the untapped table's own grain);
    `_count` stays the integer form for whole publications."""
    if value is None or pd.isna(value):
        return NA_MARK
    return f"{float(value):,.1f}"


def _band(value) -> str:
    """The arrow deadband as a plain number for the column tooltip."""
    return f"{float(value):g}"


def _frontier_glyph(value) -> str:
    """True -> glyph, False -> blank, missing -> n/a. `top25pct_frontier` is a
    pandas BooleanDtype column, so `pd.NA` reaches here as a real third state
    (the topic carries no frontier score), never as False."""
    if value is None or pd.isna(value):
        return NA_MARK
    return FRONTIER_MARK if bool(value) else FRONTIER_BLANK


def _name(ctx: dict, iid: str) -> str:
    return str(ctx["index_by_id"].loc[iid, "display_name"])


def _window(years) -> str:
    """"first{dash}last" for a window handed in as a (start, end) pair or as a
    list of years. The years come from `collab_data.PULSE_YEARS` and
    `lib.compare_data`'s dynamics constants, so no window is ever typed here."""
    ys = list(years)
    return f"{ys[0]}{DASH}{ys[-1]}"


def _window_mean(yearly: pd.DataFrame, window) -> float:
    """Mean annual joint volume over an inclusive (start, end) year window,
    read off the pulse frame the chart itself draws."""
    by_year = dict(zip(yearly["year"], yearly["copubs"]))
    years = range(window[0], window[1] + 1)
    return float(sum(float(by_year.get(y, 0.0)) for y in years) / len(list(years)))


def _trend_line(yearly: pd.DataFrame) -> str:
    """The one plain-language pulse sentence. It is a DATA question, answered by
    comparing the two dynamics windows the rest of the tool already uses
    (`compare_data.DYNAMICS_W1`/`W2`, partial year excluded), and phrased in
    neutral vocabulary: a direction and a size, never a judgement about the
    relationship."""
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


def _slots(ctx: dict, ids: list[str]) -> dict:
    """`{institution_id: slot}` by ascending `inst_key` (A8), the same
    assignment `_swatches` and the Compare page use, so the legend chip and the
    identity dot of an institution are the same colour on both pages."""
    return P.institution_slots({iid: ctx["index_by_id"].loc[iid, "inst_key"] for iid in ids})


def _frontier_flags(ctx: dict) -> dict:
    """topic_id -> `top25pct_frontier`, a LOOKUP on the dimension table the
    engine context already holds. Nothing is computed: the pair table simply
    does not carry the flag, and the joint-topic table needs it."""
    dim = ctx["topics_dim_df"]
    return dict(zip(dim["topic_id"], dim["top25pct_frontier"]))


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


def _domain_order(domain_id) -> int:
    """The taxonomy's OWN fixed domain order (`palette.OA_DOMAIN_ORDER`), which
    is what `charts_compare.fig_metric_bars`' taxonomy sort groups rows by. An
    unknown or unclassified domain sorts last rather than first."""
    order = list(P.OA_DOMAIN_ORDER)
    try:
        return order.index(int(domain_id))
    except (TypeError, ValueError):
        return len(order)


# ------------------------------------------------- the hand-built tables ----
# HTML, because a domain chip, a per-row link and a DOM-readable value are all
# impossible in Streamlit's canvas grid (module docstring). Nothing here writes
# a colour of its own: every hue is `lib/palette.py`'s, and every word is
# `lib/copy.py`'s. These builders return markup; the page hands it to
# `st.markdown(..., unsafe_allow_html=True)`, so no literal string in this
# section is ever a Streamlit call argument (the digit ban's own scope).


def _esc(value) -> str:
    return (str(value).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _chip(domain_id) -> str:
    """The taxonomy chip: the OpenAlex domain's own colour, beside a name and
    never inside a mark that carries any other identity (2B-R2-11b). `data-
    domain` is what the acceptance probe reads the chip back by."""
    return (f'<span class="bu-chip" data-domain="{_esc(domain_id)}" '
            f'style="display:inline-block;flex:none;width:{CHIP_PX}px;height:{CHIP_PX}px;'
            f'border-radius:{CHIP_PX}px;background:{P.domain_color(domain_id)};'
            f'margin-right:{C.CHIP_GAP_PX}px;"></span>')


def _taxon_cell(name, domain_id) -> str:
    return (f'<span style="display:inline-flex;align-items:center;">{_chip(domain_id)}'
            f'<span>{_esc(name)}</span></span>')


def _arrow_cell(arrow, help_text: str) -> str:
    glyph = ARROW_GLYPHS.get(str(arrow), NA_MARK)
    return (f'<span class="bu-arrow" data-arrow="{_esc(arrow)}" title="{_esc(help_text)}" '
            f'style="cursor:help;">{glyph}</span>')


def _link_cell(url, help_text: str) -> str:
    return (f'<a class="bu-link" href="{_esc(url)}" target="_blank" rel="noopener noreferrer" '
            f'title="{_esc(help_text)}" style="text-decoration:none;">{LINK_GLYPH}</a>')


def _header_cell(label: str, help_text: str | None, align: str) -> str:
    mark = ""
    if help_text:
        mark = (f'<span style="margin-left:{C.CHIP_GAP_PX}px;cursor:help;">'
                f'{X.NOTE_HELP_GLYPH}</span>')
    return (f'<th title="{_esc(help_text or label)}" '
            f'style="text-align:{align};padding:{CELL_PAD_PX}px;position:sticky;top:0;'
            f'background:{P.SURFACE};color:{P.INK_SECONDARY};font-weight:600;'
            f'border-bottom:{P.OUTLINE_WIDTH}px solid {P.BORDER};white-space:nowrap;">'
            f'{_esc(label)}{mark}</th>')


def _table(name: str, columns, rows) -> str:
    """ONE scrollable table. `columns` is a sequence of `(label, help, align)`
    and `rows` a sequence of already-built cell markup, in the same order.

    The wrapper scrolls in BOTH directions and the page body therefore never
    does: the SIRIS house rule for a wide table, checked at three widths by the
    acceptance probe."""
    head = "".join(_header_cell(label, help_text, align) for label, help_text, align in columns)
    body = []
    for i, cells in enumerate(rows):
        tds = "".join(
            f'<td style="padding:{CELL_PAD_PX}px;text-align:{align};'
            f'border-bottom:{C.HAIRLINE_PX}px solid {P.BORDER};'
            f'{"white-space:nowrap;" if align != ALIGN_LEFT else ""}">{cell}</td>'
            for cell, (_, _, align) in zip(cells, columns))
        body.append(f'<tr data-row="{i}">{tds}</tr>')
    return (f'<div class="bu-table" style="overflow:auto;max-height:{TABLE_MAX_PX}px;'
            f'border:{C.HAIRLINE_PX}px solid {P.BORDER};border-radius:{C.CHIP_GAP_PX}px;">'
            f'<table data-table="{_esc(name)}" style="width:100%;border-collapse:collapse;'
            f'font-size:{C.FONT_PX}px;color:{P.INK};">'
            f'<thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>')


def _note(reading: str, tooltip: str | None = None) -> None:
    """2B-R2-8: ONE short reading line, the methodology behind its `?`."""
    st.markdown(X.chart_note(reading, tooltip), unsafe_allow_html=True)


def _top10_text(n_top10, n_covered) -> str:
    if pd.isna(n_top10) or pd.isna(n_covered):
        return NA_MARK
    return copy.COLLAB["COL_TOP10_VALUE"].format(n_top10=_count(n_top10), n_covered=_count(n_covered))


def _trend_help() -> str:
    return copy.COLLAB["COL_TREND_HELP"].format(
        w1=_window(DYNAMICS_W1), w2=_window(DYNAMICS_W2),
        band=_band(collab_data.ARROW_DEADBAND))


def _rows_note(n_shown: int, n_total: int) -> None:
    st.caption(copy.COLLAB["TABLE_ROWS_NOTE"].format(
        n_shown=_count(n_shown), n_total=_count(n_total)))


def _rows_slider(n_total: int, *, key: str, label: str, help_text: str) -> int:
    """The row slider (2B-R2-11a). It is offered only when there is something to
    choose between: a pair with fewer rows than the default shows them all
    rather than a control with one stop."""
    if n_total <= ROWS_DEFAULT:
        return n_total
    return st.slider(label, min_value=ROWS_STEP, max_value=int(n_total),
                     value=min(ROWS_DEFAULT, int(n_total)), step=ROWS_STEP,
                     key=key, help=help_text, **state.PERSIST)


# ------------------------------------------------------------- sidebar ------

def _sidebar_basket(bundle: dict) -> None:
    """READ-ONLY here: the basket is built on Find, which owns its add/remove
    controls. This page shows what is in it, because it is where the pair
    picker's options come from, and links back to the page that can change
    it."""
    sb, names = st.sidebar, bundle["ctx"]["index_by_id"]
    sb.header(copy.FIND["BASKET_HEADER"])
    items = state.items()
    sb.caption(copy.FIND["BASKET_COUNT"].format(n=len(items), cap=state.BASKET_CAP))
    if not items:
        sb.caption(copy.FIND["BASKET_EMPTY"])
    else:
        for iid in items:
            sb.write(str(names.loc[iid, "display_name"]))
    # `st.page_link` needs the multi-page registry, which only exists when the
    # app is entered through Menu.py. Run this ONE page on its own (AppTest,
    # `streamlit run pages/3_...py`, the acceptance probe) and Streamlit raises
    # a KeyError on its own page table -- so the link degrades to its label
    # rather than taking the whole page down with it.
    try:
        sb.page_link(FIND_PAGE, label=copy.NAV["FIND_LABEL"])
    except Exception:
        sb.caption(copy.NAV["FIND_LABEL"])


# ------------------------------------------------------- header + pair ------

def _header(bundle: dict) -> None:
    """Title and lead from `copy.NAV`, the standing verdict line, and the
    index-size caption."""
    st.title(copy.NAV["COLLAB_LABEL"])
    st.subheader(copy.NAV["COLLAB_LEAD"])
    st.caption(copy.COLLAB["PAGE_INTRO_PAIR"])
    st.markdown(f"**{copy.VERDICT_LINE}**")
    st.caption(copy.FIND["SNAPSHOT_CAPTION"].format(
        n_institutions=f"{len(bundle['index_df']):,}"))


def _extras() -> list[str]:
    st.session_state.setdefault(EXTRA_KEY, [])
    return st.session_state[EXTRA_KEY]


def _candidates(bundle: dict) -> list[str]:
    """Everything the pair picker may choose from, in a stable order: the
    basket (its own user order), then whatever a deep link named, then whatever
    Compare's hand-off button just stashed in `st.session_state["pair"]` (read
    here, NOT popped -- `_pair_picker` below is the one place that consumes it,
    after this function has already folded its ids into the option list
    `st.selectbox` needs them in), then whatever was added by name on this page.
    De-duplicated, and filtered to ids the index really carries."""
    known = bundle["ctx"]["id_pos"]
    query = selection.read_query(known)
    session_pair = st.session_state.get("pair") or ()
    out: list[str] = []
    seen: set[str] = set()
    pair = query["pair"] or ()
    for iid in (*state.items(), *pair, *session_pair, *_extras()):
        if iid in known and iid not in seen:
            seen.add(iid)
            out.append(iid)
    return out


def _add_by_name(bundle: dict) -> None:
    """The "add a comparator" affordance, same shape as Find's: a free-text box,
    a selectbox over the hits, and the pick lands in this page's own extras list
    (never in the basket -- that would silently spend one of its slots)."""
    query = st.text_input(copy.COMPARE["ADD_LABEL"], key="collab_query", **state.PERSIST)
    hits = search(query, bundle["search_idx"]) if query else []
    if query and not hits:
        st.caption(copy.SEARCH_EMPTY_TEMPLATE.format(query=query))
    if not hits:
        return
    pick = st.selectbox(copy.COLLAB["PAIR_PICK"], [h["id"] for h in hits],
                        format_func=lambda i: _hit_label(hits, i), key="collab_pick")
    extras = _extras()
    if pick and pick not in extras and pick not in state.items():
        extras.append(pick)
        st.rerun()


def _swap() -> None:
    """`on_click` callback: writing a widget key is legal inside a callback and
    illegal after the widget has been instantiated, which is why the swap is a
    callback rather than a button body plus `st.rerun()`."""
    a, b = st.session_state.get("pair_a"), st.session_state.get("pair_b")
    st.session_state["pair_a"], st.session_state["pair_b"] = b, a


def default_pair(candidates: list[str], query_pair, known, session_pair=None) -> tuple | None:
    """Pure: the pair the page opens on. `session_pair` -- Compare's hand-off
    button's `st.session_state["pair"]`, already popped by the caller -- wins
    FIRST when both its ids are known: it is the reader's own most recent
    in-session action. Next a `?pair=` deep link wins (a shared link should show
    what it names), then the first two candidates in their own order. `None`
    when fewer than two are available."""
    for pair in (session_pair, query_pair):
        if pair and len(pair) >= 2:
            a, b = pair[0], pair[1]
            if a != b and a in known and b in known:
                return (a, b)
    return selection.pair_from(candidates)


def _pair_picker(bundle: dict, candidates: list[str]) -> tuple | None:
    """The directional A -> B picker. Returns `(a, b)`, or None when the page
    has nothing to read yet."""
    ctx = bundle["ctx"]
    st.subheader(copy.COLLAB["PAIR_HEADER"])
    st.caption(copy.COLLAB["PAIR_PROMPT"])
    _add_by_name(bundle)
    if len(candidates) < 2:
        st.info(copy.COLLAB["EMPTY_NO_PAIR"])
        return None

    query = selection.read_query(ctx["id_pos"])
    # Popped HERE, once: a hand-off is a one-time seed for the render right
    # after the hop, never a standing override that would keep fighting a
    # reader's own later edit to the selectboxes below.
    session_pair = st.session_state.pop("pair", None)
    default = default_pair(candidates, query["pair"], ctx["id_pos"], session_pair)
    # A stored selection that is no longer among the options would make
    # st.selectbox raise, so it is dropped rather than defended against later.
    for key, fallback in (("pair_a", default[0]), ("pair_b", default[1])):
        if session_pair or st.session_state.get(key) not in candidates:
            st.session_state[key] = fallback

    cols = st.columns([2, 2, 1])
    label = lambda i: _name(ctx, i)  # noqa: E731  (one-line format_func, both boxes)
    a = cols[0].selectbox(copy.COLLAB["PAIR_A_LABEL"], candidates, format_func=label,
                          key="pair_a", **state.PERSIST)
    b = cols[1].selectbox(copy.COLLAB["PAIR_B_LABEL"], candidates, format_func=label,
                          key="pair_b", **state.PERSIST)
    cols[2].button(copy.COLLAB["PAIR_SWAP_BUTTON"], help=copy.COLLAB["PAIR_SWAP_HELP_PAIR"],
                   on_click=_swap, key="pair_swap")
    if a == b:
        st.info(copy.COLLAB["EMPTY_SAME"])
        return None
    st.caption(copy.COLLAB["DEEPLINK_LABEL"])
    st.code(selection.deeplink("pair", [a, b]), language=None)
    return (a, b)


# -------------------------------------------------------- header strip ------

def _swatches(ctx: dict, ids: list[str]) -> dict:
    """`{institution_id: css colour}` from the identity family, or `{}` when the
    palette's institution additions are not present at runtime. Slots are
    assigned by ascending `inst_key` inside `palette.institution_slots`, never
    by the order this page holds the pair in -- so the swatch of an institution
    does not change when the reader swaps A and B."""
    if not (hasattr(P, "INSTITUTION_COLORS") and hasattr(P, "institution_slots")
            and hasattr(P, "institution_color")):
        return {}
    try:
        keys = {i: ctx["index_by_id"].loc[i, "inst_key"] for i in ids}
        slots = P.institution_slots(keys)
        return {i: P.institution_color(slots[i]) for i in ids}
    except Exception:  # a palette shape this page does not know: show no swatch
        return {}


def _identity(col, ctx: dict, iid: str, colour: str | None) -> None:
    row = ctx["index_by_id"].loc[iid]
    # A coloured GLYPH, not a styled box: an inline box would need pixel/percent
    # lengths, i.e. typed digits inside a string a Streamlit call renders, which
    # is exactly what the digit-ban forbids (BUILD_PLAN_2A.md L10). The only
    # value interpolated here is the palette's own colour.
    dot = f'<span style="color:{colour}">{SWATCH_MARK}</span> ' if colour else ""
    col.markdown(f"{dot}**{_name(ctx, iid)}**", unsafe_allow_html=True)
    col.caption(f"{str(row['type'])} {SEP} {countries.name(str(row['country_code']))}")
    col.caption(f"{copy.FIND['COL_SIZE_FULL']}: {_count(row['total_full_2020_2024'])} {SEP} "
                f"{copy.FIND['COL_SIZE_FRAC']}: {_count(row['total_frac_2020_2024'])}")


def _header_strip(bundle: dict, a: str, b: str) -> None:
    """Both institutions side by side: who they are, where they are, how big
    they are."""
    ctx = bundle["ctx"]
    with st.container(key="collab_header", border=True):
        colours = _swatches(ctx, [a, b])
        cols = st.columns(2)
        _identity(cols[0], ctx, a, colours.get(a))
        _identity(cols[1], ctx, b, colours.get(b))


def _download(df: pd.DataFrame, *, label: str, name: str, key: str) -> None:
    """Streamlit 1.61 accepts a zero-arg callable for `data`, so the CSV is
    encoded only when someone actually clicks. The RAW frame goes out."""
    st.download_button(label, lambda: df.to_csv(index=False).encode("utf-8"),
                       mime="text/csv", file_name=name, key=key)


def _below_floor_notice(n_copubs) -> None:
    """2B-R2-11(g): the shared below-floor wording, at the floor the pair tables
    actually ship with (`collab_data.PAIR_TOPICS_FLOOR`), never a floor typed
    here or in copy.py."""
    st.info(copy.SHARED["BELOW_FLOOR_NOTICE"].format(
        item=copy.COLLAB["BELOW_FLOOR_ITEM"], n=_count(n_copubs),
        floor=collab_data.PAIR_TOPICS_FLOOR))


# ------------------------------------------- 1. the relationship pulse ------

def _render_pulse(bundle: dict, a: str, b: str) -> dict | None:
    """Section one: the pair's joint publications per year, each side's joint
    share of its OWN output with both denominators named, the two ranks in
    their two directions, and one plain-language line about the movement.
    Returns the pulse frame so the sections below can reuse the joint total
    rather than read the same row twice."""
    ctx = bundle["ctx"]
    st.subheader(copy.COLLAB["PULSE_HEADER"])
    row = _pulse_frame(a, b)
    if row is None:
        st.info(copy.COLLAB["EMPTY_PULSE"].format(a=_name(ctx, a), b=_name(ctx, b)))
        return None

    names = {a: _name(ctx, a), b: _name(ctx, b)}
    # The pulse bar belongs to NEITHER institution (a co-publication is the
    # pair's), so the strip carries both identity chips AND the shared chip the
    # bars are actually drawn in.
    with st.container(key="collab_legend"):
        st.markdown(X.legend_strip([a, b], slots=_slots(ctx, [a, b]), names=names,
                                   shared=True, shared_label=copy.COLLAB["LEGEND_JOINT"]),
                    unsafe_allow_html=True)
    st.plotly_chart(X.fig_pulse(row["yearly"], value_col="copubs",
                                bonus_year=str(CFG["bonus_year"]),
                                axis_title=copy.COLLAB["PULSE_AXIS"]),
                    width="stretch", key="fig_pulse")
    _note(copy.COLLAB["PULSE_CHART_READING"],
          copy.COLLAB["PULSE_CHART_CAPTION"].format(bonus_year=CFG["bonus_year"],
                                                    star=BONUS_STAR))

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


# --------------------------------- 2. the joint corpus, field by field ------

def _domain_items(fields: pd.DataFrame) -> list[tuple]:
    """`(domain_id, domain_name)` for the domains this pair actually publishes
    in, in the taxonomy's own order -- the legend the field chart's labels are
    read against. The WORDS are the taxonomy's own, off the frame."""
    seen = {}
    for did, dname in zip(fields["domain_id"], fields["domain_name"]):
        if pd.isna(did):
            continue
        seen.setdefault(int(did), str(dname))
    return [(d, seen[d]) for d in P.OA_DOMAIN_ORDER if d in seen]


def _fields_chart(fields: pd.DataFrame):
    """One horizontal bar per field, in ONE neutral hue (2B-R2-11a).

    `PAIR_SERIES_KEY` is in no slot map, so `fig_metric_bars` draws the bars in
    COMPARISON grey and writes their labels in the secondary ink: the corpus is
    the pair's, and no institution may appear to own it.

    The DOMAIN colour then goes on the row LABELS -- the same one-way rule, and
    literally the same mechanism `charts_compare._accent_ticktext` applies to
    ERC panels and SDG goals (a coloured glyph plus a no-break gap, verified to
    render on the pinned plotly). That mechanism's own family map has no entry
    for fields and widening it belongs to the chart module's stream, so the
    already-wrapped tick strings the builder produced are re-labelled here, in
    the SAME row order the frame was handed over in (the taxonomy sort is
    stable, and the frame arrives pre-sorted on the same key)."""
    d = fields.copy()
    d["institution_id"] = PAIR_SERIES_KEY
    d["value"] = pd.to_numeric(d["vol_total"], errors="coerce")
    d["domain_order"] = [_domain_order(v) for v in d["domain_id"]]
    d = d.sort_values("domain_order", kind="mergesort").reset_index(drop=True)
    fig = X.fig_metric_bars(
        d, "vol", [PAIR_SERIES_KEY], slots={},
        names={PAIR_SERIES_KEY: copy.COLLAB["LEGEND_JOINT"]},
        level="field", sort="taxonomy", value_col="value",
        label_col="field_name", key_col="field_id",
        metric_label=copy.COLLAB["PULSE_AXIS"], gutter=False)
    ticks = list(fig.layout.yaxis.ticktext or [])
    if len(ticks) == len(d):
        fig.update_yaxes(ticktext=[
            f'<span style="color:{P.domain_color(dom)}">{X.ACCENT_GLYPH}</span>'
            f'{X.ACCENT_GAP}{tick}'
            for dom, tick in zip(d["domain_id"], ticks)])
    return fig


def _fields_table(fields: pd.DataFrame) -> str:
    columns = [
        (copy.COLLAB["JOINT_COL_FIELD"], None, ALIGN_LEFT),
        (copy.COLLAB["JOINT_COL_VOL"], None, ALIGN_RIGHT),
        (copy.COLLAB["COL_TOP10"], copy.COLLAB["COL_TOP10_HELP"], ALIGN_RIGHT),
        (copy.COLLAB["COL_MEAN_CITATIONS"], copy.COLLAB["COL_MEAN_CITATIONS_HELP"], ALIGN_RIGHT),
        (copy.COLLAB["COL_TREND"], _trend_help(), ALIGN_CENTER),
        (copy.COLLAB["COL_LINK"], copy.COLLAB["COL_LINK_HELP"], ALIGN_CENTER),
    ]
    rows = [[_taxon_cell(r["field_name"], r["domain_id"]),
             _count(r["vol_total"]),
             _top10_text(r["n_top10"], r["n_covered"]),
             _count(r["mean_citations"]),
             _arrow_cell(r["arrow"], _trend_help()),
             _link_cell(r["url"], copy.COLLAB["COL_LINK_HELP"])]
            for _, r in fields.iterrows()]
    return _table("collab_fields", columns, rows)


def _render_fields(bundle: dict, a: str, b: str, pulse_row: dict | None) -> None:
    """Section two (2B-R2-11a): the field breakdown of the joint corpus, as a
    chart and then as the numbers behind it. Below the topic floor the section
    is the honest notice and nothing else -- no empty chart, no zero."""
    st.subheader(copy.COLLAB["FIELDS_HEADER"])
    fields = _fields_frame(a, b)
    if fields.empty:
        _below_floor_notice(pulse_row["copubs_total"] if pulse_row else 0)
        return

    st.markdown(X.map_legend_strip([], slots={}, color_by="domain",
                                   domain_items=_domain_items(fields)),
                unsafe_allow_html=True)
    st.plotly_chart(_fields_chart(fields), width="stretch", key="fig_fields")
    _note(copy.COLLAB["FIELDS_CHART_READING"], copy.COLLAB["FIELDS_CHART_TOOLTIP"])

    st.markdown(_fields_table(fields), unsafe_allow_html=True)
    _note(copy.COLLAB["FIELDS_TABLE_READING"],
          f"{copy.COLLAB['FIELDS_TABLE_TOOLTIP']} {copy.FWCI_NOT_AVAILABLE_LINE}")
    _rows_note(len(fields), len(fields))
    _download(fields, label=copy.COLLAB["DOWNLOAD_FIELDS"],
              name=f"benchup_collab_fields_{a}_{b}.csv", key="dl_fields")


# ------------------------------------------------- 3. the shared topics -----

def _topics_table(topics: pd.DataFrame, flags: dict) -> str:
    columns = [
        (copy.COLLAB["JOINT_COL_TOPIC"], None, ALIGN_LEFT),
        (copy.COLLAB["JOINT_COL_SUBFIELD"], None, ALIGN_LEFT),
        (copy.COLLAB["JOINT_COL_VOL"], None, ALIGN_RIGHT),
        (copy.COLLAB["COL_TOP10"], copy.COLLAB["COL_TOP10_HELP"], ALIGN_RIGHT),
        (copy.COLLAB["JOINT_COL_SDG"], None, ALIGN_RIGHT),
        (copy.COLLAB["COL_TREND"], _trend_help(), ALIGN_CENTER),
        (copy.COLLAB["JOINT_COL_FRONTIER"], copy.COLLAB["GAPS_FRONTIER_HELP"], ALIGN_CENTER),
        (copy.COLLAB["COL_LINK"], copy.COLLAB["COL_LINK_HELP"], ALIGN_CENTER),
    ]
    rows = [[_taxon_cell(r["topic_name"], r["domain_id"]),
             _taxon_cell(r["subfield_name"], r["domain_id"]),
             _count(r["vol_total"]),
             _top10_text(r["n_top10"], r["n_covered"]),
             _count(r["sdg_tagged_n"]),
             _arrow_cell(r["arrow"], _trend_help()),
             _frontier_glyph(flags.get(r["topic_id"])),
             _link_cell(r["url"], copy.COLLAB["COL_LINK_HELP"])]
            for _, r in topics.iterrows()]
    return _table("collab_topics", columns, rows)


def _render_topics(bundle: dict, a: str, b: str, scenario: dict, pulse_row: dict | None) -> None:
    """Section three (2B-R2-11a to e): what the pair's shared publications are
    about, topic by topic, up to the shipped cap with a slider over it. Below
    the floor this section renders nothing at all -- section two already carries
    the one honest notice, and repeating it would read as two failures."""
    ctx = bundle["ctx"]
    prof = _joint_frame(a, b, scenario["tree"], scenario["basis"])
    if prof is None:
        return
    st.subheader(copy.COLLAB["TOPICS_HEADER"])
    meta, all_topics = prof["meta"], prof["topics"]
    n = _rows_slider(len(all_topics), key="topics_n", label=copy.COLLAB["TOPICS_SLIDER"],
                     help_text=copy.COLLAB["TOPICS_SLIDER_HELP"])
    topics = all_topics.head(n)
    flags = _frontier_flags(ctx)
    st.markdown(_topics_table(topics, flags), unsafe_allow_html=True)
    _note(copy.COLLAB["TOPICS_READING"],
          copy.COLLAB["TOPICS_TOOLTIP"].format(cap=meta["top_n_cap"], floor=meta["floor"]))
    _rows_note(len(topics), len(all_topics))
    _download(all_topics, label=copy.COLLAB["DOWNLOAD_SHARED"],
              name=f"benchup_collab_topics_{a}_{b}_{scenario['tree']}_{scenario['basis']}.csv",
              key="dl_topics")

    shown = float(pd.to_numeric(topics["vol_total"], errors="coerce").sum())
    tagged = int(pd.to_numeric(topics["sdg_tagged_n"], errors="coerce").sum())
    st.markdown(copy.COLLAB["JOINT_SDG_LINE"].format(
        n_tagged=_count(tagged), n_shown=_count(shown),
        share=_pct(tagged / shown if shown > 0 else None)))
    n_frontier = int(topics["topic_id"].map(flags).eq(True).sum())
    st.markdown(copy.COLLAB["JOINT_FRONTIER_LINE"].format(n_frontier=_count(n_frontier)))

    # ERC: the panel share is read of the LABELLED works only; the caption names
    # what fraction of the joint corpus carries a label at all, so the two
    # denominators are never confused for one another.
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


# ------------------------------------------- 4. untapped potential ----------

def _with_domains(ctx: dict, df: pd.DataFrame) -> pd.DataFrame:
    """`domain_id` for a frame that carries `subfield_id` only -- the fixed
    subfield -> field -> domain map the profile page already reads, joined here
    so every taxon name in these tables can carry its chip."""
    names = profile_data._subfield_field_domain_map(ctx)[["subfield_id", "domain_id"]]
    return df.merge(names, on="subfield_id", how="left")


def _untapped_table(name_a: str, name_b: str, topics: pd.DataFrame) -> str:
    columns = [
        (copy.COLLAB["UNTAPPED_COL_TOPIC"], None, ALIGN_LEFT),
        (copy.COLLAB["UNTAPPED_COL_SUBFIELD"], None, ALIGN_LEFT),
        (copy.COLLAB["UNTAPPED_COL_VOL_SIDE"].format(name=name_a), None, ALIGN_RIGHT),
        (copy.COLLAB["UNTAPPED_COL_VOL_SIDE"].format(name=name_b), None, ALIGN_RIGHT),
        (copy.COLLAB["UNTAPPED_COL_OBSERVED"], None, ALIGN_RIGHT),
        (copy.COLLAB["UNTAPPED_COL_EXPECTED"], None, ALIGN_RIGHT),
        (copy.COLLAB["UNTAPPED_COL_GAP"], None, ALIGN_RIGHT),
        (copy.COLLAB["COL_LINK"], copy.COLLAB["COL_LINK_HELP"], ALIGN_CENTER),
    ]
    rows = [[_taxon_cell(r["topic_name"], r["domain_id"]),
             _taxon_cell(r["subfield_name"], r["domain_id"]),
             _vol(r["vol_a"]), _vol(r["vol_b"]), _vol(r["joint_observed"]),
             _vol(r["joint_expected"]), _vol(r["gap"]),
             _link_cell(r["url"], copy.COLLAB["COL_LINK_HELP"])]
            for _, r in topics.iterrows()]
    return _table("collab_untapped", columns, rows)


def _siblings_table(name_a: str, name_b: str, siblings: pd.DataFrame) -> str:
    columns = [
        (copy.COLLAB["SIBLINGS_COL_TOPIC"], None, ALIGN_LEFT),
        (copy.COLLAB["SIBLINGS_COL_SUBFIELD"], None, ALIGN_LEFT),
        (copy.COLLAB["UNTAPPED_COL_VOL_SIDE"].format(name=name_a), None, ALIGN_RIGHT),
        (copy.COLLAB["UNTAPPED_COL_VOL_SIDE"].format(name=name_b), None, ALIGN_RIGHT),
    ]
    rows = [[_taxon_cell(r["topic_name"], r["domain_id"]),
             _taxon_cell(r["subfield_name"], r["domain_id"]),
             _vol(r["vol_a"]), _vol(r["vol_b"])]
            for _, r in siblings.iterrows()]
    return _table("collab_siblings", columns, rows)


def _render_untapped(bundle: dict, a: str, b: str, scenario: dict) -> None:
    """Section four: topics both institutions hold where the joint output is
    below what the pair's OWN overall collaboration rate would predict, with the
    adjacent topics kept beside them. This section does NOT depend on the topic
    floor -- it is built on the shared-topic substrate."""
    ctx = bundle["ctx"]
    name_a, name_b = _name(ctx, a), _name(ctx, b)
    st.subheader(copy.COLLAB["UNTAPPED_HEADER"])
    res = _untapped_frame(a, b, scenario["tree"], scenario["basis"])
    all_topics = _with_domains(ctx, res["topics"])
    if all_topics.empty:
        st.info(copy.COLLAB["EMPTY_UNTAPPED"])
    else:
        n = _rows_slider(len(all_topics), key="untapped_n",
                         label=copy.COLLAB["TOPICS_SLIDER"],
                         help_text=copy.COLLAB["TOPICS_SLIDER_HELP"])
        topics = all_topics.head(n)
        st.markdown(_untapped_table(name_a, name_b, topics), unsafe_allow_html=True)
        # The formula itself is the METHOD, so it goes behind the mark with the
        # window the rate is measured over; what stays visible is the one line
        # that says what the table is (2B-R2-8).
        _note(copy.COLLAB["UNTAPPED_READING"],
              copy.COLLAB["UNTAPPED_CAPTION"].format(k=_pct(res["k"])) + " "
              + copy.COLLAB["UNTAPPED_RATE_NOTE"].format(
                  window=_window(collab_data.PULSE_YEARS)))
        _rows_note(len(topics), len(all_topics))
        _download(res["topics"], label=copy.COLLAB["DOWNLOAD_UNTAPPED"],
                  name=f"benchup_collab_untapped_{a}_{b}_{scenario['tree']}_{scenario['basis']}.csv",
                  key="dl_untapped")

    siblings = _with_domains(ctx, res["siblings"])
    if not siblings.empty:
        with st.expander(copy.COLLAB["SIBLINGS_HEADER"]):
            st.caption(copy.COLLAB["SIBLINGS_CAPTION"].format(n=_count(len(siblings))))
            st.markdown(_siblings_table(name_a, name_b, siblings), unsafe_allow_html=True)


# ------------------------------------------------ 5. links + disclosure -----

def _render_links(bundle: dict, a: str, b: str) -> None:
    """Section five: the two per-institution works links and the ONE
    co-publication link (the comma-joined repeated
    `authorships.institutions.id` filter, which OpenAlex ANDs; the `+` form is
    forbidden and `lib/links.py` never builds it). This section renders for
    every pair, below-floor ones included -- it is the whole answer when the
    topic detail cannot be shown."""
    ctx = bundle["ctx"]
    st.subheader(copy.COLLAB["LINKS_HEADER"])
    st.caption(copy.COLLAB["LINKS_INTRO"])
    with st.container(key="collab_links"):
        link_cols = st.columns(3)
        for col, iid in zip(link_cols, (a, b)):
            col.link_button(copy.COLLAB["LINK_PUBS"].format(name=_name(ctx, iid)),
                            links.works_url(iid), help=copy.FIND["LINK_OPENALEX_HELP"])
        link_cols[2].link_button(copy.COLLAB["LINK_COPUBS"], links.copubs_url(a, b),
                                 help=copy.FIND["LINK_OPENALEX_HELP"])


def _render_not_offered() -> None:
    """2B-R2-8/13: what this page does NOT show, in plain language, one line per
    measure and no internal reference of any kind. The two directional gap
    tables are gone from the code, not hidden behind a toggle, so the reader is
    told once, here, what replaced them."""
    with st.container(key="collab_not_offered"):
        st.markdown(f"**{copy.SHARED['NOT_OFFERED_HEADER']}**")
        for feature, reason in (
                (copy.COLLAB["NOT_OFFERED_GAPS"], copy.COLLAB["NOT_OFFERED_GAPS_REASON"]),
                (copy.COLLAB["NOT_OFFERED_BREADTH"], copy.COLLAB["NOT_OFFERED_BREADTH_REASON"]),
                (copy.COLLAB["NOT_OFFERED_SUBFIELDS"], copy.COLLAB["NOT_OFFERED_SUBFIELDS_REASON"])):
            st.caption(copy.SHARED["NOT_OFFERED_LINE"].format(feature=feature, reason=reason))


# -------------------------------------------------------------- render ------

def render() -> None:
    """The whole Collaborate page. Computation order: sidebar scenario (so the
    tree/basis a reader carried from Find is read before anything is built) ->
    header -> pair picker -> substrates (behind the spinner) -> the five
    sections of 2B-R2-11, in the order a reader meets the partnership: how much,
    about what, in which topics, what is missing, where to read it."""
    bundle = _bundle()
    scenario = _sidebar_scenario()
    _sidebar_basket(bundle)
    _header(bundle)
    pair = _pair_picker(bundle, _candidates(bundle))
    if pair is None:
        return
    a, b = pair
    # A tree/basis flip pays build_substrates ONCE (cached, at most three
    # scenarios live); every other rerun finds it warm. The spinner's copy says
    # exactly that instead of leaving the page blank.
    with st.spinner(copy.COMPARE["SPINNER_SCENARIO"]):
        _subs(scenario["tree"], scenario["basis"])
    _header_strip(bundle, a, b)
    pulse_row = _render_pulse(bundle, a, b)
    _render_fields(bundle, a, b, pulse_row)
    _render_topics(bundle, a, b, scenario, pulse_row)
    _render_untapped(bundle, a, b, scenario)
    _render_links(bundle, a, b)
    _render_not_offered()

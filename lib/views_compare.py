"""
app/lib/views_compare.py -- the Compare page (Sprint 2 Phase 2B-R, stream CP;
BUILD_PLAN_2BR.md decisions 2B-R-4/5/6/7/8/9/12, S4 contracts, VIZ_SPEC S2
quater 4.1 ... 4.7).

REPLACES the Phase 2B dot-mirror page. What went, and why (all ruled, none of
it taste): the six-institution cap (2B-R-4 -> three, hard), the four dot
mirrors (2B-R-5 -> ONE "Compare by" metric selector over horizontal grouped
bars, because at k = 3 the number fits ON the mark and the dot row could never
carry it), the quadrant small-multiples and the frontier overlay (2B-R-9 -> a
POOLED frontier map plus a diverging "who holds the shared frontier" list, so
cross-institution occlusion is impossible rather than merely reduced).

PHASE 2B-R2 (stream CP3, decisions 2B-R2-3/4/5/8/9/10), what changed and why:
  * the overview cards lose the bootstrap-interval line and the "Publications"
    button, gain a best-value DOT in the leading institution's colour, and put
    the window sentence in each card's own `?`; the institution NAME is now the
    link to its publications (2B-R2-9);
  * the metric selector offers `charts_compare.SELECTOR_METRICS` -- "Publications
    in the world top decile" is retired as a TAB and rides in the PP view's
    gutter and hover instead (2B-R2-3);
  * every section gains a ROW-ORDER control, and the default taxonomy order is
    canonicalised HERE (`_order_rows`) so it cannot move when the reader
    switches metric (2B-R2-5 -- the one thing that makes two tabs comparable);
  * the frontier map gains a POOL selector and a colour-by-domain toggle, both
    wired straight to the builder's own modes (2B-R2-10);
  * and every grey paragraph above or below a chart is now ONE reading line with
    the methodology behind its `?` (2B-R2-8, `_note` / `charts_compare.
    chart_note`, which REFUSES an over-long line rather than truncating it).
Sort toggles were removed in 2B-R and are back in 2B-R2 for a stated reason:
2B-R's rule was "the frame arrives ranked so no control can move a colour", and
colour still never moves -- it follows the institution, not the row -- while the
gate found that a value ranking that cannot be turned OFF makes two metric tabs
incomparable, which is the more expensive of the two problems.

PHASE 2B-R3 (stream VC, BUILD_PLAN_2BR3.md SS1 item 5 / SS3 "VC", the
"ruled WITHOUT grill" list in SIRIS/brainstorms/2026-08-31-benchup-gate2br3-
refinement.md): a LAYOUT rework, not a new indicator. What changed and why:
  * SELECTION moves to the sidebar (SEL, plan ruling 1): the old free-text
    old free-text name-search box, the basket-vs-comparison cap message
    and the inline share link are GONE from this page. The reader shortlists
    from `selection.render_sidebar()` (called on every page) and this page
    now opens on `selection.slots_row("compare", state.COMPARE_CAP)` -- three
    side-by-side pickers over the basket, nothing more. There is no
    "truncated, showing 3 of N" state any more: a slot either holds one of
    the basket's own institutions or it does not, so the old cap-disclosure
    prose has nothing left to disclose.
  * LAYOUT COMPACTION (plan SS1.5): title + ONE promise line -> the three
    slots -> KPI cards -> Coverage (MOVED UP from the bottom, "top generic
    info first") -> the three "Compare by" sections -> the two frontier
    charts -> impact -> a bottom meta block. Every paragraph that used to sit
    between the title and the first chart (the index-size/data-date line,
    this page's own method sentence, the share link) now lives in the bottom
    meta block, mostly inside one collapsible ("About these figures") so a
    reader opens it on purpose rather than scrolling past it -- the point
    being that the FIRST comparison content is visible without scrolling
    past meta prose.
  * PER-CHART FURNITURE (plan SS3 VC item 2): every section now draws its
    controls on ONE row (via `st.columns`, never stacked), then the legend,
    then the chart -- and the "not shown here, and why" disclosure, which
    used to sit as captions ABOVE the metric radio, is now a `st.expander`
    BELOW the chart. Nothing in that disclosure changed; only where a reader
    meets it did.
  * the old per-subfield trends section is DELETED outright (CD4 deleted
    `compare_data.trends_subfields`, the function it drew from) and the old
    pair hand-off section is DELETED outright (the selection rework
    supersedes it; Collaborate's own entry point is `lib/views_collab.py`'s
    slots, not a button on this page).
  * The shared-frontier chart gets its OWN top-twenty-by-combined-volume
    default with a "Show all N" button (plan item 4) -- decoupled from the
    pooled map's pre-existing "Topics plotted" slider, which stays exactly
    as 2B-R2-10 shipped it and now sits on the SAME toggle row as the pool
    and colour-by controls above the map.
  * The impact-by-subfield reading line states the SELECTION RULE in plain
    words (`compare_data.impact_subfields`'s own floor-clearing union)
    instead of only naming a count with no rule behind it.
Nothing above changes an INDICATOR: every frame still comes from
`lib/compare_data.py` unmodified by this file, every figure from
`lib/charts_compare.py`, every colour from `lib/palette.py`.

COMPOSITION ONLY, the same rule as lib/views_find.py: every frame comes from
`lib/compare_data.py`, every figure from `lib/charts_compare.py`, every colour
from `lib/palette.py`, every id rule from `lib/selection.py`, every URL from
`lib/links.py`, every string from `lib/copy.py`. Nothing here recomputes an
indicator and nothing here types a number into a rendered string
(BUILD_PLAN_2A.md L10, scanned by tests/test_narrative.py). The two reshapes
this file does own -- ranking a metric frame's rows and melting the wide
shared-frontier frame into the long shape every builder takes -- move no
value and invent none.

PAGE ORDER (2BR3 VC, plan SS1.5)
  sidebar: counting & taxonomy (the SAME `tree` / `basis` widget keys Find and
  Collaborate use) + the shared search/basket (`selection.render_sidebar`).
  main: title + ONE promise line -> the three slots (`selection.slots_row`)
  -> OVERVIEW cards, one per institution, the 2B-R-7 KPI set -> Coverage ->
  subject profile (the metric selector, fields with a subfield drill) -> ERC
  panels -> SDG goals -> the two frontier charts -> impact (whole output,
  then by subfield, with the floor toggle and the selection rule stated in
  words) -> a bottom meta block (exports, "About these figures", the share
  link).

WHY THE COLOUR IS THE INSTITUTION (2B-1, narrowed once by 2B-R-8)
  Colour on a MARK is the institution and nothing else. A taxonomy's official
  hue may appear as a GLYPH in a row LABEL (ERC domains, UN goals) and never
  the other way round -- `charts_compare` routes that through
  `palette.label_accent_color`, and this file only supplies the accent KEY.
  Slots follow PICKER position (slot 1 = darkest navy; manager merge fix), so
  removing an institution never repaints the survivors (2BR3 plan item 6:
  slot i always draws in `palette.INSTITUTION_COLORS[i]`, darkest = slot 1,
  regardless of which slotbox a reader happened to put that institution in).

LEGEND ABOVE EVERY CHART (2B-R-12)
  `charts_compare.legend_strip` is rendered immediately above each figure, not
  once per page: the page scrolls through several of them, and a legend the
  reader has scrolled past is not a legend. It is also the secondary encoding
  the palette validator's warnings oblige.

PERFORMANCE (2B-14: warm rerun < 2 s; A10)
  `views_find._bundle` / `views_find._subs` are reused BY IMPORT, so the engine
  context and each (tree, basis) substrate are paid once per process and shared
  with every other page. Every frame is `@st.cache_data` keyed on the HASHABLE
  scenario identity (a tuple of ids, the tree, the basis, a level, a metric, a
  floor); ctx/subs are unhashable and are never cache_data arguments.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from lib import charts_compare as X
from lib import compare_data as K
from lib import copy, countries, links, profile_data, selection, state, tiles
from lib import palette as P
from lib.app_config import CFG
from lib.data_cache import manifest
from lib.exports import data_date_label
from lib.exports_xlsx import XLSX_MIME, workbook_bytes, workbook_filename
from lib.palette import NA_MARK
from lib.ranked import works_link_named
from lib.views_find import DASH, SEP, _bundle, _count, _pct, _sidebar_scenario, _subs

# ---------------------------------------------------------------- constants --

# 2B-R-5/2B-R-8: the metric selector's own vocabulary. The ORDER is the order
# the options are offered in; availability per level is `compare_data`'s call,
# never a second opinion typed here.
METRIC_LABELS = {
    "share": copy.COMPARE["METRIC_SHARE"],
    "vol_top10": copy.COMPARE["METRIC_VOL_TOP10"],
    "pp": copy.COMPARE["METRIC_PP"],
    "sdg_share": copy.COMPARE["METRIC_SDG_SHARE"],
    "dynamics": copy.COMPARE["METRIC_DYNAMICS"],
    "si": copy.COMPARE["METRIC_SI"],
    "vol": copy.COMPARE["METRIC_VOL"],
    "fwci": copy.COMPARE["METRIC_FWCI"],
}
# Every section starts from the SAME vocabulary and lets the level filter it
# (2B-R-5). Starting each section from a hand-written short list would hide the
# ERC and SDG gaps instead of disclosing them: as shipped, ERC serves Share and
# Specialisation, SDG serves Share and Dynamics, and each section prints
# `compare_data`'s own reason for every measure it cannot offer -- which is how a
# reader learns that a measure is missing because nothing crosses the ERC panels
# with it, not because this page decided against it.
#
# 2B-R2-3 narrows the vocabulary to `charts_compare.SELECTOR_METRICS`: Share,
# Specialisation, PP(top10%), SDG-tagged share, Change in mean annual volume,
# and Volume where a level defines one -- exactly the "Share . SI . PP . SDG
# share . Dynamics . Volume" order BUILD_PLAN_2BR3.md SS1.5 names for the
# "Compare by" family; 2BR3 changes nothing about this vocabulary or its
# order, only where a reader meets the controls that pick from it.
SUBJECT_METRICS = X.SELECTOR_METRICS
ERC_METRICS = SUBJECT_METRICS
SDG_METRICS = SUBJECT_METRICS

# 2B-R2-5: the row-order control, one per section. `taxonomy` (the default) is
# what makes two metric tabs comparable -- a row stays where it was when the
# measure changes -- and `value` is the toggle for a reader who wants the
# ranking instead. The builder owns both mechanics (`charts_compare.SORT_MODES`);
# this page owns only the widget and the words.
SORT_LABELS = {"taxonomy": copy.COMPARE["SORT_TAXONOMY"],
               "value": copy.COMPARE["SORT_VALUE"]}
SORT_DEFAULT = X.SORT_MODES[0]

# 2B-R2-10: the frontier map's own controls. The POOL is the producer's
# (`compare_data.FRONTIER_POOLS`: which topics are eligible at all); the chart
# module has its own name for the matching RANKING (`charts_compare.POOLS`), so
# the two vocabularies are mapped here, once, rather than each section guessing.
POOL_LABELS = {"volume": copy.COMPARE["FRONTIER_POOL_VOLUME"],
               "elite": copy.COMPARE["FRONTIER_POOL_ELITE"]}
POOL_RULES = {"volume": copy.COMPARE["FRONTIER_POOL_RULE_VOLUME"],
              "elite": copy.COMPARE["FRONTIER_POOL_RULE_ELITE"]}
POOL_CHART_MODE = dict(zip(K.FRONTIER_POOLS, X.POOLS))   # {"volume": "volume", "elite": "frontier"}
POOL_DEFAULT = K.FRONTIER_POOLS[0]

COLOR_BY_LABELS = {"owner": copy.COMPARE["FRONTIER_COLOR_OWNER"],
                   "domain": copy.COMPARE["FRONTIER_COLOR_DOMAIN"]}
COLOR_BY_DEFAULT = X.COLOR_BY[0]

# The accent KEY column each level's builder call needs (2B-R-8). `metric_frame`
# returns the v4 contract columns only, so the key is merged back on from the
# taxonomy's own long frame -- a join, not a recomputation.
ACCENT_KEY = {"erc": "erc_domain", "sdg": "sdg_number"}

# 2B-R-9 / A/B #8: the pooled frontier map's own slider -- the LARGEST set that
# costs nothing in occlusion (VS's MEASURED value: bubble occlusion on the real
# trio is 0.450 at N = 40 and N = 60, 0.588 at N = 80, 0.708 at N = 120). This
# is the POOLED MAP's own control (2B-R2-10); the SHARED-FRONTIER chart below
# it has its own, unrelated top-N rule (2BR3 plan item 4, `SHARED_FRONTIER_TOP_N`).
FRONTIER_TOPN_DEFAULT = 60
FRONTIER_TOPN_MIN = 20
FRONTIER_TOPN_MAX = 120
FRONTIER_TOPN_STEP = 20

# 2BR3 VC item 4: "Who holds the shared frontier" shows the twenty topics with
# the largest COMBINED volume by default, with a button (never a slider, and
# never the pooled map's own "Topics plotted" control above) swapping in the
# rest. `charts_compare.fig_diverging_shared` already takes `top_n=None` to
# mean "show every row" (PAL wired this; see its own acceptance).
SHARED_FRONTIER_TOP_N = 20

# The subfields the impact panel draws out of the union it is handed (A1).
IMPACT_ROWS_TOP_N = 20

# The impact floors the artefact ships (data_contract.yaml: impact_cells carries
# floor in {10, 30}); the higher one is the default and the lower one is the
# labelled "more cells, wider intervals" variant (A1).
IMPACT_FLOORS = tuple(sorted(K.IMPACT_CELL_FLOORS, reverse=True))
IMPACT_FLOOR_DEFAULT = IMPACT_FLOORS[0]

# CSV file-name slugs. Code identifiers, never rendered copy -- the visible
# labels are `copy.COMPARE["VIEW_*"]`. 2BR3 drops "trends" (the section is
# deleted, plan SS1 item 3).
SLUGS = {"overview": "overview", "subject": "subject", "erc": "erc", "sdg": "sdg",
         "frontier_map": "frontier_map", "shared_frontier": "shared_frontier",
         "impact": "impact", "impact_subfields": "impact_subfields",
         "coverage": "coverage"}

WINDOW_START, WINDOW_END = CFG["window"]

SWATCH_MARK = "\N{BLACK CIRCLE}"    # the strip swatch, tinted by the palette


# ------------------------------------------------------------------ frames --
# One @st.cache_data per K frame. `ids` is always a TUPLE: a list is unhashable
# and would make every one of these a cache miss on every rerun.

@st.cache_data(show_spinner=False, max_entries=12)
def _overview(ids: tuple) -> pd.DataFrame:
    return K.overview(_bundle()["ctx"], list(ids))


@st.cache_data(show_spinner=False, max_entries=48)
def _metric(ids: tuple, tree: str, basis: str, level: str, metric: str,
            field_id: int | None, floor: int) -> pd.DataFrame:
    """`compare_data.metric_frame`, cached. An unavailable (metric, level) pair
    comes back as a typed EMPTY frame carrying `.attrs["reason"]`; Streamlit's
    cache round-trips a DataFrame and drops `.attrs` with it, so the reason is
    read from `K.UNAVAILABLE_REASON` at the call site instead of off the frame
    -- same dict, same words, no cache-shaped hole in the disclosure."""
    return K.metric_frame(_bundle()["ctx"], _subs(tree, basis), list(ids), level, metric,
                          field_id=field_id, tree=tree, floor=floor)


@st.cache_data(show_spinner=False, max_entries=12)
def _fields(ids: tuple, tree: str, basis: str) -> pd.DataFrame:
    """Only the field PICKER reads this frame (the drill's option list); the
    bars themselves come from `metric_frame`."""
    return K.fields_long(_bundle()["ctx"], _subs(tree, basis), list(ids))


@st.cache_data(show_spinner=False, max_entries=12)
def _erc(ids: tuple) -> pd.DataFrame:
    return K.erc_long(_bundle()["ctx"], list(ids))


@st.cache_data(show_spinner=False, max_entries=12)
def _sdg(ids: tuple) -> pd.DataFrame:
    return K.sdg_long(_bundle()["ctx"], list(ids))


@st.cache_data(show_spinner=False, max_entries=24)
def _frontier_pooled(ids: tuple, tree: str, basis: str, top_n: int,
                     pool: str = POOL_DEFAULT) -> pd.DataFrame:
    return K.frontier_pooled(_bundle()["ctx"], _subs(tree, basis), list(ids), top_n, pool)


@st.cache_data(show_spinner=False, max_entries=12)
def _shared_frontier(ids: tuple, tree: str, basis: str,
                     pool: str = POOL_DEFAULT) -> pd.DataFrame:
    return K.shared_frontier(_bundle()["ctx"], _subs(tree, basis), list(ids), pool)


@st.cache_data(show_spinner=False, max_entries=12)
def _impact_index(ids: tuple) -> pd.DataFrame:
    return K.impact_index(_bundle()["ctx"], list(ids))


@st.cache_data(show_spinner=False, max_entries=24)
def _impact_subfields(ids: tuple, tree: str, floor: int) -> pd.DataFrame:
    return K.impact_subfields(_bundle()["ctx"], list(ids), tree, floor)


@st.cache_data(show_spinner=False, max_entries=12)
def _coverage(ids: tuple) -> pd.DataFrame:
    return K.coverage(_bundle()["ctx"], list(ids))


@st.cache_data(show_spinner=False, max_entries=24)
def _top_shared(ids: tuple, tree: str, basis: str, n: int) -> pd.DataFrame:
    return K.top_shared_subfields(_bundle()["ctx"], _subs(tree, basis), list(ids), n)


@st.cache_data(show_spinner=False, max_entries=2)
def _ci_sentence() -> str:
    """2B-R-12: the EXACT coverage of every interval on this page, in the words
    stream MU pinned to `METHODS_FAISCEAU.md` (`copy.IMPACT_CI_CAPTION`) and
    filled from the same `views_methods.methods_values()` the Methods page
    itself renders -- so the two can never drift, and neither number is typed
    here. Imported inside the function: the Methods module reads the contract
    file and the override CSV at call time, which a page that never reaches
    this caption should not pay for."""
    from lib import views_methods

    values = views_methods.methods_values()
    return copy.IMPACT_CI_CAPTION.format(ci_coverage=values["ci_coverage"],
                                         n_bootstrap=values["n_bootstrap"])


# -------------------------------------------------------------- formatting --

def _name(ctx: dict, iid: str) -> str:
    return str(ctx["index_by_id"].loc[iid, "display_name"])


def _names(ctx: dict, ids) -> dict:
    return {iid: _name(ctx, iid) for iid in ids}


def _slots(ctx: dict, ids) -> dict:
    """`{institution_id: slot}` by PICKER position (2BR3 plan item 6, manager
    merge fix: slot 1 = the darkest navy -- the reader's own slot layout IS
    the colour key, so the KPI cards and every legend follow the order the
    slots show on screen, never an internal key). `ids` arrives in picker
    order from `selection.slots_row` (see `render`)."""
    return {iid: pos for pos, iid in enumerate(ids)}


def _slot_order(ids, slots: dict) -> list:
    """The ids in the order every figure and the legend draw them."""
    return sorted(ids, key=lambda i: (slots.get(i, len(slots)), str(i)))


def _legend(ids, slots: dict, names: dict, *, shared: bool = False) -> None:
    """2B-R-12: the one key every figure needs, immediately above THAT figure."""
    st.markdown(X.legend_strip(_slot_order(ids, slots), slots=slots, names=names,
                               shared=shared, shared_label=copy.COMPARE["LEGEND_SHARED"]),
                unsafe_allow_html=True)


def _note(reading: str, tooltip: str | None = None) -> None:
    """2B-R2-8's ONE presentation primitive on this page: a short reading line
    under a chart, with the methodology folded into its `?`.

    Every grey paragraph this page used to stack above and below its figures now
    arrives through here. `charts_compare.chart_note` REFUSES a reading line
    longer than its own cap or one carrying a line break, so the wall of prose
    cannot come back through this door one release later: an over-long reading
    line fails at render time, in the test suite, not in the reader's face."""
    st.markdown(X.chart_note(reading, tooltip), unsafe_allow_html=True)


def _not_offered_expander(hidden: list, level: str) -> None:
    """2BR3 VC item 2: "Not shown here, and why" moves to a COLLAPSIBLE BELOW
    the chart (never captions stacked above the metric selector, which is
    where it lived through 2B-R2). The header and each reason are the SAME
    strings as before -- `copy.SHARED`'s wording, `compare_data`'s own
    sentence -- only the container changed."""
    if not hidden:
        return
    with st.expander(copy.SHARED["NOT_OFFERED_HEADER"]):
        for m in hidden:
            st.caption(_not_offered_line(METRIC_LABELS[m], K.UNAVAILABLE_REASON[(m, level)]))


def _not_offered_line(label: str, reason: str) -> str:
    """One "not shown here, and why" line, in `copy.SHARED`'s wording.

    A reason that ALREADY opens with the measure's own name is printed as it
    stands: 2B-R2-8's own example sentence is written that way ("Volume: shown
    in the chart gutter instead of as a tab"), and pouring it into the shared
    "{feature}: {reason}" template rendered "Volume: Volume: shown ..." on the
    live page. Trimming the duplicate here keeps ONE wording for the situation
    without editing a producer's sentence from a page."""
    prefix = f"{label}:"
    if reason.strip().lower().startswith(prefix.lower()):
        return reason.strip()
    return copy.SHARED["NOT_OFFERED_LINE"].format(feature=label, reason=reason)


def _scenario_words(sc: dict) -> dict:
    return {"basis": copy.BASIS_LABELS[sc["basis"]], "tree": copy.TREE_LABELS[sc["tree"]]}


def _window(bounds) -> str:
    """"2020-2022" from `(2020, 2022)` -- the dynamics windows, named from
    `compare_data`'s own constants (2B-R-6) rather than typed."""
    return f"{bounds[0]}{DASH}{bounds[1]}"


def _download(df: pd.DataFrame, *, slug: str, sc: dict, key: str) -> None:
    """Streamlit 1.61 accepts a zero-arg callable for `data`, so the CSV is
    encoded only when someone actually clicks. The RAW frame goes out."""
    name = f"benchup_compare_{slug}_{sc['tree']}_{sc['basis']}.csv"
    st.download_button(copy.COMPARE["DOWNLOAD_VIEW"],
                       lambda: df.to_csv(index=False).encode("utf-8"),
                       mime="text/csv", file_name=name, key=f"dl_{key}")


# ------------------------------------------------------------------ header --

def _header() -> None:
    """2BR3 VC item 1: title + ONE promise line, and nothing else -- the index
    size, the data date and this page's own method sentence move to the
    bottom meta block (`_footer`), inside "About these figures", so the first
    comparison content is visible without scrolling past meta prose."""
    st.title(copy.NAV["COMPARE_LABEL"])
    st.caption(copy.NAV["COMPARE_LEAD"])


# --------------------------------------------------- overview (VIZ 4.1) -----

CARD_COLUMNS = ("vol_full", "sdg_share", "frontier_top25_share", "pp",
                "intl_share", "company_share")
# 2B-R2-9: the six card measures, in the order they are drawn, named by the
# `compare_data.overview` COLUMN each one renders. The tuple is what `_leaders`
# ranks over, so a card and its dot can never be computed from two different
# columns.


def _card_facts(row, cell) -> list:
    """`[(column, label, value, tooltip)]` for ONE institution's card, in the
    2B-R-7 order. Every value arrives from `compare_data.overview`; a null
    source cell renders `n/a`, never zero.

    2B-R2-9 changes the shape here twice. The bootstrap-interval SUBLINE is
    gone: an interval printed under a value competed with the value at the same
    weight, and the intervals themselves are still drawn -- as intervals -- on
    the impact panel below, where they are the subject. And the window sentence
    that used to sit as one grey caption under the WHOLE strip is folded into
    each card's own `?`, beside the figure it qualifies: these six measures do
    not share a window or a denominator, so one caption under all of them could
    only ever be true of some.

    `row` (the institution's index row) is unused by the facts themselves and
    kept in the signature because the caller has it: every VALUE comes from the
    overview frame, which is exactly what the read-back test pins."""
    words = {"y0": WINDOW_START, "y1": WINDOW_END}
    window_tip = copy.COMPARE["CARD_WINDOW_TIP"].format(**words)
    return [
        ("vol_full", copy.FIND["KPI_PUBS_LABEL"], _count(cell["vol_full"]),
         copy.FIND["PUBLICATIONS_TOOLTIP"].format(bonus_year=CFG["bonus_year"], **words)
         + " " + copy.COMPARE["CARD_PUBS_FRAC"].format(n=_count(cell["vol_frac"]))),
        ("sdg_share", copy.FIND["KPI_SDG_LABEL"], _pct(cell["sdg_share"]),
         f"{copy.FIND['KPI_SDG_HELP']} {window_tip}"),
        ("frontier_top25_share", copy.FIND["KPI_FRONTIER_LABEL"],
         _pct(cell["frontier_top25_share"]),
         f"{copy.FIND['KPI_FRONTIER_HELP']} {window_tip}"),
        ("pp", copy.FIND["KPI_PP_LABEL"], _pct(cell["pp"]),
         f"{copy.FIND['KPI_PP_HELP_R2']} {window_tip}"),
        ("intl_share", copy.FIND["KPI_INTL_LABEL"], _pct(cell["intl_share"]),
         copy.FIND["KPI_INTL_HELP"].format(**words)),
        ("company_share", copy.FIND["KPI_COMPANY_LABEL"], _pct(cell["company_share"]),
         copy.FIND["KPI_COMPANY_HELP"].format(**words)),
    ]


def _leaders(df: pd.DataFrame) -> dict:
    """`{overview column: institution_id}` for the HIGHEST value of each card
    measure across the compared set (2B-R2-9's best-value dot).

    A TIE yields no entry, so no dot is drawn: the dot's whole claim is "this
    one leads", and two institutions level on a measure do not. A column with no
    finite value anywhere likewise yields nothing -- the same absence-is-never-
    zero rule the cards themselves obey."""
    cells = df.set_index("institution_id")
    out = {}
    for col in CARD_COLUMNS:
        series = pd.to_numeric(cells[col], errors="coerce").dropna()
        if series.empty:
            continue
        winners = series[series == series.max()]
        if len(winners) == 1:
            out[col] = str(winners.index[0])
    return out


def _esc(value) -> str:
    """Minimal HTML escape for institution-derived text going into markup."""
    return (str(value).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _card_html(label: str, value: str, dot: str) -> str:
    """ONE compare card: the measure NAME first, the value under it, and the
    2B-R2-9 leader dot beside the value.

    Why not `tiles.kpi_tile`, which draws the Find profile's cards: that helper
    ESCAPES everything it is given -- correctly, it renders institution data --
    so a dot cannot be passed through it, and its third line is an index
    baseline these cards do not have (here the reference is the card NEXT to
    this one, which is what a comparison is). What this DOES borrow from it is
    the TYPE SCALE: every size and weight below is `lib/tiles.py`'s own
    constant, so the two card families cannot drift apart, and no number and no
    colour is typed in this file."""
    return (f'<div class="{tiles.TILE_CLASS}">'
            f'<div style="font-size:{tiles.LABEL_PX}px;font-weight:{tiles.LABEL_WEIGHT};'
            f'line-height:{tiles.LABEL_LINE_HEIGHT};color:{P.INK};">{_esc(label)}</div>'
            f'<div style="display:flex;align-items:center;gap:{X.DOT_GAP_PX}px;'
            f'font-size:{tiles.VALUE_PX}px;font-weight:{tiles.VALUE_WEIGHT};'
            f'line-height:{tiles.VALUE_LINE_HEIGHT};color:{P.INK};">'
            f'<span>{_esc(value)}</span>{dot}</div></div>')


def _view_overview(ctx: dict, ids: list, slots: dict) -> pd.DataFrame:
    """VIZ_SPEC 4.1: not a chart. One card per compared institution, in SLOT
    order, carrying the swatch that binds it to every figure below and the six
    2B-R-7 KPI facts as NUMBERS -- six measures with no shared unit or range is
    a table's job, and drawing it would produce six mini-charts competing with
    the metric selector immediately underneath.

    2B-R2-9 rewrote the surface: the institution NAME is the link to its own
    publications in OpenAlex (the same `works_link_named` builder the Find
    profile and the benchmark tables use); the leading institution's card
    carries a dot in its own colour on the measure it leads.

    2BR3 removes the per-card "Remove" button and the strip's "Clear the
    comparison" button (plan item 1/8): an institution now leaves the
    comparison by being set back to the empty option in its OWN slot picker
    (`selection.slots_row`, drawn just above this section) or by being
    removed from the basket in the sidebar (`selection.render_sidebar`,
    always visible) -- a THIRD, page-local way to do the same thing was one
    more place a reader had to look for "remove"."""
    st.subheader(copy.COMPARE["OVERVIEW_HEADER"])
    df = _overview(tuple(ids))
    cells = df.set_index("institution_id")
    leaders = _leaders(df)
    order = _slot_order(ids, slots)
    with st.container(key="compare_strip", border=True):
        cols = st.columns(len(order))
        for col, iid in zip(cols, order):
            row = ctx["index_by_id"].loc[iid]
            slot = slots.get(iid, len(slots))
            colour = P.institution_color(slot)
            name = _name(ctx, iid)
            # A coloured GLYPH, not a styled box: a box would need typed pixel
            # lengths inside a rendered string (BUILD_PLAN_2A.md L10). The only
            # interpolated values are the palette's own colour and the link.
            col.markdown(f'<span style="color:{colour}">{SWATCH_MARK}</span> '
                         f"**[{_esc(name)}]({works_link_named(iid, name)})**",
                         unsafe_allow_html=True, help=copy.FIND["IDENTITY_NAME_HELP"])
            col.caption(f"{str(row['type'])} {SEP} "
                        f"{countries.name(str(row['country_code']))}")
            for column, label, value, tip in _card_facts(row, cells.loc[iid]):
                dot = X.best_value_dot(slot) if leaders.get(column) == iid else ""
                with col.container(border=True):
                    st.markdown(_card_html(label, value, dot),
                                unsafe_allow_html=True, help=tip)
    _note(copy.COMPARE["OVERVIEW_NOTE"], copy.COMPARE["OVERVIEW_NOTE_TIP"])
    _download(df, slug=SLUGS["overview"], sc={"tree": "", "basis": ""}, key="overview")
    return df


# ----------------------------------------- the metric selector (VIZ 4.2-4.5) --

def _metric_selector(key: str, level: str, metrics: tuple) -> tuple:
    """ONE "Compare by" control per section (2B-R-5). Options the data cannot
    serve at this level are HIDDEN, never offered returning zero.

    Returns `(picked_metric, hidden_metrics)` -- 2BR3 change: this function no
    longer RENDERS the hidden-options disclosure itself (that used to sit as
    captions directly under the radio, i.e. ABOVE the chart); the caller now
    passes `hidden` to `_not_offered_expander`, which draws it as a
    collapsible BELOW the chart (plan SS3 VC item 2). The stored choice is
    still clamped BEFORE the widget is built: a level change (the field
    drill) can retire the option a reader last picked, and Streamlit raises on
    a session value that is not in the option list rather than falling back."""
    available = [m for m in metrics if K.metric_frame_available(m, level)]
    hidden = [m for m in metrics if m not in available]
    labels = [METRIC_LABELS[m] for m in available]
    if st.session_state.get(key) not in labels:
        st.session_state[key] = labels[0]
    picked = st.radio(copy.COMPARE["METRIC_LABEL"], labels, horizontal=True, key=key,
                      help=copy.COMPARE["METRIC_HELP"], **state.PERSIST)
    return available[labels.index(picked)], hidden


def _sort_toggle(key: str) -> str:
    """2B-R2-5's per-section row-order control. Returns a
    `charts_compare.SORT_MODES` value, never a label: the builder owns the
    mechanics of both orders, this page owns only the choice and the words."""
    labels = [SORT_LABELS[m] for m in X.SORT_MODES]
    if st.session_state.get(key) not in labels:
        st.session_state[key] = SORT_LABELS[SORT_DEFAULT]
    picked = st.radio(copy.COMPARE["SORT_LABEL"], labels, horizontal=True, key=key,
                      help=copy.COMPARE["SORT_HELP"], **state.PERSIST)
    return X.SORT_MODES[labels.index(picked)]


def _current_sort(key: str) -> str:
    """The sort mode a section's toggle currently holds, read back off session
    state for the workbook (the widget itself stores the LABEL)."""
    label = st.session_state.get(key)
    for mode, text in SORT_LABELS.items():
        if text == label:
            return mode
    return SORT_DEFAULT


def _order_rows(df: pd.DataFrame) -> pd.DataFrame:
    """The frame in its CANONICAL taxonomy order: by display domain, then by the
    taxon's own id inside the domain (2B-R2-5).

    This is order only -- no value moves, no row is added or dropped -- and it
    is what makes the row order STABLE ACROSS METRIC TABS. The builder's
    `sort="taxonomy"` groups by domain and then keeps the frame's own ARRIVAL
    order inside each group, so stability is only as good as the arrival order
    the producer happened to give it: the share frame arrives in field-id order,
    the impact frame in the order its own cells are stored, and two tabs would
    then disagree about where a row sits. Sorting here, once, on keys every
    metric frame carries by contract, removes that dependency. `sort="value"`
    re-ranks on top of this, so the toggle still works exactly as before."""
    if df.empty:
        return df
    out = df.copy()
    if "domain_order" not in out.columns:
        return out.reset_index(drop=True)
    out["_dom"] = pd.to_numeric(out["domain_order"], errors="coerce")
    out["_dom"] = out["_dom"].fillna(float(len(out)))
    out["_key"] = pd.to_numeric(out["taxon_id"], errors="coerce")
    return out.sort_values(["_dom", "_key", "institution_id"], kind="mergesort").drop(
        columns=["_dom", "_key"]).reset_index(drop=True)


def _decorate(df: pd.DataFrame, level: str, long: pd.DataFrame, key_col: str,
              label_col: str | None = None) -> pd.DataFrame:
    """Merge the 2B-R-8 accent KEY (and, for the SDGs, the numbered label) back
    onto a metric frame from the taxonomy's own long frame. `metric_frame`
    returns the v4 contract columns and nothing else, so without this join the
    ERC and SDG row labels would carry no official-colour glyph at all."""
    if df.empty or long.empty:
        return df
    cols = [key_col] + [c for c in (ACCENT_KEY.get(level), label_col) if c]
    lookup = long[cols].drop_duplicates(subset=[key_col])
    out = df.merge(lookup, left_on="taxon_id", right_on=key_col, how="left")
    if label_col:
        out["taxon_label"] = out[label_col].fillna(out["taxon_label"])
    return out.drop(columns=[c for c in (key_col, label_col) if c and c in out.columns])


_RATIO_CAPTION_METRICS = ("share", "pp", "sdg_share", "dynamics", "fwci")
# D5 (CHROME_CONTRACT.md §7, normative list under §0/§7): the ratio-chart
# families that get the one-line basis/floor/coverage caption directly under
# the section title. `si` and `vol` are excluded -- the contract's own list
# names Share, PP, SDG-tagged share, Dynamics and FWCI only; `si` already
# carries an equivalent basis/floor disclosure through `_metric_tip`'s own
# `CAPTION_SI`/`CAPTION_SI_FLOOR` lines and `vol` is a raw count with no
# basis or floor to disclose.


def _basis_caption(text: str, *, warn: bool = False) -> None:
    st.markdown(X.basis_caption(text, warn=warn), unsafe_allow_html=True)


def _ratio_caption(df: pd.DataFrame, metric: str, level: str, sc: dict, *,
                   ids, tree: str, basis: str, field_id: int | None, floor: int) -> None:
    """D5: one line, directly under the section title, stating the chart's
    own basis/floor/unscored-count -- read off the FRAME and computed from
    real rows, never hand-typed (this kills the "2130-vs-1699" / "only 5
    fields" confusion class at the source, CHROME_CONTRACT.md §7).

    PP and FWCI are BASIS-PINNED (D4): their line states the FIXED basis they
    are always drawn on (articles & reviews), never the page's full/frac
    toggle -- this doubles as D4's "explicit small chip naming the pinned
    basis". Their unscored count is `taxa this basket has SOME share in`
    (the `share` metric frame, which never drops a row for a floor reason)
    MINUS `taxa this chart actually draws` -- the same union/floor idiom the
    Impact section's own `NOTE_IMPACT_SUBFIELDS` caption already uses.

    Every other covered metric (share/sdg_share/dynamics) states the page's
    CURRENT basis (it follows the toggle) and never warns -- these families
    have no floor that can drop a taxon."""
    if metric not in _RATIO_CAPTION_METRICS:
        return
    words = _scenario_words(sc)
    if metric in ("pp", "fwci"):
        universe = _metric(tuple(ids), tree, basis, level, "share", field_id, floor)
        n_have = int(universe["taxon_id"].nunique()) if not universe.empty else 0
        n_scored = int(df["taxon_id"].nunique()) if not df.empty else 0
        n_unscored = max(0, n_have - n_scored)
        if metric == "pp":
            key = "CAPTION_BASIS_PP_UNSCORED" if n_unscored else "CAPTION_BASIS_PP"
            text = copy.COMPARE[key].format(y0=WINDOW_START, y1=WINDOW_END,
                                            floor=int(floor), n=n_unscored)
        else:
            grain = K.FWCI_GRAIN_WORD[level]
            key = "CAPTION_BASIS_FWCI_UNSCORED" if n_unscored else "CAPTION_BASIS_FWCI"
            text = copy.COMPARE[key].format(y0=WINDOW_START, y1=WINDOW_END,
                                            n=n_unscored, grain=grain)
            if level == "erc":
                text += copy.COMPARE["CAPTION_BASIS_FWCI_ERC_GAP"]
        _basis_caption(text, warn=bool(n_unscored))
        return
    if metric == "dynamics":
        text = copy.COMPARE["CAPTION_BASIS_DYNAMICS"].format(
            w1=_window(K.DYNAMICS_W1), w2=_window(K.DYNAMICS_W2), basis=words["basis"])
    else:  # share / sdg_share
        text = copy.COMPARE["CAPTION_BASIS_SHARE"].format(
            basis=words["basis"], y0=WINDOW_START, y1=WINDOW_END)
    _basis_caption(text, warn=False)


def _metric_chart(df: pd.DataFrame, metric: str, ids, slots, names, level: str,
                  *, key: str, sort: str = SORT_DEFAULT) -> None:
    # D2/D3: FWCI's reference line is the European corpus-median WORK-FWCI per
    # taxon -- a different aggregation unit than the generic "index reference"
    # (institution mean) PP/SDG-share/Dynamics share, so the hover names it
    # explicitly (`compare_data.fwci_ref_label`, never hand-typed) rather than
    # falling back to `charts_compare.HOVER_REFERENCE`.
    ref_label = K.fwci_ref_label(level) if metric == "fwci" else None
    _legend(ids, slots, names)
    st.plotly_chart(
        X.fig_metric_bars(df, metric, _slot_order(ids, slots), slots=slots, names=names,
                          level=level, sort=sort, accent_col=ACCENT_KEY.get(level),
                          metric_label=METRIC_LABELS[metric], ref_label=ref_label),
        width="stretch", key=key)


def _metric_tip(df: pd.DataFrame, metric: str, sc: dict, *, accent: bool = False,
                level: str | None = None) -> str:
    """Everything that used to be a stack of grey captions under a metric chart,
    assembled into ONE tooltip (2B-R2-8): the scenario, the frame's own
    denominator, what the gutter numbers are, what the dashed reference is and
    -- crucially -- which of the two baselines it is NOT (2B-R2-3: the world
    top decile is cut on world publications per topic and year; the dashed rule
    is the mean over the institutions in this index), the low-volume marker, the
    row-label accent, and specialisation's own floors.

    The DENOMINATOR sentence is read off the frame, never written here: a
    hand-typed denominator is a second opinion about a number this page does not
    own, and for Dynamics it is also where both windows are named verbatim.

    2C (D2/D3): `metric="fwci"` never uses the generic `TIP_REFERENCE` line
    (the "average across every institution" wording is WRONG for a corpus-
    median-of-works reference, WT_2C.md claim 1) -- it names the grain-specific
    label instead (`compare_data.fwci_ref_label(level)`, requires `level`)."""
    parts = [copy.COMPARE["TIP_SCENARIO"].format(**_scenario_words(sc))]
    if not df.empty and "denominator" in df.columns:
        parts.append(str(df["denominator"].iloc[0]))
    parts.append(copy.COMPARE["TIP_GUTTER"])
    if metric == "fwci" and level:
        parts.append(copy.COMPARE["TIP_REFERENCE_FWCI"].format(ref_label=K.fwci_ref_label(level)))
    elif metric in X.REF_METRICS:
        parts.append(copy.COMPARE["TIP_REFERENCE"])
    if not df.empty and "vol_full_annual_mean" in df.columns \
            and pd.to_numeric(df["vol_full_annual_mean"], errors="coerce").notna().any():
        parts.append(copy.COMPARE["TIP_LOW_VOLUME"].format(
            floor=f"{P.RATIO_HATCH_FLOOR:,.0f}", y0=WINDOW_START, y1=WINDOW_END))
    if accent:
        parts.append(copy.COMPARE["TIP_ACCENT"])
    if metric == "si":
        parts.append(copy.FIND["CAPTION_SI"])
        parts.append(copy.FIND["CAPTION_SI_FLOOR"].format(
            floor_solid=int(profile_data.SI_FLOOR_SOLID),
            floor_thin=int(profile_data.SI_FLOOR_THIN)))
    return " ".join(parts)


def _view_subject(ids, slots, names, sc) -> tuple:
    """2B-R-5: fields by default, a drill into ONE field's subfields, one metric
    selector over both. 2BR3 puts the drill, the metric selector and the sort
    toggle on ONE row (`st.columns`, plan SS3 VC item 2) above the legend and
    the chart, and moves the hidden-metric disclosure to a collapsible below."""
    st.subheader(copy.COMPARE["VIEW_SUBJECT"])
    fields = _fields(tuple(ids), sc["tree"], sc["basis"])
    options = [None] + [int(f) for f in sorted(fields["field_id"].unique())]
    labels = dict(zip(fields["field_id"], fields["field_name"]))
    c_drill, c_metric, c_sort = st.columns([2, 4, 2])
    with c_drill:
        field_id = st.selectbox(
            copy.COMPARE["DRILL_LABEL"], options,
            format_func=lambda f: copy.COMPARE["DRILL_ALL"] if f is None else str(labels.get(f, f)),
            key="cmp_field_drill", **state.PERSIST)
    level = "field" if field_id is None else "subfield"
    with c_metric:
        metric, hidden = _metric_selector("cmp_metric_subject", level, SUBJECT_METRICS)
    with c_sort:
        sort = _sort_toggle("cmp_sort_subject")
    floor = int(st.session_state.get("cmp_impact_floor") or IMPACT_FLOOR_DEFAULT)
    df = _order_rows(_metric(tuple(ids), sc["tree"], sc["basis"], level, metric,
                             field_id, floor))
    if df.empty:
        st.caption(copy.COMPARE["EMPTY_METRIC"])
        _not_offered_expander(hidden, level)
        return df, level, metric
    _ratio_caption(df, metric, level, sc, ids=ids, tree=sc["tree"], basis=sc["basis"],
                   field_id=field_id, floor=floor)
    _metric_chart(df, metric, ids, slots, names, level, key="fig_cmp_subject", sort=sort)
    reading = copy.COMPARE["NOTE_SUBJECT"]
    tip = _metric_tip(df, metric, sc, level=level)
    if level == "subfield":
        reading = copy.COMPARE["CAPTION_DRILL"].format(field=str(labels.get(field_id, field_id)))
        tip = f"{copy.COMPARE['NOTE_SUBJECT']} {tip}"
    _note(reading, tip)
    _not_offered_expander(hidden, level)
    _download(df, slug=SLUGS["subject"], sc=sc, key="subject")
    return df, level, metric


def _shares_line(ctx: dict, ids, slots: dict, numerator: str) -> str:
    """"Name: share" for every compared institution, in the legend's own order
    -- the ERC and SDG views both rest on an institution-specific denominator,
    so the caption has to give one figure per institution."""
    idx = ctx["index_by_id"]
    parts = []
    for iid in _slot_order(ids, slots):
        row = idx.loc[iid]
        total = row["total_frac"]
        value = (row[numerator] / total) if total and not pd.isna(total) and total > 0 else None
        parts.append(f"{_name(ctx, iid)}: {_pct(value)}")
    return f" {SEP} ".join(parts)


def _taxon_tip(ctx, ids, slots, sc, df, metric, numerator: str, accent_key: str,
               level: str) -> str:
    """The ERC/SDG tooltip: the metric tooltip, plus the per-institution
    classified/tagged shares (each of these two views rests on a denominator
    that differs from one institution to the next, so one figure could not
    stand for the set), plus the accent rule and the fractional-only note when
    the reader is on the full basis. `level` ("erc"/"sdg") threads through to
    `_metric_tip` for the fwci-specific reference wording (D2/D3)."""
    parts = [_metric_tip(df, metric, sc, accent=True, level=level),
             copy.COMPARE[accent_key],
             copy.COMPARE["CAPTION_CLASSIFIED_SHARES"].format(
                 shares=_shares_line(ctx, ids, slots, numerator))]
    if sc["basis"] == "full":
        parts.append(copy.FIND["FRACTIONAL_ONLY_PANEL"])
    return " ".join(parts)


def _view_erc(ctx, ids, slots, names, sc) -> tuple:
    st.subheader(copy.COMPARE["VIEW_ERC"])
    c_metric, c_sort = st.columns([4, 2])
    with c_metric:
        metric, hidden = _metric_selector("cmp_metric_erc", "erc", ERC_METRICS)
    with c_sort:
        sort = _sort_toggle("cmp_sort_erc")
    df = _order_rows(_metric(tuple(ids), sc["tree"], sc["basis"], "erc", metric, None,
                             IMPACT_FLOOR_DEFAULT))
    df = _decorate(df, "erc", _erc(tuple(ids)), "panel_idx")
    if df.empty:
        st.caption(copy.COMPARE["EMPTY_METRIC"])
        _not_offered_expander(hidden, "erc")
        return df, metric
    _ratio_caption(df, metric, "erc", sc, ids=ids, tree=sc["tree"], basis=sc["basis"],
                   field_id=None, floor=IMPACT_FLOOR_DEFAULT)
    _metric_chart(df, metric, ids, slots, names, "erc", key="fig_cmp_erc", sort=sort)
    _note(copy.COMPARE["NOTE_ERC"],
          _taxon_tip(ctx, ids, slots, sc, df, metric, "erc_classified_mass_frac",
                     "CAPTION_ACCENT_ERC", "erc"))
    _not_offered_expander(hidden, "erc")
    _download(df, slug=SLUGS["erc"], sc=sc, key="erc")
    return df, metric


def _view_sdg(ctx, ids, slots, names, sc) -> tuple:
    st.subheader(copy.COMPARE["VIEW_SDG"])
    c_metric, c_sort = st.columns([4, 2])
    with c_metric:
        metric, hidden = _metric_selector("cmp_metric_sdg", "sdg", SDG_METRICS)
    with c_sort:
        sort = _sort_toggle("cmp_sort_sdg")
    df = _order_rows(_metric(tuple(ids), sc["tree"], sc["basis"], "sdg", metric, None,
                             IMPACT_FLOOR_DEFAULT))
    df = _decorate(df, "sdg", _sdg(tuple(ids)), "sdg_idx", label_col="sdg_label_numbered")
    if df.empty:
        st.caption(copy.COMPARE["EMPTY_METRIC"])
        _not_offered_expander(hidden, "sdg")
        return df, metric
    _ratio_caption(df, metric, "sdg", sc, ids=ids, tree=sc["tree"], basis=sc["basis"],
                   field_id=None, floor=IMPACT_FLOOR_DEFAULT)
    _metric_chart(df, metric, ids, slots, names, "sdg", key="fig_cmp_sdg", sort=sort)
    _note(copy.COMPARE["NOTE_SDG"],
          _taxon_tip(ctx, ids, slots, sc, df, metric, "sdg_classified_mass_frac",
                     "CAPTION_ACCENT_SDG", "sdg"))
    _not_offered_expander(hidden, "sdg")
    _download(df, slug=SLUGS["sdg"], sc=sc, key="sdg")
    return df, metric


# ------------------------------------------------ the frontier (VIZ 4.6/4.7) --

def _shared_long(df: pd.DataFrame, ids) -> pd.DataFrame:
    """The wide pooled frame (`vol_<institution_id>` per column) melted into the
    long shape every builder takes. A side that holds NOTHING on a shared topic
    keeps no row, so the builder draws an absent bar rather than a zero-length
    one (VIZ_SPEC 4.7's own empty state)."""
    cols = ["institution_id", "topic_id", "name", "vol", "combined_vol"]
    if df.empty:
        return pd.DataFrame(columns=cols)
    frames = []
    for iid in ids:
        col = f"vol_{iid}"
        if col not in df.columns:
            continue
        mine = df[["topic_id", "name", "combined_vol"]].copy()
        mine["institution_id"] = iid
        mine["vol"] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
        frames.append(mine[mine["vol"] > 0])
    if not frames:
        return pd.DataFrame(columns=cols)
    return pd.concat(frames, ignore_index=True).reindex(columns=cols)


def _frontier_controls() -> tuple:
    """2BR3 puts all THREE of the pooled map's own controls -- WHICH topics are
    eligible, WHAT the colour means, and HOW MANY are plotted -- on one row
    (plan SS3 VC item 2). The first two return the producer's own vocabulary
    (`compare_data.FRONTIER_POOLS`, `charts_compare.COLOR_BY`), never a label;
    the third is the pre-existing 2B-R2-10 "Topics plotted" slider, unchanged
    in range and default, only repositioned onto this same row. It has NOTHING
    to do with the separate shared-frontier top-N below (`_shared_frontier_top_n`)."""
    cols = st.columns([2, 2, 2])
    pools = list(K.FRONTIER_POOLS)
    with cols[0]:
        pool = st.radio(copy.COMPARE["FRONTIER_POOL_LABEL"], pools,
                        format_func=lambda p: POOL_LABELS[p], horizontal=True,
                        help=copy.COMPARE["FRONTIER_POOL_HELP"], key="cmp_frontier_pool",
                        **state.PERSIST)
    modes = list(X.COLOR_BY)
    with cols[1]:
        color_by = st.radio(copy.COMPARE["FRONTIER_COLOR_LABEL"], modes,
                            format_func=lambda c: COLOR_BY_LABELS[c], horizontal=True,
                            help=copy.COMPARE["FRONTIER_COLOR_HELP"], key="cmp_frontier_color",
                            **state.PERSIST)
    with cols[2]:
        top_n = st.slider(copy.COMPARE["FRONTIER_TOPN_LABEL"], FRONTIER_TOPN_MIN,
                          FRONTIER_TOPN_MAX, FRONTIER_TOPN_DEFAULT, FRONTIER_TOPN_STEP,
                          help=copy.COMPARE["FRONTIER_TOPN_HELP"], key="cmp_frontier_topn",
                          **state.PERSIST)
    return str(pool), str(color_by), int(top_n)


def _domain_items(pooled: pd.DataFrame) -> list:
    """`[(domain_id, name)]` for the domains actually plotted, in the palette's
    own domain order -- the legend the colour-by-domain mode needs. The WORDS
    come from the engine's domain map (the same `bundle["domain_names"]` the
    Find page's yearly breakdown reads), the HUES from `palette.domain_color`
    inside `charts_compare.map_legend_strip`: this page names neither."""
    if pooled.empty or "domain_id" not in pooled.columns:
        return []
    names = _bundle()["domain_names"]
    present = {int(d) for d in pd.to_numeric(pooled["domain_id"], errors="coerce").dropna()}
    ordered = [d for d in P.OA_DOMAIN_ORDER if d in present]
    ordered += sorted(d for d in present if d not in set(P.OA_DOMAIN_ORDER))
    return [(d, str(names.get(d, d))) for d in ordered]


def _shared_frontier_top_n(total: int) -> int | None:
    """2BR3 plan item 4: the shared-frontier chart's OWN top-N rule, decoupled
    from the pooled map's "Topics plotted" slider above it. Default is the
    twenty topics with the largest COMBINED volume (`fig_diverging_shared`
    ranks on `value_col` summed across institutions, PAL's own contract); a
    button -- never a slider -- swaps in the rest. `total <=
    SHARED_FRONTIER_TOP_N` needs no button at all: showing all of them IS
    showing the top N."""
    # 2C manager fix (VC blocker, root cause): the old body flipped session
    # state inside the click run and called st.rerun() -- and that explicit
    # rerun left every st.download_button on the page broken for the REST of
    # the browser session (reproduced in isolation; the long-disclosed
    # "workbook-download smoke timeout" was this bug's shadow). An on_click
    # callback runs BEFORE the script body of the rerun the click itself
    # triggers, so the state is already flipped when this function reads it:
    # same one-click behaviour, no st.rerun() anywhere on the page.
    key = "cmp_shared_frontier_all"
    if total <= SHARED_FRONTIER_TOP_N:
        return None
    show_all = bool(st.session_state.get(key, False))

    def _toggle() -> None:
        st.session_state[key] = not bool(st.session_state.get(key, False))

    label = (copy.COMPARE["SHARED_FRONTIER_SHOW_TOP"].format(n=SHARED_FRONTIER_TOP_N)
             if show_all else
             copy.COMPARE["SHARED_FRONTIER_SHOW_ALL"].format(n=f"{total:,}"))
    st.button(label, key="cmp_shared_frontier_toggle", on_click=_toggle)
    return None if show_all else SHARED_FRONTIER_TOP_N


def _view_frontier(ids, slots, names, sc) -> tuple:
    """2B-R-9's two charts. The map pools the compared institutions' eligible
    frontier topics into ONE plane -- one bubble per topic, so the same topic
    can never be drawn twice in two colours -- and the diverging list answers
    the question the map's near-degenerate head cannot: who actually holds the
    topics they share. 2BR3 moves the pooled map's THREE controls onto one row
    (`_frontier_controls`) and gives the shared list its OWN top-twenty/"show
    all" control (`_shared_frontier_top_n`), independent of the map's slider."""
    st.subheader(copy.COMPARE["VIEW_FRONTIER_MAP"])
    pool, color_by, top_n = _frontier_controls()
    pooled = _frontier_pooled(tuple(ids), sc["tree"], sc["basis"], top_n, pool)
    if pooled.empty:
        st.caption(copy.COMPARE["EMPTY_FRONTIER_POINTS"])
        return pooled, pd.DataFrame(), pool, color_by, top_n
    items = _domain_items(pooled)
    st.markdown(X.map_legend_strip(_slot_order(ids, slots), slots=slots, names=names,
                                   color_by=color_by, shared=True,
                                   shared_label=copy.COMPARE["LEGEND_SHARED"],
                                   domain_items=items),
                unsafe_allow_html=True)
    st.plotly_chart(
        X.fig_frontier_map(pooled, slots=slots, names=names,
                           pool=POOL_CHART_MODE[pool], color_by=color_by,
                           domain_labels=dict(items)),
        width="stretch", key="fig_cmp_frontier_map")
    # The shared count is READ OFF the plotted frame, never asserted in prose:
    # on a realistic trio nearly every head topic is shared, so the picture's
    # colour split is degenerate and the reading line is the only honest place
    # to say it. The POOL RULE is stated in the tooltip in the same plain words
    # the selector uses (2B-R2-10).
    n_shared = int((pooled["owner"] == X.SHARED_OWNER).sum())
    _note(copy.COMPARE["NOTE_FRONTIER_MAP"].format(
        n_shared=f"{n_shared:,}", n_shown=f"{len(pooled):,}"),
        copy.COMPARE["TIP_FRONTIER_MAP"].format(pool_rule=POOL_RULES[pool],
                                                basis=copy.BASIS_LABELS[sc["basis"]]))
    _download(pooled, slug=SLUGS["frontier_map"], sc=sc, key="frontier_map")

    st.subheader(copy.COMPARE["VIEW_SHARED_FRONTIER"])
    shared_long = _shared_long(_shared_frontier(tuple(ids), sc["tree"], sc["basis"], pool),
                               _slot_order(ids, slots))
    if shared_long.empty:
        st.caption(copy.COMPARE["EMPTY_SHARED_FRONTIER"])
        return pooled, shared_long, pool, color_by, top_n
    total_shared = int(shared_long["topic_id"].nunique())
    shared_top_n = _shared_frontier_top_n(total_shared)
    _legend(ids, slots, names)
    st.plotly_chart(
        X.fig_diverging_shared(shared_long, _slot_order(ids, slots), slots=slots,
                               names=names, value_col="vol", top_n=shared_top_n),
        width="stretch", key="fig_cmp_shared_frontier")
    _note(copy.COMPARE["NOTE_SHARED_FRONTIER"].format(n=f"{total_shared:,}"),
        copy.COMPARE["TIP_SHARED_FRONTIER"].format(basis=copy.BASIS_LABELS[sc["basis"]]))
    _download(shared_long, slug=SLUGS["shared_frontier"], sc=sc, key="shared_frontier")
    return pooled, shared_long, pool, color_by, top_n


# --------------------------------------------------------------- the impact --

def _impact_rows(union: pd.DataFrame, top: pd.DataFrame) -> pd.DataFrame:
    """The union can hold two hundred subfields; a dot-interval row per subfield
    per institution would run to a page of scrolling nobody reads. The cut is
    the subfields the compared set publishes most in, and the caption states how
    many of the union that leaves."""
    keep = [s for s in top["subfield_id"] if s in set(union["subfield_id"])]
    if keep:
        return union[union["subfield_id"].isin(keep)]
    order = (union.groupby("subfield_id")["n_works_full"].max()
                  .sort_values(ascending=False).head(IMPACT_ROWS_TOP_N).index)
    return union[union["subfield_id"].isin(list(order))]


def _view_impact(ids, slots, names, sc) -> tuple:
    """2BR3 keeps this section's shape (index intervals, then a subfield cut
    with its own floor toggle) and rewrites only the subfield reading line:
    plan item 3 replaces "showing the {n} of {n_union} subfields this set
    publishes most in" (a count with no rule behind it) with the SELECTION
    RULE in plain words -- `compare_data.impact_subfields`'s own floor-
    clearing union -- alongside the same count."""
    st.subheader(copy.COMPARE["VIEW_IMPACT"])
    st.markdown(f"**{copy.COMPARE['IMPACT_INDEX_HEADER']}**")
    index_df = _impact_index(tuple(ids))
    if index_df.empty:
        st.caption(copy.FIND["PANEL_EMPTY"])
    else:
        _legend(ids, slots, names)
        st.plotly_chart(X.fig_impact_intervals(index_df, slots, names=names),
                        width="stretch", key="fig_cmp_impact")
    _note(copy.COMPARE["NOTE_IMPACT"],
          copy.COMPARE["TIP_IMPACT"].format(y0=WINDOW_START, y1=WINDOW_END,
                                            bonus_year=CFG["bonus_year"],
                                            ci=_ci_sentence()))
    _download(index_df, slug=SLUGS["impact"], sc=sc, key="impact")

    st.markdown(f"**{copy.COMPARE['IMPACT_SUBFIELD_HEADER']}**")
    floor = st.radio(copy.COMPARE["IMPACT_FLOOR_LABEL"], IMPACT_FLOORS,
                     index=IMPACT_FLOORS.index(IMPACT_FLOOR_DEFAULT), horizontal=True,
                     format_func=lambda f: copy.COMPARE["IMPACT_FLOOR_OPTION"].format(floor=f),
                     help=copy.COMPARE["IMPACT_FLOOR_HELP"], key="cmp_impact_floor",
                     **state.PERSIST)
    union = _impact_subfields(tuple(ids), sc["tree"], int(floor))
    if union.empty:
        st.caption(copy.COMPARE["EMPTY_IMPACT_FLOOR"])
        return index_df, union
    top = _top_shared(tuple(ids), sc["tree"], sc["basis"], IMPACT_ROWS_TOP_N)
    shown = _impact_rows(union, top)
    _legend(ids, slots, names)
    st.plotly_chart(X.fig_impact_subfields(shown, slots, names=names),
                    width="stretch", key="fig_cmp_impact_subfields")
    _note(copy.COMPARE["NOTE_IMPACT_SUBFIELDS"].format(
        floor=int(floor), n=f"{shown['subfield_id'].nunique():,}",
        n_union=f"{union['subfield_id'].nunique():,}"),
        copy.COMPARE["TIP_IMPACT_SUBFIELDS"].format(ci=_ci_sentence()))
    _download(union, slug=SLUGS["impact_subfields"], sc=sc, key="impact_subfields")
    return index_df, union


# ------------------------------------------------------------- the coverage --

def _state_labels() -> dict:
    """The six exclusive states, in the page's own words."""
    return {"classified_eligible": copy.COMPARE["STATE_CLASSIFIED"],
            "title_only": copy.COMPARE["STATE_TITLE_ONLY"],
            "lang_uncertain": copy.COMPARE["STATE_LANG_UNCERTAIN"],
            "untranslated_grey": copy.COMPARE["STATE_UNTRANSLATED"],
            "unusable": copy.COMPARE["STATE_UNUSABLE"],
            "retracted_excluded": copy.COMPARE["STATE_RETRACTED"]}


def _view_coverage(ids, slots, names, sc) -> pd.DataFrame:
    """2BR3 plan item 1/3: MOVED UP, directly after the KPI cards -- "top
    generic info first", and the classified share this section states is what
    the Subject/ERC/SDG sections below rest their own denominators on."""
    st.subheader(copy.COMPARE["VIEW_COVERAGE"])
    df = _coverage(tuple(ids))
    if df.empty:
        st.caption(copy.FIND["PANEL_EMPTY"])
        return df
    _legend(ids, slots, names)
    st.plotly_chart(X.fig_coverage_strip(df, slots, names=names, labels=_state_labels()),
                    width="stretch", key="fig_cmp_coverage")
    _note(copy.COMPARE["NOTE_COVERAGE"],
          f"{copy.COMPARE['TIP_COVERAGE']} {copy.COMPARE['STATE_TOTAL_HELP']}")
    _download(df, slug=SLUGS["coverage"], sc=sc, key="coverage")
    return df


# ----------------------------------------------------------------- workbook --

def methods_rows(ctx: dict, ids: list, sc: dict, floor: int, top_n: int,
                 sheets: list, controls: dict | None = None) -> pd.DataFrame:
    """The workbook's Methods sheet: what the file is, and what every other
    sheet counts. Every VALUE comes from CFG, the manifest, `compare_data`'s own
    window constants or the live frames; every LABEL comes from `copy.COMPARE` /
    `copy.METHODS_SOURCES`, so no number is typed here either.

    2B-R re-cut: the snapshot row is GONE (2B-R-12, snapshot string removed
    app-wide) and four rows are new -- the data date, BOTH dynamics windows
    named verbatim (2B-R-6), the comparison cap (2B-R-4) with the frontier
    slider beside it, and the interval coverage sentence (2B-R-12).

    2B-R2-5/10 adds `controls`: the row ORDER, the frontier POOL and the
    frontier COLOUR mode the reader was actually on. A workbook that named the
    metric of each selector but not the pool its frontier sheet was cut from
    would describe a view nobody saw."""
    ctl = {"pool": POOL_DEFAULT, "color_by": COLOR_BY_DEFAULT, "sort": SORT_DEFAULT}
    ctl.update(controls or {})
    mf = manifest()
    words = _scenario_words(sc)
    src = copy.METHODS_SOURCES
    stamp = (mf.get("source_manifest_generated_at") or mf.get("generated_at")
             or mf.get("deployed_at"))
    rows = [
        (copy.COMPARE["XLSX_ROW_DATA"], data_date_label(stamp, NA_MARK), src["snapshot"]),
        (copy.COMPARE["XLSX_ROW_WINDOW"], f"{WINDOW_START}{DASH}{WINDOW_END}", src["y0"]),
        (copy.COMPARE["XLSX_ROW_DYNAMICS"],
         f"{_window(K.DYNAMICS_W1)} {SEP} {_window(K.DYNAMICS_W2)}",
         K.DYNAMICS_DENOM_NOTE),
        (copy.COMPARE["XLSX_ROW_TREE"], words["tree"], copy.COMPARE["XLSX_SOURCE_PAGE"]),
        (copy.COMPARE["XLSX_ROW_BASIS"], words["basis"], copy.COMPARE["XLSX_SOURCE_PAGE"]),
        (copy.COMPARE["XLSX_ROW_INSTITUTIONS"],
         "; ".join(_name(ctx, i) for i in ids), copy.COMPARE["XLSX_SOURCE_PAGE"]),
        (copy.COMPARE["XLSX_ROW_CAP"], f"{state.COMPARE_CAP:,}",
         copy.COMPARE["XLSX_SOURCE_PAGE"]),
        (copy.COMPARE["XLSX_ROW_TOPN"], f"{top_n:,}", copy.COMPARE["XLSX_SOURCE_PAGE"]),
        (copy.COMPARE["XLSX_ROW_POOL"], POOL_LABELS[ctl["pool"]],
         POOL_RULES[ctl["pool"]]),
        (copy.COMPARE["XLSX_ROW_COLOUR"], COLOR_BY_LABELS[ctl["color_by"]],
         copy.COMPARE["FRONTIER_COLOR_HELP"]),
        (copy.COMPARE["XLSX_ROW_SORT"], SORT_LABELS[ctl["sort"]],
         copy.COMPARE["SORT_HELP"]),
        (copy.COMPARE["XLSX_ROW_FLOORS"],
         copy.COMPARE["IMPACT_FLOOR_OPTION"].format(floor=floor), src["floor_solid"]),
        (copy.COMPARE["XLSX_ROW_FLOORS"],
         copy.FIND["CAPTION_SI_FLOOR"].format(floor_solid=int(profile_data.SI_FLOOR_SOLID),
                                              floor_thin=int(profile_data.SI_FLOOR_THIN)),
         src["floor_thin"]),
        (copy.COMPARE["XLSX_ROW_CI"], _ci_sentence(), src["n_bootstrap"]),
        (copy.COMPARE["XLSX_ROW_FILTERS"], NA_MARK, copy.COMPARE["XLSX_SOURCE_PAGE"]),
        (copy.COMPARE["XLSX_ROW_READING"], copy.VERDICT_LINE,
         copy.COMPARE["XLSX_SOURCE_PAGE"]),
        (copy.COMPARE["XLSX_ROW_SHEETS"], "", ""),
    ]
    rows += [(label, caption, copy.COMPARE["XLSX_ROW_DENOMINATORS"])
             for label, caption, _frame in sheets]
    return pd.DataFrame(rows, columns=[copy.COMPARE["XLSX_COL_ITEM"],
                                       copy.COMPARE["XLSX_COL_VALUE"],
                                       copy.COMPARE["XLSX_COL_SOURCE"]])


def sheet_specs(sc: dict, frames: dict, metrics: dict) -> list:
    """`[(sheet label, what that sheet counts, frame)]`, in PAGE order -- one
    sheet per view the page actually drew, with the METRIC each selector was on
    named in the caption, so a workbook cannot claim a view the reader did not
    see. 2BR3: Coverage moves up (it now sits right after Overview on the
    page) and Trends is gone."""
    C = copy.COMPARE
    words = _scenario_words(sc)
    subject_label = C["XLSX_SHEET_SUBJECT_FIELD"] if metrics["level"] == "field" \
        else C["XLSX_SHEET_SUBJECT_SUBFIELD"]
    return [
        (C["XLSX_SHEET_OVERVIEW"], C["OVERVIEW_WINDOW"].format(y0=WINDOW_START, y1=WINDOW_END),
         frames["overview"]),
        (C["VIEW_COVERAGE"], C["CAPTION_COVERAGE"], frames["coverage"]),
        (subject_label,
         C["XLSX_CAPTION_METRIC"].format(metric=METRIC_LABELS[metrics["subject"]],
                                         **words),
         frames["subject"]),
        (C["VIEW_ERC"], C["XLSX_CAPTION_METRIC"].format(
            metric=METRIC_LABELS[metrics["erc"]], **words), frames["erc"]),
        (C["VIEW_SDG"], C["XLSX_CAPTION_METRIC"].format(
            metric=METRIC_LABELS[metrics["sdg"]], **words), frames["sdg"]),
        (C["VIEW_FRONTIER_MAP"], C["CAPTION_FRONTIER_MAP"].format(
            basis=copy.BASIS_LABELS[sc["basis"]]), frames["frontier_map"]),
        (C["VIEW_SHARED_FRONTIER"], C["CAPTION_SHARED_FRONTIER"].format(
            basis=copy.BASIS_LABELS[sc["basis"]]), frames["shared_frontier"]),
        (C["XLSX_SHEET_IMPACT_INDEX"], C["CAPTION_IMPACT"].format(y0=WINDOW_START, y1=WINDOW_END),
         frames["impact"]),
        (C["XLSX_SHEET_IMPACT_SUBFIELDS"], C["IMPACT_UNION_CAPTION"], frames["impact_subfields"]),
    ]


def _workbook(ctx: dict, ids: list, sc: dict, floor: int, top_n: int, sheets: list,
              controls: dict | None = None) -> bytes:
    ordered = [(copy.COMPARE["XLSX_SHEET_METHODS"],
                methods_rows(ctx, ids, sc, floor, top_n, sheets, controls))]
    ordered += [(label, frame) for label, _caption, frame in sheets]
    return workbook_bytes(ordered)


def _exports(ctx: dict, ids: list, sc: dict, floor: int, top_n: int, sheets: list,
             controls: dict | None = None) -> None:
    """ONE workbook (2B-13) beside the per-view CSVs. `data` is a callable, so
    the sheets are only written when someone clicks."""
    st.download_button(copy.COMPARE["EXPORT_XLSX_BUTTON"],
                       lambda: _workbook(ctx, ids, sc, floor, top_n, sheets, controls),
                       file_name=workbook_filename(ids, sc["tree"], sc["basis"]),
                       mime=XLSX_MIME, help=copy.COMPARE["EXPORT_XLSX_HELP"],
                       key="dl_workbook")


# --------------------------------------------------------- bottom meta block --

def _footer(bundle: dict, ctx: dict, ids: list, sc: dict, floor: int, top_n: int,
           sheets: list, controls: dict) -> None:
    """2BR3 VC item 1: everything that used to sit BETWEEN the title and the
    first chart now lives HERE, at the foot of the page: the index-size and
    data-date line and this page's own method sentence, inside one
    collapsible ("About these figures", plan SS3 VC) so a reader opens it on
    purpose; the export workbook and per-view CSVs (unchanged, 2B-13); and the
    shareable link (`links.share_link_block`, SEL's factored-out component,
    plan item 7) naming exactly the institutions in the three slots above."""
    st.divider()
    with st.expander(copy.COMPARE["ABOUT_HEADER"]):
        st.caption(copy.COMPARE["PAGE_INTRO"])
        mf = manifest()
        stamp = (mf.get("source_manifest_generated_at") or mf.get("generated_at")
                 or mf.get("deployed_at"))
        st.caption(copy.FIND["DATA_CAPTION"].format(
            n_institutions=f"{len(bundle['index_df']):,}", sep=SEP,
            date=data_date_label(stamp, NA_MARK)))
    _exports(ctx, ids, sc, floor, top_n, sheets, controls)
    selection.share_link_block("compare", ids, caption=copy.COMPARE["DEEPLINK_LABEL"])


# ------------------------------------------------------------------ render --

def render() -> None:
    """The whole Compare page (2BR3 VC rework, plan SS1.5/SS3 VC). Order:
    sidebar scenario + the shared search/basket -> title + one promise line ->
    the three slots (`selection.slots_row`) -> substrates behind the A10
    spinner -> overview cards -> Coverage -> the three "Compare by" sections
    (subject, ERC, SDG) -> the two frontier charts -> impact -> the bottom
    meta block (exports, "About these figures", the share link)."""
    bundle = _bundle()
    scenario = _sidebar_scenario()
    selection.render_sidebar()
    _header()
    slot_picks = selection.slots_row("compare", state.COMPARE_CAP)
    ids = [i for i in slot_picks if i]
    if len(ids) < 2:
        return
    # A10: a tree/basis flip pays `build_substrates` ONCE (measured 4.6 s,
    # cached); every other rerun finds it warm.
    with st.spinner(copy.COMPARE["SPINNER_SCENARIO"]):
        _subs(scenario["tree"], scenario["basis"])
    ctx = bundle["ctx"]
    slots = _slots(ctx, ids)
    names = _names(ctx, ids)

    frames = {"overview": _view_overview(ctx, ids, slots)}
    frames["coverage"] = _view_coverage(ids, slots, names, scenario)

    subject, level, subject_metric = _view_subject(ids, slots, names, scenario)
    frames["subject"] = subject
    frames["erc"], erc_metric = _view_erc(ctx, ids, slots, names, scenario)
    frames["sdg"], sdg_metric = _view_sdg(ctx, ids, slots, names, scenario)

    frames["frontier_map"], frames["shared_frontier"], pool, color_by, top_n = \
        _view_frontier(ids, slots, names, scenario)
    frames["impact"], frames["impact_subfields"] = _view_impact(ids, slots, names, scenario)

    metrics = {"level": level, "subject": subject_metric, "erc": erc_metric,
               "sdg": sdg_metric}
    sheets = sheet_specs(scenario, frames, metrics)
    floor = int(st.session_state.get("cmp_impact_floor") or IMPACT_FLOOR_DEFAULT)
    controls = {"pool": pool, "color_by": color_by,
                "sort": _current_sort("cmp_sort_subject")}
    _footer(bundle, ctx, ids, scenario, floor, top_n, sheets, controls)

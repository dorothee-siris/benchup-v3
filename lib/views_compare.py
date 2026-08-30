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
cross-institution occlusion is impossible rather than merely reduced), and
every sort toggle (2B-R-5: the frame arrives ranked, the builder never
re-sorts, so no control can move a colour).

COMPOSITION ONLY, the same rule as lib/views_find.py: every frame comes from
`lib/compare_data.py`, every figure from `lib/charts_compare.py`, every colour
from `lib/palette.py`, every id rule from `lib/selection.py`, every URL from
`lib/links.py`, every string from `lib/copy.py`. Nothing here recomputes an
indicator and nothing here types a number into a rendered string
(BUILD_PLAN_2A.md L10, scanned by tests/test_narrative.py). The two reshapes
this file does own -- ranking a metric frame's rows and melting the wide
shared-frontier frame into the long shape every builder takes -- move no
value and invent none.

PAGE ORDER
  sidebar: counting & taxonomy (the SAME `tree` / `basis` widget keys Find and
  Collaborate use) + the basket, read-only, with a link back to Find
  main: title + lead + verdict + data line -> selection (add by name, the cap
  line, the shareable deep link) -> OVERVIEW cards, one per institution, the
  2B-R-7 KPI set with the interval's own coverage stated beside it -> subject
  profile (the metric selector, fields with a subfield drill) -> ERC panels ->
  SDG goals -> the two frontier charts -> impact (whole output, then by
  subfield, with the floor toggle) -> trends -> coverage -> the workbook -> the
  pair hand-off to Collaborate.

WHY THE COLOUR IS THE INSTITUTION (2B-1, narrowed once by 2B-R-8)
  Colour on a MARK is the institution and nothing else. A taxonomy's official
  hue may appear as a GLYPH in a row LABEL (ERC domains, UN goals) and never
  the other way round -- `charts_compare` routes that through
  `palette.label_accent_color`, and this file only supplies the accent KEY.
  Slots come from `palette.institution_slots`, by ascending `inst_key`, so
  removing an institution never repaints the survivors.

LEGEND ABOVE EVERY CHART (2B-R-12)
  `charts_compare.legend_strip` is rendered immediately above each figure, not
  once per page: the page scrolls through nine of them, and a legend the reader
  has scrolled past is not a legend. It is also the secondary encoding the
  palette validator's warnings oblige.

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
from lib import copy, countries, links, profile_data, selection, state
from lib import palette as P
from lib.app_config import CFG
from lib.data_cache import manifest
from lib.exports import data_date_label
from lib.exports_xlsx import XLSX_MIME, workbook_bytes, workbook_filename
from lib.palette import NA_MARK
from lib.search import search
from lib.views_find import (
    DASH, SEP, _bundle, _hit_label, _count, _pct, _sidebar_scenario, _subs, _vol_col,
)

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
}
# Every section starts from the SAME six-metric vocabulary and lets the level
# filter it (2B-R-5). Starting each section from a hand-written short list would
# hide the ERC and SDG gaps instead of disclosing them: as shipped, ERC serves
# Share and Specialisation, SDG serves Share and Dynamics, and each section
# prints `compare_data`'s own reason for every measure it cannot offer -- which
# is how a reader learns that "Volume of top-decile publications" is missing
# because no impact artefact crosses with the ERC panels, not because this page
# decided against it.
SUBJECT_METRICS = tuple(METRIC_LABELS)
ERC_METRICS = SUBJECT_METRICS
SDG_METRICS = SUBJECT_METRICS

# The accent KEY column each level's builder call needs (2B-R-8). `metric_frame`
# returns the six contract columns only, so the key is merged back on from the
# taxonomy's own long frame -- a join, not a recomputation.
ACCENT_KEY = {"erc": "erc_domain", "sdg": "sdg_number"}

# 2B-R-9 / A/B #8: the frontier slider. The default is VS's MEASURED value --
# bubble occlusion on the real trio is 0.450 at N = 40 and N = 60, 0.588 at
# N = 80, 0.708 at N = 120 -- i.e. sixty bubbles is the largest set that costs
# nothing in occlusion.
FRONTIER_TOPN_DEFAULT = 60
FRONTIER_TOPN_MIN = 20
FRONTIER_TOPN_MAX = 120
FRONTIER_TOPN_STEP = 20

# 2B-5 fixes the trends grid at six subfields; A3 fixes HOW the six are chosen
# -- the largest SUMMED share across the compared set, never the intersection of
# per-institution top lists, which collapses to one subfield.
TRENDS_TOP_N = 6

# The subfields the impact panel draws out of the union it is handed (A1).
IMPACT_ROWS_TOP_N = 20

# The impact floors the artefact ships (data_contract.yaml: impact_cells carries
# floor in {10, 30}); the higher one is the default and the lower one is the
# labelled "more cells, wider intervals" variant (A1).
IMPACT_FLOORS = tuple(sorted(K.IMPACT_CELL_FLOORS, reverse=True))
IMPACT_FLOOR_DEFAULT = IMPACT_FLOORS[0]

# `?compare=` seeds the basket ONCE per session and then gets out of the way: a
# link that kept winning would resurrect an institution the reader had just
# removed. After the seed the basket is the single source of truth (2B-8).
SEEDED_KEY = "compare_seeded"

FIND_PAGE = "pages/1_\U0001F50E_Find.py"
# `st.page_link` cannot carry a query string, so the SHAREABLE half of the
# hand-off is still a printed deep link (`selection.deeplink`); `COLLAB_PAGE`
# is the file path `st.switch_page` needs to hop IN-SESSION, which is what
# keeps the basket and the tree/basis scenario alive.
COLLAB_PAGE = "pages/3_\U0001F91D_Collaborate.py"

# CSV file-name slugs. Code identifiers, never rendered copy -- the visible
# labels are `copy.COMPARE["VIEW_*"]`.
SLUGS = {"overview": "overview", "subject": "subject", "erc": "erc", "sdg": "sdg",
         "frontier_map": "frontier_map", "shared_frontier": "shared_frontier",
         "impact": "impact", "impact_subfields": "impact_subfields",
         "trends": "trends", "coverage": "coverage"}

# The institution-normalised trends measure (V's needs_change 5): a subfield's
# share of that institution's OWN publications for the year.
TRENDS_VALUE_COL = "share_of_year"

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
def _frontier_pooled(ids: tuple, tree: str, basis: str, top_n: int) -> pd.DataFrame:
    return K.frontier_pooled(_bundle()["ctx"], _subs(tree, basis), list(ids), top_n)


@st.cache_data(show_spinner=False, max_entries=12)
def _shared_frontier(ids: tuple, tree: str, basis: str) -> pd.DataFrame:
    return K.shared_frontier(_bundle()["ctx"], _subs(tree, basis), list(ids))


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


@st.cache_data(show_spinner=False, max_entries=48)
def _trends(iid: str, tree: str, basis: str) -> pd.DataFrame:
    """One institution's per-year subfield volumes, PLUS the normalised measure
    the shared-scale grid needs: the subfield's share of that institution's own
    publications for that year, on the active basis."""
    df = K.trends_subfields(_bundle()["ctx"], iid, tree).copy()
    vol = _vol_col(basis)
    totals = df.groupby("year")[vol].transform("sum")
    df[TRENDS_VALUE_COL] = pd.to_numeric(df[vol], errors="coerce").div(totals).fillna(0.0)
    return df


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
    """`{institution_id: slot}` from the identity family, by ascending
    `inst_key` (A8) -- never by the order the basket happens to hold."""
    return P.institution_slots({iid: ctx["index_by_id"].loc[iid, "inst_key"] for iid in ids})


def _slot_order(ids, slots: dict) -> list:
    """The ids in the order every figure and the legend draw them."""
    return sorted(ids, key=lambda i: (slots.get(i, len(slots)), str(i)))


def _legend(ids, slots: dict, names: dict, *, shared: bool = False) -> None:
    """2B-R-12: the one key every figure needs, immediately above THAT figure."""
    st.markdown(X.legend_strip(_slot_order(ids, slots), slots=slots, names=names,
                               shared=shared, shared_label=copy.COMPARE["LEGEND_SHARED"]),
                unsafe_allow_html=True)


def _interval(low, high) -> str:
    if low is None or high is None or pd.isna(low) or pd.isna(high):
        return NA_MARK
    return copy.FIND["KPI_PP_VALUE_CI"].format(lo=_pct(low), hi=_pct(high), dash=DASH)


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


# ----------------------------------------------------------------- sidebar --

def _sidebar_basket(bundle: dict) -> None:
    """READ-ONLY here: this page edits the basket through the overview cards,
    where the reader is looking, and the sidebar only reports the count against
    the basket cap and links back to Find."""
    sb, names = st.sidebar, bundle["ctx"]["index_by_id"]
    sb.header(copy.FIND["BASKET_HEADER"])
    items = state.items()
    sb.caption(copy.FIND["BASKET_COUNT"].format(n=len(items), cap=state.BASKET_CAP))
    if not items:
        sb.caption(copy.FIND["BASKET_EMPTY"])
    for iid in items:
        sb.write(str(names.loc[iid, "display_name"]))
    # The multi-page registry only exists when the app is entered through
    # Menu.py; running this page alone (AppTest, the probe) makes `page_link`
    # raise on Streamlit's own page table, so the link degrades to its label
    # rather than taking the page down.
    try:
        sb.page_link(FIND_PAGE, label=copy.NAV["FIND_LABEL"])
    except Exception:
        sb.caption(copy.NAV["FIND_LABEL"])


# ------------------------------------------------------------------ header --

def _header(bundle: dict) -> None:
    """2B-R-12: no snapshot stamp anywhere. What stays is the two facts a
    reader uses -- how big the index is and how old the data is -- both
    computed, never typed (the same `exports.data_date_label` the Find page and
    the menu read)."""
    st.title(copy.NAV["COMPARE_LABEL"])
    st.subheader(copy.NAV["COMPARE_LEAD"])
    st.caption(copy.COMPARE["PAGE_INTRO"])
    st.markdown(f"**{copy.VERDICT_LINE}**")
    mf = manifest()
    stamp = (mf.get("source_manifest_generated_at") or mf.get("generated_at")
             or mf.get("deployed_at"))
    st.caption(copy.FIND["DATA_CAPTION"].format(
        n_institutions=f"{len(bundle['index_df']):,}", sep=SEP,
        date=data_date_label(stamp, NA_MARK)))


# --------------------------------------------------------------- selection --

def _add_by_name(bundle: dict) -> None:
    """Find's own search idiom: a free-text box, a selectbox over the hits, and
    an add button. `state.add` returns False only when the BASKET cap is
    reached and nothing changed, so the page is not rerun in that case and the
    cap message renders on this same run."""
    query = st.text_input(copy.COMPARE["ADD_LABEL"], key="compare_query", **state.PERSIST)
    hits = search(query, bundle["search_idx"]) if query else []
    if query and not hits:
        st.caption(copy.SEARCH_EMPTY_TEMPLATE.format(query=query))
    if not hits:
        return
    pick = st.selectbox(copy.COMPARE["ADD_PICK"], [h["id"] for h in hits],
                        format_func=lambda i: _hit_label(hits, i), key="compare_pick")
    if st.button(copy.COMPARE["ADD_BUTTON"], key="compare_add") and pick:
        if state.add(pick):
            st.rerun()
        else:
            st.warning(copy.COMPARE["CAP_REACHED"].format(cap=state.BASKET_CAP))


def seed_from_query(bundle: dict) -> None:
    """`?compare=` -> the basket, ONCE per session, BEFORE anything is drawn.

    The link may name more institutions than Compare shows (2B-R-4 caps the
    COMPARISON at three; the basket is a six-slot shortlist). Seeding the
    BASKET at the basket's own cap and truncating at the comparison's cap
    downstream is what lets the page say, in `_selection`, exactly how many it
    left out -- a link that silently dropped ids at parse time could not."""
    if st.session_state.get(SEEDED_KEY):
        return
    st.session_state[SEEDED_KEY] = True
    known = bundle["ctx"]["id_pos"]
    query = selection.read_query(known)["compare"]
    if not query:
        return
    ids = selection.compare_ids(state.items(), query, known, state.BASKET_CAP)
    for iid in ids:
        state.add(iid)
    state.reorder(ids)


def _selection(bundle: dict) -> list:
    """The compared set, and the controls that change it. Returns the ids in
    the reader's own basket order, truncated at `state.COMPARE_CAP` (2B-R-4)
    with the truncation DISCLOSED rather than performed silently."""
    known = bundle["ctx"]["id_pos"]
    st.subheader(copy.COMPARE["SELECTION_HEADER"])
    st.caption(copy.COMPARE["SELECTION_HELP"])
    _add_by_name(bundle)
    ids, n_dropped = selection.compare_ids_capped(state.items(), [], known, state.COMPARE_CAP)
    st.caption(copy.COMPARE["CAP_HELP"].format(cap=state.COMPARE_CAP))
    if n_dropped:
        st.warning(copy.COMPARE["CAP_TRUNCATED"].format(cap=state.COMPARE_CAP, n=n_dropped))
    st.caption(copy.COMPARE["DEEPLINK_LABEL"])
    st.code(selection.deeplink("compare", ids), language=None)
    return ids


# ---------------------------------------------------- overview (VIZ 4.1) ----

def _card_facts(row, cell) -> list:
    """`[(label, value, help, subline)]` for ONE institution's card, in the
    2B-R-7 order. Every value arrives from `compare_data.overview`; a null
    source cell renders `n/a`, never zero."""
    words = {"y0": WINDOW_START, "y1": WINDOW_END, "bonus_year": CFG["bonus_year"]}
    return [
        (copy.FIND["KPI_PUBS_LABEL"], _count(cell["vol_full"]),
         copy.FIND["KPI_PUBS_HELP"].format(**words),
         f"{_count(cell['vol_frac'])} {copy.FIND['KPI_PUBS_FRAC_LABEL']}"),
        (copy.FIND["KPI_SDG_LABEL"], _pct(cell["sdg_share"]), copy.FIND["KPI_SDG_HELP"], None),
        (copy.FIND["KPI_FRONTIER_LABEL"], _pct(cell["frontier_top25_share"]),
         copy.FIND["KPI_FRONTIER_HELP"], None),
        (copy.FIND["KPI_PP_LABEL"], _pct(cell["pp"]), copy.FIND["KPI_PP_HELP"],
         f"{_interval(cell['ci_low'], cell['ci_high'])} "
         f"{copy.FIND['KPI_PP_CI_LABEL']}"),
        (copy.FIND["IDENTITY_INTL_LABEL"], _pct(cell["intl_share"]),
         copy.FIND["IDENTITY_FACTS_HELP"].format(y0=WINDOW_START, y1=WINDOW_END), None),
        (copy.FIND["IDENTITY_COMPANY_LABEL"], _pct(cell["company_share"]),
         copy.FIND["IDENTITY_FACTS_HELP"].format(y0=WINDOW_START, y1=WINDOW_END), None),
    ]


def _view_overview(ctx: dict, ids: list, slots: dict) -> pd.DataFrame:
    """VIZ_SPEC 4.1: not a chart. One card per compared institution, in SLOT
    order, carrying the swatch that binds it to every figure below and the six
    2B-R-7 KPI facts as NUMBERS -- seven measures with no shared unit or range
    is a table's job, and drawing it would produce seven mini-charts competing
    with the metric selector immediately underneath."""
    st.subheader(copy.COMPARE["OVERVIEW_HEADER"])
    st.caption(copy.COMPARE["OVERVIEW_HELP"])
    df = _overview(tuple(ids))
    cells = df.set_index("institution_id")
    order = _slot_order(ids, slots)
    with st.container(key="compare_strip", border=True):
        cols = st.columns(len(order))
        for col, iid in zip(cols, order):
            row = ctx["index_by_id"].loc[iid]
            colour = P.institution_color(slots.get(iid, len(slots)))
            # A coloured GLYPH, not a styled box: a box would need typed pixel
            # lengths inside a rendered string (BUILD_PLAN_2A.md L10). The only
            # interpolated value is the palette's own colour.
            col.markdown(f'<span style="color:{colour}">{SWATCH_MARK}</span> '
                         f"**{_name(ctx, iid)}**", unsafe_allow_html=True)
            col.caption(f"{str(row['type'])} {SEP} "
                        f"{countries.name(str(row['country_code']))}")
            for label, value, help_text, subline in _card_facts(row, cells.loc[iid]):
                col.metric(label, value, help=help_text)
                if subline:
                    col.caption(subline)
            col.link_button(copy.COMPARE["STRIP_LINK_PUBS"], links.works_url(iid),
                            help=copy.FIND["LINK_OPENALEX_HELP"])
            if col.button(copy.COMPARE["REMOVE_BUTTON"], key=f"cmp_rm_{iid}"):
                state.remove(iid)
                st.rerun()
    st.caption(_ci_sentence())
    st.caption(copy.COMPARE["OVERVIEW_WINDOW"].format(y0=WINDOW_START, y1=WINDOW_END))
    if st.button(copy.COMPARE["CLEAR_BUTTON"], key="cmp_clear"):
        state.clear()
        st.rerun()
    _download(df, slug=SLUGS["overview"], sc={"tree": "", "basis": ""}, key="overview")
    return df


# ----------------------------------------- the metric selector (VIZ 4.2-4.5) --

def _metric_selector(key: str, level: str, metrics: tuple) -> str:
    """ONE "Compare by" control per section (2B-R-5). Options the data cannot
    serve at this level are HIDDEN, never offered returning zero, and the
    frame's own reason for each is disclosed under the control -- `compare_data`
    owns both the availability call and the wording.

    The stored choice is clamped BEFORE the widget is built: a level change (the
    field drill) can retire the option a reader last picked, and Streamlit
    raises on a session value that is not in the option list rather than falling
    back."""
    available = [m for m in metrics if K.metric_frame_available(m, level)]
    hidden = [m for m in metrics if m not in available]
    labels = [METRIC_LABELS[m] for m in available]
    if st.session_state.get(key) not in labels:
        st.session_state[key] = labels[0]
    picked = st.radio(copy.COMPARE["METRIC_LABEL"], labels, horizontal=True, key=key,
                      help=copy.COMPARE["METRIC_HELP"], **state.PERSIST)
    if hidden:
        # Plainly on the page, not behind an expander: a disclosure a reader has
        # to open is a disclosure most readers never see, and the missing option
        # is exactly the thing someone comparing two levels will look for. The
        # reason is `compare_data`'s own sentence, so the page cannot invent a
        # softer one.
        st.caption(copy.COMPARE["METRIC_HIDDEN_HEADER"])
        for m in hidden:
            st.caption(copy.COMPARE["METRIC_HIDDEN_LINE"].format(
                metric=METRIC_LABELS[m], reason=K.UNAVAILABLE_REASON[(m, level)]))
    return available[labels.index(picked)]


def _rank_rows(df: pd.DataFrame, *, keep_order: bool) -> pd.DataFrame:
    """The row order the grouped-bar builder will preserve (it never re-sorts,
    2B-R-5). `keep_order=True` leaves the taxonomy's own sequence alone -- ERC
    domains run PE, LS, SH and the SDGs are a numbered list a reader navigates
    by position, so re-ranking them would move goal seven in every comparison.
    Otherwise the taxa are ranked by the value SUMMED over the compared set (the
    A3 ruling: the intersection of per-institution top lists is not a
    comparison), which moves rows and never a colour."""
    if df.empty or keep_order:
        return df
    summed = df.groupby("taxon_id")["value"].sum(min_count=1)
    order = {t: i for i, t in enumerate(summed.sort_values(ascending=False, kind="mergesort").index)}
    out = df.copy()
    out["_rank"] = out["taxon_id"].map(order)
    return out.sort_values(["_rank", "institution_id"], kind="mergesort").drop(
        columns="_rank").reset_index(drop=True)


def _decorate(df: pd.DataFrame, level: str, long: pd.DataFrame, key_col: str,
              label_col: str | None = None) -> pd.DataFrame:
    """Merge the 2B-R-8 accent KEY (and, for the SDGs, the numbered label) back
    onto a metric frame from the taxonomy's own long frame. `metric_frame`
    returns the six contract columns and nothing else, so without this join the
    ERC and SDG row labels would carry no official-colour glyph at all."""
    if df.empty or long.empty:
        return df
    cols = [key_col] + [c for c in (ACCENT_KEY.get(level), label_col) if c]
    lookup = long[cols].drop_duplicates(subset=[key_col])
    out = df.merge(lookup, left_on="taxon_id", right_on=key_col, how="left")
    if label_col:
        out["taxon_label"] = out[label_col].fillna(out["taxon_label"])
    return out.drop(columns=[c for c in (key_col, label_col) if c and c in out.columns])


def _metric_chart(df: pd.DataFrame, metric: str, ids, slots, names, level: str,
                  *, key: str) -> None:
    _legend(ids, slots, names)
    st.plotly_chart(
        X.fig_metric_bars(df, metric, _slot_order(ids, slots), slots=slots, names=names,
                          level=level, accent_col=ACCENT_KEY.get(level),
                          metric_label=METRIC_LABELS[metric]),
        width="stretch", key=key)


def _denominator_caption(df: pd.DataFrame) -> None:
    """The frame states its own denominator (and, for dynamics, both windows
    verbatim per 2B-R-6). Rendering that column is how the caption and the
    numbers stay the same object -- a hand-written caption is a second opinion
    about a denominator this page does not own."""
    if not df.empty and "denominator" in df.columns:
        st.caption(str(df["denominator"].iloc[0]))


def _view_subject(ids, slots, names, sc) -> tuple:
    """2B-R-5: fields by default, a drill into ONE field's subfields, one metric
    selector over both."""
    st.subheader(copy.COMPARE["VIEW_SUBJECT"])
    fields = _fields(tuple(ids), sc["tree"], sc["basis"])
    options = [None] + [int(f) for f in sorted(fields["field_id"].unique())]
    labels = dict(zip(fields["field_id"], fields["field_name"]))
    field_id = st.selectbox(
        copy.COMPARE["DRILL_LABEL"], options,
        format_func=lambda f: copy.COMPARE["DRILL_ALL"] if f is None else str(labels.get(f, f)),
        key="cmp_field_drill", **state.PERSIST)
    level = "field" if field_id is None else "subfield"
    metric = _metric_selector("cmp_metric_subject", level, SUBJECT_METRICS)
    floor = int(st.session_state.get("cmp_impact_floor") or IMPACT_FLOOR_DEFAULT)
    df = _rank_rows(_metric(tuple(ids), sc["tree"], sc["basis"], level, metric,
                            field_id, floor), keep_order=False)
    if df.empty:
        st.caption(copy.COMPARE["EMPTY_METRIC"])
        return df, level, metric
    _metric_chart(df, metric, ids, slots, names, level, key="fig_cmp_subject")
    st.caption(copy.COMPARE["CAPTION_SUBJECT"].format(**_scenario_words(sc)))
    if level == "subfield":
        st.caption(copy.COMPARE["CAPTION_DRILL"].format(field=str(labels.get(field_id, field_id))))
    st.caption(copy.COMPARE["CAPTION_RANKED"])
    _denominator_caption(df)
    if metric == "si":
        st.caption(copy.FIND["CAPTION_SI"])
        st.caption(copy.FIND["CAPTION_SI_FLOOR"].format(
            floor_solid=int(profile_data.SI_FLOOR_SOLID),
            floor_thin=int(profile_data.SI_FLOOR_THIN)))
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


def _view_erc(ctx, ids, slots, names, sc) -> tuple:
    st.subheader(copy.COMPARE["VIEW_ERC"])
    metric = _metric_selector("cmp_metric_erc", "erc", ERC_METRICS)
    df = _rank_rows(_metric(tuple(ids), sc["tree"], sc["basis"], "erc", metric, None,
                            IMPACT_FLOOR_DEFAULT), keep_order=True)
    df = _decorate(df, "erc", _erc(tuple(ids)), "panel_idx")
    if df.empty:
        st.caption(copy.COMPARE["EMPTY_METRIC"])
        return df, metric
    _metric_chart(df, metric, ids, slots, names, "erc", key="fig_cmp_erc")
    st.caption(copy.COMPARE["CAPTION_ERC"])
    st.caption(copy.COMPARE["CAPTION_ACCENT_ERC"])
    st.caption(copy.COMPARE["CAPTION_CLASSIFIED_SHARES"].format(
        shares=_shares_line(ctx, ids, slots, "erc_classified_mass_frac")))
    _denominator_caption(df)
    if sc["basis"] == "full":
        st.caption(copy.FIND["FRACTIONAL_ONLY_PANEL"])
    _download(df, slug=SLUGS["erc"], sc=sc, key="erc")
    return df, metric


def _view_sdg(ctx, ids, slots, names, sc) -> tuple:
    st.subheader(copy.COMPARE["VIEW_SDG"])
    metric = _metric_selector("cmp_metric_sdg", "sdg", SDG_METRICS)
    df = _rank_rows(_metric(tuple(ids), sc["tree"], sc["basis"], "sdg", metric, None,
                            IMPACT_FLOOR_DEFAULT), keep_order=True)
    df = _decorate(df, "sdg", _sdg(tuple(ids)), "sdg_idx", label_col="sdg_label_numbered")
    if df.empty:
        st.caption(copy.COMPARE["EMPTY_METRIC"])
        return df, metric
    _metric_chart(df, metric, ids, slots, names, "sdg", key="fig_cmp_sdg")
    st.caption(copy.COMPARE["CAPTION_SDG"])
    st.caption(copy.COMPARE["CAPTION_ACCENT_SDG"])
    st.caption(copy.COMPARE["CAPTION_CLASSIFIED_SHARES"].format(
        shares=_shares_line(ctx, ids, slots, "sdg_classified_mass_frac")))
    _denominator_caption(df)
    if sc["basis"] == "full":
        st.caption(copy.FIND["FRACTIONAL_ONLY_PANEL"])
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


def _view_frontier(ids, slots, names, sc, top_n: int) -> tuple:
    """2B-R-9's two charts. The map pools the compared institutions' top-quartile
    frontier topics into ONE plane -- one bubble per topic, so the same topic
    can never be drawn twice in two colours -- and the diverging list answers
    the question the map's near-degenerate head cannot: who actually holds the
    topics they share."""
    st.subheader(copy.COMPARE["VIEW_FRONTIER_MAP"])
    pooled = _frontier_pooled(tuple(ids), sc["tree"], sc["basis"], top_n)
    if pooled.empty:
        st.caption(copy.COMPARE["EMPTY_FRONTIER_POINTS"])
        return pooled, pd.DataFrame()
    _legend(ids, slots, names, shared=True)
    st.plotly_chart(X.fig_frontier_map(pooled, slots=slots, names=names),
                    width="stretch", key="fig_cmp_frontier_map")
    st.caption(copy.COMPARE["CAPTION_FRONTIER_MAP"].format(
        basis=copy.BASIS_LABELS[sc["basis"]]))
    # The shared count is READ OFF the plotted frame, never asserted in prose:
    # on a realistic trio nearly every head topic is shared, so the picture's
    # colour split is degenerate and the caption is the only honest place to
    # say it.
    n_shared = int((pooled["owner"] == X.SHARED_OWNER).sum())
    st.caption(copy.COMPARE["CAPTION_FRONTIER_SHARED_COUNT"].format(
        n_shared=f"{n_shared:,}", n_shown=f"{len(pooled):,}"))
    st.caption(copy.COMPARE["CAPTION_FRONTIER_AXES"])
    _download(pooled, slug=SLUGS["frontier_map"], sc=sc, key="frontier_map")

    st.subheader(copy.COMPARE["VIEW_SHARED_FRONTIER"])
    shared_long = _shared_long(_shared_frontier(tuple(ids), sc["tree"], sc["basis"]),
                               _slot_order(ids, slots))
    if shared_long.empty:
        st.caption(copy.COMPARE["EMPTY_SHARED_FRONTIER"])
        return pooled, shared_long
    _legend(ids, slots, names)
    st.plotly_chart(
        X.fig_diverging_shared(shared_long, _slot_order(ids, slots), slots=slots,
                               names=names, value_col="vol", top_n=top_n),
        width="stretch", key="fig_cmp_shared_frontier")
    st.caption(copy.COMPARE["CAPTION_SHARED_FRONTIER"].format(
        basis=copy.BASIS_LABELS[sc["basis"]]))
    st.caption(copy.COMPARE["CAPTION_SHARED_TOTAL"].format(
        n=f"{shared_long['topic_id'].nunique():,}"))
    _download(shared_long, slug=SLUGS["shared_frontier"], sc=sc, key="shared_frontier")
    return pooled, shared_long


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
    st.subheader(copy.COMPARE["VIEW_IMPACT"])
    st.markdown(f"**{copy.COMPARE['IMPACT_INDEX_HEADER']}**")
    index_df = _impact_index(tuple(ids))
    if index_df.empty:
        st.caption(copy.FIND["PANEL_EMPTY"])
    else:
        _legend(ids, slots, names)
        st.plotly_chart(X.fig_impact_intervals(index_df, slots, names=names),
                        width="stretch", key="fig_cmp_impact")
    st.caption(copy.COMPARE["CAPTION_IMPACT"].format(y0=WINDOW_START, y1=WINDOW_END))
    st.caption(_ci_sentence())
    st.caption(copy.COMPARE["IMPACT_BONUS_NOTE"].format(bonus_year=CFG["bonus_year"]))
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
    st.caption(copy.COMPARE["IMPACT_UNION_CAPTION"])
    st.caption(copy.COMPARE["CAPTION_IMPACT_SHOWN"].format(
        n=f"{shown['subfield_id'].nunique():,}", n_union=f"{union['subfield_id'].nunique():,}"))
    _download(union, slug=SLUGS["impact_subfields"], sc=sc, key="impact_subfields")
    return index_df, union


# --------------------------------------------------------------- the trends --

def _view_trends(ids, slots, names, sc) -> pd.DataFrame:
    top = _top_shared(tuple(ids), sc["tree"], sc["basis"], TRENDS_TOP_N)
    st.subheader(copy.COMPARE["TRENDS_HEADER"].format(n=f"{len(top):,}"))
    if top.empty:
        st.caption(copy.COMPARE["EMPTY_TRENDS"])
        return pd.DataFrame()
    keys = list(top["subfield_id"])
    frames, kept = {}, []
    for iid in ids:
        df = _trends(iid, sc["tree"], sc["basis"])
        mine = df[df["subfield_id"].isin(keys)].assign(institution_id=iid)
        if len(mine):
            frames[iid] = mine
            kept.append(mine)
    if not frames:
        st.caption(copy.COMPARE["EMPTY_TRENDS"])
        return pd.DataFrame()
    _legend(ids, slots, names)
    # 2B-R-12: the bonus year is labelled `<year>*` on the axis and the footnote
    # lives in the caption below, not in a banner of its own.
    st.plotly_chart(
        X.fig_trends_small_multiples(frames, slots, keys, names=names,
                                     value_col=TRENDS_VALUE_COL,
                                     bonus_year=str(CFG["bonus_year"])),
        width="stretch", key="fig_cmp_trends")
    st.caption(copy.COMPARE["CAPTION_TRENDS_SHARE"].format(**_scenario_words(sc)))
    st.caption(copy.COMPARE["TRENDS_SELECTION_HELP"])
    st.caption(copy.FIND["BONUS_YEAR_CAPTION"].format(year=CFG["bonus_year"]))
    out = pd.concat(kept, ignore_index=True)
    _download(out, slug=SLUGS["trends"], sc=sc, key="trends")
    return out


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
    st.subheader(copy.COMPARE["VIEW_COVERAGE"])
    df = _coverage(tuple(ids))
    if df.empty:
        st.caption(copy.FIND["PANEL_EMPTY"])
        return df
    _legend(ids, slots, names)
    st.plotly_chart(X.fig_coverage_strip(df, slots, names=names, labels=_state_labels()),
                    width="stretch", key="fig_cmp_coverage")
    st.caption(copy.COMPARE["CAPTION_COVERAGE"])
    st.caption(copy.COMPARE["STATE_TOTAL_HELP"])
    _download(df, slug=SLUGS["coverage"], sc=sc, key="coverage")
    return df


# ----------------------------------------------------------------- workbook --

def methods_rows(ctx: dict, ids: list, sc: dict, floor: int, top_n: int,
                 sheets: list) -> pd.DataFrame:
    """The workbook's Methods sheet: what the file is, and what every other
    sheet counts. Every VALUE comes from CFG, the manifest, `compare_data`'s own
    window constants or the live frames; every LABEL comes from `copy.COMPARE` /
    `copy.METHODS_SOURCES`, so no number is typed here either.

    2B-R re-cut: the snapshot row is GONE (2B-R-12, snapshot string removed
    app-wide) and four rows are new -- the data date, BOTH dynamics windows
    named verbatim (2B-R-6), the comparison cap (2B-R-4) with the frontier
    slider beside it, and the interval coverage sentence (2B-R-12)."""
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
    """`[(sheet label, what that sheet counts, frame)]`, in page order -- one
    sheet per view the page actually drew, with the METRIC each selector was on
    named in the caption, so a workbook cannot claim a view the reader did not
    see."""
    C = copy.COMPARE
    words = _scenario_words(sc)
    subject_label = C["XLSX_SHEET_SUBJECT_FIELD"] if metrics["level"] == "field" \
        else C["XLSX_SHEET_SUBJECT_SUBFIELD"]
    return [
        (C["XLSX_SHEET_OVERVIEW"], C["OVERVIEW_WINDOW"].format(y0=WINDOW_START, y1=WINDOW_END),
         frames["overview"]),
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
        (C["VIEW_TRENDS"], C["CAPTION_TRENDS_SHARE"].format(**words), frames["trends"]),
        (C["VIEW_COVERAGE"], C["CAPTION_COVERAGE"], frames["coverage"]),
    ]


def _workbook(ctx: dict, ids: list, sc: dict, floor: int, top_n: int, sheets: list) -> bytes:
    ordered = [(copy.COMPARE["XLSX_SHEET_METHODS"],
                methods_rows(ctx, ids, sc, floor, top_n, sheets))]
    ordered += [(label, frame) for label, _caption, frame in sheets]
    return workbook_bytes(ordered)


def _exports(ctx: dict, ids: list, sc: dict, floor: int, top_n: int, sheets: list) -> None:
    """ONE workbook (2B-13) beside the per-view CSVs. `data` is a callable, so
    the sheets are only written when someone clicks."""
    st.download_button(copy.COMPARE["EXPORT_XLSX_BUTTON"],
                       lambda: _workbook(ctx, ids, sc, floor, top_n, sheets),
                       file_name=workbook_filename(ids, sc["tree"], sc["basis"]),
                       mime=XLSX_MIME, help=copy.COMPARE["EXPORT_XLSX_HELP"],
                       key="dl_workbook")


# ------------------------------------------------- hand-off to Collaborate --

def _handoff(ctx: dict, ids: list) -> None:
    """2B-8's other half: any pair of the compared set opens on Collaborate.

    The button stashes the chosen pair in `st.session_state["pair"]` -- a plain,
    non-widget key, the basket's own idiom -- and then calls `st.switch_page`,
    an IN-SESSION hop that keeps the basket and the scenario alive. That call
    raises `StreamlitAPIException` (a plain `Exception`) when no multipage
    registry exists to switch into, which is exactly the AppTest/probe case;
    `switch_page`'s real navigation control flow raises `ScriptControlException`,
    a `BaseException` FOR THIS REASON, so this guard cannot swallow it."""
    st.subheader(copy.COMPARE["HANDOFF_HEADER"])
    st.caption(copy.COMPARE["HANDOFF_HELP"])
    default = selection.pair_from(ids)
    if default is None:
        return
    cols = st.columns([2, 2, 1])
    label = lambda i: _name(ctx, i)  # noqa: E731  (one-line format_func, both boxes)
    a = cols[0].selectbox(copy.COMPARE["HANDOFF_A_LABEL"], ids, index=ids.index(default[0]),
                          format_func=label, key="cmp_pair_a")
    b = cols[1].selectbox(copy.COMPARE["HANDOFF_B_LABEL"], ids, index=ids.index(default[1]),
                          format_func=label, key="cmp_pair_b")
    pair = selection.pair_from(ids, a, b)
    if pair is None:
        return
    link = selection.deeplink("pair", list(pair))
    if cols[2].button(copy.COMPARE["HANDOFF_LINK"], key="cmp_handoff_open"):
        st.session_state["pair"] = pair
        try:
            st.switch_page(COLLAB_PAGE)
        except Exception:
            pass
    st.code(link, language=None)


# ------------------------------------------------------------------ render --

def render() -> None:
    """The whole Compare page. Order: sidebar scenario (so a tree/basis carried
    from another page is read before anything is built) -> header -> selection
    -> substrates behind the A10 spinner -> overview cards -> subject / ERC /
    SDG selectors -> the two frontier charts -> impact -> trends -> coverage ->
    exports -> the pair hand-off."""
    bundle = _bundle()
    scenario = _sidebar_scenario()
    seed_from_query(bundle)
    _sidebar_basket(bundle)
    _header(bundle)
    ids = _selection(bundle)
    if len(ids) < 2:
        st.info(copy.COMPARE["EMPTY_TOO_FEW"])
        return
    # A10: a tree/basis flip pays `build_substrates` ONCE (measured 4.6 s,
    # cached); every other rerun finds it warm.
    with st.spinner(copy.COMPARE["SPINNER_SCENARIO"]):
        _subs(scenario["tree"], scenario["basis"])
    ctx = bundle["ctx"]
    slots = _slots(ctx, ids)
    names = _names(ctx, ids)

    frames = {"overview": _view_overview(ctx, ids, slots)}
    subject, level, subject_metric = _view_subject(ids, slots, names, scenario)
    frames["subject"] = subject
    frames["erc"], erc_metric = _view_erc(ctx, ids, slots, names, scenario)
    frames["sdg"], sdg_metric = _view_sdg(ctx, ids, slots, names, scenario)

    top_n = st.slider(copy.COMPARE["FRONTIER_TOPN_LABEL"], FRONTIER_TOPN_MIN,
                      FRONTIER_TOPN_MAX, FRONTIER_TOPN_DEFAULT, FRONTIER_TOPN_STEP,
                      help=copy.COMPARE["FRONTIER_TOPN_HELP"], key="cmp_frontier_topn",
                      **state.PERSIST)
    frames["frontier_map"], frames["shared_frontier"] = _view_frontier(
        ids, slots, names, scenario, int(top_n))
    frames["impact"], frames["impact_subfields"] = _view_impact(ids, slots, names, scenario)
    frames["trends"] = _view_trends(ids, slots, names, scenario)
    frames["coverage"] = _view_coverage(ids, slots, names, scenario)

    metrics = {"level": level, "subject": subject_metric, "erc": erc_metric,
               "sdg": sdg_metric}
    sheets = sheet_specs(scenario, frames, metrics)
    floor = int(st.session_state.get("cmp_impact_floor") or IMPACT_FLOOR_DEFAULT)
    _exports(ctx, ids, scenario, floor, int(top_n), sheets)
    _handoff(ctx, ids)

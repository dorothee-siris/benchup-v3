"""
app/lib/views_compare.py -- render functions for the Compare page (Sprint 2
Phase 2B, Stream C; BUILD_PLAN_2B.md decisions 2B-1 ... 2B-6, 2B-8, 2B-13,
2B-14 and amendments A1, A2, A3, A4, A8, A9, A10, A11).

COMPOSITION ONLY, the same rule as lib/views_find.py and lib/views_collab.py:
every frame comes from `lib/compare_data.py`, every figure from
`lib/charts_compare.py`, every colour from `lib/palette.py`, every id rule from
`lib/selection.py`, every URL from `lib/links.py`, every string from
`lib/copy.py`. Nothing here recomputes an indicator and nothing here types a
number into a rendered string (BUILD_PLAN_2A.md L10, scanned by
tests/test_pages_compare.py with tests/test_narrative.py's own collector).

PAGE ORDER
  sidebar: counting & taxonomy (the SAME `tree` / `basis` widget keys the Find
  and Collaborate pages use, so one scenario carries across the app) + the
  basket, read-only, with a link back to Find
  main: title + lead + verdict + snapshot -> the selection block (add by name,
  remove, reorder, the shareable deep link) -> the institution strip, in slot
  order, which is the reading key for everything under it -> nine views, each
  with the legend above it, its own captions and its own CSV: fields, subfields,
  ERC panels, SDG goals, frontier mix, frontier topics, impact (whole output and
  by subfield), trends, coverage -> the workbook -> the pair hand-off to
  Collaborate.

WHY THE COLOUR IS THE INSTITUTION (2B-1)
  Every figure on this page is coloured by institution and by nothing else, so
  the legend rendered above each view is the ONE key a reader needs. Slots come
  from `palette.institution_slots`, which assigns them by ascending `inst_key`
  (A8): removing an institution never repaints the survivors, and the same
  institution keeps its colour between two visits.

FORM RULINGS THIS PAGE INHERITS RATHER THAN RE-DECIDES
  * mirrors are DOT ROWS, one lane per institution (A4 / V's A/B #5): the
    caption `COMPARE["READING_ORDER"]` states the lane order under every one of
    them, because a lane-split row cannot be read from colour alone.
  * the frontier plane defaults to SMALL MULTIPLES and keeps the overlay as a
    labelled secondary mode (V's A/B #6 overturned 2B-3's overlay default:
    occlusion 0.91 at k = 6 against 0.0 faceted). The overlay's caption says
    what the picture hides, qualitatively -- the measured figure lives in
    design-system/ab/AB_VERDICT.md, not in a rendered string.
  * the trends grid shares ONE vertical scale, so it is fed an
    institution-normalised measure (the subfield's share of that institution's
    own output for the year) and the caption names it.
  * the per-subfield impact panel renders the UNION of what any institution
    clears (A1), with `n/a` where a cell is missing, and offers the lower floor.

PERFORMANCE (2B-14: warm rerun < 2 s at six institutions; A10)
  `views_find._bundle` / `views_find._subs` are reused BY IMPORT, so the engine
  context (2.5 s) and each (tree, basis) substrate (4.6 s) are paid once per
  process and shared with every other page. Every frame is `@st.cache_data`
  keyed on the HASHABLE scenario identity (a tuple of ids, the tree, the basis,
  a floor) -- ctx/subs are unhashable and are never cache_data arguments. A
  tree/basis flip pays `build_substrates` once, behind the A10 spinner.
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
from lib.exports_xlsx import XLSX_MIME, workbook_bytes, workbook_filename
from lib.palette import NA_MARK
from lib.search import search
from lib.views_find import (
    DASH, FRONTIER_TOP_N, SEP, SORT_TAXONOMY, SORT_VOLUME, _bundle, _hit_label, _count,
    _pct,
    _sidebar_scenario, _sort_control, _subs, _vol_col,
)

# ---------------------------------------------------------------- constants --
# SUBFIELDS_TOP_N is TWENTY here, not the profile's thirty. The mirror draws one
# LANE PER INSTITUTION inside every row (A4), so a row costs six times what the
# same row costs on the Find profile: V measured the twenty-six-row fields
# mirror at 2,020 px and states that the only honest lever on height is fewer
# ROWS, never a thinner mark (the >= 8 px mark is an acceptance floor). Thirty
# subfields at six lanes would put this one view past two full screens of
# scrolling before the reader reaches the ERC mirror. Twenty rows keeps the
# section comparable in height to the fields mirror above it, and the cut itself
# is disclosed in the caption.
SUBFIELDS_TOP_N = 20

# 2B-5 fixes the trends grid at six subfields (three columns x two rows of
# panels); A3 fixes HOW the six are chosen -- the largest SUMMED share across
# the compared set, never the intersection of per-institution top lists, which
# collapses to one subfield at k = 6.
TRENDS_TOP_N = 6

# The impact floors the artefact ships (data_contract.yaml: impact_cells carries
# floor in {10, 30}); the higher one is the default and the lower one is the
# labelled "more cells, wider intervals" variant (A1).
IMPACT_FLOORS = tuple(sorted(K.IMPACT_CELL_FLOORS, reverse=True))
IMPACT_FLOOR_DEFAULT = IMPACT_FLOORS[0]

# `?compare=` seeds the basket ONCE per session and then gets out of the way: a
# link that kept winning would resurrect an institution the reader had just
# removed. After the seed the basket is the single source of truth for this
# page, which is what makes add / remove / reorder mean anything (2B-8).
SEEDED_KEY = "compare_seeded"

FIND_PAGE = "pages/1_\U0001F50E_Find.py"
# `st.page_link` cannot carry a query string, so the SHAREABLE half of the
# hand-off is still a printed deep link (`selection.deeplink`). But a
# `st.link_button` to that link is a TRUE browser navigation -- a fresh page
# load that starts a brand-new Streamlit session, dropping the basket and the
# tree/basis scenario with it (Stream H's smoke finding, progress/2B_H.md:
# only the pair survived, because it rode the query string). `COLLAB_PAGE` is
# the file path `st.switch_page` needs to hop IN-SESSION instead, the same
# client-routed navigation `st.page_link` and the sidebar nav already use;
# `COLLAB_URL_PATH` remains only for the printed link's own text, a URL a
# reader can paste outside this session, never a page_link/switch_page arg.
COLLAB_PAGE = "pages/3_\U0001F91D_Collaborate.py"
COLLAB_URL_PATH = "/Collaborate"

# CSV file-name slugs. Code identifiers, never rendered copy -- the visible
# labels are `copy.COMPARE["VIEW_*"]`.
SLUGS = {"fields": "fields", "subfields": "subfields", "erc": "erc", "sdg": "sdg",
         "frontier_mix": "frontier_mix", "frontier_points": "frontier_topics",
         "impact": "impact", "impact_subfields": "impact_subfields",
         "trends": "trends", "coverage": "coverage"}

# The institution-normalised trends measure (V's needs_change 5): a subfield's
# share of that institution's OWN publications for the year. A column name, not
# a rendered string -- the caption that names the measure is
# `COMPARE["CAPTION_TRENDS_SHARE"]`.
TRENDS_VALUE_COL = "share_of_year"

WINDOW_START, WINDOW_END = CFG["window"]

# The institution swatch in the strip: a coloured glyph, tinted by the palette.
SWATCH_MARK = "●"        # black circle, the same mark lib/views_collab.py uses


# ------------------------------------------------------------------ frames --
# One @st.cache_data per K frame. `ids` is always a TUPLE: a list is unhashable
# and would make every one of these a cache miss on every rerun.

@st.cache_data(show_spinner=False, max_entries=12)
def _fields(ids: tuple, tree: str, basis: str) -> pd.DataFrame:
    return K.fields_long(_bundle()["ctx"], _subs(tree, basis), list(ids))


@st.cache_data(show_spinner=False, max_entries=12)
def _subfields(ids: tuple, tree: str, basis: str) -> pd.DataFrame:
    return K.subfields_long(_bundle()["ctx"], _subs(tree, basis), list(ids))


@st.cache_data(show_spinner=False, max_entries=12)
def _erc(ids: tuple) -> pd.DataFrame:
    return K.erc_long(_bundle()["ctx"], list(ids))


@st.cache_data(show_spinner=False, max_entries=12)
def _sdg(ids: tuple) -> pd.DataFrame:
    return K.sdg_long(_bundle()["ctx"], list(ids))


@st.cache_data(show_spinner=False, max_entries=12)
def _frontier_mix(ids: tuple) -> pd.DataFrame:
    """K names the fifth segment `not_scored`; the builder's own vocabulary is
    `charts_compare.NOT_SCORED`. The rename happens HERE, once: pass K's frame
    through unchanged and the builder would treat the residual row as a fifth
    quadrant, sum it into `scored`, and draw the not-scored segment at zero --
    silently losing between three and eighty-seven per cent of an institution's
    mass, which is exactly what A2 added the segment to prevent."""
    df = K.frontier_mix(_bundle()["ctx"], list(ids)).copy()
    df["quadrant"] = df["quadrant"].astype(str).replace({K.NOT_SCORED: X.NOT_SCORED})
    return df


@st.cache_data(show_spinner=False, max_entries=12)
def _frontier_points(ids: tuple, tree: str, basis: str, mode: str) -> pd.DataFrame:
    return K.frontier_points(_bundle()["ctx"], _subs(tree, basis), list(ids), mode)


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
    publications for that year, on the active basis. Normalising here (not in
    the builder) keeps the number the caption names and the number the line
    draws the same object."""
    df = K.trends_subfields(_bundle()["ctx"], iid, tree).copy()
    vol = _vol_col(basis)
    totals = df.groupby("year")[vol].transform("sum")
    df[TRENDS_VALUE_COL] = pd.to_numeric(df[vol], errors="coerce").div(totals).fillna(0.0)
    return df


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


def _legend(names: dict, slots: dict) -> None:
    """The one key every view needs, repeated above each of them: the palette's
    worst CVD pair is legal only WITH a secondary encoding, and this strip plus
    the row labels plus the hover are it (palette_validation run 9)."""
    st.markdown(X.institution_legend_html(names, slots), unsafe_allow_html=True)


def _interval(low, high) -> str:
    if low is None or high is None or pd.isna(low) or pd.isna(high):
        return NA_MARK
    return f"{_pct(low)}{DASH}{_pct(high)}"


def _scenario_words(sc: dict) -> dict:
    return {"basis": copy.BASIS_LABELS[sc["basis"]], "tree": copy.TREE_LABELS[sc["tree"]]}


def _shares_line(ctx: dict, ids, slots: dict, numerator: str) -> str:
    """"Name: share" for every compared institution, in the legend's own order
    -- the ERC and SDG mirrors both rest on an institution-specific
    denominator, so the caption has to give one figure per institution."""
    idx = ctx["index_by_id"]
    parts = []
    for iid in _slot_order(ids, slots):
        row = idx.loc[iid]
        total = row["total_frac"]
        value = (row[numerator] / total) if total and not pd.isna(total) and total > 0 else None
        parts.append(f"{_name(ctx, iid)}: {_pct(value)}")
    return f" {SEP} ".join(parts)


def _download(df: pd.DataFrame, *, slug: str, sc: dict, key: str) -> None:
    """Streamlit 1.61 accepts a zero-arg callable for `data`, so the CSV is
    encoded only when someone actually clicks (lib/views_find.py's pattern).
    The RAW frame goes out: fractions, ids and every column K ships."""
    name = f"benchup_compare_{slug}_{sc['tree']}_{sc['basis']}.csv"
    st.download_button(copy.COMPARE["DOWNLOAD_VIEW"],
                       lambda: df.to_csv(index=False).encode("utf-8"),
                       mime="text/csv", file_name=name, key=f"dl_{key}")


# ----------------------------------------------------------------- sidebar --

def _sidebar_basket(bundle: dict) -> None:
    """READ-ONLY here, exactly as on Collaborate: this page edits the basket
    through its own selection block, where the reader is looking, and the
    sidebar only reports the count against the cap and links back to Find."""
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
    # rather than taking the page down (views_collab.py's own note).
    try:
        sb.page_link(FIND_PAGE, label=copy.NAV["FIND_LABEL"])
    except Exception:
        sb.caption(copy.NAV["FIND_LABEL"])


# ------------------------------------------------------------------ header --

def _header(bundle: dict) -> None:
    st.title(copy.NAV["COMPARE_LABEL"])
    st.subheader(copy.NAV["COMPARE_LEAD"])
    st.caption(copy.COMPARE["PAGE_INTRO"])
    st.markdown(f"**{copy.VERDICT_LINE}**")
    mf = manifest()
    stamp = (mf.get("generated_at") or mf.get("source_manifest_generated_at")
             or mf.get("deployed_at") or NA_MARK)
    st.caption(copy.FIND["SNAPSHOT_CAPTION"].format(
        snapshot=mf.get("snapshot") or CFG["snapshot"], generated_at=stamp,
        n_institutions=f"{len(bundle['index_df']):,}", sep=SEP))


# --------------------------------------------------------------- selection --

def _add_by_name(bundle: dict) -> None:
    """Find's own search idiom: a free-text box, a selectbox over the hits, and
    an add button. `state.add` returns False only when the cap is already
    reached and NOTHING changed, so the page is not rerun in that case and the
    cap message renders on this same run (Stream S's contract)."""
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


def _selection_controls(ctx: dict, ids: list) -> None:
    """One row per compared institution in the reader's OWN order (the order
    `state.move` maintains and the deep link carries), with move and remove
    buttons. Colours do not follow this order -- they follow `inst_key` -- and
    `COMPARE["MOVE_HELP"]` says so, because a reader who reorders and sees no
    colour move is entitled to an explanation."""
    for n, iid in enumerate(ids):
        cols = st.columns([6, 1, 1, 1])
        cols[0].write(_name(ctx, iid))
        if cols[1].button(copy.COMPARE["MOVE_UP"], key=f"cmp_up_{iid}", disabled=n == 0):
            state.move(iid, -1)
            st.rerun()
        if cols[2].button(copy.COMPARE["MOVE_DOWN"], key=f"cmp_down_{iid}",
                          disabled=n == len(ids) - 1):
            state.move(iid, 1)
            st.rerun()
        if cols[3].button(copy.COMPARE["REMOVE_BUTTON"], key=f"cmp_rm_{iid}"):
            state.remove(iid)
            st.rerun()
    if ids and st.button(copy.COMPARE["CLEAR_BUTTON"], key="cmp_clear"):
        state.clear()
        st.rerun()


def seed_from_query(bundle: dict) -> None:
    """`?compare=` -> the basket, ONCE per session, BEFORE anything is drawn.

    Two reasons it is not part of `_selection`. First, the sidebar basket is
    rendered before the main column, so seeding later left a deep-linked reader
    looking at an empty basket count until their next interaction (caught by
    reading the probe's own head screenshot, not by a test). Second, seeding
    once and then reading only the basket is what makes remove and reorder
    stick: a link that kept winning would resurrect an institution the reader
    had just removed."""
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
    the reader's own order, capped."""
    ctx = bundle["ctx"]
    known = ctx["id_pos"]
    st.subheader(copy.COMPARE["SELECTION_HEADER"])
    st.caption(copy.COMPARE["SELECTION_HELP"])
    _add_by_name(bundle)
    ids = selection.compare_ids(state.items(), [], known, state.BASKET_CAP)
    _selection_controls(ctx, ids)
    st.caption(copy.COMPARE["CAP_HELP"].format(cap=state.BASKET_CAP))
    st.caption(copy.COMPARE["MOVE_HELP"])
    st.caption(copy.COMPARE["DEEPLINK_LABEL"])
    st.code(selection.deeplink("compare", ids), language=None)
    return ids


# --------------------------------------------------------- the strip (2B-1) --

def _strip(ctx: dict, ids: list, slots: dict) -> None:
    """One row per institution IN SLOT ORDER -- the same order the legend and
    every figure use, so the strip is the reading key: swatch, name, type and
    country, both size figures, the impact figure with its interval, and the
    link out to the publications behind it."""
    impact = _impact_index(tuple(ids)).set_index("institution_id")
    st.subheader(copy.COMPARE["STRIP_HEADER"])
    st.caption(copy.COMPARE["STRIP_COLOUR_NOTE"])
    with st.container(key="compare_strip", border=True):
        for iid in _slot_order(ids, slots):
            row = ctx["index_by_id"].loc[iid]
            cols = st.columns([3, 2, 2, 2, 2])
            colour = P.institution_color(slots.get(iid, len(slots)))
            # A coloured GLYPH, not a styled box: a box would need typed pixel
            # lengths inside a rendered string (BUILD_PLAN_2A.md L10). The only
            # interpolated value is the palette's own colour.
            cols[0].markdown(f'<span style="color:{colour}">{SWATCH_MARK}</span> '
                             f"**{_name(ctx, iid)}**", unsafe_allow_html=True)
            cols[1].caption(f"{str(row['type'])} {SEP} "
                            f"{countries.name(str(row['country_code']))}")
            cols[2].caption(f"{copy.FIND['COL_SIZE_FULL']}: "
                            f"{_count(row['total_full_2020_2024'])}")
            cols[2].caption(f"{copy.FIND['COL_SIZE_FRAC']}: "
                            f"{_count(row['total_frac_2020_2024'])}")
            if iid in impact.index:
                cell = impact.loc[iid]
                cols[3].caption(f"{copy.COMPARE['STRIP_PP']}: {_pct(cell['pp'])}")
                cols[3].caption(_interval(cell["ci_low"], cell["ci_high"]))
            else:
                cols[3].caption(f"{copy.COMPARE['STRIP_PP']}: {NA_MARK}")
            cols[4].link_button(copy.COMPARE["STRIP_LINK_PUBS"], links.works_url(iid),
                                help=copy.FIND["LINK_OPENALEX_HELP"])


# ------------------------------------------------------------- the mirrors --

def _view_fields(ids, slots, names, sc) -> pd.DataFrame:
    st.subheader(copy.COMPARE["VIEW_FIELDS"])
    df = _fields(tuple(ids), sc["tree"], sc["basis"])
    if df.empty:
        st.caption(copy.FIND["PANEL_EMPTY"])
        return df
    sort = _sort_control("compare_fields")
    _legend(names, slots)
    st.plotly_chart(X.fig_mirror_dots(df, family="oa", slots=slots, sort=sort, names=names,
                                      label_col="field_name", volume_col=_vol_col(sc["basis"])),
                    width="stretch", key="fig_cmp_fields")
    st.caption(copy.COMPARE["CAPTION_FIELDS"].format(**_scenario_words(sc)))
    st.caption(copy.COMPARE["READING_ORDER"])
    st.caption(copy.FIND["CAPTION_SI"])
    _download(df, slug=SLUGS["fields"], sc=sc, key="fields")
    return df


def _view_subfields(ids, slots, names, sc) -> pd.DataFrame:
    """The top SUBFIELDS_TOP_N subfields by the mass the compared SET holds in
    them (A3) -- not the intersection of per-institution top lists, which is one
    subfield at six institutions, and not a per-institution top list, which
    would draw a different row set for every lane."""
    st.subheader(copy.COMPARE["VIEW_SUBFIELDS"])
    df = _subfields(tuple(ids), sc["tree"], sc["basis"])
    top = _top_shared(tuple(ids), sc["tree"], sc["basis"], SUBFIELDS_TOP_N)
    if df.empty or top.empty:
        st.caption(copy.FIND["PANEL_EMPTY"])
        return df
    keep = list(top["subfield_id"])
    shown = df[df["subfield_id"].isin(keep)]
    _legend(names, slots)
    st.plotly_chart(X.fig_mirror_dots(shown, family="oa", slots=slots, sort=SORT_VOLUME,
                                      names=names, label_col="subfield_name",
                                      volume_col=_vol_col(sc["basis"])),
                    width="stretch", key="fig_cmp_subfields")
    st.caption(copy.COMPARE["CAPTION_SUBFIELDS"].format(**_scenario_words(sc)))
    st.caption(copy.COMPARE["CAPTION_SUBFIELDS_TOP"].format(n=f"{len(keep):,}"))
    st.caption(copy.COMPARE["READING_ORDER"])
    st.caption(copy.FIND["CAPTION_SI"])
    st.caption(copy.FIND["CAPTION_SI_FLOOR"].format(
        floor_solid=int(profile_data.SI_FLOOR_SOLID),
        floor_thin=int(profile_data.SI_FLOOR_THIN)))
    _download(shown, slug=SLUGS["subfields"], sc=sc, key="subfields")
    return shown


def _missing_note(ctx: dict, ids, df: pd.DataFrame, template: str) -> None:
    """An institution with no row in a classified panel is NAMED, never left to
    read as a flat zero (BUILD_PLAN_2A.md L11: n/a is never 0)."""
    have = set(df["institution_id"]) if len(df) else set()
    for iid in ids:
        if iid not in have:
            st.caption(template.format(institution=_name(ctx, iid)))


def _view_erc(ctx, ids, slots, names, sc) -> pd.DataFrame:
    st.subheader(copy.COMPARE["VIEW_ERC"])
    df = _erc(tuple(ids))
    if df.empty:
        st.caption(copy.FIND["PANEL_EMPTY"])
        return df
    sort = _sort_control("compare_erc", default=SORT_TAXONOMY)
    _legend(names, slots)
    st.plotly_chart(X.fig_mirror_dots(df, family="erc", slots=slots, sort=sort, names=names,
                                      label_col="panel_label", volume_col="mass"),
                    width="stretch", key="fig_cmp_erc")
    st.caption(copy.COMPARE["CAPTION_ERC"])
    st.caption(copy.COMPARE["CAPTION_CLASSIFIED_SHARES"].format(
        shares=_shares_line(ctx, ids, slots, "erc_classified_mass_frac")))
    st.caption(copy.COMPARE["READING_ORDER"])
    st.caption(copy.FIND["CAPTION_SI"])
    if sc["basis"] == "full":
        st.caption(copy.FIND["FRACTIONAL_ONLY_PANEL"])
    _missing_note(ctx, ids, df, copy.COMPARE["EMPTY_NO_ERC"])
    _download(df, slug=SLUGS["erc"], sc=sc, key="erc")
    return df


def _view_sdg(ctx, ids, slots, names, sc) -> pd.DataFrame:
    st.subheader(copy.COMPARE["VIEW_SDG"])
    df = _sdg(tuple(ids))
    if df.empty:
        st.caption(copy.FIND["PANEL_EMPTY"])
        return df
    _legend(names, slots)
    # No sort toggle, for the profile panel's own reason: the goal numbers are a
    # canonical sequence a reader navigates by position.
    st.plotly_chart(X.fig_mirror_dots(df, family="sdg", slots=slots, sort=SORT_TAXONOMY,
                                      names=names, label_col="sdg_label_numbered",
                                      si_col="esi", volume_col="mass"),
                    width="stretch", key="fig_cmp_sdg")
    st.caption(copy.COMPARE["CAPTION_SDG"])
    st.caption(copy.COMPARE["CAPTION_CLASSIFIED_SHARES"].format(
        shares=_shares_line(ctx, ids, slots, "sdg_classified_mass_frac")))
    st.caption(copy.COMPARE["READING_ORDER"])
    if sc["basis"] == "full":
        st.caption(copy.FIND["FRACTIONAL_ONLY_PANEL"])
    _missing_note(ctx, ids, df, copy.COMPARE["EMPTY_NO_SDG"])
    _download(df, slug=SLUGS["sdg"], sc=sc, key="sdg")
    return df


# ------------------------------------------------------------- the frontier --

def _view_frontier_mix(ctx, ids, slots, names, sc) -> pd.DataFrame:
    st.subheader(copy.COMPARE["VIEW_FRONTIER_MIX"])
    df = _frontier_mix(tuple(ids))
    if df.empty:
        st.caption(copy.FIND["PANEL_EMPTY"])
        return df
    _legend(names, slots)
    st.plotly_chart(
        X.fig_quadrant_mix(df, slots, names=names,
                           labels={X.NOT_SCORED: copy.COMPARE["QUADRANT_UNSCORED_LABEL"]}),
        width="stretch", key="fig_cmp_quadrant")
    st.caption(copy.COMPARE["CAPTION_FRONTIER_MIX"])
    # The two counts are computed from the frame on screen and the index's own
    # fractional totals, never typed: unscored mass is the fifth segment's share
    # times the institution's output, summed over the compared set.
    idx = ctx["index_by_id"]
    unscored = 0.0
    total = 0.0
    for iid in ids:
        mass = float(idx.loc[iid, "total_frac"] or 0.0)
        share = df[(df["institution_id"] == iid) & (df["quadrant"] == X.NOT_SCORED)]["share"]
        total += mass
        unscored += mass * (float(share.iloc[0]) if len(share) else 0.0)
    st.caption(copy.COMPARE["CAPTION_QUADRANT_COUNTS"].format(
        n_scored=_count(total - unscored), n_unscored=_count(unscored)))
    st.caption(copy.COMPARE["QUADRANT_UNSCORED_HELP"])
    st.caption(copy.COMPARE["QUADRANT_MISSING_HELP"])
    _download(df, slug=SLUGS["frontier_mix"], sc=sc, key="frontier_mix")
    return df


def _frontier_modes() -> tuple:
    return (copy.FIND["FRONTIER_MODE_TOP"].format(n=f"{FRONTIER_TOP_N:,}"),
            copy.FIND["FRONTIER_MODE_EMERGING"])


def _view_frontier_points(ids, slots, names, sc) -> pd.DataFrame:
    """TWO controls, because they answer two different questions: WHICH topics
    are drawn (the R2 frontier mode, volume or emergence) and HOW they are laid
    out (V's A/B #6 winner by default, the overlay behind a label)."""
    st.subheader(copy.COMPARE["VIEW_FRONTIER_POINTS"])
    facets, overlay = (copy.COMPARE["FRONTIER_FORM_FACETS"],
                       copy.COMPARE["FRONTIER_FORM_OVERLAY"])
    st.segmented_control(copy.COMPARE["FRONTIER_FORM_LABEL"], [facets, overlay],
                         default=facets, required=True, key="cmp_frontier_form",
                         **state.PERSIST)
    mode_top, mode_emerging = _frontier_modes()
    st.segmented_control(copy.FIND["FRONTIER_MODE_LABEL"], [mode_top, mode_emerging],
                         default=mode_top, required=True, key="cmp_frontier_mode",
                         **state.PERSIST)
    picked_mode = st.session_state.get("cmp_frontier_mode") or mode_top
    mode = "emerging" if picked_mode == mode_emerging else "top"
    df = _frontier_points(tuple(ids), sc["tree"], sc["basis"], mode)
    if df.empty:
        st.caption(copy.COMPARE["EMPTY_FRONTIER_POINTS"])
        return df
    _legend(names, slots)
    picked_form = st.session_state.get("cmp_frontier_form") or facets
    size_col = _vol_col(sc["basis"])
    with st.container(key="cmp_frontier_plot"):
        if picked_form == overlay:
            st.plotly_chart(X.fig_frontier_overlay(df, slots, names=names, size_col=size_col),
                            width="stretch", key="fig_cmp_frontier_overlay")
        else:
            st.plotly_chart(
                X.fig_frontier_small_multiples(df, slots, names=names, size_col=size_col),
                width="stretch", key="fig_cmp_frontier_facets")
    st.caption(copy.COMPARE["CAPTION_FRONTIER_POINTS"].format(basis=copy.BASIS_LABELS[sc["basis"]]))
    st.caption(copy.COMPARE["CAPTION_FRONTIER_OVERLAY"] if picked_form == overlay
               else copy.COMPARE["CAPTION_FRONTIER_FACETS"])
    _download(df, slug=SLUGS["frontier_points"], sc=sc, key="frontier_points")
    return df


# --------------------------------------------------------------- the impact --

def _impact_rows(union: pd.DataFrame, top: pd.DataFrame) -> pd.DataFrame:
    """The union can hold two hundred subfields; a dot-interval row per subfield
    per institution would run to a page of scrolling nobody reads. The cut is
    the SAME rule the subfields mirror uses -- the subfields the compared set
    publishes most in -- so the two sections show the same subjects, and the
    caption states how many of the union that leaves."""
    keep = [s for s in top["subfield_id"] if s in set(union["subfield_id"])]
    if keep:
        return union[union["subfield_id"].isin(keep)]
    # No overlap at all (possible at the high floor on a set whose biggest
    # subfields are all thin): fall back to the union's own best-evidenced
    # subfields rather than showing nothing.
    order = (union.groupby("subfield_id")["n_works_full"].max()
                  .sort_values(ascending=False).head(SUBFIELDS_TOP_N).index)
    return union[union["subfield_id"].isin(list(order))]


def _view_impact(ids, slots, names, sc) -> tuple:
    st.subheader(copy.COMPARE["VIEW_IMPACT"])
    _legend(names, slots)
    st.markdown(f"**{copy.COMPARE['IMPACT_INDEX_HEADER']}**")
    index_df = _impact_index(tuple(ids))
    if index_df.empty:
        st.caption(copy.FIND["PANEL_EMPTY"])
    else:
        st.plotly_chart(X.fig_impact_intervals(index_df, slots, names=names),
                        width="stretch", key="fig_cmp_impact")
    st.caption(copy.COMPARE["CAPTION_IMPACT"].format(y0=WINDOW_START, y1=WINDOW_END))
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
    top = _top_shared(tuple(ids), sc["tree"], sc["basis"], SUBFIELDS_TOP_N)
    shown = _impact_rows(union, top)
    st.plotly_chart(X.fig_impact_subfields(shown, slots, names=names),
                    width="stretch", key="fig_cmp_impact_subfields")
    st.caption(copy.COMPARE["IMPACT_UNION_CAPTION"])
    st.caption(copy.COMPARE["CAPTION_IMPACT_SHOWN"].format(
        n=f"{shown['subfield_id'].nunique():,}", n_union=f"{union['subfield_id'].nunique():,}"))
    st.caption(copy.COMPARE["READING_ORDER"])
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
    _legend(names, slots)
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
    """The six exclusive states, in the page's own words (N's dict) rather than
    the builder's fallbacks."""
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
    _legend(names, slots)
    st.plotly_chart(X.fig_coverage_strip(df, slots, names=names, labels=_state_labels()),
                    width="stretch", key="fig_cmp_coverage")
    st.caption(copy.COMPARE["CAPTION_COVERAGE"])
    st.caption(copy.COMPARE["STATE_TOTAL_HELP"])
    _download(df, slug=SLUGS["coverage"], sc=sc, key="coverage")
    return df


# ----------------------------------------------------------------- workbook --

def methods_rows(ctx: dict, ids: list, sc: dict, floor: int, sheets: list) -> pd.DataFrame:
    """The workbook's Methods sheet: what the file is, and what every other
    sheet counts. Every VALUE comes from CFG, the manifest or the live frames;
    every LABEL comes from `copy.COMPARE` / `copy.METHODS_SOURCES`, so no number
    is typed here either (the workbook is a rendered surface like any other)."""
    mf = manifest()
    words = _scenario_words(sc)
    src = copy.METHODS_SOURCES
    rows = [
        (copy.COMPARE["XLSX_ROW_SNAPSHOT"], str(mf.get("snapshot") or CFG["snapshot"]),
         src["snapshot"]),
        (copy.COMPARE["XLSX_ROW_WINDOW"], f"{WINDOW_START}{DASH}{WINDOW_END}", src["y0"]),
        (copy.COMPARE["XLSX_ROW_TREE"], words["tree"], copy.COMPARE["XLSX_SOURCE_PAGE"]),
        (copy.COMPARE["XLSX_ROW_BASIS"], words["basis"], copy.COMPARE["XLSX_SOURCE_PAGE"]),
        (copy.COMPARE["XLSX_ROW_INSTITUTIONS"],
         "; ".join(_name(ctx, i) for i in ids), copy.COMPARE["XLSX_SOURCE_PAGE"]),
        (copy.COMPARE["XLSX_ROW_FLOORS"],
         copy.COMPARE["IMPACT_FLOOR_OPTION"].format(floor=floor), src["floor_solid"]),
        (copy.COMPARE["XLSX_ROW_FLOORS"],
         copy.FIND["CAPTION_SI_FLOOR"].format(floor_solid=int(profile_data.SI_FLOOR_SOLID),
                                              floor_thin=int(profile_data.SI_FLOOR_THIN)),
         src["floor_thin"]),
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


def sheet_specs(sc: dict, frames: dict) -> list:
    """`[(sheet label, what that sheet counts, frame)]`, in page order. Built
    HERE rather than inline in `render` so a test can assert that the workbook
    carries a sheet for every view the page drew, using the same labels and the
    same captions the reader saw."""
    C = copy.COMPARE
    words = _scenario_words(sc)
    return [
        (C["VIEW_FIELDS"], C["CAPTION_FIELDS"].format(**words), frames["fields"]),
        (C["VIEW_SUBFIELDS"], C["CAPTION_SUBFIELDS"].format(**words), frames["subfields"]),
        (C["VIEW_ERC"], C["CAPTION_ERC"], frames["erc"]),
        (C["VIEW_SDG"], C["CAPTION_SDG"], frames["sdg"]),
        (C["VIEW_FRONTIER_MIX"], C["CAPTION_FRONTIER_MIX"], frames["frontier_mix"]),
        (C["VIEW_FRONTIER_POINTS"],
         C["CAPTION_FRONTIER_POINTS"].format(basis=copy.BASIS_LABELS[sc["basis"]]),
         frames["frontier_points"]),
        (C["XLSX_SHEET_IMPACT_INDEX"], C["CAPTION_IMPACT"].format(y0=WINDOW_START, y1=WINDOW_END),
         frames["impact"]),
        (C["XLSX_SHEET_IMPACT_SUBFIELDS"], C["IMPACT_UNION_CAPTION"], frames["impact_subfields"]),
        (C["VIEW_TRENDS"], C["CAPTION_TRENDS_SHARE"].format(**words), frames["trends"]),
        (C["VIEW_COVERAGE"], C["CAPTION_COVERAGE"], frames["coverage"]),
    ]


def _workbook(ctx: dict, ids: list, sc: dict, floor: int, sheets: list) -> bytes:
    ordered = [(copy.COMPARE["XLSX_SHEET_METHODS"],
                methods_rows(ctx, ids, sc, floor, sheets))]
    ordered += [(label, frame) for label, _caption, frame in sheets]
    return workbook_bytes(ordered)


def _exports(ctx: dict, ids: list, sc: dict, floor: int, sheets: list) -> None:
    """ONE workbook (2B-13) beside the per-view CSVs. `data` is a callable, so
    the sheets are only written when someone clicks -- the frames themselves are
    already in the cache from the render above."""
    st.download_button(copy.COMPARE["EXPORT_XLSX_BUTTON"],
                       lambda: _workbook(ctx, ids, sc, floor, sheets),
                       file_name=workbook_filename(ids, sc["tree"], sc["basis"]),
                       mime=XLSX_MIME, help=copy.COMPARE["EXPORT_XLSX_HELP"],
                       key="dl_workbook")


# ----------------------------------------------------- hand-off to Collaborate --

def _handoff(ctx: dict, ids: list) -> None:
    """2B-8's other half: any pair of the compared set opens on Collaborate.

    The button stashes the chosen pair in `st.session_state["pair"]` -- a
    plain, non-widget key, the same idiom the basket already uses -- and then
    calls `st.switch_page(COLLAB_PAGE)`, an IN-SESSION client-routed hop that
    keeps the basket and the tree/basis scenario alive (unlike the
    `link_button` this replaces: a true browser navigation that started a
    fresh session every time, see `COLLAB_PAGE`'s comment above).
    `views_collab._pair_picker` reads and consumes that key first, ahead of
    the `?pair=` query and the basket order.

    `st.switch_page` raises `StreamlitAPIException` (a plain `Exception`) when
    no multipage registry exists to switch into -- AppTest and the acceptance
    probe both run this page standalone, exactly the gap `_sidebar_basket`'s
    `page_link` call already guards a few hundred lines up. The `except
    Exception` here is deliberately narrow: `switch_page`'s own real
    navigation control flow raises `ScriptControlException`, which Streamlit
    define as a `BaseException` FOR THIS REASON (its own docstring: "to avoid
    being caught by user code"), so this guard cannot swallow it."""
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
    -> substrates behind the A10 spinner -> the strip -> nine views -> exports
    -> the pair hand-off."""
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
    # cached, at most three scenarios live); every other rerun finds it warm.
    with st.spinner(copy.COMPARE["SPINNER_SCENARIO"]):
        _subs(scenario["tree"], scenario["basis"])
    ctx = bundle["ctx"]
    slots = _slots(ctx, ids)
    names = _names(ctx, ids)
    _strip(ctx, ids, slots)

    # Dict literals evaluate in source order, so the views still render top to
    # bottom; collecting them here is what lets ONE list drive both the page and
    # the workbook (`sheet_specs`).
    frames = {"fields": _view_fields(ids, slots, names, scenario),
              "subfields": _view_subfields(ids, slots, names, scenario),
              "erc": _view_erc(ctx, ids, slots, names, scenario),
              "sdg": _view_sdg(ctx, ids, slots, names, scenario),
              "frontier_mix": _view_frontier_mix(ctx, ids, slots, names, scenario),
              "frontier_points": _view_frontier_points(ids, slots, names, scenario)}
    impact, impact_subs = _view_impact(ids, slots, names, scenario)
    frames["impact"], frames["impact_subfields"] = impact, impact_subs
    frames["trends"] = _view_trends(ids, slots, names, scenario)
    frames["coverage"] = _view_coverage(ids, slots, names, scenario)

    sheets = sheet_specs(scenario, frames)
    floor = int(st.session_state.get("cmp_impact_floor") or IMPACT_FLOOR_DEFAULT)
    _exports(ctx, ids, scenario, floor, sheets)
    _handoff(ctx, ids)

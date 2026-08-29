"""
app/lib/views_find.py -- render functions for the Find page (Sprint 2 Phase 2A,
Stream E; rebuilt for Refinement R1 by stream R-E2 against BUILD_PLAN_2A.md
S9.2 L16-L23 and docs/VIZ_SPEC.md S1.3/S1.9/S2.10-S2.22).

COMPOSITION ONLY: every ranking, filter, badge, frame, figure, table shape,
string and number comes from lib/engine and lib/{profile_data,charts,tiles,
wordcloud_png,ranked,search,filters,badges,exports,links,countries,copy,state,
palette,app_config,data_cache}. Nothing here re-implements them and nothing
here types a value into a rendered string (BUILD_PLAN_2A.md L10).

PAGE ORDER (L16/L17, re-laid by R2/L30 as the Lorraine lab card's GRID, top to
bottom, and the order the code below follows):
  title + intro + verdict + snapshot caption, with the "Filtered by..." strip
  slot right under it -> seed search -> PROFILE section: row 1 in three columns
  (identity | eight KPI tiles in a 2 x 4 grid, each carrying its index baseline
  | subfield wordcloud), row 2 full width (one segmented control and one chip
  legend above a global + yearly breakdown pair), then six collapsed chart
  panels -> BENCHMARK section, headed by the controls row (depth, C1, L7, a
  post-filters expander) and the "How to read the lenses" guide -> the lens
  tabs, labelled by `copy.LENS_NAMES`. The SIDEBAR now holds only what is
  app-wide: counting & taxonomy (tree, basis) and the Basket (L16 -- gate-2A
  feedback #1: a control that governs one section belongs at the head of that
  section, not a page away in the sidebar).

  The R1 coverage line is GONE (L30, VIZ_SPEC S2.12 RETIRED): each of its four
  items now sits where it is read -- ERC-classified share in the ERC panel
  caption, catch-all share in the top-topics caption, L2f-eligible cells in the
  L2f tab's own intro, SDG-tagged share was already a tile.

PERFORMANCE SHAPE (measured on this data, env-app; see progress/R1_E2.md):
  * load_context 2.5 s / build_substrates 4.6 s, both @st.cache_resource;
    rank_all 0.12 s per seed, recomputed every rerun (cheap);
  * build_rows over a FULL ranking is 0.95 s per lens, so rows are built only
    for what is actually shown -- the post-filtered depth cut, the tail-search
    matches, and (lazily, through st.download_button's callable `data`) the
    full filtered ranking for the CSV. The lens-specific evidence
    (`engine.evidence.rows_evidence`) is computed on exactly the same id
    subsets, never on the whole population.
  * `st.expander` BODIES EXECUTE on every rerun even when collapsed -- only
    the display folds. Two consequences, both load-bearing:
      - the POST-FILTERS expander must keep executing (its widgets have to
        register every run), so it is never gated;
      - the six PANEL expanders therefore build six figures every rerun.
        Their FRAMES are `@st.cache_data` keyed on (iid, tree, basis) and
        fetch ctx/subs from the cache_resource internally -- ctx and subs are
        unhashable and are never passed as cache_data arguments -- which is
        what brings a full warm rerun WITH all six panels to a measured
        0.88 s (0.30 s for the profile without them). Gating the bodies on
        the expander's own session-state key was tried and rejected: that
        state resets to the coded `expanded=` on the next rerun
        (progress/R1_E2.md), so a gated panel would blank itself.

STRINGS: every user-facing string lives in `lib/copy.py` under its own
digit-ban rule -- no digit outside a lens code / "top10"; every number is a
`{placeholder}` filled here from CFG or the live data
(`tests/test_narrative.py` enforces this over this file's `st.*` calls).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from lib import baselines, charts, copy, countries, links, profile_data, state, tiles
from lib import palette as P
from lib.app_config import CFG
from lib.badges import badges_for, catchall_tooltip, umbrella_flags, umbrella_medians
from lib.data_cache import DATA_DIR, doctype_by_year, index, manifest, topics_dim
from lib.engine import (
    ALL_LENSES, CONCORDANCE_N, aspirational, build_rows, build_substrates, catchall_811_share,
    concordance, cut_with_ties, family_overlap_scores, load_context, rank_all, seed_card,
)
from lib.engine.evidence import rows_evidence
from lib.exports import ranking_csv, ranking_filename
from lib.filters import active_controls_strip, apply_filters, explain_empty
from lib.palette import NA_MARK
from lib.ranked import (
    concordance_caption, depth_caption, format_concordance, format_rows,
    render_concordance_table, render_ranked_table,
)
from lib.search import build_search_index, normalize, search
from lib.wordcloud_png import render_wordcloud_png

# The C1 lens restricts L1 to the seed's top-N subfields; N is a bare literal
# inside lib/engine/lenses.py::build_c1_for_seed (`np.argsort(...)[:20]`), which
# is Stream B's vendored file and gives it no name. Read here ONCE so no
# rendered string ever types it (BUILD_PLAN_2A.md L10).
CORE_TOP_N = 20

# The displayed cut of the "top N" profile panels and of the frontier panel's
# volume mode. Module constants, never a digit inside a caption: the captions
# take them as `{n}` placeholders. SUBFIELDS_TOP_N is 30 under R2/L34 (the panel
# also lost its sort toggle: "top 30" is itself a volume-ordered concept, and a
# taxonomy re-sort of a volume-defined cut reads as an arbitrary 30 rows in ID
# order); FRONTIER_TOP_N is L33's two-hundred-topic volume mode.
SUBFIELDS_TOP_N = 30
TOPICS_TOP_N = 20
FRONTIER_TOP_N = 200

SEP = "·"   # middle dot -- the separator copy.STRIP_JOIN already uses
DASH = "–"  # en dash -- interval rendering

WINDOW_START, WINDOW_END = CFG["window"]
DEPTH_OPTIONS = [CFG["depth"]["default"], CFG["depth"]["max"]]

# Layout constants (VIZ_SPEC S1.9 / S2.11 / S2.21). Streamlit collapses a
# horizontal block to a vertical stack below its own small breakpoint, which is
# what makes the eight tiles wrap one-per-row at 390 px with no media query.
N_TILES = 8
# L30 asks for a 2 x 4 grid inside row 1's middle column. MEASURED at 1280 px
# (`tests/ui/screenshots/e3_find_top_1280.png`, first render): the main content
# box is ~820 px, the profile's own bordered container takes ~32 px of it, the
# three columns split the remaining ~756 px 1.0 : 2.0 : 1.4, so the middle
# column is ~344 px -- four tiles across it are ~74 px wide, ~40 px inside each
# tile's bordered container, and every label breaks mid-word ("Concent ration",
# "publicat ions"). That is the SAME failure the R1 manager edit recorded for
# seven tiles in one full-width row, at half the width. Four rows of two give
# each tile ~150 px (~118 px inside the border), which holds "Concentration" on
# one line -- so the grid is transposed, not the ruled column widths. Flip this
# constant back to 4 the day the middle column is wide enough (it already is at
# 1920 px, where four across measure ~146 px).
TILE_GRID_COLS = 2                     # 4 rows x 2 tiles (L30, transposed)
PROFILE_ROW1_WIDTHS = [1.0, 2.0, 1.4]  # identity | KPI tiles | wordcloud
PROFILE_ROW2_WIDTHS = [1, 1]           # global breakdown | yearly breakdown
CONTROLS_ROW_WIDTHS = [1, 1, 1, 2]     # depth | C1 | L7 | post-filters expander

SORT_VOLUME, SORT_TAXONOMY = "volume", "taxonomy"


# ------------------------------------------------------------- caches -------

@st.cache_resource
def _bundle() -> dict:
    """Everything computed once per process: the engine context plus the search
    index, umbrella flags/medians, catch-all shares, normalised names for the
    tail search, the domain-id -> name map the yearly breakdown needs, and the
    lightweight per-institution dict the post-filters run over (`lite` -- four
    keys, exactly what `filters.apply_filters` reads)."""
    idx = index()
    ctx = load_context(str(DATA_DIR))
    lite = {r.institution_id: {"institution_id": r.institution_id, "type": str(r.type),
                               "country_code": str(r.country_code),
                               "total_full_2020_2024": (None if pd.isna(r.total_full_2020_2024)
                                                        else float(r.total_full_2020_2024))}
            for r in idx.itertuples(index=False)}
    td = topics_dim()
    # R2/L31: the KPI baselines are one pass over the whole index, so they are
    # built HERE (inside the process-wide cache_resource) rather than per rerun.
    # `bonus_year_full` is the one DERIVED KPI -- `baselines.KPI_COLUMNS` holds
    # its parser, so the per-institution bonus-year count is read through the
    # same public spec the median is computed from, never re-parsed here.
    bonus_spec = baselines.KPI_COLUMNS["bonus_year_full"]
    bonus = bonus_spec(idx) if callable(bonus_spec) else idx[bonus_spec]
    return {"ctx": ctx, "index_df": idx, "lite": lite,
            "baselines": baselines.build(idx),
            "bonus_year_full": dict(zip(idx["institution_id"], bonus)),
            "search_idx": build_search_index(idx),
            "flags": umbrella_flags(idx), "medians": umbrella_medians(idx),
            "catchall": catchall_811_share(ctx),
            "norm_names": {i: normalize(n)
                           for i, n in zip(idx["institution_id"], idx["display_name"])},
            "domain_names": dict(zip(td["domain_id"], td["domain_name"])),
            "n_fields": int(td["field_id"].nunique())}


@st.cache_resource(max_entries=3)
def _subs(tree: str, basis: str) -> dict:
    """One (tree, basis) scenario's substrates. Bounded: three live at most."""
    return build_substrates(_bundle()["ctx"], tree, basis)


# ------------------------------------------------- profile frames (cached) --
# One @st.cache_data per S9.4 profile table, keyed on the HASHABLE scenario
# identity (iid, tree, basis) and fetching ctx/subs from the cache_resource
# above internally -- ctx and subs are unhashable, so they are never arguments.
# `st.expander` bodies execute on every rerun, so without these every collapsed
# panel would recompute its frame each time the user touched any control.

@st.cache_data(show_spinner=False, max_entries=24)
def _fields_frame(iid: str, tree: str, basis: str) -> pd.DataFrame:
    return profile_data.fields_table(_bundle()["ctx"], _subs(tree, basis), iid)


@st.cache_data(show_spinner=False, max_entries=24)
def _subfields_frame(iid: str, tree: str, basis: str) -> pd.DataFrame:
    return profile_data.subfields_table(_bundle()["ctx"], _subs(tree, basis), iid)


@st.cache_data(show_spinner=False, max_entries=12)
def _topics_frame(iid: str, tree: str, basis: str) -> pd.DataFrame:
    return profile_data.topics_table(_bundle()["ctx"], _subs(tree, basis), iid)


@st.cache_data(show_spinner=False, max_entries=24)
def _yearly_domain_frame(iid: str, tree: str) -> pd.DataFrame:
    """Basis-independent in its KEY: the frame carries both `vol_full` and
    `vol_frac`, and the caller picks the column the active basis names."""
    return profile_data.yearly_by_domain(_bundle()["ctx"], iid, tree)


@st.cache_data(show_spinner=False, max_entries=24)
def _yearly_doctype_frame(iid: str) -> pd.DataFrame:
    """The R1 doc-type artefact, sliced to one institution. Neither tree- nor
    basis-scoped: a document type has no taxonomy tree, and the table ships
    both bases (progress/R1_S5.md S9). `doc_type` is a CATEGORY dtype in the
    parquet -- cast to str here, once, so no downstream `.map()` ever meets a
    categorical (Assembly Line gotcha)."""
    df = doctype_by_year()
    out = df[df["institution_id"] == iid].copy()
    out["doc_type"] = out["doc_type"].astype(str)
    return out[["year", "doc_type", "vol_full", "vol_frac"]].reset_index(drop=True)


@st.cache_data(show_spinner=False, max_entries=24)
def _sdg_frame(iid: str) -> pd.DataFrame:
    return profile_data.sdg_table(_bundle()["ctx"], iid)


@st.cache_data(show_spinner=False, max_entries=24)
def _erc_frame(iid: str) -> pd.DataFrame:
    return profile_data.erc_table(_bundle()["ctx"], iid)


@st.cache_data(show_spinner=False, max_entries=24)
def _wordcloud_inputs(iid: str, tree: str, basis: str) -> tuple[dict, dict]:
    """`({subfield_name: weight}, {subfield_name: domain_id})` -- plain dicts,
    so `wordcloud_png.render_wordcloud_png` (itself cache_data) can hash them."""
    weights, domains = profile_data.wordcloud_weights(_bundle()["ctx"], _subs(tree, basis), iid)
    return {str(k): float(v) for k, v in weights.items()}, {str(k): v for k, v in domains.items()}


def _vol_col(basis: str) -> str:
    """The volume column the active counting basis names -- the gutter number,
    the wordcloud weight, the bubble area and the breakdown bars all read it."""
    return "vol_frac" if basis == "frac" else "vol_full"


# ------------------------------------------------------------- sidebar ------

def _sidebar_scenario() -> dict:
    """L16: the sidebar holds ONLY what is app-wide -- the scenario (tree x
    basis), which re-derives every shape on the page, profile panels included.
    Depth, C1, L7 and the post-filters moved to the controls row at the head of
    the Benchmark section; their widget KEYS are unchanged by the move, so
    cross-page persistence and the Playwright selectors survive it."""
    sb = st.sidebar
    sb.header(copy.FIND["SCENARIO_HEADER"])
    trees = CFG["scenario"]["toggles"]["tree"]
    # R2/L29: the OPTION stays the internal value (every frame, every cache key
    # and every export reads it); only its rendering changes, through
    # `format_func`. A reader never meets "bestfit" or "frac" on the page again.
    tree = sb.selectbox(copy.FIND["TREE_LABEL"], trees,
                        index=trees.index(CFG["scenario"]["tree_default"]),
                        format_func=lambda v: copy.TREE_LABELS[v],
                        help=copy.FIND["TREE_HELP"], key="tree", **state.PERSIST)
    bases = CFG["scenario"]["toggles"]["basis"]
    basis = sb.selectbox(copy.FIND["BASIS_LABEL"], bases,
                         index=bases.index(CFG["scenario"]["basis_default"]),
                         format_func=lambda v: copy.BASIS_LABELS[v],
                         help=copy.FIND["BASIS_HELP"], key="basis", **state.PERSIST)
    return {"tree": tree, "basis": basis}


def _strip_tree(tree: str) -> str:
    """The value `filters.active_controls_strip` should receive for `tree`.

    That function uses its `tree` argument for TWO jobs at once: the off-default
    TEST (against `CFG["scenario"]["tree_default"]`, an internal value) and the
    strip's own DISPLAY text (`copy.STRIP_TREE`). Handing it the display label
    unconditionally would make the test never match and pin the strip open at
    the defaults; handing it the internal value keeps "bestfit" on screen, which
    L29 removed everywhere else. So the internal value goes in when it IS the
    default (the only case the test reads it) and the display label otherwise
    (the only case the text is rendered). Splitting that argument in two belongs
    in `lib/filters.py`, another stream's file this wave."""
    default = CFG["scenario"]["tree_default"]
    return default if tree == default else copy.TREE_LABELS[tree]


def _hit_label(hits: list[dict], iid: str) -> str:
    """name . country . type . size -- VIZ_SPEC S2.1's candidate line, with the
    country by NAME since R1/L22."""
    h = next(x for x in hits if x["id"] == iid)
    total = h["total_full_2020_2024"]
    if total is None or pd.isna(total):
        size = NA_MARK
    else:
        size = f"{total:,.0f}"
    return (f"{h['display_name']} {SEP} {countries.name(h['country_code'])} {SEP} "
            f"{h['type']} {SEP} {size}")


def _sidebar_basket(bundle: dict) -> None:
    """VIZ_SPEC S1.3 / S2.9: the basket list, a remove control per item, a
    clear button, and the free-text "add a comparator" box. Stays in the
    sidebar under L16 -- the basket is app-wide, not a benchmark control."""
    sb, names = st.sidebar, bundle["ctx"]["index_by_id"]
    sb.header(copy.FIND["BASKET_HEADER"])
    items = state.items()
    if not items:
        sb.caption(copy.FIND["BASKET_EMPTY"])
    else:
        for iid in list(items):
            col_a, col_b = sb.columns([4, 1])
            col_a.write(str(names.loc[iid, "display_name"]))
            if col_b.button(copy.FIND["BASKET_REMOVE"], key=f"rm_{iid}"):
                state.remove(iid)
                st.rerun()
        if sb.button(copy.FIND["BASKET_CLEAR"], key="basket_clear"):
            state.clear()
            st.rerun()
    query = sb.text_input(copy.FIND["ADD_COMPARATOR_LABEL"], help=copy.ADD_COMPARATOR_HELP,
                          key="basket_query", **state.PERSIST)
    hits = search(query, bundle["search_idx"]) if query else []
    if query and not hits:
        sb.caption(copy.SEARCH_EMPTY_TEMPLATE.format(query=query))
    if hits:
        pick = sb.selectbox(copy.FIND["ADD_COMPARATOR_PICK"], [h["id"] for h in hits],
                            format_func=lambda i: _hit_label(hits, i), key="basket_pick")
        if sb.button(copy.FIND["ADD_COMPARATOR_BUTTON"], key="basket_add"):
            state.add(pick)
            st.rerun()


# ------------------------------------------------------- header + search ----

def _header(bundle: dict) -> None:
    """Title, the standing verdict line, and the snapshot stamp -- both label
    and figures computed from the deployed manifest (BUILD_PLAN_2A.md L11)."""
    st.title(copy.FIND["PAGE_TITLE"])
    st.caption(copy.FIND["PAGE_INTRO"])
    st.markdown(f"**{copy.VERDICT_LINE}**")
    mf = manifest()
    # ops/deploy.py writes `source_manifest_generated_at` / `deployed_at`; the
    # pre-staged source_manifest.json writes `generated_at`. Take whichever the
    # deployed file actually carries rather than showing NA_MARK for both.
    stamp = (mf.get("generated_at") or mf.get("source_manifest_generated_at")
             or mf.get("deployed_at") or NA_MARK)
    st.caption(copy.FIND["SNAPSHOT_CAPTION"].format(
        snapshot=mf.get("snapshot") or CFG["snapshot"], generated_at=stamp,
        n_institutions=f"{len(bundle['index_df']):,}", sep=SEP))


def _seed_search(bundle: dict) -> str | None:
    """VIZ_SPEC S2.1: search-first, no default listing. The chosen id lives in
    the plain (non-widget) session key `seed_id`, so it survives page hops."""
    query = st.text_input(copy.FIND["SEED_SEARCH_LABEL"], key="seed_query", **state.PERSIST)
    hits = search(query, bundle["search_idx"]) if query else []
    if query and not hits:
        st.info(copy.SEARCH_EMPTY_TEMPLATE.format(query=query))
    if hits:
        pick = st.selectbox(copy.FIND["SEED_PICK_LABEL"], [h["id"] for h in hits],
                            format_func=lambda i: _hit_label(hits, i), key="seed_pick")
        if pick:
            st.session_state["seed_id"] = pick
    return st.session_state.get("seed_id")


# ------------------------------------------------------------ formatting ----

def _pct(value) -> str:
    """One precision level per measure; NA_MARK for missing, never 0."""
    if value is None or pd.isna(value):
        return NA_MARK
    return f"{float(value):.1%}"


def _count(value) -> str:
    """Thousands separator; NA_MARK for missing (BUILD_PLAN_2A.md L11)."""
    if value is None or pd.isna(value):
        return NA_MARK
    return f"{float(value):,.0f}"


def _hhi(value) -> str:
    """The subfield HHI as the data ships it: a 0-10,000 scale (`index.parquet`
    min 88, max 7,454 -- data_contract.yaml), so one precision level for this
    measure is the integer, not three decimals."""
    if value is None or pd.isna(value):
        return NA_MARK
    return f"{float(value):,.0f}"


# ------------------------------------------------------------- profile ------

def _profile_identity(card: dict, row, bundle: dict) -> None:
    """VIZ_SPEC S2.10: name, "type . city, COUNTRY NAME", the two seed-level
    badges (mutually exclusive by `badges.badges_for`'s own assertion), then
    the link row. A missing city / ROR / homepage drops silently; a missing
    type renders NA_MARK, never a blank or a guess."""
    st.subheader(str(card["display_name"]))
    country = countries.name(str(card["country_code"]))
    city = row.get("city")
    if isinstance(city, str) and city:
        place = f"{city}, {country}"
    else:
        place = country
    kind = str(card["type"]) if card["type"] else NA_MARK
    st.caption(f"{kind} {SEP} {place}")

    labels = badges_for(card, bundle["flags"], bundle["medians"])
    if labels:
        med = bundle["medians"].get((str(card["country_code"]), str(card["type"])))
        if med is None:
            tip = copy.UMBRELLA_TOOLTIP.format(median=NA_MARK)
        else:
            tip = copy.UMBRELLA_TOOLTIP.format(median=f"{med:,.0f}")
        st.markdown(f" {SEP} ".join(labels), help=tip)

    # L23: the works link carries the harvest's OWN server-side filters, so it
    # counts the corpus the app counted -- give or take live-vs-snapshot drift,
    # which the tooltip discloses (measured 0.99907-1.00023 on six seeds,
    # progress/R1_B.md) rather than hiding.
    #
    # R2/L29: that link is now labelled by what it ANSWERS ("what counts as a
    # publication") rather than by where it points, and the whole row carries
    # the corpus definition as its tooltip -- stated ONCE for the section, so
    # every tile and panel beneath can say "publications" without re-explaining
    # document types, the DOI requirement or the bonus year. The drift sentence
    # is appended, not dropped: it is the ratified fix for gate-2A bug #9.
    parts = [f"[{copy.FIND['PUBLICATIONS_LINK_LABEL']}]"
             f"({links.works_url(card['institution_id'])})"]
    ror = row.get("ror_id")
    if isinstance(ror, str) and ror:
        parts.append(f"[{copy.FIND['LINK_ROR']}]({links.ror_url(ror)})")
    home = row.get("homepage_url")
    if isinstance(home, str) and home:
        parts.append(f"[{copy.FIND['LINK_HOMEPAGE']}]({home})")
    tooltip = copy.FIND["PUBLICATIONS_TOOLTIP"].format(
        y0=WINDOW_START, y1=WINDOW_END, bonus_year=CFG["bonus_year"], dash=DASH, sep=SEP)
    st.markdown(f" {SEP} ".join(parts),
                help=f"{tooltip} {copy.FIND['LINK_OPENALEX_HELP']}")


def _baseline_sub(bundle: dict, kpi: str, value, fmt) -> str:
    """R2/L31: the tile's SECOND subline, positioning the value in the index --
    "index median {m} . higher than {pct} of institutions". The median is
    formatted by the tile's OWN formatter, so a share reads as a share and a
    count as a count; a null value keeps the median visible and marks its own
    position NA_MARK (`baselines.percentile` returns None there), because a
    missing measure has no percentile but the reference still exists."""
    ref = baselines.stats(bundle["baselines"], kpi)
    pct = baselines.percentile(bundle["baselines"], kpi, value)
    if pct is None:
        pct_text = NA_MARK
    else:
        pct_text = f"{pct:.0%}"
    return copy.FIND["TILE_BASELINE_SUB"].format(median=fmt(ref["median"]), pct=pct_text, sep=SEP)


def _tile_specs(card: dict, row, bundle: dict) -> list[tuple]:
    """(baseline key, label, value, formatter, own subline) x 8, in the FIXED
    order of `baselines.KPI_COLUMNS` (VIZ_SPEC S2.11): size full, size
    fractional, concentration, breadth, SDG-tagged share, frontier top-quartile
    share, PP(top10%), publications in the bonus year.

    The concentration tile carries NO class word (R2/L32: `hhi_class`'s
    textbook thresholds called 86 % of the index "generalist", which is not a
    distinction) -- the index percentile in the baseline subline is what
    positions it now."""
    iid = card["institution_id"]
    return [
        ("total_full_2020_2024", copy.FIND["TILE_SIZE_FULL"],
         card["total_full_2020_2024"], _count,
         copy.FIND["TILE_SIZE_FULL_SUB"].format(y0=WINDOW_START, y1=WINDOW_END, dash=DASH)),
        ("total_frac_2020_2024", copy.FIND["TILE_SIZE_FRAC"],
         card["total_frac_2020_2024"], _count,
         copy.FIND["TILE_SIZE_FRAC_SUB"]),
        ("hhi_subfield", copy.FIND["TILE_HHI"],
         card["hhi_subfield"], _hhi,
         copy.FIND["TILE_HHI_SUB"]),
        ("breadth_subfields", copy.FIND["TILE_BREADTH"],
         card["breadth_subfields"], _count,
         copy.FIND["TILE_BREADTH_SUB"].format(floor=CFG["g6_floor"])),
        ("sdg_tagged_share", copy.FIND["TILE_SDG"],
         card["sdg_tagged_share"], _pct,
         copy.FIND["TILE_SDG_SUB"]),
        ("frontier_top25_share", copy.FIND["TILE_FRONTIER"],
         card["frontier_top25_share_index"], _pct,
         copy.FIND["TILE_FRONTIER_SUB"]),
        ("pp_top10_frac", copy.FIND["TILE_PP"],
         row["pp_top10_frac"], _pct,
         copy.FIND["TILE_PP_SUB"].format(lo=_pct(row["pp_ci_low"]),
                                         hi=_pct(row["pp_ci_high"]), dash=DASH)),
        ("bonus_year_full", copy.FIND["TILE_BONUS_YEAR"].format(year=CFG["bonus_year"]),
         bundle["bonus_year_full"].get(iid), _count,
         copy.FIND["TILE_BONUS_YEAR_SUB"]),
    ]


def _profile_tiles(card: dict, row, bundle: dict) -> None:
    """VIZ_SPEC S2.11 / L30 / L31: EIGHT tiles in a 2 x 4 grid filling column 2
    of the profile's row 1, each `value + label + its own subline + the index
    baseline`. `n/a` for anything the data cannot support -- never 0, never a
    hidden tile.

    A grid rather than one row of eight, at TILE_GRID_COLS per row: see that
    constant for the 1280 px measurement that fixes its value. Streamlit stacks
    every row one-tile-per-line below its own small breakpoint, so 390 px needs
    no media query."""
    st.markdown(f"**{copy.FIND['TILES_HEADER']}**", help=copy.FIND["BASELINE_HELP"])
    cols = []
    for _ in range(N_TILES // TILE_GRID_COLS):
        cols.extend(st.columns(TILE_GRID_COLS))
    for col, (kpi, label, value, fmt, subline) in zip(cols, _tile_specs(card, row, bundle)):
        tiles.kpi_tile(col, label, fmt(value), subline, _baseline_sub(bundle, kpi, value, fmt))


def _erc_share(card: dict, row) -> float | None:
    """The ERC-classified share the ERC panel caption reports (R2/L30 moved it
    off the retired coverage line). A RATIO of two card fields, computed once so
    the caption reads a value rather than an expression.

    Manager edit 2026-08-29 (E2 needs_change #1): the numerator is on the
    WHOLE-RUN mass basis (2020-2025), so its denominator must be the whole-run
    `total_frac`, not the 2020-2024 window (which printed 109.1 % for
    Strasbourg). `data_contract.yaml` index.erc_classified_mass_frac carries the
    corrected formula."""
    erc, tot = card["erc_classified_mass_frac"], row.get("total_frac")
    if erc is None or tot is None or pd.isna(tot) or float(tot) <= 0:
        return None
    return erc / float(tot)


def _profile_wordcloud(iid: str, ctl: dict) -> None:
    """VIZ_SPEC S2.13 / R2 L30: a raster in COLUMN 3 of the profile's row 1,
    beside the tiles it illustrates rather than beside the breakdown pair it was
    never related to. Size = publications on the current basis, colour = domain
    -- both stated in the caption, because a wordcloud whose size channel is
    unstated is a decoration."""
    weights, domains = _wordcloud_inputs(iid, ctl["tree"], ctl["basis"])
    png = render_wordcloud_png(weights, domains)
    if png is None:
        st.caption(copy.FIND["WORDCLOUD_EMPTY"])
        return
    st.image(png, width="stretch")
    st.caption(copy.FIND["WORDCLOUD_CAPTION"].format(sep=SEP))


def _domain_series(iid: str, ctl: dict, bundle: dict, years: list[int]):
    """(series keys, labels, colours, per-year totals) for the DOMAIN view.
    Fixed family order (`palette.OA_DOMAIN_ORDER`) plus the explicit
    "Unclassified" residual (`profile_data.UNCLASSIFIED_DOMAIN_ID`, the works
    that carry no primary topic) so this view and the document-type view sum to
    the same yearly totals -- the whole point of putting them on one control."""
    df = _yearly_domain_frame(iid, ctl["tree"])
    col = _vol_col(ctl["basis"])
    keys = [*P.OA_DOMAIN_ORDER, profile_data.UNCLASSIFIED_DOMAIN_ID]
    labels, colors, totals = {}, {}, {}
    by_key = {int(k): g for k, g in df.groupby("domain_id")}
    for k in keys:
        g = by_key.get(int(k))
        if k == profile_data.UNCLASSIFIED_DOMAIN_ID:
            labels[k] = copy.FIND["UNCLASSIFIED_LABEL"]
        else:
            labels[k] = str(bundle["domain_names"].get(k, k))
        colors[k] = P.domain_color(k)
        per_year = {} if g is None else dict(zip(g["year"], g[col]))
        totals[k] = [float(per_year.get(y, 0.0)) for y in years]
    return keys, labels, colors, totals


def _doctype_series(iid: str, ctl: dict, years: list[int]):
    """Same shape for the DOCUMENT-TYPE view, from the R1 artefact. Returns
    `None` when the institution has no doc-type rows at all, so the caller can
    disclose the fallback to the domain view instead of showing an empty pair
    (VIZ_SPEC S2.14 empty state)."""
    df = _yearly_doctype_frame(iid)
    if df.empty:
        return None
    col = _vol_col(ctl["basis"])
    keys = list(P.DOCTYPE_ORDER)
    labels = {k: P.DOCTYPE_LABELS.get(k, k) for k in keys}
    colors = {k: P.doctype_color(k) for k in keys}
    by_key = {str(k): g for k, g in df.groupby("doc_type")}
    totals = {}
    for k in keys:
        g = by_key.get(str(k))
        per_year = {} if g is None else dict(zip(g["year"], g[col]))
        totals[k] = [float(per_year.get(y, 0.0)) for y in years]
    return keys, labels, colors, totals


def _profile_breakdown(iid: str, ctl: dict, bundle: dict) -> None:
    """VIZ_SPEC S2.14: ONE segmented control swapping the identity family for
    BOTH figures, ONE shared chip legend, grouped bars (never stacked), years
    as strings. The two figures can never disagree because one control drives
    them both."""
    st.segmented_control(
        copy.FIND["BREAKDOWN_CONTROL_LABEL"],
        [copy.FIND["BREAKDOWN_DOMAIN"], copy.FIND["BREAKDOWN_DOCTYPE"]],
        default=copy.FIND["BREAKDOWN_DOMAIN"], required=True,
        key="breakdown_dim", **state.PERSIST)
    pick = st.session_state.get("breakdown_dim") or copy.FIND["BREAKDOWN_DOMAIN"]

    years = sorted(int(y) for y in _yearly_domain_frame(iid, ctl["tree"])["year"].unique())
    if not years:
        st.caption(copy.FIND["PANEL_EMPTY"])
        return
    built = None
    if pick == copy.FIND["BREAKDOWN_DOCTYPE"]:
        built = _doctype_series(iid, ctl, years)
        if built is None:
            st.caption(copy.FIND["BREAKDOWN_DOCTYPE_MISSING"])
    if built is None:
        built = _domain_series(iid, ctl, bundle, years)
    keys, labels, colors, totals = built

    legend = [(labels[k], colors[k]) for k in keys]
    st.markdown(charts.chip_legend_html(legend), unsafe_allow_html=True)
    # R2/L30 reverses R1's stacking. R1 put the two figures one above the other
    # because this pair shared its row with the wordcloud, which left each
    # sub-column ~260 px of plot at 1280 px -- a width at which category labels
    # clip and value ticks rotate to vertical. The wordcloud has moved up into
    # row 1, so the pair now owns the FULL section width and each panel gets
    # ~600 px, comfortably past that failure point; side by side is what the
    # Lorraine lab card does and what makes the two reads comparable at a
    # glance. Streamlit stacks the two columns anyway below its own small
    # breakpoint, so the 390 px behaviour is exactly R1's.
    left, right = st.columns(PROFILE_ROW2_WIDTHS)
    with left:
        st.markdown(f"**{copy.FIND['BREAKDOWN_GLOBAL_TITLE']}**")
        st.plotly_chart(
            charts.fig_breakdown_global([labels[k] for k in keys],
                                        [sum(totals[k]) for k in keys],
                                        [colors[k] for k in keys]),
            width="stretch", key="fig_breakdown_global")
    with right:
        st.markdown(f"**{copy.FIND['BREAKDOWN_YEARLY_TITLE']}**")
        st.plotly_chart(
            charts.fig_breakdown_yearly([str(y) for y in years], keys, labels, colors, totals),
            width="stretch", key="fig_breakdown_yearly")
    st.caption(copy.FIND["BONUS_YEAR_CAPTION"].format(year=CFG["bonus_year"]))


# ---------------------------------------------------------- chart panels ----

def _sort_control(panel: str, default: str = SORT_VOLUME) -> str:
    """The shared sort toggle (L20). Colour follows the entity, never the rank,
    so the toggle never repaints anything -- `tests/test_charts.py` pins that."""
    options = [copy.FIND["SORT_VOLUME"], copy.FIND["SORT_TAXONOMY"]]
    idx = 0 if default == SORT_VOLUME else 1
    picked = st.radio(copy.FIND["SORT_LABEL"], options, index=idx, horizontal=True,
                      key=f"sort_{panel}", **state.PERSIST)
    return SORT_VOLUME if picked == copy.FIND["SORT_VOLUME"] else SORT_TAXONOMY


def _panel_fields(iid: str, ctl: dict, card: dict) -> None:
    """VIZ_SPEC S2.15: one row per field, coloured by its DOMAIN, share bars +
    SI lollipops. No SI floor at field grain (the G6 floor is a subfield rule
    -- the data contract says so on both rows)."""
    df = _fields_frame(iid, ctl["tree"], ctl["basis"])
    if df.empty:
        st.caption(copy.FIND["PANEL_EMPTY"])
        return
    sort = _sort_control("fields")
    st.plotly_chart(charts.fig_share_si(df, family="oa", sort=sort, label_col="field_name",
                                        volume_col=_vol_col(ctl["basis"])),
                    width="stretch", key="fig_fields")
    st.caption(copy.FIND["CAPTION_SI"])


def _panel_subfields(iid: str, ctl: dict, card: dict) -> None:
    """VIZ_SPEC S2.16 / R2 L34: the top SUBFIELDS_TOP_N subfields by volume on
    the current basis, and NO sort toggle -- "top 30" is itself a volume-ordered
    concept, so a taxonomy re-sort of it would read as an arbitrary 30 rows in
    ID order. The SI mark is solid at or above the solid floor, hollow between
    the two floors and absent below the thin one; `charts.fig_share_si` reads
    that off the frame's own `si_status` column, and the floors are printed from
    `profile_data`'s constants, the ONE place those numbers are typed."""
    df = _subfields_frame(iid, ctl["tree"], ctl["basis"])
    if df.empty:
        st.caption(copy.FIND["PANEL_EMPTY"])
        return
    vol = _vol_col(ctl["basis"])
    top = df.nlargest(SUBFIELDS_TOP_N, vol)
    st.plotly_chart(charts.fig_share_si(top, family="oa", sort=SORT_VOLUME,
                                        label_col="subfield_name", volume_col=vol),
                    width="stretch", key="fig_subfields")
    st.caption(copy.FIND["CAPTION_TOP_N_VOLUME"].format(n=f"{len(top):,}"))
    st.caption(copy.FIND["CAPTION_SI"])
    st.caption(copy.FIND["CAPTION_SI_FLOOR"].format(
        floor_solid=int(profile_data.SI_FLOOR_SOLID),
        floor_thin=int(profile_data.SI_FLOOR_THIN)))


def _panel_topics(iid: str, ctl: dict, card: dict) -> None:
    """VIZ_SPEC S2.17: the top topics by share. A catch-all (out-of-scope, 811)
    topic is FLAGGED and COUNTED, never dropped -- its presence is exactly what
    a reader needs in order to discount every other number in the section."""
    df = _topics_frame(iid, ctl["tree"], ctl["basis"])
    if df.empty:
        st.caption(copy.FIND["PANEL_EMPTY"])
        return
    sort = _sort_control("topics")
    top = df.nlargest(TOPICS_TOP_N, "share")
    st.plotly_chart(charts.fig_topics(top, sort=sort, volume_col=_vol_col(ctl["basis"])),
                    width="stretch", key="fig_topics")
    st.caption(copy.FIND["CAPTION_TOP_N_SHARE"].format(n=f"{len(top):,}"))
    # R2/L30: the seed's catch-all SHARE moved off the retired coverage line
    # into this caption, which already counted the flagged rows from the data --
    # a caveat is read where the rows it qualifies are on screen.
    st.caption(copy.FIND["CAPTION_TOPICS_CATCHALL"].format(
        n=f"{int(top['is_excluded'].fillna(False).sum()):,}", glyph=charts.EXCLUDED_GLYPH,
        catchall=_pct(card["catchall_811_share"])))


def _frontier_modes() -> tuple[str, str]:
    """The two L33 mode labels, built once so the control, the default and the
    comparison below all read the same strings."""
    return (copy.FIND["FRONTIER_MODE_TOP"].format(n=FRONTIER_TOP_N),
            copy.FIND["FRONTIER_MODE_EMERGING"])


def _panel_frontier(iid: str, ctl: dict, card: dict) -> None:
    """VIZ_SPEC S2.18 / R2 L33: Expansion x Acceleration, bubble area = volume
    on the current basis, colour = domain, an INK outline on a top-quartile
    topic. TWO modes behind one segmented control, each handing `fig_frontier` a
    pre-filtered frame (the builder never learns which mode produced its input):
    the seed's biggest FRONTIER_TOP_N topics by volume, or every topic in the
    global top quartile of emergence -- NOT a subset of the first, since a topic
    can be small and highly emergent or large and static.

    Topics that cannot be PLACED (unscored on either axis) or that are
    out-of-scope are dropped and COUNTED in the caption, mode-independently:
    that count is a fact about the seed's topic set, not about the cut on
    screen, while the count SHOWN is the mode's own."""
    df = _topics_frame(iid, ctl["tree"], ctl["basis"])
    if df.empty:
        st.caption(copy.FIND["PANEL_EMPTY"])
        return
    mode_top, mode_emerging = _frontier_modes()
    st.segmented_control(copy.FIND["FRONTIER_MODE_LABEL"], [mode_top, mode_emerging],
                         default=mode_top, required=True, key="frontier_mode", **state.PERSIST)
    pick = st.session_state.get("frontier_mode") or mode_top

    placeable = (df["frontier_score_latest"].notna() & df["expansion_latest"].notna()
                 & df["acceleration_latest"].notna())
    scored = placeable & ~df["is_excluded"].fillna(False)
    if pick == mode_emerging:
        keep = scored & df["top25pct_frontier"].fillna(False)
    else:
        keep = scored & (df["rank_volume"] <= FRONTIER_TOP_N)
    subset = df[keep]
    if subset.empty:
        st.caption(copy.FIND["FRONTIER_EMPTY"])
    else:
        st.plotly_chart(charts.fig_frontier(subset, size_col=_vol_col(ctl["basis"])),
                        width="stretch", key="fig_frontier")
    st.caption(copy.FIND["CAPTION_FRONTIER"].format(
        n_shown=f"{len(subset):,}", n_excluded=f"{int((~scored).sum()):,}"))


def _panel_sdg(iid: str, ctl: dict, card: dict) -> None:
    """VIZ_SPEC S2.19: sixteen bars in FIXED goal order (the one panel with no
    sort toggle -- the SDG numbers are a canonical sequence a reader navigates
    by position), official UN colours, ESI in the SI slot."""
    df = _sdg_frame(iid)
    if df.empty:
        st.caption(copy.FIND["PANEL_EMPTY"])
        return
    st.plotly_chart(charts.fig_sdg(df), width="stretch", key="fig_sdg")
    st.caption(copy.FIND["CAPTION_SDG"].format(
        n_missing=", ".join(str(n) for n in P.SDG_UNCOVERED)))
    if ctl["basis"] == "full":
        st.caption(copy.FIND["FRACTIONAL_ONLY_PANEL"])


def _panel_erc(iid: str, ctl: dict, card: dict) -> None:
    """VIZ_SPEC S2.20: one row per ERC evaluation panel, coloured by its ERC
    DOMAIN (three hues that share nothing with the OpenAlex four -- a different
    taxonomy of the same output), grouped PE -> LS -> SH under the taxonomy
    sort, which is this panel's default."""
    df = _erc_frame(iid)
    if df.empty:
        st.caption(copy.FIND["PANEL_EMPTY"])
        return
    sort = _sort_control("erc", default=SORT_TAXONOMY)
    st.plotly_chart(charts.fig_erc(df, sort=sort), width="stretch", key="fig_erc")
    st.caption(copy.FIND["CAPTION_SI"])
    # R2/L30: the ERC-classified share moved off the retired coverage line into
    # this caption, where the panel it qualifies is on screen.
    st.caption(copy.FIND["CAPTION_ERC"].format(n_panels=f"{len(df):,}",
                                               erc_share=_pct(card.get("_erc_share"))))
    if ctl["basis"] == "full":
        st.caption(copy.FIND["FRACTIONAL_ONLY_PANEL"])


# The six panels of VIZ_SPEC S1.9 block 5, in their fixed order. The key is
# BOTH the expander's session-state key and the widget key suffix.
#
# A panel whose TITLE states its own cut takes its arguments from here rather
# than typing the number into copy.py (L10): R2/L34's "Top {n} subfields" is the
# only such title today.
PANEL_LABEL_ARGS = {"subfields": {"n": SUBFIELDS_TOP_N}}

PANELS = (
    ("fields", "PANEL_FIELDS", _panel_fields),
    ("subfields", "PANEL_SUBFIELDS", _panel_subfields),
    ("topics", "PANEL_TOPICS", _panel_topics),
    ("frontier", "PANEL_FRONTIER", _panel_frontier),
    ("sdg", "PANEL_SDG", _panel_sdg),
    ("erc", "PANEL_ERC", _panel_erc),
)


def _profile_panels(iid: str, ctl: dict, card: dict) -> None:
    """The six panels are COLLAPSED by default (VIZ_SPEC S1.9) but their bodies
    run every rerun -- `st.expander` folds the display, never the execution.

    A lazy gate was built and REJECTED on a measurement (progress/R1_E2.md,
    verify-before-building item b): Streamlit 1.61.1's `st.expander` does take
    a `key=` and does publish its open/closed state into `st.session_state`,
    but that state RESETS to the coded `expanded=` on the very next rerun, so
    a body gated on it would blank itself the moment the reader touched any
    other control. Rendering all six unconditionally costs a measured 0.88 s
    warm on the largest seed tested, inside the 1.5 s budget, so the panels are
    always built and the `key=` is kept only as a stable DOM hook
    (`.st-key-panel_<name>`) for the probe."""
    for name, copy_key, body in PANELS:
        label = copy.FIND[copy_key].format(**PANEL_LABEL_ARGS.get(name, {}))
        with st.expander(label, expanded=False, key=f"panel_{name}"):
            body(iid, ctl, card)


def _render_profile(bundle: dict, subs: dict, seed_id: str, ctl: dict) -> dict:
    """VIZ_SPEC S1.9 / L30 -- the Lorraine lab card's grid. Row 1 in three
    columns (identity | eight KPI tiles | wordcloud), row 2 full width (one
    control and one chip legend above the breakdown pair), then the six
    collapsed panels. Returns the seed card, which the L2f tab intro and the
    export path both read after the profile has rendered."""
    ctx = bundle["ctx"]
    card = seed_card(ctx, seed_id, subs, bundle["catchall"])
    row = ctx["index_by_id"].loc[seed_id]
    card["_erc_share"] = _erc_share(card, row)
    st.header(copy.FIND["PROFILE_HEADER"])
    with st.container(border=True, key="profile"):
        c_identity, c_tiles, c_cloud = st.columns(PROFILE_ROW1_WIDTHS)
        with c_identity:
            _profile_identity(card, row, bundle)
        with c_tiles:
            _profile_tiles(card, row, bundle)
        with c_cloud:
            _profile_wordcloud(seed_id, ctl)
        _profile_breakdown(seed_id, ctl, bundle)
        _profile_panels(seed_id, ctl, card)
    return card


# --------------------------------------------------------- controls row -----

def _same_country_share(rankings: dict, ctx: dict, seed_row, depth: int) -> str:
    """The live figure copy.L3_COUNTRY_TOOLTIP asks for: the share of L3's own
    visible candidates sitting in the seed's country. NA_MARK when L3 is
    undefined -- never a typed number, never 0 (BUILD_PLAN_2A.md L11)."""
    r = rankings.get("L3")
    if r is None or r["undefined"] or not r["sorted_ids"]:
        return NA_MARK
    ids, _ = cut_with_ties(r["sorted_ids"], r["sorted_scores"], depth)
    own = str(seed_row["country_code"])
    same = sum(1 for i in ids if str(ctx["index_by_id"].loc[i, "country_code"]) == own)
    return f"{same / len(ids):.0%}"


def _post_filters(bundle: dict, rankings: dict, seed_row, depth: int) -> dict:
    """L16/L6: every post-filter opt-in and off by default, moved out of the
    sidebar into the controls row's expander with its widget KEYS unchanged.
    Rendered after the rankings exist so the same-country tooltip carries a
    computed share. Returns exactly `filters.apply_filters`' keyword set."""
    idx = bundle["index_df"]
    st.caption(copy.FIND["FILTERS_HELP"])
    types = st.multiselect(copy.FIND["TYPE_LABEL"], sorted(idx["type"].astype(str).unique()),
                           default=[], key="f_types", **state.PERSIST)
    # Options stay the CODES (the value `apply_filters` matches on), displayed
    # and ordered by their English name -- R1/L22.
    codes = sorted(idx["country_code"].astype(str).unique(), key=countries.name)
    picked = st.multiselect(copy.FIND["COUNTRY_LABEL"], codes, default=[],
                            format_func=countries.name, key="f_countries", **state.PERSIST)
    excl = st.checkbox(copy.FIND["EXCLUDE_OWN_LABEL"], value=False,
                       help=copy.L3_COUNTRY_TOOLTIP.format(
                           share=_same_country_share(rankings, bundle["ctx"], seed_row, depth)),
                       key="f_excl_own", **state.PERSIST)
    lo_all = int(np.floor(idx["total_full_2020_2024"].min()))
    hi_all = int(np.ceil(idx["total_full_2020_2024"].max()))
    lo, hi = st.slider(copy.FIND["SIZE_LABEL"], lo_all, hi_all, (lo_all, hi_all),
                       key="f_size", **state.PERSIST)
    guard = st.checkbox(copy.FIND["SCALE_GUARD_LABEL"], value=False,
                        help=copy.FIND["SCALE_GUARD_HELP"], key="f_guard", **state.PERSIST)
    thr = CFG["family_filter_threshold"]
    fam = st.checkbox(copy.FIND["FAMILY_LABEL"], value=False,
                      help=copy.FIND["FAMILY_HELP"].format(threshold=thr),
                      key="f_family", **state.PERSIST)
    narrowed = (lo, hi) != (lo_all, hi_all)
    return {"types": types or None, "countries": picked or None, "exclude_own_country": excl,
            "size_range": (lo, hi) if narrowed else None, "scale_guard": guard,
            "family_min": thr if fam else None}


def _controls_row(bundle: dict, rankings: dict, seed_row) -> tuple[dict, dict]:
    """L16 / VIZ_SPEC S2.21: the head of the Benchmark section. Depth, C1 and
    L7 are ORDINARY controls a reader touches on a first visit, so they sit in
    the open; the six post-filters are the advanced ones and live one click
    down, in a collapsed expander whose body still EXECUTES every rerun (its
    widgets must register). Each control carries a `help=` that explains what
    the option DOES -- the gate-2A complaint was a sidebar that named options
    without explaining them."""
    st.header(copy.FIND["BENCHMARK_HEADER"])
    st.caption(copy.FIND["BENCHMARK_INTRO"])
    c_depth, c_c1, c_l7, c_filters = st.columns(CONTROLS_ROW_WIDTHS)
    with c_depth:
        depth = st.radio(copy.FIND["DEPTH_LABEL"], DEPTH_OPTIONS, index=0, horizontal=True,
                         help=copy.FIND["DEPTH_HELP"], key="depth", **state.PERSIST)
    with c_c1:
        c1_on = st.checkbox(copy.C1_TOGGLE_LABEL, value=False,
                            help=copy.FIND["C1_HELP"].format(core_top_n=CORE_TOP_N),
                            key="c1_on", **state.PERSIST)
    with c_l7:
        l7_on = st.checkbox(copy.L7_TOGGLE_LABEL, value=False, help=copy.FIND["L7_HELP"],
                            key="l7_on", **state.PERSIST)
    with c_filters:
        with st.expander(copy.FIND["POSTFILTERS_EXPANDER"], expanded=False, key="postfilters"):
            filters = _post_filters(bundle, rankings, seed_row, int(depth))
    return {"depth": int(depth), "c1_on": c1_on, "l7_on": l7_on}, filters


# --------------------------------------------------- rows, filters, rank ----

def _rows_for_ids(ranking: dict, ctx: dict, ids: list, scores, rankings: dict | None,
                  subs: dict | None = None) -> list[dict]:
    """`engine.build_rows` over an explicit id subset, with the ORIGINAL
    competition rank restored from the unfiltered ranking's `rmap` (post-filters
    remove rows, they never renumber -- BUILD_PLAN_2A.md L6/VIZ_SPEC S1.7).
    `subs` is forwarded so every row's `shape_top3_fields` follows the active
    tree x basis (R1 bug #5)."""
    if not ids:
        return []
    sub = dict(ranking)
    sub["sorted_ids"] = list(ids)
    sub["sorted_scores"] = np.asarray(scores)
    rows = build_rows(sub, ctx, len(ids), rankings, subs)
    for r in rows:
        r["rank"] = ranking["rmap"][r["institution_id"]]
    return rows


def _with_evidence(rows: list[dict], ctx: dict, subs: dict, lens: str, seed_id: str) -> list[dict]:
    """L21: the lens-specific evidence cell -- the top shared cell for THAT
    lens, labelled in that lens's own namespace -- attached to the rows the
    table is about to render. Computed for the VISIBLE ids only, never over the
    whole population (S9.4 contract); `ranked.format_rows` and
    `exports.ranking_csv` both read `row["evidence_text"]`."""
    if not rows:
        return rows
    texts = rows_evidence(ctx, subs, lens, seed_id, [r["institution_id"] for r in rows])
    for r in rows:
        r["evidence_text"] = texts.get(r["institution_id"])
    return rows


def _cross_lens(rankings: dict) -> dict | None:
    """`build_rows`' optional L1/L3 cross-reference, only when both are defined
    (an undefined ranking carries `scores=None`, which that path would crash on)."""
    ok = all(ln in rankings and not rankings[ln]["undefined"] for ln in ("L1", "L3"))
    if ok:
        return rankings
    return None


def _filtered(ranking: dict, bundle: dict, filters: dict, seed_row, family_scores):
    """Post-filters on the FULL ranking, evaluated over the lightweight row
    dicts (`lite`) so nothing pays `build_rows` for rows nobody will see."""
    lite = bundle["lite"]
    rows = [lite[i] for i in ranking["sorted_ids"] if i in lite]
    kept = apply_filters(rows, seed_row=seed_row, family_scores=family_scores, **filters)
    kept_ids = [r["institution_id"] for r in kept]
    by_id = dict(zip(ranking["sorted_ids"], ranking["sorted_scores"]))
    return kept_ids, [by_id[i] for i in kept_ids]


def _family_scores(bundle: dict, subs: dict, seed_id: str, filters: dict) -> dict | None:
    """L0 field-grain scores, computed only when the opt-in family filter asks."""
    if filters["family_min"] is None:
        return None
    ctx = bundle["ctx"]
    return dict(zip(ctx["inst_ids"], family_overlap_scores(ctx, subs, seed_id)))


# ------------------------------------------------------------- lens tab -----

def _gloss_values(bundle: dict) -> dict:
    """Every placeholder copy.LENS_GLOSS/LENS_CAVEAT can ask for, filled from
    CFG, the engine's own constants and the live data -- never typed."""
    return {"n_fields": bundle["n_fields"], "n_named_lenses": len(ALL_LENSES),
            "n_default_lenses": len(CFG["lenses"]["default"]),
            "floor_papers": CFG["l2f_floor"]["value"], "core_top_n": CORE_TOP_N,
            "depth_max": CFG["depth"]["max"]}


def _lens_intro(lens: str, ranking: dict, subs: dict, basis: str, bundle: dict,
                card: dict) -> None:
    """Gloss + caveat + this seed's evidence line + the basis disclosure, all
    above the table and never tooltip-only (VIZ_SPEC S2.4). R2/L30 adds the
    L2f-eligible cell count here, on the L2f tab and nowhere else: it is a
    precondition for THAT lens's ranking, so a reader meets it on the tab whose
    list it explains rather than in the profile's retired coverage line."""
    vals = _gloss_values(bundle)
    st.markdown(f"**{copy.LENS_GLOSS[lens].format(**vals)}**")
    st.caption(copy.LENS_CAVEAT[lens].format(**vals))
    if lens == "L2f":
        st.caption(copy.FIND["EV_L2F"].format(
            value=f"{card['n_eligible_subfields_L2f']:,}"))
    ev = {k: v for k, v in (ranking.get("evidence") or {}).items() if isinstance(v, (int, float))}
    if ev:
        text = "; ".join(f"{k.replace('_', ' ')}: {v:,.3f}" for k, v in ev.items())
        st.caption(copy.FIND["EVIDENCE_LABEL"].format(text=text, sep=SEP))
    else:
        st.caption(copy.FIND["EV_NONE"])
    if basis == "full" and not subs["basis_applies"][lens]:
        st.caption(copy.FIND["BASIS_DISCLOSURE"])


def _tail_and_export(lens: str, ranking: dict, bundle: dict, subs: dict, kept,
                     ctx_bits: dict) -> None:
    """VIZ_SPEC S2.7: search scoped to the FULL filtered ranking, and the CSV of
    that same full ranking -- generated lazily on click (Streamlit 1.61 accepts
    a zero-arg callable for `data`), so no rerun ever pays for rows nobody
    downloads. Both paths carry the lens-specific evidence."""
    kept_ids, kept_scores = kept
    ctx, norm = bundle["ctx"], bundle["norm_names"]
    seed_id = ranking["seed_id"]
    query = st.text_input(copy.FIND["TAIL_SEARCH_LABEL"], key=f"tail_{lens}", **state.PERSIST)
    if query:
        q = normalize(query)
        hits = [(i, s) for i, s in zip(kept_ids, kept_scores) if q in norm.get(i, "")]
        if not hits:
            st.caption(copy.TAIL_SEARCH_EMPTY_TEMPLATE.format(query=query))
        else:
            rows = _rows_for_ids(ranking, ctx, [h[0] for h in hits], [h[1] for h in hits],
                                 ctx_bits["cross"], subs)
            _with_evidence(rows, ctx, subs, lens, seed_id)
            st.caption(copy.FIND["TAIL_CAPTION"])
            render_ranked_table(format_rows(rows, lens=lens, depth=len(rows)),
                                key=f"tailtbl_{lens}")

    def _csv() -> bytes:
        rows = _rows_for_ids(ranking, ctx, kept_ids, kept_scores, ctx_bits["cross"], subs)
        _with_evidence(rows, ctx, subs, lens, seed_id)
        return ranking_csv(rows, seed_id=seed_id, lens=lens, tree=ctx_bits["tree"],
                           basis=ctx_bits["basis"], snapshot=ctx_bits["snapshot"],
                           filters_label=ctx_bits["filters_label"])

    st.download_button(copy.EXPORT_BUTTON_LABEL, _csv, mime="text/csv",
                       file_name=ranking_filename(seed_id, lens, ctx_bits["tree"],
                                                  ctx_bits["basis"], ctx_bits["filtered"]),
                       key=f"dl_{lens}")


def _basket_button(selected: list, key: str) -> None:
    """One "add selected" affordance per table (VIZ_SPEC S2.9)."""
    if st.button(copy.FIND["ADD_SELECTED"], key=key, disabled=not selected):
        for iid in selected:
            state.add(iid)
        st.rerun()
    if not selected:
        st.caption(copy.FIND["ADD_SELECTED_NONE"])


def _render_lens_tab(lens: str, ranking: dict, bundle: dict, subs: dict, filters: dict,
                     seed_row, ctx_bits: dict) -> None:
    """VIZ_SPEC S2.4 / S2.22, the one shared form every lens renders through."""
    _lens_intro(lens, ranking, subs, ctx_bits["basis"], bundle, ctx_bits["card"])
    if ranking["undefined"]:
        # R2/L29: the engine's own `reason` is a debugging string (it names
        # internal structures and types digits this app bans in copy), so the
        # reader gets the lens's plain-language precondition instead. The
        # engine's version stays in its own log, unchanged.
        st.info(copy.UNDEFINED_LENS_TEMPLATE.format(
            lens=copy.LENS_NAMES[lens], reason=copy.LENS_UNDEFINED_REASON[lens]))
        return
    ctx, depth = bundle["ctx"], ctx_bits["depth"]
    kept_ids, kept_scores = _filtered(ranking, bundle, filters, seed_row, ctx_bits["family"])
    if not kept_ids:
        st.info(explain_empty(filters, seed_row))
        return
    vis_ids, vis_scores = cut_with_ties(kept_ids, np.asarray(kept_scores), depth)
    rows = _rows_for_ids(ranking, ctx, vis_ids, vis_scores, ctx_bits["cross"], subs)
    _with_evidence(rows, ctx, subs, lens, ranking["seed_id"])
    selected = render_ranked_table(format_rows(rows, lens=lens, depth=depth), key=f"tbl_{lens}")
    st.caption(depth_caption(len(rows), len(kept_ids), depth, max(len(rows) - depth, 0)))
    st.caption(copy.FIND["POP_CAPTION"].format(n_pop=f"{len(ranking['sorted_ids']):,}"))
    _basket_button(selected, f"add_{lens}")
    _tail_and_export(lens, ranking, bundle, subs, (kept_ids, kept_scores), ctx_bits)


# ------------------------------------------------------------- overview -----

def _render_overview(bundle: dict, rankings: dict, lenses: list, filters: dict, seed_row) -> None:
    """VIZ_SPEC S2.3: k of n over the UNFILTERED rankings; post-filters remove
    rows and never recompute k (BUILD_PLAN_2A.md L3)."""
    st.caption(copy.FIND["OVERVIEW_INTRO"])
    rows = concordance(bundle["ctx"], rankings, lenses, CONCORDANCE_N)
    if not rows:
        st.info(copy.FIND["CONCORDANCE_EMPTY"])
        return
    n_defined = rows[0]["n"]
    kept = apply_filters(rows, seed_row=seed_row, family_scores=None, **filters)
    if not kept:
        st.info(explain_empty(filters, seed_row))
        return
    selected = render_concordance_table(
        format_concordance(kept, lenses=lenses, N=CONCORDANCE_N), key="tbl_concordance")
    st.caption(concordance_caption(n_defined, CONCORDANCE_N, len(kept)))
    # R2/L29: the chips are lens CODES, which are stable identifiers rather than
    # self-explaining names -- so the table says what a chip means and points at
    # the guide that names every lens in full.
    st.caption(copy.FIND["LENS_LEGEND_CAPTION"].format(N=CONCORDANCE_N))
    _basket_button(selected, "add_concordance")


# ---------------------------------------------------------- aspirational ----

def _aspirational_frame(rows: list[dict]) -> pd.DataFrame:
    """VIZ_SPEC S2.5 + R1/L22: PP(top10%) as a percent AND its interval as its
    own column (the point estimate is never shown alone, RULES S9.6), both size
    bases, country by NAME, and NO badge column."""
    out = []
    for r in rows:
        iid = r["institution_id"]
        out.append({
            "rank": r["rank"], "institution": r["display_name"],
            "institution_link": links.works_url(iid),
            "country": countries.name(str(r["country_code"])), "type": str(r["type"]),
            "size_full": _count(r.get("total_full_2020_2024")),
            "size_frac": _count(r.get("total_frac_2020_2024")),
            "pp": _pct(r["pp_top10_frac"]),
            "ci": f"{_pct(r['pp_ci_low'])}{DASH}{_pct(r['pp_ci_high'])}",
            "l1": r["lens_score_L1_overlap"], "institution_id": iid})
    return pd.DataFrame(out)


def _render_aspirational_table(df: pd.DataFrame) -> list:
    """Own column set (not the shared lens form): the interval column is
    mandatory here whatever A/B #1 decided (VIZ_SPEC S2.5)."""
    event = st.dataframe(
        df, hide_index=True, width="stretch", on_select="rerun",
        selection_mode="multi-row", key="tbl_aspirational",
        column_order=["rank", "institution", "institution_link", "country", "type",
                      "size_full", "size_frac", "pp", "ci", "l1"],
        column_config={
            "rank": st.column_config.NumberColumn(copy.FIND["COL_RANK"]),
            "institution": st.column_config.TextColumn(copy.FIND["COL_INSTITUTION"]),
            "institution_link": st.column_config.LinkColumn(copy.FIND["COL_WORKS"],
                                                            display_text="->"),
            "institution_id": None,
            "country": st.column_config.TextColumn(copy.FIND["COL_COUNTRY"]),
            "type": st.column_config.TextColumn(copy.FIND["COL_TYPE"]),
            "size_full": st.column_config.TextColumn(copy.FIND["COL_SIZE_FULL"]),
            "size_frac": st.column_config.TextColumn(copy.FIND["COL_SIZE_FRAC"]),
            "pp": st.column_config.TextColumn(copy.FIND["COL_PP"]),
            "ci": st.column_config.TextColumn(copy.FIND["COL_CI"]),
            # format="percent" (not a printf "%.0f%%", which renders a 0-1
            # overlap score as "1%" -- see the defect note on lib/ranked.py in
            # progress/2A_E.md).
            "l1": st.column_config.ProgressColumn(copy.FIND["COL_L1"], min_value=0,
                                                  max_value=1, format="percent")})
    rows_sel = event.selection.rows if event and event.selection else []
    return [df.iloc[i]["institution_id"] for i in rows_sel]


def _render_aspirational(bundle: dict, rankings: dict, filters: dict, seed_row,
                         ctx_bits: dict) -> None:
    """VIZ_SPEC S2.5, kept in L1-overlap order unless the analyst asks for a PP
    sort -- which is a control, never the default (BUILD_PLAN_2A.md L4)."""
    st.caption(copy.FIND["ASP_INTRO"])
    l1 = rankings.get("L1")
    if l1 is None or l1["undefined"] or pd.isna(seed_row["pp_top10_frac"]) \
            or pd.isna(seed_row["pp_ci_high"]):
        st.info(copy.FIND["ASP_UNDEFINED"])
        return
    rows = aspirational(bundle["ctx"], l1)
    pool = len(cut_with_ties(l1["sorted_ids"], l1["sorted_scores"], CFG["depth"]["max"])[0])
    kept = apply_filters(rows, seed_row=seed_row, family_scores=None, **filters)
    if not kept:
        if rows:
            st.info(explain_empty(filters, seed_row))
        else:
            st.info(copy.FIND["ASP_EMPTY"].format(seed=seed_row["display_name"]))
        return
    if st.checkbox(copy.FIND["ASP_SORT_LABEL"], value=False, key="asp_sort", **state.PERSIST):
        kept = sorted(kept, key=lambda r: -r["pp_top10_frac"])
    selected = _render_aspirational_table(_aspirational_frame(kept))
    st.caption(copy.FIND["ASP_CAPTION"].format(n_rows=f"{len(kept):,}", n_pool=f"{pool:,}"))
    _basket_button(selected, "add_aspirational")
    _aspirational_export(kept, ctx_bits)


def _aspirational_export(rows: list[dict], ctx_bits: dict) -> None:
    """Same export contract as a lens tab; the L1-overlap score is what this
    view ranks on, so it is what the CSV's score column carries."""
    lens = "aspirational_by_impact"

    def _csv() -> bytes:
        payload = []
        for r in rows:
            r2 = dict(r)
            r2["lens_score"] = r["lens_score_L1_overlap"]
            payload.append(r2)
        return ranking_csv(payload, seed_id=ctx_bits["seed_id"], lens=lens, tree=ctx_bits["tree"],
                           basis=ctx_bits["basis"], snapshot=ctx_bits["snapshot"],
                           filters_label=ctx_bits["filters_label"])

    st.download_button(copy.EXPORT_BUTTON_LABEL, _csv, mime="text/csv", key="dl_aspirational",
                       file_name=ranking_filename(ctx_bits["seed_id"], lens, ctx_bits["tree"],
                                                  ctx_bits["basis"], ctx_bits["filtered"]))


# ---------------------------------------------------------------- render ----

def _lenses_shown(ctl: dict) -> list:
    """CFG's eight defaults in their ruled order, plus each optional lens whose
    own toggle is on (BUILD_PLAN_2A.md L1)."""
    shown = list(CFG["lenses"]["default"])
    if ctl["c1_on"]:
        shown.append("C1")
    if ctl["l7_on"]:
        shown.append("L7")
    return shown


def _lens_guide(lenses: list) -> None:
    """R2/L29: "How to read the lenses", a collapsed expander at the head of the
    Benchmark section. One plain sentence per SHOWN lens (the guide never
    describes a tab that is not on screen), each headed by the same label its
    tab carries, so the code in the Overview chips, the evidence column and the
    CSV can stay a bare identifier without being unexplained."""
    with st.expander(copy.FIND["LENS_INTRO_HEADER"], expanded=False, key="lens_guide"):
        st.caption(copy.FIND["LENS_INTRO_LEAD"])
        for lens in lenses:
            st.markdown(f"**{copy.LENS_NAMES[lens]}** {DASH} {copy.LENS_INTRO[lens]}")


def _ctx_bits(ctl: dict, filters: dict, seed_id: str, rankings: dict, strip: str | None,
              family, card: dict) -> dict:
    """The per-render constants every tab needs, assembled once."""
    filtered = any(v not in (None, False, []) for v in filters.values())
    if strip:
        label = strip
    else:
        label = ""
    return {"tree": ctl["tree"], "basis": ctl["basis"], "depth": ctl["depth"],
            "snapshot": manifest().get("snapshot") or CFG["snapshot"], "seed_id": seed_id,
            "filters_label": label, "filtered": filtered, "family": family,
            "card": card, "cross": _cross_lens(rankings)}


def render() -> None:
    """The whole Find page, in the argument order VIZ_SPEC S1.3/S1.9/S2 fixes.

    Computation order (L16/L17/L29): sidebar counting & taxonomy -> header ->
    seed search -> substrates -> rank_all -> PROFILE (which returns the seed
    card the L2f tab intro reads) -> controls row (which needs the rankings for
    the same-country tooltip) -> the lens guide -> the strip, rendered back into
    the slot reserved under the title -> tabs."""
    bundle = _bundle()
    qp_seed = st.query_params.get("seed")
    if qp_seed and "seed_id" not in st.session_state and qp_seed in bundle["ctx"]["id_pos"]:
        st.session_state["seed_id"] = qp_seed
    scenario = _sidebar_scenario()
    _header(bundle)
    strip_slot = st.empty()
    seed_id = _seed_search(bundle)
    if not seed_id:
        st.info(copy.FIND["SEED_PROMPT"])
        _sidebar_basket(bundle)
        return
    subs = _subs(scenario["tree"], scenario["basis"])
    ctx = bundle["ctx"]
    rankings = rank_all(ctx, subs, seed_id)
    seed_row = ctx["index_by_id"].loc[seed_id]
    _sidebar_basket(bundle)
    card = _render_profile(bundle, subs, seed_id, scenario)
    benchmark, filters = _controls_row(bundle, rankings, seed_row)
    ctl = {**scenario, **benchmark}
    lenses = _lenses_shown(ctl)
    _lens_guide(lenses)
    strip = active_controls_strip(tree=_strip_tree(ctl["tree"]), basis=ctl["basis"],
                                  depth=ctl["depth"], c1_on=ctl["c1_on"], l7_on=ctl["l7_on"],
                                  filters=filters)
    if strip:
        with strip_slot.container(key="strip"):
            st.markdown(strip)
    bits = _ctx_bits(ctl, filters, seed_id, rankings, strip,
                     _family_scores(bundle, subs, seed_id, filters), card)
    # R2/L29: the tab carries the lens's NAME; the code stays the identifier the
    # Overview chips, the evidence column and the CSV cross-reference.
    tabs = st.tabs([copy.FIND["TAB_OVERVIEW"], *[copy.LENS_NAMES[ln] for ln in lenses],
                    copy.FIND["TAB_ASPIRATIONAL"]])
    with tabs[0]:
        _render_overview(bundle, rankings, lenses, filters, seed_row)
    for tab, lens in zip(tabs[1:-1], lenses):
        with tab:
            _render_lens_tab(lens, rankings[lens], bundle, subs, filters, seed_row, bits)
    with tabs[-1]:
        _render_aspirational(bundle, rankings, filters, seed_row, bits)

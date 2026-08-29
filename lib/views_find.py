"""
app/lib/views_find.py -- render functions for the Find page (Sprint 2 Phase 2A,
Stream E). COMPOSITION ONLY: every ranking, filter, badge, table shape, string
and number comes from lib/engine and lib/{ranked,search,filters,badges,exports,
copy,state,palette,app_config,data_cache}. Nothing here re-implements them and
nothing here types a value into a rendered string (BUILD_PLAN_2A.md L10).

Performance shape (measured on this data, env-app): load_context 3.1 s,
build_substrates 4.4 s (both cached as resources), rank_all 0.12 s per seed
(recomputed every rerun -- cheap), build_rows over a FULL ranking 0.95 s per
lens (7,556 rows) -- far too slow to pay eleven times per rerun, since st.tabs
executes every tab body. So rows are built only for what is actually shown: the
post-filtered depth cut, the tail-search matches, and -- lazily, via
st.download_button's callable `data` (Streamlit 1.61 runs it on click, off the
script thread) -- the full filtered ranking for the CSV. Post-filters are
evaluated on a lightweight per-institution dict built once (`lite`), and the
displayed rank is always the ORIGINAL competition rank from the unfiltered
ranking (`ranking["rmap"]`, verified equal to `build_rows`' own
`competition_ranks` output), never a renumbering of the filtered list.

STRINGS: `lib/copy.py` is Stream F's file and is closed. Any user-facing string
this page needs that copy.py does not carry is defined ONCE in `EXTRA_COPY`
below under copy.py's own rule -- no digit character except inside a lens code
(L0..L7, L2f, F1, C1) or "top10"/"PP(top10%)"; every other number is a
`{placeholder}` the caller fills from CFG or the live data. The manager folds
these into copy.py later (progress/2A_E.md lists every key).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from lib import copy, state
from lib.app_config import CFG
from lib.badges import badges_for, catchall_tooltip, umbrella_flags, umbrella_medians
from lib.data_cache import DATA_DIR, index, manifest, topics_dim
from lib.engine import (
    ALL_LENSES, CONCORDANCE_N, aspirational, build_rows, build_substrates, catchall_811_share,
    concordance, cut_with_ties, family_overlap_scores, load_context, rank_all, seed_card,
)
from lib.exports import ranking_csv, ranking_filename
from lib.filters import active_controls_strip, apply_filters, explain_empty
from lib.palette import NA_MARK
from lib.ranked import (
    concordance_caption, depth_caption, format_concordance, format_rows,
    render_concordance_table, render_ranked_table,
)
from lib.search import build_search_index, normalize, search

# The C1 lens restricts L1 to the seed's top-N subfields; N is a bare literal
# inside lib/engine/lenses.py::build_c1_for_seed (`np.argsort(...)[:20]`), which
# is Stream B's vendored file and gives it no name. Read here ONCE so no
# rendered string ever types it (BUILD_PLAN_2A.md L10).
CORE_TOP_N = 20

SEP = "·"   # middle dot -- the separator copy.STRIP_JOIN already uses
DASH = "–"  # en dash -- interval rendering

EXTRA_COPY = {
    "SCENARIO_HEADER": "Scenario",
    "TREE_LABEL": "Subfield tree",
    "BASIS_LABEL": "Counting basis",
    "DEPTH_HEADER": "Depth",
    "DEPTH_LABEL": "Rows shown per lens",
    "OPTIONAL_HEADER": "Optional lenses",
    "L7_HEADER": "Experimental view",
    "FILTERS_HEADER": "Post-filters",
    "FILTERS_HELP": "Applied after ranking: they remove rows, they never change a rank.",
    "TYPE_LABEL": "Institution type",
    "COUNTRY_LABEL": "Country",
    "EXCLUDE_OWN_LABEL": "Exclude the seed's own country",
    "SIZE_LABEL": "Size range (full works)",
    "SCALE_GUARD_LABEL": "Scale guard (comparable size band)",
    "SCALE_GUARD_HELP": ("Keeps candidates within a size ratio of the seed; the ratio is banded "
                          "by the seed's own size."),
    "FAMILY_LABEL": "Family filter (field-grain overlap)",
    "FAMILY_HELP": "Keeps candidates whose L0 field-grain overlap with the seed is at or above {threshold}.",
    "BASKET_HEADER": "Basket",
    "BASKET_EMPTY": "No comparators added yet -- use the add button under any table.",
    "BASKET_CLEAR": "Clear basket",
    "BASKET_REMOVE": "Remove",
    "ADD_COMPARATOR_LABEL": "Add a comparator not found above",
    "ADD_COMPARATOR_PICK": "Matching institutions",
    "ADD_COMPARATOR_BUTTON": "Add to basket",
    "PAGE_TITLE": "Find",
    "PAGE_INTRO": "Search for an institution, then read who resembles it across independent lenses.",
    "SNAPSHOT_CAPTION": ("Snapshot: {snapshot} (generated {generated_at}) {sep} {n_institutions} "
                          "institutions in the index."),
    "SEED_SEARCH_LABEL": "Institution name, acronym or alternative name",
    "SEED_PICK_LABEL": "Matching institutions",
    "SEED_PROMPT": "Type an institution name above to load its benchmark.",
    "CARD_SIZE_FULL": "Size (full counting)",
    "CARD_SIZE_FRAC": "Size (fractional counting)",
    "CARD_HHI": "Concentration",
    "CARD_BREADTH": "Breadth (subfields)",
    "CARD_DENOM_CAPTION": ("Works published {y0}{dash}{y1}. Full counting credits a whole work to the "
                            "institution; fractional counting credits its author share. Concentration "
                            "is the subfield HHI ({hhi_value}); breadth is the number of subfields present."),
    "CARD_TOP_FIELDS": "Top fields",
    "CARD_TOP_SUBFIELDS": "Top subfields",
    "CARD_EVIDENCE": "Coverage evidence for this seed",
    "EV_L2F": "Eligible subfield cells for L2f: {value}",
    "EV_SDG": "SDG-tagged share of works: {value}",
    "EV_ERC": "ERC-classified share of fractional mass: {value}",
    "EV_FRONTIER": "Frontier top-quartile share: {value}",
    "EV_CATCHALL": "Catch-all (out-of-scope) topic share: {value}",
    "CARD_PP": "PP(top10%): {pp} [{lo}{dash}{hi}]",
    "CARD_PP_CAPTION": ("Share of the institution's fractional output in the world top decile of its own "
                         "citation distribution, with its bootstrap interval -- never the point estimate alone."),
    "LINK_OPENALEX": "OpenAlex works",
    "LINK_ROR": "ROR",
    "LINK_HOMEPAGE": "Homepage",
    "TAB_OVERVIEW": "Overview",
    "TAB_ASPIRATIONAL": "Aspirational",
    "OVERVIEW_INTRO": ("Candidates that several independent lenses agree on. Order here is agreement, "
                        "not a score."),
    "CONCORDANCE_EMPTY": ("No candidate is found by more than one of the lenses defined for this seed. "
                           "Open the single-lens tabs instead."),
    "BASIS_DISCLOSURE": "This lens is fractional-only: the counting-basis toggle does not change it.",
    "EVIDENCE_LABEL": "Evidence for this seed {sep} {text}",
    "EV_NONE": "No lens-specific evidence line for this seed.",
    "ADD_SELECTED": "Add selected rows to basket",
    "ADD_SELECTED_NONE": "Select rows in the table above, then use this button.",
    "BADGE_NOTE": "Some rows carry a badge {sep} hover for what each one compares against.",
    "TAIL_SEARCH_LABEL": "Search the full ranking (beyond the rows shown)",
    "TAIL_CAPTION": "Matches anywhere in this lens's ranking, with their original rank.",
    "POP_CAPTION": "Ranked against {n_pop} institutions in the index, the seed excluded.",
    "ASP_INTRO": ("Candidates already found by L1 whose impact interval sits entirely above the seed's. "
                   "Kept in L1-overlap order."),
    "ASP_SORT_LABEL": "Sort by PP(top10%) instead of L1 overlap",
    "ASP_EMPTY": "No L1 candidate's impact interval sits fully above {seed}'s in the pool.",
    "ASP_UNDEFINED": ("The aspirational view needs a defined L1 ranking and a PP(top10%) value with an "
                       "interval for the seed; one of them is missing here."),
    "ASP_CAPTION": "{n_rows} candidates clear the interval test, out of {n_pool} in the L1 pool considered.",
    "COL_RANK": "Rank",
    "COL_INSTITUTION": "Institution",
    "COL_WORKS": "OpenAlex works",
    "COL_COUNTRY": "Country",
    "COL_TYPE": "Type",
    "COL_BADGE": "Badge",
    "COL_SIZE": "Size (full)",
    "COL_PP": "PP(top10%)",
    "COL_CI": "Interval",
    "COL_L1": "L1 overlap",
}

WINDOW_START, WINDOW_END = CFG["window"]
DEPTH_OPTIONS = [CFG["depth"]["default"], CFG["depth"]["max"]]


# ------------------------------------------------------------- caches -------

@st.cache_resource
def _bundle() -> dict:
    """Everything computed once per process: the engine context plus the search
    index, umbrella flags/medians, catch-all shares, normalised names for the
    tail search, and the lightweight per-institution dict the post-filters run
    over (`lite` -- four keys, exactly what `filters.apply_filters` reads)."""
    idx = index()
    ctx = load_context(str(DATA_DIR))
    lite = {r.institution_id: {"institution_id": r.institution_id, "type": str(r.type),
                               "country_code": str(r.country_code),
                               "total_full_2020_2024": (None if pd.isna(r.total_full_2020_2024)
                                                        else float(r.total_full_2020_2024))}
            for r in idx.itertuples(index=False)}
    return {"ctx": ctx, "index_df": idx, "lite": lite,
            "search_idx": build_search_index(idx),
            "flags": umbrella_flags(idx), "medians": umbrella_medians(idx),
            "catchall": catchall_811_share(ctx),
            "norm_names": {i: normalize(n)
                           for i, n in zip(idx["institution_id"], idx["display_name"])},
            "n_fields": int(topics_dim()["field_id"].nunique())}


@st.cache_resource(max_entries=3)
def _subs(tree: str, basis: str) -> dict:
    """One (tree, basis) scenario's substrates. Bounded: three live at most."""
    return build_substrates(_bundle()["ctx"], tree, basis)


# ------------------------------------------------------------ sidebar -------

def _sidebar_scenario() -> dict:
    """VIZ_SPEC S1.3 controls 1-3. Every widget keyed and persisted so a
    Menu<->Find round trip does not reset it (state.PERSIST). C1 and L7 are two
    SEPARATE affordances under their own headers, never one bundled control."""
    sb = st.sidebar
    sb.header(EXTRA_COPY["SCENARIO_HEADER"])
    trees = CFG["scenario"]["toggles"]["tree"]
    tree = sb.selectbox(EXTRA_COPY["TREE_LABEL"], trees,
                        index=trees.index(CFG["scenario"]["tree_default"]),
                        key="tree", **state.PERSIST)
    bases = CFG["scenario"]["toggles"]["basis"]
    basis = sb.selectbox(EXTRA_COPY["BASIS_LABEL"], bases,
                         index=bases.index(CFG["scenario"]["basis_default"]),
                         help=copy.BASIS_NOT_APPLIED_TOOLTIP, key="basis", **state.PERSIST)
    sb.header(EXTRA_COPY["DEPTH_HEADER"])
    depth = sb.radio(EXTRA_COPY["DEPTH_LABEL"], DEPTH_OPTIONS, index=0, horizontal=True,
                     key="depth", **state.PERSIST)
    sb.header(EXTRA_COPY["OPTIONAL_HEADER"])
    c1_on = sb.checkbox(copy.C1_TOGGLE_LABEL, value=False, key="c1_on", **state.PERSIST)
    sb.caption(EXTRA_COPY["L7_HEADER"])
    l7_on = sb.checkbox(copy.L7_TOGGLE_LABEL, value=False, key="l7_on", **state.PERSIST)
    return {"tree": tree, "basis": basis, "depth": int(depth), "c1_on": c1_on, "l7_on": l7_on}


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


def _sidebar_filters(bundle: dict, rankings: dict, seed_row, depth: int) -> dict:
    """VIZ_SPEC S1.3 control 4 -- every post-filter opt-in and off by default.
    Rendered AFTER the rankings exist so the same-country tooltip carries a
    computed share. Returns exactly `filters.apply_filters`' keyword set."""
    sb, idx = st.sidebar, bundle["index_df"]
    sb.header(EXTRA_COPY["FILTERS_HEADER"])
    sb.caption(EXTRA_COPY["FILTERS_HELP"])
    types = sb.multiselect(EXTRA_COPY["TYPE_LABEL"], sorted(idx["type"].astype(str).unique()),
                           default=[], key="f_types", **state.PERSIST)
    countries = sb.multiselect(EXTRA_COPY["COUNTRY_LABEL"],
                               sorted(idx["country_code"].astype(str).unique()),
                               default=[], key="f_countries", **state.PERSIST)
    excl = sb.checkbox(EXTRA_COPY["EXCLUDE_OWN_LABEL"], value=False,
                       help=copy.L3_COUNTRY_TOOLTIP.format(
                           share=_same_country_share(rankings, bundle["ctx"], seed_row, depth)),
                       key="f_excl_own", **state.PERSIST)
    lo_all = int(np.floor(idx["total_full_2020_2024"].min()))
    hi_all = int(np.ceil(idx["total_full_2020_2024"].max()))
    lo, hi = sb.slider(EXTRA_COPY["SIZE_LABEL"], lo_all, hi_all, (lo_all, hi_all),
                       key="f_size", **state.PERSIST)
    guard = sb.checkbox(EXTRA_COPY["SCALE_GUARD_LABEL"], value=False,
                        help=EXTRA_COPY["SCALE_GUARD_HELP"], key="f_guard", **state.PERSIST)
    thr = CFG["family_filter_threshold"]
    fam = sb.checkbox(EXTRA_COPY["FAMILY_LABEL"], value=False,
                      help=EXTRA_COPY["FAMILY_HELP"].format(threshold=thr),
                      key="f_family", **state.PERSIST)
    narrowed = (lo, hi) != (lo_all, hi_all)
    return {"types": types or None, "countries": countries or None, "exclude_own_country": excl,
            "size_range": (lo, hi) if narrowed else None, "scale_guard": guard,
            "family_min": thr if fam else None}


def _hit_label(hits: list[dict], iid: str) -> str:
    """name . country . type . size -- VIZ_SPEC S2.1's candidate line."""
    h = next(x for x in hits if x["id"] == iid)
    total = h["total_full_2020_2024"]
    if total is None or pd.isna(total):
        size = NA_MARK
    else:
        size = f"{total:,.0f}"
    return f"{h['display_name']} {SEP} {h['country_code']} {SEP} {h['type']} {SEP} {size}"


def _sidebar_basket(bundle: dict) -> None:
    """VIZ_SPEC S1.3 control 5 / S2.9: the basket list, a remove control per
    item, a clear button, and the free-text "add a comparator" box."""
    sb, names = st.sidebar, bundle["ctx"]["index_by_id"]
    sb.header(EXTRA_COPY["BASKET_HEADER"])
    items = state.items()
    if not items:
        sb.caption(EXTRA_COPY["BASKET_EMPTY"])
    else:
        for iid in list(items):
            col_a, col_b = sb.columns([4, 1])
            col_a.write(str(names.loc[iid, "display_name"]))
            if col_b.button(EXTRA_COPY["BASKET_REMOVE"], key=f"rm_{iid}"):
                state.remove(iid)
                st.rerun()
        if sb.button(EXTRA_COPY["BASKET_CLEAR"], key="basket_clear"):
            state.clear()
            st.rerun()
    query = sb.text_input(EXTRA_COPY["ADD_COMPARATOR_LABEL"], help=copy.ADD_COMPARATOR_HELP,
                          key="basket_query", **state.PERSIST)
    hits = search(query, bundle["search_idx"]) if query else []
    if query and not hits:
        sb.caption(copy.SEARCH_EMPTY_TEMPLATE.format(query=query))
    if hits:
        pick = sb.selectbox(EXTRA_COPY["ADD_COMPARATOR_PICK"], [h["id"] for h in hits],
                            format_func=lambda i: _hit_label(hits, i), key="basket_pick")
        if sb.button(EXTRA_COPY["ADD_COMPARATOR_BUTTON"], key="basket_add"):
            state.add(pick)
            st.rerun()


# ------------------------------------------------------- header + search ----

def _header(bundle: dict) -> None:
    """Title, the standing verdict line, and the snapshot stamp -- both label
    and figures computed from the deployed manifest (BUILD_PLAN_2A.md L11)."""
    st.title(EXTRA_COPY["PAGE_TITLE"])
    st.caption(EXTRA_COPY["PAGE_INTRO"])
    st.markdown(f"**{copy.VERDICT_LINE}**")
    mf = manifest()
    # ops/deploy.py writes `source_manifest_generated_at` / `deployed_at`; the
    # pre-staged source_manifest.json writes `generated_at`. Take whichever the
    # deployed file actually carries rather than showing NA_MARK for both.
    stamp = (mf.get("generated_at") or mf.get("source_manifest_generated_at")
             or mf.get("deployed_at") or NA_MARK)
    st.caption(EXTRA_COPY["SNAPSHOT_CAPTION"].format(
        snapshot=mf.get("snapshot") or CFG["snapshot"], generated_at=stamp,
        n_institutions=f"{len(bundle['index_df']):,}", sep=SEP))


def _seed_search(bundle: dict) -> str | None:
    """VIZ_SPEC S2.1: search-first, no default listing. The chosen id lives in
    the plain (non-widget) session key `seed_id`, so it survives page hops."""
    query = st.text_input(EXTRA_COPY["SEED_SEARCH_LABEL"], key="seed_query", **state.PERSIST)
    hits = search(query, bundle["search_idx"]) if query else []
    if query and not hits:
        st.info(copy.SEARCH_EMPTY_TEMPLATE.format(query=query))
    if hits:
        pick = st.selectbox(EXTRA_COPY["SEED_PICK_LABEL"], [h["id"] for h in hits],
                            format_func=lambda i: _hit_label(hits, i), key="seed_pick")
        if pick:
            st.session_state["seed_id"] = pick
    return st.session_state.get("seed_id")


# --------------------------------------------------------- the seed card ----

def _pct(value) -> str:
    """One precision level per measure; NA_MARK for missing, never 0."""
    if value is None or pd.isna(value):
        return NA_MARK
    return f"{float(value):.1%}"


def _seed_badges(card: dict, bundle: dict) -> None:
    """Umbrella / type-corrected badges for the seed, mutually exclusive by
    `badges.badges_for`'s own assertion; the umbrella tooltip carries the
    country-and-type median it was compared against (WT verifiability edit)."""
    labels = badges_for(card, bundle["flags"], bundle["medians"])
    if not labels:
        return
    med = bundle["medians"].get((str(card["country_code"]), str(card["type"])))
    if med is None:
        tip = copy.UMBRELLA_TOOLTIP.format(median=NA_MARK)
    else:
        tip = copy.UMBRELLA_TOOLTIP.format(median=f"{med:,.0f}")
    st.markdown(f" {SEP} ".join(labels), help=tip)


def _card_kpis(card: dict, row) -> None:
    """VIZ_SPEC S2.2 block 2: size on BOTH bases, concentration, breadth -- the
    denominators stated in the caption directly under them."""
    cols = st.columns(4)
    full, frac = card["total_full_2020_2024"], card["total_frac_2020_2024"]
    if full is None:
        full_txt = NA_MARK
    else:
        full_txt = f"{full:,.0f}"
    if frac is None:
        frac_txt = NA_MARK
    else:
        frac_txt = f"{frac:,.0f}"
    cols[0].metric(EXTRA_COPY["CARD_SIZE_FULL"], full_txt)
    cols[1].metric(EXTRA_COPY["CARD_SIZE_FRAC"], frac_txt)
    cols[2].metric(EXTRA_COPY["CARD_HHI"], str(row["hhi_class"]))
    if card["breadth_subfields"] is None:
        breadth_txt = NA_MARK
    else:
        breadth_txt = f"{card['breadth_subfields']:,}"
    cols[3].metric(EXTRA_COPY["CARD_BREADTH"], breadth_txt)
    if card["hhi_subfield"] is None:
        hhi_txt = NA_MARK
    else:
        hhi_txt = f"{card['hhi_subfield']:.3f}"
    st.caption(EXTRA_COPY["CARD_DENOM_CAPTION"].format(
        y0=WINDOW_START, y1=WINDOW_END, dash=DASH, hhi_value=hhi_txt))


def _card_shape(card: dict) -> None:
    """VIZ_SPEC S2.2 block 3: top-3 fields and top-5 subfields as text lists."""
    cols = st.columns(2)
    fields = card["shape_top3_fields"] or []
    subs = card["top5_subfields_default_scenario"] or []
    cols[0].markdown(f"**{EXTRA_COPY['CARD_TOP_FIELDS']}**")
    for f in fields:
        cols[0].write(f"{f['field_name']} {SEP} {f['share']:.1%}")
    if not fields:
        cols[0].write(NA_MARK)
    cols[1].markdown(f"**{EXTRA_COPY['CARD_TOP_SUBFIELDS']}**")
    for s in subs:
        cols[1].write(f"{s['name']} {SEP} {s['share_frac']:.1%}")
    if not subs:
        cols[1].write(NA_MARK)


def _card_evidence(card: dict) -> None:
    """VIZ_SPEC S2.2 blocks 4-5: the continuous evidence lines (never a gate)
    and PP(top10%) with its interval."""
    st.markdown(f"**{EXTRA_COPY['CARD_EVIDENCE']}**")
    st.write(EXTRA_COPY["EV_L2F"].format(value=f"{card['n_eligible_subfields_L2f']:,}"))
    st.write(EXTRA_COPY["EV_SDG"].format(value=_pct(card["sdg_tagged_share"])))
    erc, tot = card["erc_classified_mass_frac"], card["total_frac_2020_2024"]
    if erc is None or tot in (None, 0):
        erc_txt = NA_MARK
    else:
        erc_txt = _pct(erc / tot)
    st.write(EXTRA_COPY["EV_ERC"].format(value=erc_txt))
    st.write(EXTRA_COPY["EV_FRONTIER"].format(value=_pct(card["frontier_top25_share_index"])))
    st.caption(EXTRA_COPY["EV_CATCHALL"].format(value=_pct(card["catchall_811_share"])),
               help=catchall_tooltip(card["catchall_811_share"]))


def _card_impact(row) -> None:
    """PP(top10%) with CI, "value [low-high]", NA_MARK when null (never 0)."""
    st.markdown(EXTRA_COPY["CARD_PP"].format(
        pp=_pct(row["pp_top10_frac"]), lo=_pct(row["pp_ci_low"]), hi=_pct(row["pp_ci_high"]),
        dash=DASH))
    st.caption(EXTRA_COPY["CARD_PP_CAPTION"])


def _card_links(card: dict, row) -> None:
    """OpenAlex works deep link (window years from CFG), ROR, homepage."""
    iid = card["institution_id"]
    works = (f"https://openalex.org/works?filter=authorships.institutions.id:{iid},"
             f"publication_year:{WINDOW_START}-{WINDOW_END}")
    parts = [f"[{EXTRA_COPY['LINK_OPENALEX']}]({works})"]
    ror = row.get("ror_id")
    if isinstance(ror, str) and ror:
        parts.append(f"[{EXTRA_COPY['LINK_ROR']}]({ror})")
    home = row.get("homepage_url")
    if isinstance(home, str) and home:
        parts.append(f"[{EXTRA_COPY['LINK_HOMEPAGE']}]({home})")
    st.markdown(f" {SEP} ".join(parts))


def _render_seed_card(bundle: dict, subs: dict, seed_id: str) -> None:
    """VIZ_SPEC S2.2, composed from `engine.seed_card` + the index row."""
    ctx = bundle["ctx"]
    card = seed_card(ctx, seed_id, subs, bundle["catchall"])
    row = ctx["index_by_id"].loc[seed_id]
    with st.container(border=True, key="seed_card"):
        st.subheader(str(card["display_name"]))
        city = row.get("city")
        if isinstance(city, str) and city:
            place = f"{city}, {card['country_code']}"
        else:
            place = str(card["country_code"])
        st.caption(f"{card['type']} {SEP} {place}")
        _seed_badges(card, bundle)
        _card_kpis(card, row)
        _card_shape(card)
        _card_evidence(card)
        _card_impact(row)
        _card_links(card, row)


# --------------------------------------------------- rows, filters, rank ----

def _rows_for_ids(ranking: dict, ctx: dict, ids: list, scores, rankings: dict | None) -> list[dict]:
    """`engine.build_rows` over an explicit id subset, with the ORIGINAL
    competition rank restored from the unfiltered ranking's `rmap` (post-filters
    remove rows, they never renumber -- BUILD_PLAN_2A.md L6/VIZ_SPEC S1.7)."""
    if not ids:
        return []
    sub = dict(ranking)
    sub["sorted_ids"] = list(ids)
    sub["sorted_scores"] = np.asarray(scores)
    rows = build_rows(sub, ctx, len(ids), rankings)
    for r in rows:
        r["rank"] = ranking["rmap"][r["institution_id"]]
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


def _badges_map(rows: list[dict], bundle: dict) -> tuple[dict, str]:
    """Badge text per visible row + the tooltip body naming each flagged row's
    country-and-type median (st.dataframe has no per-cell tooltip, so the
    medians ride on one caption's `help` under the table)."""
    out, tips = {}, []
    for r in rows:
        labels = badges_for(r, bundle["flags"], bundle["medians"])
        if not labels:
            continue
        out[r["institution_id"]] = f" {SEP} ".join(labels)
        med = bundle["medians"].get((str(r["country_code"]), str(r["type"])))
        if med is not None:
            tips.append(f"{r['display_name']}: " + copy.UMBRELLA_TOOLTIP.format(median=f"{med:,.0f}"))
    return out, "\n\n".join(tips)


# ------------------------------------------------------------- lens tab -----

def _gloss_values(bundle: dict) -> dict:
    """Every placeholder copy.LENS_GLOSS/LENS_CAVEAT can ask for, filled from
    CFG, the engine's own constants and the live data -- never typed."""
    return {"n_fields": bundle["n_fields"], "n_named_lenses": len(ALL_LENSES),
            "n_default_lenses": len(CFG["lenses"]["default"]),
            "floor_papers": CFG["l2f_floor"]["value"], "core_top_n": CORE_TOP_N,
            "depth_max": CFG["depth"]["max"]}


def _lens_intro(lens: str, ranking: dict, subs: dict, basis: str, bundle: dict) -> None:
    """Gloss + caveat + this seed's evidence line + the basis disclosure, all
    above the table and never tooltip-only (VIZ_SPEC S2.4)."""
    vals = _gloss_values(bundle)
    st.markdown(f"**{copy.LENS_GLOSS[lens].format(**vals)}**")
    st.caption(copy.LENS_CAVEAT[lens].format(**vals))
    ev = {k: v for k, v in (ranking.get("evidence") or {}).items() if isinstance(v, (int, float))}
    if ev:
        text = "; ".join(f"{k.replace('_', ' ')}: {v:,.3f}" for k, v in ev.items())
        st.caption(EXTRA_COPY["EVIDENCE_LABEL"].format(text=text, sep=SEP))
    else:
        st.caption(EXTRA_COPY["EV_NONE"])
    if basis == "full" and not subs["basis_applies"][lens]:
        st.caption(EXTRA_COPY["BASIS_DISCLOSURE"])


def _tail_and_export(lens: str, ranking: dict, bundle: dict, kept, ctx_bits: dict) -> None:
    """VIZ_SPEC S2.7: search scoped to the FULL filtered ranking, and the CSV of
    that same full ranking -- generated lazily on click (Streamlit 1.61 accepts
    a zero-arg callable for `data`), so no rerun ever pays for rows nobody
    downloads."""
    kept_ids, kept_scores = kept
    ctx, norm = bundle["ctx"], bundle["norm_names"]
    query = st.text_input(EXTRA_COPY["TAIL_SEARCH_LABEL"], key=f"tail_{lens}", **state.PERSIST)
    if query:
        q = normalize(query)
        hits = [(i, s) for i, s in zip(kept_ids, kept_scores) if q in norm.get(i, "")]
        if not hits:
            st.caption(copy.TAIL_SEARCH_EMPTY_TEMPLATE.format(query=query))
        else:
            rows = _rows_for_ids(ranking, ctx, [h[0] for h in hits], [h[1] for h in hits],
                                 ctx_bits["cross"])
            st.caption(EXTRA_COPY["TAIL_CAPTION"])
            render_ranked_table(format_rows(rows, lens=lens, depth=len(rows)),
                                key=f"tailtbl_{lens}")

    def _csv() -> bytes:
        rows = _rows_for_ids(ranking, ctx, kept_ids, kept_scores, ctx_bits["cross"])
        return ranking_csv(rows, seed_id=ranking["seed_id"], lens=lens, tree=ctx_bits["tree"],
                           basis=ctx_bits["basis"], snapshot=ctx_bits["snapshot"],
                           filters_label=ctx_bits["filters_label"])

    st.download_button(copy.EXPORT_BUTTON_LABEL, _csv, mime="text/csv",
                       file_name=ranking_filename(ranking["seed_id"], lens, ctx_bits["tree"],
                                                  ctx_bits["basis"], ctx_bits["filtered"]),
                       key=f"dl_{lens}")


def _basket_button(selected: list, key: str) -> None:
    """One "add selected" affordance per table (VIZ_SPEC S2.9)."""
    if st.button(EXTRA_COPY["ADD_SELECTED"], key=key, disabled=not selected):
        for iid in selected:
            state.add(iid)
        st.rerun()
    if not selected:
        st.caption(EXTRA_COPY["ADD_SELECTED_NONE"])


def _render_lens_tab(lens: str, ranking: dict, bundle: dict, subs: dict, filters: dict,
                     seed_row, ctx_bits: dict) -> None:
    """VIZ_SPEC S2.4, the one shared form every lens renders through."""
    _lens_intro(lens, ranking, subs, ctx_bits["basis"], bundle)
    if ranking["undefined"]:
        st.info(copy.UNDEFINED_LENS_TEMPLATE.format(lens=lens, reason=ranking["reason"]))
        return
    ctx, depth = bundle["ctx"], ctx_bits["depth"]
    kept_ids, kept_scores = _filtered(ranking, bundle, filters, seed_row, ctx_bits["family"])
    if not kept_ids:
        st.info(explain_empty(filters, seed_row))
        return
    vis_ids, vis_scores = cut_with_ties(kept_ids, np.asarray(kept_scores), depth)
    rows = _rows_for_ids(ranking, ctx, vis_ids, vis_scores, ctx_bits["cross"])
    badges, tips = _badges_map(rows, bundle)
    selected = render_ranked_table(format_rows(rows, lens=lens, depth=depth, badges=badges),
                                   key=f"tbl_{lens}")
    st.caption(depth_caption(len(rows), len(kept_ids), depth, max(len(rows) - depth, 0)))
    st.caption(EXTRA_COPY["POP_CAPTION"].format(n_pop=f"{len(ranking['sorted_ids']):,}"))
    if tips:
        st.caption(EXTRA_COPY["BADGE_NOTE"].format(sep=SEP), help=tips)
    _basket_button(selected, f"add_{lens}")
    _tail_and_export(lens, ranking, bundle, (kept_ids, kept_scores), ctx_bits)


# ------------------------------------------------------------- overview -----

def _render_overview(bundle: dict, rankings: dict, lenses: list, filters: dict, seed_row) -> None:
    """VIZ_SPEC S2.3: k of n over the UNFILTERED rankings; post-filters remove
    rows and never recompute k (BUILD_PLAN_2A.md L3)."""
    st.caption(EXTRA_COPY["OVERVIEW_INTRO"])
    rows = concordance(bundle["ctx"], rankings, lenses, CONCORDANCE_N)
    if not rows:
        st.info(EXTRA_COPY["CONCORDANCE_EMPTY"])
        return
    n_defined = rows[0]["n"]
    kept = apply_filters(rows, seed_row=seed_row, family_scores=None, **filters)
    if not kept:
        st.info(explain_empty(filters, seed_row))
        return
    selected = render_concordance_table(
        format_concordance(kept, lenses=lenses, N=CONCORDANCE_N), key="tbl_concordance")
    st.caption(concordance_caption(n_defined, CONCORDANCE_N, len(kept)))
    _basket_button(selected, "add_concordance")


# ---------------------------------------------------------- aspirational ----

def _aspirational_frame(rows: list[dict], bundle: dict) -> pd.DataFrame:
    """VIZ_SPEC S2.5: PP(top10%) as a percent AND its interval as its own
    column -- the point estimate is never shown alone (RULES S9.6)."""
    badges, _ = _badges_map(rows, bundle)
    out = []
    for r in rows:
        iid = r["institution_id"]
        out.append({
            "rank": r["rank"], "institution": r["display_name"],
            "institution_link": (f"https://openalex.org/works?filter=authorships.institutions.id:"
                                 f"{iid},publication_year:{WINDOW_START}-{WINDOW_END}"),
            "country": str(r["country_code"]), "type": str(r["type"]),
            "badge": badges.get(iid, ""),
            "size": f"{r['total_full_2020_2024']:,.0f}" if r["total_full_2020_2024"] else NA_MARK,
            "pp": _pct(r["pp_top10_frac"]),
            "ci": f"{_pct(r['pp_ci_low'])}{DASH}{_pct(r['pp_ci_high'])}",
            "l1": r["lens_score_L1_overlap"], "institution_id": iid})
    return pd.DataFrame(out)


def _render_aspirational_table(df: pd.DataFrame) -> list:
    """Own column set (not the shared lens form): the interval column is
    mandatory here whatever A/B #1 decided (VIZ_SPEC S2.5)."""
    event = st.dataframe(
        df, hide_index=True, use_container_width=True, on_select="rerun",
        selection_mode="multi-row", key="tbl_aspirational",
        column_order=["rank", "institution", "institution_link", "country", "type", "badge",
                      "size", "pp", "ci", "l1"],
        column_config={
            "rank": st.column_config.NumberColumn(EXTRA_COPY["COL_RANK"]),
            "institution": st.column_config.TextColumn(EXTRA_COPY["COL_INSTITUTION"]),
            "institution_link": st.column_config.LinkColumn(EXTRA_COPY["COL_WORKS"],
                                                            display_text="->"),
            "institution_id": None,
            "country": st.column_config.TextColumn(EXTRA_COPY["COL_COUNTRY"]),
            "type": st.column_config.TextColumn(EXTRA_COPY["COL_TYPE"]),
            "badge": st.column_config.TextColumn(EXTRA_COPY["COL_BADGE"]),
            "size": st.column_config.TextColumn(EXTRA_COPY["COL_SIZE"]),
            "pp": st.column_config.TextColumn(EXTRA_COPY["COL_PP"]),
            "ci": st.column_config.TextColumn(EXTRA_COPY["COL_CI"]),
            # format="percent" (not a printf "%.0f%%", which renders a 0-1
            # overlap score as "1%" -- see the defect note on lib/ranked.py in
            # progress/2A_E.md).
            "l1": st.column_config.ProgressColumn(EXTRA_COPY["COL_L1"], min_value=0,
                                                  max_value=1, format="percent")})
    rows_sel = event.selection.rows if event and event.selection else []
    return [df.iloc[i]["institution_id"] for i in rows_sel]


def _render_aspirational(bundle: dict, rankings: dict, filters: dict, seed_row,
                         ctx_bits: dict) -> None:
    """VIZ_SPEC S2.5, kept in L1-overlap order unless the analyst asks for a PP
    sort -- which is a control, never the default (BUILD_PLAN_2A.md L4)."""
    st.caption(EXTRA_COPY["ASP_INTRO"])
    l1 = rankings.get("L1")
    if l1 is None or l1["undefined"] or pd.isna(seed_row["pp_top10_frac"]) \
            or pd.isna(seed_row["pp_ci_high"]):
        st.info(EXTRA_COPY["ASP_UNDEFINED"])
        return
    rows = aspirational(bundle["ctx"], l1)
    pool = len(cut_with_ties(l1["sorted_ids"], l1["sorted_scores"], CFG["depth"]["max"])[0])
    kept = apply_filters(rows, seed_row=seed_row, family_scores=None, **filters)
    if not kept:
        if rows:
            st.info(explain_empty(filters, seed_row))
        else:
            st.info(EXTRA_COPY["ASP_EMPTY"].format(seed=seed_row["display_name"]))
        return
    if st.checkbox(EXTRA_COPY["ASP_SORT_LABEL"], value=False, key="asp_sort", **state.PERSIST):
        kept = sorted(kept, key=lambda r: -r["pp_top10_frac"])
    selected = _render_aspirational_table(_aspirational_frame(kept, bundle))
    st.caption(EXTRA_COPY["ASP_CAPTION"].format(n_rows=f"{len(kept):,}", n_pool=f"{pool:,}"))
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


def _ctx_bits(ctl: dict, filters: dict, seed_id: str, rankings: dict, strip: str | None,
              family) -> dict:
    """The per-render constants every tab needs, assembled once."""
    filtered = any(v not in (None, False, []) for v in filters.values())
    if strip:
        label = strip
    else:
        label = ""
    return {"tree": ctl["tree"], "basis": ctl["basis"], "depth": ctl["depth"],
            "snapshot": manifest().get("snapshot") or CFG["snapshot"], "seed_id": seed_id,
            "filters_label": label, "filtered": filtered, "family": family,
            "cross": _cross_lens(rankings)}


def render() -> None:
    """The whole Find page, in the argument order VIZ_SPEC S1.3/S2 fixes."""
    bundle = _bundle()
    qp_seed = st.query_params.get("seed")
    if qp_seed and "seed_id" not in st.session_state and qp_seed in bundle["ctx"]["id_pos"]:
        st.session_state["seed_id"] = qp_seed
    ctl = _sidebar_scenario()
    _header(bundle)
    strip_slot = st.empty()
    seed_id = _seed_search(bundle)
    if not seed_id:
        st.info(EXTRA_COPY["SEED_PROMPT"])
        _sidebar_basket(bundle)
        return
    subs = _subs(ctl["tree"], ctl["basis"])
    ctx = bundle["ctx"]
    rankings = rank_all(ctx, subs, seed_id)
    seed_row = ctx["index_by_id"].loc[seed_id]
    filters = _sidebar_filters(bundle, rankings, seed_row, ctl["depth"])
    _sidebar_basket(bundle)
    strip = active_controls_strip(tree=ctl["tree"], basis=ctl["basis"], depth=ctl["depth"],
                                  c1_on=ctl["c1_on"], l7_on=ctl["l7_on"], filters=filters)
    if strip:
        with strip_slot.container(key="strip"):
            st.markdown(strip)
    _render_seed_card(bundle, subs, seed_id)
    lenses = _lenses_shown(ctl)
    bits = _ctx_bits(ctl, filters, seed_id, rankings,
                     strip, _family_scores(bundle, subs, seed_id, filters))
    tabs = st.tabs([EXTRA_COPY["TAB_OVERVIEW"], *lenses, EXTRA_COPY["TAB_ASPIRATIONAL"]])
    with tabs[0]:
        _render_overview(bundle, rankings, lenses, filters, seed_row)
    for tab, lens in zip(tabs[1:-1], lenses):
        with tab:
            _render_lens_tab(lens, rankings[lens], bundle, subs, filters, seed_row, bits)
    with tabs[-1]:
        _render_aspirational(bundle, rankings, filters, seed_row, bits)

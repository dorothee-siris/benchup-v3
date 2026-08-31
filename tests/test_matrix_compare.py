"""
tests/test_matrix_compare.py -- Stream G (2B-R): Compare/Collaborate scenario
matrix, RE-CUT against the CURRENT `lib/compare_data.py` / `lib/views_compare.py`
API (BUILD_PLAN_2BR.md S3 row G, A13 cap-3).

The 2B version of this file drove a RETIRED API (`views_compare._frontier_mix`,
a 4-quadrant frontier-mix frame; `k` up to 6). 2B-R replaced both: Compare is
capped at 3 (`state.COMPARE_CAP`, 2B-R-4/A13) and the frontier section is now
TWO charts built off `compare_data.frontier_pooled`/`shared_frontier`
(2B-R-9). This file re-cuts the SAME idea -- a full cross-product sanity pass,
one scenario per cell, cheap enough to run every cell every time -- against
what actually ships now.

AppTest over the Compare page for the FULL cross product basket size {2, 3} x
tree {bestfit, original, conservative} x basis {frac, full} -- 12 cells, run
in ONE module so `st.cache_resource` (the engine context, each (tree, basis)
substrate) stays warm across cells: the first cell pays the cold engine load,
every later cell -- including the Collaborate cells at the end of this same
file -- finds the substrate for its (tree, basis) already built. Only SIX
distinct substrates exist across every cell in this file (3 trees x 2 bases),
so at most six `build_substrates` calls ever run.

Per Compare cell:
  * the page renders with no exception, every section's subheader present
    (proves the frontier map / diverging-pair charts and every other section
    survive the whole cross product, not just the default scenario
    tests/test_pages_compare.py already exercises exhaustively at ONE
    scenario);
  * the legend the page renders carries exactly one swatch per compared
    institution (basket size);
  * under basis="full" the ERC and SDG panel captions carry
    `copy.FIND["FRACTIONAL_ONLY_PANEL"]`, and never do under basis="frac";
  * `compare_data.overview` returns one row per institution;
  * a METRIC-SELECTOR STATE cycled round-robin across the 12 cells (so every
    one of `compare_data.SUBJECT_METRICS` gets exercised at field level
    somewhere in the matrix, not just "share" every time): share sums to 1
    per institution, si's reference line is always 1.0, dynamics names BOTH
    2B-R-6 windows verbatim, and pp/vol_top10/sdg_share return the contract's
    six columns without raising;
  * `compare_data.frontier_pooled`/`shared_frontier` (2B-R-9's two charts):
    every `owner` is one of the compared ids or "shared", `combined_vol` is
    non-increasing (the pooled frame's own sort), and the shared frame is
    EXACTLY the pooled frame's `owner == "shared"` rows, uncapped;
  * the impact floor toggle 30 -> 10 never REDUCES the union frame's row
    count (a lower floor can only ADD subfields to the union, A1);
  * the `?compare=` deep link the page prints round-trips through
    `selection.parse_query` back to the same id list (k in {2, 3} never hits
    `state.COMPARE_CAP` = 3, so nothing is truncated here).

One dedicated (non-parametrized) test drives the ACTUAL "Compare by" radio
widget through several metric states on one scenario -- the matrix cells
above check the same states at the data layer, cheaply, across all 12 cells;
this one proves the WIDGET itself survives the switch, the same idiom
tests/test_pages_compare.py uses for its own single-scenario coverage.

Then the Collaborate page x {bestfit, original, conservative} x {frac, full}
for one pair (6 cells): renders with no exception, and the shared-topics
table's Sigma(min_share) equals the engine's own L3 lens score for the pair
under that SAME scenario -- the identity tests/test_pages_collab.py already
pins at the default scenario, generalised here across all six. `collab_data.
shared_topics` is untouched by the 2B-R Compare re-cut, so this half of the
file carries over unchanged from 2B (only TREES widened from 2 to 3).

Run from cwd `app/`:  python -m pytest tests/test_matrix_compare.py -q
"""
from __future__ import annotations

import itertools
from pathlib import Path

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from lib import charts_compare, compare_data as K, copy, selection, views_compare, views_collab
from lib.data_cache import DATA_DIR
from lib.engine import load_context, rank_all
from lib.views_find import _subs

APP_DIR = Path(__file__).resolve().parents[1]
COMPARE_PAGE = str(APP_DIR / "pages" / "2_⚖️_Compare.py")     # scales
COLLAB_PAGE = str(APP_DIR / "pages" / "3_\U0001F91D_Collaborate.py")    # handshake

STRASBOURG = "I68947357"    # Universite de Strasbourg -- the R1 reference seed
GDANSK = "I40413290"        # University of Gdansk -- panel_v2 D19 seed
IFPEN = "I265217849"        # IFP Energies nouvelles -- the RTO case

TWO = [STRASBOURG, GDANSK]
THREE = [STRASBOURG, GDANSK, IFPEN]
SIZE_TO_IDS = {2: TWO, 3: THREE}

TREES = ["bestfit", "original", "conservative"]   # config.yaml scenario.toggles.tree, all 3
BASES = ["frac", "full"]

COMPARE_MATRIX = list(itertools.product([2, 3], TREES, BASES))   # 12 cells
COLLAB_MATRIX = list(itertools.product(TREES, BASES))            # 6 cells

# Round-robin one compare_data.SUBJECT_METRICS entry per matrix cell (index by
# position in COMPARE_MATRIX) so all six metrics get exercised somewhere in
# the 12-cell run, at the DATA layer (cheap: no extra AppTest rerun), rather
# than repeating "share" 12 times.
SUBJECT_METRICS = views_compare.SUBJECT_METRICS
# The selector vocabulary and the data layer's METRICS must be the same set --
# a hardcoded length here broke the day a seventh metric (vol) landed.
assert set(SUBJECT_METRICS) == set(K.METRICS)

# Every section's subheader must render, in every cell, proving the whole
# page -- including the two 2B-R-9 frontier charts -- survives the full
# scenario cross product, not just the single scenario
# tests/test_pages_compare.py checks in depth.
EXPECTED_SUBHEADERS = [
    copy.COMPARE["OVERVIEW_HEADER"], copy.COMPARE["VIEW_SUBJECT"],
    copy.COMPARE["VIEW_ERC"], copy.COMPARE["VIEW_SDG"],
    copy.COMPARE["VIEW_FRONTIER_MAP"], copy.COMPARE["VIEW_SHARED_FRONTIER"],
    copy.COMPARE["VIEW_IMPACT"], copy.COMPARE["VIEW_COVERAGE"],
    copy.COMPARE["HANDOFF_HEADER"],
]


@pytest.fixture(scope="module")
def ctx():
    return load_context(str(DATA_DIR))


def _compare_app(ids, tree, basis) -> AppTest:
    at = AppTest.from_file(COMPARE_PAGE, default_timeout=600)
    at.session_state["basket"] = list(ids)
    at.session_state["tree"] = tree
    at.session_state["basis"] = basis
    return at.run()


def _collab_app(pair, tree, basis) -> AppTest:
    at = AppTest.from_file(COLLAB_PAGE, default_timeout=300)
    at.session_state["basket"] = list(pair)
    at.session_state["tree"] = tree
    at.session_state["basis"] = basis
    return at.run()


def _assert_metric_state(ctx_, subs, ids, metric) -> None:
    """One `compare_data.SUBJECT_METRICS` state at field level, checked at
    the data layer (cheap -- no widget interaction)."""
    df = K.metric_frame(ctx_, subs, list(ids), "field", metric)
    if not K.metric_frame_available(metric, "field"):
        assert df.empty and "reason" in df.attrs
        return
    assert list(df.columns) == K.METRIC_FRAME_COLS
    if metric == "share":
        sums = df.groupby("institution_id")["value"].sum()
        assert len(sums) == len(ids)
        for iid, total in sums.items():
            assert total == pytest.approx(1.0, abs=1e-6), (metric, iid, total)
    elif metric == "si":
        assert (df["ref_value"].dropna() == 1.0).all(), "SI's reference line must always be 1.0"
    elif metric == "dynamics":
        note = df["denominator"].iloc[0] if len(df) else ""
        assert f"{K.DYNAMICS_W1[0]}-{K.DYNAMICS_W1[1]}" in note
        assert f"{K.DYNAMICS_W2[0]}-{K.DYNAMICS_W2[1]}" in note
    # pp / vol_top10 / sdg_share: the columns/no-raise check above is the
    # matrix's own job here -- tests/test_pages_compare.py already covers
    # each of these in full detail at one scenario.


def _assert_frontier(ctx_, subs, ids) -> None:
    """2B-R-9's two charts, at the data layer, for every cell."""
    pooled = K.frontier_pooled(ctx_, subs, list(ids), 60)
    shared = K.shared_frontier(ctx_, subs, list(ids))
    if pooled.empty:
        assert shared.empty
        return
    owners = set(pooled["owner"].unique())
    assert owners <= (set(ids) | {"shared"}), owners
    vols = pooled["combined_vol"].to_numpy()
    assert np.all(vols[:-1] >= vols[1:]), "frontier_pooled must be sorted by combined_vol, descending"
    assert (shared["owner"] == "shared").all() if len(shared) else True
    # shared_frontier is UNCAPPED (2B-R-9): it can hold topics outside the
    # top_n=60 slice `pooled` was capped to, so it is compared against the
    # FULL (uncapped) pool frame, not `pooled` itself.
    full_pool = K._frontier_pool_frame(ctx_, subs, list(ids))
    assert set(shared["topic_id"]) == set(full_pool.loc[full_pool["owner"] == "shared", "topic_id"])
    assert set(pooled.loc[pooled["owner"] == "shared", "topic_id"]) <= set(shared["topic_id"])


# --------------------------------------------------------- Compare matrix --

@pytest.mark.parametrize(
    "size,tree,basis", COMPARE_MATRIX,
    ids=[f"k{size}_{tree}_{basis}" for size, tree, basis in COMPARE_MATRIX])
def test_compare_matrix_cell(size, tree, basis, ctx):
    ids = SIZE_TO_IDS[size]
    cell_index = COMPARE_MATRIX.index((size, tree, basis))
    at = _compare_app(ids, tree, basis)
    assert not at.exception, (size, tree, basis, [str(e) for e in at.exception])

    # -- every section renders (proves the frontier map / diverging pair and
    # every other view survive this scenario, not just the default one).
    subheaders = [s.value for s in at.subheader]
    for expected in EXPECTED_SUBHEADERS:
        assert expected in subheaders, (size, tree, basis, expected, subheaders)
    assert any(s.startswith("Trends in the") for s in subheaders), (size, tree, basis, subheaders)

    # -- legend swatch count == basket size, and the exact markup is on the
    # page (test_pages_compare.py's own idiom).
    names = views_compare._names(ctx, ids)
    slots = views_compare._slots(ctx, ids)
    legend_html = charts_compare.institution_legend_html(names, slots)
    assert legend_html.count("background:") == len(ids), (size, tree, basis, legend_html)
    rendered = [m.value for m in at.markdown]
    assert legend_html in rendered, (size, tree, basis, "legend markup missing from the page")

    # -- basis == "full": the ERC and SDG captions carry FRACTIONAL_ONLY_PANEL;
    # basis == "frac": neither does.
    captions = [c.value for c in at.caption]
    if basis == "full":
        assert copy.FIND["FRACTIONAL_ONLY_PANEL"] in captions, (size, tree, basis, captions)
    else:
        assert copy.FIND["FRACTIONAL_ONLY_PANEL"] not in captions, (size, tree, basis, captions)

    # -- overview: one row per compared institution (2B-R-7 KPI row).
    overview = K.overview(ctx, ids)
    assert len(overview) == len(ids)
    assert list(overview.columns) == K.OVERVIEW_COLS

    # -- one SUBJECT_METRICS state per cell, round-robin (all six covered
    # across the 12-cell matrix).
    subs = _subs(tree, basis)
    metric = SUBJECT_METRICS[cell_index % len(SUBJECT_METRICS)]
    _assert_metric_state(ctx, subs, ids, metric)

    # -- the two 2B-R-9 frontier charts.
    _assert_frontier(ctx, subs, ids)

    # -- impact floor toggle 30 -> 10 never REDUCES the union row count (A1: a
    # lower floor only ADDS subfields to the union, never removes one).
    high, low = views_compare.IMPACT_FLOORS
    assert high > low
    union_high = views_compare._impact_subfields(tuple(ids), tree, high)
    union_low = views_compare._impact_subfields(tuple(ids), tree, low)
    assert len(union_low) >= len(union_high), (
        size, tree, basis, len(union_low), len(union_high))
    assert union_low["subfield_id"].nunique() >= union_high["subfield_id"].nunique()

    # -- the deep link the page prints round-trips through selection.parse_query
    # (k in {2, 3} never exceeds state.COMPARE_CAP == 3 -- nothing truncated).
    codes = [c.value for c in at.get("code")]
    link = selection.deeplink("compare", ids)
    assert link in codes, (size, tree, basis, codes)
    parsed = selection.parse_query({"compare": link.split("=", 1)[1]}, ids)
    assert parsed["compare"] == list(ids), (size, tree, basis, parsed)


def test_compare_matrix_covers_the_full_cross_product():
    """Non-vacuity of the matrix itself: 2 sizes x 3 trees x 2 bases, no
    accidental collapse (e.g. a broken itertools.product call producing far
    fewer cells than the brief's 12)."""
    assert len(COMPARE_MATRIX) == 12
    assert len({(s, t, b) for s, t, b in COMPARE_MATRIX}) == 12


def test_switching_the_subject_metric_widget_survives_across_the_matrix_scenarios():
    """ONE widget-level check (not the whole matrix -- test_pages_compare.py
    already drives this radio exhaustively at the default scenario): the
    "Compare by" control itself survives a metric switch on a NON-default
    (tree, basis) pair, proving this file's own AppTest fixture -- not just
    the data layer -- carries the metric-selector state change."""
    at = _compare_app(THREE, "conservative", "full")
    assert not at.exception
    at.radio(key="cmp_metric_subject").set_value(
        views_compare.METRIC_LABELS["si"]).run()
    assert not at.exception
    assert at.session_state["cmp_metric_subject"] == views_compare.METRIC_LABELS["si"]
    captions = [c.value for c in at.caption]
    assert copy.FIND["CAPTION_SI"] in captions   # only drawn when metric == "si"


# ------------------------------------------------------- Collaborate matrix --

@pytest.mark.parametrize(
    "tree,basis", COLLAB_MATRIX, ids=[f"{t}_{b}" for t, b in COLLAB_MATRIX])
def test_collab_matrix_cell_shared_topics_matches_engine_l3(tree, basis, ctx):
    a, b = STRASBOURG, GDANSK
    at = _collab_app((a, b), tree, basis)
    assert not at.exception, (tree, basis, [str(e) for e in at.exception])

    df = views_collab._shared_frame(a, b, tree, basis)
    page_score = float(df["min_share"].sum())

    subs = _subs(tree, basis)
    l3 = rank_all(ctx, subs, a)["L3"]
    engine_score = float(l3["scores"][ctx["id_pos"][b]])

    # tests/test_collab_data.py's OWN tolerance convention: atol=1e-6 (its
    # tighter check) on the frac/bestfit default, rtol=1e-5 wherever basis
    # or tree departs from that default (test_shared_topics_tree_invariant,
    # test_shared_topics_basis_full) -- basis="full" resums float32 vol_full-
    # normalised shares in a different order than the frac path, which moves
    # the last ULPs (same class of drift as the numpy-float32-sum-memory-
    # order lesson: bit-identical inputs, different accumulation order, ~1e-6
    # noise). A fixed abs=1e-6 is exactly what trips on that noise at full
    # basis while staying valid at frac -- so match K's own two-tier rule
    # instead of tightening past what the float32 path can deliver.
    tol = dict(rel=0, abs=1e-6) if (tree, basis) == ("bestfit", "frac") else dict(rel=1e-5, abs=1e-6)
    assert page_score == pytest.approx(engine_score, **tol), (
        tree, basis, page_score, engine_score)


def test_collab_matrix_covers_the_full_cross_product():
    """Non-vacuity: 3 trees x 2 bases, no accidental collapse."""
    assert len(COLLAB_MATRIX) == 6
    assert len({(t, b) for t, b in COLLAB_MATRIX}) == 6

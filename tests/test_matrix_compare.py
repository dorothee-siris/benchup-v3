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
for one pair (6 cells): renders with no exception. 2B-R2-12 RETIRED this
half's original cross-check -- the page's top-shared-topics section used to
be `views_collab._shared_frame`, ranked by `min_share` (the engine's own L3
lens score, an each-institution's-own-portfolio-share quantity); it is now
`views_collab._joint_frame` -> `collab_data.joint_profile`, ranked by
`vol_total` off the shipped, floor-5/top-100 `collab_pair_topics.parquet`
(the pair's ACTUAL joint-corpus volume per topic -- a different quantity
entirely, so a Sigma(min_share) == L3-score identity no longer holds for
what the page renders). `collab_data.shared_topics` itself is untouched and
still equals L3 (test_collab_data.py keeps that pin) -- it is simply not on
this page's render path any more. What DOES generalise across the six cells:
`collab_pair_topics.parquet` carries no tree or basis dimension at all, so
every per-topic value column the page shows must be IDENTICAL to the raw
shipped table, in every one of the six cells -- checked here against a
fresh, independent `pd.read_parquet` of that file, not through `collab_data`'s
own cached loader.

Run from cwd `app/`:  python -m pytest tests/test_matrix_compare.py -q
"""
from __future__ import annotations

import itertools
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from lib import charts_compare, collab_data as CL, compare_data as K, copy, selection, state, views_compare, views_collab
from lib.data_cache import DATA_DIR
from lib.engine import load_context
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
# 2B-R2-3: the selector vocabulary (`charts_compare.SELECTOR_METRICS`, what
# the "Compare by" radio offers) and the data layer's `K.METRICS` are NO
# LONGER the same set BY DESIGN -- `vol_top10` is DATA ONLY (it feeds the PP
# view's volume gutter, 2B-R2-3) and was deliberately retired as a pickable
# tab; `vol` is the opposite direction, a metric CD3 added to both. So the
# live contract is: every selector option must have a data path (subset,
# not equality), and the data-layer-only extras are the named exceptions.
# A hardcoded length/equality here is exactly what broke the day `vol_top10`
# was retired as a selector option while staying in `K.METRICS` as data.
#
# 2C (Stream CD5, BUILD_PLAN_2C.md S3 CD5) RE-TIGHTENED (Stream VC): `fwci`
# joined `K.METRICS` a wave ahead of `charts_compare.SELECTOR_METRICS` being
# wired to offer it -- VC's own wave (BUILD_PLAN_2C.md S3 VC, D2) has now
# added `fwci` to `SELECTOR_METRICS` (Subject/ERC/SDG "Compare by" selector,
# all four grains), so the vocabulary is back in sync and the exclusion set
# narrows to its pre-2C shape: `vol_top10` alone (2B-R2-3, data-only by
# ruling -- its mass rides the PP view's own gutter/hover instead of a tab).
assert set(SUBJECT_METRICS) <= set(K.METRICS), (SUBJECT_METRICS, K.METRICS)
assert set(K.METRICS) - set(SUBJECT_METRICS) == {"vol_top10"}, (
    "the only data-only, non-selectable metric should be vol_top10 (2B-R2-3); "
    f"got {set(K.METRICS) - set(SUBJECT_METRICS)}")

# Every section's subheader must render, in every cell, proving the whole
# page -- including the two 2B-R-9 frontier charts -- survives the full
# scenario cross product, not just the single scenario
# tests/test_pages_compare.py checks in depth.
# 2BR3 VC (BUILD_PLAN_2BR3.md SS3 VC): the old pair hand-off section
# (copy.COMPARE["HANDOFF_HEADER"]) is DELETED outright -- the selection
# rework (`selection.slots_row`/`render_sidebar`) supersedes it, Collaborate's
# own entry point is its own slots, not a button on this page (TEV-U wave 3
# cleanup, MT sweep casualty #1).
EXPECTED_SUBHEADERS = [
    copy.COMPARE["OVERVIEW_HEADER"], copy.COMPARE["VIEW_SUBJECT"],
    copy.COMPARE["VIEW_ERC"], copy.COMPARE["VIEW_SDG"],
    copy.COMPARE["VIEW_FRONTIER_MAP"], copy.COMPARE["VIEW_SHARED_FRONTIER"],
    copy.COMPARE["VIEW_IMPACT"], copy.COMPARE["VIEW_COVERAGE"],
]


@pytest.fixture(scope="module")
def ctx():
    return load_context(str(DATA_DIR))


def _seed_slots(at: AppTest, view: str, ids, n: int) -> None:
    """2BR3 SEL (plan §3 SEL, ruling 1): `views_compare.render()`/
    `views_collab.render()` no longer read the basket directly -- they call
    `selection.slots_row(view, n)`, which reads/writes its OWN per-(view,
    index) session keys (`slot_<view>_<i>`) and only auto-fills them from a
    `?compare=`/`?pair=` URL param on first load. An AppTest session has no
    URL, so the slots have to be seeded directly, exactly the shape
    `slots_row` itself would have written them to (`selection.SLOT_EMPTY`
    padding) -- and the one-shot hydration guard set so the page's own
    (no-op, empty-query) hydration pass never overwrites them (TEV-U wave 3
    re-cut, MT sweep casualty #1)."""
    from lib.selection import SLOT_EMPTY

    padded = (list(ids) + [SLOT_EMPTY] * n)[:n]
    at.session_state[f"_slots_hydrated_{view}"] = True
    for i, iid in enumerate(padded):
        at.session_state[f"slot_{view}_{i}"] = iid


def _compare_app(ids, tree, basis) -> AppTest:
    at = AppTest.from_file(COMPARE_PAGE, default_timeout=600)
    at.session_state["basket"] = list(ids)
    at.session_state["tree"] = tree
    at.session_state["basis"] = basis
    _seed_slots(at, "compare", ids, state.COMPARE_CAP)
    return at.run()


def _collab_app(pair, tree, basis) -> AppTest:
    at = AppTest.from_file(COLLAB_PAGE, default_timeout=300)
    at.session_state["basket"] = list(pair)
    at.session_state["tree"] = tree
    at.session_state["basis"] = basis
    _seed_slots(at, "collab", pair, state.COLLAB_CAP)
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


def _assert_frontier(ctx_, subs, ids, pool: str) -> None:
    """2B-R-9's two charts, at the data layer, for every cell -- cycled over
    `K.FRONTIER_POOLS` (2B-R2-10's pool selector: "volume" = top-25%-frontier
    ranked by combined volume, "elite" = global top-10% most frontier) so
    both modes get exercised somewhere across the matrix, the same
    round-robin idiom as SUBJECT_METRICS above."""
    pooled = K.frontier_pooled(ctx_, subs, list(ids), 60, pool)
    shared = K.shared_frontier(ctx_, subs, list(ids), pool)
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
    full_pool = K._frontier_pool_frame(ctx_, subs, list(ids), pool)
    assert set(shared["topic_id"]) == set(full_pool.loc[full_pool["owner"] == "shared", "topic_id"])
    assert set(pooled.loc[pooled["owner"] == "shared", "topic_id"]) <= set(shared["topic_id"])
    if pool == "elite":
        # 2B-R2-10: "elite" restricts to the global top-10% most-frontier
        # topics -- every pooled topic must be in that fixed set.
        elite_ids = K._elite_frontier_topic_ids(ctx_)
        assert set(pooled["topic_id"]) <= elite_ids, (pool, "elite pool leaked a non-elite topic")


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
    # 2BR3 VC: "Trends in the N subfields" is DELETED outright (CD4 dropped
    # compare_data.trends_subfields, the function it read) -- assert its
    # ABSENCE now, the inverse of the old presence check (TEV-U wave 3).
    assert not any(s.startswith("Trends in the") for s in subheaders), (size, tree, basis, subheaders)

    # -- legend swatch count == basket size, and the exact markup is on the
    # page (test_pages_compare.py's own idiom).
    names = views_compare._names(ctx, ids)
    slots = views_compare._slots(ctx, ids)
    legend_html = charts_compare.institution_legend_html(names, slots)
    assert legend_html.count("background:") == len(ids), (size, tree, basis, legend_html)
    rendered = [m.value for m in at.markdown]
    assert legend_html in rendered, (size, tree, basis, "legend markup missing from the page")

    # -- basis == "full": the ERC/SDG chart notes carry FRACTIONAL_ONLY_PANEL;
    # basis == "frac": neither does. 2B-R2-8 moved this from a bare
    # `st.caption` (checked via `at.caption`) into the `?` tooltip of
    # `charts_compare.chart_note` (views_compare._taxon_tip), rendered as an
    # HTML `title=` attribute inside `st.markdown(..., unsafe_allow_html=True)`
    # -- so it now has to be found as a substring of the rendered markdown,
    # not as an exact `at.caption` element.
    rendered_md = "\n".join(rendered)
    if basis == "full":
        assert copy.FIND["FRACTIONAL_ONLY_PANEL"] in rendered_md, (size, tree, basis)
    else:
        assert copy.FIND["FRACTIONAL_ONLY_PANEL"] not in rendered_md, (size, tree, basis)

    # -- overview: one row per compared institution (2B-R-7 KPI row).
    overview = K.overview(ctx, ids)
    assert len(overview) == len(ids)
    assert list(overview.columns) == K.OVERVIEW_COLS

    # -- one SUBJECT_METRICS state per cell, round-robin (all six covered
    # across the 12-cell matrix).
    subs = _subs(tree, basis)
    metric = SUBJECT_METRICS[cell_index % len(SUBJECT_METRICS)]
    _assert_metric_state(ctx, subs, ids, metric)

    # -- the two 2B-R-9 frontier charts, cycled over the 2B-R2-10 pool
    # selector (both "volume" and "elite" get exercised across the matrix).
    pool = K.FRONTIER_POOLS[cell_index % len(K.FRONTIER_POOLS)]
    _assert_frontier(ctx, subs, ids, pool)

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
    # 2B-R2-8 folded this into the `?` tooltip of `charts_compare.chart_note`
    # (views_compare._metric_tip), an HTML `title=` attribute inside
    # `st.markdown(..., unsafe_allow_html=True)` -- no longer a bare
    # `st.caption`, so it is found in the rendered markdown, not `at.caption`.
    rendered_md = "\n".join(m.value for m in at.markdown)
    assert copy.FIND["CAPTION_SI"] in rendered_md   # only drawn when metric == "si"


# ------------------------------------------------------- Collaborate matrix --

@pytest.mark.parametrize(
    "tree,basis", COLLAB_MATRIX, ids=[f"{t}_{b}" for t, b in COLLAB_MATRIX])
def test_collab_matrix_cell_joint_topics_match_the_shipped_pair_table(tree, basis, ctx):
    """2B-R2-12 re-cut (`views_collab._shared_frame` is gone -- see the module
    docstring): the page's top-shared-topics section reads `collab_pair_
    topics.parquet` through `collab_data.joint_profile`, a table with NO tree
    or basis dimension. So every cell of this matrix must show the exact same
    per-topic values, independently recomputed here with a fresh
    `pd.read_parquet` of the shipped file (not `collab_data`'s cached
    loader)."""
    a, b = STRASBOURG, GDANSK
    at = _collab_app((a, b), tree, basis)
    assert not at.exception, (tree, basis, [str(e) for e in at.exception])

    frame = views_collab._joint_frame(a, b, tree, basis)
    assert frame is not None, (tree, basis, "Strasbourg x Gdansk must clear PAIR_TOPICS_FLOOR")
    topics = frame["topics"].set_index("topic_id").sort_index()
    assert len(topics) <= CL.PAIR_TOPICS_TOP_N
    assert frame["meta"]["floor"] == CL.PAIR_TOPICS_FLOOR

    # 2BR3 P7 v2 schema (TEV-U wave 3 re-cut, MT sweep casualty #1): the
    # primary volume column is `vol` now (was `vol_total`; `vol_2025` also
    # dropped) -- CD4 already updated CL.JOINT_ROLLUP_VALUE_COLS to the new
    # names (vol_w1/vol_w2/vol/n_covered/n_top10/n_sdg), read dynamically
    # below so this test tracks any future rename with no edit here.
    value_cols = CL.JOINT_ROLLUP_VALUE_COLS
    sorted_by_vol = frame["topics"]["vol"].to_numpy()
    assert np.all(sorted_by_vol[:-1] >= sorted_by_vol[1:]), "joint topics must be sorted by vol_total, descending"
    assert (topics["n_top10"] <= topics["n_covered"]).all(), (tree, basis, "n_top10 must never exceed n_covered")

    raw = pd.read_parquet(DATA_DIR / "collab_pair_topics.parquet")
    lo, hi = (a, b) if a < b else (b, a)
    raw_rows = raw[(raw["a"] == lo) & (raw["b"] == hi)].copy()
    raw_rows["topic_id"] = raw_rows["topic_id"].astype(str)
    raw_rows = raw_rows.set_index("topic_id").sort_index()
    assert set(topics.index) == set(raw_rows.index), (tree, basis, "topic set must not move with tree/basis")
    got = topics[value_cols].astype(float).sort_index()
    want = raw_rows.loc[got.index, value_cols].astype(float)
    np.testing.assert_allclose(got.to_numpy(), want.to_numpy(), rtol=0, atol=1e-9,
                               err_msg=f"{tree},{basis}: joint-topic values must match the shipped table exactly")


def test_collab_matrix_covers_the_full_cross_product():
    """Non-vacuity: 3 trees x 2 bases, no accidental collapse."""
    assert len(COLLAB_MATRIX) == 6
    assert len({(t, b) for t, b in COLLAB_MATRIX}) == 6

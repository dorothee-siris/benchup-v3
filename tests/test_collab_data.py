"""
Stream K -- lib/collab_data.py acceptance tests (BUILD_PLAN_2B.md S4/S5,
Tier A). Anchors are concrete values recomputed from app/data/*.parquet on
2026-08-29 (env-app, bestfit/frac default scenario) -- see
V3/progress/2B_K.md for the recomputation script.

Run: python -m pytest tests/test_collab_data.py -q
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from lib import collab_data as CL
from lib.engine import build_substrates, load_context

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

STRASBOURG, IFPEN, GDANSK, ISCTE, SORBONNE, ETH = (
    "I68947357", "I265217849", "I40413290", "I110026055", "I39804081", "I35440088")


@pytest.fixture(scope="module")
def ctx():
    return load_context(DATA_DIR)


@pytest.fixture(scope="module")
def subs_bestfit(ctx):
    return build_substrates(ctx)  # default: bestfit / frac


def _l3_score(ctx, subs, a, b) -> float:
    """Direct hand-recomputation of the engine's own L3 histogram-
    intersection score (BUILD_PLAN_2A.md `lenses.rank_all`'s L3 branch):
    Sigma_topic min(share_a, share_b), no further division."""
    a_idx, b_idx = ctx["id_pos"][a], ctx["id_pos"][b]
    l3 = subs["l3"]["share"]
    return float(np.minimum(l3[a_idx], l3[b_idx]).astype("float64").sum())


# --------------------------------------------------------- shared_topics ----

@pytest.mark.parametrize("a,b,want_l3,want_rows", [
    (STRASBOURG, SORBONNE, 0.558309, 2536),
    (STRASBOURG, GDANSK, 0.272140, 1581),
    (IFPEN, SORBONNE, 0.090119, 308),
    (GDANSK, ISCTE, 0.189873, 727),
    (ETH, STRASBOURG, 0.350223, 2205),
])
def test_shared_topics_sum_equals_l3_score(ctx, subs_bestfit, a, b, want_l3, want_rows):
    """Engine identity (WT-2B #10): Sigma(min_share) over `shared_topics`
    exactly equals the L3 lens score for the pair -- both are the SAME sum
    over the SAME matrix, just one restricted to the nonzero-overlap rows."""
    df = CL.shared_topics(ctx, subs_bestfit, a, b)
    assert list(df.columns) == CL.SHARED_TOPICS_COLS
    l3_direct = _l3_score(ctx, subs_bestfit, a, b)
    np.testing.assert_allclose(l3_direct, want_l3, atol=1e-5)
    np.testing.assert_allclose(float(df["min_share"].sum()), l3_direct, rtol=1e-5)
    assert len(df) == want_rows


def test_shared_topics_sorted_desc_and_keywords_present(ctx, subs_bestfit):
    df = CL.shared_topics(ctx, subs_bestfit, STRASBOURG, SORBONNE)
    assert df["min_share"].is_monotonic_decreasing
    assert (df["share_a"] > 0).all() and (df["share_b"] > 0).all()
    assert df["keywords"].notna().all()
    assert (df["keywords"].str.contains(r"\|")).any()  # `|`-delimited, WT-2B #9
    top = df.iloc[0]
    assert top["topic_id"] == "T11475"
    assert top["subfield_name"] == "Geography, Planning and Development"


def test_shared_topics_tree_invariant(ctx):
    """L3 is topic-grain -- the identity holds under a different tree too
    (WT-2B #10)."""
    subs_original = build_substrates(ctx, tree="original", basis="frac")
    l3_direct = _l3_score(ctx, subs_original, STRASBOURG, SORBONNE)
    df = CL.shared_topics(ctx, subs_original, STRASBOURG, SORBONNE)
    np.testing.assert_allclose(float(df["min_share"].sum()), l3_direct, rtol=1e-5)


def test_shared_topics_basis_full(ctx):
    """The identity also holds on basis='full' (recomputed vol_full-
    normalised share, not `topics_all.share_frac` verbatim)."""
    subs_full = build_substrates(ctx, tree="bestfit", basis="full")
    l3_direct = _l3_score(ctx, subs_full, STRASBOURG, SORBONNE)
    df = CL.shared_topics(ctx, subs_full, STRASBOURG, SORBONNE)
    np.testing.assert_allclose(float(df["min_share"].sum()), l3_direct, rtol=1e-5)


# -------------------------------------------------- gaps() DELETED (2B-R2-11f)
# `collab_data.gaps()` (the "what B publishes that A doesn't" footprint-gap
# table) and its `GAPS_COLS`/`_top10_subfield_ids` are REMOVED this round --
# `untapped()` below is the ruled replacement (an expected-vs-observed JOINT
# gap, not a footprint gap). Its old test suite is deleted with it.


# ----------------------------------------------------------- breadth_jaccard-

@pytest.mark.parametrize("a,b,want", [
    (STRASBOURG, SORBONNE, {"jaccard": 0.6997792494481236, "n_a": 2741, "n_b": 3419, "n_shared": 2536}),
    (STRASBOURG, GDANSK, {"jaccard": 0.4779322853688029, "n_a": 2741, "n_b": 2148, "n_shared": 1581}),
    (IFPEN, SORBONNE, {"jaccard": 0.08974358974358974, "n_a": 321, "n_b": 3419, "n_shared": 308}),
    (GDANSK, ISCTE, {"jaccard": 0.28376268540202965, "n_a": 2148, "n_b": 1141, "n_shared": 727}),
])
def test_breadth_jaccard_anchor(ctx, subs_bestfit, a, b, want):
    got = CL.breadth_jaccard(ctx, subs_bestfit, a, b)
    assert got["n_a"] == want["n_a"]
    assert got["n_b"] == want["n_b"]
    assert got["n_shared"] == want["n_shared"]
    np.testing.assert_allclose(got["jaccard"], want["jaccard"], rtol=1e-9)


def test_breadth_jaccard_recomputed_by_hand(ctx, subs_bestfit):
    """Independent by-hand recomputation (set arithmetic on the raw L3
    matrix, no reuse of the function's own code path) for one pair."""
    a_idx, b_idx = ctx["id_pos"][STRASBOURG], ctx["id_pos"][SORBONNE]
    l3 = subs_bestfit["l3"]["share"]
    topics_a = set(np.nonzero(l3[a_idx] > 0)[0].tolist())
    topics_b = set(np.nonzero(l3[b_idx] > 0)[0].tolist())
    inter = topics_a & topics_b
    union = topics_a | topics_b
    want_jaccard = len(inter) / len(union)
    got = CL.breadth_jaccard(ctx, subs_bestfit, STRASBOURG, SORBONNE)
    np.testing.assert_allclose(got["jaccard"], want_jaccard, rtol=1e-9)
    assert got["n_shared"] == len(inter)


def test_breadth_jaccard_symmetric(ctx, subs_bestfit):
    fwd = CL.breadth_jaccard(ctx, subs_bestfit, STRASBOURG, GDANSK)
    bwd = CL.breadth_jaccard(ctx, subs_bestfit, GDANSK, STRASBOURG)
    np.testing.assert_allclose(fwd["jaccard"], bwd["jaccard"], rtol=1e-12)
    assert fwd["n_a"] == bwd["n_b"] and fwd["n_b"] == bwd["n_a"]
    assert fwd["n_shared"] == bwd["n_shared"]


CNRS = "I1294671590"


# ============================================================================
# 2B-R (Stream CD, BUILD_PLAN_2BR.md S1 2B-R-10, S4) -- anchors recomputed
# 2026-08-30 via an INDEPENDENT code path (plain pandas over
# app/data/collab_pairs.parquet / collab_pair_topics.parquet, no import of
# lib.collab_data) -- see V3/progress/2BR_CD.md for the script.
# ============================================================================

def test_pulse_pinned_anchor_cnrs_strasbourg_table_order(ctx):
    """Manager-pinned fact (BUILD_PLAN_2BR.md CD brief): copubs_total 12694,
    rank_in_b 1 -- called in the TABLE's own a<b order (CNRS < Strasbourg
    lexicographically)."""
    got = CL.pulse(ctx, CNRS, STRASBOURG)
    assert got["copubs_total"] == 12694
    assert got["rank_in_a"] == 16
    assert got["rank_in_b"] == 1
    want_years = {2020: 2284, 2021: 2357, 2022: 2190, 2023: 2123, 2024: 2034, 2025: 1706}
    for y, v in want_years.items():
        row = got["yearly"].loc[got["yearly"]["year"] == y, "copubs"].iloc[0]
        assert int(row) == v
    assert got["yearly"]["copubs"].sum() == 12694


def test_pulse_swapped_call_order_reorients_ranks(ctx):
    """Calling pulse(Strasbourg, CNRS) -- the OPPOSITE of the table's own
    a<b order -- must swap rank_in_a/rank_in_b to stay CALLER-relative:
    rank_in_a (rank of CNRS among Strasbourg's partners) == 1, rank_in_b
    (rank of Strasbourg among CNRS's partners) == 16."""
    got = CL.pulse(ctx, STRASBOURG, CNRS)
    assert got["copubs_total"] == 12694
    assert got["rank_in_a"] == 1
    assert got["rank_in_b"] == 16


def test_pulse_denominators_and_share_anchor(ctx):
    """Independently summed off index.vol_full_by_year_this_run (2020-2025):
    Strasbourg 22865, CNRS 281939 (raw pandas over index.parquet, not
    lib.collab_data's own _parse_packed_years call site)."""
    got = CL.pulse(ctx, STRASBOURG, CNRS)
    np.testing.assert_allclose(got["denominator_a"], 22865.0, rtol=1e-9)
    np.testing.assert_allclose(got["denominator_b"], 281939.0, rtol=1e-9)
    np.testing.assert_allclose(got["share_of_a"], 12694 / 22865.0, rtol=1e-9)
    np.testing.assert_allclose(got["share_of_b"], 12694 / 281939.0, rtol=1e-9)


def test_pulse_none_for_a_pair_that_never_co_published(ctx):
    """Two small, unrelated institutions with NO row in collab_pairs at all
    (floor 1 -- absent truly means zero co-publications, 2BR A1)."""
    a, b = "I1305429183", "I1308570094"
    import pandas as _pd
    pairs = _pd.read_parquet(Path(ctx["data_dir"]) / "collab_pairs.parquet")
    lo, hi = sorted([a, b])
    assert pairs[(pairs["a"] == lo) & (pairs["b"] == hi)].empty  # precondition, independently checked
    assert CL.pulse(ctx, a, b) is None


def test_joint_profile_anchor_strasbourg_ifpen(ctx, subs_bestfit):
    """RE-DERIVED 2BR3 (BUILD_PLAN_2BR3.md Stream TEV-D, item 3 -- `vol_total`
    -> `vol`, rebased all-types/2020-2025 -> CORE-AR articles+reviews/2020-
    2024, WT_2BR3.md task 6 row 9's exact 'joint 1,882 vs covered 1,642'
    mismatch class). Independently recomputed off `collab_pair_topics.
    parquet` v2: 11 topic rows (was 12 -- one topic's works all fall outside
    the narrower CORE-AR basis), Sigma(vol) == 14 == collab_pairs.core_total
    for this pair (below the top-100 cap so the FULL CORE-AR joint corpus is
    captured, no truncation) -- NO LONGER equal to `pulse`'s `copubs_total`
    (15, all-types/2020-2025, a DIFFERENT basis by design, ruling 3): the two
    numbers are now allowed, EXPECTED, to differ. `sdg_tagged_total` stays 0
    (still true on the narrower CORE-AR population). `erc_top_panel`/`_n`/
    `labelled_n` are UNCHANGED ('PE3'/6/15) -- WT_2BR3.md SS0 gap g moved
    these to `collab_pairs.parquet` v2 on their OLD, undisturbed basis
    (disclosed, not recomputed on CORE-AR)."""
    got = CL.joint_profile(ctx, subs_bestfit, STRASBOURG, IFPEN)
    assert got is not None
    assert got["meta"]["n_topics_shown"] == 11
    assert int(got["topics"]["vol"].sum()) == 14

    pairs = CL._load_collab_pairs(ctx)
    lo, hi = sorted([STRASBOURG, IFPEN])
    prow = pairs[(pairs["a"] == lo) & (pairs["b"] == hi)].iloc[0]
    assert int(prow["core_total"]) == 14
    assert int(got["topics"]["vol"].sum()) == int(prow["core_total"])

    pulse_ab = CL.pulse(ctx, STRASBOURG, IFPEN)
    assert pulse_ab["copubs_total"] == 15  # UNCHANGED (pulse stays all-types/2020-2025, ruling 3)
    assert pulse_ab["copubs_total"] != int(got["topics"]["vol"].sum())  # the two bases now legitimately diverge

    assert got["sdg_tagged_total"] == 0
    assert got["erc"]["panel_idx"] == "PE3"
    assert got["erc"]["panel_n"] == 6
    assert got["erc"]["labelled_n"] == 15
    assert list(got["topics"].columns) == CL.JOINT_TOPICS_COLS
    assert got["topics"]["vol"].is_monotonic_decreasing
    assert got["fields"]["vol"].sum() == got["topics"]["vol"].sum()
    assert got["subfields"]["vol"].sum() == got["topics"]["vol"].sum()


def test_joint_profile_below_floor_returns_none(ctx, subs_bestfit):
    """A pair with copubs_total in {1..4} (below the regenerated 2B-R2-12
    PAIR_TOPICS_FLOOR=5) has ZERO rows in collab_pair_topics --
    independently verified here -- and joint_profile must return None, not
    an empty-but-present frame."""
    pairs = _load_pairs_raw(ctx)
    below = pairs[pairs["copubs_total"].between(1, 4)].iloc[0]
    a, b = below["a"], below["b"]
    topics = _load_topics_raw(ctx)
    assert topics[(topics["a"] == a) & (topics["b"] == b)].empty
    assert CL.joint_profile(ctx, subs_bestfit, a, b) is None
    assert CL.PAIR_TOPICS_FLOOR == 5
    assert CL.PAIR_TOPICS_TOP_N == 100


def _load_pairs_raw(ctx):
    import pandas as _pd
    return _pd.read_parquet(Path(ctx["data_dir"]) / "collab_pairs.parquet")


def _load_topics_raw(ctx):
    import pandas as _pd
    return _pd.read_parquet(Path(ctx["data_dir"]) / "collab_pair_topics.parquet")


def test_untapped_gap_positive_sorted_and_capped(ctx, subs_bestfit):
    got = CL.untapped(ctx, subs_bestfit, STRASBOURG, IFPEN, top_n=10)
    df = got["topics"]
    assert list(df.columns) == CL.UNTAPPED_COLS
    assert len(df) <= 10
    assert (df["gap"] > 0).all()
    assert df["gap"].is_monotonic_decreasing
    np.testing.assert_allclose((df["joint_expected"] - df["joint_observed"]).to_numpy(dtype="float64"),
                               df["gap"].to_numpy(dtype="float64"), atol=1e-9)


def test_untapped_k_formula_independent_recompute(ctx, subs_bestfit):
    """k = copubs_total / min(a_total, b_total) -- independently recomputed
    (Strasbourg/IFPEN): 15 / min(22865, 1247) = 0.012028869286287089."""
    got = CL.untapped(ctx, subs_bestfit, STRASBOURG, IFPEN)
    np.testing.assert_allclose(got["k"], 0.012028869286287089, rtol=1e-9)


def test_untapped_self_pair_never_raises_and_types_are_frames(ctx, subs_bestfit):
    """Defensive edge case: a self-pair (a==b, k undefined via pulse since a
    pair never co-publishes 'with itself' in collab_pairs -- absent from the
    table) must return typed frames, never raise. k falls back to 0.0 (no
    pulse row -> smaller==0 guard) rather than NaN propagating into gap."""
    got = CL.untapped(ctx, subs_bestfit, STRASBOURG, STRASBOURG)
    assert isinstance(got["topics"], pd.DataFrame) and list(got["topics"].columns) == CL.UNTAPPED_COLS
    assert got["k"] == 0.0


def test_untapped_return_shape_is_topics_and_k_only(ctx, subs_bestfit):
    """D8 (2C, grill ruling): the extra 'adjacent topics' frame this
    function used to also return is REMOVED end to end -- this pins the
    function's own return shape structurally, not just the render side."""
    got = CL.untapped(ctx, subs_bestfit, STRASBOURG, SORBONNE, top_n=15)
    assert set(got) == {"topics", "k"}


def test_breadth_jaccard_min_full_floor_shrinks_sets(ctx, subs_bestfit):
    subs = subs_bestfit
    """Manager addition 2026-08-29 (WT-2B E5): a publication floor never grows a
    topic set, and min_full=1 equals the nonzero-share rule (every touched
    topic has >= 1 full publication)."""
    from lib import collab_data as CD
    base = CD.breadth_jaccard(ctx, subs, "I68947357", "I40413290")
    one = CD.breadth_jaccard(ctx, subs, "I68947357", "I40413290", min_full=1)
    two = CD.breadth_jaccard(ctx, subs, "I68947357", "I40413290", min_full=2)
    assert one["n_a"] == base["n_a"] and one["n_b"] == base["n_b"]
    assert two["n_a"] <= base["n_a"] and two["n_b"] <= base["n_b"] and two["n_shared"] <= base["n_shared"]
    assert 0.0 <= two["jaccard"] <= 1.0


# ============================================================================
# 2B-R2 (Stream CD3, 2B-R2-11/12) -- collab_pair_topics/fields v3: n_top10/
# n_covered impact columns, NEW field_breakdown(), per-row arrows + live
# OpenAlex deep-dive urls, gaps() deletion. Anchors recomputed 2026-08-31 via
# INDEPENDENT reads of the shipped parquet files (no import of this module's
# own loaders) -- see V3/progress/2BR2_CD3.md for the scripts.
# ============================================================================

def _load_raw_pair_topics():
    return pd.read_parquet(Path(__file__).resolve().parents[1] / "data" / "collab_pair_topics.parquet")


def _load_raw_pair_fields():
    return pd.read_parquet(Path(__file__).resolve().parents[1] / "data" / "collab_pair_fields.parquet")


def test_joint_profile_n_top10_n_covered_anchor(ctx, subs_bestfit):
    """RE-DERIVED 2BR3 (Stream TEV-D, item 3 -- `vol_total` -> `vol`, rebased
    to CORE-AR). T10048 stays CNRS x Strasbourg's largest joint topic even
    under the narrower CORE-AR basis; its `vol` dropped from v1's 384
    (all-types/2020-2025) to 327 (articles+reviews/2020-2024) -- `n_top10`
    is UNCHANGED at 81 (impact-eligible works were already articles+reviews-
    restricted upstream, v1 and v2 alike) and `n_covered` is now numerically
    EQUAL to `vol` (327 == 327: every one of this topic's CORE-AR joint works
    happens to land in a cell with a world threshold -- a coincidence of this
    particular cell, not a new invariant) -- n_top10 <= n_covered <= vol
    still holds, never divide n_top10 by vol, only by n_covered."""
    raw = _load_raw_pair_topics()
    lo, hi = sorted([CNRS, STRASBOURG])
    raw_row = raw[(raw["a"] == lo) & (raw["b"] == hi)].sort_values("vol", ascending=False).iloc[0]
    assert raw_row["topic_id"] == "T10048"
    assert int(raw_row["vol"]) == 327 and int(raw_row["n_top10"]) == 81 and int(raw_row["n_covered"]) == 327

    got = CL.joint_profile(ctx, subs_bestfit, CNRS, STRASBOURG)
    assert got is not None
    row = got["topics"][got["topics"]["topic_id"] == "T10048"].iloc[0]
    assert int(row["vol"]) == 327
    assert int(row["n_top10"]) == 81
    assert int(row["n_covered"]) == 327
    assert (got["topics"]["n_top10"] <= got["topics"]["n_covered"]).all()
    assert (got["topics"]["n_covered"] <= got["topics"]["vol"]).all()
    assert "n_top10" not in got["erc"]  # impact cols live on topics/fields, never the pair-level erc dict


def test_joint_profile_topics_have_no_mean_citations_column_and_meta_says_why(ctx, subs_bestfit):
    got = CL.joint_profile(ctx, subs_bestfit, CNRS, STRASBOURG)
    assert "mean_citations" not in got["topics"].columns
    assert "mean_citations" not in got["fields"].columns  # joint_profile's OWN rollup, not field_breakdown
    assert got["meta"]["mean_citations_note"] == CL.MEAN_CITATIONS_NOTE
    for forbidden in ("2B-R", "BUILD_PLAN", "pipeline", "artefact", ".parquet"):
        assert forbidden not in got["meta"]["note"]
        assert forbidden not in got["meta"]["mean_citations_note"]
        assert forbidden not in got["erc"]["denominator_note"]


def test_field_breakdown_matches_collab_pair_fields_anchor(ctx):
    """RE-DERIVED 2BR3 (BUILD_PLAN_2BR3.md Stream TEV-D, item 3): `vol_total`
    -> `vol` (rebased all-types/2020-2025 -> CORE-AR articles+reviews/2020-
    2024) and `mean_citations` DROPPED entirely, superseded by `fwci_median`
    (ruling 4, SS2.2 dropped_column note). Independent anchor, re-read RAW off
    `collab_pair_fields.parquet` v2 (also cross-referenced against
    `evals/golden_2BR3.json`'s OpenAlex-diagnostic-verified `computed_vol`/
    `computed_n_top10`/`computed_n_covered` for this exact pair/field, see
    `test_golden_numbers.py`): CNRS x Strasbourg's largest joint field
    (field_id 31, Physics and Astronomy) -- vol 1643 (was 1882 under the
    wider all-types/2020-2025 basis -- the exact WT_2BR3.md task 6 row-9
    'joint 1,882 vs covered 1,642' mismatch class, now resolved: vol and
    n_covered are on the SAME basis), n_top10 383 (UNCHANGED -- impact
    eligibility was already articles+reviews-restricted upstream), n_covered
    1642 (UNCHANGED), fwci_median 0.7711243033409119."""
    raw = _load_raw_pair_fields()
    lo, hi = sorted([CNRS, STRASBOURG])
    raw_row = raw[(raw["a"] == lo) & (raw["b"] == hi) & (raw["field_id"] == 31)].iloc[0]
    assert int(raw_row["vol"]) == 1643
    assert int(raw_row["n_top10"]) == 383
    assert int(raw_row["n_covered"]) == 1642
    assert "mean_citations" not in raw.columns  # dropped entirely, not renamed (SS2.2)
    np.testing.assert_allclose(float(raw_row["fwci_median"]), 0.7711243033409119, rtol=1e-6)

    df = CL.field_breakdown(ctx, CNRS, STRASBOURG)
    assert list(df.columns) == CL.FIELD_BREAKDOWN_COLS
    assert "mean_citations" not in df.columns
    row = df[df["field_id"] == 31].iloc[0]
    assert int(row["vol"]) == 1643
    assert int(row["n_top10"]) == 383
    assert int(row["n_covered"]) == 1642
    np.testing.assert_allclose(float(row["fwci_median"]), 0.7711243033409119, rtol=1e-6)
    assert row["field_name"] == "Physics and Astronomy"
    assert df.attrs["note"] == CL.FIELD_BREAKDOWN_NOTE
    assert df.attrs["floor"] == CL.PAIR_TOPICS_FLOOR
    assert (df["n_top10"] <= df["n_covered"]).all()
    assert (df["n_covered"] <= df["vol"]).all()
    assert df["vol"].is_monotonic_decreasing


def test_field_breakdown_empty_below_floor(ctx):
    """A pair below PAIR_TOPICS_FLOOR (or that never co-published) gets an
    empty, correctly-columned frame -- never raises."""
    df = CL.field_breakdown(ctx, "I1305429183", "I1308570094")
    assert list(df.columns) == CL.FIELD_BREAKDOWN_COLS
    assert len(df) == 0


def test_field_breakdown_arrows_and_urls(ctx):
    """Every row carries an arrow in the fixed vocabulary and a live
    OpenAlex url that names both institutions and this field."""
    df = CL.field_breakdown(ctx, CNRS, STRASBOURG)
    assert len(df)
    assert set(df["arrow"]) <= {CL.ARROW_UP, CL.ARROW_DOWN, CL.ARROW_FLAT}
    row31 = df[df["field_id"] == 31].iloc[0]
    from urllib.parse import unquote
    decoded = unquote(row31["url"])
    assert f"authorships.institutions.id:{CNRS}" in decoded
    assert f"authorships.institutions.id:{STRASBOURG}" in decoded
    assert "primary_topic.field.id:31" in decoded


def test_arrow_deadband_hand_recomputed():
    """Independent recompute of `_arrow`'s own formula: mean-annual w2 vs w1
    (windows of 2 and 3 years respectively), deadband 0.5 works/year."""
    assert CL._arrow(30, 20) == CL.ARROW_FLAT   # w1=10.0/yr, w2=10.0/yr -> delta 0.0
    assert CL._arrow(30, 30) == CL.ARROW_UP     # w1=10.0/yr, w2=15.0/yr -> delta +5.0
    assert CL._arrow(60, 20) == CL.ARROW_DOWN   # w1=20.0/yr, w2=10.0/yr -> delta -10.0
    assert CL._arrow(3, 1) == CL.ARROW_DOWN     # w1=1.0/yr, w2=0.5/yr -> delta -0.5, AT the deadband (not <, so it counts)


def test_untapped_default_top_n_is_100_and_carries_url(ctx, subs_bestfit):
    got = CL.untapped(ctx, subs_bestfit, STRASBOURG, SORBONNE)
    assert len(got["topics"]) <= 100
    assert list(got["topics"].columns) == CL.UNTAPPED_COLS
    if len(got["topics"]):
        from urllib.parse import unquote
        decoded = unquote(got["topics"].iloc[0]["url"])
        assert f"authorships.institutions.id:{STRASBOURG}" in decoded
        assert f"authorships.institutions.id:{SORBONNE}" in decoded


def test_gaps_and_top10_subfield_ids_are_gone():
    """2B-R2-11(f): the deleted footprint-gap table leaves no trace."""
    assert not hasattr(CL, "gaps")
    assert not hasattr(CL, "GAPS_COLS")
    assert not hasattr(CL, "_top10_subfield_ids")

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


# ---------------------------------------------------------------- gaps ------

@pytest.mark.parametrize("a,b,want_rows", [
    (STRASBOURG, SORBONNE, 156),
    (SORBONNE, STRASBOURG, 12),
    (STRASBOURG, GDANSK, 110),
    (GDANSK, STRASBOURG, 141),
    (IFPEN, SORBONNE, 58),
    (SORBONNE, IFPEN, 0),
])
def test_gaps_row_count_anchor(ctx, subs_bestfit, a, b, want_rows):
    df = CL.gaps(ctx, subs_bestfit, a, b)
    assert list(df.columns) == CL.GAPS_COLS
    assert len(df) == want_rows


def test_gaps_subset_of_b_absent_from_a_and_in_a_top10(ctx, subs_bestfit):
    """gaps(a, b) subseteq B's topics (share_b > 0) AND NOT IN A (share_a ==
    0) AND subfield in A's own top-10 (by L1 share)."""
    a, b = STRASBOURG, SORBONNE
    df = CL.gaps(ctx, subs_bestfit, a, b)
    assert len(df)  # non-trivial (S0 "confirmed unchanged": tens of topics)

    a_idx, b_idx = ctx["id_pos"][a], ctx["id_pos"][b]
    l3 = subs_bestfit["l3"]
    cats = np.asarray(l3["cats"], dtype=object)
    share_a = dict(zip(cats, l3["share"][a_idx]))
    share_b = dict(zip(cats, l3["share"][b_idx]))
    top10 = CL._top10_subfield_ids(subs_bestfit, a_idx)
    sub_map = CL._topic_subfield_map(ctx, subs_bestfit["tree"]).set_index("topic_id")["subfield_id"]

    for _, row in df.iterrows():
        t = row["topic_id"]
        assert share_b[t] > 0
        assert share_a[t] == 0
        assert sub_map.loc[t] in top10

    assert df["share_b"].is_monotonic_decreasing


def test_gaps_symmetric_call_differs(ctx, subs_bestfit):
    """gaps(a, b) and gaps(b, a) are genuinely different sets, not a
    coincidental mirror -- the two row counts differ for this pair."""
    fwd = CL.gaps(ctx, subs_bestfit, STRASBOURG, SORBONNE)
    bwd = CL.gaps(ctx, subs_bestfit, SORBONNE, STRASBOURG)
    assert len(fwd) != len(bwd)
    assert set(fwd["topic_id"]).isdisjoint(set(bwd["topic_id"]))  # A-lacks vs B-lacks, disjoint by construction


def test_gaps_self_pair_is_empty(ctx, subs_bestfit):
    """Defensive edge case: a self-pair can never produce a gap (share_b > 0
    AND share_a == 0 is impossible when a == b) -- must return an empty
    frame with the right columns, never raise."""
    df = CL.gaps(ctx, subs_bestfit, STRASBOURG, STRASBOURG)
    assert list(df.columns) == CL.GAPS_COLS
    assert len(df) == 0


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
    """Independently recomputed off collab_pair_topics.parquet: 12 topic
    rows, Sigma(vol_total) == 15 == collab_pairs.copubs_total (below the
    top-20 cap so this pair's FULL joint corpus is captured, no truncation),
    Sigma(sdg_tagged_n) == 0, erc_top_panel 'PE3' / panel_n 6 / labelled_n 15."""
    got = CL.joint_profile(ctx, subs_bestfit, STRASBOURG, IFPEN)
    assert got is not None
    assert got["meta"]["n_topics_shown"] == 12
    assert int(got["topics"]["vol_total"].sum()) == 15
    pulse_ab = CL.pulse(ctx, STRASBOURG, IFPEN)
    assert pulse_ab["copubs_total"] == 15
    assert got["sdg_tagged_total"] == 0
    assert got["erc"]["panel_idx"] == "PE3"
    assert got["erc"]["panel_n"] == 6
    assert got["erc"]["labelled_n"] == 15
    assert list(got["topics"].columns) == CL.JOINT_TOPICS_COLS
    assert got["topics"]["vol_total"].is_monotonic_decreasing
    assert got["fields"]["vol_total"].sum() == got["topics"]["vol_total"].sum()
    assert got["subfields"]["vol_total"].sum() == got["topics"]["vol_total"].sum()


def test_joint_profile_below_floor_returns_none(ctx, subs_bestfit):
    """A pair with copubs_total in {1, 2} (below PAIR_TOPICS_FLOOR=3) has
    ZERO rows in collab_pair_topics -- independently verified here -- and
    joint_profile must return None, not an empty-but-present frame."""
    pairs = _load_pairs_raw(ctx)
    below = pairs[pairs["copubs_total"].between(1, 2)].iloc[0]
    a, b = below["a"], below["b"]
    topics = _load_topics_raw(ctx)
    assert topics[(topics["a"] == a) & (topics["b"] == b)].empty
    assert CL.joint_profile(ctx, subs_bestfit, a, b) is None
    assert CL.PAIR_TOPICS_FLOOR == 3
    assert CL.PAIR_TOPICS_TOP_N == 20


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


def test_untapped_siblings_exclude_shared_topics_and_are_active_on_a_side(ctx, subs_bestfit):
    got = CL.untapped(ctx, subs_bestfit, STRASBOURG, SORBONNE, top_n=15)
    shared_ids = set(CL.shared_topics(ctx, subs_bestfit, STRASBOURG, SORBONNE)["topic_id"])
    sib = got["siblings"]
    assert list(sib.columns) == CL.SIBLING_COLS
    assert set(sib["topic_id"]).isdisjoint(shared_ids)
    assert ((sib["vol_a"] > 0) | (sib["vol_b"] > 0)).all()


def test_untapped_self_pair_never_raises_and_types_are_frames(ctx, subs_bestfit):
    """Defensive edge case: a self-pair (a==b, k undefined via pulse since a
    pair never co-publishes 'with itself' in collab_pairs -- absent from the
    table) must return typed frames, never raise. k falls back to 0.0 (no
    pulse row -> smaller==0 guard) rather than NaN propagating into gap."""
    got = CL.untapped(ctx, subs_bestfit, STRASBOURG, STRASBOURG)
    assert isinstance(got["topics"], pd.DataFrame) and list(got["topics"].columns) == CL.UNTAPPED_COLS
    assert isinstance(got["siblings"], pd.DataFrame) and list(got["siblings"].columns) == CL.SIBLING_COLS
    assert got["k"] == 0.0


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

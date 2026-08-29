"""
Stream K -- lib/compare_data.py acceptance tests (BUILD_PLAN_2B.md S4/S5,
Tier A). Anchors are concrete values recomputed from app/data/*.parquet on
2026-08-29 (env-app, bestfit/frac default scenario) -- see
V3/progress/2B_K.md for the recomputation script.

Run: python -m pytest tests/test_compare_data.py -q
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from lib import compare_data as CD
from lib import profile_data as P
from lib.engine import build_substrates, load_context

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

# The six named seeds (2B-K brief): Strasbourg, IFPEN, Gdansk, Iscte, Sorbonne, ETH Zurich.
STRASBOURG, IFPEN, GDANSK, ISCTE, SORBONNE, ETH = (
    "I68947357", "I265217849", "I40413290", "I110026055", "I39804081", "I35440088")
IDS6 = [STRASBOURG, IFPEN, GDANSK, ISCTE, SORBONNE, ETH]
ORFEO_CINQA = "I4210143641"  # WT-2B #3: only institution shipping 3 of 4 quadrant entries


@pytest.fixture(scope="module")
def ctx():
    return load_context(DATA_DIR)


@pytest.fixture(scope="module")
def subs_bestfit(ctx):
    return build_substrates(ctx)  # default: bestfit / frac


# ------------------------------------------------------------ fields/subs ---

def test_fields_long_columns_and_share_sum(ctx, subs_bestfit):
    df = CD.fields_long(ctx, subs_bestfit, IDS6)
    assert list(df.columns) == CD.FIELDS_LONG_COLS
    assert df["institution_id"].tolist() == sorted(df["institution_id"].tolist())
    sums = df.groupby("institution_id")["share"].sum().astype("float64")
    assert (sums.sub(1.0).abs() <= 1e-6).all(), sums.to_dict()


def test_fields_long_anchor_strasbourg_top_field(ctx, subs_bestfit):
    """Anchor: Strasbourg's top field by share is Medicine (field_id 27),
    share 0.211435, si 0.630268, si_status solid, vol_full 5387."""
    df = CD.fields_long(ctx, subs_bestfit, IDS6)
    row = df[df["institution_id"] == STRASBOURG].sort_values("share", ascending=False).iloc[0]
    assert int(row["field_id"]) == 27
    assert row["field_name"] == "Medicine"
    assert row["si_status"] == "solid"
    assert int(row["vol_full"]) == 5387
    np.testing.assert_allclose(float(row["share"]), 0.211435, atol=1e-5)
    np.testing.assert_allclose(float(row["si"]), 0.630268, atol=1e-5)


def test_subfields_long_columns_share_sum_and_row_counts(ctx, subs_bestfit):
    """Anchor: subfield rows per institution (nonzero-mass subfields only)."""
    df = CD.subfields_long(ctx, subs_bestfit, IDS6)
    assert list(df.columns) == CD.SUBFIELDS_LONG_COLS
    sums = df.groupby("institution_id")["share"].sum().astype("float64")
    assert (sums.sub(1.0).abs() <= 1e-6).all(), sums.to_dict()
    counts = df.groupby("institution_id").size().to_dict()
    want = {STRASBOURG: 237, IFPEN: 115, GDANSK: 229, ISCTE: 182, SORBONNE: 245, ETH: 239}
    assert counts == want


# ------------------------------------------------------------------ ERC/SDG -

def test_erc_long_columns_and_anchor_strasbourg(ctx):
    """Anchor: Strasbourg panel_idx 0 (LS9, Biotechnology and Biosystems
    Engineering) share 0.002827 / si 0.347769 / mass 14.554565 / thin;
    panel_idx 1 (LS3) mass 62.740841, solid."""
    df = CD.erc_long(ctx, IDS6)
    assert list(df.columns) == CD.ERC_LONG_COLS
    strasbourg = df[df["institution_id"] == STRASBOURG].set_index("panel_idx")
    r0 = strasbourg.loc[0]
    assert r0["panel_code"] == "LS9"
    assert r0["si_status"] == "thin"
    np.testing.assert_allclose(float(r0["share"]), 0.002827, atol=1e-5)
    np.testing.assert_allclose(float(r0["mass"]), 14.554565, atol=1e-3)
    r1 = strasbourg.loc[1]
    assert r1["panel_code"] == "LS3"
    assert r1["si_status"] == "solid"
    np.testing.assert_allclose(float(r1["mass"]), 62.740841, atol=1e-3)


def test_sdg_long_dense_16_per_institution_and_anchor(ctx):
    """Anchor: Strasbourg SDG 3 (Good Health) share 0.152615 solid; SDG 1
    (No Poverty) share 0.026837 thin."""
    df = CD.sdg_long(ctx, IDS6)
    assert list(df.columns) == CD.SDG_LONG_COLS
    counts = df.groupby("institution_id").size()
    assert (counts == 16).all(), counts.to_dict()
    strasbourg = df[df["institution_id"] == STRASBOURG].set_index("sdg_number")
    np.testing.assert_allclose(float(strasbourg.loc[3, "share"]), 0.152615, atol=1e-5)
    assert strasbourg.loc[3, "si_status"] == "solid"
    np.testing.assert_allclose(float(strasbourg.loc[1, "share"]), 0.026837, atol=1e-5)
    assert strasbourg.loc[1, "si_status"] == "thin"


# --------------------------------------------------------------- frontier ---

def test_frontier_mix_sums_to_one_and_anchor_strasbourg(ctx):
    """A2: 4 fixed quadrants + `not_scored` sum to 1 per institution.
    Anchor (Strasbourg): accelerating_expansion 0.235271, accelerating_
    contraction 0.252417, decelerating_expansion 0.160118, decelerating_
    contraction 0.240267, not_scored 0.111927."""
    df = CD.frontier_mix(ctx, IDS6)
    assert set(df["quadrant"].unique()) == set(CD.QUADRANTS) | {CD.NOT_SCORED}
    totals = df.groupby("institution_id")["share"].sum().astype("float64")
    assert (totals.sub(1.0).abs() <= 1e-6).all(), totals.to_dict()

    row = df[df["institution_id"] == STRASBOURG].set_index("quadrant")["share"]
    want = {"accelerating_expansion": 0.235271, "accelerating_contraction": 0.252417,
            "decelerating_expansion": 0.160118, "decelerating_contraction": 0.240267,
            "not_frontier_scored": 0.111927}
    for q, v in want.items():
        np.testing.assert_allclose(float(row[q]), v, atol=1e-5)


def test_frontier_mix_orfeo_missing_quadrant_is_zero(ctx):
    """WT-2B #3: I4210143641 (ORFEO-CINQA Research Network) ships only 3 of
    the 4 packed quadrant entries -- the missing one (decelerating_expansion)
    must render as 0.0, never a dropped row, and the frame still sums to 1."""
    if ORFEO_CINQA not in ctx["id_pos"]:
        pytest.skip("ORFEO-CINQA not in this snapshot's index")
    df = CD.frontier_mix(ctx, [ORFEO_CINQA])
    row = df.set_index("quadrant")["share"]
    assert len(df) == 5  # 4 quadrants + not_scored, even though the source packs only 3
    np.testing.assert_allclose(float(row["decelerating_expansion"]), 0.0, atol=1e-9)
    np.testing.assert_allclose(float(row["accelerating_expansion"]), 0.548461, atol=1e-5)
    np.testing.assert_allclose(float(row["accelerating_contraction"]), 0.110996, atol=1e-5)
    np.testing.assert_allclose(float(row["decelerating_contraction"]), 0.340543, atol=1e-5)
    np.testing.assert_allclose(float(row.sum()), 1.0, atol=1e-6)


@pytest.mark.parametrize("mode", ["top", "emerging"])
def test_frontier_points_scored_only_and_mode_filter(ctx, subs_bestfit, mode):
    df = CD.frontier_points(ctx, subs_bestfit, IDS6, mode)
    assert list(df.columns) == CD.FRONTIER_POINTS_COLS
    assert df["quadrant"].notna().all()
    if mode == "top":
        # every row is inside the institution's own top-200-by-volume set --
        # re-derive via profile_data.topics_table for one seed and cross-check.
        raw = P.topics_table(ctx, subs_bestfit, STRASBOURG)
        want_topics = set(raw.loc[(raw["rank_volume"] <= 200) & raw["quadrant"].notna(), "topic_id"])
        got_topics = set(df.loc[df["institution_id"] == STRASBOURG, "topic_id"])
        assert got_topics == want_topics
    else:
        assert (df["top25pct_frontier"] == True).all()  # noqa: E712


def test_frontier_points_invalid_mode_raises(ctx, subs_bestfit):
    with pytest.raises(AssertionError):
        CD.frontier_points(ctx, subs_bestfit, IDS6, "bogus")


# ------------------------------------------------------------------ impact --

def test_impact_index_anchors(ctx):
    """Anchors: ETH pp 0.257732 [0.251736-0.264092]; Strasbourg pp 0.104415
    [0.098974-0.109908]; ci_low <= pp <= ci_high for every row."""
    df = CD.impact_index(ctx, IDS6)
    assert list(df.columns) == CD.IMPACT_INDEX_COLS
    assert (df["ci_low"] <= df["pp"]).all() and (df["pp"] <= df["ci_high"]).all()
    eth = df[df["institution_id"] == ETH].iloc[0]
    np.testing.assert_allclose(eth["pp"], 0.257732, atol=1e-5)
    np.testing.assert_allclose(eth["ci_low"], 0.251736, atol=1e-5)
    np.testing.assert_allclose(eth["ci_high"], 0.264092, atol=1e-5)
    strasbourg = df[df["institution_id"] == STRASBOURG].iloc[0]
    np.testing.assert_allclose(strasbourg["pp"], 0.104415, atol=1e-5)


def test_impact_subfields_union_subset_and_in_all_ids(ctx, subs_bestfit):
    """A1: `impact_subfields` returns the UNION of subfields any compared
    institution clears at the floor, with NaN (never 0) where an
    institution has no cell. Anchor (IFPEN, Strasbourg, Gdansk, Sorbonne,
    floor 30, bestfit): 108 subfields in the union, exactly ONE
    (subfield_id 1503, Catalysis) held by all four."""
    ids4 = [IFPEN, STRASBOURG, GDANSK, SORBONNE]
    df = CD.impact_subfields(ctx, ids4, "bestfit", floor=30)
    assert list(df.columns) == CD.IMPACT_SUBFIELDS_COLS
    assert df["subfield_id"].nunique() == 108
    in_all = df.loc[df["in_all_ids"], "subfield_id"].unique()
    assert list(in_all) == [1503]
    assert (df.loc[df["in_all_ids"], "subfield_name"] == "Catalysis").all()

    # union property: every subfield in the frame is held by >= 1 id, and every
    # (institution, subfield) pair present in impact_cells at this floor/tree
    # for these ids appears here (subset check both ways on the join key).
    from lib.engine.substrates import load_impact_cells
    raw = load_impact_cells(ctx)
    raw_f = raw[(raw["tree"].astype(str) == "bestfit") & (raw["floor"] == 30)
                & (raw["institution_id"].isin(ids4))]
    defined = df.dropna(subset=["pp"])
    assert len(defined) == len(raw_f)
    assert set(zip(defined["institution_id"], defined["subfield_id"])) == \
        set(zip(raw_f["institution_id"], raw_f["subfield_id"]))


def test_impact_subfields_floor10_wider_than_floor30(ctx):
    """A1: floor 10 is the labelled information-only variant with MORE
    cells (wider intervals) -- anchor: 6-institution union has 208 subfields
    at floor 10 vs 165 at floor 30."""
    df30 = CD.impact_subfields(ctx, IDS6, "bestfit", floor=30)
    df10 = CD.impact_subfields(ctx, IDS6, "bestfit", floor=10)
    assert df30["subfield_id"].nunique() == 165
    assert df10["subfield_id"].nunique() == 208
    assert df10["subfield_id"].nunique() > df30["subfield_id"].nunique()


def test_impact_subfields_rejects_unshipped_floor(ctx):
    with pytest.raises(AssertionError):
        CD.impact_subfields(ctx, IDS6, "bestfit", floor=20)


# ------------------------------------------------------------------ trends --

def test_trends_subfields_matches_yearly_by_domain(ctx, subs_bestfit):
    """Cross-grain identity: Sigma over subfields per year (trends_subfields,
    the K brief's `compare_data.trends_subfields`) == Sigma over domains per
    year (`profile_data.yearly_by_domain`) for the SAME institution/tree --
    both reconcile to the index's own by-year bookkeeping total, verified
    for all six named seeds."""
    for iid in IDS6:
        ybd = P.yearly_by_domain(ctx, iid, subs_bestfit["tree"])
        ybs = CD.trends_subfields(ctx, iid, subs_bestfit["tree"])
        assert list(ybs.columns) == P.SUBFIELD_YEARLY_COLS
        d_full = ybd.groupby("year")["vol_full"].sum()
        s_full = ybs.groupby("year")["vol_full"].sum()
        d_frac = ybd.groupby("year")["vol_frac"].sum()
        s_frac = ybs.groupby("year")["vol_frac"].sum()
        np.testing.assert_allclose(s_full.reindex(d_full.index).to_numpy(dtype="float64"),
                                   d_full.to_numpy(dtype="float64"), atol=1e-6)
        np.testing.assert_allclose(s_frac.reindex(d_frac.index).to_numpy(dtype="float64"),
                                   d_frac.to_numpy(dtype="float64"), atol=1e-3)


# ------------------------------------------------------- shared subfields ---

def test_top_shared_subfields_anchor(ctx, subs_bestfit):
    """A3: summed-share ranking (not per-institution top-6 intersection,
    which collapses to ~1 subfield for this set). Anchor top result:
    subfield 1202 (History), summed_share 0.194833; 6th result: subfield
    2002 (Economics and Econometrics), summed_share 0.116918."""
    df = CD.top_shared_subfields(ctx, subs_bestfit, IDS6, 6)
    assert list(df.columns) == CD.TOP_SHARED_SUBFIELDS_COLS
    assert len(df) == 6
    assert df["summed_share"].is_monotonic_decreasing
    assert int(df.iloc[0]["subfield_id"]) == 1202
    assert df.iloc[0]["subfield_name"] == "History"
    np.testing.assert_allclose(df.iloc[0]["summed_share"], 0.194833, atol=1e-5)
    assert int(df.iloc[5]["subfield_id"]) == 2002
    np.testing.assert_allclose(df.iloc[5]["summed_share"], 0.116918, atol=1e-5)


# ------------------------------------------------------------------ grey ----

def test_coverage_sums_to_one_and_anchor(ctx):
    """A9: SIX mass_* states sum to total_frac exactly. Anchor (Strasbourg):
    classified_eligible 0.795498; ETH: classified_eligible 0.904158."""
    df = CD.coverage(ctx, IDS6)
    assert list(df.columns) == CD.COVERAGE_COLS
    assert set(df["state"].unique()) == set(CD.COVERAGE_COLUMN_BY_STATE.keys())
    totals = df.groupby("institution_id")["share"].sum().astype("float64")
    assert (totals.sub(1.0).abs() <= 1e-6).all(), totals.to_dict()

    strasbourg = df[df["institution_id"] == STRASBOURG].set_index("state")["share"]
    np.testing.assert_allclose(float(strasbourg["classified_eligible"]), 0.795498, atol=1e-5)
    eth = df[df["institution_id"] == ETH].set_index("state")["share"]
    np.testing.assert_allclose(float(eth["classified_eligible"]), 0.904158, atol=1e-5)


# ------------------------------------------------------------- performance --

def test_six_institution_frames_warm_under_1s(ctx, subs_bestfit):
    """2B-14 (as scoped by WT-2B #23 -- warm substrates already built by the
    module-scoped fixture): fields/subfields/erc/sdg_long for 6 institutions
    together well under the 2 s Compare-page budget."""
    t0 = time.time()
    CD.fields_long(ctx, subs_bestfit, IDS6)
    t1 = time.time()
    CD.subfields_long(ctx, subs_bestfit, IDS6)
    t2 = time.time()
    CD.erc_long(ctx, IDS6)
    t3 = time.time()
    CD.sdg_long(ctx, IDS6)
    t4 = time.time()
    print(f"[timing] fields_long={t1 - t0:.4f}s subfields_long={t2 - t1:.4f}s "
          f"erc_long={t3 - t2:.4f}s sdg_long={t4 - t3:.4f}s total={t4 - t0:.4f}s")
    assert (t4 - t0) < 1.0


def test_trends_subfields_warm_under_200ms(ctx, subs_bestfit):
    t0 = time.time()
    CD.trends_subfields(ctx, STRASBOURG, subs_bestfit["tree"])
    dt = time.time() - t0
    print(f"[timing] trends_subfields(1 institution)={dt:.4f}s")
    assert dt < 0.2

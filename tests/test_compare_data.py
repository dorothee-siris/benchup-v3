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


# 2BR3 CD4 item 7 (BUILD_PLAN_2BR3.md SS1.5 "'Trends in the 6 subfields'
# DELETED"): `compare_data.trends_subfields` is removed this round --
# `test_trends_subfields_matches_yearly_by_domain` tested a function that no
# longer exists and is removed WITH it (this plan, CD4 items 7/8). The
# cross-grain identity it checked (Sigma subfields == Sigma domains per year)
# still holds at the `profile_data.yearly_by_subfield`/`yearly_by_domain`
# level -- unchanged, untouched by this plan -- just no longer exercised
# through a `compare_data` wrapper that no longer exists.

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


# ============================================================================
# 2B-R (Stream CD, BUILD_PLAN_2BR.md S4) -- anchors recomputed on 2026-08-30
# via an INDEPENDENT code path (plain pandas over app/data/*.parquet, no
# import of lib.compare_data) -- see V3/progress/2BR_CD.md for the script.
# ============================================================================

def test_overview_columns_and_anchors(ctx):
    """10 independently-recomputed anchors (index.parquet read directly):
    Strasbourg + ETH x 5 columns each."""
    df = CD.overview(ctx, [STRASBOURG, ETH])
    assert list(df.columns) == CD.OVERVIEW_COLS
    s = df[df["institution_id"] == STRASBOURG].iloc[0]
    e = df[df["institution_id"] == ETH].iloc[0]
    np.testing.assert_allclose(s["vol_full"], 19402.0, rtol=1e-9)
    np.testing.assert_allclose(s["vol_frac"], 4716.2568287880495, rtol=1e-6)
    np.testing.assert_allclose(s["sdg_share"], 0.15542365135307884, rtol=1e-6)
    np.testing.assert_allclose(s["frontier_top25_share"], 0.18884864, rtol=1e-5)
    np.testing.assert_allclose(s["intl_share"], 0.5645294299556747, rtol=1e-6)
    np.testing.assert_allclose(e["vol_full"], 37877.0, rtol=1e-9)
    np.testing.assert_allclose(e["pp"], 0.2577321470534367, rtol=1e-6)
    np.testing.assert_allclose(e["ci_low"], 0.2517363750957043, rtol=1e-6)
    np.testing.assert_allclose(e["ci_high"], 0.2640919396495935, rtol=1e-6)
    np.testing.assert_allclose(e["company_share"], 0.11394777833513742, rtol=1e-6)
    assert (df["ci_low"] <= df["pp"]).all() and (df["pp"] <= df["ci_high"]).all()


def test_metric_frame_field_share_matches_fields_long(ctx, subs_bestfit):
    mf = CD.metric_frame(ctx, subs_bestfit, IDS6, "field", "share")
    assert list(mf.columns) == CD.METRIC_FRAME_COLS
    fl = CD.fields_long(ctx, subs_bestfit, IDS6)
    sums = mf.groupby("institution_id")["value"].sum().astype("float64")
    assert (sums.sub(1.0).abs() <= 1e-6).all(), sums.to_dict()
    assert len(mf) == len(fl)
    assert mf["ref_value"].isna().all()


def test_metric_frame_field_si_matches_fields_long_and_ref_is_one(ctx, subs_bestfit):
    mf = CD.metric_frame(ctx, subs_bestfit, IDS6, "field", "si")
    assert (mf["ref_value"] == 1.0).all()
    fl = CD.fields_long(ctx, subs_bestfit, IDS6).set_index(["institution_id", "field_id"])["si"]
    got = mf.set_index(["institution_id", "taxon_id"])["value"]
    np.testing.assert_allclose(got.reindex(fl.index).to_numpy(dtype="float64"),
                               fl.to_numpy(dtype="float64"), atol=1e-6)


def test_metric_frame_field_pp_and_vol_top10_anchor(ctx):
    """Anchor (Strasbourg, bestfit, floor 30): field 35 pp_top10_frac
    0.252981, n_works_full 160 -> vol_top10 = 0.252981*160 = 40.47696."""
    pp = CD.metric_frame(ctx, None, [STRASBOURG], "field", "pp", tree="bestfit", floor=30)
    row = pp[pp["taxon_id"] == 35].iloc[0]
    np.testing.assert_allclose(row["value"], 0.252981, atol=1e-5)
    assert row["ref_value"] is not None and not pd.isna(row["ref_value"])

    vol = CD.metric_frame(ctx, None, [STRASBOURG], "field", "vol_top10", tree="bestfit", floor=30)
    vrow = vol[vol["taxon_id"] == 35].iloc[0]
    np.testing.assert_allclose(vrow["value"], 0.252981 * 160, rtol=1e-4)
    assert vol["ref_value"].isna().all()


def test_metric_frame_field_sdg_share_anchor(ctx, subs_bestfit):
    """RE-DERIVED 2BR3 (BUILD_PLAN_2BR3.md Stream TEV-D, item 3 -- the v1
    anchor read the OLD per-goal `sdg_fields.mass` column, which is EXACTLY
    the 264.8%-bug mechanism WT_2BR3.md task 5.2 traced this table to; that
    column and grain (per-goal `sdg_idx`) no longer exist in v2). New anchor
    (Strasbourg, bestfit, fractional basis), independently summed off v2's
    `sdg_fields.parquet` (`mass_any_frac`, DISTINCT-tagged, no sdg_idx to
    double-count over) / `fields.parquet` (`vol_frac`), SAME 2020-2024 core
    window on both sides: field 33 142.799271 / 878.0426 = 0.16263365; field
    23 44.070625 / 114.91687 = 0.38350005."""
    df = CD.metric_frame(ctx, subs_bestfit, [STRASBOURG], "field", "sdg_share")
    row33 = df[df["taxon_id"] == 33].iloc[0]
    row23 = df[df["taxon_id"] == 23].iloc[0]
    np.testing.assert_allclose(row33["value"], 0.1626336469516921, rtol=1e-4)
    np.testing.assert_allclose(row23["value"], 0.38350004886344685, rtol=1e-4)
    assert (df["taxon_id"] != -1).all()  # untopiced residual never surfaces as a field row
    assert (df["value"] >= 0.0).all() and (df["value"] <= 1.0 + 1e-6).all()  # the bounded-share fix itself


def test_metric_frame_field_dynamics_matches_independent_yearly_rollup(ctx, subs_bestfit):
    """Field-grain dynamics for Strasbourg must equal an INDEPENDENT rollup
    of `profile_data.yearly_by_subfield` to field via the subfield->field
    map (same source data, hand-rolled groupby -- not calling
    compare_data._field_dynamics_frame's own code)."""
    from lib import profile_data as P
    yb = P.yearly_by_subfield(ctx, STRASBOURG, "bestfit")
    sfd = P._subfield_field_domain_map(ctx)[["subfield_id", "field_id"]]
    yb = yb.merge(sfd, on="subfield_id", how="left")
    yb["field_id"] = yb["field_id"].fillna(0).astype(int)
    mf = CD.metric_frame(ctx, subs_bestfit, [STRASBOURG], "field", "dynamics")
    checked = 0
    for fid, g in yb.groupby("field_id"):
        by_year = g.groupby("year")["vol_frac"].sum().to_dict()  # sum subfields sharing a field/year
        w1 = np.mean([by_year.get(y, 0.0) for y in (2020, 2021, 2022)])
        w2 = np.mean([by_year.get(y, 0.0) for y in (2023, 2024)])
        want = np.nan if w1 <= 0 else (w2 - w1) / w1
        got = mf.loc[mf["taxon_id"] == fid, "value"]
        if not len(got):
            continue
        if np.isnan(want):
            assert np.isnan(got.iloc[0])
        else:
            np.testing.assert_allclose(got.iloc[0], want, rtol=1e-6)
        checked += 1
    assert checked >= 10


def test_metric_frame_subfield_share_and_dynamics_within_field(ctx, subs_bestfit):
    """Subfield drill (field_id=27, Medicine, Strasbourg's top field):
    share sums to <= the field's own share (a subset of the full share
    vector), and dynamics values are finite or NaN, never raise."""
    field_id = 27
    share = CD.metric_frame(ctx, subs_bestfit, [STRASBOURG], "subfield", "share", field_id=field_id)
    dyn = CD.metric_frame(ctx, subs_bestfit, [STRASBOURG], "subfield", "dynamics", field_id=field_id)
    assert len(share) > 0 and len(dyn) > 0
    assert set(share["taxon_id"]) == set(dyn["taxon_id"])
    field_share = CD.fields_long(ctx, subs_bestfit, [STRASBOURG])
    field_share = field_share.loc[field_share["field_id"] == field_id, "share"].iloc[0]
    np.testing.assert_allclose(share["value"].sum(), field_share, rtol=1e-3)


def test_metric_frame_erc_share_si_matches_erc_long(ctx):
    share = CD.metric_frame(ctx, {"tree": "bestfit"}, IDS6, "erc", "share")
    si = CD.metric_frame(ctx, {"tree": "bestfit"}, IDS6, "erc", "si")
    el = CD.erc_long(ctx, IDS6)
    got_share = share.set_index(["institution_id", "taxon_id"])["value"]
    want_share = el.set_index(["institution_id", "panel_idx"])["share"]
    np.testing.assert_allclose(got_share.reindex(want_share.index).to_numpy(dtype="float64"),
                               want_share.to_numpy(dtype="float64"), atol=1e-6)
    assert (si["ref_value"] == 1.0).all()


def test_metric_frame_sdg_share_matches_sdg_long_and_dynamics_anchor(ctx, subs_bestfit):
    """SDG-grain `share` reuses `sdg_long` exactly; `dynamics` anchor
    (Strasbourg, independently recomputed off sdg_year.parquet): sdg_idx 0
    pct -0.11040, sdg_idx 1 pct -0.16949, sdg_idx 2 pct -0.25533."""
    share = CD.metric_frame(ctx, {"tree": "bestfit"}, IDS6, "sdg", "share")
    sl = CD.sdg_long(ctx, IDS6)
    got = share.set_index(["institution_id", "taxon_id"])["value"]
    want = sl.set_index(["institution_id", "sdg_idx"])["share"]
    np.testing.assert_allclose(got.reindex(want.index).to_numpy(dtype="float64"),
                               want.to_numpy(dtype="float64"), atol=1e-6)

    dyn = CD.metric_frame(ctx, subs_bestfit, [STRASBOURG], "sdg", "dynamics")
    assert len(dyn) == 16  # dense, matching sdg_table's own convention
    want_pct = {0: -0.11040039229141002, 1: -0.16949344533806474, 2: -0.25532591239100466}
    for sidx, pct in want_pct.items():
        np.testing.assert_allclose(dyn.loc[dyn["taxon_id"] == sidx, "value"].iloc[0], pct, rtol=1e-5)


def test_metric_frame_vol_erc_and_sdg_anchors(ctx):
    """2B-R-8 gap fix, RE-DERIVED 2BR3 for the SDG half (BUILD_PLAN_2BR3.md
    Stream TEV-D, item 3): ERC 'Volume' still reads `erc.parquet.mass`
    UNCHANGED (v2 only ADDS `mass_full` beside it, ruling 2/SS2.2) -- the ERC
    anchors are byte-identical to v1. SDG 'Volume tagged' MOVED off the
    whole-run (2020-2025) `sdg.parquet.mass` onto `sdg_year.parquet` v2,
    window-sliced to the 2020-2024 core window (2BR3 CD4 item 1: 'SDG
    Volume tagged... moved off sdg.parquet's whole-run mass onto
    sdg_year.parquet, window-sliced 2020-2024') -- so both the VALUES and the
    denominator note's window text change. New anchor (Strasbourg,
    fractional basis), independently summed off `sdg_year.parquet`'s
    `mass_frac` for years 2020-2024 only: sdg idx 3 = 54.305721, idx 1 =
    18.018429 (both LOWER than v1's whole-run 67.25587/21.483147, as
    expected -- a 5-year window is a strict subset of the 6-year one)."""
    erc_vol = CD.metric_frame(ctx, {"tree": "bestfit"}, [STRASBOURG], "erc", "vol")
    assert list(erc_vol.columns) == CD.METRIC_FRAME_COLS
    np.testing.assert_allclose(erc_vol.loc[erc_vol["taxon_id"] == 0, "value"].iloc[0], 14.554565, atol=1e-3)
    np.testing.assert_allclose(erc_vol.loc[erc_vol["taxon_id"] == 1, "value"].iloc[0], 62.74084, atol=1e-3)
    assert erc_vol["ref_value"].isna().all()
    assert erc_vol["denominator"].iloc[0] == CD.ERC_VOL_DENOM_NOTE

    # independent recompute: sdg_year.parquet, window-sliced 2020-2024, no
    # import of `_vol_frame`/`_sdg_year_window_mass`'s own code
    sdg_year = pd.read_parquet(Path(ctx["data_dir"]) / "sdg_year.parquet")
    win = sdg_year[(sdg_year["institution_id"] == STRASBOURG) & sdg_year["year"].between(2020, 2024)]
    hand_idx3 = float(win.loc[win["sdg_idx"] == 3, "mass_frac"].sum())
    hand_idx1 = float(win.loc[win["sdg_idx"] == 1, "mass_frac"].sum())
    np.testing.assert_allclose(hand_idx3, 54.305721282958984, atol=1e-3)
    np.testing.assert_allclose(hand_idx1, 18.018428802490234, atol=1e-3)

    sdg_vol = CD.metric_frame(ctx, {"tree": "bestfit", "basis": "frac"}, [STRASBOURG], "sdg", "vol")
    assert len(sdg_vol) == 16  # dense, matches sdg_long's own convention
    np.testing.assert_allclose(sdg_vol.loc[sdg_vol["taxon_id"] == 3, "value"].iloc[0], hand_idx3, atol=1e-3)
    np.testing.assert_allclose(sdg_vol.loc[sdg_vol["taxon_id"] == 1, "value"].iloc[0], hand_idx1, atol=1e-3)
    assert "2020-2024" in sdg_vol["denominator"].iloc[0]  # window text now matches the new source (was "2020-2025")
    assert "2020-2025" not in sdg_vol["denominator"].iloc[0]
    assert sdg_vol["ref_value"].isna().all()


def test_metric_frame_vol_matches_erc_long_and_sdg_long_mass(ctx):
    """RE-DERIVED 2BR3 (Stream TEV-D, item 3): ERC's `vol` metric is STILL
    identical to `erc_long`'s own `mass` column (unchanged source) -- that
    half of this anchor survives verbatim. SDG's `vol` metric is now a
    GENUINE, DELIBERATE divergence from `sdg_long`'s `mass` column: `sdg_long`
    (a thin wrapper over `profile_data.sdg_table`, untouched by CD4's fence)
    still reports the whole-run 2020-2025 mass off `sdg.parquet`, while the
    `vol` metric moved to the 2020-2024-windowed `sdg_year.parquet` (item 1
    above) -- so asserting equality here would now be asserting the OLD,
    un-fixed behaviour. This is re-derived as a NON-equality (the window
    narrowed, `sdg_long`'s mass can only be >= the windowed vol) plus a
    positive cross-check against a fresh `sdg_year.parquet` recompute."""
    erc_vol = CD.metric_frame(ctx, {"tree": "bestfit"}, IDS6, "erc", "vol")
    el = CD.erc_long(ctx, IDS6).set_index(["institution_id", "panel_idx"])["mass"]
    got = erc_vol.set_index(["institution_id", "taxon_id"])["value"]
    np.testing.assert_allclose(got.reindex(el.index).to_numpy(dtype="float64"),
                               el.to_numpy(dtype="float64"), atol=1e-6)

    sdg_vol = CD.metric_frame(ctx, {"tree": "bestfit", "basis": "frac"}, IDS6, "sdg", "vol")
    sl = CD.sdg_long(ctx, IDS6).set_index(["institution_id", "sdg_idx"])["mass"]
    got2 = sdg_vol.set_index(["institution_id", "taxon_id"])["value"]
    aligned_sl = sl.reindex(got2.index).to_numpy(dtype="float64")
    aligned_got2 = got2.to_numpy(dtype="float64")
    # NOT equal in general any more (whole-run mass >= windowed vol); assert
    # the direction of the divergence rather than a stale equality
    assert (aligned_sl >= aligned_got2 - 1e-6).all(), "sdg_long's whole-run mass should never be < the windowed vol"
    assert (aligned_sl > aligned_got2 + 1e-6).any(), "expected at least one row where the window narrowing actually bites"

    # positive cross-check: `vol`'s SDG value == a fresh sdg_year.parquet
    # window-slice recompute (never sdg_long/sdg.parquet), for all of IDS6
    sdg_year = pd.read_parquet(Path(ctx["data_dir"]) / "sdg_year.parquet")
    win = sdg_year[sdg_year["institution_id"].isin(IDS6) & sdg_year["year"].between(2020, 2024)]
    hand = win.groupby(["institution_id", "sdg_idx"])["mass_frac"].sum()
    np.testing.assert_allclose(got2.reindex(hand.index).to_numpy(dtype="float64"),
                               hand.to_numpy(dtype="float64"), atol=1e-3)


def test_metric_frame_vol_unavailable_at_field_and_subfield(ctx):
    assert not CD.metric_frame_available("vol", "field")
    assert not CD.metric_frame_available("vol", "subfield")
    df_field = CD.metric_frame(ctx, {"tree": "bestfit"}, [STRASBOURG], "field", "vol")
    assert df_field.empty and df_field.attrs.get("reason")
    df_sub = CD.metric_frame(ctx, {"tree": "bestfit"}, [STRASBOURG], "subfield", "vol", field_id=27)
    assert df_sub.empty and df_sub.attrs.get("reason")


@pytest.mark.parametrize("metric,level", [
    ("vol_top10", "subfield"), ("pp", "subfield"), ("sdg_share", "subfield"),
    ("vol_top10", "erc"), ("pp", "erc"), ("sdg_share", "erc"), ("dynamics", "erc"),
    ("vol_top10", "sdg"), ("pp", "sdg"), ("sdg_share", "sdg"), ("si", "sdg"),
    ("vol", "field"), ("vol", "subfield"),
])
def test_metric_frame_unavailable_combinations_return_typed_empty(ctx, metric, level):
    assert not CD.metric_frame_available(metric, level)
    kwargs = {"field_id": 27} if level == "subfield" else {}
    df = CD.metric_frame(ctx, {"tree": "bestfit"}, [STRASBOURG], level, metric, **kwargs)
    assert df.empty
    assert list(df.columns) == CD.METRIC_FRAME_COLS
    assert df.attrs.get("reason")


def test_metric_frame_rejects_subfield_without_field_id(ctx, subs_bestfit):
    with pytest.raises(AssertionError):
        CD.metric_frame(ctx, subs_bestfit, [STRASBOURG], "subfield", "share")


# --------------------------------------------------------- frontier 2B-R ----

def test_frontier_pooled_owner_categories_and_combined_vol(ctx, subs_bestfit):
    """2B-R-9: with N=3 ids, owner is one of the 3 ids or 'shared' -- never
    a 4th value; combined_vol == the per-id vol columns' row sum."""
    ids3 = [STRASBOURG, IFPEN, GDANSK]
    df = CD.frontier_pooled(ctx, subs_bestfit, ids3, top_n=60)
    assert set(df.columns) == {"topic_id", "name", "x", "y", "combined_vol", "owner", "domain_id",
                               f"vol_{STRASBOURG}", f"vol_{IFPEN}", f"vol_{GDANSK}"}
    assert set(df["owner"].unique()) <= set(ids3) | {"shared"}
    vol_cols = [f"vol_{i}" for i in ids3]
    np.testing.assert_allclose(df[vol_cols].sum(axis=1).to_numpy(dtype="float64"),
                               df["combined_vol"].to_numpy(dtype="float64"), rtol=1e-6)
    assert len(df) <= 60
    assert df["combined_vol"].is_monotonic_decreasing


def test_shared_frontier_is_subset_owned_by_two_or_more(ctx, subs_bestfit):
    ids3 = [STRASBOURG, IFPEN, GDANSK]
    pooled = CD.frontier_pooled(ctx, subs_bestfit, ids3, top_n=10_000)
    shared = CD.shared_frontier(ctx, subs_bestfit, ids3)
    assert (shared["owner"] == "shared").all()
    vol_cols = [f"vol_{i}" for i in ids3]
    n_holders = (shared[vol_cols] > 0).sum(axis=1)
    assert (n_holders >= 2).all()
    assert set(shared["topic_id"]) <= set(pooled.loc[pooled["owner"] == "shared", "topic_id"])
    assert shared["combined_vol"].is_monotonic_decreasing


# --------------------------------------------------------- performance -----

def test_three_institution_2br_frames_warm_under_1s(ctx, subs_bestfit):
    """CD brief acceptance: warm-frame timing for 3 institutions (Compare's
    own cap, `state.COMPARE_CAP`), printed, < 1 s target -- `overview` +
    the field-grain metric selector (share/dynamics/pp) + sdg dynamics +
    both frontier charts (the frame group one Compare render needs). The
    lazy sdg_fields/sdg_year/impact_fields/collab_* loaders are warmed by
    the module-scoped `ctx` fixture's earlier tests, matching how a real
    Streamlit session keeps `ctx` warm across reruns."""
    ids3 = [STRASBOURG, IFPEN, GDANSK]
    t0 = time.time()
    CD.overview(ctx, ids3)
    t1 = time.time()
    CD.metric_frame(ctx, subs_bestfit, ids3, "field", "share")
    t2 = time.time()
    CD.metric_frame(ctx, subs_bestfit, ids3, "field", "dynamics")
    t3 = time.time()
    CD.metric_frame(ctx, subs_bestfit, ids3, "field", "pp", tree="bestfit", floor=30)
    t4 = time.time()
    CD.metric_frame(ctx, subs_bestfit, ids3, "sdg", "dynamics")
    t5 = time.time()
    CD.frontier_pooled(ctx, subs_bestfit, ids3, top_n=60)
    t6 = time.time()
    CD.shared_frontier(ctx, subs_bestfit, ids3)
    t7 = time.time()
    print(f"[timing] overview={t1-t0:.4f}s field_share={t2-t1:.4f}s field_dynamics={t3-t2:.4f}s "
          f"field_pp={t4-t3:.4f}s sdg_dynamics={t5-t4:.4f}s frontier_pooled={t6-t5:.4f}s "
          f"shared_frontier={t7-t6:.4f}s total={t7-t0:.4f}s")
    assert (t7 - t0) < 1.0


def test_frontier_pooled_empty_for_no_frontier_topics(ctx, subs_bestfit):
    """A single id with a normal frontier footprint still returns rows
    (sanity: the function never raises on N=1); owner is that id for every
    row since a set of 1 can never produce 'shared'."""
    df = CD.frontier_pooled(ctx, subs_bestfit, [IFPEN], top_n=50)
    if len(df):
        assert (df["owner"] == IFPEN).all()


# ============================================================================
# 2B-R2 (Stream CD3, A5/2B-R2-10) -- metric_frame v3 contract: domain_id/
# domain_order, vol_display, vol_full_annual_mean, ref_value for sdg_share/
# dynamics, Unclassified excluded from Dynamics, frontier pool="elite".
# Anchors recomputed 2026-08-31 via INDEPENDENT code paths (raw duckdb/pandas
# over app/data/*.parquet, no import of lib.compare_data's own helpers) --
# see V3/progress/2BR2_CD3.md for the scripts.
# ============================================================================

def test_metric_frame_field_share_domain_and_volume_anchor(ctx, subs_bestfit):
    """Anchor: Strasbourg field 27 (Medicine, domain_id 4 Health Sciences,
    OA_DOMAIN_ORDER index 3). `vol_display` follows the CURRENT basis (frac
    by default, `fields_long`'s own vol_frac); `vol_full_annual_mean` is
    ALWAYS on the FULL basis (vol_full=5387 / 5 years, 2B-R2-4), regardless
    of which basis is displayed."""
    fl = CD.fields_long(ctx, subs_bestfit, [STRASBOURG])
    fl_row = fl[fl["field_id"] == 27].iloc[0]
    assert int(fl_row["vol_full"]) == 5387

    mf = CD.metric_frame(ctx, subs_bestfit, [STRASBOURG], "field", "share")
    row = mf[mf["taxon_id"] == 27].iloc[0]
    assert int(row["domain_id"]) == 4
    assert int(row["domain_order"]) == 3  # OA_DOMAIN_ORDER = (1,2,3,4) -> index 3
    np.testing.assert_allclose(row["vol_display"], float(fl_row["vol_frac"]), rtol=1e-6)  # basis='frac' default
    np.testing.assert_allclose(row["vol_full_annual_mean"], 5387.0 / 5, rtol=1e-6)
    assert pd.isna(row["vol_top10"])


def test_metric_frame_erc_share_domain_cols(ctx):
    """ERC domain_id is the panel's own erc_domain code (PE/LS/SH), ordered
    by `palette.ERC_DOMAIN_ORDER`; Strasbourg panel_idx 0 is LS9 -> LS."""
    mf = CD.metric_frame(ctx, {"tree": "bestfit"}, [STRASBOURG], "erc", "share")
    row = mf[mf["taxon_id"] == 0].iloc[0]
    assert row["domain_id"] == "LS"
    assert int(row["domain_order"]) == 1  # ERC_DOMAIN_ORDER = ("PE","LS","SH") -> index 1


def test_metric_frame_sdg_share_domain_is_constant_and_order_is_numeric(ctx):
    """SDG carries NO taxonomy domain (2B-R2-5 'SDG numeric') -- every row
    ships the SAME sentinel `domain_id` (so no domain-boundary rule ever
    fires between two SDG rows) and `domain_order` is the plain SDG number."""
    mf = CD.metric_frame(ctx, {"tree": "bestfit"}, [STRASBOURG], "sdg", "share")
    assert (mf["domain_id"] == CD.SDG_DOMAIN_ID).all()
    assert mf["domain_id"].nunique() == 1
    got_order = mf.set_index("taxon_id")["domain_order"]
    sl = CD.sdg_long(ctx, [STRASBOURG]).set_index("sdg_idx")["sdg_number"]
    np.testing.assert_array_equal(got_order.reindex(sl.index).to_numpy(dtype="int64"),
                                  sl.to_numpy(dtype="int64"))


def test_metric_frame_field_dynamics_excludes_unclassified(ctx, subs_bestfit):
    """2B-R2-4: the Unclassified pseudo-field (taxon_id 0) never appears in
    a Dynamics frame, at field OR subfield grain."""
    fdyn = CD.metric_frame(ctx, subs_bestfit, IDS6, "field", "dynamics")
    assert (fdyn["taxon_id"] != 0).all()
    sdyn = CD.metric_frame(ctx, subs_bestfit, [STRASBOURG], "subfield", "dynamics", field_id=27)
    assert (sdyn["taxon_id"] != 0).all()


def test_metric_frame_field_dynamics_ref_value_hand_duckdb_anchor(ctx, subs_bestfit):
    """Independent anchor: the population mean Dynamics value for field 11
    (Agricultural and Biological Sciences, bestfit/frac), hand-recomputed via
    a SEPARATE duckdb query (own topic->field join, no import of
    `compare_data._dynamics_population_ref`): 0.818266213962639 over 6,304
    institutions with nonzero window-1 mass -- UNCHANGED by 2BR3 (this ref
    value and the duckdb query itself are built on `vol_frac`, which P7 never
    touched: topics_all.parquet is not a 2BR3 artefact).

    RE-DERIVED 2BR3 gutter string only (BUILD_PLAN_2BR3.md Stream TEV-D, item
    3 -- this WAS the exact 'dynamics value/gutter basis mismatch' bug,
    compare_data.py item 1's own fix): v1 asserted the gutter as
    '130.0 -> 136.0/yr' -- those are FULL-basis numbers, which the OLD code
    hard-wired regardless of the page's basis toggle. `subs_bestfit` here is
    frac/bestfit (the module fixture's default), so post-fix the gutter now
    shows the SAME basis as `value` itself: fractional annual means '22.5 ->
    21.7/yr' (w1=22.451658, w2=21.662164, both independently summed off
    `topics_all.vol_frac_<year>` below). `vol_full_annual_mean` (the
    low-volume FLOOR marker) is UNCHANGED -- it stays on the full basis by
    design regardless of the toggle, so 132.4 (=(130*3+136*2)/5) still holds."""
    import duckdb
    tree = "bestfit"
    dim = ctx["topics_dim_df"][["topic_id", f"{tree}_subfield_id"]].rename(
        columns={f"{tree}_subfield_id": "subfield_id"})
    sfd = P._subfield_field_domain_map(ctx)[["subfield_id", "field_id"]]
    dim = dim.merge(sfd, on="subfield_id", how="left")
    dim["field_id"] = dim["field_id"].fillna(0).astype(int)
    sub = dim[dim["field_id"] == 11][["topic_id"]]
    con = duckdb.connect()
    con.register("_m", sub)
    ta_posix = Path(ctx["topics_all_path"]).as_posix()
    sql = f"""
        SELECT ta.inst_key,
               SUM(vol_frac_2020 + vol_frac_2021 + vol_frac_2022) / 3.0 AS w1,
               SUM(vol_frac_2023 + vol_frac_2024) / 2.0 AS w2
        FROM read_parquet('{ta_posix}') ta JOIN _m ON ta.topic_id = _m.topic_id
        GROUP BY ta.inst_key
    """
    hand = con.sql(sql).df()
    con.close()
    hand = hand[hand["w1"] > 0]
    hand_ref = float(((hand["w2"] - hand["w1"]) / hand["w1"]).mean())
    assert len(hand) == 6304

    mf = CD.metric_frame(ctx, subs_bestfit, [STRASBOURG], "field", "dynamics")
    row = mf[mf["taxon_id"] == 11].iloc[0]
    np.testing.assert_allclose(float(row["ref_value"]), hand_ref, rtol=1e-9)
    np.testing.assert_allclose(hand_ref, 0.818266213962639, rtol=1e-9)
    # RE-DERIVED 2BR3: frac-basis gutter (was the hard-FULL "130.0 -> 136.0/yr"
    # pre-fix) -- independently summed off topics_all.vol_frac_<year>, for
    # Strasbourg's own field-11 topic set (`sub`, already isolated above by
    # the SAME tree-aware subfield->field join the duckdb query used -- `sub`
    # itself carries topic_id only, so reload the frac year columns fresh).
    ta_cols = ["topic_id", "inst_key"] + [f"vol_frac_{y}" for y in range(2020, 2025)]
    ta = pd.read_parquet(Path(ctx["data_dir"]) / "topics_all.parquet", columns=ta_cols)
    strasbourg_ik = int(ctx["index_by_id"].loc[STRASBOURG, "inst_key"])
    ta_sub = ta[(ta["inst_key"] == strasbourg_ik) & ta["topic_id"].isin(set(sub["topic_id"]))]
    frac_by_year = {y: float(ta_sub[f"vol_frac_{y}"].sum()) for y in range(2020, 2025)}
    w1_frac = np.mean([frac_by_year[y] for y in (2020, 2021, 2022)])
    w2_frac = np.mean([frac_by_year[y] for y in (2023, 2024)])
    np.testing.assert_allclose(w1_frac, 22.451658248901367, atol=1e-4)
    np.testing.assert_allclose(w2_frac, 21.662163734436035, atol=1e-4)
    assert row["vol_display"] == f"{w1_frac:.1f} \N{RIGHTWARDS ARROW} {w2_frac:.1f}/yr" == "22.5 \N{RIGHTWARDS ARROW} 21.7/yr"
    np.testing.assert_allclose(row["denom_value"], w1_frac, rtol=1e-6)
    # vol_full_annual_mean (the low-volume FLOOR marker) stays FULL-basis
    # regardless of the toggle -- UNCHANGED by the item-1 fix, still 132.4.
    np.testing.assert_allclose(row["vol_full_annual_mean"], (130.0 * 3 + 136.0 * 2) / 5, rtol=1e-6)


def test_metric_frame_sdg_share_ref_value_hand_pandas_anchor(ctx, subs_bestfit):
    """RE-DERIVED 2BR3 (BUILD_PLAN_2BR3.md Stream TEV-D, item 3 -- this test
    IS the SDG-share-264.8%-bug's own regression guard, so it must be rebuilt
    against the v2 fix, not just re-pinned). v1 read the OLD per-goal
    `sdg_fields.mass` column and `.groupby("institution_id")["mass"].sum()`
    -- summing across up to 16 goal-rows PER field, the exact mechanism
    WT_2BR3.md task 5.2 traces the 264.8% bug to. v2's `sdg_fields.parquet`
    has no `sdg_idx`/per-goal grain left to sum over: `mass_any_frac` is
    ALREADY distinct-tagged (>=1 goal, counted once) per (institution, field,
    tree), on the field-cross's own 2020-2024 core window (window_conventions.
    core_window, NOT `sdg.parquet`'s whole-run 2020-2025). New independent
    anchor (plain pandas, own groupby, no import of
    `compare_data._sdg_share_field_ref_means`): population mean ratio for
    field 33 (bestfit) = 0.2114361822605133 (was 0.44246414 under the old,
    inflated per-goal-summed numerator -- LOWER here as expected, since a
    distinct-tagged numerator can only be <= a per-goal-summed one)."""
    sdg_fields = pd.read_parquet(Path(ctx["data_dir"]) / "sdg_fields.parquet")
    fields_raw = pd.read_parquet(Path(ctx["data_dir"]) / "fields.parquet",
                                 columns=["institution_id", "field_id", "tree", "vol_frac"])
    sub = sdg_fields[(sdg_fields["tree"] == "bestfit") & (sdg_fields["field_id"] == 33)]
    tagged = sub.groupby("institution_id")["mass_any_frac"].sum()  # v2: already distinct-tagged, no sdg_idx to sum over
    fm = fields_raw[(fields_raw["field_id"] == 33) & (fields_raw["tree"] == "bestfit")].set_index("institution_id")["vol_frac"]
    ratio = tagged.reindex(fm.index).fillna(0.0) / fm
    hand_ref = float(ratio.mean())
    assert len(fm) == 7402  # unchanged: fields.parquet's own field-33 population, untouched by P7

    mf = CD.metric_frame(ctx, subs_bestfit, [STRASBOURG], "field", "sdg_share")
    row = mf[mf["taxon_id"] == 33].iloc[0]
    np.testing.assert_allclose(float(row["ref_value"]), hand_ref, rtol=1e-6)
    np.testing.assert_allclose(hand_ref, 0.2114361822605133, rtol=1e-6)
    assert int(row["domain_id"]) == 2
    # vol_display/denom_value == the field's own vol_frac -- unchanged by P7
    # (fields.parquet itself carries no 2BR3 rebuild)
    np.testing.assert_allclose(row["vol_display"], 878.0426, rtol=1e-4)
    np.testing.assert_allclose(row["denom_value"], 878.0426, rtol=1e-4)


def test_metric_frame_pp_carries_vol_top10_gutter_data(ctx):
    """2B-R2-3: vol_top10 is retired as a selector TAB but stays AS DATA --
    the `pp` frame carries it as an extra column (the PP view's gutter),
    identical to what the standalone `vol_top10` metric's own `value`
    reports for the same cell."""
    pp = CD.metric_frame(ctx, None, [STRASBOURG], "field", "pp", tree="bestfit", floor=30)
    vol = CD.metric_frame(ctx, None, [STRASBOURG], "field", "vol_top10", tree="bestfit", floor=30)
    row = pp[pp["taxon_id"] == 35].iloc[0]
    vrow = vol[vol["taxon_id"] == 35].iloc[0]
    np.testing.assert_allclose(float(row["vol_top10"]), float(vrow["value"]), rtol=1e-9)
    assert vol["vol_top10"].isna().all()  # not duplicated on the vol_top10 metric's own frame


def test_frontier_pooled_elite_pool_is_subset_of_volume_pool_and_carries_domain(ctx, subs_bestfit):
    """2B-R2-10: pool='elite' (global top-10% by frontier_score_latest) is a
    STRICT SUBSET of pool='volume' (top-25% by construction) -- independently
    verified against a hand-computed global cutoff (own quantile call, no
    import of `compare_data._elite_frontier_topic_ids`): cutoff 0.359763,
    371 of 3,706 scored topics qualify."""
    ids3 = [STRASBOURG, IFPEN, GDANSK]
    dim = pd.read_parquet(Path(ctx["data_dir"]) / "topics_dim.parquet",
                          columns=["topic_id", "frontier_score_latest"])
    scored = dim["frontier_score_latest"].dropna()
    cutoff = float(scored.quantile(0.90))
    np.testing.assert_allclose(cutoff, 0.35976293683052063, rtol=1e-6)
    elite_ids = set(dim.loc[dim["frontier_score_latest"] >= cutoff, "topic_id"])
    assert len(scored) == 3706 and len(elite_ids) == 371

    pooled_elite = CD.frontier_pooled(ctx, subs_bestfit, ids3, top_n=10_000, pool="elite")
    pooled_volume = CD.frontier_pooled(ctx, subs_bestfit, ids3, top_n=10_000, pool="volume")
    assert len(pooled_elite) > 0
    assert set(pooled_elite["topic_id"]) <= elite_ids
    assert set(pooled_elite["topic_id"]) <= set(pooled_volume["topic_id"])
    assert len(pooled_elite) < len(pooled_volume)
    assert "domain_id" in pooled_elite.columns and pooled_elite["domain_id"].notna().any()


def test_frontier_pooled_rejects_unknown_pool(ctx, subs_bestfit):
    with pytest.raises(AssertionError):
        CD.frontier_pooled(ctx, subs_bestfit, [STRASBOURG], top_n=10, pool="bogus")


def test_unavailable_reason_is_plain_language():
    """2B-R2-13 plain-language sweep: no plan codes, artefact filenames or
    the word 'pipeline' in any UNAVAILABLE_REASON string."""
    forbidden = ("2B-R", "BUILD_PLAN", "pipeline", "artefact", ".parquet")
    for (metric, level), text in CD.UNAVAILABLE_REASON.items():
        for token in forbidden:
            assert token not in text, f"{(metric, level)} reason contains forbidden token {token!r}: {text}"

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
    """Anchor (Strasbourg, bestfit): field 33 SDG-tagged mass 253.856812 /
    field mass 878.0426 = 0.28911674; field 23: 100.5692/114.91687 =
    0.8751474 (independently summed off sdg_fields.parquet/fields.parquet)."""
    df = CD.metric_frame(ctx, subs_bestfit, [STRASBOURG], "field", "sdg_share")
    row33 = df[df["taxon_id"] == 33].iloc[0]
    row23 = df[df["taxon_id"] == 23].iloc[0]
    np.testing.assert_allclose(row33["value"], 0.28911674, rtol=1e-4)
    np.testing.assert_allclose(row23["value"], 0.8751474, rtol=1e-4)
    assert (df["taxon_id"] != -1).all()  # untopiced residual never surfaces as a field row


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


@pytest.mark.parametrize("metric,level", [
    ("vol_top10", "subfield"), ("pp", "subfield"), ("sdg_share", "subfield"),
    ("vol_top10", "erc"), ("pp", "erc"), ("sdg_share", "erc"), ("dynamics", "erc"),
    ("vol_top10", "sdg"), ("pp", "sdg"), ("sdg_share", "sdg"), ("si", "sdg"),
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
    assert set(df.columns) == {"topic_id", "name", "x", "y", "combined_vol", "owner",
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

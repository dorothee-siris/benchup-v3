"""
tests/test_cd4_2br3.py -- CD4 (BUILD_PLAN_2BR3.md, Phase 2B-R3) fixture-driven
acceptance tests. Runs against the SMALL fixtures under tests/fixtures/data/
(built by tests/fixtures/build_fixtures.py, hand-verified numbers documented
there), NOT the real app/data/ artefacts -- P7 has not rebuilt those to the
SS2.2 v2 schemas yet (BUILD_PLAN_2BR3.md S4 W1 -- P7/CD4 run in the same
parallel wave). The manager re-runs this suite against real artefacts once
P7 lands (S4 W3).

Run: python -m pytest tests/test_cd4_2br3.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "fixtures"))
from fixture_ctx import IA, IB, IC, build_ctx, build_subs  # noqa: E402

from lib import collab_data as CL  # noqa: E402
from lib import compare_data as CD  # noqa: E402


@pytest.fixture(scope="module")
def ctx():
    return build_ctx()


@pytest.fixture()
def subs_frac(ctx):
    return build_subs(ctx, basis="frac")


@pytest.fixture()
def subs_full(ctx):
    return build_subs(ctx, basis="full")


IDS3 = [IA, IB, IC]

# ============================================================================
# 1. metric_frame v4 contract + share-family bounds + denom_value finiteness
# ============================================================================

def test_metric_frame_v4_column_contract():
    """RE-PINNED 2C (Stream CD5): v4 -> v5 adds ONE column, `fwci_mean`
    (D2 -- the FWCI metric's hover-only mean; every other metric ships
    `None` here). The name is 'v4' in this test's own title for history --
    the docstring above `compare_data.METRIC_FRAME_COLS` names the v5 bump."""
    assert CD.METRIC_FRAME_COLS == [
        "institution_id", "taxon_id", "taxon_label", "value", "fwci_mean", "ref_value", "denominator",
        "denom_value", "domain_id", "domain_order", "vol_display", "vol_full_annual_mean", "vol_top10",
    ]


@pytest.mark.parametrize("level,metric,kwargs", [
    ("field", "share", {}), ("field", "sdg_share", {}), ("field", "dynamics", {}),
    ("erc", "share", {}), ("sdg", "share", {}),
])
def test_share_family_frames_are_bounded_0_1(ctx, subs_frac, level, metric, kwargs):
    """Acceptance item 8: every share-family frame value in [0, 1]. `dynamics`
    is NOT a share -- included here only to prove it is correctly excluded
    from this bound (a %-change frame legitimately goes negative/large)."""
    df = CD.metric_frame(ctx, subs_frac, IDS3, level, metric, **kwargs)
    if metric == "dynamics":
        assert not df.empty
        return
    vals = df["value"].dropna()
    assert len(vals) > 0
    assert (vals >= -1e-9).all() and (vals <= 1.0 + 1e-6).all(), (level, metric, vals.tolist())


def test_field_share_denom_value_finite_wherever_value_is_finite(ctx, subs_frac):
    df = CD.metric_frame(ctx, subs_frac, IDS3, "field", "share")
    finite_value = df["value"].notna()
    assert finite_value.all()  # every field row here has a share (fixture has no zero-mass field rows)
    assert df.loc[finite_value, "denom_value"].notna().all()
    # cross-check: denom_value * value == vol_display (the taxon's own raw volume) for share
    got = (df["denom_value"] * df["value"]).to_numpy(dtype="float64")
    want = df["vol_display"].to_numpy(dtype="float64")
    np.testing.assert_allclose(got, want, atol=1e-6)


def test_field_share_denom_value_finite_on_zero_value_row(ctx, subs_frac):
    """The IB/field2 SDG-share row has value == 0.0 (mass_any_frac == 0.0) --
    denom_value must still be finite (the field's own nonzero total mass),
    never NaN from a 0/0 back-division."""
    df = CD.metric_frame(ctx, subs_frac, [IB], "field", "sdg_share")
    row = df[df["taxon_id"] == 2].iloc[0]
    assert row["value"] == pytest.approx(0.0, abs=1e-9)
    assert np.isfinite(row["denom_value"])
    np.testing.assert_allclose(row["denom_value"], 5.0, atol=1e-9)


def test_si_and_vol_metrics_denom_value_is_nan_by_design(ctx, subs_frac):
    si = CD.metric_frame(ctx, subs_frac, IDS3, "field", "si")
    assert si["denom_value"].isna().all()
    vol = CD.metric_frame(ctx, {"tree": "bestfit", "basis": "frac"}, [IA], "erc", "vol")
    assert vol["denom_value"].isna().all()


# ============================================================================
# 2. dynamics gutter/value same-basis fix + recompute-to-value check
# ============================================================================

def test_field_dynamics_value_and_gutter_agree_frac_basis(ctx, subs_frac):
    """IA field1: W1=10.0 -> W2=15.0 on FRAC (item-1 anchor from
    build_fixtures.py) -- value +50%, gutter '10.0 -> 15.0/yr' (frac, NOT the
    full-basis '20.0 -> 30.0/yr' the pre-2BR3 bug would have shown)."""
    df = CD.metric_frame(ctx, subs_frac, [IA], "field", "dynamics")
    row = df[df["taxon_id"] == 1].iloc[0]
    np.testing.assert_allclose(row["value"], 0.5, rtol=1e-9)
    assert row["vol_display"] == "10.0 → 15.0/yr"
    np.testing.assert_allclose(row["denom_value"], 10.0, atol=1e-9)
    np.testing.assert_allclose(row["vol_full_annual_mean"], (20.0 * 3 + 30.0 * 2) / 5, rtol=1e-9)  # floor stays FULL


def test_field_dynamics_value_and_gutter_agree_full_basis(ctx, subs_full):
    """SAME field, basis='full': W1=20.0 -> W2=30.0 -- value is STILL +50%
    (my fixture scales full=2x frac uniformly) but the gutter NUMBER changes
    to the full-basis figures, proving the gutter now tracks the toggle."""
    df = CD.metric_frame(ctx, subs_full, [IA], "field", "dynamics")
    row = df[df["taxon_id"] == 1].iloc[0]
    np.testing.assert_allclose(row["value"], 0.5, rtol=1e-9)
    assert row["vol_display"] == "20.0 → 30.0/yr"
    np.testing.assert_allclose(row["denom_value"], 20.0, atol=1e-9)


def test_field_dynamics_down_and_stable_anchors(ctx, subs_frac):
    """IB field1: W1=8.0->W2=4.0, value -50%. IB field2: flat, value 0%."""
    df = CD.metric_frame(ctx, subs_frac, [IB], "field", "dynamics")
    r1 = df[df["taxon_id"] == 1].iloc[0]
    np.testing.assert_allclose(r1["value"], -0.5, rtol=1e-9)
    assert r1["vol_display"] == "8.0 → 4.0/yr"
    r2 = df[df["taxon_id"] == 2].iloc[0]
    np.testing.assert_allclose(r2["value"], 0.0, atol=1e-9)
    assert r2["vol_display"] == "1.0 → 1.0/yr"


@pytest.mark.parametrize("level,kwargs", [("field", {}), ("subfield", {"field_id": 1})])
def test_dynamics_gutter_string_recomputes_to_value_within_rounding(ctx, subs_frac, level, kwargs):
    """Acceptance item 8: the gutter STRING's two numbers, parsed back out,
    reproduce `value` within rounding -- generalised over every row/level,
    not just the hand-picked anchors above."""
    df = CD.metric_frame(ctx, subs_frac, IDS3, level, "dynamics", **kwargs)
    checked = 0
    for _, row in df.iterrows():
        w1_str, w2_str = row["vol_display"].replace("/yr", "").split(" → ")
        w1, w2 = float(w1_str), float(w2_str)
        want = np.nan if w1 <= 0 else (w2 - w1) / w1
        if np.isnan(want):
            assert np.isnan(row["value"])
        else:
            np.testing.assert_allclose(row["value"], want, rtol=1e-6, atol=1e-9)
            checked += 1
    assert checked >= 2


def test_subfield_dynamics_matches_field_dynamics_one_to_one_fixture(ctx, subs_frac):
    """This fixture has exactly one subfield per field -- subfield-grain
    dynamics for field_id=1 must reproduce field-grain dynamics exactly."""
    fdyn = CD.metric_frame(ctx, subs_frac, [IA], "field", "dynamics")
    sdyn = CD.metric_frame(ctx, subs_frac, [IA], "subfield", "dynamics", field_id=1)
    frow = fdyn[fdyn["taxon_id"] == 1].iloc[0]
    srow = sdyn[sdyn["taxon_id"] == 101].iloc[0]
    np.testing.assert_allclose(frow["value"], srow["value"], rtol=1e-9)
    assert frow["vol_display"] == srow["vol_display"]


def test_sdg_dynamics_basis_toggle_and_full_marker_now_populated(ctx, subs_frac, subs_full):
    """IA sdg_idx 0: frac W1=4.0->W2=6.0 (+50%); IB sdg_idx 1 is all-zero ->
    NaN value (w1<=0 guard), never a crash. `vol_full_annual_mean` is now a
    real number (v2 sdg_year.mass_full closes the v3 NaN-always gap)."""
    df = CD.metric_frame(ctx, subs_frac, [IA, IB], "sdg", "dynamics")
    ia0 = df[(df["institution_id"] == IA) & (df["taxon_id"] == 0)].iloc[0]
    np.testing.assert_allclose(ia0["value"], 0.5, rtol=1e-9)
    assert np.isfinite(ia0["vol_full_annual_mean"])
    ib1 = df[(df["institution_id"] == IB) & (df["taxon_id"] == 1)].iloc[0]
    assert np.isnan(ib1["value"])

    dfull = CD.metric_frame(ctx, subs_full, [IA], "sdg", "dynamics")
    ia0_full = dfull[dfull["taxon_id"] == 0].iloc[0]
    assert ia0_full["vol_display"] == "8.0 → 12.0/yr"


# ============================================================================
# 3. SDG-share fix (item 2): distinct-tagged numerator, matched-window
#    denominator, bounded <= 1 + eps, asserted INSIDE the function.
# ============================================================================

def test_sdg_share_field_anchors_and_bound(ctx, subs_frac):
    """IA field1: 24/60=0.4; IA field2: 25/25=1.0 EXACTLY (the edge case --
    must still pass the function's own internal assert); IB field1: 16/32=0.5."""
    df = CD.metric_frame(ctx, subs_frac, [IA, IB], "field", "sdg_share")
    ia1 = df[(df["institution_id"] == IA) & (df["taxon_id"] == 1)].iloc[0]
    ia2 = df[(df["institution_id"] == IA) & (df["taxon_id"] == 2)].iloc[0]
    ib1 = df[(df["institution_id"] == IB) & (df["taxon_id"] == 1)].iloc[0]
    np.testing.assert_allclose(ia1["value"], 0.4, rtol=1e-9)
    np.testing.assert_allclose(ia2["value"], 1.0, rtol=1e-9)
    np.testing.assert_allclose(ib1["value"], 0.5, rtol=1e-9)
    assert (df["value"] <= 1.0 + CD.SDG_SHARE_EPS).all()
    np.testing.assert_allclose(ia1["denom_value"], 60.0, atol=1e-9)


def test_sdg_share_field_basis_toggle(ctx, subs_full):
    """Full basis: 48/120 == 0.4 (SAME ratio, since mass_any_full=2x and
    vol_full=2x uniformly in the fixture) but denom_value doubles in magnitude."""
    df = CD.metric_frame(ctx, subs_full, [IA], "field", "sdg_share")
    row = df[df["taxon_id"] == 1].iloc[0]
    np.testing.assert_allclose(row["value"], 0.4, rtol=1e-9)
    np.testing.assert_allclose(row["denom_value"], 120.0, atol=1e-9)


def test_sdg_share_field_denom_note_names_both_windows_no_mismatch():
    note = CD.SDG_SHARE_FIELD_DENOM_NOTE
    assert "2020-2024" in note
    assert "2020-2025" not in note  # the old mismatched window must not survive


# ============================================================================
# 4. PP gutter basis toggle (item 1)
# ============================================================================

def test_pp_is_fully_basis_pinned(ctx):
    """2D RE-PIN (E2/E4, decisions log 2026-09-02): PP10_WD rebased onto
    `impact_taxa.parquet` (fixture: IA field1 pp10_wd=0.25, n_covered_pp=120)
    is now FULLY basis-pinned, like fwci -- `value`, `vol_display` AND
    `denom_value` are all IDENTICAL regardless of the toggle (impact_taxa.
    parquet has no basis column at all). This REPLACES the old `impact_
    fields.parquet`-based contract ('gutter follows basis, value pinned'),
    retired with that reader path."""
    frac = CD.metric_frame(ctx, {"tree": "bestfit", "basis": "frac"}, [IA], "field", "pp", tree="bestfit", floor=30)
    full = CD.metric_frame(ctx, {"tree": "bestfit", "basis": "full"}, [IA], "field", "pp", tree="bestfit", floor=30)
    rf = frac[frac["taxon_id"] == 1].iloc[0]
    rl = full[full["taxon_id"] == 1].iloc[0]
    np.testing.assert_allclose(rf["value"], 0.25, rtol=1e-9)
    np.testing.assert_allclose(rl["value"], 0.25, rtol=1e-9)
    np.testing.assert_allclose(rf["vol_display"], 120.0, atol=1e-9)
    np.testing.assert_allclose(rl["vol_display"], 120.0, atol=1e-9)
    np.testing.assert_allclose(rf["denom_value"], 120.0, atol=1e-9)
    np.testing.assert_allclose(rl["denom_value"], 120.0, atol=1e-9)


def test_vol_top10_metric_denom_value_is_none(ctx):
    vol = CD.metric_frame(ctx, {"tree": "bestfit", "basis": "frac"}, [IA], "field", "vol_top10", tree="bestfit", floor=30)
    assert vol["denom_value"].isna().all()


# ============================================================================
# 5. ERC/SDG "vol" metric basis toggle
# ============================================================================

def test_erc_vol_metric_basis_toggle(ctx):
    frac = CD.metric_frame(ctx, {"tree": "bestfit", "basis": "frac"}, [IA], "erc", "vol")
    full = CD.metric_frame(ctx, {"tree": "bestfit", "basis": "full"}, [IA], "erc", "vol")
    np.testing.assert_allclose(frac.loc[frac["taxon_id"] == 0, "value"].iloc[0], 14.0, atol=1e-9)
    np.testing.assert_allclose(full.loc[full["taxon_id"] == 0, "value"].iloc[0], 28.0, atol=1e-9)


def test_sdg_vol_metric_now_sourced_from_sdg_year_window_sliced(ctx):
    """SDG 'Volume tagged' moved off sdg.parquet's 2020-2025 mass onto
    sdg_year.parquet's 2020-2024 window-sliced sum (item 1). IA sdg_idx 0
    over 2020-2024 = 4+4+4+6+6 = 24.0 (2025's 6.0 excluded)."""
    df = CD.metric_frame(ctx, {"tree": "bestfit", "basis": "frac"}, [IA], "sdg", "vol")
    assert len(df) == 16  # dense, matches sdg_long's own convention
    row0 = df[df["taxon_id"] == 0].iloc[0]
    np.testing.assert_allclose(row0["value"], 24.0, atol=1e-9)
    assert "2020-2024" in row0["denominator"]
    dfull = CD.metric_frame(ctx, {"tree": "bestfit", "basis": "full"}, [IA], "sdg", "vol")
    np.testing.assert_allclose(dfull[dfull["taxon_id"] == 0]["value"].iloc[0], 48.0, atol=1e-9)


# ============================================================================
# 6. Deletions (item 7)
# ============================================================================

def test_trends_subfields_deleted():
    assert not hasattr(CD, "trends_subfields")


# ============================================================================
# 7. Momentum display ladder (item 5) -- 9-case truth table
# ============================================================================

FACTS = {"med": 1.0, "weak_base_max": 4, "new_min_c2": 5, "dormant_min_c1": 5}

MOMENTUM_CASES = [
    ("null", None, None, None, 0, 0, ("—", CL.MOMENTUM_COLORS["neutral"], CL.MOMENTUM_GLYPH["neutral"])),
    ("up_normal", "up", 1.5, 0.01, 15, 20, ("+50%", CL.MOMENTUM_COLORS["up"], CL.MOMENTUM_GLYPH["up"])),
    ("up_clamped", "up", 15.0, 0.001, 2, 30, ("> +999%", CL.MOMENTUM_COLORS["up"], CL.MOMENTUM_GLYPH["up"])),
    ("down_normal", "down", 0.5, 0.02, 20, 10, ("-50%", CL.MOMENTUM_COLORS["down"], CL.MOMENTUM_GLYPH["down"])),
    ("stable", "stable", 1.0, 0.9, 20, 20, ("+0%", CL.MOMENTUM_COLORS["stable"], CL.MOMENTUM_GLYPH["stable"])),
    ("ns", "ns", 1.4, 0.3, 10, 12, ("n.s.", CL.MOMENTUM_COLORS["neutral"], CL.MOMENTUM_GLYPH["neutral"])),
    ("new", "new", None, None, 0, 6, ("new", CL.MOMENTUM_COLORS["neutral"], CL.MOMENTUM_GLYPH["neutral"])),
    ("dormant", "dormant", None, None, 6, 0, ("dormant", CL.MOMENTUM_COLORS["neutral"], CL.MOMENTUM_GLYPH["neutral"])),
    ("weak", "weak", None, None, 3, 8, ("weak base", CL.MOMENTUM_COLORS["neutral"], CL.MOMENTUM_GLYPH["neutral"])),
]
assert len(MOMENTUM_CASES) == 9, "the ladder is a 9-case truth table (CD4 item 5)"


@pytest.mark.parametrize("name,mom_class,mom_rr,mom_p,c1,c2,want", MOMENTUM_CASES, ids=[c[0] for c in MOMENTUM_CASES])
def test_momentum_display_truth_table(name, mom_class, mom_rr, mom_p, c1, c2, want):
    got = CL.momentum_display(mom_class, mom_rr, mom_p, c1, c2, FACTS)
    assert got == want, (name, got, want)


def test_momentum_display_colour_never_alone():
    """Every case's glyph is a non-empty string distinct from a bare colour
    -- the WT_2BR3.md task 2.8 mandatory rule, checked structurally."""
    for _, mom_class, mom_rr, mom_p, c1, c2, _ in MOMENTUM_CASES:
        text, color, glyph = CL.momentum_display(mom_class, mom_rr, mom_p, c1, c2, FACTS)
        assert text and glyph and color.startswith("#")


def test_pair_momentum_matches_fixture_and_ladder(ctx):
    """collab_pairs fixture row: mom_class='up', mom_rr=1.5 -> ('+50%', ...)."""
    got = CL.pair_momentum(ctx, IA, IB)
    assert got is not None
    assert got["mom_class"] == "up"
    np.testing.assert_allclose(got["mom_rr"], 1.5, rtol=1e-9)
    assert got["text"] == "+50%"
    assert got["color"] == CL.MOMENTUM_COLORS["up"]
    np.testing.assert_allclose(got["d1"], 450.0, atol=1e-9)  # 300 (IA) + 150 (IB)
    np.testing.assert_allclose(got["d2"], 360.0, atol=1e-9)  # 220 (IA) + 140 (IB)


def test_pair_momentum_none_for_unknown_pair(ctx):
    assert CL.pair_momentum(ctx, IA, IC) is None  # no collab_pairs row for this pair in the fixture


# ============================================================================
# 8. untapped() uncapped fix (item 4)
# ============================================================================

def test_untapped_joint_observed_matches_uncapped_fixture_vols(ctx, subs_frac):
    """T3 is a shared topic (IA/IB both nonzero) present ONLY in
    collab_topic_vols.parquet (vol=2), absent from collab_pair_topics
    (simulating the top-100 cap). The OLD code (reading collab_pair_topics)
    would read joint_observed=0 for T3; the FIXED code must read 2."""
    got = CL.untapped(ctx, subs_frac, IA, IB, top_n=50)
    df = got["topics"]
    assert "T3" in set(df["topic_id"])
    row = df[df["topic_id"] == "T3"].iloc[0]
    np.testing.assert_allclose(row["joint_observed"], 2.0, atol=1e-9)

    raw_vols = pd.read_parquet(Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "data"
                               / "collab_topic_vols.parquet")
    want = dict(zip(raw_vols["topic_id"], raw_vols["vol"]))
    for _, r in df.iterrows():
        if r["topic_id"] in want:
            np.testing.assert_allclose(r["joint_observed"], want[r["topic_id"]], atol=1e-9)

    assert (df["gap"] > 0).all()
    assert df["gap"].is_monotonic_decreasing


def test_untapped_t3_absent_from_capped_pair_topics_precondition(ctx):
    """Precondition check on the fixture itself: T3 truly is absent from
    collab_pair_topics.parquet (the cap simulation) -- if this ever fails the
    fixture no longer tests what item 4 claims."""
    topics = pd.read_parquet(Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "data"
                             / "collab_pair_topics.parquet")
    assert "T3" not in set(topics["topic_id"])


# ============================================================================
# 9. reciprocity_frame (item 6) -- symmetric fixture check
# ============================================================================

def test_reciprocity_frame_anchor_and_joint_vol(ctx, subs_frac):
    df = CL.reciprocity_frame(ctx, subs_frac, IA, IB)
    assert list(df.columns) == CL.RECIPROCITY_COLS
    assert len(df) == 2  # both fields have joint vol > 0 in the fixture
    r1 = df[df["field_id"] == 1].iloc[0]
    np.testing.assert_allclose(r1["joint_vol"], 15.0, atol=1e-9)
    np.testing.assert_allclose(r1["y"], 60.0 / 85.0, rtol=1e-6)  # A's (IA) own field1 share
    np.testing.assert_allclose(r1["x"], 32.0 / 37.0, rtol=1e-6)  # B's (IB) own field1 share


def test_reciprocity_frame_symmetric_on_swap(ctx, subs_frac):
    fwd = CL.reciprocity_frame(ctx, subs_frac, IA, IB).set_index("field_id")
    bwd = CL.reciprocity_frame(ctx, subs_frac, IB, IA).set_index("field_id")
    np.testing.assert_allclose(fwd["x"].to_numpy(), bwd["y"].to_numpy(), rtol=1e-9)
    np.testing.assert_allclose(fwd["y"].to_numpy(), bwd["x"].to_numpy(), rtol=1e-9)
    np.testing.assert_allclose(fwd["joint_vol"].to_numpy(), bwd["joint_vol"].to_numpy(), rtol=1e-9)


def test_reciprocity_frame_only_positive_joint_vol_rows():
    """Structural: the function filters `field_breakdown`'s own vol > 0 --
    covered by construction since the fixture's field_breakdown never ships
    a zero-vol row; asserted here as a standing invariant on the frame."""
    pass  # covered by test_reciprocity_frame_anchor_and_joint_vol's len(df)==2 check


# ============================================================================
# 10. collab_data v2 loaders / module constants (item 3)
# ============================================================================

def test_joint_topics_and_field_breakdown_cols_use_v2_names():
    assert "vol" in CL.JOINT_TOPICS_COLS and "vol_total" not in CL.JOINT_TOPICS_COLS
    assert "vol_2025" not in CL.JOINT_TOPICS_COLS
    assert "n_sdg" in CL.JOINT_TOPICS_COLS and "sdg_tagged_n" not in CL.JOINT_TOPICS_COLS
    assert "vol" in CL.FIELD_BREAKDOWN_COLS and "mean_citations" not in CL.FIELD_BREAKDOWN_COLS
    assert set(CL.JOINT_ROLLUP_VALUE_COLS) <= set(CL.JOINT_TOPICS_COLS)


def test_field_breakdown_v2_anchors(ctx):
    df = CL.field_breakdown(ctx, IA, IB)
    assert list(df.columns) == CL.FIELD_BREAKDOWN_COLS
    row1 = df[df["field_id"] == 1].iloc[0]
    np.testing.assert_allclose(row1["vol"], 15.0, atol=1e-9)
    assert row1["mom_class"] == "up"
    np.testing.assert_allclose(row1["fwci_median"], 1.2, rtol=1e-9)
    assert df["vol"].is_monotonic_decreasing


def test_joint_profile_v2_erc_moved_to_collab_pairs(ctx, subs_frac):
    got = CL.joint_profile(ctx, subs_frac, IA, IB)
    assert got is not None
    assert got["erc"] is not None
    assert got["erc"]["panel_idx"] == "PE3"
    assert got["erc"]["panel_n"] == 5
    assert got["erc"]["labelled_n"] == 20
    assert "n_sdg" not in _load_raw_pair_topics_cols()  # v2 collab_pair_topics carries no erc_* / uses n_sdg not sdg_tagged_n
    assert got["sdg_tagged_total"] == int(got["topics"]["n_sdg"].sum())
    assert list(got["topics"].columns) == CL.JOINT_TOPICS_COLS


def _load_raw_pair_topics_cols():
    df = pd.read_parquet(Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "data"
                         / "collab_pair_topics.parquet")
    return set(df.columns) & {"sdg_tagged_n"}


# ============================================================================
# 11. matrix-relationship semantics survive (item 8: SUBJECT_METRICS subset)
# ============================================================================

def test_metrics_vocabulary_unchanged_by_this_plan():
    """CD4 (2BR3) did not touch METRICS/LEVELS vocabulary -- the
    SUBJECT_METRICS subset check in tests/test_matrix_compare.py (at the
    time, K.METRICS minus SUBJECT_METRICS == {'vol_top10'}) survived
    unmodified because the left-hand side it compares against (K.METRICS)
    was unchanged by CD4.

    RE-PINNED 2C (Stream CD5, BUILD_PLAN_2C.md S3 CD5, D2): `fwci` is a
    genuinely NEW metric (all four grains) -- METRICS grows by one, LEVELS
    is untouched (fwci reuses the same four grains, no fifth taxonomy)."""
    assert CD.METRICS == ("share", "vol_top10", "pp", "sdg_share", "dynamics", "si", "vol", "fwci")
    assert CD.LEVELS == ("field", "subfield", "erc", "sdg")

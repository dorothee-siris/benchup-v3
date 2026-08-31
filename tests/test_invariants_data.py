"""
tests/test_invariants_data.py -- BUILD_PLAN_2BR3.md Stream TEV-D deterministic
data invariants, run against REAL `app/data/*.parquet` artefacts (P7-built v2
schema, contract v1.3) -- no fixtures, no mocks, no fabricated data. Every
check below is either a full-table vectorised pandas pass over the raw
parquet (cheap: the largest table here, `collab_pair_topics.parquet`, is
13.4M rows and a column comparison over it runs in well under a second) or a
frame-level check over a small, deterministic, stratified institution sample
(module-scoped fixtures build every `metric_frame` combo ONCE and every other
test reads from that shared dict -- see the `frames` fixture).

Bug -> invariant map (each item is a round-3 user-reported bug from
`brainstorms/2026-08-31-benchup-gate2br3-refinement.md` "Root causes
established before the grill"; the right column is the test in THIS file that
now pins it so it cannot regress silently):

| # | Round-3 bug (brainstorm root cause)                                | Invariant here                                                    |
|---|----------------------------------------------------------------------|---------------------------------------------------------------------|
| 1 | SDG share 264.8% (multi-label x16-goal fan-out, window mismatch)    | test_share_family_bounded_zero_one; test_sdg_mass_any_le_field_mass_full_table |
| 2 | Dynamics "-16.4%" beside gutter "3.7 -> 4.5/yr" (value/gutter basis mismatch) | test_dynamics_gutter_reconciles_to_value_same_basis          |
| 3 | PP gutter hard-FULL / SDG dynamics hard-FRAC (no basis toggle)      | test_denom_value_finite_wherever_value_is_finite (pp + sdg dynamics, both bases) |
| 4 | Tooltip denominators always "NA" (NOTE string, not a number)        | test_denom_value_finite_wherever_value_is_finite                  |
| 5 | Gaps table "expected == gap" (top-100-capped `joint_observed`)      | test_untapped_joint_observed_matches_uncapped_topic_vols          |
| 6 | Joint 1,882 vs top-decile-covered 1,642 (all-types vs CORE-AR basis mismatch) | test_ordering_n_top10_le_n_covered_le_vol_full_tables; test_cross_view_pin_collaborate_field_vol |
| 7 | Momentum machinery correctness (new this phase, ruling 6)           | test_momentum_vocabulary_and_stat_rules                           |
| 8 | FWCI invariant (new this phase, ruling 4)                            | test_fwci_stratum_citation_weighted_mean_equals_one; test_fwci_median_nonnegative_and_null_rate_sane |
| 9 | Cross-view drift (Find profile vs Compare vs raw parquet)           | test_cross_view_pin_field_share_find_compare_parquet              |

Session-scoped fixtures SKIP (never fail) the whole module when
`app/data/collab_pairs.parquet` is absent -- CI without the data snapshot
exits clean, per the brief's "skip-if-absent CI guard".

Runtime budget: this file + test_golden_numbers.py together < 120 s (brief
acceptance). Frame-level checks use one fixed 25(+3 named-anchor)-institution
stratified sample (by `total_full_2020_2024` percentile, deterministic --
`np.linspace` over the sorted population, no RNG) rather than the full
7,557-institution population.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from lib import collab_data as CL
from lib import compare_data as CD
from lib import profile_data as P
from lib.engine import build_substrates, load_context

APP_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = APP_DIR / "data"
FWCI_DIR = APP_DIR.parent / "data" / "interim" / "fwci"  # pipeline-internal, NOT deployed (data_contract.yaml)

STRASBOURG, IFPEN, GDANSK, ISCTE, SORBONNE, ETH = (
    "I68947357", "I265217849", "I40413290", "I110026055", "I39804081", "I35440088")
CNRS = "I1294671590"

pytestmark = pytest.mark.skipif(
    not (DATA_DIR / "collab_pairs.parquet").exists(),
    reason="app/data/*.parquet v2 artefacts not present -- skip-if-absent CI guard (WT_2BR3.md P7 not yet built)")


# ============================================================================
# fixtures
# ============================================================================

@pytest.fixture(scope="module")
def ctx():
    return load_context(DATA_DIR)


@pytest.fixture(scope="module")
def subs_frac(ctx):
    return build_substrates(ctx, tree="bestfit", basis="frac")


@pytest.fixture(scope="module")
def subs_full(ctx):
    return build_substrates(ctx, tree="bestfit", basis="full")


@pytest.fixture(scope="module")
def sample_ids():
    """25 institutions stratified by `total_full_2020_2024` percentile (ranks
    evenly spaced over the SORTED population, `np.linspace` -- deterministic,
    no randomness) plus the 3 named anchors this suite's golden numbers use
    (Strasbourg, IFPEN, CNRS), so every level/metric combo below gets both
    broad population coverage and guaranteed non-trivial rows."""
    idx = pd.read_parquet(DATA_DIR / "index.parquet",
                          columns=["institution_id", "total_full_2020_2024"]).dropna()
    idx = idx.sort_values("total_full_2020_2024").reset_index(drop=True)
    positions = np.linspace(0, len(idx) - 1, 25).astype(int)
    ids = idx.loc[positions, "institution_id"].tolist()
    for extra in (STRASBOURG, IFPEN, CNRS):
        if extra not in ids:
            ids.append(extra)
    return ids


_SUBFIELD_PROBE_FIELD_ID = 27  # Medicine -- broad enough that most sample institutions have >0 mass here

# Every (metric, level, extra-kwargs) combo the frame-level checks below need.
# Built ONCE per basis in the `frames` fixture (module-scoped) so the suite
# pays for each `metric_frame()` call exactly once, not once per test.
_COMBOS = [
    ("share", "field", {}),
    ("share", "subfield", {"field_id": _SUBFIELD_PROBE_FIELD_ID}),
    ("share", "erc", {}),
    ("share", "sdg", {}),
    ("si", "field", {}),
    ("si", "subfield", {"field_id": _SUBFIELD_PROBE_FIELD_ID}),
    ("si", "erc", {}),
    ("sdg_share", "field", {}),
    ("pp", "field", {"tree": "bestfit", "floor": 30}),
    ("dynamics", "field", {}),
    ("dynamics", "subfield", {"field_id": _SUBFIELD_PROBE_FIELD_ID}),
    ("dynamics", "sdg", {}),
]


@pytest.fixture(scope="module")
def frames(ctx, subs_frac, subs_full, sample_ids):
    """{(metric, level, basis_name): metric_frame(...)} for every combo in
    `_COMBOS`, both bases -- shared by every frame-level test below."""
    out = {}
    for basis_name, subs in (("frac", subs_frac), ("full", subs_full)):
        for metric, level, kw in _COMBOS:
            if not CD.metric_frame_available(metric, level):
                continue
            out[(metric, level, basis_name)] = CD.metric_frame(ctx, subs, sample_ids, level, metric, **kw)
    return out


# ============================================================================
# item 1 -- share-family metric_frame values in [0,1]; si >= 0 (bug #1)
# ============================================================================

def test_share_family_bounded_zero_one(frames):
    """share/sdg_share/pp are all denominated as a fraction of a whole --
    every value must land in [0,1] (float tolerance 1e-6 for float32 storage
    round-trips). This is the direct regression guard for the round-3 SDG
    264.8% bug (the multi-label x16-goal fan-out that produced shares > 100%)
    -- both `share` (sdg-grain, per-goal, contract-documented 0<=share<=1 per
    row) and `sdg_share` (field-grain cross, the metric the bug lived in)."""
    checked = 0
    for (metric, level, basis), df in frames.items():
        if metric not in ("share", "sdg_share", "pp"):
            continue
        bad = df[(df["value"] < -1e-9) | (df["value"] > 1.0 + 1e-6)]
        assert bad.empty, (
            f"{metric}@{level} basis={basis} out of [0,1]: "
            f"{bad[['institution_id', 'taxon_id', 'value']].to_dict('records')}")
        checked += len(df)
    assert checked > 100, f"too few rows checked: {checked}"


def test_si_nonnegative(frames):
    """si has no documented upper bound (a highly specialised institution can
    legitimately score si >> 1) but is a ratio of nonnegative shares, so it
    can never be negative."""
    checked = 0
    for (metric, level, basis), df in frames.items():
        if metric != "si":
            continue
        bad = df[df["value"] < -1e-9]
        assert bad.empty, f"si@{level} basis={basis} negative: {bad[['institution_id', 'taxon_id', 'value']].to_dict('records')}"
        checked += len(df)
    assert checked > 50, f"too few rows checked: {checked}"


# ============================================================================
# item 2 -- sdg mass_any <= field mass, SAME basis, FULL TABLE, both bases
# (bug #1's structural fix, verified at the source table, not just at the
# sampled metric_frame layer above)
# ============================================================================

def test_sdg_mass_any_le_field_mass_full_table():
    """`sdg_fields.parquet` v2's distinct-tagged `mass_any_frac`/`mass_any_full`
    can never exceed `fields.parquet`'s own `vol_frac`/`vol_full` for the SAME
    (institution, field, tree=bestfit) cell -- a work counting once toward a
    field's SDG-tagged mass cannot exceed the field's own total mass. Checked
    on EVERY row of both tables (bestfit only -- `fields.parquet` ships no
    other tree), both bases, vectorised (no Python row loop)."""
    sdg_fields = pd.read_parquet(DATA_DIR / "sdg_fields.parquet")
    fields = pd.read_parquet(DATA_DIR / "fields.parquet",
                             columns=["institution_id", "field_id", "tree", "vol_frac", "vol_full"])
    sub = sdg_fields[(sdg_fields["tree"] == "bestfit") & (sdg_fields["field_id"] != -1)]
    fb = fields[fields["tree"] == "bestfit"].set_index(["institution_id", "field_id"])
    merged = sub.set_index(["institution_id", "field_id"]).join(fb[["vol_frac", "vol_full"]], how="left")

    missing = merged["vol_frac"].isna().sum()
    assert missing == 0, f"{missing} sdg_fields cells have no matching fields.parquet row (should be impossible: fields.parquet ships every nonzero-mass cell)"

    bad_frac = merged[merged["mass_any_frac"] > merged["vol_frac"] + 1e-4]
    assert bad_frac.empty, f"mass_any_frac > vol_frac (fractional basis): {len(bad_frac)} / {len(merged):,} cells"
    bad_full = merged[merged["mass_any_full"] > merged["vol_full"] + 1e-4]
    assert bad_full.empty, f"mass_any_full > vol_full (full basis): {len(bad_full)} / {len(merged):,} cells"
    assert len(merged) > 50_000, f"suspiciously few cells checked: {len(merged)}"


# ============================================================================
# item 3 -- n_top10 <= n_covered <= vol on EVERY row of the two field/topic
# collab tables (bug #6's structural guarantee, full table, vectorised)
# ============================================================================

def test_ordering_n_top10_le_n_covered_le_vol_full_tables():
    for name in ("collab_pair_fields.parquet", "collab_pair_topics.parquet", "collab_pairs.parquet"):
        cols = ["n_top10", "n_covered"] + (["core_total"] if name == "collab_pairs.parquet" else ["vol"])
        df = pd.read_parquet(DATA_DIR / name, columns=cols)
        vol_col = "core_total" if name == "collab_pairs.parquet" else "vol"
        bad = df[(df["n_top10"] > df["n_covered"]) | (df["n_covered"] > df[vol_col])]
        assert bad.empty, f"{name}: n_top10<=n_covered<={vol_col} violated on {len(bad)} / {len(df):,} rows"


# ============================================================================
# item 4 -- dynamics reconciliation: THE test for the round-3 "-16.4% beside
# 3.7 -> 4.5/yr" bug (item 2 in the plan)
# ============================================================================

_DYNAMICS_GUTTER_RE = re.compile(rf"^(-?[\d.]+) {re.escape(CD.DYNAMICS_ARROW)} (-?[\d.]+)/yr$")


def test_dynamics_gutter_reconciles_to_value_same_basis(frames):
    """Parse `vol_display`'s 'w1 -> w2/yr' gutter string and assert
    (w2-w1)/w1 matches `value` -- on the SAME basis the frame itself was
    built on (never a cross-basis comparison: the round-3 bug was exactly a
    silent basis mismatch between `value`, computed on the CURRENT basis, and
    the gutter, hard-wired to FULL). Uses the row's own (unrounded)
    `denom_value` as w1 (it equals w1 exactly by construction, per
    `_field_dynamics_frame`'s own code: `denom_value = w1 if w1 > 0 else nan`)
    so only the display-rounded w2 needs parsing out of the string -- this
    keeps the reconciliation tolerance tight without being sensitive to the
    string's own 1-decimal-place rounding on BOTH ends. Rows with a small w1
    (< 5.0) are skipped for the numeric reconciliation (1-dp rounding on a
    small base can swing the ratio by more than a sane tolerance) but every
    row's `vol_display` must still match the fixed 'w1 -> w2/yr' shape."""
    checked = 0
    for (metric, level, basis), df in frames.items():
        if metric != "dynamics":
            continue
        for _, row in df.iterrows():
            m = _DYNAMICS_GUTTER_RE.match(str(row["vol_display"]))
            assert m, f"vol_display does not match 'w1 -> w2/yr': {row['vol_display']!r} (level={level} basis={basis})"
            w2 = float(m.group(2))
            w1 = row["denom_value"]
            if pd.isna(row["value"]):
                assert pd.isna(w1) or float(m.group(1)) <= 0.0, (
                    f"value is NaN but the gutter's own w1 is positive: {row.to_dict()}")
                continue
            if pd.isna(w1) or w1 < 5.0:
                continue  # too small a base for 1-dp string rounding to reconcile tightly
            want = (w2 - float(w1)) / float(w1)
            assert abs(float(row["value"]) - want) < 0.01, (
                f"DYNAMICS VALUE/GUTTER BASIS MISMATCH (the round-3 bug): level={level} basis={basis} "
                f"taxon={row['taxon_id']} value={row['value']} gutter={row['vol_display']!r} implies {want}")
            checked += 1
    assert checked > 100, f"too few dynamics rows reconciled: {checked}"


# ============================================================================
# item 5 -- denom_value finite wherever value is finite (bugs #3/#4: the
# hover "NA" bug and the hard-FULL/hard-FRAC gutter bugs)
# ============================================================================

def test_denom_value_finite_wherever_value_is_finite(frames):
    """share/sdg_share/pp/dynamics all carry a genuine count-style
    denominator (SS2.5 v4 contract) -- wherever `value` is a real number,
    `denom_value` must be too (never the string-through-`_fmt_vol` "NA" bug).
    si/vol/vol_top10 are DOCUMENTED exceptions (no natural count-style
    denominator -- a population-mean ratio or a raw count) and are
    deliberately excluded here, matching `metric_frame`'s own docstrings."""
    checked = 0
    for (metric, level, basis), df in frames.items():
        if metric not in ("share", "sdg_share", "pp", "dynamics"):
            continue
        finite_val = df["value"].apply(lambda v: v is not None and pd.notna(v) and np.isfinite(float(v)))
        bad = df[finite_val & df["denom_value"].isna()]
        assert bad.empty, (
            f"denom_value is NaN/None where value is finite (the hover-'NA' bug): {metric}@{level} basis={basis}: "
            f"{bad[['institution_id', 'taxon_id', 'value']].to_dict('records')}")
        checked += int(finite_val.sum())
    assert checked > 100, f"too few finite-value rows checked: {checked}"


# ============================================================================
# item 6 -- FWCI: citation-weighted stratum-mean == 1 (ruling 4 invariant)
# ============================================================================

_FWCI_FILES_PRESENT = (FWCI_DIR / "fwci_ref.parquet").exists() and (FWCI_DIR / "fwci_work.parquet").exists()


@pytest.mark.skipif(not _FWCI_FILES_PRESENT, reason="pipeline-internal fwci_ref/fwci_work.parquet not present (not deployed to app/data -- V3/data/interim/fwci/ only)")
def test_fwci_stratum_citation_weighted_mean_equals_one():
    """FWCI(work) = cited_by_count / mean_cited(subfield x year x type
    stratum) -- by construction, the mean of fwci over the works THAT
    STRATUM'S mean_cited was itself computed from must equal 1.0, on every
    NON-FALLBACK (subfield-level) stratum. Tolerance 1e-6 (float32 storage
    rounding, same disclosed widening as `evals/invariants_p7.py`'s own
    check -- the plan's 1e-9 is a float64 mathematical guarantee, unreachable
    once fwci is stored as float32)."""
    ref = pd.read_parquet(FWCI_DIR / "fwci_ref.parquet")
    work = pd.read_parquet(FWCI_DIR / "fwci_work.parquet")
    non_fb = ref[ref["fallback_level"] == "subfield"]
    keys = set(zip(non_fb["subfield_id"], non_fb["year"], non_fb["type"]))

    w = work.dropna(subset=["fwci"])
    mask = np.array([k in keys for k in zip(w["subfield_id"], w["year"], w["type"])])
    non_fb_work = w[mask]
    means = non_fb_work.groupby(["subfield_id", "year", "type"], observed=True)["fwci"].mean()
    max_dev = float((means - 1.0).abs().max())
    assert max_dev <= 1e-6, f"citation-weighted mean(fwci) deviates from 1.0 by {max_dev:.3e} on some stratum"
    assert len(means) >= 1000, f"suspiciously few non-fallback strata checked: {len(means)}"


def test_fwci_median_nonnegative_and_null_rate_sane():
    """`fwci_median` (a MEDIAN of nonnegative per-work FWCI ratios) can never
    be negative, on all 3 collab tables. Null-rate check is DELIBERATELY
    approximate (CD4's own progress note flags this): SS2.4's 'null when < 3
    covered works' means covered-by-a-valid-FWCI-value, a DIFFERENT concept
    from the PP-threshold `n_covered` column tested elsewhere in this suite
    -- so this checks only that the null rate among clearly-qualifying rows
    (n_covered >= 10, safely above the <3 floor even allowing for the ~0.07%
    topicless-work edge case) is small, not that it is exactly zero."""
    for name in ("collab_pairs.parquet", "collab_pair_fields.parquet", "collab_pair_topics.parquet"):
        vol_col = "core_total" if name == "collab_pairs.parquet" else "vol"
        df = pd.read_parquet(DATA_DIR / name, columns=["n_covered", "fwci_median", vol_col])
        neg = df[df["fwci_median"].notna() & (df["fwci_median"] < -1e-9)]
        assert neg.empty, f"{name}: {len(neg)} rows have a negative fwci_median"

        qualifying = df[df["n_covered"] >= 10]
        if len(qualifying) == 0:
            continue
        null_rate = float(qualifying["fwci_median"].isna().mean())
        assert null_rate < 0.01, (
            f"{name}: fwci_median null on {null_rate:.2%} of rows with n_covered>=10 "
            f"(expected near-zero; the <3-valid-FWCI-works floor should almost never bind above n_covered=10)")


# ============================================================================
# item 7 -- momentum: vocabulary, up/down significance, MED band, weak rule
# (ruling 6, full table, vectorised)
# ============================================================================

def test_momentum_vocabulary_and_stat_rules():
    cp = pd.read_parquet(DATA_DIR / "collab_pairs.parquet",
                         columns=["c1", "c2", "mom_class", "mom_rr", "mom_p"])
    facts = json.loads((DATA_DIR / "collab_facts.json").read_text(encoding="utf-8"))
    alpha = facts["alpha"]

    allowed = {"up", "down", "stable", "ns", "new", "dormant", "weak"}
    observed = set(cp["mom_class"].dropna().unique().tolist())
    assert observed <= allowed, f"unexpected mom_class value(s): {observed - allowed}"

    assert 0.8 <= facts["med"] <= 1.3, f"collab_facts.json MED out of the [0.8,1.3] sanity band: {facts['med']}"

    up_down = cp[cp["mom_class"].isin(["up", "down"])]
    bad_p = up_down[~(up_down["mom_p"] < alpha)]
    assert bad_p.empty, (
        f"{len(bad_p)} 'up'/'down'-classified rows have mom_p >= alpha ({alpha}) or null -- "
        f"the z-test demotion to 'ns' should have caught these")

    weak_range = (cp["c1"] > 0) & (cp["c1"] < 5)
    mismatch_a = cp[weak_range & (cp["mom_class"] != "weak")]
    mismatch_b = cp[(cp["mom_class"] == "weak") & ~weak_range]
    assert mismatch_a.empty, f"{len(mismatch_a)} rows with 0<c1<5 are NOT classified 'weak'"
    assert mismatch_b.empty, f"{len(mismatch_b)} rows classified 'weak' do NOT have 0<c1<5"


# ============================================================================
# item 8 -- collab_topic_vols pair set == collab_pairs qualifying set;
# untapped()'s joint_observed matches the uncapped table exactly (bug #5)
# ============================================================================

def test_collab_topic_vols_pair_set_matches_qualifying_pairs():
    """Vectorised (merge-based, never a Python set-of-15M-tuples loop --
    that measured 30s+ in a naive form during this stream's own calibration,
    the merge form runs in ~1.5s). Tolerance <=5 mirrors `evals/
    invariants_p7.py`'s own disclosed edge case: a qualifying pair whose
    every joint work lacks a primary topic never enters a topic-grain table
    at all (~0.07% of works corpus-wide)."""
    cp = pd.read_parquet(DATA_DIR / "collab_pairs.parquet", columns=["a", "b", "core_total"])
    ctv = pd.read_parquet(DATA_DIR / "collab_topic_vols.parquet", columns=["a", "b"])
    qualifying = cp.loc[cp["core_total"] >= 5, ["a", "b"]].drop_duplicates()
    ctv_pairs = ctv.drop_duplicates()
    merged = qualifying.merge(ctv_pairs.assign(_in_ctv=True), on=["a", "b"], how="outer", indicator=True)
    diff = int((merged["_merge"] != "both").sum())
    assert diff <= 5, f"collab_topic_vols pair set vs collab_pairs core_total>=5 qualifying set: symmetric diff {diff}"


@pytest.mark.parametrize("a,b", [(STRASBOURG, SORBONNE), (STRASBOURG, IFPEN), (CNRS, STRASBOURG)])
def test_untapped_joint_observed_matches_uncapped_topic_vols(ctx, subs_frac, a, b):
    """THE regression guard for bug #5 ('gaps table expected==gap', the
    top-100-capped `joint_observed` undercount): every `joint_observed` value
    `untapped()` returns must equal the pair's own uncapped
    `collab_topic_vols.parquet` row exactly (0 only when that topic is
    TRULY absent from the uncapped table, never merely outside a cap)."""
    got = CL.untapped(ctx, subs_frac, a, b, top_n=25)
    df = got["topics"]
    if df.empty:
        pytest.skip(f"no untapped rows (gap>0) for {a}/{b} -- nothing to check")
    raw = CL._load_collab_topic_vols(ctx)
    lo, hi = sorted([a, b])
    raw_row = raw[(raw["a"] == lo) & (raw["b"] == hi)].set_index("topic_id")["vol"]
    for _, row in df.iterrows():
        want = float(raw_row.get(row["topic_id"], 0.0))
        assert row["joint_observed"] == want, (
            f"untapped() joint_observed={row['joint_observed']} != collab_topic_vols row {want} "
            f"for topic {row['topic_id']} (pair {a}/{b}) -- the exact top-100-cap undercount bug")


# ============================================================================
# item 9 -- cross-view pins: Find profile field share == Compare share-frame
# value == fields.parquet raw, byte-equal; Collaborate field vol ==
# collab_pair_fields row exactly
# ============================================================================

_PIN_IDS = [STRASBOURG, IFPEN, GDANSK, SORBONNE, ETH]


@pytest.mark.parametrize("basis", ["frac", "full"])
def test_cross_view_pin_field_share_find_compare_parquet(ctx, subs_frac, subs_full, basis):
    """`profile_data.fields_table` (what the Find profile page shows) ==
    `compare_data.metric_frame(..., 'field', 'share')` (what Compare shows)
    == a fresh raw read of `fields.parquet`'s own `share_<basis>` column, for
    5 institutions, both bases -- byte-equal (no arithmetic between the three
    reads, so an exact-equality check is the right bar, not a tolerance)."""
    subs = subs_frac if basis == "frac" else subs_full
    share_col = f"share_{basis}"
    fields_raw = pd.read_parquet(DATA_DIR / "fields.parquet",
                                 columns=["institution_id", "field_id", "tree", share_col])
    fields_raw = fields_raw[fields_raw["tree"] == "bestfit"]

    for iid in _PIN_IDS:
        find_df = P.fields_table(ctx, subs, iid).set_index("field_id")["share"]
        compare_df = CD.metric_frame(ctx, subs, [iid], "field", "share").set_index("taxon_id")["value"]
        raw_row = fields_raw[fields_raw["institution_id"] == iid].set_index("field_id")[share_col]

        assert set(find_df.index) == set(raw_row.index), f"{iid}/{basis}: Find profile field set != fields.parquet field set"
        np.testing.assert_array_equal(
            find_df.reindex(raw_row.index).to_numpy(dtype="float64"),
            raw_row.to_numpy(dtype="float64"),
            err_msg=f"{iid}/{basis}: Find profile share != fields.parquet raw share")
        np.testing.assert_array_equal(
            compare_df.reindex(raw_row.index).to_numpy(dtype="float64"),
            raw_row.to_numpy(dtype="float64"),
            err_msg=f"{iid}/{basis}: Compare share-frame value != fields.parquet raw share")


def test_cross_view_pin_collaborate_field_vol(ctx):
    """`collab_data.field_breakdown` (what Collaborate's field chart is built
    from, SS1.6) == a fresh raw read of `collab_pair_fields.parquet` v2, for
    2 real pairs -- exact integer equality on `vol`/`n_top10`/`n_covered`."""
    raw = pd.read_parquet(DATA_DIR / "collab_pair_fields.parquet")
    for a, b in [(CNRS, STRASBOURG), (STRASBOURG, IFPEN)]:
        lo, hi = sorted([a, b])
        raw_rows = raw[(raw["a"] == lo) & (raw["b"] == hi)].set_index("field_id")
        if raw_rows.empty:
            continue
        got = CL.field_breakdown(ctx, a, b).set_index("field_id")
        for fid, raw_row in raw_rows.iterrows():
            got_row = got.loc[fid]
            assert int(got_row["vol"]) == int(raw_row["vol"]), f"{a}/{b} field {fid}: vol mismatch"
            assert int(got_row["n_top10"]) == int(raw_row["n_top10"]), f"{a}/{b} field {fid}: n_top10 mismatch"
            assert int(got_row["n_covered"]) == int(raw_row["n_covered"]), f"{a}/{b} field {fid}: n_covered mismatch"

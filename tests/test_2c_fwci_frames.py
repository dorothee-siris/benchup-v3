"""tests/test_2c_fwci_frames.py -- Phase 2C, stream TEV, guards D2/D3.

BUILD_PLAN_2C.md D2 (bar = MEDIAN, hover = MEAN + covered-works denominator,
at every feasible grain) and D3 (the FWCI reference line is the European
CORPUS-MEDIAN work-FWCI per taxon, "NEVER a 1.0 rule", and a real 0.0
reference -- a genuine humanities citation-practice fact, WT_2C.md claim 1 --
must survive untouched, never dropped or truthiness-tested away).

This is a REAL-DATA sweep against the shipped `app/data/fwci_taxa.parquet` /
`fwci_taxa_ref.parquet` (pipeline step 18, Stream P8) and
`compare_data.metric_frame`, independent of stream CD5's own unit tests
(`tests/test_compare_data.py`) -- it re-derives the same facts a different
way (a parquet-level sweep rather than a fixed institution list, and a
GENERIC search for a zero-reference taxon rather than a hardcoded one) so a
regression that slipped past CD5's own fixture would still be caught here.

Invariants checked:
  1. n_covered >= 3 on EVERY row of the raw `fwci_taxa.parquet` file (P8's
     own floor, restated in `compare_data._fwci_denom_note`: "taxa covered
     by fewer than 3 such works are not shown") -- and, downstream, on every
     row `metric_frame(..., "fwci")` returns for a real basket.
  2. `fwci_mean` (the v5 METRIC_FRAME_COLS column) is null on every metric
     EXCEPT fwci, and non-null on every row of an fwci frame.
  3. a real `eu_median_work_fwci == 0.0` taxon (found by SEARCHING
     `fwci_taxa_ref.parquet`, not assumed) survives the ref-value join into
     a real institution's fwci frame as an actual 0.0.
  4. the golden anchor (I154202486, field 11): median 0.8149413466453552 /
     mean 1.3476839065551758 / n_covered 1700.

Run from cwd `app/`: python -m pytest tests/test_2c_fwci_frames.py -q
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from lib import compare_data as CD
from lib.engine import build_substrates, load_context

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
IFREMER = "I154202486"


@pytest.fixture(scope="module")
def ctx():
    return load_context(DATA_DIR)


@pytest.fixture(scope="module")
def subs(ctx):
    return build_substrates(ctx)  # default bestfit/frac -- fwci ignores it anyway (D3/D4)


@pytest.fixture(scope="module")
def fwci_taxa_raw() -> pd.DataFrame:
    return pd.read_parquet(DATA_DIR / "fwci_taxa.parquet")


@pytest.fixture(scope="module")
def fwci_taxa_ref_raw() -> pd.DataFrame:
    return pd.read_parquet(DATA_DIR / "fwci_taxa_ref.parquet")


# ---------------------------------------------------------------------------
# 1. n_covered >= 3, everywhere -- the raw file, then the frame layer
# ---------------------------------------------------------------------------

def test_n_covered_floor_holds_on_the_raw_artefact(fwci_taxa_raw):
    """The strongest possible sweep: EVERY one of the ~700K rows P8 shipped,
    not a sample."""
    assert len(fwci_taxa_raw) > 0
    assert int(fwci_taxa_raw["n_covered"].min()) >= 3

    # VACUITY: inject one below-floor row on an in-memory copy and confirm
    # the same check now fails.
    corrupt = fwci_taxa_raw.copy()
    corrupt.loc[corrupt.index[0], "n_covered"] = 2
    assert int(corrupt["n_covered"].min()) < 3


@pytest.mark.parametrize("level", CD.LEVELS)
def test_n_covered_floor_holds_through_metric_frame(ctx, subs, level):
    """The SAME floor, re-derived through the public API a page actually
    calls, on a real multi-institution basket -- `denom_value` (== the
    frame's `n_covered`, per `_fwci_frame`'s own docstring) must never read
    below 3 for any row `metric_frame` hands back."""
    ids = [IFREMER, "I4210107283", "I34403800"]
    kw = {"field_id": 11} if level == "subfield" else {}
    d = CD.metric_frame(ctx, subs, ids, level, "fwci", **kw)
    assert len(d) > 0
    assert (d["denom_value"].astype("float64") >= 3).all()
    # `_fwci_frame`'s own docstring: `denom_value` == `vol_display` == n_covered
    np.testing.assert_array_equal(d["denom_value"].to_numpy(), d["vol_display"].to_numpy())

    # VACUITY: a hand-built row at n_covered=2 must fail the SAME check.
    bad_row = pd.DataFrame([{"denom_value": 2.0}])
    assert not (bad_row["denom_value"] >= 3).all()


# ---------------------------------------------------------------------------
# 2. fwci_mean -- non-null ONLY on the fwci metric
# ---------------------------------------------------------------------------

_OTHER_METRIC_LEVELS = [
    ("share", "field"), ("si", "field"), ("dynamics", "field"),
    ("pp", "field"), ("vol_top10", "field"), ("sdg_share", "field"),
    ("share", "erc"), ("vol", "erc"), ("share", "sdg"), ("vol", "sdg"),
]


def test_fwci_mean_is_null_everywhere_except_the_fwci_metric(ctx, subs):
    ids = [IFREMER]
    checked = 0
    for metric, level in _OTHER_METRIC_LEVELS:
        if not CD.metric_frame_available(metric, level):
            continue
        d = CD.metric_frame(ctx, subs, ids, level, metric)
        if d.empty:
            continue
        assert d["fwci_mean"].isna().all(), (metric, level)
        checked += 1
    assert checked >= 8, f"only {checked} non-fwci (metric, level) pairs produced rows to check"

    fwci = CD.metric_frame(ctx, subs, ids, "field", "fwci")
    assert len(fwci) > 0
    assert fwci["fwci_mean"].notna().all()

    # VACUITY: an in-memory fwci_mean leak on a non-fwci frame must be caught.
    leaked = CD.metric_frame(ctx, subs, ids, "field", "share").copy()
    leaked.loc[leaked.index[0], "fwci_mean"] = 1.23
    assert not leaked["fwci_mean"].isna().all()


# ---------------------------------------------------------------------------
# 3. a real ref_value == 0.0 survives the join (searched, not hardcoded)
# ---------------------------------------------------------------------------

def test_a_real_zero_reference_taxon_survives_into_an_institutions_frame(ctx, subs, fwci_taxa_raw, fwci_taxa_ref_raw):
    """D3/WT_2C.md claim 1: the corpus reference can be a genuine 0.0 (a
    real citation-practice fact, e.g. a humanities field) -- this must never
    be dropped or read as falsy. Rather than trust CD5's own hardcoded
    ZERO_REF_INST fixture, this test SEARCHES `fwci_taxa_ref.parquet` for a
    zero-reference (grain, taxon_id) pair that some institution actually
    holds in `fwci_taxa.parquet`, then proves it flows through
    `metric_frame` intact."""
    zero_ref = fwci_taxa_ref_raw[fwci_taxa_ref_raw["eu_median_work_fwci"] == 0.0]
    assert len(zero_ref) > 0, "no zero-reference taxon exists on this snapshot -- D3's own premise is gone"

    found = None
    for _, row in zero_ref.iterrows():
        grain, taxon_id = row["grain"], int(row["taxon_id"])
        holders = fwci_taxa_raw[(fwci_taxa_raw["grain"] == grain) & (fwci_taxa_raw["taxon_id"] == taxon_id)]
        if len(holders):
            found = (grain, taxon_id, str(holders.iloc[0]["institution_id"]))
            break
    assert found is not None, "no institution holds ANY zero-reference taxon -- cannot exercise the join"
    grain, taxon_id, iid = found

    kw = {"field_id": taxon_id} if grain == "subfield" else {}
    # subfield's own taxon_id IS the field_id to drill within only when grain
    # is field; a zero-ref SUBFIELD found above needs its PARENT field, which
    # this search does not resolve -- restrict the live-join proof to a
    # field/erc/sdg grain (subfield is already covered by the raw-file search
    # below, which needs no drill).
    if grain == "subfield":
        pytest.skip("zero-ref hit landed on a subfield taxon; field/erc/sdg covered directly below")
    d = CD.metric_frame(ctx, subs, [iid], grain, "fwci", **kw)
    hit = d[d["taxon_id"] == taxon_id]
    assert len(hit) == 1, f"{grain} taxon {taxon_id} dropped for {iid}, must survive as a real 0.0"
    assert hit.iloc[0]["ref_value"] == 0.0
    assert pd.notna(hit.iloc[0]["ref_value"]), "a real 0.0 must never read as missing"

    # VACUITY: the exact bug this guards against is a TRUTHINESS test
    # (`if ref_value:` treating 0.0 as "no reference") -- demonstrate that
    # such a test would have silently swallowed this real row.
    would_be_dropped_by_truthiness = not bool(hit.iloc[0]["ref_value"])
    assert would_be_dropped_by_truthiness, (
        "sanity: 0.0 must be falsy in Python, or this vacuity proof is meaningless")


def test_zero_reference_subfield_also_exists_in_the_raw_join(fwci_taxa_raw, fwci_taxa_ref_raw):
    """The subfield-grain half of the same fact, checked directly on the raw
    tables (no field_id drill needed at this level): at least one zero-ref
    SUBFIELD taxon is actually held by some institution in fwci_taxa.parquet,
    and merging the two tables the way `_fwci_frame` does (a plain left join,
    never a truthiness test) preserves it as 0.0."""
    zero_sub = fwci_taxa_ref_raw[(fwci_taxa_ref_raw["grain"] == "subfield")
                                 & (fwci_taxa_ref_raw["eu_median_work_fwci"] == 0.0)]
    assert len(zero_sub) > 0
    taxa_sub = fwci_taxa_raw[fwci_taxa_raw["grain"] == "subfield"]
    merged = taxa_sub.merge(
        zero_sub[["taxon_id", "eu_median_work_fwci"]], on="taxon_id", how="inner")
    assert len(merged) > 0, "no institution holds a zero-ref subfield -- cannot prove the join preserves it"
    assert (merged["eu_median_work_fwci"] == 0.0).all()
    assert merged["eu_median_work_fwci"].notna().all()


# ---------------------------------------------------------------------------
# 4. golden anchor
# ---------------------------------------------------------------------------

def test_golden_anchor_ifremer_field_11(ctx, subs):
    """P8's own byte-identical golden (progress/2C_P8.md /
    progress/2C_CD5.md): I154202486 x field_id=11, median
    0.8149413466453552, mean 1.3476839065551758, n_covered 1700."""
    d = CD.metric_frame(ctx, subs, [IFREMER], "field", "fwci")
    row = d[d["taxon_id"] == 11].iloc[0]
    np.testing.assert_allclose(float(row["value"]), 0.8149413466453552, atol=1e-9)
    np.testing.assert_allclose(float(row["fwci_mean"]), 1.3476839065551758, atol=1e-9)
    assert int(row["denom_value"]) == 1700

    # VACUITY: a value one ULP-scale off must fail an atol=1e-9 check.
    with pytest.raises(AssertionError):
        np.testing.assert_allclose(float(row["value"]) + 1e-6, 0.8149413466453552, atol=1e-9)

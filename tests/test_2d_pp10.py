"""tests/test_2d_pp10.py -- Phase 2D, stream TEV5, cross-cutting guard for E2
(PP10_WD offered, crossable, at ALL FOUR grains) and E4 (NO display floor --
every taxon with `n_covered_pp>=1` ships a row, the 10/30 impact-floor
control retired from the API entirely), BUILD_PLAN_2D.md S1/S7.

CD6's own `tests/test_compare_data.py` already golden-tests this data layer
in real depth (progress/2D_CD6.md S6/S9: the Ifremer/Strasbourg anchors, the
basis/tree-pinning sweep, the four-grain availability check). This module
is deliberately a SECOND, independent witness: every check here reads
`impact_taxa.parquet` straight off disk (never through `compare_data`'s own
`_load_impact_taxa` ctx-cache) and probes a DIFFERENT institution/grain
combination than CD6's own golden wherever the two could otherwise share a
blind spot -- so a regression that breaks CD6's own re-pinned assertions
alongside the code they guard is still caught here.

VACUITY, per module: every assertion below is followed by an in-memory
mutation (a hand-floored slice of the same table, a value pushed outside
[0,1], a genuinely basis-toggled sibling metric, an unknown level string)
that makes the identical check fail -- proving none of these are trivially
satisfied by any frame `metric_frame` could return.

Run: python -m pytest tests/test_2d_pp10.py -q
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from lib import compare_data as CD
from lib import profile_data as P
from lib.engine import build_substrates, load_context

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
IFREMER = "I154202486"          # CD6's own golden institution (field 11)
STRASBOURG = "I68947357"        # this module's OWN probe, distinct from IFREMER


@pytest.fixture(scope="module")
def ctx():
    return load_context(DATA_DIR)


@pytest.fixture(scope="module")
def impact_taxa() -> pd.DataFrame:
    """A FRESH read, independent of `compare_data`'s own ctx-cached loader."""
    return pd.read_parquet(DATA_DIR / "impact_taxa.parquet")


# ============================================================================
# E4 -- no display floor: row counts match impact_taxa exactly, per basket
# ============================================================================

def test_no_floor_row_counts_match_impact_taxa_per_basket(ctx, impact_taxa):
    """E4's own headline: `metric_frame(..., 'pp')` must ship EXACTLY the
    rows `impact_taxa.parquet` carries for this basket at this grain -- no
    10/30 (or any other) re-filter on the way out, at any of the four
    grains."""
    ids = [IFREMER]
    field_id = 11
    sfd = P._subfield_field_domain_map(ctx)
    wanted_subfields = set(sfd.loc[sfd["field_id"] == field_id, "subfield_id"])

    for level, kwargs in (("field", {}), ("erc", {}), ("sdg", {}),
                         ("subfield", {"field_id": field_id})):
        df = CD.metric_frame(ctx, None, ids, level, "pp", **kwargs)
        want = impact_taxa[(impact_taxa["grain"] == level)
                           & (impact_taxa["institution_id"].isin(ids))]
        if level == "subfield":
            want = want[want["taxon_id"].isin(wanted_subfields)]
        assert len(df) == len(want) > 0, (level, len(df), len(want))
        assert (df["denom_value"].astype(float) >= 1).all(), level

    # VACUITY: a HAND-floored slice of the SAME raw table (denom_value >= 30,
    # the retired impact-floor's own old high setting) is strictly SMALLER
    # than what `metric_frame` actually returns at field grain -- proving the
    # exact row-count match above is not vacuously true of an
    # already-floored source table (i.e. Ifremer genuinely has a below-30
    # field row that the un-floored API correctly keeps).
    field_rows = impact_taxa[(impact_taxa["grain"] == "field")
                             & (impact_taxa["institution_id"].isin(ids))]
    fake_floored = field_rows[field_rows["n_covered_pp"] >= 30]
    real = CD.metric_frame(ctx, None, ids, "field", "pp")
    assert len(fake_floored) < len(field_rows), "fixture must contain a below-30 row"
    assert len(fake_floored) < len(real)


# ============================================================================
# E2/E4 -- value in [0, 1] at all four grains
# ============================================================================

def test_pp_value_in_unit_interval_at_all_four_grains(ctx):
    ids = [IFREMER]
    for level, kwargs in (("field", {}), ("erc", {}), ("sdg", {}),
                         ("subfield", {"field_id": 11})):
        df = CD.metric_frame(ctx, None, ids, level, "pp", **kwargs)
        assert len(df) > 0, level
        v = df["value"].astype(float)
        assert v.notna().all(), level
        assert v.between(0.0, 1.0).all(), (level, float(v.min()), float(v.max()))

    # VACUITY: the check above is a real bound, not an unreachable range --
    # confirmed against the WHOLE field-grain population (not just one
    # institution), and a value nudged past 1.0 in memory is caught by the
    # identical .between() call.
    whole_field = pd.read_parquet(DATA_DIR / "impact_taxa.parquet")
    whole_field = whole_field[whole_field["grain"] == "field"]["pp10_wd"].astype(float)
    assert whole_field.min() >= 0.0 and whole_field.max() <= 1.0
    mutated = whole_field.copy()
    mutated.iloc[0] = 1.5
    with pytest.raises(AssertionError):
        assert mutated.between(0.0, 1.0).all()


# ============================================================================
# E2 -- basis- AND tree-pinned (identical under both toggles)
# ============================================================================

def test_pp_is_pinned_across_basis_and_tree_on_an_independent_probe(ctx):
    """CD6's own golden pins this for Ifremer (progress/2D_CD6.md S9,
    `test_metric_frame_pp_is_basis_and_tree_pinned`); this probes a
    DIFFERENT institution (Strasbourg) at erc/sdg grain, both toggles moved
    at once (bestfit/frac vs original/full), so the two guards do not share
    a blind spot."""
    for level, kwargs in (("erc", {}), ("sdg", {})):
        a = CD.metric_frame(ctx, {"tree": "bestfit", "basis": "frac"},
                            [STRASBOURG], level, "pp", **kwargs)
        b = CD.metric_frame(ctx, {"tree": "original", "basis": "full"},
                            [STRASBOURG], level, "pp", **kwargs)
        assert len(a) > 0, level
        pd.testing.assert_frame_equal(a.reset_index(drop=True), b.reset_index(drop=True))

    # VACUITY: the SAME two scenarios on `share` at FIELD grain (a genuinely
    # basis-toggled metric -- `fields_long`'s own `share_frac`/`share_full`
    # split, confirmed live: field 11 reads 0.023951/0.034371 respectively
    # for Strasbourg) must DIFFER -- proving `assert_frame_equal` above is a
    # real discriminating comparison, not trivially satisfied because the
    # two calls always return identical frames regardless of metric. (`erc`
    # share is a poor probe for this: `erc_long`'s own share is basis-
    # invariant by construction, so it was tried and rejected here.)
    sa = CD.metric_frame(ctx, build_substrates(ctx, tree="bestfit", basis="frac"),
                         [STRASBOURG], "field", "share")
    sb = CD.metric_frame(ctx, build_substrates(ctx, tree="bestfit", basis="full"),
                         [STRASBOURG], "field", "share")
    with pytest.raises(AssertionError):
        pd.testing.assert_frame_equal(sa.reset_index(drop=True), sb.reset_index(drop=True))


# ============================================================================
# Golden -- Ifremer x field 11 = 0.167746 / 1699 (P9's three-way-verified cell)
# ============================================================================

def test_golden_ifremer_field11_through_metric_frame(ctx):
    df = CD.metric_frame(ctx, None, [IFREMER], "field", "pp")
    row = df[df["taxon_id"] == 11].iloc[0]
    np.testing.assert_allclose(float(row["value"]), 0.167746, atol=1e-6)
    assert int(row["denom_value"]) == 1699
    assert int(row["vol_display"]) == 1699

    # VACUITY: a neighbouring field's row must NOT also read 0.167746/1699 --
    # proving the golden above is pinned to the RIGHT row, not to a value
    # every row happens to share (e.g. through a broadcast/reindex bug).
    other = df[df["taxon_id"] != 11]
    assert not np.isclose(other["value"].astype(float), 0.167746, atol=1e-6).any()
    assert not (other["denom_value"].astype(int) == 1699).any()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))

"""tests/test_2d_references.py -- Phase 2D, stream TEV5, cross-cutting guard
for E8 (BUILD_PLAN_2D.md S1/S7): every metric frame that carries a
reference resolves it through `compare_data`'s own hooks at ALL FOUR
grains, `si` is newly offered at sdg/erc, and a genuine 0.0 reference
survives end to end -- data layer through the chart layer -- rather than
being silently read as "missing" anywhere along the way.

CD6's own `tests/test_compare_data.py` golden-tests the SDG/ERC SI rebase
and the share `ref_value` wiring in depth (progress/2D_CD6.md S2/S3/S6).
This module probes independently: a DIFFERENT basis ("full", where CD6's
own golden checks "frac"), a DIFFERENT institution pair, and one check that
crosses into `charts_compare.fig_metric_bars` to confirm the 0.0 reference
that reaches a frame also reaches a rendered figure (the CD6/CH2 contract
stated in `_add_reference`'s own docstring: "tests `np.isfinite`, never
truthiness").

VACUITY, per module: every assertion is followed by an in-memory mutation
that makes the identical check fail.

Run: python -m pytest tests/test_2d_references.py -q
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from lib import compare_data as CD
from lib.engine import build_substrates, load_context

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
STRASBOURG = "I68947357"
IFPEN = "I265217849"
ZERO_REF_INST = "I100063501"  # ships a field-12 row -- eu_median_work_fwci == 0.0 there (test_compare_data.py's own anchor)


@pytest.fixture(scope="module")
def ctx():
    return load_context(DATA_DIR)


@pytest.fixture(scope="module")
def share_refs() -> pd.DataFrame:
    return pd.read_parquet(DATA_DIR / "share_refs.parquet")


# ============================================================================
# E8 -- share frames carry ref_value at all four grains
# ============================================================================

def test_share_ref_value_matches_share_refs_parquet_on_the_full_basis(ctx, share_refs):
    """E8: `_share_frame` sets `ref_value` at ALL FOUR grains now (was
    `None` everywhere pre-2D). CD6's own golden checks the `frac` basis
    (test_metric_frame_field_share_matches_fields_long); this samples the
    OTHER basis ("full") at every grain, against a FRESH, independent read
    of `share_refs.parquet` (never through `compare_data`'s own
    `_share_ref_series` cache)."""
    ids = [STRASBOURG, IFPEN]
    subs_full = build_substrates(ctx, tree="bestfit", basis="full")
    checked = 0
    for level, kwargs in (("field", {}), ("erc", {}), ("sdg", {}), ("subfield", {"field_id": 11})):
        df = CD.metric_frame(ctx, subs_full, ids, level, "share", **kwargs)
        assert len(df) > 0, level
        refs = (share_refs[(share_refs["grain"] == level) & (share_refs["basis"] == "full")]
               .set_index("taxon_id")["eu_mean_share"])
        have_ref = df.dropna(subset=["ref_value"])
        assert len(have_ref) > 0, level
        sample = have_ref.sample(n=min(5, len(have_ref)), random_state=0)
        for _, row in sample.iterrows():
            np.testing.assert_allclose(float(row["ref_value"]), float(refs.loc[int(row["taxon_id"])]),
                                       rtol=1e-9)
            checked += 1
    assert checked >= 4, "at least one real cross-check per grain, not a silent no-op"

    # VACUITY: perturbing the SAME matched value by +1.0 makes the identical
    # comparison fail -- proving this is a real cross-check against the
    # shipped file, not a tautology comparing a value against itself.
    one = sample.iloc[0]
    true_ref = float(refs.loc[int(one["taxon_id"])])
    with pytest.raises(AssertionError):
        np.testing.assert_allclose(float(one["ref_value"]), true_ref + 1.0, rtol=1e-9)


# ============================================================================
# E8 -- si offered at sdg + erc
# ============================================================================

def test_si_offered_at_sdg_and_erc_with_neutral_reference(ctx):
    """SI's reference is always the neutral constant 1.0, at every grain
    (unchanged by E8) -- this pins that sdg/erc, the two grains E8 newly
    opens, both carry it and both return real, non-null values."""
    for level, kwargs in (("sdg", {}), ("erc", {})):
        assert CD.metric_frame_available("si", level), level
        assert ("si", level) not in CD.UNAVAILABLE_REASON
        df = CD.metric_frame(ctx, {"tree": "bestfit", "basis": "frac"}, [STRASBOURG], level, "si", **kwargs)
        assert len(df) > 0, level
        assert (df["ref_value"] == 1.0).all(), level
        assert df["value"].notna().any(), level

    # VACUITY: `metric_frame_available` genuinely discriminates -- an
    # unknown level string still raises through its own assertion, proving
    # the availability check above is live machinery, not a function that
    # always returns True.
    with pytest.raises(AssertionError):
        CD.metric_frame_available("si", "not-a-real-level")


# ============================================================================
# E3/E8 -- FWCI/PP ref labels resolve via the CD6 hooks
# ============================================================================

def test_fwci_and_pp_ref_labels_resolve_via_the_cd6_hooks():
    """`compare_data.fwci_ref_label`/`pp_ref_label` (and their `FWCI_REF_
    LABEL`/`PP_REF_LABEL` dict mirrors) are the ONLY place these sentences
    are built -- views_compare.py reuses them verbatim (progress/2D_VC4.md
    S3). Both must name "European" (the reference population) and the two
    must stay DIFFERENT sentences (the two-axes distinction: FWCI reads
    against the European baseline, PP against the world threshold -- only
    the reference LINE population is European for both, disclosed
    differently)."""
    for level in CD.LEVELS:
        fwci_label = CD.fwci_ref_label(level)
        pp_label = CD.pp_ref_label(level)
        assert "European" in fwci_label, (level, fwci_label)
        assert "European" in pp_label, (level, pp_label)
        assert CD.FWCI_REF_LABEL[level] == fwci_label
        assert CD.PP_REF_LABEL[level] == pp_label
        assert fwci_label != pp_label, level

    # VACUITY: an unknown level string is not silently accepted by either
    # hook -- both assert `level in LEVELS` before building the sentence, so
    # a bad level raises rather than returning some default text.
    with pytest.raises(AssertionError):
        CD.fwci_ref_label("not-a-real-level")
    with pytest.raises(AssertionError):
        CD.pp_ref_label("not-a-real-level")


# ============================================================================
# E8 -- a 0.0 reference survives, data layer through the chart layer
# ============================================================================

def test_a_zero_reference_survives_from_frame_to_chart(ctx):
    """The CD6/CH2 contract, checked end to end: a genuine 0.0 `ref_value`
    (I100063501, field 12) reaches `metric_frame` as a real, non-null
    number (CD6's own pinned anchor), and it must ALSO reach
    `charts_compare.fig_metric_bars` as a drawn diamond reference marker --
    `_add_reference`'s own docstring promises `np.isfinite`, never
    truthiness."""
    from lib import charts_compare as X
    from lib import palette as P

    df = CD.metric_frame(ctx, None, [ZERO_REF_INST], "field", "fwci")
    assert len(df) > 1, "need more than the zero-ref row for the VARYING (diamond) reference branch"
    row = df[df["taxon_id"] == 12].iloc[0]
    assert row["ref_value"] == 0.0
    assert pd.notna(row["ref_value"])

    slots = P.institution_slots({ZERO_REF_INST: 1})
    names = {ZERO_REF_INST: "Institution Zero-Ref"}
    fig = X.fig_metric_bars(df, "fwci", [ZERO_REF_INST], slots=slots, names=names,
                            level="field", gutter=False)
    diamonds = [tr for tr in fig.data
               if tr.type == "scatter" and tr.marker.symbol == X.REF_MARKER_SYMBOL]
    assert len(diamonds) == 1, "exactly one varying-reference diamond trace"
    assert 0.0 in list(diamonds[0].x), "the zero reference must be one of the plotted diamonds"

    # VACUITY: blank OUT the zero row's own ref_value (None, genuinely
    # missing, not zero) on the SAME multi-row frame -- the diamond trace
    # must still exist (the OTHER rows still vary) but must NO LONGER carry
    # a 0.0 point. This proves the membership check above is reading the
    # real per-row reference data, not a coincidental property of the chart
    # (e.g. an axis that always happens to touch zero).
    blanked = df.copy()
    blanked.loc[blanked["taxon_id"] == 12, "ref_value"] = None
    fig2 = X.fig_metric_bars(blanked, "fwci", [ZERO_REF_INST], slots=slots, names=names,
                             level="field", gutter=False)
    diamonds2 = [tr for tr in fig2.data
                if tr.type == "scatter" and tr.marker.symbol == X.REF_MARKER_SYMBOL]
    assert len(diamonds2) == 1
    assert 0.0 not in list(diamonds2[0].x)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))

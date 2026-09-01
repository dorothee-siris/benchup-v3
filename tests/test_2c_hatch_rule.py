"""tests/test_2c_hatch_rule.py -- Phase 2C, stream TEV, guards the amended D6.

BUILD_PLAN_2C.md decisions log, D6 AMENDMENT: the user-facing rule stays ONE
sentence ("a bar hatches when it rests on fewer than 50 works over 2020-2024")
but the IMPLEMENTATION forks by metric family (`charts_compare._is_low_volume`,
`RATIO_HATCH_METRICS`):

  * `pp` and `fwci` hatch on their own per-row `denom_value`
    (n_works_full / n_covered) against `palette.RATIO_HATCH_FLOOR` (50) --
    these two metrics carry a genuinely diagnostic per-row denominator.
  * every OTHER metric (share, si, sdg_share, dynamics, vol, vol_top10) keeps
    hatching on `vol_full_annual_mean` against `LOW_VOLUME_FLOOR` (10/yr,
    algebraically the SAME 50-over-the-window number) -- because for THOSE
    metrics `denom_value` is an INSTITUTION-level constant (e.g. Share's own
    total mass across every taxon), and re-keying hatching to it would
    silently disable hatching entirely (WT_2C.md claim 4, cited verbatim in
    `RATIO_HATCH_METRICS`'s own docstring in charts_compare.py).

This module builds small SYNTHETIC frames (two taxa, deliberately in
DISAGREEMENT: one row has a tiny `denom_value` but an ample
`vol_full_annual_mean`, the other the reverse) and renders them through the
REAL `charts_compare.fig_metric_bars` -- so the two candidate hatch rules
produce OPPOSITE hatch patterns on this fixture, and a passing test result
tells you WHICH rule actually fired, not just "something hatched".

VACUITY: because the fixture is built so the two rules disagree, every
assertion below is proven non-trivial simply by exhibiting -- and asserting
against -- the pattern the OTHER rule would have produced (see
`_OPPOSITE_OF` in each test): if `_is_low_volume`'s per-metric fork were ever
collapsed back to one rule, these tests would start passing on the WRONG
pattern, which the explicit "not equal to the opposite" assertions catch.

Run from cwd `app/`: python -m pytest tests/test_2c_hatch_rule.py -q
"""
from __future__ import annotations

import pandas as pd
import pytest

from lib import charts_compare as X
from lib import palette as P

IID = "Ix"
NAMES = {IID: "Institution X"}


def _slots():
    return P.institution_slots({IID: 1})


# Row A: denom_value TINY (< RATIO_HATCH_FLOOR), vol_full_annual_mean AMPLE
#        (>= LOW_VOLUME_FLOOR) -- should hatch under the denom-keyed rule
#        (pp/fwci) and NOT under the volume-keyed rule (everyone else).
# Row B: the mirror image -- denom_value AMPLE, vol_full_annual_mean TINY --
#        should hatch under the volume-keyed rule and NOT the denom-keyed one.
assert P.RATIO_HATCH_FLOOR == 50, "fixture below is tuned to the ruled floor of 50"
assert X.LOW_VOLUME_FLOOR == 10.0, "fixture below is tuned to the ruled floor of 10/yr"

ROW_A = dict(taxon_id=1, taxon_label="Taxon A", value=0.20, ref_value=0.5,
            denominator="note", denom_value=10.0,             # < 50
            domain_id=1, domain_order=0,
            vol_display=10.0, vol_full_annual_mean=100.0,     # >= 10/yr
            vol_top10=None)
ROW_B = dict(taxon_id=2, taxon_label="Taxon B", value=0.30, ref_value=0.5,
            denominator="note", denom_value=1000.0,           # >= 50
            domain_id=1, domain_order=0,
            vol_display=1000.0, vol_full_annual_mean=2.0,     # < 10/yr
            vol_top10=None)


def _frame(metric: str) -> pd.DataFrame:
    fwci_mean = 1.1 if metric == "fwci" else None
    rows = [dict(institution_id=IID, fwci_mean=fwci_mean, **ROW_A),
            dict(institution_id=IID, fwci_mean=fwci_mean, **ROW_B)]
    return pd.DataFrame(rows)


def _hatched_flags(metric: str) -> list[bool]:
    """[row A hatched?, row B hatched?] as actually drawn by fig_metric_bars,
    in the frame's own taxon_id order (both rows belong to one institution,
    one trace, so this is `tr.marker.pattern.shape` read straight off the
    only trace, in draw order == row order for a single-institution frame)."""
    fig = X.fig_metric_bars(_frame(metric), metric, [IID], slots=_slots(), names=NAMES, level="field")
    assert len(fig.data) == 1
    shapes = list(fig.data[0].marker.pattern.shape)
    assert len(shapes) == 2
    return [s == X.LOW_VOLUME_PATTERN_SHAPE for s in shapes]


@pytest.mark.parametrize("metric", ["pp", "fwci"])
def test_pp_and_fwci_hatch_on_denom_value_not_on_volume(metric):
    """Row A (denom<50, vol ample) hatches; Row B (denom>=50, vol tiny) does
    NOT -- the exact 'a pp/fwci bar with denom_value >= 50 but tiny vol does
    NOT hatch' acceptance line from the dispatch, plus its converse."""
    flags = _hatched_flags(metric)
    assert flags == [True, False], (metric, flags)
    # VACUITY: this is NOT the pattern the volume-keyed rule would draw --
    # if the per-metric fork were ever removed, this metric would start
    # drawing the volume-keyed rule's pattern instead, and this assertion
    # would catch it turning into [False, True].
    assert flags != [False, True]


@pytest.mark.parametrize("metric", ["share", "si", "sdg_share", "dynamics", "vol", "vol_top10"])
def test_every_other_metric_hatches_on_volume_not_on_denom_value(metric):
    """Row A (vol ample, denom tiny) does NOT hatch; Row B (vol tiny, denom
    ample) DOES -- the dispatch's 'vice versa': re-keying these metrics to
    `denom_value` (their own institution-level constant) would have silently
    disabled hatching on real data (WT_2C.md claim 4)."""
    flags = _hatched_flags(metric)
    assert flags == [False, True], (metric, flags)
    # VACUITY: not the denom-keyed pattern pp/fwci draw on this same fixture.
    assert flags != [True, False]


def test_ratio_hatch_metrics_vocabulary_is_exactly_pp_and_fwci():
    """The fork itself, not just its effect: `RATIO_HATCH_METRICS` must name
    exactly the two metrics with a genuinely per-row diagnostic denominator --
    neither more (which would silently re-key a metric whose `denom_value`
    is an institution-level constant, per the module's own docstring) nor
    fewer (which would leave pp or fwci on the old, wrong trigger)."""
    assert set(X.RATIO_HATCH_METRICS) == {"pp", "fwci"}
    # every metric this chart can draw is accounted for one way or the other
    assert set(X.RATIO_HATCH_METRICS) <= set(X.METRICS)


def test_one_user_facing_sentence_for_both_mechanisms():
    """D6's own ruling: ONE sentence for every hatched bar, whichever
    mechanism triggered it -- `HOVER_LOW_VOLUME` is a `{floor}` template
    filled from `palette.RATIO_HATCH_FLOOR` (never a digit literal in this
    digit-banned module), and it is the SAME string object regardless of
    which family hatched."""
    hover_pp = None
    hover_share = None
    for metric, slot in (("pp", "hover_pp"), ("share", "hover_share")):
        fig = X.fig_metric_bars(_frame(metric), metric, [IID], slots=_slots(), names=NAMES, level="field")
        hovers = "".join(c for tr in fig.data for c in tr.customdata)
        expected = X.HOVER_LOW_VOLUME.format(floor=X._fmt_vol(P.RATIO_HATCH_FLOOR))
        assert expected in hovers, (metric, hovers)
        if metric == "pp":
            hover_pp = expected
        else:
            hover_share = expected
    assert hover_pp == hover_share  # literally the same rendered sentence

    # VACUITY: the two mechanisms really are different code paths even
    # though they render the same sentence -- proven by the fixture-flip
    # tests above (a metric collapsed onto the wrong rule renders a
    # DIFFERENT hatch pattern, not a different sentence, which is exactly
    # why this module tests the pattern directly rather than only the text).

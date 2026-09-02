"""tests/test_2c_hatch_rule.py -- Phase 2C, stream TEV, guards the amended D6;
REWRITTEN Phase 2D (stream CH2, BUILD_PLAN_2D.md S7 2026-09-02 ruling, E5) to
pin the NEW ruled rendering after the hatch/hollow machinery was deleted.

The per-metric FLOOR FORK itself is UNCHANGED (E4: the floors do not move) --
`charts_compare._is_low_volume`/`RATIO_HATCH_METRICS` still decide, exactly as
before, which family keys off which column:

  * `pp` and `fwci` caution on their own per-row `denom_value`
    (n_works_full / n_covered) against `palette.RATIO_HATCH_FLOOR` (50) --
    these two metrics carry a genuinely diagnostic per-row denominator.
  * every OTHER metric (share, si, sdg_share, dynamics, vol, vol_top10) keeps
    cautioning on `vol_full_annual_mean` against `LOW_VOLUME_FLOOR` (10/yr,
    algebraically the SAME 50-over-the-window number) -- because for THOSE
    metrics `denom_value` is an INSTITUTION-level constant (e.g. Share's own
    total mass across every taxon), and re-keying cautioning to it would
    silently disable it entirely (WT_2C.md claim 4, cited verbatim in
    `RATIO_HATCH_METRICS`'s own docstring in charts_compare.py).

What CHANGED (2D, E5) is how a flagged row is DRAWN: every bar is now SOLID,
in the institution's own colour -- no hollow fill, no diagonal
`marker.pattern` anywhere in `fig_metric_bars` -- and the flagged row's VALUE
text switches to `palette.WARNING_CAPTION_COLOR` (never bold), keeping the
dagger. This module builds the SAME small SYNTHETIC frames as before (two
taxa, deliberately in DISAGREEMENT: one row has a tiny `denom_value` but an
ample `vol_full_annual_mean`, the other the reverse) and renders them through
the REAL `charts_compare.fig_metric_bars` -- so the two candidate caution
rules produce OPPOSITE caution-text patterns on this fixture, and a passing
test result tells you WHICH rule actually fired, not just "something was
cautioned".

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

from lib import charts as C
from lib import charts_compare as X
from lib import palette as P

IID = "Ix"
NAMES = {IID: "Institution X"}


def _slots():
    return P.institution_slots({IID: 1})


def _ink() -> str:
    return P.institution_ink(_slots()[IID])


# Row A: denom_value TINY (< RATIO_HATCH_FLOOR), vol_full_annual_mean AMPLE
#        (>= LOW_VOLUME_FLOOR) -- should caution under the denom-keyed rule
#        (pp/fwci) and NOT under the volume-keyed rule (everyone else).
# Row B: the mirror image -- denom_value AMPLE, vol_full_annual_mean TINY --
#        should caution under the volume-keyed rule and NOT the denom-keyed one.
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


def _render(metric: str):
    """The one real trace this single-institution frame draws -- `gutter=False`
    isolates the caution-CHANNEL assertions below from the separate E6 left-
    gutter-column feature (its own dedicated tests live in
    tests/test_charts_compare.py)."""
    fig = X.fig_metric_bars(_frame(metric), metric, [IID], slots=_slots(), names=NAMES,
                            level="field", gutter=False)
    assert len(fig.data) == 1
    return fig.data[0]


def _caution_flags(metric: str) -> list[bool]:
    """[row A cautioned?, row B cautioned?], read off the ONE trace's per-point
    `textfont.color` array, in the frame's own taxon_id order (both rows
    belong to one institution, one trace, so draw order == row order for a
    single-institution frame). Also pins E5's two other invariants on the
    SAME trace: every bar stays SOLID (no SURFACE fill, no pattern shape) and
    every outline keeps the SAME width -- the caution lives in text colour
    ALONE now, nothing about the bar's own geometry changes."""
    tr = _render(metric)
    colors = list(tr.textfont.color)
    assert len(colors) == 2
    ink = _ink()
    assert set(colors) <= {ink, P.WARNING_CAPTION_COLOR}
    assert P.SURFACE not in tr.marker.color
    assert not any(tr.marker.pattern.shape or ())
    assert tr.marker.line.width == C.HAIRLINE_PX
    return [c == P.WARNING_CAPTION_COLOR for c in colors]


@pytest.mark.parametrize("metric", ["pp", "fwci"])
def test_pp_and_fwci_caution_on_denom_value_not_on_volume(metric):
    """Row A (denom<50, vol ample) is cautioned; Row B (denom>=50, vol tiny)
    is NOT -- the exact 'a pp/fwci bar with denom_value >= 50 but tiny vol
    does NOT get the caution treatment' acceptance line from the dispatch,
    plus its converse."""
    flags = _caution_flags(metric)
    assert flags == [True, False], (metric, flags)
    # VACUITY: this is NOT the pattern the volume-keyed rule would draw --
    # if the per-metric fork were ever removed, this metric would start
    # drawing the volume-keyed rule's pattern instead, and this assertion
    # would catch it turning into [False, True].
    assert flags != [False, True]


@pytest.mark.parametrize("metric", ["share", "si", "sdg_share", "dynamics", "vol", "vol_top10"])
def test_every_other_metric_cautions_on_volume_not_on_denom_value(metric):
    """Row A (vol ample, denom tiny) is NOT cautioned; Row B (vol tiny, denom
    ample) IS -- the dispatch's 'vice versa': re-keying these metrics to
    `denom_value` (their own institution-level constant) would have silently
    disabled cautioning on real data (WT_2C.md claim 4)."""
    flags = _caution_flags(metric)
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


def test_dagger_still_marks_every_cautioned_value():
    """2D kept the dagger (E5): the caution channel is TEXT COLOUR + dagger
    together, never colour alone -- a reader who cannot distinguish the two
    inks still sees the glyph."""
    for metric in ("pp", "share"):
        tr = _render(metric)
        daggered = [X.LOW_VOLUME_GLYPH in t for t in tr.text]
        cautioned = [c == P.WARNING_CAPTION_COLOR for c in tr.textfont.color]
        assert daggered == cautioned, (metric, daggered, cautioned)
        assert any(cautioned), metric


def test_one_user_facing_sentence_for_both_mechanisms():
    """D6's own ruling: ONE sentence for every cautioned bar, whichever
    mechanism triggered it -- `HOVER_LOW_VOLUME` is a `{floor}` template
    filled from `palette.RATIO_HATCH_FLOOR` (never a digit literal in this
    digit-banned module), and it is the SAME string object regardless of
    which family cautioned."""
    hover_pp = None
    hover_share = None
    for metric, slot in (("pp", "hover_pp"), ("share", "hover_share")):
        tr = _render(metric)
        hovers = "".join(tr.customdata)
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
    # DIFFERENT caution pattern, not a different sentence, which is exactly
    # why this module tests the per-point text colour directly rather than
    # only the hover text).

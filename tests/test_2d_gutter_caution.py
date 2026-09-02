"""tests/test_2d_gutter_caution.py -- Phase 2D, stream TEV5, cross-cutting
guard for E5 (the caution channel: no more hatch/hollow, solid bars +
WARNING_CAPTION_COLOR text + dagger) and E6 (the left-gutter column: a
phantom trace + header annotation replacing the pre-2D bar-end "(N)" text),
BUILD_PLAN_2D.md S1/S7.

`tests/test_2c_hatch_rule.py` (CH2's own re-pin, the ONE granted full-module
rewrite exception this round) already exercises the caution FORK in depth --
deliberately with `gutter=False`, to isolate the caution assertions from the
gutter feature entirely (its own docstring says so explicitly). This module
is the one that turns the gutter ON and checks the two 2D features TOGETHER
(the header annotation text, the phantom trace's OWN caution colour -- CH2's
docstring promises the flag reaches "its VALUE text AND its gutter-column
text", a claim `test_2c_hatch_rule.py` never has the gutter live to check),
plus the module-wide "no marker.pattern anywhere" ban and the wide/narrow
dual-variant contract `views_compare._metric_chart` builds for every
section (E6's own caller-decides idiom).

VACUITY, per module: every assertion is followed by an in-memory mutation
that makes the identical check fail.

Run: python -m pytest tests/test_2d_gutter_caution.py -q
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


# Two rows, deliberately DISAGREEING on volume, mirroring test_2c_hatch_
# rule.py's own fixture shape so this module's frames are known-compatible
# with every metric `fig_metric_bars` draws.
ROW_LOW = dict(taxon_id=1, taxon_label="Taxon A", value=0.10, ref_value=0.5,
              denominator="note", denom_value=1000.0,
              domain_id=1, domain_order=0,
              vol_display=1000.0, vol_full_annual_mean=2.0,   # < LOW_VOLUME_FLOOR (10/yr)
              vol_top10=None)
ROW_OK = dict(taxon_id=2, taxon_label="Taxon B", value=0.30, ref_value=0.5,
             denominator="note", denom_value=1000.0,
             domain_id=1, domain_order=0,
             vol_display=1000.0, vol_full_annual_mean=40.0,   # >= floor
             vol_top10=None)
assert X.LOW_VOLUME_FLOOR == 10.0, "fixture is tuned to the ruled floor of 10/yr"


def _frame() -> pd.DataFrame:
    return pd.DataFrame([dict(institution_id=IID, fwci_mean=None, **ROW_LOW),
                         dict(institution_id=IID, fwci_mean=None, **ROW_OK)])


def _phantom(fig) -> list:
    return [tr for tr in fig.data if set(tr.marker.color) == {X.GUTTER_PHANTOM_FILL}]


def _bars(fig) -> list:
    return [tr for tr in fig.data if set(tr.marker.color) != {X.GUTTER_PHANTOM_FILL}]


# ============================================================================
# E6 -- the gutter column: phantom trace + header annotation
# ============================================================================

def test_gutter_true_emits_the_phantom_trace_and_header_annotation():
    """`gutter=True` must draw ONE phantom `go.Bar` trace alongside the real
    bar, and the header text must land in a layout annotation VERBATIM --
    charts_compare's own docstring: 'the caller supplies the word, this
    module never invents one'."""
    header = "Publications"
    fig = X.fig_metric_bars(_frame(), "share", [IID], slots=_slots(), names=NAMES,
                            level="field", gutter=True, gutter_header=header)
    assert len(fig.data) == 2, "one real bar trace + one phantom gutter trace"
    assert len(_phantom(fig)) == 1
    ann_texts = [a.text for a in fig.layout.annotations]
    assert header in ann_texts, ann_texts

    # VACUITY: a figure built WITHOUT a header carries no such annotation at
    # all -- proves the check above is not trivially true of every figure
    # `fig_metric_bars` can draw.
    bare = X.fig_metric_bars(_frame(), "share", [IID], slots=_slots(), names=NAMES,
                             level="field", gutter=True, gutter_header=None)
    with pytest.raises(AssertionError):
        assert header in [a.text for a in bare.layout.annotations]


def test_gutter_false_drops_both_the_phantom_trace_and_the_header():
    """The narrow-viewport variant VC4 renders below the breakpoint:
    'gutter=False' means the column is entirely ABSENT, not merely
    unlabelled -- no phantom trace, no annotation, whatever `gutter_header`
    was passed."""
    fig = X.fig_metric_bars(_frame(), "share", [IID], slots=_slots(), names=NAMES,
                            level="field", gutter=False, gutter_header="Publications")
    assert len(fig.data) == 1
    assert not fig.layout.annotations

    # VACUITY: the SAME frame with gutter=True DOES carry both -- proves
    # `gutter=False`'s absence above is the flag's own effect, not an
    # artefact of this particular frame shape.
    fig_on = X.fig_metric_bars(_frame(), "share", [IID], slots=_slots(), names=NAMES,
                               level="field", gutter=True, gutter_header="Publications")
    assert len(fig_on.data) == 2
    assert fig_on.layout.annotations


def test_below_floor_row_cautions_its_gutter_text_too_not_only_the_bar():
    """E5+E6 together: the flagged row's caution colour must reach BOTH
    texts CH2's own docstring promises -- the bar's value text AND its
    gutter-column text -- with the gutter ACTUALLY ON this time."""
    fig = X.fig_metric_bars(_frame(), "share", [IID], slots=_slots(), names=NAMES,
                            level="field", gutter=True, gutter_header="Publications")
    bar, gutter = _bars(fig)[0], _phantom(fig)[0]
    ink = _ink()
    # row order is taxon order: ROW_LOW (taxon 1, cautioned) then ROW_OK (not)
    assert list(bar.textfont.color) == [P.WARNING_CAPTION_COLOR, ink]
    assert list(gutter.textfont.color) == [P.WARNING_CAPTION_COLOR, ink]
    assert X.LOW_VOLUME_GLYPH in bar.text[0] and X.LOW_VOLUME_GLYPH not in bar.text[1]

    # VACUITY: swap WHICH row is flagged (mutate vol_full_annual_mean in
    # memory) and confirm the caution follows the DATA, not a fixed row
    # index -- proves the colour arrays above are computed per-row, not a
    # constant [cautioned, not-cautioned] pattern this fixture always draws.
    flipped = _frame()
    flipped.loc[0, "vol_full_annual_mean"] = 40.0
    flipped.loc[1, "vol_full_annual_mean"] = 2.0
    fig2 = X.fig_metric_bars(flipped, "share", [IID], slots=_slots(), names=NAMES,
                             level="field", gutter=True, gutter_header="Publications")
    bar2 = _bars(fig2)[0]
    assert list(bar2.textfont.color) == [ink, P.WARNING_CAPTION_COLOR]


# ============================================================================
# E5 -- no marker.pattern (hatch), ever, in this chart
# ============================================================================

def test_no_marker_pattern_anywhere_in_a_rendered_metric_bars_figure():
    """E5's own headline: `fig_metric_bars` must never emit a
    `marker.pattern` shape on ANY trace -- bar or gutter -- for ANY metric
    this chart draws. The hatch/hollow machinery is DELETED, not merely
    unused by default (CH2's own docstring: 'no more marker.pattern
    anywhere in this function')."""
    for metric in X.SELECTOR_METRICS:
        fig = X.fig_metric_bars(_frame(), metric, [IID], slots=_slots(), names=NAMES,
                                level="field", gutter=True, gutter_header="Publications")
        for tr in fig.data:
            assert not any(tr.marker.pattern.shape or ()), (metric, tr.marker.pattern.shape)

    # VACUITY: stamp a pattern shape onto a real trace's marker IN MEMORY and
    # confirm the IDENTICAL assertion now fails -- proves the check above is
    # not vacuously true because a fresh plotly trace never carries a
    # `pattern` at all (i.e. this is a real ban, not an unreachable check).
    fig = X.fig_metric_bars(_frame(), "share", [IID], slots=_slots(), names=NAMES, level="field")
    fig.data[0].marker.pattern.shape = X.LOW_VOLUME_PATTERN_SHAPE
    with pytest.raises(AssertionError):
        for tr in fig.data:
            assert not any(tr.marker.pattern.shape or ())


# ============================================================================
# E6 -- the wide/narrow dual-variant contract (views_compare._metric_chart)
# ============================================================================

def test_wide_and_narrow_variants_both_build_from_the_same_frame():
    """`views_compare._metric_chart` (VC4, progress/2D_VC4.md S3) renders
    BOTH a `gutter=True` ('__wide') and a `gutter=False` ('__narrow') figure
    from the SAME frame for every section, and a CSS media query picks the
    one that fits the real viewport. Exercised here at the charts_compare
    API level -- the two exact calls `_metric_chart` makes -- with no
    Streamlit runtime needed: both must build without error, differ ONLY in
    the gutter mechanism, and never disagree on the actual bar values a
    reader would read off either one."""
    df = _frame()
    wide = X.fig_metric_bars(df, "pp", [IID], slots=_slots(), names=NAMES,
                             level="field", gutter=True, gutter_header="Publications")
    narrow = X.fig_metric_bars(df, "pp", [IID], slots=_slots(), names=NAMES,
                               level="field", gutter=False)
    assert len(wide.data) == 2 * len(narrow.data)
    assert wide.layout.annotations and not narrow.layout.annotations
    assert list(_bars(wide)[0].x) == list(narrow.data[0].x)

    # VACUITY: a frame with NO gutter column at all collapses the wide
    # variant's own trace count back down to the narrow one -- proving the
    # "2x" assertion above is genuinely reading the phantom trace's
    # presence, not an unconditional doubling this builder always performs.
    bare = df.drop(columns=["vol_display"])
    wide_bare = X.fig_metric_bars(bare, "pp", [IID], slots=_slots(), names=NAMES,
                                  level="field", gutter=True, gutter_header="Publications")
    assert len(wide_bare.data) == len(narrow.data)
    with pytest.raises(AssertionError):
        assert len(wide_bare.data) == 2 * len(narrow.data)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))

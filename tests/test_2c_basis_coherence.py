"""tests/test_2c_basis_coherence.py -- Phase 2C, stream TEV, guards D4.

BUILD_PLAN_2C.md D4 ("Basis policy ... no chart mixes bases between value and
gutter; enforcement test ships") plus the decisions log's D4 codification:
"pinned metrics (pp, fwci) ... show an explicit basis chip/caption" while
"fwci: all columns identical" under the toggle and "pp: value identical,
gutter follows basis by contract" (progress/2C_CD5.md's own D4 audit table,
which additionally certifies erc/sdg share+si as basis-INVARIANT by design --
`_vol_display_col_for` always returns "mass" for those two levels -- and
certifies the ONE bug it found and fixed: `_field_pp_frame`'s `vol_top10`
branch, where `vol_display` used to mirror the `pp` branch's basis-toggled
gutter variable instead of the metric's own basis-invariant `value`).

This module does not trust that narrative -- it recomputes each promise
directly against `compare_data.metric_frame` on REAL data (a fixed
3-institution basket, per the dispatch: I154202486 / I4210107283 /
I34403800), for every (metric, level) combination `metric_frame` actually
offers, and states EXACTLY what each builder's own docstring promises before
asserting it:

  * fwci                         -> value/vol_display/denom_value/every OTHER
                                     column BYTE-IDENTICAL across basis (no
                                     `subs` reaches `_fwci_frame` at all).
  * pp (field)                   -> `value` basis-invariant (a population
                                     statistic); `vol_display`/`denom_value`
                                     DO move with basis, and full >= frac
                                     row-wise (fractional counting sums a
                                     PER-WORK SHARE <= 1, so a work's
                                     fractional contribution can never exceed
                                     its full-count contribution of exactly 1).
  * vol_top10 (field)             -> POST-D4-FIX: `value` AND `vol_display`
                                     both basis-invariant (CD5's own fix made
                                     the gutter mirror the bar directly).
  * share (field)                 -> the EXACT aggregation invariant the bug
                                     class is named for: per institution,
                                     SUM(vol_display over every field row) ==
                                     denom_value, at EITHER basis (this is
                                     what "value and gutter on the same basis"
                                     cashes out to arithmetically -- a value/
                                     gutter basis mix would break this sum).
  * share / si (erc, sdg)         -> BYTE-IDENTICAL across basis (fractional-
                                     only by design, per `_vol_display_col_for`'s
                                     own docstring).
  * si (field, subfield)          -> `vol_display` full >= frac row-wise (same
                                     direction as share, same shared column).
  * sdg_share (field)             -> `vol_display` IS `denom_value` (the code
                                     builds both from the same local variable
                                     `fm`) -- a mix would desynchronise them.
  * vol (erc, sdg)                -> `value` IS `vol_display` (mirrors the
                                     bar unconditionally, by construction) and
                                     full >= frac (mass_full >= mass_frac).
  * dynamics (field, subfield, sdg) -> `value` and `vol_display` (the
                                     "w1 -> w2/yr" gutter STRING) are
                                     numerically self-consistent: recomputing
                                     w2 from `value` and the row's own
                                     (full-precision) `denom_value` (== w1)
                                     reproduces the DISPLAYED w2 within the
                                     string's own 1-decimal rounding -- this
                                     is exactly the 2BR3 bug class the
                                     `_field_dynamics_frame` docstring narrates
                                     ("this WAS the historical 2BR3 CD4 bug").
                                     `vol_full_annual_mean` (the floor marker)
                                     is separately asserted basis-INVARIANT
                                     (it is deliberately always full-basis).

VACUITY: every assertion above is DEMONSTRATED, not just stated, to be able
to fail -- each test corrupts an in-memory COPY of a real, passing frame
(never a file on disk, never `compare_data.py`/`charts_compare.py` itself)
in the one way that would reproduce the bug class the assertion guards
against, and confirms the SAME assertion then raises. Every numeric fact
this module leans on (which columns move, which stay pinned, the exact
byte-identical claims) was independently probed against the live
`app/data/*.parquet` files before being written down here -- see the
worker's transcript for the probe scripts; nothing here is asserted on
narrative alone.

Run from cwd `app/`: python -m pytest tests/test_2c_basis_coherence.py -q
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd
import pytest

from lib import compare_data as CD
from lib.engine import build_substrates, load_context
from lib.app_config import CFG

DATA_DIR = __import__("pathlib").Path(__file__).resolve().parents[1] / "data"

# The dispatch's own 3-institution fixture basket.
IFREMER = "I154202486"
BASKET = [IFREMER, "I4210107283", "I34403800"]
FIELD_ID = 11  # Agricultural and Biological Sciences -- Ifremer's own golden field (2C_CD5.md)

_ARROW_PAT = re.compile(r"^(-?[\d.]+) " + re.escape(CD.DYNAMICS_ARROW) + r" (-?[\d.]+)/yr$")


@pytest.fixture(scope="module")
def ctx():
    return load_context(DATA_DIR)


@pytest.fixture(scope="module")
def subs_frac(ctx):
    return build_substrates(ctx, basis="frac")


@pytest.fixture(scope="module")
def subs_full(ctx):
    return build_substrates(ctx, basis="full")


def _frame(ctx, subs, level, metric, **kw) -> pd.DataFrame:
    d = CD.metric_frame(ctx, subs, BASKET, level, metric, **kw)
    return d.sort_values(["institution_id", "taxon_id"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# fwci -- fully basis-pinned, every column, every grain
# ---------------------------------------------------------------------------

def test_fwci_is_byte_identical_across_basis_at_every_grain(ctx, subs_frac, subs_full):
    for level in CD.LEVELS:
        kw = {"field_id": FIELD_ID} if level == "subfield" else {}
        frac = _frame(ctx, subs_frac, level, "fwci", **kw)
        full = _frame(ctx, subs_full, level, "fwci", **kw)
        assert len(frac) > 0, level
        pd.testing.assert_frame_equal(frac, full, check_dtype=False)

        # VACUITY: perturb one cell of the "full" copy the way a real basis
        # leak would (a number that quietly differs) -- the SAME assertion
        # must now raise, or this whole test is checking nothing.
        corrupt = full.copy()
        corrupt.loc[0, "value"] = corrupt.loc[0, "value"] + 0.001
        with pytest.raises(AssertionError):
            pd.testing.assert_frame_equal(frac, corrupt, check_dtype=False)


# ---------------------------------------------------------------------------
# pp -- value pinned, gutter follows basis (by contract, disclosed)
# ---------------------------------------------------------------------------

def test_pp_value_is_pinned_but_its_gutter_follows_basis(ctx, subs_frac, subs_full):
    frac = _frame(ctx, subs_frac, "field", "pp")
    full = _frame(ctx, subs_full, "field", "pp")
    assert len(frac) == len(full) > 0

    np.testing.assert_allclose(frac["value"].to_numpy(dtype="float64"),
                               full["value"].to_numpy(dtype="float64"))

    # the gutter DOES move -- if it did not, this metric would be silently
    # basis-pinned like fwci, contradicting its own denominator note ("on the
    # current basis"). full counting attributes >=1 whole work per matching
    # work, fractional counting a per-work SHARE <= 1 of the same works, so
    # full's gutter can never read BELOW fractional's for the same row.
    assert (full["vol_display"] != frac["vol_display"]).any()
    assert (full["vol_display"].to_numpy(dtype="float64")
           >= frac["vol_display"].to_numpy(dtype="float64") - 1e-9).all()
    assert (full["denom_value"].to_numpy(dtype="float64")
           >= frac["denom_value"].to_numpy(dtype="float64") - 1e-9).all()

    # VACUITY: two identical calls (frac vs frac) must NOT show the gutter
    # moving -- proves the "any()" check above is not trivially true.
    frac_again = _frame(ctx, subs_frac, "field", "pp")
    assert not (frac["vol_display"] != frac_again["vol_display"]).any()


def test_vol_top10_is_fully_basis_invariant_after_the_d4_fix(ctx, subs_frac, subs_full):
    """CD5's own D4 fix (progress/2C_CD5.md): `vol_top10`'s `vol_display`
    used to mirror the SIBLING `pp` branch's basis-toggled gutter -- a
    DIFFERENT count on a DIFFERENT basis than the bar it sat under, even
    though `value` here is always full-count-derived regardless of basis.
    Post-fix, `vol_display = value` on this branch: both are basis-invariant."""
    frac = _frame(ctx, subs_frac, "field", "vol_top10")
    full = _frame(ctx, subs_full, "field", "vol_top10")
    assert len(frac) == len(full) > 0
    np.testing.assert_allclose(frac["value"].to_numpy(dtype="float64"),
                               full["value"].to_numpy(dtype="float64"))
    np.testing.assert_allclose(frac["vol_display"].to_numpy(dtype="float64"),
                               full["vol_display"].to_numpy(dtype="float64"))
    # every row's own gutter mirrors its own bar (the fixed convention)
    np.testing.assert_allclose(frac["value"].to_numpy(dtype="float64"),
                               frac["vol_display"].to_numpy(dtype="float64"))

    # VACUITY: reproduce the PRE-FIX shape by hand (gutter = the OTHER
    # branch's basis-toggled `pp_denominator_frac`-style number) on an
    # in-memory copy, and confirm the SAME identity check then fails.
    pp_frac = _frame(ctx, subs_frac, "field", "pp")
    broken = frac.copy()
    broken["vol_display"] = pp_frac["denom_value"].to_numpy()
    with pytest.raises(AssertionError):
        np.testing.assert_allclose(broken["value"].to_numpy(dtype="float64"),
                                   broken["vol_display"].to_numpy(dtype="float64"))


# ---------------------------------------------------------------------------
# share -- the exact aggregation invariant (the "2130-vs-1699" bug class)
# ---------------------------------------------------------------------------

def test_share_field_gutter_sums_exactly_to_its_own_denominator(ctx, subs_frac, subs_full):
    """`_share_denom_value`'s own docstring: field-level `denom_value` is
    "own total mass across ALL fields" -- and `metric_frame(level="field")`
    always returns every field row, so SUM(vol_display) per institution must
    equal `denom_value` EXACTLY, at either basis. This is what "value and
    gutter never mix bases" cashes out to arithmetically: if `vol_display`
    ever read a DIFFERENT basis's column than the one `denom_value` was
    summed from, this identity breaks."""
    for subs in (subs_frac, subs_full):
        d = _frame(ctx, subs, "field", "share")
        g = d.groupby("institution_id").agg(
            sum_vol=("vol_display", "sum"), denom=("denom_value", "first"),
            n_denom=("denom_value", "nunique"))
        assert (g["n_denom"] == 1).all(), "denom_value must be a per-institution CONSTANT"
        np.testing.assert_allclose(g["sum_vol"].to_numpy(dtype="float64"),
                                   g["denom"].to_numpy(dtype="float64"), rtol=1e-9)

        # VACUITY: corrupt ONE row's vol_display (the exact shape of a basis
        # leak -- one row quietly reading the other basis's column) and show
        # the sum-identity now fails.
        corrupt = d.copy()
        corrupt.loc[0, "vol_display"] = corrupt.loc[0, "vol_display"] * 2.0
        g2 = corrupt.groupby("institution_id")["vol_display"].sum()
        denom0 = float(d.loc[0, "denom_value"])
        iid0 = d.loc[0, "institution_id"]
        assert abs(float(g2.loc[iid0]) - denom0) > 1e-6


# ---------------------------------------------------------------------------
# erc/sdg share + si -- fractional-only by design, basis-INVARIANT
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("level,metric", [("erc", "share"), ("sdg", "share"), ("erc", "si")])
def test_erc_and_sdg_share_and_si_are_basis_invariant_by_design(ctx, subs_frac, subs_full, level, metric):
    """`_vol_display_col_for`'s own docstring: erc/sdg stay on "mass"
    regardless of `basis` for the share/si family (no `mass_full` toggle is
    even consulted here) -- value, gutter and denominator must therefore be
    BYTE-IDENTICAL across the page's basis toggle."""
    frac = _frame(ctx, subs_frac, level, metric)
    full = _frame(ctx, subs_full, level, metric)
    assert len(frac) == len(full) > 0
    for col in ("value", "vol_display", "denom_value"):
        np.testing.assert_array_equal(frac[col].to_numpy(), full[col].to_numpy())

    # VACUITY: perturb one "full" value and show the equality check fails.
    corrupt = full["value"].to_numpy(dtype="float64").copy()
    corrupt[0] += 1.0
    with pytest.raises(AssertionError):
        np.testing.assert_array_equal(frac["value"].to_numpy(), corrupt)


def test_si_field_and_subfield_gutter_moves_with_basis_in_the_full_direction(ctx, subs_frac, subs_full):
    """SI at field/subfield DOES share the toggle-aware `vol_display` column
    the share family uses (`_vol_display_col_for`) -- unlike erc's `si`
    above, this is the OTHER half of the same contract: full counting's
    gutter never reads below fractional's for the same row."""
    for level, kw in (("field", {}), ("subfield", {"field_id": FIELD_ID})):
        frac = _frame(ctx, subs_frac, level, "si", **kw)
        full = _frame(ctx, subs_full, level, "si", **kw)
        assert len(frac) == len(full) > 0
        assert (full["vol_display"].to_numpy(dtype="float64")
               >= frac["vol_display"].to_numpy(dtype="float64") - 1e-9).all()
        assert (full["vol_display"] != frac["vol_display"]).any()

        # VACUITY: comparing frac to itself must show NO movement.
        frac_again = _frame(ctx, subs_frac, level, "si", **kw)
        assert not (frac["vol_display"] != frac_again["vol_display"]).any()


# ---------------------------------------------------------------------------
# sdg_share -- gutter IS its own denominator (same local variable, by code)
# ---------------------------------------------------------------------------

def test_sdg_share_field_gutter_equals_its_own_denominator(ctx, subs_frac, subs_full):
    for subs in (subs_frac, subs_full):
        d = _frame(ctx, subs, "field", "sdg_share")
        have_denom = d.dropna(subset=["denom_value"])
        assert len(have_denom) > 0
        np.testing.assert_array_equal(have_denom["vol_display"].to_numpy(dtype="float64"),
                                      have_denom["denom_value"].to_numpy(dtype="float64"))

        # VACUITY: desync one row and show the identity check then fails.
        corrupt = have_denom.copy()
        corrupt.iloc[0, corrupt.columns.get_loc("vol_display")] += 5.0
        with pytest.raises(AssertionError):
            np.testing.assert_array_equal(corrupt["vol_display"].to_numpy(dtype="float64"),
                                          corrupt["denom_value"].to_numpy(dtype="float64"))


# ---------------------------------------------------------------------------
# vol (erc, sdg) -- value IS vol_display, full >= frac
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("level", ["erc", "sdg"])
def test_vol_metric_bar_equals_its_own_gutter_and_full_never_reads_below_frac(ctx, subs_frac, subs_full, level):
    frac = _frame(ctx, subs_frac, level, "vol")
    full = _frame(ctx, subs_full, level, "vol")
    assert len(frac) == len(full) > 0
    for d in (frac, full):
        np.testing.assert_array_equal(d["value"].to_numpy(dtype="float64"),
                                      d["vol_display"].to_numpy(dtype="float64"))
    assert (full["value"].to_numpy(dtype="float64")
           >= frac["value"].to_numpy(dtype="float64") - 1e-9).all()

    # VACUITY: desync value from vol_display on a copy and show it is caught.
    corrupt = frac.copy()
    corrupt.loc[0, "vol_display"] = corrupt.loc[0, "vol_display"] + 1.0
    with pytest.raises(AssertionError):
        np.testing.assert_array_equal(corrupt["value"].to_numpy(dtype="float64"),
                                      corrupt["vol_display"].to_numpy(dtype="float64"))


# ---------------------------------------------------------------------------
# dynamics -- value and its "w1 -> w2/yr" gutter derive from the SAME numbers
# ---------------------------------------------------------------------------

def _dynamics_gutter_is_coherent(d: pd.DataFrame) -> list[int]:
    """Returns the positional indices of rows where `value` and the parsed
    `vol_display` STRING disagree by more than the string's own 1-decimal
    rounding tolerance -- empty means coherent. `denom_value` carries w1 at
    FULL precision (never rounded for display), so w2 is reconstructed as
    `value * w1 + w1` and compared to the string's own (rounded) w2."""
    bad = []
    for i, r in enumerate(d.itertuples(index=False)):
        m = _ARROW_PAT.match(str(r.vol_display))
        assert m, f"unparseable dynamics gutter: {r.vol_display!r}"
        w2_shown = float(m.group(2))
        w1 = r.denom_value
        val = r.value
        if pd.notna(w1) and w1 > 0:
            if pd.isna(val):
                bad.append(i)
                continue
            w2_expected = val * w1 + w1
            if abs(w2_expected - w2_shown) > 0.06:  # %.1f rounding, max 0.05
                bad.append(i)
        elif not pd.isna(val):
            bad.append(i)  # w1<=0 must yield an n/a value, never a number
    return bad


@pytest.mark.parametrize("level", ["field", "subfield", "sdg"])
def test_dynamics_value_and_gutter_are_numerically_self_consistent(ctx, subs_frac, subs_full, level):
    """This IS the 2BR3 CD4 bug class the frame builders' own docstrings
    narrate ("this WAS the historical 2BR3 CD4 bug ... value and gutter
    silently disagreeing in basis") -- verified here by RECOMPUTING one from
    the other's displayed numbers, not by trusting the docstring's claim
    that it was fixed."""
    kw = {"field_id": FIELD_ID} if level == "subfield" else {}
    for subs in (subs_frac, subs_full):
        d = _frame(ctx, subs, level, "dynamics", **kw)
        assert len(d) > 0
        bad = _dynamics_gutter_is_coherent(d)
        assert not bad, f"{level}: {len(bad)}/{len(d)} rows disagree: {d.iloc[bad][['institution_id','taxon_id','value','vol_display','denom_value']]}"

    # `vol_full_annual_mean` (the low-volume FLOOR marker) is deliberately
    # ALWAYS full-basis -- never the page's toggle.
    frac = _frame(ctx, subs_frac, level, "dynamics", **kw)
    full = _frame(ctx, subs_full, level, "dynamics", **kw)
    np.testing.assert_allclose(frac["vol_full_annual_mean"].to_numpy(dtype="float64"),
                               full["vol_full_annual_mean"].to_numpy(dtype="float64"),
                               equal_nan=True)

    # VACUITY (two shapes): (1) swap w1/w2 inside one row's gutter STRING --
    # the exact shape of "the two numbers no longer describe the same
    # arithmetic" -- and confirm the checker now flags it; (2) a value
    # deliberately computed from the WRONG (opposite-basis) window mean must
    # also be flagged.
    corrupt = frac.copy()
    m = _ARROW_PAT.match(str(corrupt.loc[0, "vol_display"]))
    swapped = f"{m.group(2)} {CD.DYNAMICS_ARROW} {m.group(1)}/yr"
    corrupt.loc[0, "vol_display"] = swapped
    if float(m.group(1)) != float(m.group(2)):  # a no-op swap proves nothing
        assert 0 in _dynamics_gutter_is_coherent(corrupt)

    corrupt2 = frac.copy()
    corrupt2.loc[0, "value"] = (corrupt2.loc[0, "value"] or 0.0) + 5.0
    assert 0 in _dynamics_gutter_is_coherent(corrupt2)


def test_dynamics_window_labels_match_the_config_core_window():
    """A basis-coherence sweep is only meaningful if it is reading the SAME
    5-year core window the rest of Compare states everywhere else -- guard
    the constant itself against config drift."""
    assert CD.CORE_WINDOW == tuple(CFG["window"])
    assert CD.N_CORE_YEARS == CD.CORE_WINDOW[1] - CD.CORE_WINDOW[0] + 1

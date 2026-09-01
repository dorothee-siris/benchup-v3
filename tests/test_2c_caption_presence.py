"""tests/test_2c_caption_presence.py -- Phase 2C, stream TEV, guards D5.

BUILD_PLAN_2C.md D5 ("Every ratio chart: one-line basis caption under the
title (corpus basis, floor, N taxa unscored); warnings RED, not bold")
plus the decisions log's two ruled sentences this test pins verbatim:

  * the D6 hatch floor, stated once app-wide: "a bar hatches when it rests
    on fewer than {floor} works over {y0} to {y1}" -- `copy.COMPARE[
    "TIP_LOW_VOLUME"]`, filled from `palette.RATIO_HATCH_FLOOR` (50).
  * the FWCI basis caption's bestfit-taxonomy pin: "Best-fit taxonomy,
    covered articles and reviews, ... fixed regardless of the counting-basis
    toggle" -- `copy.COMPARE["CAPTION_BASIS_FWCI"]` (WT_2C.md claim 2
    adjustment #1: field/subfield FWCI never moves with the tree toggle,
    and the caption must say so in words, not gray out silently).
  * the ERC coverage-gap sentence -- `copy.COMPARE["CAPTION_BASIS_FWCI_
    ERC_GAP"]` (the ~7.3% ERC-panel coverage gap named in words, decisions
    log 2026-09-01).

This is an IMPORT-LEVEL check (no Streamlit runtime needed): `copy.py` is a
pure dict-of-strings module, and the substrings a caption must carry are a
property of the STRING, independent of whether a page happens to render it
this run -- checking the string directly is a stronger, cheaper guarantee
than an AppTest screenshot for a text-presence fact.

Also pins the D5/D6 colour contract: `palette.WARNING_CAPTION_COLOR ==
palette.SHARED_FRONTIER` (CHROME_CONTRACT.md S7: the warning caption colour
is D7's frontier red BY REFERENCE, not a second, driftable hex).

VACUITY: each substring check is run once against the REAL rendered string
(passes) and once against a deliberately mutated in-memory COPY with the
ruled phrase removed (must fail) -- proving the assertion is reading the
actual sentence, not a name that happens to exist.

Run from cwd `app/`: python -m pytest tests/test_2c_caption_presence.py -q
"""
from __future__ import annotations

import pytest

from lib import compare_data as CD
from lib import copy
from lib import palette as P

Y0, Y1 = CD.CORE_WINDOW


def _assert_contains_and_is_sensitive(rendered: str, needle: str, mutated_missing: str) -> None:
    """The real string must contain `needle`; a copy with `needle` removed
    (`mutated_missing` is that copy, built by the caller) must not -- proves
    the check is not vacuously true for any string."""
    assert needle in rendered, f"expected {needle!r} in {rendered!r}"
    assert needle not in mutated_missing, "vacuity setup itself is broken"


# ---------------------------------------------------------------------------
# 1. the D6 hatch-floor sentence, app-wide, one template
# ---------------------------------------------------------------------------

def test_tip_low_volume_names_the_ruled_floor_of_fifty_works():
    template = copy.COMPARE["TIP_LOW_VOLUME"]
    rendered = template.format(floor=P.RATIO_HATCH_FLOOR, y0=Y0, y1=Y1)
    needle = f"fewer than {P.RATIO_HATCH_FLOOR} works"
    assert needle == "fewer than 50 works"  # the literal the dispatch names
    _assert_contains_and_is_sensitive(rendered, needle, rendered.replace(needle, ""))

    # VACUITY: the substring is a function of the REAL constant, not a
    # coincidence -- a different floor renders a DIFFERENT sentence, and the
    # "fewer than 50 works" check must then fail.
    wrong_floor_rendered = template.format(floor=30, y0=Y0, y1=Y1)
    assert needle not in wrong_floor_rendered
    assert "fewer than 30 works" in wrong_floor_rendered


# ---------------------------------------------------------------------------
# 2. the FWCI bestfit-taxonomy pin sentence
# ---------------------------------------------------------------------------

def test_caption_basis_fwci_names_the_bestfit_taxonomy_pin():
    rendered = copy.COMPARE["CAPTION_BASIS_FWCI"].format(y0=Y0, y1=Y1)
    needle = "Best-fit taxonomy"
    mutated = rendered.replace(needle, "")
    _assert_contains_and_is_sensitive(rendered, needle, mutated)
    # the FIXED-regardless-of-toggle half of the same sentence (D4 pin)
    assert "fixed regardless of the counting-basis toggle" in rendered

    # the UNSCORED variant carries the same pin PLUS a real computed count
    unscored = copy.COMPARE["CAPTION_BASIS_FWCI_UNSCORED"].format(
        y0=Y0, y1=Y1, n=3, grain="field")
    assert "Best-fit taxonomy" in unscored
    assert "3 fields" in unscored


# ---------------------------------------------------------------------------
# 3. the ERC coverage-gap sentence
# ---------------------------------------------------------------------------

def test_caption_basis_fwci_erc_gap_names_the_coverage_gap():
    rendered = copy.COMPARE["CAPTION_BASIS_FWCI_ERC_GAP"]
    for needle in ("Coverage", "incomplete"):
        mutated = rendered.replace(needle, "")
        _assert_contains_and_is_sensitive(rendered, needle, mutated)

    # it composes onto the base FWCI caption for the ERC grain (VC's own
    # composition rule, progress/2C_VC.md S2) without any hand-typed digit --
    # copy.py's own digit-ban would reject a literal "7.3%" here.
    base = copy.COMPARE["CAPTION_BASIS_FWCI"].format(y0=Y0, y1=Y1)
    composed = base + rendered
    assert "Coverage on this grain is incomplete" in composed
    assert not any(ch.isdigit() for ch in rendered), (
        "the ERC gap sentence must carry NO hand-typed digit -- the exact "
        "percentage lives in compare_data.FWCI_DENOM_NOTE['erc'] instead")


# ---------------------------------------------------------------------------
# 4. the warning-caption colour IS the frontier red, by reference
# ---------------------------------------------------------------------------

def test_warning_caption_color_is_the_shared_frontier_red():
    assert P.WARNING_CAPTION_COLOR == P.SHARED_FRONTIER
    assert P.WARNING_CAPTION_COLOR == "#821D13"

    # VACUITY: a DIFFERENT red must fail the same equality.
    assert P.WARNING_CAPTION_COLOR != "#7A1600"  # the pre-D7 red this replaced


# ---------------------------------------------------------------------------
# 5. VL/VF also introduced their own D4/D5 basis-disclosure keys this plan
# ---------------------------------------------------------------------------

def test_collab_core_ar_basis_chip_exists_and_names_full_counting():
    """VL's D4 chip (progress/2C_VL.md): every CORE-AR section on Collaborate
    (pulse, joint-topics table, untapped table) is pinned to ONE explicit
    basis, stated in words."""
    rendered = copy.COLLAB["BASIS_CAPTION_CORE_AR"].format(y0=Y0, y1=Y1)
    needle = "full counting"
    _assert_contains_and_is_sensitive(rendered, needle, rendered.replace(needle, ""))


def test_find_six_year_basis_disclosure_key_exists_and_names_the_whole_run():
    """VF's D5 disclosure (progress/2C_VF.md): the SDG/ERC profile panels
    read a WHOLE-RUN (six-year) window, different from the five-year core
    window the rest of Find states -- said in words wherever the ratio it
    qualifies is on screen."""
    template = copy.FIND["RATIO_WHOLE_RUN_BASIS"]
    rendered = template.format(window="2020-2025", corpus="2020-2024")
    needle = "not the {corpus} window used".format(corpus="2020-2024")
    _assert_contains_and_is_sensitive(rendered, needle, rendered.replace(needle, ""))
    assert "2020-2025" in rendered and "2020-2024" in rendered


def test_copy_digit_ban_still_holds_after_2c_additions():
    """A permanent guard alongside the locale ban (D9's sibling rule): none
    of the 2C caption keys this module just quoted verbatim may carry a
    hand-typed digit outside an approved `{placeholder}` -- re-run copy.py's
    OWN scanner here so a future edit to any COMPARE/COLLAB/FIND caption key
    cannot reintroduce a hand-typed number without this suite noticing."""
    violations = copy.scan_for_digit_violations()
    assert violations == [], violations

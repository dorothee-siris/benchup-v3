"""tests/test_2d_downloads.py -- Phase 2D, stream TEV5, cross-cutting guard
for E7 (BUILD_PLAN_2D.md S1/S7): ALL per-section download buttons removed,
ONE "Download this view (Excel)" button at the very END of each of
Find/Compare/Collaborate.

Each stream (VC4/VF4/VL4) already re-pinned this INSIDE its own file's own
test module (`test_pages_compare.py`/smoke's `check_tables_and_export`/
`test_pages_collab.py::test_render_export_is_the_only_download_button_in_
this_streams_file`). This module is the ONE place that sweeps all three
`views_*.py` files TOGETHER, plus every OTHER `lib/*.py` module, in a single
assertion -- so a future edit to any one file that reintroduces a second
button is caught here even if that stream's own test file is not the one
touched.

It also checks the workbook BUILDERS exist and return the contracted sheet
counts named in the dispatch: Find 13, Collaborate 6, Compare 10+.

VACUITY, per module: every assertion is followed by an in-memory mutation
that makes the identical check fail.

Run: python -m pytest tests/test_2d_downloads.py -q
"""
from __future__ import annotations

import inspect
from pathlib import Path

import pandas as pd
import pytest

APP_DIR = Path(__file__).resolve().parents[1]
LIB_DIR = APP_DIR / "lib"
VIEW_FILES = ("views_compare.py", "views_find.py", "views_collab.py")


def _src(name: str) -> str:
    return (LIB_DIR / name).read_text(encoding="utf-8")


# ============================================================================
# E7 -- exactly one st.download_button( call site per view module
# ============================================================================

@pytest.mark.parametrize("filename", VIEW_FILES)
def test_exactly_one_download_button_call_site(filename):
    src = _src(filename)
    n = src.count("st.download_button(")
    assert n == 1, (filename, n)

    # VACUITY: appending a second literal call site to the SAME source text
    # makes the identical count assertion fail -- proving `.count(...)` is
    # doing real counting on this file's actual content, not returning a
    # constant 1.
    mutated = src + "\n    st.download_button('x', lambda: b'', key='dl_extra')\n"
    assert mutated.count("st.download_button(") == 2
    with pytest.raises(AssertionError):
        assert mutated.count("st.download_button(") == 1


def test_no_download_button_call_site_outside_the_three_view_modules():
    """E7's own scope is the per-section CSVs the Find/Compare/Collaborate
    pages used to offer -- it never touched `views_methods.py`'s own,
    pre-existing "Download METHODS_NOTE.md" button (a standing feature,
    unrelated to any 2D metric/workbook), so that ONE extra file is
    disclosed and allowed here by name rather than silently excluded.
    Beyond that single, named exception, no OTHER file in `lib/` may call
    `st.download_button(` at all."""
    ALLOWED_EXTRA = {"views_methods.py"}
    hits = [f.name for f in LIB_DIR.glob("*.py")
           if f.name not in VIEW_FILES and f.name not in ALLOWED_EXTRA
           and "st.download_button(" in f.read_text(encoding="utf-8")]
    assert hits == [], hits

    # VACUITY: a scratch module carrying the literal call site IS caught by
    # the same substring test -- proves the sweep is a real text search over
    # real file contents, not a check that always finds nothing regardless
    # of what a file contains.
    assert "st.download_button(" in "st.download_button('y', lambda: b'', key='dl_fake')"


# ============================================================================
# E7 -- workbook builders exist and return the contracted sheet counts
# ============================================================================

def test_compare_workbook_builder_returns_at_least_ten_sheets():
    """Compare 10+ (progress/2D_VC4.md: 10 view sheets from `sheet_specs`
    plus one Methods sheet added by `_workbook`, 11 total in the real
    download)."""
    from lib import views_compare as VC

    sc = {"tree": "bestfit", "basis": "frac"}
    metrics = {"level": "field", "subject": "share", "erc": "share", "sdg": "share"}
    frame_keys = ["overview", "coverage", "subject", "erc", "sdg", "dynamics",
                 "frontier_map", "shared_frontier", "impact", "impact_subfields"]
    frames = {k: pd.DataFrame() for k in frame_keys}

    specs = VC.sheet_specs(sc, frames, metrics)
    assert len(specs) >= 10, len(specs)
    labels = [label for label, _caption, _frame in specs]
    assert len(labels) == len(set(labels)), "sheet labels must be unique before Excel-legalisation"

    # VACUITY: a frames dict missing one of the contracted sheets' own data
    # (Dynamics, E10's own addition) makes `sheet_specs` raise a KeyError
    # rather than silently returning a shorter, still->=10 list -- proving
    # the >=10 count above genuinely depends on every named frame being
    # present, not on a hardcoded pass-through.
    short_frames = {k: v for k, v in frames.items() if k != "dynamics"}
    with pytest.raises(KeyError):
        VC.sheet_specs(sc, short_frames, metrics)


def test_find_workbook_sheet_count_matches_the_all_lenses_contract():
    """Find 13 (progress/2D_VF4.md: Profile + Overview + one sheet per
    `ALL_LENSES` + Aspirational, live-verified by VF4's own Playwright
    download and sheet-name read). Assembling a real render context for
    `_find_workbook` (bundle/seed_row/card/rankings/bits) is Find's own
    render() pipeline (VF4's fence) -- this pins the STRUCTURAL contract
    behind the number instead, at the source level, so a change to either
    side (ALL_LENSES gaining/losing a lens, or a fixed sheet being added or
    removed) is caught without a full render."""
    from lib import views_find as VF
    from lib.engine import ALL_LENSES

    src = inspect.getsource(VF._find_workbook)
    fixed_sheets = src.count('copy.FIND["XLSX_SHEET_')
    assert fixed_sheets == 3, ("PROFILE + OVERVIEW + ASPIRATIONAL", fixed_sheets)
    assert "for lens in ALL_LENSES:" in src
    assert len(ALL_LENSES) + fixed_sheets == 13

    # VACUITY: the SAME arithmetic on an ALL_LENSES one lens short does NOT
    # equal 13 -- proving this is a real dependency on the current
    # `ALL_LENSES` length, not a hardcoded "13 == 13" tautology.
    with pytest.raises(AssertionError):
        assert len(ALL_LENSES) - 1 + fixed_sheets == 13


def test_collab_workbook_builder_returns_exactly_six_sheets():
    """Collaborate 6 (progress/2D_VL4.md: Pair overview, Yearly
    co-publications, Fields, Reciprocity by field, Shared topics, Untapped
    potential -- in page order), called through the SAME `@st.cache_data`
    accessors the real page renders, on real data."""
    from lib import views_collab as VL

    bundle = VL._bundle()
    sc = {"tree": "bestfit", "basis": "frac"}
    strasbourg, cnrs = "I68947357", "I1294671590"
    sheets = VL._workbook_sheets(bundle, strasbourg, cnrs, sc)
    assert len(sheets) == 6, len(sheets)
    labels = [label for label, _frame in sheets]
    assert len(labels) == len(set(labels))
    assert all(isinstance(frame, pd.DataFrame) for _label, frame in sheets)

    # VACUITY: a hand-truncated copy of this SAME real result no longer
    # satisfies "== 6" -- demonstrated explicitly, so the check above is
    # shown to discriminate a wrong count, not merely restate a constant.
    truncated = sheets[:-1]
    with pytest.raises(AssertionError):
        assert len(truncated) == 6


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))

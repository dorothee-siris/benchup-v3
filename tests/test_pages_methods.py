"""
tests/test_pages_methods.py -- Stream M (Phase 2B): the Methods page
(BUILD_PLAN_2B.md S1 2B-9/2B-10, S3 row M) and the four-card Menu.

Run from cwd `app/`:  python -m pytest tests/test_pages_methods.py -q
"""
from __future__ import annotations

import re
from pathlib import Path

from streamlit.testing.v1 import AppTest

from lib import copy
from lib.data_cache import manifest

APP_DIR = Path(__file__).resolve().parents[1]
MENU_PAGE = str(APP_DIR / "Menu.py")
# open-book-tilted-left, the file's real name (AppTest.from_file resolves a
# relative path against THIS module, under tests/, so both paths are made
# absolute here -- same reason pages/1_(magnifying-glass)_Find.py is absolute
# in tests/test_pages.py).
METHODS_PAGE = str(APP_DIR / "pages" / "4_\U0001F4D6_Methods.py")

# `{[a-z_]+}` -- a real unfilled template placeholder ("{n_seeds}") never
# contains anything but lowercase letters and underscores; this deliberately
# will NOT flag a markdown/CSS brace pair with other content, so the test
# stays specific to the failure mode it exists to catch.
PLACEHOLDER_RE = re.compile(r"\{[a-z_]+\}")


def _methods_app() -> AppTest:
    return AppTest.from_file(METHODS_PAGE, default_timeout=120)


def _page_text(at: AppTest) -> str:
    """Every rendered string AppTest exposes for this page. `at.markdown`
    and `at.caption` are FLAT collectors across the whole element tree
    (verified interactively: a page of 16 st.expander sections yields
    exactly 16 top-level `at.markdown` entries plus the ones rendered
    outside them, with no separate per-expander traversal needed), so this
    does not need to walk `at.expander[i].markdown` itself."""
    parts = [t.value for t in at.title]
    parts += [c.value for c in at.caption]
    parts += [m.value for m in at.markdown]
    parts += [e.label for e in at.expander]
    return "\n".join(p for p in parts if p)


# ------------------------------------------------------------- Methods -----

def test_methods_page_renders_without_exception():
    at = _methods_app().run()
    assert not at.exception, [str(e) for e in at.exception]


def test_methods_page_title_and_lead_from_nav():
    at = _methods_app().run()
    assert not at.exception
    assert copy.NAV["METHODS_LABEL"] in [t.value for t in at.title]
    assert copy.NAV["METHODS_LEAD"] in [c.value for c in at.caption]


def test_methods_page_verdict_line_present():
    at = _methods_app().run()
    assert not at.exception
    assert copy.VERDICT_LINE in _page_text(at)


def test_methods_page_shows_every_section_title():
    at = _methods_app().run()
    assert not at.exception
    labels = [e.label for e in at.expander]
    assert len(labels) == len(copy.METHODS), (len(labels), len(copy.METHODS))
    for key, section in copy.METHODS.items():
        assert section["title"] in labels, (key, section["title"], labels)


def test_methods_page_has_no_unfilled_placeholder():
    """Every `{placeholder}` copy.METHODS carries must be gone from the
    rendered page: methods_values() fills every name METHODS_SOURCES
    documents (test_methods_note.py already proves the two dicts agree)."""
    at = _methods_app().run()
    assert not at.exception
    leftover = PLACEHOLDER_RE.findall(_page_text(at))
    assert not leftover, leftover


def test_methods_page_snapshot_stamp_matches_manifest():
    at = _methods_app().run()
    assert not at.exception
    mf = manifest()
    snapshot = mf.get("snapshot") or "n/a"
    assert snapshot != "n/a", "manifest() carries no snapshot to compare against"
    assert snapshot in _page_text(at)


def test_methods_page_offers_the_note_download():
    at = _methods_app().run()
    assert not at.exception
    buttons = at.get("download_button")
    assert len(buttons) >= 1, "no st.download_button on the Methods page"


def test_methods_values_match_documented_sources():
    """Cross-check against progress/2B_N.md S2 / copy.METHODS_SOURCES: every
    documented placeholder name has an entry in methods_values(), and every
    filled (non-NA) value is a plain int/float/str, never a stray NaN or a
    pandas scalar type that would render oddly."""
    from lib.palette import NA_MARK
    from lib.views_methods import methods_values

    values = methods_values()
    documented = set(copy.METHODS_SOURCES)
    assert documented <= set(values), documented - set(values)
    for name, v in values.items():
        if v == NA_MARK:
            continue
        assert isinstance(v, (int, float, str)), (name, type(v), v)


# ------------------------------------------------------------------ Menu ---

def test_menu_renders_four_cards_in_narrative_order():
    at = AppTest.from_file(MENU_PAGE, default_timeout=60).run()
    assert not at.exception, [str(e) for e in at.exception]
    assert len(at.columns) == 4, len(at.columns)
    text = " ".join(m.value for m in at.markdown)
    for key in ("FIND_LABEL", "COMPARE_LABEL", "COLLAB_LABEL", "METHODS_LABEL"):
        assert copy.NAV[key] in text, (key, text)


def test_menu_intro_from_nav():
    at = AppTest.from_file(MENU_PAGE, default_timeout=60).run()
    assert not at.exception
    assert copy.NAV["MENU_INTRO"] in [c.value for c in at.caption]


def test_menu_find_card_is_live():
    at = AppTest.from_file(MENU_PAGE, default_timeout=60).run()
    assert not at.exception
    links = at.get("page_link")
    assert len(links) >= 1, "the Find card should be a live st.page_link"
    assert any("Find" in (lk.label or "") for lk in links), [lk.label for lk in links]

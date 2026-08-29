"""
tests/test_pages.py -- Stream G: Streamlit AppTest page-render tests for
Menu.py and pages/1_(magnifying-glass)_Find.py (BUILD_PLAN_2A.md Stream G
build step 1).

Streamlit's own `st.cache_resource` keeps lib/views_find.py's engine bundle
warm across AppTest instances within one pytest PROCESS (measured on this
build: the first Find-page AppTest.run() pays the ~9 s cold load; every
later AppTest instance in the same process -- a fresh seed, a fresh page --
runs in ~0.1-0.4 s), so each test below builds its OWN AppTest rather than
mutating one shared instance: session_state on a shared instance would leak
selections between tests, and the shared cost is the process-wide Streamlit
cache, not a pytest fixture.

`AppTest.tabs` returns one entry per rendered `st.tabs(...)` label with a
`.label` attribute -- confirmed against this Streamlit build (1.61.1)
interactively before writing this file; that is the "verify the AppTest
attribute for tabs" step BUILD_PLAN_2A.md Stream G asks for.

Run from cwd `app/`:  python -m pytest tests/test_pages.py -q
"""
from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from lib import copy

APP_DIR = Path(__file__).resolve().parents[1]
# AppTest.from_file resolves a RELATIVE path against the file that CALLS it
# (this test module, under tests/), not the pytest run cwd -- so both page
# paths are made absolute here.
MENU_PAGE = str(APP_DIR / "Menu.py")
FIND_PAGE = str(APP_DIR / "pages" / "1_\U0001F50E_Find.py")  # magnifying-glass-tilted-left, the file's real name

GDANSK = "I40413290"           # University of Gdansk -- panel_v2 D19 seed, all default lenses defined
EMPTY_SIZE_RANGE = (100_000, 100_001)  # verified empty for Gdansk/L1 (see test below), inside the
                                        # slider's real bounds [200, 238_978] on this deployed index


def _find_app(seed_id: str = GDANSK, **extra_state) -> AppTest:
    at = AppTest.from_file(FIND_PAGE, default_timeout=120)
    at.session_state["seed_id"] = seed_id
    at.session_state["basket"] = []
    for k, v in extra_state.items():
        at.session_state[k] = v
    return at


def _template_literal_segment(template: str) -> str:
    """The template's fixed part for a substring check against rendered
    text: the first NON-EMPTY literal segment once every `{placeholder}` is
    cut out. A plain "text before the first {" reading is empty for a
    template that OPENS on a placeholder (copy.UNDEFINED_LENS_TEMPLATE =
    "{lens} is undefined for this seed: {reason}." starts with "{lens}"),
    which would make that check vacuously true -- this generalises it to
    the first segment that actually carries fixed text, covering both
    template shapes the same way."""
    import re

    segments = [s for s in re.split(r"\{[^{}]*\}", template) if s]
    assert segments, f"template has no fixed text at all: {template!r}"
    return segments[0]


# ---------------------------------------------------------------- Menu -----

def test_menu_renders_without_exception():
    at = AppTest.from_file(MENU_PAGE, default_timeout=60).run()
    assert not at.exception, [str(e) for e in at.exception]


def test_menu_has_at_least_three_nav_cards():
    at = AppTest.from_file(MENU_PAGE, default_timeout=60).run()
    assert not at.exception
    # Menu.py lays out st.columns(len(DIMENSIONS)) with one bordered
    # container per dimension (Find/Compare/Collaborate) -- st.columns is
    # the cheapest locale-independent proxy AppTest exposes for "N nav
    # cards rendered" (this AppTest build has no dedicated container
    # element type to inspect directly, confirmed interactively: at.get
    # ("container") returns 0 even though 3 bordered st.container()s render).
    assert len(at.columns) >= 3
    all_markdown = " ".join(m.value for m in at.markdown)
    for word in ("Find", "Compare", "Collaborate"):
        assert word in all_markdown, all_markdown


def test_menu_snapshot_caption_has_real_label_and_no_na():
    at = AppTest.from_file(MENU_PAGE, default_timeout=60).run()
    from lib.app_config import CFG
    from lib.data_cache import manifest

    mf = manifest()
    snapshot_label = mf.get("snapshot") or CFG.get("snapshot", "n/a")
    captions = [c.value for c in at.caption]
    snap_caption = next((c for c in captions if c.startswith("Snapshot:")), None)
    assert snap_caption is not None, captions
    assert snapshot_label in snap_caption
    assert "n/a" not in snap_caption, snap_caption


# ---------------------------------------------------------------- Find -----

def test_find_default_seed_renders_ten_tabs_no_c1_l7():
    at = _find_app().run()
    assert not at.exception, [str(e) for e in at.exception]
    labels = [t.label for t in at.tabs]
    assert len(at.tabs) >= 10, labels
    assert "Overview" in labels
    assert "Aspirational" in labels
    assert "C1" not in labels, "C1 must be OFF by default (BUILD_PLAN_2A.md L1)"
    assert "L7" not in labels, "L7 must be OFF by default (BUILD_PLAN_2A.md L1)"


def test_find_c1_and_l7_toggles_add_two_tabs():
    at = _find_app().run()
    assert not at.exception
    # keys read from lib/views_find.py::_sidebar_scenario (sb.checkbox(..., key="c1_on"/"l7_on")),
    # never guessed from label text (state-driven, locale-independent selector).
    at.session_state["c1_on"] = True
    at.session_state["l7_on"] = True
    at.run()
    assert not at.exception, [str(e) for e in at.exception]
    labels = [t.label for t in at.tabs]
    assert len(at.tabs) == 12, labels
    assert "C1" in labels and "L7" in labels, labels


def test_undefined_lens_shows_template(undefined_l2f_seed):
    at = _find_app(seed_id=undefined_l2f_seed).run()
    assert not at.exception, [str(e) for e in at.exception]
    labels = [t.label for t in at.tabs]
    assert "L2f" in labels, labels
    tab = at.tabs[labels.index("L2f")]
    text = " ".join(x.value for x in (*tab.info, *tab.caption, *tab.markdown))
    fixed = _template_literal_segment(copy.UNDEFINED_LENS_TEMPLATE)
    assert fixed in text, text


def test_type_filter_empties_a_lens_list():
    """DEVIATION from the brief's exact wording ("set a type filter to a
    type absent from the seed's L1 top-50"): measured directly (see
    progress/2A_G.md) -- for I40413290/L1, EVERY institution type has at
    least 76 candidates somewhere in the full positive-score ranking (not
    just the top 50), so no single-type filter empties the list. A narrow
    total-works size_range does reliably empty it (apply_filters(...,
    size_range=(100_000, 100_001)) -> 0 kept, verified against this
    deployed index whose max total_full_2020_2024 is 238,978) and exercises
    the same "post-filter empties the ranking" code path the brief is
    really after (lib/filters.py's own predicates are independent per
    BUILD_PLAN_2A.md L6)."""
    at = _find_app().run()
    assert not at.exception
    at.session_state["f_size"] = EMPTY_SIZE_RANGE
    at.run()
    assert not at.exception, [str(e) for e in at.exception]
    labels = [t.label for t in at.tabs]
    tab = at.tabs[labels.index("L1")]
    text = " ".join(x.value for x in tab.info)
    fixed = _template_literal_segment(copy.EMPTY_STATE_TEMPLATE)
    assert fixed in text, text


# --------------------------------------------------------- fixtures --------

@pytest.fixture(scope="module")
def engine_ctx():
    """Module-scope: cold load (~7 s) paid ONCE for this file's undefined-
    seed discovery, independent of the process-wide Streamlit cache the
    AppTest-based tests above ride on."""
    from lib.engine import build_substrates, load_context

    ctx = load_context(APP_DIR / "data")
    subs = build_substrates(ctx)  # default scenario: bestfit / frac
    return ctx, subs


@pytest.fixture(scope="module")
def undefined_l2f_seed(engine_ctx) -> str:
    """A seed whose L2f ranking is undefined, found via the engine over the
    20 smallest-total_full_2020_2024 institutions (BUILD_PLAN_2A.md Stream G
    build step 1c) -- I24568809 on this deployed snapshot, reason:
    "seed's excess-SI vector is empty under candidate (f), papers>=30
    (n_eligible_cells=0)"."""
    from lib.engine import rank_all

    ctx, subs = engine_ctx
    idx = ctx["index_df"].nsmallest(20, "total_full_2020_2024")
    for iid in idx["institution_id"]:
        if rank_all(ctx, subs, iid, ["L2f"])["L2f"]["undefined"]:
            return iid
    pytest.skip("no undefined-L2f seed found among the 20 smallest institutions on this snapshot")

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


# ---------------------------------------------------------- 2BR / stream MU --

def test_lens_concordance_covers_all_ten_lenses_both_ways():
    """copy._lens_concordance_table() must name every display code AND every
    internal id exactly once each, built from FC's own LENS_DISPLAY_CODE/
    LENS_DISPLAY_NAMES rather than a second hand-typed list that could drift."""
    table = copy._lens_concordance_table()
    for internal, display in copy.LENS_DISPLAY_CODE.items():
        assert f"**{display}**" in table, (internal, display, table)
        assert f"({internal})" in table, (internal, table)


def test_collab_topic_floor_and_cap_are_measured_off_the_shipped_tables():
    """2B-R2-12/P6: collab_pair_topics.parquet ships floor>=5 co-publications
    + top-100 topics per pair (regenerated from the 2B-R floor>=3/top-20
    build, progress/2BR2_P6.md). These are MEASURED here off the actual
    shipped parquet files (lib.views_methods._collab_pair_topic_facts), not a
    config literal, so a future artefact refresh that recalibrates the
    floor/cap fails this test loudly rather than drifting silently from the
    copy."""
    from lib.palette import NA_MARK
    from lib.views_methods import _collab_pair_topic_facts

    facts = _collab_pair_topic_facts()
    assert facts["collab_topic_floor"] != NA_MARK, "collab_pairs/collab_pair_topics not found under app/data"
    assert facts["collab_topic_floor"] == 5, facts
    assert facts["collab_topic_cap"] == 100, facts


def test_dynamics_windows_come_from_the_contract_verbatim():
    """2B-R-6/A7: the two Dynamics windows the Methods page states must be the
    EXACT strings PC's own window_conventions block in data_contract.yaml
    carries, never retyped, so the two can never silently diverge."""
    import yaml

    from lib.views_methods import CONTRACT_PATH, _window_conventions

    contract = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
    wc = contract["window_conventions"]
    got = _window_conventions()
    assert got["dynamics_window_1"] == wc["dynamics_window_1"]
    assert got["dynamics_window_2"] == wc["dynamics_window_2"]


def test_n_gated_is_zero_every_previously_gated_case_is_now_applied():
    """2BR MU: docs/data_contract.yaml's own type_overrides.n_ids grain note
    states "0 gated rows remain from any round". Both GATE .md files (R1's
    4 ids, R2's 7) are historical records only, predating the rulings that
    resolved them (contract `stale_reference_note`) -- verified live here by
    checking type_overrides.csv itself carries all 11 of those ids, rather
    than trusting either stale file's own "none applied" line."""
    import pandas as pd

    from lib.app_config import CFG

    df = pd.read_csv(APP_DIR / "data" / "overrides" / "type_overrides.csv")
    ids = set(df["institution_id"])
    r1_gate_ids = {"I4210119716", "I4210138806", "I205703379", "I4210153845"}  # NLDA, MAL, IMT, FUNIBER
    r2_gate_ids = {"I4210155236", "I148297040", "I87653560",                   # CNR, TNO, VTT
                   "I4210127591", "I2801533059", "I4210129183", "I4210115305"}  # DZHK, DZNE, DZL, DZIF
    missing = (r1_gate_ids | r2_gate_ids) - ids
    assert not missing, f"previously-gated id(s) not found in type_overrides.csv: {missing}"
    assert CFG["methods_facts"]["n_gated"] == 0, CFG["methods_facts"]["n_gated"]


def test_impact_ci_coverage_matches_the_pipeline_bootstrap_alpha():
    """2B-R-12: the impact-interval coverage stated in copy.IMPACT_CI_CAPTION
    (and reused by config.yaml methods_facts.impact_ci_coverage_pct) must
    match the ACTUAL pipeline constant it is read off --
    pipeline/agg/impact.py's poisson_bootstrap_ci_vectorized default alpha,
    which pipeline/ (outside the app/ repo) never overrides at any call site.
    This is the closest a test inside app/ can get to re-deriving
    METHODS_FAISCEAU.md's own bootstrap-CI point from the real implementation
    rather than trusting a typed-in number."""
    import re as _re

    from lib.app_config import CFG

    pipeline_dir = APP_DIR.parent / "pipeline"
    impact_py = (pipeline_dir / "agg" / "impact.py").read_text(encoding="utf-8")
    m = _re.search(
        r"def poisson_bootstrap_ci_vectorized\(.*?alpha:\s*float\s*=\s*([\d.]+)",
        impact_py, _re.S,
    )
    assert m, "could not find poisson_bootstrap_ci_vectorized's alpha default in pipeline/agg/impact.py"
    alpha = float(m.group(1))
    derived_coverage = round(100 * (1 - alpha))

    configured = CFG.get("methods_facts", {}).get("impact_ci_coverage_pct")
    assert configured == derived_coverage, (configured, derived_coverage)

    # No known caller overrides alpha -- a future override would silently
    # change the true coverage without this test noticing the number itself,
    # so also check the call sites directly for an explicit alpha= override.
    for rel in ("16_crosses.py", "09b_aggregate_eu.py", "agg/eu_enriched.py", "agg/impact_cells.py"):
        text = (pipeline_dir / rel).read_text(encoding="utf-8")
        assert "alpha=" not in text.replace(" ", ""), (
            f"{rel} passes an explicit alpha=, coverage may no longer be {derived_coverage}%")

    assert "bootstrap" in copy.IMPACT_CI_CAPTION.lower()
    rendered = copy.IMPACT_CI_CAPTION.format(ci_coverage=configured, n_bootstrap=1000)
    assert f"{configured}%" in rendered, rendered


def test_below_floor_collaborate_notice_is_additive_and_digit_free():
    """The below-floor honest notice LP reuses next wave (BUILD_PLAN_2BR.md S3
    LP row) must exist now, carry both instance placeholders, and obey the
    same digit-ban RULE as everything else in copy.py (checked generically by
    test_narrative.py's own scan; pinned again here narrowly so this key
    specifically cannot regress unnoticed before LP's wave reads it)."""
    notice = copy.COLLAB["TOPIC_BELOW_FLOOR_NOTICE"]
    assert "{n_copubs}" in notice and "{floor}" in notice
    import re as _re

    cleaned = _re.sub(r"\{[^{}]*\}", "", notice)
    assert not _re.search(r"\d", cleaned), notice

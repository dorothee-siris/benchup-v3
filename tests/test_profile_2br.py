"""
tests/test_profile_2br.py -- Sprint 2 Phase 2B-R, stream FA: the Find page's
profile + search rework (BUILD_PLAN_2BR.md S0 A12/A14/A15, S1 decisions
2B-R-1 / 2B-R-2 / 2B-R-7 / 2B-R-12).

Five claims, one section each:

  1. SEARCH ON VALIDATE (2B-R-12 / A12). Typing a query renders the results
     list and NOTHING below it: no profile header, no benchmark header, no KPI
     card. Picking a match renders the profile. Both halves are asserted --
     a test that only checked "the profile appears after a pick" would pass
     against the old auto-load behaviour, which is the exact defect.

  2. FOUR CARDS (2B-R-2). Card count, one subline each (the index baseline),
     the companion figures (fractional count on the publications card, the
     bootstrap interval on the PP card), and a `?` tooltip on every card
     carrying the methodology that used to print as a subline.

  3. THE IDENTITY FACTS (2B-R-7). `intl_share` / `company_share` land on
     `index.parquet` LATER this phase (stream P2). BOTH branches are covered
     here on the pure helper -- absent column -> n/a, present column -> the
     formatted percent -- so the day the columns ship, this file already
     asserts the behaviour rather than needing an edit.

  4. NO SNAPSHOT STRING (2B-R-12 / A14). The verbose stamp is gone from the
     rendered Find page and from `lib/copy.py`'s own template; the CSV export
     keeps its factual provenance column, renamed `data_snapshot`.

  5. THE BONUS YEAR (2B-R-2). Starred on the year axis, its footnote in the
     section tooltip, and the standalone banner gone from the page.

Run from cwd `app/`:  python -m pytest tests/test_profile_2br.py -q
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from lib import copy, exports, tiles, views_find
from lib.app_config import CFG
from lib.palette import NA_MARK

APP_DIR = Path(__file__).resolve().parents[1]
FIND_PAGE = str(APP_DIR / "pages" / "1_\U0001F50E_Find.py")

STRASBOURG = "I68947357"      # the gate-2A drive seed, kept as this file's seed
STRASBOURG_QUERY = "Strasbourg"


def _fresh_find_app() -> AppTest:
    """A Find page with NO `seed_id` in session state -- the state a first
    visitor is in. Every other page test in this suite seeds `seed_id`
    directly (which is what makes them fast and independent); this file is the
    one that must not, because the claim under test is exactly what happens
    before a seed exists."""
    at = AppTest.from_file(FIND_PAGE, default_timeout=120)
    at.session_state["basket"] = []
    return at


def _page_strings(at: AppTest) -> str:
    return " ".join(x.value for x in (*at.caption, *at.markdown, *at.info, *at.header,
                                      *at.subheader, *at.title))


# ------------------------------------------- 1. search on validate (A12) ----

def test_a_query_alone_renders_the_results_list_and_nothing_below_it():
    """The load-bearing half: after typing, the reader sees matches and NO
    profile. `index=None` on the results selectbox is what makes `seed_id`
    stay unwritten, and `render()`'s existing early return does the rest."""
    at = _fresh_find_app()
    at.session_state["seed_query"] = STRASBOURG_QUERY
    at.run()
    assert not at.exception, [str(e) for e in at.exception]

    keys = [s.key for s in at.selectbox]
    assert "seed_pick" in keys, keys
    pick = next(s for s in at.selectbox if s.key == "seed_pick")
    assert pick.value is None, pick.value
    assert len(pick.options) >= 1, pick.options

    assert "seed_id" not in at.session_state
    headers = [h.value for h in at.header]
    assert copy.FIND["PROFILE_HEADER"] not in headers, headers
    assert copy.FIND["BENCHMARK_HEADER"] not in headers, headers
    assert not [m.value for m in at.markdown if tiles.TILE_CLASS in m.value]
    assert copy.FIND["SEED_PROMPT"] in [i.value for i in at.info]


def test_picking_a_match_renders_the_profile():
    """The other half, on the SAME app instance shape: select an option in the
    results list and the profile appears. Selecting by the widget (not by
    writing `seed_id`) is the point -- it exercises the one code path a reader
    has."""
    at = _fresh_find_app()
    at.session_state["seed_query"] = STRASBOURG_QUERY
    at.run()
    pick = next(s for s in at.selectbox if s.key == "seed_pick")
    # `.options` carries the FORMATTED labels (`format_func` is applied), so
    # the pick is made by POSITION -- which is also what a reader does. The
    # top hit for this query is the university itself (the search's own
    # "ties by total_full desc" rule), asserted rather than assumed.
    pick.select_index(0).run()
    assert not at.exception, [str(e) for e in at.exception]

    assert at.session_state["seed_id"] == STRASBOURG
    headers = [h.value for h in at.header]
    assert copy.FIND["PROFILE_HEADER"] in headers, headers
    assert copy.FIND["BENCHMARK_HEADER"] in headers, headers
    assert len([m.value for m in at.markdown if tiles.TILE_CLASS in m.value]) == \
        views_find.N_CARDS


def test_the_results_list_opens_on_its_placeholder_not_on_a_match():
    """A pure-copy guard on the same decision: the placeholder key exists and
    carries no institution name of its own."""
    placeholder = copy.FIND["SEED_PICK_PLACEHOLDER"]
    assert placeholder
    assert STRASBOURG_QUERY.lower() not in placeholder.lower()


# --------------------------------------------------- 2. four cards (2B-R-2) --

@pytest.fixture(scope="module")
def profile_app() -> AppTest:
    at = AppTest.from_file(FIND_PAGE, default_timeout=120)
    at.session_state["seed_id"] = STRASBOURG
    at.session_state["basket"] = []
    at.run()
    assert not at.exception, [str(e) for e in at.exception]
    return at


def _cards(at: AppTest) -> list[str]:
    return [m.value for m in at.markdown if tiles.TILE_CLASS in m.value]


def test_the_profile_shows_four_cards_each_with_one_baseline_subline(profile_app):
    cards = _cards(profile_app)
    assert len(cards) == views_find.N_CARDS == 4, len(cards)
    baseline = copy.FIND["TILE_BASELINE_SUB"].split("{")[0]
    for html in cards:
        assert html.count(tiles.SUBLINE_CLASS) == 1, html
        assert baseline in html, html


def test_the_publications_card_carries_both_counting_bases(profile_app):
    """2B-R-2 (1): full AND fractional on ONE card -- the companion figure has
    its own class hook, so this is a count, not a string match on a number."""
    cards = _cards(profile_app)
    pubs = [h for h in cards if copy.FIND["KPI_PUBS_LABEL"] in h]
    assert len(pubs) == 1, len(pubs)
    assert tiles.VALUE2_CLASS in pubs[0], pubs[0]
    assert copy.FIND["KPI_PUBS_FRAC_LABEL"] in pubs[0], pubs[0]


def test_the_pp_card_carries_its_interval(profile_app):
    """2B-R-2 (4) + the standing rule that the point estimate is never shown
    alone: the CI is the PP card's companion figure."""
    cards = _cards(profile_app)
    pp = [h for h in cards if copy.FIND["KPI_PP_LABEL"] in h]
    assert len(pp) == 1, len(pp)
    assert tiles.VALUE2_CLASS in pp[0], pp[0]
    assert copy.FIND["KPI_PP_CI_LABEL"] in pp[0], pp[0]
    assert views_find.DASH in pp[0], pp[0]


def test_every_card_hides_its_methodology_behind_a_tooltip(profile_app):
    """2B-R-2: ALL methodology in a `?` tooltip. AppTest exposes a markdown
    element's `help`, so this reads the real rendered attribute rather than
    the copy dict."""
    helped = [m.help for m in profile_app.markdown
              if tiles.TILE_CLASS in m.value]
    assert len(helped) == views_find.N_CARDS, len(helped)
    for tip in helped:
        assert tip, helped
    for key in ("KPI_PUBS_HELP", "KPI_SDG_HELP", "KPI_FRONTIER_HELP", "KPI_PP_HELP"):
        fixed = copy.FIND[key].split("{")[0]
        assert any(fixed in (tip or "") for tip in helped), key


def test_the_four_dropped_measures_are_off_the_card_grid(profile_app):
    """2B-R-2 drops concentration, breadth, the second size tile as a tile of
    its own, and the bonus-year tile. Asserted absent, not merely unasserted."""
    cards = " ".join(_cards(profile_app))
    for label in (copy.FIND["TILE_HHI"], copy.FIND["TILE_BREADTH"],
                  copy.FIND["TILE_BONUS_YEAR"].format(year=CFG["bonus_year"])):
        assert label not in cards, label


def test_the_card_spec_is_the_ruled_order_of_four(profile_app):
    """A unit-level pin on the spec itself, so a reorder is caught even if the
    rendered HTML still holds four cards."""
    from lib.engine import seed_card

    bundle = views_find._bundle()
    subs = views_find._subs(CFG["scenario"]["tree_default"], CFG["scenario"]["basis_default"])
    card = seed_card(bundle["ctx"], STRASBOURG, subs, bundle["catchall"])
    row = bundle["ctx"]["index_by_id"].loc[STRASBOURG]
    specs = views_find._card_specs(card, row)
    assert [s[0] for s in specs] == ["total_full_2020_2024", "sdg_tagged_share",
                                     "frontier_top25_share", "pp_top10_frac"]
    assert specs[0][5] is not None and specs[3][5] is not None      # companion figures
    assert specs[1][5] is None and specs[2][5] is None


def test_the_wordcloud_caption_states_the_two_bases_render_differently(profile_app):
    """2B-R-1 / A15: the cap alone is not the fix -- a reader also has to be
    told the two bases are not on one scale."""
    tip = copy.FIND["WORDCLOUD_HELP"].lower()
    assert "fractional" in tip and "scale" in tip, tip
    helps = [c.help for c in profile_app.caption if c.help]
    assert any(copy.FIND["WORDCLOUD_HELP"] == h for h in helps), helps


def test_the_wordcloud_caps_its_largest_word():
    """2B-R-1 / A15: the font cap is a module constant, applied by default."""
    from lib import wordcloud_png

    assert wordcloud_png.MAX_FONT_SIZE == 84
    import inspect
    sig = inspect.signature(wordcloud_png.render_wordcloud_png)
    assert sig.parameters["max_font_size"].default == wordcloud_png.MAX_FONT_SIZE


# ------------------------------------------- 3. identity facts (2B-R-7) -----

def test_identity_fact_reads_n_a_while_the_column_is_absent():
    """The branch that is live TODAY: stream P2 has not landed the columns, so
    the honest render is n/a -- never 0, which would claim the institution
    co-publishes with nobody abroad."""
    row = pd.Series({"display_name": "Somewhere"})
    assert views_find._identity_fact(row, views_find.INTL_COLUMN) == NA_MARK
    assert views_find._identity_fact(row, views_find.COMPANY_COLUMN) == NA_MARK


def test_identity_fact_formats_the_share_once_the_column_exists():
    """The branch that goes live when P2 ships: a real share renders as a
    percent, and a NULL value in a PRESENT column still reads n/a."""
    row = pd.Series({views_find.INTL_COLUMN: 0.4237,
                     views_find.COMPANY_COLUMN: float("nan")})
    assert views_find._identity_fact(row, views_find.INTL_COLUMN) == "42.4%"
    assert views_find._identity_fact(row, views_find.COMPANY_COLUMN) == NA_MARK


def test_both_identity_facts_render_in_the_profile(profile_app):
    text = _page_strings(profile_app)
    assert copy.FIND["IDENTITY_INTL_LABEL"] in text, text[:400]
    assert copy.FIND["IDENTITY_COMPANY_LABEL"] in text, text[:400]


# ------------------------------------- 4. the snapshot string (2B-R-12) -----

def test_the_snapshot_stamp_is_gone_from_the_find_page(profile_app):
    """The rendered page carries neither the artefact label nor the verbose
    "(generated ...)" wrapper -- and DOES carry what replaced them."""
    from lib.data_cache import manifest

    text = _page_strings(profile_app)
    mf = manifest()
    label = mf.get("snapshot") or CFG.get("snapshot")
    assert label, "no snapshot label available to assert the absence of"
    assert label not in text, text[:400]
    assert "generated" not in text.lower(), text[:400]
    date = exports.data_date_label(
        mf.get("source_manifest_generated_at") or mf.get("generated_at")
        or mf.get("deployed_at"), NA_MARK)
    assert date != NA_MARK, "the deployed manifest carries no parsable stamp"
    assert date in text, text[:400]


def test_the_copy_template_itself_no_longer_types_the_stamp():
    """The three pages FA does not own (Compare, Collaborate, Methods) read the
    SAME key, so killing the string in the template is what removes it from all
    of them without editing another stream's file. Pinned here so a later
    stream cannot quietly put it back."""
    template = copy.FIND["SNAPSHOT_CAPTION"]
    assert "Snapshot" not in template, template
    assert "generated" not in template, template
    assert "{generated_at}" not in template, template
    # ...and the key still tolerates every keyword its four callers pass.
    rendered = template.format(snapshot="x", generated_at="y", n_institutions="1,234", sep="·")
    assert "1,234" in rendered


def test_the_export_keeps_a_plain_provenance_column():
    """A14: the CSV keeps FACTUAL provenance (one column, one label) -- the
    stamp was never in the file and the column is now self-describing."""
    rows = [{"rank": 1, "institution_id": "I1", "display_name": "A", "country_code": "FR",
             "type": "education", "total_full_2020_2024": 10.0,
             "total_frac_2020_2024": 5.0, "lens_score": 0.5}]
    csv = exports.ranking_csv(rows, seed_id="I0", lens="L1", tree="bestfit", basis="frac",
                              snapshot="august_2026", filters_label="none").decode("utf-8")
    header = csv.splitlines()[0].split(",")
    assert "data_snapshot" in header, header
    assert "snapshot" not in header, header


def test_the_data_date_label_parses_the_manifest_stamp_and_degrades_honestly():
    assert exports.data_date_label("2026-08-27T13:41:28.350794+00:00", NA_MARK) == \
        "August 27, 2026"
    assert exports.data_date_label(None, NA_MARK) == NA_MARK
    assert exports.data_date_label("", NA_MARK) == NA_MARK
    assert exports.data_date_label("not-a-date", NA_MARK) == NA_MARK


# ------------------------------------------- 5. the bonus year (2B-R-2) -----

def test_the_bonus_year_is_starred_on_the_axis():
    year = int(CFG["bonus_year"])
    assert views_find._year_label(year) == f"{year}{views_find.BONUS_STAR}"
    assert views_find._year_label(year - 1) == str(year - 1)


def test_the_bonus_year_banner_is_gone_and_its_footnote_is_in_the_tooltip(profile_app):
    text = _page_strings(profile_app)
    banner = copy.FIND["BONUS_YEAR_CAPTION"].format(year=CFG["bonus_year"])
    assert banner not in text, text[:400]
    expected = copy.FIND["BREAKDOWN_SECTION_HELP"].format(
        year=CFG["bonus_year"], star=views_find.BONUS_STAR)
    helps = [m.help for m in profile_app.markdown if m.help]
    assert expected in helps, helps


def test_the_breakdown_control_label_is_collapsed_but_still_set(profile_app):
    """2B-R-2 removes the "Break down by" LABEL from the page, not the label
    argument -- a screen reader still gets one."""
    ctl = next(s for s in profile_app.segmented_control if s.key == "breakdown_dim")
    assert ctl.label == copy.FIND["BREAKDOWN_CONTROL_LABEL"]
    # AppTest hands back the protobuf enum, whose str() is "value: COLLAPSED".
    assert "COLLAPSED" in str(ctl.label_visibility), ctl.label_visibility
    assert copy.FIND["BREAKDOWN_SECTION_TITLE"] in _page_strings(profile_app)

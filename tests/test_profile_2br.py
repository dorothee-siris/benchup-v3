"""
tests/test_profile_2br.py -- Sprint 2 Phase 2B-R, stream FA: the Find page's
profile + search rework (BUILD_PLAN_2BR.md S0 A12/A14/A15, S1 decisions
2B-R-1 / 2B-R-2 / 2B-R-7 / 2B-R-12).

RE-CUT for Phase 2B-R2, stream FA3 (BUILD_PLAN_2BR2.md S1 decisions 2B-R2-1a /
2B-R2-6 / 2B-R2-7 / 2B-R2-8): SIX cards instead of four, name-first anatomy, the
publications card's fractional note in place of an index line, the PP card
without its interval line, the identity line's inline type correction and the
ten profiles that used to crash on it.

Six claims, one section each:

  1. SEARCH ON VALIDATE (2B-R-12 / A12). Typing a query renders the results
     list and NOTHING below it: no profile header, no benchmark header, no KPI
     card. Picking a match renders the profile. Both halves are asserted --
     a test that only checked "the profile appears after a pick" would pass
     against the old auto-load behaviour, which is the exact defect.

  2. SIX CARDS (2B-R2-6). Card count and order, ONE small line each (the index
     baseline for five of them, the fractional-counting note for publications),
     the name-first anatomy, the PP card WITHOUT its interval line, and a `?`
     tooltip on every card carrying the methodology that used to print under it.

  3. THE TWO CO-PUBLICATION MEASURES (2B-R-7, promoted to cards by 2B-R2-6).
     Both branches are covered on the pure helper -- absent column -> None ->
     n/a, present column -> the value -- so an index rebuild that drops one
     renders honestly rather than as a zero.

  4. NO SNAPSHOT STRING (2B-R-12 / A14). The verbose stamp is gone from the
     rendered Find page and from `lib/copy.py`'s own template; the CSV export
     keeps its factual provenance column, renamed `data_snapshot`.

  5. THE BONUS YEAR (2B-R-2). Starred on the year axis, its footnote in the
     section tooltip, and the standalone banner gone from the page.

  6. THE CRASH (2B-R2-1a). All TEN institutions that are both an umbrella and
     type-corrected render their profile end to end with no exception, and the
     correction is on the page in its INLINE form. This is the regression test
     for the gate-2B-R crash: every one of these ten raised an AssertionError
     out of `badges.badges_for` before the invariant was retired.

Run from cwd `app/`:  python -m pytest tests/test_profile_2br.py -q
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from lib import badges, copy, exports, tiles, views_find
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


# ------------------------------- 1. basket-only seed pick (2BR3 SEL) --------
# Re-cut for BUILD_PLAN_2BR3.md SEL: the free-text seed search this section
# used to drive is GONE from this page (moved to the shared sidebar,
# lib/selection.render_sidebar); the claims are the SAME shape -- nothing
# renders before a subject is chosen, a choice is never made silently -- read
# off the basket instead of off a live query.

OTHER_SEED = "I265217849"  # IFPEN, a second real id distinct from STRASBOURG


def test_an_empty_basket_renders_the_prompt_and_nothing_below_it():
    """The load-bearing half: an empty basket shows the prompt and NO
    profile -- `_seed_pick`'s own early return is what keeps `seed_id`
    unwritten, and `render()`'s early return does the rest."""
    at = _fresh_find_app()
    at.run()
    assert not at.exception, [str(e) for e in at.exception]

    assert "seed_id" not in at.session_state
    headers = [h.value for h in at.header]
    assert copy.FIND["PROFILE_HEADER"] not in headers, headers
    assert copy.FIND["BENCHMARK_HEADER"] not in headers, headers
    assert not [m.value for m in at.markdown if tiles.TILE_CLASS in m.value]
    assert copy.FIND["SEED_PROMPT"] in [i.value for i in at.info]


def test_a_basket_of_one_auto_selects_and_renders_the_profile():
    """2BR3 SEL, plan §3: exactly one basket item needs no click at all --
    the profile renders straight away, and no picker widget is even shown
    (nothing to choose between)."""
    at = _fresh_find_app()
    at.session_state["basket"] = [STRASBOURG]
    at.run()
    assert not at.exception, [str(e) for e in at.exception]

    assert at.session_state["seed_id"] == STRASBOURG
    headers = [h.value for h in at.header]
    assert copy.FIND["PROFILE_HEADER"] in headers, headers
    assert copy.FIND["BENCHMARK_HEADER"] in headers, headers
    assert len([m.value for m in at.markdown if tiles.TILE_CLASS in m.value]) == \
        views_find.N_CARDS
    assert "seed_pick" not in [s.key for s in at.selectbox]


def test_a_basket_of_several_needs_an_explicit_pick():
    """The other half: more than one basket item shows the dropdown OVER THE
    BASKET (2B-R-12's 'never load a match silently' guarantee, now read off
    the basket), and picking by the widget renders that institution's
    profile."""
    at = _fresh_find_app()
    at.session_state["basket"] = [OTHER_SEED, STRASBOURG]
    at.run()
    assert not at.exception, [str(e) for e in at.exception]

    assert "seed_id" not in at.session_state
    assert copy.FIND["PROFILE_HEADER"] not in [h.value for h in at.header]
    pick = next(s for s in at.selectbox if s.key == "seed_pick")
    assert pick.value is None, pick.value
    # AppTest exposes the FORMATTED labels (format_func applied), not the raw
    # ids -- length is what a pure-copy check can assert without depending on
    # display-name text; the pick itself is made by POSITION below, which is
    # also what a reader does, and basket order ([OTHER_SEED, STRASBOURG]) is
    # exactly `state.items()`'s own insertion order.
    assert len(pick.options) == 2, pick.options

    pick.select_index(1).run()  # basket[1] == STRASBOURG
    assert not at.exception, [str(e) for e in at.exception]

    assert at.session_state["seed_id"] == STRASBOURG
    headers = [h.value for h in at.header]
    assert copy.FIND["PROFILE_HEADER"] in headers, headers
    assert copy.FIND["BENCHMARK_HEADER"] in headers, headers
    assert len([m.value for m in at.markdown if tiles.TILE_CLASS in m.value]) == \
        views_find.N_CARDS


def test_the_seed_pick_placeholder_names_no_institution():
    """A pure-copy guard: the placeholder carries no institution name of its
    own -- it is shown alongside every basket option, so it must never look
    like one of them."""
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


def _seed_card_and_row(iid: str):
    """(seed card, index row) for one institution, through the page's OWN
    cached bundle -- the same two objects `_card_specs` and `_profile_identity`
    are handed at render time."""
    from lib.engine import seed_card

    bundle = views_find._bundle()
    subs = views_find._subs(CFG["scenario"]["tree_default"], CFG["scenario"]["basis_default"])
    card = seed_card(bundle["ctx"], iid, subs, bundle["catchall"])
    return card, bundle["ctx"]["index_by_id"].loc[iid]


def test_the_profile_shows_six_cards_each_with_exactly_one_small_line(profile_app):
    """2B-R2-6: six cards, one small line each. FIVE carry the index baseline;
    the publications card carries the fractional note instead, which is why the
    baseline is counted rather than asserted on every card."""
    cards = _cards(profile_app)
    assert len(cards) == views_find.N_CARDS == 6, len(cards)
    baseline = copy.FIND["TILE_BASELINE_SUB"].split("{")[0]
    for html in cards:
        assert html.count(tiles.SUBLINE_CLASS) == 1, html
    assert sum(baseline in html for html in cards) == views_find.N_CARDS - 1, cards


def test_a_card_puts_its_name_above_its_value():
    """2B-R2-6's anatomy claim, asserted on POSITION in the markup rather than
    on a font size: the name is the first thing in the card, the value follows,
    the small line closes it. Pure unit on the builder -- no app needed."""
    html = tiles.tile_html("Metric name", "1,234", subline="index median 900")
    assert html.index("Metric name") < html.index("1,234") < html.index("index median 900")
    assert tiles.LABEL_PX < tiles.VALUE_PX and tiles.META_PX < tiles.LABEL_PX


def test_a_card_cannot_carry_two_small_lines_or_none():
    """The rule the builder enforces, so no future caller can rebuild the grey
    stack 2B-R2-6 removed."""
    with pytest.raises(ValueError):
        tiles.tile_html("N", "1", subline="a", note_template="({n})", note_value="2")
    with pytest.raises(ValueError):
        tiles.tile_html("N", "1")


def test_the_publications_card_carries_the_fractional_count_as_its_small_line(profile_app):
    """2B-R2-6 (1): full AND fractional on ONE card -- the note has its own
    class hook inside the small line, so this is a count, not a string match on
    a number -- and NO index line on that card."""
    cards = _cards(profile_app)
    pubs = [h for h in cards if copy.FIND["KPI_PUBS_LABEL"] in h]
    assert len(pubs) == 1, len(pubs)
    assert tiles.VALUE2_CLASS in pubs[0], pubs[0]
    note = copy.FIND["KPI_PUBS_FRAC_NOTE"].split(tiles.NOTE_SLOT)[-1]
    assert note in pubs[0], pubs[0]
    assert copy.FIND["TILE_BASELINE_SUB"].split("{")[0] not in pubs[0], pubs[0]


def test_the_pp_card_no_longer_prints_its_interval(profile_app):
    """2B-R2-6: the interval line is off the card surface; the caveat it
    carried is the last sentence of the card's own tooltip instead."""
    cards = _cards(profile_app)
    pp = [h for h in cards if copy.FIND["KPI_PP_LABEL"] in h]
    assert len(pp) == 1, len(pp)
    assert tiles.VALUE2_CLASS not in pp[0], pp[0]
    assert copy.FIND["KPI_PP_CI_LABEL"] not in pp[0], pp[0]
    helped = [m.help for m in profile_app.markdown
              if tiles.TILE_CLASS in m.value and copy.FIND["KPI_PP_LABEL"] in m.value]
    assert helped and copy.FIND["KPI_PP_HELP_R2"] in helped[0], helped


def test_the_two_copublication_measures_are_cards_now(profile_app):
    """2B-R2-6: promoted out of the identity column onto the grid, each with
    its own index baseline line like every other measured card."""
    cards = _cards(profile_app)
    for key in ("KPI_INTL_LABEL", "KPI_COMPANY_LABEL"):
        hits = [h for h in cards if copy.FIND[key] in h]
        assert len(hits) == 1, (key, len(hits))
        assert copy.FIND["TILE_BASELINE_SUB"].split("{")[0] in hits[0], hits[0]


def test_every_card_hides_its_methodology_behind_a_tooltip(profile_app):
    """2B-R-2: ALL methodology in a `?` tooltip. AppTest exposes a markdown
    element's `help`, so this reads the real rendered attribute rather than
    the copy dict."""
    helped = [m.help for m in profile_app.markdown
              if tiles.TILE_CLASS in m.value]
    assert len(helped) == views_find.N_CARDS, len(helped)
    for tip in helped:
        assert tip, helped
    for key in ("PUBLICATIONS_TOOLTIP", "KPI_PUBS_HELP_FULL", "KPI_SDG_HELP",
                "KPI_FRONTIER_HELP", "KPI_PP_HELP_R2", "KPI_INTL_HELP",
                "KPI_COMPANY_HELP"):
        fixed = copy.FIND[key].split("{")[0]
        assert any(fixed in (tip or "") for tip in helped), key


def test_the_four_dropped_measures_are_off_the_card_grid(profile_app):
    """2B-R-2 drops concentration, breadth, the second size tile as a tile of
    its own, and the bonus-year tile. Asserted absent, not merely unasserted."""
    cards = " ".join(_cards(profile_app))
    for label in (copy.FIND["TILE_HHI"], copy.FIND["TILE_BREADTH"],
                  copy.FIND["TILE_BONUS_YEAR"].format(year=CFG["bonus_year"])):
        assert label not in cards, label


def test_the_card_spec_is_the_ruled_order_of_six(profile_app):
    """A unit-level pin on the spec itself, so a reorder is caught even if the
    rendered HTML still holds six cards."""
    specs = views_find._card_specs(*_seed_card_and_row(STRASBOURG))
    assert [s[0] for s in specs] == [
        views_find.KPI_PUBS_KEY, "sdg_tagged_share", "frontier_top25_share",
        "pp_top10_frac", views_find.INTL_COLUMN, views_find.COMPANY_COLUMN]
    assert all(len(s) == 5 for s in specs), specs      # no companion-figure slots left


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

def test_the_copublication_value_is_none_when_the_column_is_absent():
    """An index rebuilt without the column must render n/a -- never 0, which
    would claim the institution co-publishes with nobody abroad. `None` is what
    `_pct` turns into NA_MARK and what `baselines.percentile` refuses to
    position, so both halves of the card degrade together."""
    row = pd.Series({"display_name": "Somewhere"})
    assert views_find._identity_value(row, views_find.INTL_COLUMN) is None
    assert views_find._pct(views_find._identity_value(row, views_find.INTL_COLUMN)) == NA_MARK


def test_the_copublication_value_reads_through_once_the_column_exists():
    """A real share formats as a percent; a NULL value in a PRESENT column
    still reads n/a."""
    row = pd.Series({views_find.INTL_COLUMN: 0.4237,
                     views_find.COMPANY_COLUMN: float("nan")})
    assert views_find._pct(views_find._identity_value(row, views_find.INTL_COLUMN)) == "42.4%"
    assert views_find._pct(views_find._identity_value(row, views_find.COMPANY_COLUMN)) == NA_MARK


def test_both_copublication_measures_render_on_the_card_grid(profile_app):
    text = _page_strings(profile_app)
    assert copy.FIND["KPI_INTL_LABEL"] in text, text[:400]
    assert copy.FIND["KPI_COMPANY_LABEL"] in text, text[:400]


def test_the_index_has_a_population_for_both_measures():
    """The promotion is only honest if the index really has a median to
    position an institution against: an empty population would render every
    card's baseline as n/a and say nothing."""
    bl = views_find._bundle()["baselines"]
    for column in (views_find.INTL_COLUMN, views_find.COMPANY_COLUMN):
        assert bl[column]["n"] > 0, column
        assert 0.0 <= bl[column]["median"] <= 1.0, (column, bl[column]["median"])


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


# ------------------------------- 6. the ten crashing profiles (2B-R2-1a) -----

# Every institution in the index that is BOTH an umbrella (volume against its
# country-type median) and type-corrected. Under the 2A L7 invariant each of
# these raised an AssertionError out of `badges.badges_for`, which took the
# whole profile down -- the gate hit it on Ifremer. The list is pinned here as
# DATA rather than recomputed, so a future index that quietly stops correcting
# one of them fails this file instead of silently shrinking the regression.
BOTH_BADGE_IDS = {
    "I154202486": "Ifremer",
    "I148297040": "TNO",
    "I4210155236": "CNR",
    "I173888879": "SINTEF",
    "I2898391981": "DLR",
    "I110594554": "Ikerbasque",
    "I4210127591": "DZHK",
    "I2801533059": "DZNE",
    "I4210129183": "DZL",
    "I4210115305": "DZIF",
}


def test_the_ten_both_badge_institutions_are_exactly_this_set():
    """Non-vacuity guard for the render test below: if the population changed,
    the ten renders would still pass while testing something else."""
    bundle = views_find._bundle()
    idx = bundle["index_df"]
    flags = bundle["flags"]
    found = {r.institution_id for r in idx.itertuples(index=False)
             if bool(flags.get(r.institution_id, False))
             and str(r.type) != str(r.type_openalex)}
    assert found == set(BOTH_BADGE_IDS), sorted(found ^ set(BOTH_BADGE_IDS))


@pytest.mark.parametrize("iid", sorted(BOTH_BADGE_IDS), ids=sorted(BOTH_BADGE_IDS.values()))
def test_every_formerly_crashing_profile_renders(iid):
    """THE regression test: the whole Find page, seeded on each of the ten, with
    no exception -- and the type correction present in its INLINE form (the
    literal head of the identity template, plus the original type it names),
    with no badge carrying it."""
    at = AppTest.from_file(FIND_PAGE, default_timeout=120)
    at.session_state["seed_id"] = iid
    at.session_state["basket"] = []
    at.run()
    assert not at.exception, [str(e) for e in at.exception]
    assert len(_cards(at)) == views_find.N_CARDS

    card, row = _seed_card_and_row(iid)
    was = badges.corrected_from(row)
    assert was, iid
    kind, kind_help = views_find._identity_kind(card, row)
    assert kind == copy.FIND["IDENTITY_TYPE_CORRECTED"].format(
        kind=str(card["type"]), star=f":red[{views_find.BONUS_STAR}]", was=was)
    assert kind_help == copy.FIND["IDENTITY_TYPE_HELP"]
    captions = [c.value for c in at.caption]
    assert any(kind in c for c in captions), captions[:6]
    # ...and the umbrella badge is still there, on its own.
    assert copy.UMBRELLA_BADGE_LABEL in _page_strings(at)
    assert not any(was in b for b in
                   badges.badges_for(card, views_find._bundle()["flags"], {})), iid

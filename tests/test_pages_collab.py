"""
tests/test_pages_collab.py -- Stream LP: AppTest page-render tests for
pages/3_(handshake)_Collaborate.py and the render helpers in
lib/views_collab.py, rewritten for the FOUR-SECTION page of BUILD_PLAN_2BR.md
decision 2B-R-10 (relationship pulse / joint corpus / untapped potential /
link-outs).

TWO PAIRS ARE RENDERED (N = 2), and the second one is the point:

  * Universite de Strasbourg x CNRS -- the manager-verified anchor. 12,694
    joint works; CNRS is Strasbourg's FIRST partner and Strasbourg is CNRS's
    SIXTEENTH, so this pair is also the RANK-DIRECTION pin: a page that renders
    `rank_in_a` as A's own rank instead of B's would still look plausible and
    would be wrong, and only an asymmetric pair catches it.
  * Universite de Strasbourg x Bavarian Academy of Sciences and Humanities --
    a REAL sub-floor pair (2 joint works, under `collab_data.PAIR_TOPICS_
    FLOOR`), which must render the honest notice with its own numbers, drop the
    three joint-corpus tables rather than show empty ones, and keep the pulse
    and every link-out.

WHAT IS PINNED HERE (rather than in tests/test_collab_data.py, which owns the
frames themselves): that the PAGE renders those frames' numbers, in the right
direction, with their denominators named -- and the digit-ban over this
stream's files. The live URL path (`?pair=A,B`), the rendered legend strip, the
starred partial year on the chart axis and the three link hrefs are probed in
ops/_probe_collab.py, which drives a real browser.

Same process economics as tests/test_pages.py: `st.cache_resource` keeps the
engine context and the (tree, basis) substrates warm across AppTest instances
inside one pytest PROCESS. Each test still builds its OWN AppTest -- a shared
instance would leak the pair selection between tests.

Run from cwd `app/`:  python -m pytest tests/test_pages_collab.py -q
"""
from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest
from streamlit.testing.v1 import AppTest

from lib import collab_data, copy, links, selection, views_collab
from lib.compare_data import DYNAMICS_W1, DYNAMICS_W2
from lib.data_cache import DATA_DIR
from lib.engine import build_substrates, load_context, rank_all

APP_DIR = Path(__file__).resolve().parents[1]
COLLAB_PAGE = str(APP_DIR / "pages" / "3_\U0001F91D_Collaborate.py")  # handshake, the file's real name

STRASBOURG = "I68947357"        # the R1 reference seed
CNRS = "I1294671590"            # Strasbourg's own first partner
BAVARIAN = "I109144446"         # 2 joint works with Strasbourg: under the topic floor
GDANSK = "I40413290"            # panel_v2 D19 seed, kept for the selection tests
PAIR = [STRASBOURG, CNRS]
SUB_FLOOR_PAIR = [STRASBOURG, BAVARIAN]

TREE = "bestfit"           # config.yaml's own defaults, i.e. what the page opens on
BASIS = "frac"

N_TABLES = 8               # joint fields/subfields/topics + untapped + siblings + 2 gaps + overlap
N_TABLES_BELOW_FLOOR = 5   # the three joint-corpus tables are the only ones that go


def _app(basket=None, **extra_state) -> AppTest:
    at = AppTest.from_file(COLLAB_PAGE, default_timeout=300)
    at.session_state["basket"] = list(PAIR if basket is None else basket)
    for k, v in extra_state.items():
        at.session_state[k] = v
    return at


@pytest.fixture(scope="module")
def engine():
    """The raw engine, loaded ONCE for the whole module. `load_context` /
    `build_substrates` are the same calls lib/views_find.py's cache_resource
    wrappers make, so this fixture is cheap in practice: whichever runs first
    fills the process cache the other reads."""
    ctx = load_context(str(DATA_DIR))
    return ctx, build_substrates(ctx, TREE, BASIS)


def _text(at) -> str:
    """Everything the page wrote as markdown or caption, emphasis stripped, so
    a `**bold**` template compares against what a reader sees."""
    parts = [m.value for m in at.markdown] + [c.value for c in at.caption]
    parts += [i.value for i in at.info] + [s.value for s in at.subheader]
    return " ".join(parts).replace("**", "")


def _first_literal(template: str) -> str:
    """The template's first non-empty fixed segment, for a substring check
    against rendered text (tests/test_pages.py's own idiom)."""
    import re

    segments = [s for s in re.split(r"\{[^{}]*\}", template) if s.strip()]
    assert segments, f"template has no fixed text: {template!r}"
    return segments[0].strip()


# ------------------------------------------------------------- render ------

def test_page_renders_without_exception():
    at = _app().run()
    assert not at.exception, [str(e) for e in at.exception]


def test_the_four_sections_render_in_the_order_2br10_names():
    at = _app().run()
    assert not at.exception, [str(e) for e in at.exception]
    heads = [s.value for s in at.subheader]
    order = [copy.COLLAB["PULSE_HEADER"], copy.COLLAB["JOINT_HEADER"],
             copy.COLLAB["UNTAPPED_HEADER"], copy.COLLAB["LINKS_HEADER"]]
    positions = [heads.index(h) for h in order]
    assert positions == sorted(positions), heads
    assert len(at.dataframe) == N_TABLES, f"{len(at.dataframe)} tables, expected {N_TABLES}"


# ------------------------------------------- 1. the relationship pulse -----

def test_pulse_numbers_are_collab_datas_own(engine):
    """Total, both shares and both denominators, read off the page against a
    fresh `collab_data.pulse`."""
    ctx, _subs = engine
    p = collab_data.pulse(ctx, STRASBOURG, CNRS)
    at = _app().run()
    values = [m.value for m in at.metric]
    assert views_collab._count(p["copubs_total"]) in values
    assert views_collab._pct(p["share_of_a"]) in values
    assert views_collab._pct(p["share_of_b"]) in values
    names = {i: str(ctx["index_by_id"].loc[i, "display_name"]) for i in PAIR}
    assert copy.COLLAB["PULSE_SHARE_DENOM"].format(
        window=views_collab._window(collab_data.PULSE_YEARS),
        name_a=names[STRASBOURG], name_b=names[CNRS],
        vol_a=views_collab._count(p["denominator_a"]),
        vol_b=views_collab._count(p["denominator_b"])) in _text(at)


def test_rank_direction_is_rendered_the_right_way_round(engine):
    """`rank_in_a` is where B sits among A's partners. On this pair the two
    ranks differ by an order of magnitude, so a page that swapped them would
    read as CNRS's sixteenth partner being Strasbourg's first."""
    ctx, _subs = engine
    p = collab_data.pulse(ctx, STRASBOURG, CNRS)
    assert (p["rank_in_a"], p["rank_in_b"]) == (1, 16), p
    names = {i: str(ctx["index_by_id"].loc[i, "display_name"]) for i in PAIR}
    at = _app().run()
    assert copy.COLLAB["PULSE_RANK_LINE"].format(
        name_a=names[STRASBOURG], name_b=names[CNRS],
        rank_of_b=views_collab._count(p["rank_in_a"]),
        rank_of_a=views_collab._count(p["rank_in_b"])).replace("**", "") in _text(at)


def test_pulse_trend_line_follows_the_two_dynamics_windows(engine):
    """The plain-language line is a DATA answer: mean annual joint volume over
    the two windows the rest of the tool reads dynamics on, in neutral
    vocabulary and with the partial year excluded from both."""
    ctx, _subs = engine
    p = collab_data.pulse(ctx, STRASBOURG, CNRS)
    yearly = p["yearly"]
    w1 = views_collab._window_mean(yearly, DYNAMICS_W1)
    w2 = views_collab._window_mean(yearly, DYNAMICS_W2)
    change = (w2 - w1) / w1
    line = views_collab._trend_line(yearly)
    if abs(change) < views_collab.TREND_BAND:
        expected = copy.COLLAB["PULSE_TREND_FLAT"]
    else:
        expected = copy.COLLAB["PULSE_TREND_UP" if change > 0 else "PULSE_TREND_DOWN"]
    assert _first_literal(expected) in line
    # the 2025 bonus year is in the frame but in neither window
    assert int(collab_data.PULSE_YEARS[-1]) not in range(DYNAMICS_W1[0], DYNAMICS_W2[1] + 1)
    assert line in _text(_app().run())


def test_pulse_line_carries_no_value_judgement():
    at = _app().run()
    line = views_collab._trend_line(
        collab_data.pulse(views_collab._bundle()["ctx"], STRASBOURG, CNRS)["yearly"])
    for word in ("dying", "healthy", "weak", "strong", "vibrant", "failing"):
        assert word not in line.lower(), line
    assert line in _text(at)


# ------------------------------------------------ 2. the joint corpus ------

def test_joint_corpus_discloses_floor_and_cap_and_matches_its_frame(engine):
    ctx, subs = engine
    prof = collab_data.joint_profile(ctx, subs, STRASBOURG, CNRS)
    assert prof is not None
    at = _app().run()
    text = _text(at)
    assert copy.COLLAB["JOINT_INTRO"].format(
        cap=collab_data.PAIR_TOPICS_TOP_N, floor=collab_data.PAIR_TOPICS_FLOOR) in text
    shown = float(prof["topics"]["vol_total"].sum())
    tagged = int(prof["sdg_tagged_total"])
    assert copy.COLLAB["JOINT_SDG_LINE"].format(
        n_tagged=views_collab._count(tagged), n_shown=views_collab._count(shown),
        share=views_collab._pct(tagged / shown)) in text
    assert len(prof["topics"]) <= collab_data.PAIR_TOPICS_TOP_N


def test_erc_line_divides_by_the_labelled_count_never_by_the_pair_total(engine):
    """2BR A9: the panel share's denominator is the labelled joint works, and
    the caption states what share of the pair carries a label at all. The two
    denominators are different numbers and both are on the page."""
    ctx, subs = engine
    prof = collab_data.joint_profile(ctx, subs, STRASBOURG, CNRS)
    erc = prof["erc"]
    total = collab_data.pulse(ctx, STRASBOURG, CNRS)["copubs_total"]
    assert erc["labelled_n"] < total, "this pair would not prove the two denominators differ"
    text = _text(_app().run())
    assert copy.COLLAB["JOINT_ERC_LINE"].format(
        panel=views_collab._erc_panel_label(ctx, erc["panel_idx"]),
        n_panel=views_collab._count(erc["panel_n"]),
        n_labelled=views_collab._count(erc["labelled_n"]),
        share=views_collab._pct(erc["panel_n"] / erc["labelled_n"])).replace("**", "") in text
    assert copy.COLLAB["JOINT_ERC_CAPTION"].format(
        pct=views_collab._pct(erc["labelled_n"] / total)) in text


# ------------------------------------------------ the below-floor branch ---

def test_below_floor_pair_renders_the_notice_and_no_joint_tables(engine):
    """The acceptance case of 2B-R-10: a REAL sub-floor pair. Topline, honest
    notice, no invented topic detail, and the link-outs still there."""
    ctx, subs = engine
    p = collab_data.pulse(ctx, STRASBOURG, BAVARIAN)
    assert p is not None and p["copubs_total"] < collab_data.PAIR_TOPICS_FLOOR, p
    assert collab_data.joint_profile(ctx, subs, STRASBOURG, BAVARIAN) is None

    at = _app(basket=SUB_FLOOR_PAIR).run()
    assert not at.exception, [str(e) for e in at.exception]
    text = _text(at)
    assert copy.COLLAB["TOPIC_BELOW_FLOOR_NOTICE"].format(
        n_copubs=views_collab._count(p["copubs_total"]),
        floor=collab_data.PAIR_TOPICS_FLOOR) in text
    assert len(at.dataframe) == N_TABLES_BELOW_FLOOR, (
        f"{len(at.dataframe)} tables below the floor, expected {N_TABLES_BELOW_FLOOR}")
    # the topline and the link-outs survive
    assert views_collab._count(p["copubs_total"]) in [m.value for m in at.metric]
    assert copy.COLLAB["LINKS_HEADER"] in [s.value for s in at.subheader]
    assert copy.COLLAB["JOINT_INTRO"].split("{")[0].strip() not in text


def test_below_floor_pair_still_reads_the_two_portfolios(engine):
    """Sections three and four do NOT depend on the topic floor: the untapped
    reading is built on the shared-topic substrate, not on the pair table."""
    ctx, subs = engine
    res = collab_data.untapped(ctx, subs, STRASBOURG, BAVARIAN)
    assert not res["topics"].empty
    at = _app(basket=SUB_FLOOR_PAIR).run()
    assert copy.COLLAB["UNTAPPED_CAPTION"].format(
        k=views_collab._pct(res["k"])) in _text(at)


# --------------------------------------------- 3. untapped potential -------

def test_untapped_table_matches_its_own_formula(engine):
    ctx, subs = engine
    res = collab_data.untapped(ctx, subs, STRASBOURG, CNRS)
    topics = res["topics"]
    assert not topics.empty
    assert (topics["gap"] > 0).all(), "a row with nothing left over is not untapped"
    assert list(topics["gap"]) == sorted(topics["gap"], reverse=True)
    assert (topics["joint_expected"] >= topics["joint_observed"]).all()
    at = _app().run()
    text = _text(at)
    assert copy.COLLAB["UNTAPPED_CAPTION"].format(k=views_collab._pct(res["k"])) in text
    assert copy.COLLAB["UNTAPPED_RATE_NOTE"].format(
        window=views_collab._window(collab_data.PULSE_YEARS)) in text


def test_the_2b_tables_are_kept_under_the_untapped_section(engine):
    """2B-R-10 recycles the gap tables rather than dropping them, and the
    weighted topic overlap still asserts the engine identity its caption
    claims."""
    ctx, subs = engine
    at = _app().run()
    labels = [d.label for d in at.get("download_button")]
    assert labels.count(copy.COLLAB["DOWNLOAD_GAPS"]) == 2
    assert labels.count(copy.COLLAB["DOWNLOAD_UNTAPPED"]) == 1
    df = views_collab._shared_frame(STRASBOURG, CNRS, TREE, BASIS)
    page_score = float(df["min_share"].sum())
    engine_score = float(rank_all(ctx, subs, STRASBOURG)["L3"]["scores"][ctx["id_pos"][CNRS]])
    assert page_score == pytest.approx(engine_score, rel=0, abs=1e-6)
    assert copy.COLLAB["SHARED_CAPTION"].format(score=f"{page_score:.3f}") in _text(at)


def test_gaps_are_directional_and_the_swap_button_reverses_them(engine):
    ctx, _subs = engine
    ab = views_collab._gaps_frame(STRASBOURG, CNRS, TREE, BASIS)
    ba = views_collab._gaps_frame(CNRS, STRASBOURG, TREE, BASIS)
    assert set(ab["topic_id"]) != set(ba["topic_id"])

    name_a = str(ctx["index_by_id"].loc[STRASBOURG, "display_name"])
    name_b = str(ctx["index_by_id"].loc[CNRS, "display_name"])
    header = copy.COLLAB["GAPS_HEADER"]
    at = _app().run()
    before = [s.value for s in at.subheader]
    assert before.index(header.format(a=name_a)) < before.index(header.format(a=name_b))
    at.button(key="pair_swap").click().run()
    assert not at.exception, [str(e) for e in at.exception]
    after = [s.value for s in at.subheader]
    assert after.index(header.format(a=name_b)) < after.index(header.format(a=name_a))
    assert at.selectbox(key="pair_a").value == CNRS
    assert at.selectbox(key="pair_b").value == STRASBOURG


# ------------------------------------------------------ 4. the link-outs ---

def test_link_outs_are_the_three_of_2br10(engine):
    ctx, _subs = engine
    at = _app().run()
    urls = {b.proto.url for b in at.get("link_button")} if at.get("link_button") else set()
    assert links.works_url(STRASBOURG) in urls
    assert links.works_url(CNRS) in urls
    copub = links.copubs_url(STRASBOURG, CNRS)
    assert copub in urls
    # A7: the co-publication URL repeats the SAME filter key, comma-joined.
    assert f"authorships.institutions.id:{STRASBOURG},authorships.institutions.id:{CNRS}" in copub
    assert "+" not in copub, "the `+` intersection form is forbidden (A7)"


def test_header_strip_names_both_institutions(engine):
    ctx, _subs = engine
    at = _app().run()
    rendered = " ".join(m.value for m in at.markdown)
    for iid in PAIR:
        assert str(ctx["index_by_id"].loc[iid, "display_name"]) in rendered


# ------------------------------------------------------- selection ---------

def test_pair_deeplink_seeds_the_page_with_an_empty_basket(engine):
    """`?pair=...` on a reader who has no basket at all. AppTest exposes no
    query-param API on Streamlit 1.61.1, so `selection.read_query` (the ONE
    Streamlit touchpoint in that module, by its own design) is patched -- the
    live URL path is probed in ops/_probe_collab.py."""
    fake = {"compare": [], "pair": (STRASBOURG, CNRS), "dropped": []}
    with mock.patch.object(selection, "read_query", lambda known: fake):
        at = _app(basket=[]).run()
    assert not at.exception, [str(e) for e in at.exception]
    assert len(at.dataframe) == N_TABLES, "a deep-linked pair did not render the page"
    assert at.selectbox(key="pair_a").value == STRASBOURG
    assert at.selectbox(key="pair_b").value == CNRS


def test_session_pair_from_handoff_wins_over_query_and_is_consumed_once():
    """Compare's hand-off button stashes `st.session_state["pair"]` before
    calling `st.switch_page` -- it must win even over a `?pair=` query naming
    the SAME two ids in the other order, and must not linger past the render
    that consumes it."""
    fake = {"compare": [], "pair": (STRASBOURG, CNRS), "dropped": []}
    with mock.patch.object(selection, "read_query", lambda known: fake):
        at = _app(basket=[], pair=(CNRS, STRASBOURG)).run()
        assert not at.exception, [str(e) for e in at.exception]
        assert at.selectbox(key="pair_a").value == CNRS
        assert at.selectbox(key="pair_b").value == STRASBOURG
        assert "pair" not in at.session_state, "the session pair must be consumed, not left standing"
        at.run()
        assert at.selectbox(key="pair_a").value == CNRS
        assert at.selectbox(key="pair_b").value == STRASBOURG


def test_default_pair_prefers_the_session_pair_then_the_query_then_the_basket():
    known = {STRASBOURG: 0, CNRS: 1, GDANSK: 2, "I4": 3}
    assert views_collab.default_pair(
        [STRASBOURG, CNRS], (STRASBOURG, CNRS), known, (CNRS, STRASBOURG)) == (CNRS, STRASBOURG)
    # a stale/invalid session pair (unknown id, or a == b) falls through
    assert views_collab.default_pair(
        [STRASBOURG, CNRS], (STRASBOURG, CNRS), known, (STRASBOURG, STRASBOURG)
    ) == (STRASBOURG, CNRS)
    assert views_collab.default_pair(
        [GDANSK, "I4"], (STRASBOURG, CNRS), known) == (STRASBOURG, CNRS)
    assert views_collab.default_pair([GDANSK, "I4"], None, known) == (GDANSK, "I4")
    assert views_collab.default_pair([GDANSK], None, known) is None


def test_deeplink_shown_on_the_page_round_trips_through_selection():
    at = _app().run()
    codes = [c.value for c in at.get("code")]
    link = selection.deeplink("pair", PAIR)
    assert link in codes, codes
    parsed = selection.parse_query({"pair": link.split("=", 1)[1]}, PAIR)
    assert parsed["pair"] == (STRASBOURG, CNRS)


def test_empty_state_when_the_basket_holds_one_institution():
    at = _app(basket=[STRASBOURG]).run()
    assert not at.exception, [str(e) for e in at.exception]
    assert not at.dataframe, "a single institution must not render a pair view"
    assert _first_literal(copy.COLLAB["EMPTY_NO_PAIR"]) in " ".join(i.value for i in at.info)


def test_empty_state_when_both_selections_are_the_same_institution():
    at = _app(pair_a=STRASBOURG, pair_b=STRASBOURG).run()
    assert not at.exception, [str(e) for e in at.exception]
    assert not at.dataframe
    assert _first_literal(copy.COLLAB["EMPTY_SAME"]) in " ".join(i.value for i in at.info)


def test_scenario_widgets_use_the_find_page_keys():
    """2B-8: the tree/basis choice must carry across pages, which it only does
    if this page reuses Find's own widget keys."""
    at = _app().run()
    assert {"tree", "basis"} <= {sb.key for sb in at.selectbox}


# ------------------------------------------------------------ digit ban ----

def test_no_digit_ban_violations_in_this_streams_files():
    """`tests/test_narrative.py` globs lib/views_*.py and pages/*.py, so both of
    this stream's files are already inside Stream G's scope -- this runs the
    same collector over the same allowlist here too, so a violation surfaces in
    the stream that introduced it rather than in G's suite."""
    from tests.test_narrative import collect_ui_call_strings, has_digit_violation, load_allowlist

    tokens = load_allowlist()
    files = [APP_DIR / "lib" / "views_collab.py", Path(COLLAB_PAGE)]
    strings = [(loc, s) for f in files for loc, s in collect_ui_call_strings(f)]
    assert strings, "collector found no UI-call strings in this stream's files -- it is vacuous"
    violations = [(loc, s) for loc, s in strings if has_digit_violation(s, tokens)]
    assert not violations, violations

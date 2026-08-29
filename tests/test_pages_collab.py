"""
tests/test_pages_collab.py -- Stream L: AppTest page-render tests for
pages/3_(handshake)_Collaborate.py and the render helpers in
lib/views_collab.py (BUILD_PLAN_2B.md decisions 2B-7 / 2B-8, amendments A7 and
A11).

Same process economics as tests/test_pages.py: `st.cache_resource` keeps the
engine context and the (tree, basis) substrates warm across AppTest instances
inside one pytest PROCESS, so the FIRST test here pays the cold engine load
(~10 s measured on this build) and every later one runs in well under a second.
Each test still builds its OWN AppTest -- a shared instance would leak the pair
selection between tests.

WHAT IS PINNED HERE (and why each is a page-level test rather than a
lib/collab_data.py one, which tests/test_collab_data.py already covers):

  * ENGINE IDENTITY THROUGH THE PAGE. The number the page prints as the
    topic-overlap score is the sum of the `min_share` column of the frame the
    page actually renders, and that sum equals the engine's own L3 lens score
    for the pair. If a future edit re-sorts, truncates or filters the shared
    table, this test fails -- which is the point: the caption asserts an
    identity, so the table must not quietly stop satisfying it.
  * DIRECTION. `gaps` is directional; swapping A and B must swap the two gap
    tables, not just their titles.
  * The `?pair=` deep link, patched at `lib.selection.read_query` (AppTest on
    this Streamlit build exposes no query-param API of its own -- verified
    against 1.61.1 before writing this file), with the live URL path covered
    end-to-end by ops/_probe_collab.py instead.
  * The digit-ban over THIS stream's two new files, using
    tests/test_narrative.py's own collector and shared allowlist, so the page
    is proven clean before Stream G widens that test's file list (A5).

Run from cwd `app/`:  python -m pytest tests/test_pages_collab.py -q
"""
from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest
from streamlit.testing.v1 import AppTest

from lib import collab_data, copy, selection, views_collab
from lib.data_cache import DATA_DIR
from lib.engine import build_substrates, load_context, rank_all

APP_DIR = Path(__file__).resolve().parents[1]
COLLAB_PAGE = str(APP_DIR / "pages" / "3_\U0001F91D_Collaborate.py")  # handshake, the file's real name

STRASBOURG = "I68947357"   # Universite de Strasbourg -- the R1 reference seed
GDANSK = "I40413290"       # University of Gdansk -- panel_v2 D19 seed
PAIR = [STRASBOURG, GDANSK]

TREE = "bestfit"           # config.yaml's own defaults, i.e. what the page opens on
BASIS = "frac"


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


def test_page_renders_three_tables_and_both_gap_downloads():
    at = _app().run()
    assert not at.exception, [str(e) for e in at.exception]
    # shared + two directional gap tables (2B-7)
    assert len(at.dataframe) == 3, f"{len(at.dataframe)} tables rendered, expected the three of 2B-7"
    labels = [d.label for d in at.get("download_button")]
    assert labels.count(copy.COLLAB["DOWNLOAD_SHARED"]) == 1
    assert labels.count(copy.COLLAB["DOWNLOAD_GAPS"]) == 2


def test_header_strip_names_both_institutions_and_links_copubs(engine):
    ctx, _subs = engine
    at = _app().run()
    assert not at.exception, [str(e) for e in at.exception]
    rendered = " ".join(m.value for m in at.markdown)
    for iid in PAIR:
        assert str(ctx["index_by_id"].loc[iid, "display_name"]) in rendered
    # A7: the co-publication URL repeats the SAME filter key, comma-joined.
    from lib import links

    url = links.copubs_url(*PAIR)
    assert f"authorships.institutions.id:{STRASBOURG},authorships.institutions.id:{GDANSK}" in url
    assert "+" not in url, "the `+` intersection form is forbidden (A7)"


# --------------------------------------------------- engine identity -------

def test_shared_min_share_sum_equals_engine_l3_score(engine):
    """The identity `copy.COLLAB["SHARED_CAPTION"]` asserts, checked on the
    frame the PAGE renders (`views_collab._shared_frame`), not on a fresh call
    to `collab_data.shared_topics`."""
    ctx, subs = engine
    df = views_collab._shared_frame(STRASBOURG, GDANSK, TREE, BASIS)
    page_score = float(df["min_share"].sum())
    l3 = rank_all(ctx, subs, STRASBOURG)["L3"]
    engine_score = float(l3["scores"][ctx["id_pos"][GDANSK]])
    assert page_score == pytest.approx(engine_score, rel=0, abs=1e-6), (
        f"page {page_score!r} vs engine L3 {engine_score!r}")
    # ... and the caption really prints that number, at the precision the page
    # formats it with (so a silently changed format is caught too).
    at = _app().run()
    captions = " ".join(c.value for c in at.caption)
    assert copy.COLLAB["SHARED_CAPTION"].format(score=f"{page_score:.3f}") in captions


def test_shared_score_is_symmetric_under_swap(engine):
    """min(a, b) is symmetric, so the topic-overlap score must not depend on
    which institution the reader put in slot A."""
    ab = float(views_collab._shared_frame(STRASBOURG, GDANSK, TREE, BASIS)["min_share"].sum())
    ba = float(views_collab._shared_frame(GDANSK, STRASBOURG, TREE, BASIS)["min_share"].sum())
    assert ab == pytest.approx(ba, abs=1e-12)


# ---------------------------------------------------------------- gaps -----

def test_gaps_rows_are_a_subset_of_b_topics_and_absent_from_a(engine):
    """2B-7's own definition, checked on the page's cached frame: every row is
    a topic B holds mass in, and none is a topic A holds mass in."""
    ctx, subs = engine
    df = views_collab._gaps_frame(STRASBOURG, GDANSK, TREE, BASIS)
    assert not df.empty
    l3 = subs["l3"]
    cats = list(l3["cats"])
    share_a = l3["share"][ctx["id_pos"][STRASBOURG]]
    share_b = l3["share"][ctx["id_pos"][GDANSK]]
    b_topics = {cats[i] for i in range(len(cats)) if share_b[i] > 0}
    a_topics = {cats[i] for i in range(len(cats)) if share_a[i] > 0}
    rows = set(df["topic_id"])
    assert rows <= b_topics, f"{len(rows - b_topics)} gap rows are not topics B publishes in"
    assert not (rows & a_topics), f"{len(rows & a_topics)} gap rows are topics A already holds"


def test_gaps_are_directional():
    """The two tables answer different questions -- if they were the same
    frame, the page's second table would be decoration."""
    ab = views_collab._gaps_frame(STRASBOURG, GDANSK, TREE, BASIS)
    ba = views_collab._gaps_frame(GDANSK, STRASBOURG, TREE, BASIS)
    assert set(ab["topic_id"]) != set(ba["topic_id"])


def test_swap_button_swaps_the_gap_tables(engine):
    ctx, _subs = engine
    name_a = str(ctx["index_by_id"].loc[STRASBOURG, "display_name"])
    name_b = str(ctx["index_by_id"].loc[GDANSK, "display_name"])
    header = copy.COLLAB["GAPS_HEADER"]

    at = _app().run()
    assert not at.exception, [str(e) for e in at.exception]
    before = [s.value for s in at.subheader]
    assert before.index(header.format(a=name_a)) < before.index(header.format(a=name_b))

    at.button(key="pair_swap").click().run()
    assert not at.exception, [str(e) for e in at.exception]
    after = [s.value for s in at.subheader]
    assert after.index(header.format(a=name_b)) < after.index(header.format(a=name_a)), (
        "swapping A and B did not reverse the two gap tables")
    # and the frames behind them really are the other direction's
    assert at.selectbox(key="pair_a").value == GDANSK
    assert at.selectbox(key="pair_b").value == STRASBOURG


# -------------------------------------------------------- breadth ----------

def test_breadth_uses_the_publication_floor_the_caption_states():
    """The page passes `min_full=2` (the manager's WT-2B E5 fix) and says so;
    the unfloored number is materially different, so a silent revert to K's
    default would change the sentence a reader acts on."""
    floored = views_collab._breadth(STRASBOURG, GDANSK, TREE, BASIS)
    ctx = views_collab._bundle()["ctx"]
    subs = views_collab._subs(TREE, BASIS)
    unfloored = collab_data.breadth_jaccard(ctx, subs, STRASBOURG, GDANSK, min_full=0)
    expected = collab_data.breadth_jaccard(ctx, subs, STRASBOURG, GDANSK,
                                           min_full=views_collab.BREADTH_MIN_FULL)
    assert floored == expected
    assert floored["n_a"] < unfloored["n_a"], "the floor removed nothing -- is it wired?"
    at = _app().run()
    captions = " ".join(c.value for c in at.caption)
    assert copy.COLLAB["BREADTH_FLOOR"].format(
        min_pubs=views_collab.BREADTH_MIN_FULL) in captions


# ------------------------------------------------------- selection ---------

def test_pair_deeplink_seeds_the_page_with_an_empty_basket(engine):
    """`?pair=I68947357,I40413290` on a reader who has no basket at all. AppTest
    exposes no query-param API on Streamlit 1.61.1, so `selection.read_query`
    (the ONE Streamlit touchpoint in that module, by its own design) is patched
    -- the live URL path is probed in ops/_probe_collab.py."""
    ctx, _subs = engine
    fake = {"compare": [], "pair": (STRASBOURG, GDANSK), "dropped": []}
    with mock.patch.object(selection, "read_query", lambda known: fake):
        at = _app(basket=[]).run()
    assert not at.exception, [str(e) for e in at.exception]
    assert len(at.dataframe) == 3, "a deep-linked pair did not render the three tables"
    assert at.selectbox(key="pair_a").value == STRASBOURG
    assert at.selectbox(key="pair_b").value == GDANSK


def test_session_pair_from_handoff_wins_over_query_and_is_consumed_once():
    """Compare's hand-off button stashes `st.session_state["pair"]` before
    calling `st.switch_page` (lib/views_compare.py `_handoff`,
    BUILD_PLAN_2B.md progress/2B_X.md) -- the fix for a hand-off that used to
    drop the whole session, keeping only the pair alive via the query string.
    A session pair must therefore win even over a `?pair=` query naming the
    SAME two ids in the other order, and must not linger past the render that
    consumes it -- a lingering value would keep re-forcing itself onto
    pair_a/pair_b on every later rerun, defeating any subsequent reader
    edit."""
    fake = {"compare": [], "pair": (STRASBOURG, GDANSK), "dropped": []}
    with mock.patch.object(selection, "read_query", lambda known: fake):
        at = _app(basket=[], pair=(GDANSK, STRASBOURG)).run()
        assert not at.exception, [str(e) for e in at.exception]
        assert at.selectbox(key="pair_a").value == GDANSK
        assert at.selectbox(key="pair_b").value == STRASBOURG
        assert "pair" not in at.session_state, "the session pair must be consumed, not left standing"

        # A bare rerun (no session pair left to re-force anything) must hold
        # steady rather than snap back to the query's own (STRASBOURG, GDANSK).
        at.run()
        assert not at.exception, [str(e) for e in at.exception]
        assert at.selectbox(key="pair_a").value == GDANSK
        assert at.selectbox(key="pair_b").value == STRASBOURG


def test_default_pair_prefers_the_session_pair_over_the_query():
    known = {STRASBOURG: 0, GDANSK: 1}
    assert views_collab.default_pair(
        [STRASBOURG, GDANSK], (STRASBOURG, GDANSK), known, (GDANSK, STRASBOURG)
    ) == (GDANSK, STRASBOURG)
    # a stale/invalid session pair (unknown id, or a==b) falls through to the query
    assert views_collab.default_pair(
        [STRASBOURG, GDANSK], (STRASBOURG, GDANSK), known, (STRASBOURG, STRASBOURG)
    ) == (STRASBOURG, GDANSK)
    assert views_collab.default_pair(
        [STRASBOURG, GDANSK], (STRASBOURG, GDANSK), known, ("IX", GDANSK)
    ) == (STRASBOURG, GDANSK)


def test_default_pair_prefers_the_query_over_the_basket():
    known = {STRASBOURG: 0, GDANSK: 1, "I3": 2, "I4": 3}
    assert views_collab.default_pair(["I3", "I4"], (STRASBOURG, GDANSK), known) == (STRASBOURG,
                                                                                    GDANSK)
    assert views_collab.default_pair(["I3", "I4"], None, known) == ("I3", "I4")
    # a half-valid or self-referential link falls back to the basket order
    assert views_collab.default_pair(["I3", "I4"], ("I3", "I3"), known) == ("I3", "I4")
    assert views_collab.default_pair(["I3", "I4"], ("I3", "IX"), known) == ("I3", "I4")
    assert views_collab.default_pair(["I3"], None, known) is None


def test_deeplink_shown_on_the_page_round_trips_through_selection():
    at = _app().run()
    codes = [c.value for c in at.get("code")]
    link = selection.deeplink("pair", PAIR)
    assert link in codes, codes
    parsed = selection.parse_query({"pair": link.split("=", 1)[1]}, PAIR)
    assert parsed["pair"] == (STRASBOURG, GDANSK)


def test_empty_state_when_the_basket_holds_one_institution():
    at = _app(basket=[STRASBOURG]).run()
    assert not at.exception, [str(e) for e in at.exception]
    assert not at.dataframe, "a single institution must not render a pair view"
    infos = " ".join(i.value for i in at.info)
    assert _first_literal(copy.COLLAB["EMPTY_NO_PAIR"]) in infos


def test_empty_state_when_both_selections_are_the_same_institution():
    at = _app(pair_a=STRASBOURG, pair_b=STRASBOURG).run()
    assert not at.exception, [str(e) for e in at.exception]
    assert not at.dataframe
    infos = " ".join(i.value for i in at.info)
    assert _first_literal(copy.COLLAB["EMPTY_SAME"]) in infos


def test_scenario_widgets_use_the_find_page_keys():
    """2B-8: the tree/basis choice must carry across pages, which it only does
    if this page reuses Find's own widget keys."""
    at = _app().run()
    keys = {sb.key for sb in at.selectbox}
    assert {"tree", "basis"} <= keys, keys


# ------------------------------------------------------------ digit ban ----

def test_no_digit_ban_violations_in_this_streams_files():
    """A5: `tests/test_narrative.py` does not yet list lib/views_collab.py (it
    does already glob pages/*.py). Run its own collector, over its own shared
    allowlist, on both files this stream adds -- so the page is proven clean
    now, and Stream G's widening finds nothing to fix."""
    from tests.test_narrative import collect_ui_call_strings, has_digit_violation, load_allowlist

    tokens = load_allowlist()
    files = [APP_DIR / "lib" / "views_collab.py", Path(COLLAB_PAGE)]
    strings = [(loc, s) for f in files for loc, s in collect_ui_call_strings(f)]
    assert strings, "collector found no UI-call strings in this stream's files -- it is vacuous"
    violations = [(loc, s) for loc, s in strings if has_digit_violation(s, tokens)]
    assert not violations, violations

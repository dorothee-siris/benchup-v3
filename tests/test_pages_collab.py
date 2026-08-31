"""
tests/test_pages_collab.py -- stream LP3: AppTest page-render tests for
pages/3_(handshake)_Collaborate.py and the render helpers in
lib/views_collab.py, re-cut for the FIVE-SECTION page of BUILD_PLAN_2BR2.md
decision 2B-R2-11 (pulse -> field breakdown chart -> shared topics -> untapped
potential -> link-outs, plus the plain-language "not shown here" block).

TWO PAIRS ARE RENDERED (N = 2), and the second one is the point:

  * Universite de Strasbourg x CNRS -- the manager-verified anchor. CNRS is
    Strasbourg's FIRST partner and Strasbourg is CNRS's SIXTEENTH, so this pair
    is also the RANK-DIRECTION pin: a page that rendered `rank_in_a` as A's own
    rank instead of B's would still look plausible and would be wrong, and only
    an asymmetric pair catches it.
  * Universite de Strasbourg x Bavarian Academy of Sciences and Humanities -- a
    REAL sub-floor pair (2 joint works, under `collab_data.PAIR_TOPICS_FLOOR`,
    which 2B-R2-12 moved to five), which must render the SHARED below-floor
    notice with its own numbers, drop the field and topic tables rather than
    show empty ones, and keep the pulse, the untapped reading and every
    link-out.

WHAT IS PINNED HERE (rather than in tests/test_collab_data.py, which owns the
frames themselves): that the PAGE renders those frames' numbers, in the right
direction, with their denominators named; that every taxon name carries its
domain chip, every row its arrow and its live link; that the sliders really cut
the rendered rows; that the two directional gap tables are GONE from the code
rather than hidden; and the digit ban over this stream's files. The live URL
path (`?pair=A,B`), the rendered legend strip, the starred partial year on the
chart axis, the link hrefs as a browser sees them and the three viewport widths
are probed in ops/_probe_collab.py, which drives a real browser.

The four tables are hand-built HTML (see lib/views_collab.py's docstring on why
Streamlit's canvas grid cannot carry a chip, a per-row link or a readable
value), so they are asserted THROUGH THAT MARKUP here -- `data-table` names the
table, `data-row` its rows, `data-domain` a chip and `data-arrow` a direction.

Run from cwd `app/`:  python -m pytest tests/test_pages_collab.py -q
"""
from __future__ import annotations

import re
from pathlib import Path
from unittest import mock

import pytest
from streamlit.testing.v1 import AppTest

from lib import collab_data, copy, links, palette, selection, views_collab
from lib.compare_data import DYNAMICS_W1, DYNAMICS_W2
from lib.data_cache import DATA_DIR
from lib.engine import build_substrates, load_context

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

TABLES = ("collab_fields", "collab_topics", "collab_untapped", "collab_siblings")
TABLES_BELOW_FLOOR = ("collab_untapped", "collab_siblings")


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


def _tables(at) -> dict:
    """`{table name: its markup}` for the hand-built tables on the page."""
    out = {}
    for m in at.markdown:
        for name in re.findall(r'data-table="([a-z_]+)"', m.value):
            out[name] = m.value
    return out


def _rows(at, name: str) -> int:
    return _tables(at).get(name, "").count("data-row=")


def _first_literal(template: str) -> str:
    """The template's first non-empty fixed segment, for a substring check
    against rendered text (tests/test_pages.py's own idiom)."""
    segments = [s for s in re.split(r"\{[^{}]*\}", template) if s.strip()]
    assert segments, f"template has no fixed text: {template!r}"
    return segments[0].strip()


# ------------------------------------------------------------- render ------

def test_page_renders_without_exception():
    at = _app().run()
    assert not at.exception, [str(e) for e in at.exception]


def test_the_five_sections_render_in_the_order_2br2_11_names():
    at = _app().run()
    assert not at.exception, [str(e) for e in at.exception]
    heads = [s.value for s in at.subheader]
    order = [copy.COLLAB["PULSE_HEADER"], copy.COLLAB["FIELDS_HEADER"],
             copy.COLLAB["TOPICS_HEADER"], copy.COLLAB["UNTAPPED_HEADER"],
             copy.COLLAB["LINKS_HEADER"]]
    positions = [heads.index(h) for h in order]
    assert positions == sorted(positions), heads


def test_the_four_tables_are_dom_readable_markup_not_canvas_grids():
    """The 2B-R2-11 tables carry a chip, an arrow and a per-row link, none of
    which Streamlit's canvas grid can render or a probe can read back."""
    at = _app().run()
    assert set(_tables(at)) == set(TABLES), sorted(_tables(at))
    assert not at.dataframe, f"{len(at.dataframe)} canvas grids left on the page"


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
    yearly = collab_data.pulse(ctx, STRASBOURG, CNRS)["yearly"]
    w1 = views_collab._window_mean(yearly, DYNAMICS_W1)
    w2 = views_collab._window_mean(yearly, DYNAMICS_W2)
    change = (w2 - w1) / w1
    line = views_collab._trend_line(yearly)
    if abs(change) < views_collab.TREND_BAND:
        expected = copy.COLLAB["PULSE_TREND_FLAT"]
    else:
        expected = copy.COLLAB["PULSE_TREND_UP" if change > 0 else "PULSE_TREND_DOWN"]
    assert _first_literal(expected) in line
    # the bonus year is in the frame but in neither window
    assert int(collab_data.PULSE_YEARS[-1]) not in range(DYNAMICS_W1[0], DYNAMICS_W2[1] + 1)
    at = _app().run()
    assert line in _text(at)
    for word in ("dying", "healthy", "weak", "strong", "vibrant", "failing"):
        assert word not in line.lower(), line


# ------------------------------- 2. the joint corpus, field by field -------

def test_field_chart_draws_the_pairs_own_volumes_in_one_neutral_hue(engine):
    """2B-R2-11(a). The bars are the pair's, so no institution colour may reach
    them: `PAIR_SERIES_KEY` is in no slot map and the fills come back COMPARISON
    grey. The values are `collab_pair_fields`' own, unrounded."""
    ctx, _subs = engine
    fields = collab_data.field_breakdown(ctx, STRASBOURG, CNRS)
    assert not fields.empty
    fig = views_collab._fields_chart(fields)
    drawn = [float(v) for tr in fig.data for v in tr.x]
    assert sorted(drawn) == sorted(float(v) for v in fields["vol_total"])
    fills = {c for tr in fig.data for c in tuple(tr.marker.color)}
    assert fills == {palette.COMPARISON}, fills
    assert not (fills & set(palette.INSTITUTION_COLORS)), "an institution hue reached the pair's bars"


def test_field_chart_labels_carry_the_openalex_domain_colour(engine):
    """The coexistence rule, one way round: the taxonomy's colour appears on the
    row LABEL (and on the chip beside the name in the table), never on a mark."""
    ctx, _subs = engine
    fields = collab_data.field_breakdown(ctx, STRASBOURG, CNRS)
    fig = views_collab._fields_chart(fields)
    ticks = list(fig.layout.yaxis.ticktext)
    assert len(ticks) == len(fields)
    wanted = {palette.domain_color(d) for d in fields["domain_id"]}
    assert wanted <= {c for t in ticks for c in re.findall(r"color:(#[0-9A-Fa-f]{6})", t)}
    for name, domain in zip(fields["field_name"], fields["domain_id"]):
        hit = [t for t in ticks if name.split()[0] in t.replace("<br>", " ")]
        assert hit, name
        assert palette.domain_color(domain) in hit[0], name


def test_field_table_carries_the_chips_impact_pair_and_row_links(engine):
    ctx, _subs = engine
    fields = collab_data.field_breakdown(ctx, STRASBOURG, CNRS)
    at = _app().run()
    markup = _tables(at)["collab_fields"]
    assert markup.count("data-row=") == len(fields)
    for _, r in fields.head(5).iterrows():
        assert f'data-domain="{int(r["domain_id"])}"' in markup
        assert palette.domain_color(r["domain_id"]) in markup
        assert copy.COLLAB["COL_TOP10_VALUE"].format(
            n_top10=views_collab._count(r["n_top10"]),
            n_covered=views_collab._count(r["n_covered"])) in markup
        assert views_collab._count(r["mean_citations"]) in markup
        assert r["url"] in markup
    arrows = set(re.findall(r'data-arrow="([a-z]+)"', markup))
    assert arrows <= {collab_data.ARROW_UP, collab_data.ARROW_DOWN, collab_data.ARROW_FLAT}
    assert arrows == set(fields["arrow"])


def test_the_field_section_says_the_impact_columns_have_no_normalised_score(engine):
    """2B-R2-11(c): the descope is stated WHERE the impact columns are
    introduced, in the shared wording, not invented a second time here."""
    at = _app().run()
    text = _text(at)
    assert copy.FWCI_NOT_AVAILABLE_LINE.split(":")[0] in text
    assert copy.COLLAB["COL_TOP10_HELP"].split(".")[0] in text


def test_field_breakdown_does_not_follow_the_taxonomy_toggle(engine):
    """The pair x field table ships one tree, so the frame is keyed on the pair
    alone -- and the tooltip says so rather than letting a reader think the
    numbers moved with the sidebar."""
    ctx, _subs = engine
    one = collab_data.field_breakdown(ctx, STRASBOURG, CNRS)
    assert views_collab._fields_frame.__wrapped__.__code__.co_varnames[:2] == ("a", "b")
    assert list(one["field_id"]) == list(collab_data.field_breakdown(ctx, CNRS, STRASBOURG)["field_id"])
    assert _first_literal(copy.COLLAB["FIELDS_CHART_TOOLTIP"]) in _text(_app().run())


# ------------------------------------------------- 3. the shared topics ----

def test_topics_table_matches_the_frame_row_for_row(engine):
    ctx, subs = engine
    prof = collab_data.joint_profile(ctx, subs, STRASBOURG, CNRS)
    at = _app().run()
    markup = _tables(at)["collab_topics"]
    shown = markup.count("data-row=")
    assert shown == min(views_collab.ROWS_DEFAULT, len(prof["topics"]))
    head = prof["topics"].head(shown)
    for _, r in head.head(5).iterrows():
        assert r["url"] in markup
        assert f'data-arrow="{r["arrow"]}"' in markup
        assert copy.COLLAB["COL_TOP10_VALUE"].format(
            n_top10=views_collab._count(r["n_top10"]),
            n_covered=views_collab._count(r["n_covered"])) in markup
        assert f'data-domain="{int(r["domain_id"])}"' in markup
    assert copy.COLLAB["TABLE_ROWS_NOTE"].format(
        n_shown=views_collab._count(shown),
        n_total=views_collab._count(len(prof["topics"]))) in _text(at)


def test_the_slider_really_cuts_the_rendered_rows(engine):
    """The slider is the whole reason the top-100 cap is usable: it must change
    the TABLE, not just its own value."""
    ctx, subs = engine
    prof = collab_data.joint_profile(ctx, subs, STRASBOURG, CNRS)
    cap = len(prof["topics"])
    assert cap > views_collab.ROWS_DEFAULT, "this pair cannot exercise the slider"
    at = _app().run()
    assert _rows(at, "collab_topics") == views_collab.ROWS_DEFAULT
    at.slider(key="topics_n").set_value(cap).run()
    assert not at.exception, [str(e) for e in at.exception]
    assert _rows(at, "collab_topics") == cap
    at.slider(key="topics_n").set_value(views_collab.ROWS_STEP).run()
    assert _rows(at, "collab_topics") == views_collab.ROWS_STEP


def test_topic_rows_link_to_the_pairs_own_publications_on_that_topic(engine):
    """2B-R2-11(e): a live OpenAlex link per row, both institutions ANDed and
    the topic filter added -- never the forbidden `+` union form."""
    ctx, subs = engine
    prof = collab_data.joint_profile(ctx, subs, STRASBOURG, CNRS)
    row = prof["topics"].iloc[0]
    url = row["url"]
    assert url == links.copubs_taxon_url(STRASBOURG, CNRS, "topic", row["topic_id"])
    assert f"authorships.institutions.id:{STRASBOURG},authorships.institutions.id:{CNRS}" in url
    assert f"{links.TAXON_FILTER_KEY['topic']}:{row['topic_id']}" in url
    assert "+" not in url.split("filter=")[-1]
    assert url in _tables(_app().run())["collab_topics"]


def test_goal_and_panel_lines_keep_their_own_denominators(engine):
    """The panel share's denominator is the LABELLED joint works and the goal
    line's is the shown topics: two different numbers, both on the page."""
    ctx, subs = engine
    prof = collab_data.joint_profile(ctx, subs, STRASBOURG, CNRS)
    erc = prof["erc"]
    total = collab_data.pulse(ctx, STRASBOURG, CNRS)["copubs_total"]
    assert erc["labelled_n"] < total, "this pair would not prove the two denominators differ"
    at = _app().run()
    text = _text(at)
    assert copy.COLLAB["JOINT_ERC_LINE"].format(
        panel=views_collab._erc_panel_label(ctx, erc["panel_idx"]),
        n_panel=views_collab._count(erc["panel_n"]),
        n_labelled=views_collab._count(erc["labelled_n"]),
        share=views_collab._pct(erc["panel_n"] / erc["labelled_n"])).replace("**", "") in text
    assert copy.COLLAB["JOINT_ERC_CAPTION"].format(
        pct=views_collab._pct(erc["labelled_n"] / total)) in text
    shown = prof["topics"].head(views_collab.ROWS_DEFAULT)
    tagged = int(shown["sdg_tagged_n"].sum())
    vol = float(shown["vol_total"].sum())
    assert copy.COLLAB["JOINT_SDG_LINE"].format(
        n_tagged=views_collab._count(tagged), n_shown=views_collab._count(vol),
        share=views_collab._pct(tagged / vol)) in text


# ------------------------------------------------ the below-floor branch ---

def test_below_floor_pair_renders_the_shared_notice_and_no_breakdown(engine):
    """The acceptance case of 2B-R2-11(g): a REAL sub-floor pair at the floor
    the pair tables now ship with. Topline, honest notice, no invented detail,
    and the link-outs still there."""
    ctx, subs = engine
    p = collab_data.pulse(ctx, STRASBOURG, BAVARIAN)
    assert p is not None and p["copubs_total"] < collab_data.PAIR_TOPICS_FLOOR, p
    assert collab_data.joint_profile(ctx, subs, STRASBOURG, BAVARIAN) is None
    assert collab_data.field_breakdown(ctx, STRASBOURG, BAVARIAN).empty

    at = _app(basket=SUB_FLOOR_PAIR).run()
    assert not at.exception, [str(e) for e in at.exception]
    text = _text(at)
    assert copy.SHARED["BELOW_FLOOR_NOTICE"].format(
        item=copy.COLLAB["BELOW_FLOOR_ITEM"],
        n=views_collab._count(p["copubs_total"]),
        floor=collab_data.PAIR_TOPICS_FLOOR) in text
    assert set(_tables(at)) == set(TABLES_BELOW_FLOOR), sorted(_tables(at))
    assert copy.COLLAB["TOPICS_HEADER"] not in [s.value for s in at.subheader]
    # the topline and the link-outs survive
    assert views_collab._count(p["copubs_total"]) in [m.value for m in at.metric]
    assert copy.COLLAB["LINKS_HEADER"] in [s.value for s in at.subheader]


def test_below_floor_pair_still_reads_the_two_portfolios(engine):
    """Section four does NOT depend on the topic floor: the untapped reading is
    built on the shared-topic substrate, not on the pair table."""
    ctx, subs = engine
    res = collab_data.untapped(ctx, subs, STRASBOURG, BAVARIAN)
    assert not res["topics"].empty
    at = _app(basket=SUB_FLOOR_PAIR).run()
    assert copy.COLLAB["UNTAPPED_CAPTION"].format(k=views_collab._pct(res["k"])) in _text(at)


# --------------------------------------------- 4. untapped potential -------

def test_untapped_table_matches_its_own_formula_and_carries_chips_and_links(engine):
    ctx, subs = engine
    res = collab_data.untapped(ctx, subs, STRASBOURG, CNRS)
    topics = res["topics"]
    assert not topics.empty
    assert (topics["gap"] > 0).all(), "a row with nothing left over is not untapped"
    assert list(topics["gap"]) == sorted(topics["gap"], reverse=True)
    assert (topics["joint_expected"] >= topics["joint_observed"]).all()
    at = _app().run()
    markup = _tables(at)["collab_untapped"]
    assert markup.count("data-row=") == min(views_collab.ROWS_DEFAULT, len(topics))
    for _, r in topics.head(3).iterrows():
        assert r["url"] in markup
        assert views_collab._vol(r["gap"]) in markup
    assert 'data-domain="' in markup
    text = _text(at)
    assert copy.COLLAB["UNTAPPED_READING"] in text
    assert copy.COLLAB["UNTAPPED_CAPTION"].format(k=views_collab._pct(res["k"])) in text
    assert copy.COLLAB["UNTAPPED_RATE_NOTE"].format(
        window=views_collab._window(collab_data.PULSE_YEARS)) in text


def test_sibling_suggestions_are_kept_beside_the_untapped_table(engine):
    ctx, subs = engine
    res = collab_data.untapped(ctx, subs, STRASBOURG, CNRS)
    at = _app().run()
    assert copy.COLLAB["SIBLINGS_CAPTION"].format(
        n=views_collab._count(len(res["siblings"]))) in _text(at)
    assert _rows(at, "collab_siblings") == len(res["siblings"])


# ------------------------------------------------ 5. links + disclosure ----

def test_link_outs_are_the_three_of_the_closing_section(engine):
    at = _app().run()
    urls = {b.proto.url for b in at.get("link_button")} if at.get("link_button") else set()
    assert links.works_url(STRASBOURG) in urls
    assert links.works_url(CNRS) in urls
    copub = links.copubs_url(STRASBOURG, CNRS)
    assert copub in urls
    assert f"authorships.institutions.id:{STRASBOURG},authorships.institutions.id:{CNRS}" in copub
    assert "+" not in copub, "the `+` intersection form is forbidden"


def test_the_two_directional_gap_tables_are_deleted_not_hidden():
    """2B-R2-11(f). The check is structural as well as visual: the data function
    is gone from `lib/collab_data.py`, its two render helpers are gone from this
    page, and nothing on the page names them."""
    assert not hasattr(collab_data, "gaps")
    for gone in ("_render_gaps", "_gaps_frame", "_gaps_display", "_render_breadth",
                 "_render_shared", "_shared_frame"):
        assert not hasattr(views_collab, gone), gone
    ctx = views_collab._bundle()["ctx"]
    at = _app().run()
    text = _text(at)
    heads = [s.value for s in at.subheader]
    for iid in PAIR:
        assert copy.COLLAB["GAPS_HEADER"].format(
            a=str(ctx["index_by_id"].loc[iid, "display_name"])) not in heads
    labels = [d.label for d in at.get("download_button")]
    assert copy.COLLAB["DOWNLOAD_GAPS"] not in labels
    assert _first_literal(copy.COLLAB["BREADTH_LINE"]) not in text


def test_what_is_not_shown_is_stated_in_plain_language():
    """2B-R2-8: one line per hidden measure, in the shared wording, with no
    internal reference of any kind."""
    at = _app().run()
    text = _text(at)
    assert copy.SHARED["NOT_OFFERED_HEADER"] in text
    for feature, reason in (
            (copy.COLLAB["NOT_OFFERED_GAPS"], copy.COLLAB["NOT_OFFERED_GAPS_REASON"]),
            (copy.COLLAB["NOT_OFFERED_BREADTH"], copy.COLLAB["NOT_OFFERED_BREADTH_REASON"]),
            (copy.COLLAB["NOT_OFFERED_SUBFIELDS"], copy.COLLAB["NOT_OFFERED_SUBFIELDS_REASON"])):
        assert copy.SHARED["NOT_OFFERED_LINE"].format(feature=feature, reason=reason) in text


def test_no_rendered_string_names_a_build_code_or_a_table():
    """2B-R2-13, over the page as it actually renders (the copy module's own
    scan is tests/test_forbidden_vocabulary.py's)."""
    from tests.test_forbidden_vocabulary import _violations

    at = _app().run()
    visible = [(c.__class__.__name__, c.value) for c in list(at.caption) + list(at.subheader)
               + list(at.info)]
    assert not _violations(visible), _violations(visible)


def test_header_strip_names_both_institutions(engine):
    ctx, _subs = engine
    at = _app().run()
    rendered = " ".join(m.value for m in at.markdown)
    for iid in PAIR:
        assert str(ctx["index_by_id"].loc[iid, "display_name"]) in rendered


# ------------------------------------------------------- selection ---------

def test_pair_deeplink_seeds_the_page_with_an_empty_basket():
    """`?pair=...` on a reader who has no basket at all. AppTest exposes no
    query-param API on Streamlit 1.61.1, so `selection.read_query` (the ONE
    Streamlit touchpoint in that module, by its own design) is patched -- the
    live URL path is probed in ops/_probe_collab.py."""
    fake = {"compare": [], "pair": (STRASBOURG, CNRS), "dropped": []}
    with mock.patch.object(selection, "read_query", lambda known: fake):
        at = _app(basket=[]).run()
    assert not at.exception, [str(e) for e in at.exception]
    assert set(_tables(at)) == set(TABLES), "a deep-linked pair did not render the page"
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


def test_swap_button_reverses_the_pair():
    at = _app().run()
    at.button(key="pair_swap").click().run()
    assert not at.exception, [str(e) for e in at.exception]
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
    assert not _tables(at), "a single institution must not render a pair view"
    assert _first_literal(copy.COLLAB["EMPTY_NO_PAIR"]) in " ".join(i.value for i in at.info)


def test_empty_state_when_both_selections_are_the_same_institution():
    at = _app(pair_a=STRASBOURG, pair_b=STRASBOURG).run()
    assert not at.exception, [str(e) for e in at.exception]
    assert not _tables(at)
    assert _first_literal(copy.COLLAB["EMPTY_SAME"]) in " ".join(i.value for i in at.info)


def test_scenario_widgets_use_the_find_page_keys():
    """The tree/basis choice must carry across pages, which it only does if this
    page reuses Find's own widget keys."""
    at = _app().run()
    assert {"tree", "basis"} <= {sb.key for sb in at.selectbox}


# ------------------------------------------------------------ digit ban ----

def test_no_digit_ban_violations_in_this_streams_files():
    """`tests/test_narrative.py` globs lib/views_*.py and pages/*.py, so both of
    this stream's files are already inside stream G's scope -- this runs the
    same collector over the same allowlist here too, so a violation surfaces in
    the stream that introduced it rather than in G's suite."""
    from tests.test_narrative import collect_ui_call_strings, has_digit_violation, load_allowlist

    tokens = load_allowlist()
    files = [APP_DIR / "lib" / "views_collab.py", Path(COLLAB_PAGE)]
    strings = [(loc, s) for f in files for loc, s in collect_ui_call_strings(f)]
    assert strings, "collector found no UI-call strings in this stream's files -- it is vacuous"
    violations = [(loc, s) for loc, s in strings if has_digit_violation(s, tokens)]
    assert not violations, violations

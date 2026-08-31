"""
tests/test_pages_compare.py -- stream CP: AppTest page-render tests for
pages/2_(scales)_Compare.py and the render helpers in lib/views_compare.py
(BUILD_PLAN_2BR.md decisions 2B-R-4/5/6/7/8/9/12, S4 contracts, VIZ_SPEC
S2 quater 4.1 ... 4.7).

REWRITTEN for Phase 2B-R. The Phase 2B file pinned a six-institution page of
dot mirrors; the page it tested no longer exists. What is pinned now:

  * THE PAGE RENDERS AT N = 2 AND N = 3, the only two cardinalities 2B-R-4
    allows (one institution is a PROFILE and the app has one).
  * THE CAP IS THREE AND THE TRUNCATION IS DISCLOSED (2B-R-4): a basket of six
    compares three, says how many it left out, and the deep link it prints
    carries the three it actually drew.
  * THE OVERVIEW CARDS READ BACK (2B-R-7): every rendered KPI equals the value
    `compare_data.overview` returns for that institution, formatted by the
    page's own formatter -- a card that drifted from the frame would pass a
    "renders" test and fail this one.
  * THE METRIC SELECTOR'S STATES (2B-R-5): each level offers exactly the
    metrics `compare_data.metric_frame_available` allows, switching metric
    redraws without exception, drilling into a field switches the level to
    subfield, and a metric the drill retires is CLAMPED rather than raising.
  * THE UNAVAILABLE OPTIONS ARE DISCLOSED, not merely hidden: the frame's own
    reason string is rendered.
  * THE ROW ORDER IS STABLE ACROSS METRIC TABS (2B-R2-5): `_order_rows` is
    order-only -- same rows, same values -- and the DRAWN row order is identical
    from one measure to the next, which is what makes two tabs comparable; the
    per-section toggle really does re-rank.

Re-cut again for Phase 2B-R2 (stream CP3). What is pinned on top of the above:

  * THE CARDS LOST THE INTERVAL LINE AND THE PUBLICATIONS BUTTON, gained the
    best-value DOT in the leading institution's colour, and the institution name
    is now the OpenAlex link (2B-R2-9).
  * "PUBLICATIONS IN THE WORLD TOP DECILE" IS NOT A TAB (2B-R2-3) while staying
    a metric the data frame and the builder still know.
  * EVERY SELECTOR OPTION IS DRIVEN TO A RENDER at every level -- the 2B-R
    lesson, where an option was visible and its render path unreached.
  * THE FRONTIER POOL AND COLOUR CONTROLS (2B-R2-10) do real work: the elite
    pool is a strict subset, and the colour swap rebuilds the legend.
  * EVERY READING LINE FITS ONE LINE (2B-R2-8), enforced by the builder itself.
  * THE SHARED-FRONTIER MELT IS LOSSLESS (2B-R-9): per topic, the long frame's
    volumes sum to the wide frame's `combined_vol`.
  * A LEGEND SITS ABOVE EVERY CHART (2B-R-12): at least as many legend strips
    as plotly figures.
  * THE INTERVAL COVERAGE IS THE METHODS PAGE'S OWN SENTENCE (2B-R-12), filled
    from `views_methods.methods_values()`, never hand-typed here or there.
  * THE WORKBOOK MATCHES THE VIEWS (sheet names, order, the re-cut Methods
    sheet: data date, BOTH dynamics windows, the cap, the slider, the interval
    coverage; and no snapshot row, which 2B-R-12 removed app-wide).
  * The digit-ban over this stream's files, using tests/test_narrative.py's own
    collector and shared allowlist.

Same process economics as before: `st.cache_resource` keeps the engine context
and the substrates warm across AppTest instances inside one pytest PROCESS, so
the first test pays the cold load and every later one runs in about a second.
Each test builds its OWN AppTest -- a shared instance would leak the basket and
the widget state between tests.

Run from cwd `app/`:  python -m pytest tests/test_pages_compare.py -q
"""
from __future__ import annotations

import io
import re
from pathlib import Path
from unittest import mock

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from lib import charts_compare, compare_data, copy, selection, state, tiles, views_compare
from lib.data_cache import DATA_DIR
from lib.engine import build_substrates, load_context

APP_DIR = Path(__file__).resolve().parents[1]
COMPARE_PAGE = str(APP_DIR / "pages" / "2_⚖️_Compare.py")  # scales, the file's real name

STRASBOURG = "I68947357"    # Universite de Strasbourg -- the R1 reference seed
SORBONNE = "I39804081"      # Sorbonne Universite
FREIBURG = "I161046081"     # University of Freiburg -- the non-FR third
GDANSK = "I40413290"
IFPEN = "I265217849"
ISCTE = "I110026055"

PAIR = [STRASBOURG, SORBONNE]
TRIO = [STRASBOURG, SORBONNE, FREIBURG]
SIX = TRIO + [GDANSK, IFPEN, ISCTE]

TREE = "bestfit"            # config.yaml's own defaults, i.e. what the page opens on
BASIS = "frac"
SCENARIO = {"tree": TREE, "basis": BASIS}


def _app(basket=None, **extra_state) -> AppTest:
    at = AppTest.from_file(COMPARE_PAGE, default_timeout=900)
    at.session_state["basket"] = list(TRIO if basket is None else basket)
    for k, v in extra_state.items():
        at.session_state[k] = v
    return at


@pytest.fixture(scope="module")
def engine():
    ctx = load_context(str(DATA_DIR))
    return ctx, build_substrates(ctx, TREE, BASIS)


def _first_literal(template: str) -> str:
    """The template's first non-empty fixed segment, for a substring check
    against rendered text."""
    import re

    segments = [s for s in re.split(r"\{[^{}]*\}", template) if s.strip()]
    assert segments, f"template has no fixed text: {template!r}"
    return segments[0].strip()


def _captions(at) -> str:
    return " ".join(c.value for c in at.caption)


def _markdown(at) -> str:
    """Every rendered markdown block, joined. 2B-R2-8 moved most of this page's
    prose OUT of `st.caption` and into `charts_compare.chart_note` -- a reading
    line plus a `title=` tooltip, both rendered through `st.markdown` -- so a
    test that only read captions would now be testing an empty surface."""
    return " ".join(m.value for m in at.markdown)


def _rendered(at) -> str:
    return _markdown(at) + " " + _captions(at)


def _cards(at) -> int:
    """How many overview cards were drawn (2B-R2-9: the cards are markup, not
    `st.metric`, because `st.metric` cannot carry the leader dot)."""
    return sum(m.value.count(f'class="{tiles.TILE_CLASS}"') for m in at.markdown)


# ------------------------------------------------------------- render ------

@pytest.mark.parametrize("ids", [PAIR, TRIO], ids=["k_two", "k_three"])
def test_page_renders_at_both_allowed_cardinalities(ids):
    at = _app(basket=ids).run()
    assert not at.exception, [str(e) for e in at.exception]
    headers = [s.value for s in at.subheader]
    for key in ("OVERVIEW_HEADER", "VIEW_SUBJECT", "VIEW_ERC", "VIEW_SDG",
                "VIEW_FRONTIER_MAP", "VIEW_SHARED_FRONTIER", "VIEW_IMPACT",
                "VIEW_COVERAGE", "SELECTION_HEADER", "HANDOFF_HEADER"):
        assert copy.COMPARE[key] in headers, (key, headers)
    assert len(at.get("plotly_chart")) >= 8, len(at.get("plotly_chart"))


def test_the_retired_2b_views_are_gone():
    """2B-R-5/2B-R-9 removed the dot mirrors, the quadrant-mix strip and the
    frontier form control outright. A page that still drew them would still
    pass every 'renders' assertion above."""
    at = _app().run()
    headers = [s.value for s in at.subheader]
    assert copy.COMPARE["VIEW_FRONTIER_MIX"] not in headers
    assert copy.COMPARE["VIEW_FRONTIER_POINTS"] not in headers
    keys = {w.key for w in at.get("radio")} | {w.key for w in at.get("selectbox")}
    assert "cmp_frontier_form" not in keys and "cmp_frontier_mode" not in keys
    assert not any(str(k).startswith("sort_compare") for k in keys), keys


def test_empty_state_below_two_institutions():
    at = _app(basket=[STRASBOURG]).run()
    assert not at.exception, [str(e) for e in at.exception]
    infos = " ".join(i.value for i in at.info)
    assert _first_literal(copy.COMPARE["EMPTY_TOO_FEW"]) in infos
    assert not at.get("plotly_chart"), "a single institution must not draw a comparison"


# ------------------------------------------------------------ the cap (4) --

def test_the_comparison_caps_at_three_and_says_how_many_it_left_out():
    at = _app(basket=SIX).run()
    assert not at.exception, [str(e) for e in at.exception]
    assert state.COMPARE_CAP == 3 and state.BASKET_CAP > state.COMPARE_CAP
    warnings = " ".join(w.value for w in at.warning)
    assert _first_literal(copy.COMPARE["CAP_TRUNCATED"]) in warnings, warnings
    codes = [c.value for c in at.get("code")]
    assert selection.deeplink("compare", SIX[:state.COMPARE_CAP]) in codes, codes
    # the basket itself is untouched: the cap is a display rule, not a deletion
    assert at.session_state["basket"] == list(SIX)


def test_an_over_cap_deep_link_truncates_with_a_rendered_reason():
    """The live `?compare=` path, patched at `lib.selection.read_query`
    (AppTest on Streamlit 1.61.1 exposes no query-param API); the browser path
    is covered end to end by ops/_probe_compare.py."""
    fake = {"compare": list(SIX), "pair": None, "dropped": []}
    with mock.patch.object(selection, "read_query", lambda known: fake):
        at = _app(basket=[]).run()
    assert not at.exception, [str(e) for e in at.exception]
    assert at.session_state["basket"] == SIX[:state.BASKET_CAP]
    warnings = " ".join(w.value for w in at.warning)
    assert _first_literal(copy.COMPARE["CAP_TRUNCATED"]) in warnings, warnings
    assert _cards(at) == state.COMPARE_CAP * len(
        views_compare._card_facts(None, views_compare._overview(tuple(TRIO)).iloc[0]))


# ------------------------------------------------- the overview cards (7) --

def test_every_overview_card_value_reads_back_from_compare_data(engine):
    """2B-R-7: the cards are a rendering of `compare_data.overview` and nothing
    else -- recompute the frame and match every rendered card value.

    2B-R2-9 changed the CARRIER (markup, not `st.metric`, so the leader dot can
    sit beside the value) and not the contract: label and value must still both
    be on the card, together, for every measure of every institution."""
    ctx, _subs = engine
    at = _app(basket=TRIO).run()
    frame = compare_data.overview(ctx, TRIO).set_index("institution_id")
    blocks = [m.value for m in at.markdown if tiles.TILE_CLASS in m.value]
    assert len(blocks) == len(TRIO) * len(views_compare.CARD_COLUMNS), len(blocks)
    for iid in TRIO:
        cell = frame.loc[iid]
        for _col, label, value, _tip in views_compare._card_facts(
                ctx["index_by_id"].loc[iid], cell):
            assert any(label in b and value in b for b in blocks), (iid, label, value)
    # ... and the two 2B-R-7 facts are real, not the pre-co-publication n/a
    for iid in TRIO:
        assert 0.0 <= float(frame.loc[iid, "intl_share"]) <= 1.0
        assert 0.0 <= float(frame.loc[iid, "company_share"]) <= 1.0


def test_the_cards_carry_no_interval_line_and_no_publications_button():
    """2B-R2-9's two deletions, checked as deletions. The interval STRING that
    used to sit under the PP value is gone from the strip, and the separate
    "Publications" link button is gone from every card -- both because the
    institution name now carries that link and the impact panel carries the
    intervals."""
    at = _app().run()
    labels = [b.label for b in at.button]
    assert copy.COMPARE["STRIP_LINK_PUBS"] not in labels, labels
    # the interval STRING itself -- "[x-y]" -- is what left the cards; the
    # coverage SENTENCE stays on the impact panels, where the intervals are
    # drawn, so the check is on the rendered range and not on the words.
    frame = views_compare._overview(tuple(TRIO)).set_index("institution_id")
    cards = " ".join(m.value for m in at.markdown if tiles.TILE_CLASS in m.value)
    for iid in TRIO:
        cell = frame.loc[iid]
        rendered_interval = copy.FIND["KPI_PP_VALUE_CI"].format(
            lo=views_compare._pct(cell["ci_low"]), hi=views_compare._pct(cell["ci_high"]),
            dash=views_compare.DASH)
        assert rendered_interval not in cards, (iid, rendered_interval)


def test_the_interval_coverage_sentence_is_the_methods_page_one():
    """2B-R-12: stated beside every interval, from METHODS_FAISCEAU through
    `copy.IMPACT_CI_CAPTION`, filled by the Methods page's own values.

    2B-R2-9 moved it OFF the cards (which no longer print an interval) and left
    it on BOTH impact panels, where the intervals are actually drawn -- inside
    the chart note's tooltip, per 2B-R2-8."""
    from lib import views_methods

    values = views_methods.methods_values()
    expected = copy.IMPACT_CI_CAPTION.format(ci_coverage=values["ci_coverage"],
                                             n_bootstrap=values["n_bootstrap"])
    assert views_compare._ci_sentence() == expected
    at = _app().run()
    assert _markdown(at).count(expected) >= 2, "the coverage is not stated beside both intervals"


# ------------------------------------------------ the metric selector (5) --

def test_each_level_offers_exactly_the_metrics_the_data_can_serve():
    at = _app().run()
    offered = {r.key: list(r.options) for r in at.get("radio")}
    for key, level, metrics in (("cmp_metric_subject", "field", views_compare.SUBJECT_METRICS),
                                ("cmp_metric_erc", "erc", views_compare.ERC_METRICS),
                                ("cmp_metric_sdg", "sdg", views_compare.SDG_METRICS)):
        expected = [views_compare.METRIC_LABELS[m] for m in metrics
                    if compare_data.metric_frame_available(m, level)]
        assert offered[key] == expected, (key, offered[key], expected)
    # the ERC and SDG sections really do hide something -- otherwise the
    # "hidden with a reason" contract below is vacuous
    assert any(not compare_data.metric_frame_available(m, "erc")
               for m in views_compare.SUBJECT_METRICS)


def test_a_hidden_metric_carries_the_frames_own_reason():
    """2B-R2-8/13: the header and the line are `copy.SHARED`'s -- the SAME two
    strings the Collaborate page uses for the same situation -- and the reason
    is the frame's own plain-language sentence."""
    at = _app().run()
    text = _captions(at)
    assert copy.SHARED["NOT_OFFERED_HEADER"] in text
    hidden = [m for m in views_compare.SUBJECT_METRICS
              if not compare_data.metric_frame_available(m, "sdg")]
    assert hidden
    for m in hidden:
        line = views_compare._not_offered_line(
            views_compare.METRIC_LABELS[m], compare_data.UNAVAILABLE_REASON[(m, "sdg")])
        assert line in text, m
    # a reason that already opens with the measure's own name is not printed
    # twice -- the live page read "Volume: Volume: shown in the chart gutter"
    assert views_compare._not_offered_line(
        "Volume", "Volume: shown in the chart gutter instead of as a tab."
    ) == "Volume: shown in the chart gutter instead of as a tab."
    at2 = _app().run()
    assert "Volume: Volume" not in _captions(at2)


def test_the_top_decile_volume_is_not_a_tab_any_more():
    """2B-R2-3: `vol_top10` is retired as a SELECTOR option at every level (its
    mass rides in the PP view's gutter and hover instead) -- while remaining a
    metric the builder and the data frame still know, which is the distinction
    the 2B-R2-1b crash class was about."""
    at = _app().run()
    label = views_compare.METRIC_LABELS["vol_top10"]
    for r in at.get("radio"):
        assert label not in list(r.options), (r.key, r.options)
    assert "vol_top10" not in views_compare.SUBJECT_METRICS
    assert "vol_top10" in compare_data.METRICS and "vol_top10" in charts_compare.METRICS
    # and the field-level frame still carries that mass, for the PP gutter
    frame = views_compare._metric(tuple(TRIO), TREE, BASIS, "field", "pp", None,
                                  views_compare.IMPACT_FLOOR_DEFAULT)
    assert frame["vol_top10"].notna().any()


def test_switching_the_subject_metric_redraws_the_page():
    at = _app().run()
    before = len(at.get("plotly_chart"))
    at.radio(key="cmp_metric_subject").set_value(
        views_compare.METRIC_LABELS["si"]).run()
    assert not at.exception, [str(e) for e in at.exception]
    assert len(at.get("plotly_chart")) == before
    assert at.session_state["cmp_metric_subject"] == views_compare.METRIC_LABELS["si"]
    # SI is the one metric with a constant reference, and its floor sentence is
    # only rendered on that metric -- inside the chart note's tooltip (2B-R2-8)
    assert _first_literal(copy.FIND["CAPTION_SI"]) in _markdown(at)


def test_every_selector_option_renders_at_every_level():
    """The 2B-R lesson, pinned: an option the selector OFFERS must reach a
    render, or the crash lives on a path no test drives. Every option of every
    section is set here, one after another, including the subfield drill."""
    at = _app().run()
    for key, level in (("cmp_metric_subject", "field"), ("cmp_metric_erc", "erc"),
                       ("cmp_metric_sdg", "sdg")):
        options = list(at.radio(key=key).options)
        assert options, key
        for label in options:
            at.radio(key=key).set_value(label).run()
            assert not at.exception, (key, label, [str(e) for e in at.exception])
            assert len(at.get("plotly_chart")) >= 8, (key, label)
    field_id = int(sorted(views_compare._fields(tuple(TRIO), TREE, BASIS)["field_id"].unique())[0])
    at.selectbox(key="cmp_field_drill").set_value(field_id).run()
    for label in list(at.radio(key="cmp_metric_subject").options):
        at.radio(key="cmp_metric_subject").set_value(label).run()
        assert not at.exception, ("subfield", label, [str(e) for e in at.exception])


def test_drilling_into_a_field_switches_the_level_and_clamps_a_retired_metric():
    """`pp` exists at field grain and NOT at subfield grain (impact_fields is
    field-grain this phase). Picking it and then drilling must clamp to an
    available option instead of raising on a session value Streamlit cannot
    place in the option list."""
    at = _app().run()
    at.radio(key="cmp_metric_subject").set_value(views_compare.METRIC_LABELS["pp"]).run()
    assert not at.exception, [str(e) for e in at.exception]
    field_id = int(sorted(views_compare._fields(tuple(TRIO), TREE, BASIS)["field_id"].unique())[0])
    at.selectbox(key="cmp_field_drill").set_value(field_id).run()
    assert not at.exception, [str(e) for e in at.exception]
    assert not compare_data.metric_frame_available("pp", "subfield")
    assert at.session_state["cmp_metric_subject"] in [
        views_compare.METRIC_LABELS[m] for m in views_compare.SUBJECT_METRICS
        if compare_data.metric_frame_available(m, "subfield")]
    assert _first_literal(copy.COMPARE["CAPTION_DRILL"]) in _markdown(at)


def test_the_dynamics_view_names_both_windows(engine):
    """2B-R-6: both windows named everywhere. The caption is the FRAME's own
    denominator note, so the page cannot name one window and the data another."""
    ctx, subs = engine
    df = compare_data.metric_frame(ctx, subs, TRIO, "field", "dynamics")
    note = str(df["denominator"].iloc[0])
    for bounds in (compare_data.DYNAMICS_W1, compare_data.DYNAMICS_W2):
        assert f"{bounds[0]}" in note and f"{bounds[1]}" in note, (bounds, note)
    at = _app().run()
    at.radio(key="cmp_metric_subject").set_value(
        views_compare.METRIC_LABELS["dynamics"]).run()
    assert not at.exception, [str(e) for e in at.exception]
    assert note in _markdown(at)


def _row_labels(df, metric, slots, sort="taxonomy", level="field"):
    fig = charts_compare.fig_metric_bars(
        views_compare._order_rows(df), metric, list(slots), slots=slots,
        names={i: i for i in slots}, level=level, sort=sort)
    return [str(t) for t in fig.layout.yaxis.ticktext]


def test_the_row_order_is_stable_across_metric_tabs(engine):
    """2B-R2-5, the property the whole taxonomy order exists for: switch the
    measure and every row stays where it was, so two tabs can be read against
    each other. Checked on the ROWS THE BUILDER DRAWS, not on the frame, and on
    three metrics whose producers order their own output differently."""
    ctx, subs = engine
    slots = {iid: n for n, iid in enumerate(TRIO)}
    orders = {}
    for metric in ("share", "dynamics", "sdg_share"):
        df = compare_data.metric_frame(ctx, subs, TRIO, "field", metric)
        rows = views_compare._order_rows(df)
        orders[metric] = rows.drop_duplicates("taxon_id")["taxon_id"].tolist()
    base = orders["share"]
    assert len(base) > 5, base
    for metric, order in orders.items():
        common = [t for t in base if t in set(order)]
        assert common == [t for t in order if t in set(base)], metric
        assert len(common) > 5, (metric, len(common))
    # ... and the drawn labels agree with that, metric to metric
    a = _row_labels(compare_data.metric_frame(ctx, subs, TRIO, "field", "share"),
                    "share", slots)
    b = _row_labels(compare_data.metric_frame(ctx, subs, TRIO, "field", "dynamics"),
                    "dynamics", slots)
    strip = lambda s: s.split(charts_compare.C.TICK_LABEL_GAP)[0]  # noqa: E731
    assert [strip(x) for x in a] == [strip(x) for x in b]


def test_the_sort_toggle_reranks_and_moves_no_value(engine):
    """The other half of 2B-R2-5: `value` really does re-rank, and ordering is
    ORDER ONLY -- same rows, same numbers, in both modes."""
    ctx, subs = engine
    slots = {iid: n for n, iid in enumerate(TRIO)}
    raw = compare_data.metric_frame(ctx, subs, TRIO, "field", "share")
    ordered = views_compare._order_rows(raw)
    assert len(ordered) == len(raw)
    key = ["institution_id", "taxon_id"]
    assert (ordered.sort_values(key).reset_index(drop=True)["value"].round(12).tolist()
            == raw.sort_values(key).reset_index(drop=True)["value"].round(12).tolist())
    by_taxonomy = _row_labels(raw, "share", slots, sort="taxonomy")
    by_value = _row_labels(raw, "share", slots, sort="value")
    assert set(by_taxonomy) == set(by_value)
    assert by_taxonomy != by_value, "the sort toggle changed nothing"


def test_the_sort_toggle_is_offered_per_section_and_defaults_to_taxonomy():
    at = _app().run()
    keys = {r.key: list(r.options) for r in at.get("radio")}
    for key in ("cmp_sort_subject", "cmp_sort_erc", "cmp_sort_sdg"):
        assert keys[key] == [views_compare.SORT_LABELS[m] for m in charts_compare.SORT_MODES], key
        assert at.session_state[key] == views_compare.SORT_LABELS[views_compare.SORT_DEFAULT]
    at.radio(key="cmp_sort_subject").set_value(
        views_compare.SORT_LABELS["value"]).run()
    assert not at.exception, [str(e) for e in at.exception]
    assert at.session_state["cmp_sort_subject"] == views_compare.SORT_LABELS["value"]


def test_the_erc_and_sdg_frames_carry_their_label_accent_key(engine):
    """2B-R-8: taxonomy colour on LABELS, never on marks -- which needs the
    accent key joined back onto a metric frame that ships six columns."""
    ctx, subs = engine
    erc = views_compare._decorate(compare_data.metric_frame(ctx, subs, TRIO, "erc", "share"),
                                  "erc", views_compare._erc(tuple(TRIO)), "panel_idx")
    assert views_compare.ACCENT_KEY["erc"] in erc.columns
    assert erc[views_compare.ACCENT_KEY["erc"]].notna().all()
    sdg = views_compare._decorate(compare_data.metric_frame(ctx, subs, TRIO, "sdg", "share"),
                                  "sdg", views_compare._sdg(tuple(TRIO)), "sdg_idx",
                                  label_col="sdg_label_numbered")
    assert views_compare.ACCENT_KEY["sdg"] in sdg.columns
    assert sdg[views_compare.ACCENT_KEY["sdg"]].notna().all()
    # and the numbered goal label survived the join (the number IS the encoding,
    # 2B-R-8: two of the UN hues are near-identical, so the colour is only
    # recognition on top of it)
    numbered = set(views_compare._sdg(tuple(TRIO))["sdg_label_numbered"])
    assert set(sdg["taxon_label"]) <= numbered and len(numbered) > 1


# ---------------------------------------------------------- frontier (9) ---

def test_the_leader_dot_marks_one_card_per_measure(engine):
    """2B-R2-9: the dot is drawn in the LEADING institution's own colour, on the
    measure it leads, and on nothing else. A tie draws no dot -- the dot's claim
    is "this one leads", which two level institutions do not support."""
    ctx, _subs = engine
    frame = views_compare._overview(tuple(TRIO))
    leaders = views_compare._leaders(frame)
    assert leaders, "no leader on any measure -- the dot would never be drawn"
    cells = frame.set_index("institution_id")
    for column, iid in leaders.items():
        best = pd.to_numeric(cells[column], errors="coerce").max()
        assert float(cells.loc[iid, column]) == pytest.approx(float(best))
    slots = views_compare._slots(ctx, TRIO)
    at = _app().run()
    text = _markdown(at)
    for column, iid in leaders.items():
        dot = charts_compare.best_value_dot(slots[iid])
        assert dot in text, (column, iid)
    assert text.count("border-radius:") >= len(leaders)
    # a tie yields nothing, tested on a frame that is level by construction
    tied = pd.DataFrame({"institution_id": list(TRIO[:2])}
                        | {c: [1.0, 1.0] for c in views_compare.CARD_COLUMNS})
    assert views_compare._leaders(tied) == {}


def test_the_institution_name_is_the_openalex_link():
    """2B-R2-9: the name IS the link (the same fragment-carrying builder the
    Find profile and the benchmark tables use), which is what let the separate
    Publications button go."""
    from lib.ranked import works_link_named

    at = _app().run()
    text = _markdown(at)
    ctx = views_compare._bundle()["ctx"]
    for iid in TRIO:
        name = views_compare._name(ctx, iid)
        assert f"]({works_link_named(iid, name)})" in text, iid


def test_the_frontier_slider_defaults_to_the_measured_value_and_caps_the_frame():
    at = _app().run()
    slider = at.slider(key="cmp_frontier_topn")
    assert slider.value == views_compare.FRONTIER_TOPN_DEFAULT == 60
    pooled = views_compare._frontier_pooled(tuple(TRIO), TREE, BASIS, int(slider.value))
    assert 0 < len(pooled) <= int(slider.value)
    at.slider(key="cmp_frontier_topn").set_value(views_compare.FRONTIER_TOPN_MIN).run()
    assert not at.exception, [str(e) for e in at.exception]
    smaller = views_compare._frontier_pooled(tuple(TRIO), TREE, BASIS,
                                             views_compare.FRONTIER_TOPN_MIN)
    assert len(smaller) < len(pooled)


def test_the_shared_frontier_melt_loses_no_volume():
    wide = views_compare._shared_frontier(tuple(TRIO), TREE, BASIS)
    long = views_compare._shared_long(wide, TRIO)
    assert not long.empty
    assert (long["vol"] > 0).all(), "a side that holds nothing must not get a zero-length bar"
    summed = long.groupby("topic_id")["vol"].sum()
    combined = wide.set_index("topic_id")["combined_vol"]
    for topic, total in summed.items():
        # rel, not abs: the volumes are float32 in the artefact and the wide
        # frame sums them in a different order than the melt does
        assert total == pytest.approx(float(combined.loc[topic]), rel=1e-6), topic
    assert set(long["institution_id"]) <= set(TRIO)


def test_the_frontier_note_counts_the_shared_topics_from_the_data():
    at = _app().run()
    pooled = views_compare._frontier_pooled(tuple(TRIO), TREE, BASIS,
                                            views_compare.FRONTIER_TOPN_DEFAULT,
                                            views_compare.POOL_DEFAULT)
    n_shared = int((pooled["owner"] == charts_compare.SHARED_OWNER).sum())
    line = copy.COMPARE["NOTE_FRONTIER_MAP"].format(
        n_shared=f"{n_shared:,}", n_shown=f"{len(pooled):,}")
    assert line in _markdown(at), line


def test_the_frontier_pool_selector_narrows_the_topic_set():
    """2B-R2-10: the elite pool is a STRICT subset of the default one (the cut
    is global, so it does not move with the basket), and picking it redraws the
    page without exception."""
    at = _app().run()
    assert list(at.radio(key="cmp_frontier_pool").options) == [
        views_compare.POOL_LABELS[p] for p in compare_data.FRONTIER_POOLS]
    # UNCAPPED on both sides: the subset claim is about the POOL, and two
    # different top-N cuts of two different rankings need not nest.
    uncapped = 10 ** 6
    wide = views_compare._frontier_pooled(tuple(TRIO), TREE, BASIS, uncapped, "volume")
    elite = views_compare._frontier_pooled(tuple(TRIO), TREE, BASIS, uncapped, "elite")
    assert not elite.empty
    assert set(elite["topic_id"]) <= set(wide["topic_id"])
    assert len(elite) < len(wide)
    at.radio(key="cmp_frontier_pool").set_value("elite").run()
    assert not at.exception, [str(e) for e in at.exception]
    assert copy.COMPARE["FRONTIER_POOL_RULE_ELITE"] in _markdown(at)


def test_the_colour_toggle_rebuilds_the_frontier_legend():
    """2B-R2-10: colouring by broad subject area REPLACES the ownership reading,
    legend included -- in that mode no mark means an institution, so a legend
    naming the institutions would name a figure that is not on screen."""
    at = _app().run()
    assert list(at.radio(key="cmp_frontier_color").options) == [
        views_compare.COLOR_BY_LABELS[c] for c in charts_compare.COLOR_BY]
    pooled = views_compare._frontier_pooled(tuple(TRIO), TREE, BASIS,
                                            views_compare.FRONTIER_TOPN_DEFAULT,
                                            views_compare.POOL_DEFAULT)
    items = views_compare._domain_items(pooled)
    assert items and all(isinstance(label, str) and label for _d, label in items)
    at.radio(key="cmp_frontier_color").set_value("domain").run()
    assert not at.exception, [str(e) for e in at.exception]
    text = _markdown(at)
    for _did, label in items:
        assert label in text, label


# -------------------------------------------------------------- legends ----

def test_a_legend_strip_sits_above_every_chart(engine):
    ctx, _subs = engine
    at = _app().run()
    slots = views_compare._slots(ctx, TRIO)
    names = views_compare._names(ctx, TRIO)
    plain = charts_compare.legend_strip(views_compare._slot_order(TRIO, slots),
                                        slots=slots, names=names)
    shared = charts_compare.legend_strip(views_compare._slot_order(TRIO, slots),
                                         slots=slots, names=names, shared=True,
                                         shared_label=copy.COMPARE["LEGEND_SHARED"])
    rendered = [m.value for m in at.markdown]
    n_legends = rendered.count(plain) + rendered.count(shared)
    assert n_legends >= len(at.get("plotly_chart")), (n_legends, len(at.get("plotly_chart")))
    assert rendered.count(shared) >= 1, "the frontier map needs the shared chip"


# ------------------------------------------------------------- frames ------

def test_coverage_states_are_exhaustive_per_institution():
    df = views_compare._coverage(tuple(TRIO))
    assert set(df["state"]) == set(views_compare._state_labels())
    for iid, total in df.groupby("institution_id")["share"].sum().items():
        assert total == pytest.approx(1.0, abs=1e-9), (iid, total)


def test_the_trends_measure_is_institution_normalised():
    df = views_compare._trends(FREIBURG, TREE, BASIS)
    assert views_compare.TRENDS_VALUE_COL in df.columns
    per_year = df.groupby("year")[views_compare.TRENDS_VALUE_COL].sum()
    assert len(per_year) > 1
    for year, total in per_year.items():
        assert total == pytest.approx(1.0, abs=1e-6), (year, total)


def test_impact_union_carries_a_missing_cell_at_the_high_floor():
    union = views_compare._impact_subfields(tuple(TRIO), TREE,
                                            views_compare.IMPACT_FLOOR_DEFAULT)
    assert not union.empty
    assert union["pp"].isna().any(), "no missing cell -- this is not a union frame"
    # A MISSING cell is NaN across the whole row (BUILD_PLAN_2A L11: n/a is
    # never 0). A genuine measured zero is legal and must NOT be read as
    # missing, which is why the test asks about the row and not about the value.
    missing = union[union["n_works_full"].isna()]
    assert len(missing)
    assert missing[["pp", "ci_low", "ci_high"]].isna().all().all()


def test_the_floor_toggle_changes_both_the_union_and_the_rows_drawn():
    high, low = views_compare.IMPACT_FLOORS
    assert high > low
    union_high = views_compare._impact_subfields(tuple(TRIO), TREE, high)
    union_low = views_compare._impact_subfields(tuple(TRIO), TREE, low)
    assert union_low["subfield_id"].nunique() > union_high["subfield_id"].nunique()
    top = views_compare._top_shared(tuple(TRIO), TREE, BASIS, views_compare.IMPACT_ROWS_TOP_N)
    shown_high = views_compare._impact_rows(union_high, top)
    shown_low = views_compare._impact_rows(union_low, top)
    # the drawn ROW SET is capped at the same cut, so what the lower floor buys
    # is MEASURED CELLS inside those rows -- fewer n/a marks, wider intervals
    assert shown_low["pp"].notna().sum() > shown_high["pp"].notna().sum(), (
        shown_high["pp"].notna().sum(), shown_low["pp"].notna().sum())


# ------------------------------------------------------------- selection ---

def test_removing_an_institution_shrinks_the_comparison():
    at = _app(basket=TRIO).run()
    at.button(key=f"cmp_rm_{SORBONNE}").click().run()
    assert not at.exception, [str(e) for e in at.exception]
    assert SORBONNE not in at.session_state["basket"]
    codes = [c.value for c in at.get("code")]
    assert selection.deeplink("compare", [i for i in TRIO if i != SORBONNE]) in codes


def test_the_scenario_widgets_use_the_find_page_keys():
    at = _app().run()
    assert {"tree", "basis"} <= {sb.key for sb in at.selectbox}


def test_the_pair_handoff_button_seeds_session_state_pair_without_crashing():
    at = _app().run()
    assert "pair" not in at.session_state
    at.button(key="cmp_handoff_open").click().run()
    assert not at.exception, [str(e) for e in at.exception]
    assert tuple(at.session_state["pair"]) == (STRASBOURG, SORBONNE)


def test_the_snapshot_string_is_gone_from_this_page():
    """2B-R-12: removed app-wide. The page states how big the index is and how
    old the data is, both computed."""
    at = _app().run()
    text = _captions(at) + " ".join(m.value for m in at.markdown)
    assert "napshot" not in text, [c.value for c in at.caption if "napshot" in c.value]
    assert _first_literal(copy.FIND["DATA_CAPTION"].replace("{n_institutions}", "")) in text


# ------------------------------------------------------------- workbook ----

def _frames_for(ids) -> dict:
    return {
        "overview": views_compare._overview(tuple(ids)),
        "subject": views_compare._metric(tuple(ids), TREE, BASIS, "field", "share", None,
                                         views_compare.IMPACT_FLOOR_DEFAULT),
        "erc": views_compare._metric(tuple(ids), TREE, BASIS, "erc", "share", None,
                                     views_compare.IMPACT_FLOOR_DEFAULT),
        "sdg": views_compare._metric(tuple(ids), TREE, BASIS, "sdg", "share", None,
                                     views_compare.IMPACT_FLOOR_DEFAULT),
        "frontier_map": views_compare._frontier_pooled(
            tuple(ids), TREE, BASIS, views_compare.FRONTIER_TOPN_DEFAULT),
        "shared_frontier": views_compare._shared_long(
            views_compare._shared_frontier(tuple(ids), TREE, BASIS), list(ids)),
        "impact": views_compare._impact_index(tuple(ids)),
        "impact_subfields": views_compare._impact_subfields(
            tuple(ids), TREE, views_compare.IMPACT_FLOOR_DEFAULT),
        "trends": views_compare._trends(ids[0], TREE, BASIS),
        "coverage": views_compare._coverage(tuple(ids)),
    }


METRICS_STATE = {"level": "field", "subject": "share", "erc": "share", "sdg": "share"}


def test_workbook_opens_with_openpyxl_and_carries_every_view(engine):
    import openpyxl

    ctx, _subs = engine
    sheets = views_compare.sheet_specs(SCENARIO, _frames_for(TRIO), METRICS_STATE)
    raw = views_compare._workbook(ctx, list(TRIO), SCENARIO,
                                  views_compare.IMPACT_FLOOR_DEFAULT,
                                  views_compare.FRONTIER_TOPN_DEFAULT, sheets)
    assert isinstance(raw, bytes) and raw[:2] == b"PK", "not a zip container, so not an xlsx"
    book = openpyxl.load_workbook(io.BytesIO(raw))
    expected = [copy.COMPARE["XLSX_SHEET_METHODS"]] + [label for label, _c, _f in sheets]
    assert book.sheetnames == expected, book.sheetnames
    assert len(sheets) == len(views_compare.SLUGS), (len(sheets), len(views_compare.SLUGS))
    methods = book[copy.COMPARE["XLSX_SHEET_METHODS"]]
    values = [str(c.value) for row in methods.iter_rows() for c in row if c.value is not None]
    for label, caption, _frame in sheets:
        assert label in values and caption in values, label
    header = [c.value for c in next(book[copy.COMPARE["XLSX_SHEET_OVERVIEW"]].iter_rows())]
    assert header == list(views_compare._overview(tuple(TRIO)).columns)


def test_the_methods_sheet_records_the_controls_the_reader_was_on(engine):
    """2B-R2-5/10: the workbook names the row order, the frontier pool and the
    colour mode. A file that named the metric of each selector but not the pool
    its frontier sheet was cut from would describe a view nobody saw."""
    ctx, _subs = engine
    controls = {"pool": "elite", "color_by": "domain", "sort": "value"}
    rows = views_compare.methods_rows(ctx, list(TRIO), SCENARIO,
                                      views_compare.IMPACT_FLOOR_DEFAULT,
                                      views_compare.FRONTIER_TOPN_DEFAULT, [], controls)
    items = list(rows[copy.COMPARE["XLSX_COL_ITEM"]])
    values = list(rows[copy.COMPARE["XLSX_COL_VALUE"]])
    for key in ("XLSX_ROW_POOL", "XLSX_ROW_COLOUR", "XLSX_ROW_SORT"):
        assert copy.COMPARE[key] in items, key
    assert views_compare.POOL_LABELS["elite"] in values
    assert views_compare.COLOR_BY_LABELS["domain"] in values
    assert views_compare.SORT_LABELS["value"] in values
    # ... and the defaults stand in when the page passes nothing
    plain = views_compare.methods_rows(ctx, list(TRIO), SCENARIO,
                                       views_compare.IMPACT_FLOOR_DEFAULT,
                                       views_compare.FRONTIER_TOPN_DEFAULT, [])
    assert views_compare.POOL_LABELS[views_compare.POOL_DEFAULT] in list(
        plain[copy.COMPARE["XLSX_COL_VALUE"]])


def test_every_reading_line_fits_the_one_line_rule():
    """2B-R2-8's enforcement, read back over this page's OWN copy: every `NOTE_*`
    key must survive `charts_compare.chart_note`, which raises on a line break
    or on a line over its cap. A wall of prose cannot come back as a "note"."""
    notes = {k: v for k, v in copy.COMPARE.items()
             if k.startswith("NOTE_") and isinstance(v, str)}
    assert len(notes) >= 6, notes.keys()
    for key, template in notes.items():
        filled = re.sub(r"\{[^{}]*\}", "0", template)
        rendered = charts_compare.chart_note(filled, "a tooltip")
        assert charts_compare.NOTE_HELP_GLYPH in rendered, key


def test_the_methods_sheet_states_the_windows_the_floor_and_the_cap(engine):
    ctx, _subs = engine
    rows = views_compare.methods_rows(ctx, list(TRIO), SCENARIO,
                                      views_compare.IMPACT_FLOOR_DEFAULT,
                                      views_compare.FRONTIER_TOPN_DEFAULT, [])
    assert list(rows.columns) == [copy.COMPARE["XLSX_COL_ITEM"], copy.COMPARE["XLSX_COL_VALUE"],
                                  copy.COMPARE["XLSX_COL_SOURCE"]]
    items = list(rows[copy.COMPARE["XLSX_COL_ITEM"]])
    for key in ("XLSX_ROW_DATA", "XLSX_ROW_WINDOW", "XLSX_ROW_DYNAMICS", "XLSX_ROW_TREE",
                "XLSX_ROW_BASIS", "XLSX_ROW_INSTITUTIONS", "XLSX_ROW_CAP", "XLSX_ROW_TOPN",
                "XLSX_ROW_FLOORS", "XLSX_ROW_CI", "XLSX_ROW_READING"):
        assert copy.COMPARE[key] in items, key
    assert copy.COMPARE["XLSX_ROW_SNAPSHOT"] not in items, "2B-R-12 removed the snapshot row"
    values = " ".join(str(v) for v in rows[copy.COMPARE["XLSX_COL_VALUE"]])
    for bounds in (compare_data.DYNAMICS_W1, compare_data.DYNAMICS_W2):
        assert views_compare._window(bounds) in values, bounds
    assert views_compare._ci_sentence() in values


def test_workbook_filename_is_self_describing():
    name = views_compare.workbook_filename(TRIO, TREE, BASIS)
    assert name.endswith(".xlsx")
    for iid in TRIO:
        assert iid in name
    assert TREE in name and BASIS in name


def test_every_view_offers_its_own_csv_and_the_one_workbook():
    at = _app().run()
    labels = [d.label for d in at.get("download_button")]
    assert labels.count(copy.COMPARE["EXPORT_XLSX_BUTTON"]) == 1, labels
    assert labels.count(copy.COMPARE["DOWNLOAD_VIEW"]) == len(views_compare.SLUGS), labels


# ------------------------------------------------------------ digit ban ----

def test_no_digit_ban_violations_in_this_streams_files():
    from tests.test_narrative import collect_ui_call_strings, has_digit_violation, load_allowlist

    tokens = load_allowlist()
    files = [APP_DIR / "lib" / "views_compare.py", APP_DIR / "lib" / "exports_xlsx.py",
             Path(COMPARE_PAGE)]
    strings = [(loc, s) for f in files for loc, s in collect_ui_call_strings(f)]
    assert strings, "collector found no UI-call strings in this stream's files -- it is vacuous"
    violations = [(loc, s) for loc, s in strings if has_digit_violation(s, tokens)]
    assert not violations, violations


def test_the_new_compare_copy_keys_hold_no_typed_digit():
    """Scope (a) of the digit ban, narrowed to the keys this stream added: a
    number in a Compare string must arrive as a `{placeholder}` the page fills
    from the config, the frame or the constants."""
    from tests.test_narrative import has_digit_violation, load_allowlist

    tokens = load_allowlist()
    added = [k for k in copy.COMPARE if k.startswith(("METRIC_", "CAPTION_FRONTIER_",
                                                      "OVERVIEW_", "XLSX_ROW_", "DRILL_",
                                                      "VIEW_", "CAP_", "LEGEND_"))]
    assert added
    violations = [(k, copy.COMPARE[k]) for k in added
                  if isinstance(copy.COMPARE[k], str) and has_digit_violation(copy.COMPARE[k], tokens)]
    assert not violations, violations


def test_no_hex_colour_is_typed_in_this_page():
    import re

    source = (APP_DIR / "lib" / "views_compare.py").read_text(encoding="utf-8")
    hits = re.findall(r"#[0-9a-fA-F]{3}|#[0-9a-fA-F]{6}", source)
    assert not hits, hits


def test_the_page_module_is_thin():
    """The page file is page config + state + one render call; every decision
    lives in lib/views_compare.py, which is what lets AppTest and the probe
    drive the same code the deployed app runs."""
    source = Path(COMPARE_PAGE).read_text(encoding="utf-8")
    assert "views_compare.render()" in source
    assert "plotly" not in source and "pandas" not in source

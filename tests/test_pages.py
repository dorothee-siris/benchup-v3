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

from lib import copy, tiles

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


# ------------------------------------------------ Find: the R1 profile -----
# Refinement R1 (BUILD_PLAN_2A.md S9.2 L16-L22, stream R-E2): the seed card
# became a PROFILE section (header, 7 KPI tiles, coverage caption, wordcloud +
# yearly breakdown pair, six collapsed chart panels) and the benchmark controls
# moved out of the sidebar into a controls row at the head of the Benchmark
# section. Every selector below is state- or copy-driven, never a typed label.

STRASBOURG = "I68947357"   # the gate-2A drive seed; the R1 reference seed

# Widget keys L16 froze: the controls MOVED but were NOT renamed, which is the
# whole reason the move was cheap (the smoke suite's selectors survive it).
CONTROLS_ROW_KEYS = ("depth", "c1_on", "l7_on")
POST_FILTER_KEYS = ("f_types", "f_countries", "f_excl_own", "f_size", "f_guard", "f_family")


def test_find_profile_section_renders_header_and_seven_tiles():
    """L17 blocks 1-2: the profile section holds the seed's name and exactly
    seven KPI tiles. AppTest exposes no container element type (see
    test_menu_has_at_least_three_nav_cards), so the tiles are counted by
    lib/tiles.py's own stable class hook, never by a user-facing string."""
    at = _find_app(seed_id=STRASBOURG).run()
    assert not at.exception, [str(e) for e in at.exception]
    headers = [h.value for h in at.header]
    assert copy.FIND["PROFILE_HEADER"] in headers, headers
    assert copy.FIND["BENCHMARK_HEADER"] in headers, headers
    rendered = [m.value for m in at.markdown if tiles.TILE_CLASS in m.value]
    assert len(rendered) == 7, len(rendered)
    for label_key in ("TILE_SIZE_FULL", "TILE_SIZE_FRAC", "TILE_HHI", "TILE_BREADTH",
                      "TILE_SDG", "TILE_FRONTIER", "TILE_PP"):
        assert any(copy.FIND[label_key] in html for html in rendered), label_key


def test_find_profile_has_wordcloud_image_and_breakdown_control():
    """L17 block 4: the wordcloud raster, and the ONE segmented control that
    swaps both breakdown figures between the domain and doc-type family."""
    at = _find_app(seed_id=STRASBOURG).run()
    assert not at.exception, [str(e) for e in at.exception]
    assert len(at.get("image")) >= 1, "the subfield wordcloud PNG did not render"
    controls = {s.key: s.value for s in at.segmented_control}
    assert "breakdown_dim" in controls, controls
    assert controls["breakdown_dim"] == copy.FIND["BREAKDOWN_DOMAIN"], controls


def test_find_six_chart_panels_are_expanders_in_the_ruled_order():
    """L17 block 5 / VIZ_SPEC S1.9: Fields, Top subfields, Top topics, Frontier
    positioning, SDG profile, ERC profile -- in that order -- plus the
    post-filters expander that heads the Benchmark section."""
    at = _find_app(seed_id=STRASBOURG).run()
    assert not at.exception, [str(e) for e in at.exception]
    labels = [e.label for e in at.expander]
    expected = [copy.FIND[k] for k in ("PANEL_FIELDS", "PANEL_SUBFIELDS", "PANEL_TOPICS",
                                       "PANEL_FRONTIER", "PANEL_SDG", "PANEL_ERC")]
    assert labels[:len(expected)] == expected, labels
    assert copy.FIND["POSTFILTERS_EXPANDER"] in labels, labels


def test_find_sidebar_holds_scenario_and_basket_only():
    """L16: depth, C1, L7 and every post-filter LEFT the sidebar. Asserted by
    element TYPE, so a copy edit cannot make it vacuous: depth was the sidebar's
    only radio and the post-filters its only multiselects and its only slider."""
    at = _find_app(seed_id=STRASBOURG).run()
    assert not at.exception, [str(e) for e in at.exception]
    assert len(at.sidebar.radio) == 0, [r.key for r in at.sidebar.radio]
    assert len(at.sidebar.multiselect) == 0, [m.key for m in at.sidebar.multiselect]
    assert len(at.sidebar.slider) == 0, [s.key for s in at.sidebar.slider]
    # ...and what DOES stay: the two scenario selectboxes (tree, basis).
    assert {s.key for s in at.sidebar.selectbox} >= {"tree", "basis"}, \
        [s.key for s in at.sidebar.selectbox]


def test_find_controls_row_keeps_the_same_widget_keys_in_the_main_area():
    """L16's cheapness claim, made falsifiable: the controls moved into the main
    area but every widget key is unchanged, so persist_state and the Playwright
    st-key-* selectors survive the move."""
    at = _find_app(seed_id=STRASBOURG).run()
    assert not at.exception, [str(e) for e in at.exception]
    main_keys = {w.key for w in (*at.radio, *at.checkbox, *at.multiselect, *at.slider)}
    for key in (*CONTROLS_ROW_KEYS, *POST_FILTER_KEYS):
        assert key in main_keys, (key, sorted(k for k in main_keys if k))


def test_find_renders_under_every_tree_and_the_fields_frame_follows_the_tree():
    """Toggle coherence: the page renders under a non-default tree, AND the
    Fields panel's own frame (profile_data.fields_table over that tree's
    substrates -- exactly what views_find._fields_frame caches) actually changes
    with the tree. Computed through the engine rather than scraped off the page,
    because the panel is a Plotly canvas."""
    at = _find_app(seed_id=STRASBOURG)
    at.session_state["tree"] = "original"
    at.run()
    assert not at.exception, [str(e) for e in at.exception]

    from lib import profile_data
    from lib.engine import build_substrates, load_context

    ctx = load_context(APP_DIR / "data")
    frames = {}
    for tree in ("original", "bestfit"):
        subs = build_substrates(ctx, tree, "frac")
        frames[tree] = profile_data.fields_table(ctx, subs, STRASBOURG).set_index("field_id")
    common = frames["original"].index.intersection(frames["bestfit"].index)
    assert len(common) > 0
    diff = (frames["original"].loc[common, "share"] - frames["bestfit"].loc[common, "share"]).abs()
    assert float(diff.max()) > 0, "the Fields frame is identical under original and bestfit"


def test_breakdown_pair_series_agree_on_every_year_total():
    """The invariant that makes ONE segmented control legitimate over TWO data
    sources (BUILD_PLAN_2A.md S9.7, the "Unclassified" residual decision): the
    domain view and the document-type view must sum to the SAME volume per year,
    or the swap would read as a bug. Recomputed from the two sources the page
    reads, not from the page."""
    from lib import profile_data
    from lib.data_cache import doctype_by_year
    from lib.engine import load_context

    ctx = load_context(APP_DIR / "data")
    domain = profile_data.yearly_by_domain(ctx, STRASBOURG, "bestfit")
    dt = doctype_by_year()
    dt = dt[dt["institution_id"] == STRASBOURG]
    assert not domain.empty and not dt.empty

    dom_full = domain.groupby("year")["vol_full"].sum()
    dt_full = dt.groupby("year", observed=True)["vol_full"].sum()
    assert sorted(dom_full.index) == sorted(dt_full.index), (list(dom_full.index),
                                                             list(dt_full.index))
    for year in dom_full.index:
        assert abs(float(dom_full[year]) - float(dt_full[year])) < 1.0, (
            year, float(dom_full[year]), float(dt_full[year]))
        dom_frac = float(domain.loc[domain["year"] == year, "vol_frac"].sum())
        dt_frac = float(dt.loc[dt["year"] == year, "vol_frac"].sum())
        assert abs(dom_frac - dt_frac) <= 1e-3 * max(dom_frac, 1.0), (year, dom_frac, dt_frac)


def test_ranked_frame_carries_two_sizes_and_no_badge_column():
    """L22 on the frame the page actually renders: both counting bases as their
    own columns, the lens-specific evidence cell filled, and no badge column."""
    from lib.engine import build_rows, build_substrates, load_context, rank_all
    from lib.engine.evidence import rows_evidence
    from lib.ranked import format_rows

    ctx = load_context(APP_DIR / "data")
    subs = build_substrates(ctx, "bestfit", "frac")
    rankings = rank_all(ctx, subs, STRASBOURG)
    l1 = rankings["L1"]
    rows = build_rows(l1, ctx, 5, rankings, subs)
    texts = rows_evidence(ctx, subs, "L1", STRASBOURG, [r["institution_id"] for r in rows])
    for r in rows:
        r["evidence_text"] = texts.get(r["institution_id"])
    df = format_rows(rows, lens="L1", depth=5)
    assert {"size_full", "size_frac", "evidence"} <= set(df.columns), list(df.columns)
    assert "badge" not in df.columns, list(df.columns)
    assert (df["evidence"] != "n/a").any(), df["evidence"].tolist()

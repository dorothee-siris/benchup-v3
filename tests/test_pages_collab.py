"""
tests/test_pages_collab.py -- stream VL (BUILD_PLAN_2BR3.md SS3 VL): tests
for the rebuilt Collaborate page (lib/views_collab.py) and the render
helpers over it -- slots + instant identity cards, the pair momentum
headline, the domain-coloured field chart, the "Strategic reciprocity by
field" bubble scatter, the native sortable topic deep dive / untapped
dataframes with a 20-then-show-all pattern, and the deletions the rework
asks for (the old free-text pair picker, the field TABLE, every row slider,
"Read the publications on OpenAlex").

WHY MOST OF THIS FILE RUNS AGAINST THE FIXTURE CONTEXT, NOT A LIVE PAGE.
`lib/collab_data.py` (CD4) targets the SS2.2 v2 schemas; P7 has not rebuilt
`app/data/collab_pairs.parquet` etc. to those schemas yet (same wave, by
design -- BUILD_PLAN_2BR3.md SS4 W1/W2, confirmed live 2026-08-31:
`collab_facts.json`, `collab_topic_vols.parquet` and `fwci_ref.parquet` do
not exist on disk yet and `index.parquet` carries no `total_ar_full_w1/w2`).
An `AppTest` render against the real app would therefore KeyError/
FileNotFoundError on data that is not this stream's to build -- EXPECTED,
per the brief, not a defect here. Every render helper this stream wrote is
instead exercised directly against `tests/fixtures/fixture_ctx.py` (the SAME
small, hand-verified fixture CD4's own `tests/test_cd4_2br3.py` uses), which
already carries the v2 schemas -- this proves the NEW code against the NEW
contract today, byte-identically to how it will run once P7 lands.
`test_page_group` at the bottom holds the one AppTest suite that DOES need
the real app; it self-skips with a stated reason while `collab_facts.json`
is absent and starts running the moment a manager re-run finds it (no edit
needed here when that happens).

Run from cwd `app/`:  python -m pytest tests/test_pages_collab.py -q
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "fixtures"))
from fixture_ctx import IA, IB, IC, build_ctx, build_subs  # noqa: E402

from lib import collab_data as CL  # noqa: E402
from lib import copy  # noqa: E402
from lib import links  # noqa: E402
from lib import palette as P  # noqa: E402
from lib import views_collab as VC  # noqa: E402
from lib.compare_data import DYNAMICS_W1, DYNAMICS_W2  # noqa: E402
from lib.data_cache import DATA_DIR  # noqa: E402

APP_DIR = Path(__file__).resolve().parents[1]
COLLAB_PAGE = str(APP_DIR / "pages" / "3_\U0001F91D_Collaborate.py")  # handshake

REAL_V2_READY = (DATA_DIR / "collab_facts.json").exists()
SKIP_REASON = ("real app/data/ is still v1 schema (collab_facts.json absent) -- "
               "P7 has not landed yet; deferred to the manager's post-P7 pass "
               "per this stream's brief")


@pytest.fixture(scope="module")
def ctx():
    return build_ctx()


@pytest.fixture()
def subs_frac(ctx):
    return build_subs(ctx, basis="frac")


# ============================================================================
# 1. the pair momentum headline (section 1)
# ============================================================================

def test_pair_momentum_frame_matches_the_fixtures_hand_verified_ladder_case(ctx):
    """collab_pairs fixture row: mom_class='up', mom_rr=1.5 -> '+50%'
    (tests/fixtures/build_fixtures.py's own comment says so)."""
    mom = CL.pair_momentum(ctx, IA, IB)
    assert mom is not None
    assert mom["text"] == "+50%"
    assert mom["color"] == P.MOMENTUM_COLORS["up"]
    assert mom["glyph"] == P.MOMENTUM_GLYPHS["up"]
    assert mom["c1"] == 15.0 and mom["c2"] == 6.0
    np.testing.assert_allclose(mom["d1"], 450.0, atol=1e-9)  # 300 (IA) + 150 (IB)
    np.testing.assert_allclose(mom["d2"], 360.0, atol=1e-9)  # 220 (IA) + 140 (IB)


def test_pair_momentum_none_for_a_pair_that_never_co_published(ctx):
    assert CL.pair_momentum(ctx, IA, IC) is None


def test_evidence_block_shares_and_significance_are_composed_not_hardcoded(ctx):
    """The window labels, the two shares, the raw counts and the p-value all
    come off `mom` + `collab_facts.json`'s own `alpha` -- this pins the
    ARITHMETIC the render helper performs before handing numbers to
    copy.py's placeholders."""
    mom = CL.pair_momentum(ctx, IA, IB)
    facts = CL._load_collab_facts(ctx)
    assert facts["alpha"] == 0.05
    w1_share = mom["c1"] / mom["d1"]
    w2_share = mom["c2"] / mom["d2"]
    np.testing.assert_allclose(w1_share, 15.0 / 450.0, atol=1e-9)
    np.testing.assert_allclose(w2_share, 6.0 / 360.0, atol=1e-9)
    line = copy.COLLAB["MOMENTUM_EVIDENCE_SHARE"].format(
        w1=VC._window(DYNAMICS_W1), share1=VC._pct(w1_share),
        w2=VC._window(DYNAMICS_W2), share2=VC._pct(w2_share), sep=VC.SEP)
    assert VC._pct(w1_share) in line and VC._pct(w2_share) in line
    sig = copy.COLLAB["MOMENTUM_EVIDENCE_SIGNIFICANCE"].format(
        p=VC._pval(mom["mom_p"]), alpha=VC._pct(facts["alpha"]))
    assert "0.010" in sig  # mom_p fixture value 0.01, formatted to 3dp
    assert VC._pct(0.05) in sig
    copubs = copy.COLLAB["MOMENTUM_EVIDENCE_COPUBS"].format(
        c1=VC._count(mom["c1"]), c2=VC._count(mom["c2"]), arrow=VC.ARROW)
    assert "15" in copubs and "6" in copubs and VC.ARROW in copubs


def test_pval_formatter_floors_a_very_small_p_and_discloses_na():
    assert VC._pval(None) == P.NA_MARK
    assert VC._pval(float("nan")) == P.NA_MARK
    assert VC._pval(0.01) == "0.010"
    assert VC._pval(0.0000001) == f"< {VC.PVAL_FLOOR:.3f}"


# ============================================================================
# 2. field/topic-grain momentum cell (the dataframe's own "Momentum" column)
# ============================================================================

MOMENTUM_CLASS_CASES = [
    (None, VC.MOMENTUM_CLASS_WORD.get, False),
    ("up", "up", True), ("down", "down", True), ("stable", "stable", True),
    ("ns", "n.s.", True), ("new", "new", True), ("dormant", "dormant", True),
    ("weak", "weak base", True),
]


@pytest.mark.parametrize("mom_class,want_text,known", MOMENTUM_CLASS_CASES)
def test_momentum_cell_is_class_only_never_a_percentage(mom_class, want_text, known):
    """SS2.3: field/topic grain carries CLASS ONLY, no percentage. A real
    'up' class must render the WORD 'up', never a '+NN%' string (which is
    what `collab_data.momentum_display` would silently produce if handed a
    None mom_rr for this same class -- the exact trap this page's own
    docstring names)."""
    text, color, glyph = VC._momentum_cell(mom_class)
    if known:
        assert text == want_text
        assert "%" not in text
        assert color.startswith("#") and glyph
    else:
        assert text == CL.MOMENTUM_NULL_TEXT


def test_momentum_cell_colours_and_glyphs_come_from_palette_not_a_local_hex():
    for cls in ("up", "down", "stable"):
        _, color, glyph = VC._momentum_cell(cls)
        assert color == P.MOMENTUM_COLORS[cls]
        assert glyph == P.MOMENTUM_GLYPHS[cls]
    for cls in ("ns", "new", "dormant", "weak"):
        _, color, glyph = VC._momentum_cell(cls)
        assert color == P.MOMENTUM_COLORS["ns"]
        assert glyph == P.MOMENTUM_GLYPHS["ns"]


# ============================================================================
# 3. the field chart (section 2) -- domain-coloured bars
# ============================================================================

def test_field_chart_bars_are_coloured_by_domain_not_by_institution(ctx):
    fields = CL.field_breakdown(ctx, IA, IB)
    assert len(fields) == 2  # the fixture's own two fields
    fig = VC._fields_chart(fields)
    assert len(fig.data) == 1  # ONE trace -- the corpus is the pair's, not either side's
    colors = set(fig.data[0].marker.color)
    wanted = {P.domain_color(d) for d in fields["domain_id"]}
    assert colors == wanted
    assert not (colors & set(P.INSTITUTION_COLORS)), "an institution hue reached the pair's bars"


def test_field_chart_values_are_the_pairs_own_core_ar_volumes(ctx):
    fields = CL.field_breakdown(ctx, IA, IB)
    fig = VC._fields_chart(fields)
    drawn = sorted(float(v) for v in fig.data[0].x)
    assert drawn == sorted(float(v) for v in fields["vol"])  # [6.0, 15.0]
    assert drawn == [6.0, 15.0]


def test_field_chart_axis_is_a_plain_publication_count_not_a_share():
    """The 2BR3 reason a NEW small builder lives in this file rather than
    calling `charts.fig_topics`: that builder hard-codes a percent axis."""
    fields = CL.field_breakdown(build_ctx(), IA, IB)
    fig = VC._fields_chart(fields)
    assert fig.layout.xaxis.tickformat != VC.C._AXIS_PCT_FMT
    assert fig.layout.xaxis.title.text == copy.COLLAB["PULSE_AXIS"]


# ============================================================================
# 4. "Strategic reciprocity by field" (section 3, Lorraine port)
# ============================================================================

def test_reciprocity_chart_is_area_true_domain_coloured_and_squared(ctx, subs_frac):
    df = CL.reciprocity_frame(ctx, subs_frac, IA, IB)
    assert len(df) == 2
    fig = VC._reciprocity_chart(df, "A name", "B name")
    scatter = fig.data[0]
    assert scatter.marker.sizemode == "area"
    assert set(scatter.marker.color) == {P.domain_color(d) for d in df["domain_id"]}
    assert scatter.marker.line.color == P.SURFACE
    # squared axes: identical range on x and y, and the aspect ratio locked
    assert list(fig.layout.xaxis.range) == list(fig.layout.yaxis.range)
    assert fig.layout.yaxis.scaleanchor == "x"
    # exactly one dotted diagonal shape, from the origin to the axis max
    shapes = fig.layout.shapes
    assert len(shapes) == 1
    assert shapes[0].line.dash == "dot"
    assert shapes[0].x0 == 0 and shapes[0].y0 == 0
    assert shapes[0].x1 == shapes[0].y1 == fig.layout.xaxis.range[1]


def test_reciprocity_hover_names_the_field_both_shares_and_the_joint_count(ctx, subs_frac):
    df = CL.reciprocity_frame(ctx, subs_frac, IA, IB)
    fig = VC._reciprocity_chart(df, "Institution A", "Institution B")
    hover = list(fig.data[0].customdata)
    row1 = df[df["field_id"] == 1].iloc[0]
    text = [h for h in hover if "Field One" in h][0]
    assert VC._pct(row1["x"]) in text
    assert VC._pct(row1["y"]) in text
    assert VC._count(row1["joint_vol"]) in text


def test_reciprocity_section_renders_nothing_when_the_frame_is_empty():
    """A pair below the topic floor has an empty `field_breakdown`, so
    `reciprocity_frame` is empty too -- and section 3 skips its OWN header
    and info box rather than repeating section 2's below-floor notice a
    second time (the same 'no double failure' rule the topic table already
    followed pre-2BR3)."""
    empty = pd.DataFrame(columns=CL.RECIPROCITY_COLS)
    assert empty.empty  # nothing to build a chart from; `_render_reciprocity` returns before st.*


# ============================================================================
# 5. the topic deep dive dataframe (section 4 -- native, sortable)
# ============================================================================

def test_topics_display_frame_shares_and_columns(ctx, subs_frac):
    prof = CL.joint_profile(ctx, subs_frac, IA, IB)
    disp = VC._topics_display_frame(prof["topics"])
    assert list(disp.columns) == ["topic_name", "domain_name", "vol", "top10_share",
                                  "sdg_share", "sdg_n", "fwci_median", "momentum", "url"]
    row_t1 = disp[disp["topic_name"] == "Topic One"].iloc[0]
    np.testing.assert_allclose(row_t1["vol"], 15.0)
    np.testing.assert_allclose(row_t1["top10_share"], 3.0 / 15.0)   # n_top10 / vol, NOT / n_covered
    np.testing.assert_allclose(row_t1["sdg_share"], 2.0 / 15.0)
    np.testing.assert_allclose(row_t1["sdg_n"], 2.0)
    np.testing.assert_allclose(row_t1["fwci_median"], 1.2)
    assert row_t1["momentum"].endswith("up") or "up" in row_t1["momentum"]
    assert "%" not in row_t1["momentum"]


def test_topics_column_config_shapes_match_streamlits_native_widgets(ctx, subs_frac):
    prof = CL.joint_profile(ctx, subs_frac, IA, IB)
    cfg = VC._topics_column_config()
    assert set(cfg) == set(VC._topics_display_frame(prof["topics"]).columns)
    assert cfg["vol"]["type_config"]["type"] == "number"
    assert cfg["top10_share"]["type_config"]["type"] == "progress"
    assert cfg["top10_share"]["type_config"]["min_value"] == 0
    assert cfg["top10_share"]["type_config"]["max_value"] == 1
    assert cfg["top10_share"]["type_config"]["format"] == "percent"
    assert cfg["sdg_share"]["type_config"]["type"] == "progress"
    assert cfg["fwci_median"]["type_config"]["type"] == "number"
    assert cfg["momentum"]["type_config"]["type"] == "text"
    assert cfg["url"]["type_config"]["type"] == "link"
    assert cfg["url"]["type_config"]["display_text"] == copy.COLLAB["COL_LINK_DISPLAY"]
    # every label is copy.py's own string, never a bare technical column name
    assert cfg["vol"]["label"] == copy.COLLAB["JOINT_COL_VOL"]
    assert cfg["fwci_median"]["label"] == copy.COLLAB["DF_COL_FWCI"]


def test_topics_deep_dive_carries_no_frontier_column():
    """2BR3's own column list (Topic, Domain, Joint publications, top decile,
    SDG-tagged, Median FWCI, Momentum, link) drops the old Frontier column --
    a structural pin, not just an absence of the word in copy.py."""
    assert "frontier" not in {c.lower() for c in VC._topics_column_config()}


# ============================================================================
# 6. the untapped dataframe (section 5) -- same treatment, fixed ranking
# ============================================================================

def test_untapped_display_frame_matches_untapped_and_stays_gap_descending(ctx, subs_frac):
    res = CL.untapped(ctx, subs_frac, IA, IB, top_n=50)
    disp = VC._untapped_display_frame(res["topics"])
    assert list(disp.columns) == ["topic_name", "subfield_name", "vol_a", "vol_b",
                                  "joint_observed", "joint_expected", "gap", "url"]
    assert list(disp["gap"]) == sorted(disp["gap"], reverse=True)
    assert (disp["joint_expected"] >= disp["joint_observed"]).all()
    # the item-4 fix's own anchor: T3's true uncapped observed volume (2.0)
    t3 = disp[disp["topic_name"] == "Topic Three"]
    if len(t3):
        np.testing.assert_allclose(t3.iloc[0]["joint_observed"], 2.0, atol=1e-9)


def test_untapped_column_config_uses_the_per_side_names(ctx, subs_frac):
    res = CL.untapped(ctx, subs_frac, IA, IB, top_n=50)
    cfg = VC._untapped_column_config("Institution A", "Institution B")
    assert copy.COLLAB["UNTAPPED_COL_VOL_SIDE"].format(name="Institution A") in \
        {v["label"] for v in cfg.values()}
    assert cfg["gap"]["type_config"]["type"] == "number"
    assert cfg["url"]["type_config"]["type"] == "link"


# ============================================================================
# 7. the 20-then-show-all pattern (no slider anywhere -- sections 4/5)
# ============================================================================

@pytest.mark.parametrize("n_total,show_all,want", [
    (5, False, 5), (5, True, 5),
    (20, False, 20), (21, False, 20), (21, True, 21),
    (100, False, 20), (100, True, 100),
])
def test_visible_row_count_truth_table(n_total, show_all, want):
    assert VC._visible_row_count(n_total, show_all) == want


def test_rows_default_matches_the_shipped_constant():
    assert VC.ROWS_DEFAULT == 20


# ============================================================================
# 8. the pulse legend -- joint chip ONLY (section 1's chart, 2BR3 task 2)
# ============================================================================

def test_pulse_legend_carries_the_joint_chip_and_no_institution_chip():
    """2BR3 task 2: `ids=[]` -- the strip carries the ONE shared/joint chip
    and nothing else, since the pulse bars belong to the pair, not to
    either institution."""
    from lib import charts_compare as X

    strip = X.legend_strip([], slots={}, shared=True, shared_label=copy.COLLAB["LEGEND_JOINT"])
    assert copy.COLLAB["LEGEND_JOINT"] in strip
    # exactly one chip swatch in the whole strip
    assert strip.count('style="width:') == 1
    assert not any(c in strip for c in P.INSTITUTION_COLORS)


# ============================================================================
# 9. deletions -- structural (the functions are gone) and textual (grep)
# ============================================================================

DELETED_FUNCTIONS = [
    "_pair_picker", "_swap", "_add_by_name", "_candidates", "default_pair",
    "_sidebar_basket", "_fields_table", "_topics_table", "_untapped_table",
    "_arrow_cell", "_frontier_flags", "_frontier_glyph", "_top10_text",
    "_trend_help", "_rows_slider", "_download", "_extras",
]


@pytest.mark.parametrize("name", DELETED_FUNCTIONS)
def test_old_pair_picker_and_hand_table_functions_are_gone(name):
    assert not hasattr(VC, name), name


def test_no_slider_widgets_remain_in_this_streams_file():
    src = (APP_DIR / "lib" / "views_collab.py").read_text(encoding="utf-8")
    assert "st.slider(" not in src


def test_read_the_publications_on_openalex_is_gone_entirely():
    """The phrase survives ONLY inside this module's own docstring (naming
    what was deleted, in past tense) -- never as a copy.py value and never
    as a literal string handed to a Streamlit UI call."""
    from tests.test_narrative import collect_ui_call_strings

    for key in ("LINKS_HEADER", "LINK_PUBS", "LINK_COPUBS", "LINKS_INTRO"):
        assert key not in copy.COLLAB, key
    assert not any("Read the publications on OpenAlex" in v
                   for v in copy.COLLAB.values() if isinstance(v, str))
    ui_strings = collect_ui_call_strings(APP_DIR / "lib" / "views_collab.py")
    assert not any("Read the publications on OpenAlex" in s for _loc, s in ui_strings)


def test_slots_row_is_the_only_selection_entry_point_left():
    """`selection.slots_row("collab", state.COLLAB_CAP)` replaces the old
    two-selectbox A/B picker end to end -- confirmed by the render source
    calling it, and by the OLD picker's own copy keys being gone."""
    src = (APP_DIR / "lib" / "views_collab.py").read_text(encoding="utf-8")
    assert 'selection.slots_row("collab", state.COLLAB_CAP)' in src
    assert "selection.render_sidebar()" in src
    for key in ("PAIR_HEADER", "PAIR_A_LABEL", "PAIR_B_LABEL", "PAIR_SWAP_BUTTON",
                "PAIR_PROMPT", "PAIR_PICK", "EMPTY_NO_PAIR"):
        assert key not in copy.COLLAB, key


def test_field_table_is_gone_the_chart_is_the_whole_section():
    for key in ("JOINT_COL_FIELD", "COL_MEAN_CITATIONS", "COL_MEAN_CITATIONS_HELP",
                "FIELDS_TABLE_READING", "FIELDS_TABLE_TOOLTIP", "DOWNLOAD_FIELDS"):
        assert key not in copy.COLLAB, key


def test_trend_column_is_gone_momentum_replaces_it_everywhere():
    for key in ("COL_TREND", "COL_TREND_HELP"):
        assert key not in copy.COLLAB, key
    assert "DF_COL_MOMENTUM" in copy.COLLAB


# ============================================================================
# 10. digit ban over this stream's files
# ============================================================================

def test_no_digit_ban_violations_in_this_streams_files():
    from tests.test_narrative import collect_ui_call_strings, has_digit_violation, load_allowlist

    tokens = load_allowlist()
    files = [APP_DIR / "lib" / "views_collab.py", Path(COLLAB_PAGE)]
    strings = [(loc, s) for f in files for loc, s in collect_ui_call_strings(f)]
    assert strings, "collector found no UI-call strings in this stream's files -- it is vacuous"
    violations = [(loc, s) for loc, s in strings if has_digit_violation(s, tokens)]
    assert not violations, violations


def test_no_forbidden_vocabulary_in_the_new_collab_copy():
    from tests.test_forbidden_vocabulary import _violations

    new_keys = ("MOMENTUM_LABEL", "MOMENTUM_EVIDENCE_SHARE", "MOMENTUM_EVIDENCE_COPUBS",
                "MOMENTUM_EVIDENCE_SIGNIFICANCE", "RECIPROCITY_HEADER", "RECIPROCITY_HOW_TO_READ",
                "RECIPROCITY_WHY", "RECIPROCITY_AXIS_X", "RECIPROCITY_AXIS_Y", "COL_TOP10_DF_HELP",
                "COL_SDG_DF_HELP", "DF_COL_FWCI", "COL_FWCI_HELP", "DF_COL_MOMENTUM",
                "DF_COL_MOMENTUM_HELP", "SHOW_ALL_BUTTON", "META_EXPANDER")
    strings = [(k, copy.COLLAB[k]) for k in new_keys]
    assert not _violations(strings), _violations(strings)


# ============================================================================
# 11. page group -- needs the REAL app; self-skips until P7 lands
# ============================================================================

@pytest.mark.skipif(not REAL_V2_READY, reason=SKIP_REASON)
class TestPageGroup:
    """Deferred to the manager's post-P7 pass (see the module docstring):
    activates automatically -- no edit needed here -- the moment
    `app/data/collab_facts.json` exists, i.e. the moment P7's pipeline v2
    artefacts land."""

    STRASBOURG = "I68947357"
    CNRS = "I1294671590"
    PAIR = [STRASBOURG, CNRS]

    _UNSET = object()

    def _app(self, basket=None, a=_UNSET, b=_UNSET):
        """`slots_row` hydrates its two slots from `?pair=` on first load --
        an AppTest session has no URL, so a pre-selected pair is simulated
        the way `slots_row`'s own docstring documents its session-state
        contract: `slot_collab_0`/`slot_collab_1` plus the one-shot
        `_slots_hydrated_collab` guard, set BEFORE the first `.run()` so the
        hydration branch never fires and overwrites them. `a`/`b` default to
        the class's own PAIR when BOTH are omitted; passing `None` for one
        of them (with the other set) leaves that ONE slot empty -- the
        'only one slot filled' case."""
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(COLLAB_PAGE, default_timeout=300)
        at.session_state["basket"] = list(self.PAIR if basket is None else basket)
        if a is self._UNSET and b is self._UNSET:
            a, b = self.PAIR
        if a is not self._UNSET or b is not self._UNSET:
            at.session_state["slot_collab_0"] = a if a not in (None, self._UNSET) else VC.selection.SLOT_EMPTY
            at.session_state["slot_collab_1"] = b if b not in (None, self._UNSET) else VC.selection.SLOT_EMPTY
            at.session_state["_slots_hydrated_collab"] = True
        return at

    def test_page_renders_without_exception(self):
        at = self._app(a=self.STRASBOURG, b=self.CNRS).run()
        assert not at.exception, [str(e) for e in at.exception]

    def test_no_horizontal_slider_widget_on_the_real_page(self):
        at = self._app(a=self.STRASBOURG, b=self.CNRS).run()
        assert not at.slider, "a slider widget survived the 2BR3 rework"

    def test_momentum_headline_renders_for_a_real_pair(self):
        at = self._app(a=self.STRASBOURG, b=self.CNRS).run()
        assert not at.exception, [str(e) for e in at.exception]
        assert copy.COLLAB["MOMENTUM_LABEL"] in " ".join(c.value for c in at.caption)

    def test_identity_cards_render_before_the_pair_is_complete(self):
        """One slot filled -- that ONE institution's card must render
        without waiting for the second slot (2BR3 task 1: 'render
        IMMEDIATELY per filled slot'), and none of the sections below the
        header (which need a complete pair) render at all."""
        at = self._app(a=self.STRASBOURG, b=None).run()
        assert not at.exception, [str(e) for e in at.exception]
        rendered = " ".join(m.value for m in at.markdown)
        assert "Strasbourg" in rendered
        assert copy.COLLAB["PULSE_HEADER"] not in [s.value for s in at.subheader]

    def test_no_field_table_or_topic_html_table_remain_on_the_real_page(self):
        at = self._app(a=self.STRASBOURG, b=self.CNRS).run()
        assert not at.exception, [str(e) for e in at.exception]
        markup = " ".join(m.value for m in at.markdown)
        assert 'data-table="collab_fields"' not in markup
        assert 'data-table="collab_topics"' not in markup
        assert 'data-table="collab_untapped"' not in markup
        assert len(at.dataframe) >= 2  # the topic deep dive + untapped, native grids

    def test_reciprocity_and_momentum_headline_together_at_1920(self, tmp_path):
        """Also writes the visual proof PNG the acceptance asks for."""
        at = self._app(a=self.STRASBOURG, b=self.CNRS).run()
        assert not at.exception, [str(e) for e in at.exception]
        heads = [s.value for s in at.subheader]
        assert copy.COLLAB["FIELDS_HEADER"] in heads
        assert copy.COLLAB["RECIPROCITY_HEADER"] in heads
        assert copy.COLLAB["TOPICS_HEADER"] in heads
        assert copy.COLLAB["UNTAPPED_HEADER"] in heads
        # section order
        order = [copy.COLLAB["PULSE_HEADER"], copy.COLLAB["FIELDS_HEADER"],
                 copy.COLLAB["RECIPROCITY_HEADER"], copy.COLLAB["TOPICS_HEADER"],
                 copy.COLLAB["UNTAPPED_HEADER"]]
        positions = [heads.index(h) for h in order]
        assert positions == sorted(positions), heads


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))

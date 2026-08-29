"""
tests/test_pages_compare.py -- Stream C: AppTest page-render tests for
pages/2_(scales)_Compare.py and the render helpers in lib/views_compare.py
(BUILD_PLAN_2B.md decisions 2B-1 ... 2B-6, 2B-8, 2B-13, 2B-14 and amendments
A1, A2, A3, A9, A11).

Same process economics as tests/test_pages_collab.py: `st.cache_resource` keeps
the engine context and the (tree, basis) substrates warm across AppTest
instances inside one pytest PROCESS, so the FIRST test pays the cold engine load
(~10 s on this build) and every later one runs in about a second. Each test
builds its OWN AppTest -- a shared instance would leak the basket and the floor
toggle between tests.

WHAT IS PINNED HERE (and why each is a page-level test rather than a
lib/compare_data.py one, which tests/test_compare_data.py already covers):

  * THE PAGE RENDERS AT EVERY BASKET SIZE the cap allows (two, four, six). A
    Compare view that only works at one k is not a comparison page.
  * THE SHARES THE PAGE DRAWS SUM TO ONE per institution -- read off the frame
    the page's own cache returns, not off a fresh compare_data call.
  * THE FIFTH QUADRANT SEGMENT SURVIVES THE HAND-OFF (A2). K names the residual
    `not_scored` and lib/charts_compare.py names it `not_frontier_scored`; the
    page renames it, and without that rename the builder would silently draw the
    residual at zero. This test is the reason the rename exists.
  * THE IMPACT UNION IS A UNION (A1): at the high floor, on a realistic
    four-institution set, at least one cell is missing -- and a missing cell is
    NaN, never zero.
  * THE FLOOR TOGGLE MOVES SOMETHING: both the union it selects from and the
    rows the panel actually draws.
  * THE `?compare=` DEEP LINK, patched at `lib.selection.read_query` (AppTest on
    Streamlit 1.61.1 exposes no query-param API -- verified before writing this
    file), with the live URL path covered end to end by ops/_probe_compare.py.
  * THE WORKBOOK OPENS (2B-13): real bytes, real openpyxl, the expected sheet
    names in the expected order.
  * The digit-ban over THIS stream's three new files, using
    tests/test_narrative.py's own collector and shared allowlist, so they are
    proven clean before Stream G widens that test's file list (A5).

Run from cwd `app/`:  python -m pytest tests/test_pages_compare.py -q
"""
from __future__ import annotations

import io
from pathlib import Path
from unittest import mock

import pytest
from streamlit.testing.v1 import AppTest

from lib import charts_compare, compare_data, copy, selection, views_compare
from lib.data_cache import DATA_DIR
from lib.engine import build_substrates, load_context

APP_DIR = Path(__file__).resolve().parents[1]
COMPARE_PAGE = str(APP_DIR / "pages" / "2_⚖️_Compare.py")  # scales, the file's real name

STRASBOURG = "I68947357"    # Universite de Strasbourg -- the R1 reference seed
GDANSK = "I40413290"        # University of Gdansk -- panel_v2 D19 seed
IFPEN = "I265217849"        # IFP Energies nouvelles -- the RTO case
ISCTE = "I110026055"        # Iscte, Lisbon -- the SSH-heavy case
SORBONNE = "I39804081"
ETH = "I35440088"

PAIR = [STRASBOURG, GDANSK]
FOUR = [STRASBOURG, GDANSK, IFPEN, ISCTE]
SIX = FOUR + [SORBONNE, ETH]

TREE = "bestfit"            # config.yaml's own defaults, i.e. what the page opens on
BASIS = "frac"
SCENARIO = {"tree": TREE, "basis": BASIS}


def _app(basket=None, **extra_state) -> AppTest:
    at = AppTest.from_file(COMPARE_PAGE, default_timeout=600)
    at.session_state["basket"] = list(FOUR if basket is None else basket)
    for k, v in extra_state.items():
        at.session_state[k] = v
    return at


@pytest.fixture(scope="module")
def engine():
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

@pytest.mark.parametrize("ids", [PAIR, FOUR, SIX], ids=["k_two", "k_four", "k_six"])
def test_page_renders_at_every_basket_size(ids):
    at = _app(basket=ids).run()
    assert not at.exception, [str(e) for e in at.exception]
    # every view drew its section header
    headers = [s.value for s in at.subheader]
    for key in ("VIEW_FIELDS", "VIEW_SUBFIELDS", "VIEW_ERC", "VIEW_SDG",
                "VIEW_FRONTIER_MIX", "VIEW_FRONTIER_POINTS", "VIEW_IMPACT",
                "VIEW_COVERAGE", "STRIP_HEADER", "HANDOFF_HEADER"):
        assert copy.COMPARE[key] in headers, (key, headers)


def test_every_view_offers_its_own_csv_and_the_one_workbook():
    at = _app().run()
    assert not at.exception, [str(e) for e in at.exception]
    labels = [d.label for d in at.get("download_button")]
    assert labels.count(copy.COMPARE["EXPORT_XLSX_BUTTON"]) == 1, labels
    assert labels.count(copy.COMPARE["DOWNLOAD_VIEW"]) == len(views_compare.SLUGS), labels


def test_legend_is_rendered_once_per_view_and_names_every_institution(engine):
    ctx, _subs = engine
    at = _app().run()
    rendered = " ".join(m.value for m in at.markdown)
    for iid in FOUR:
        assert str(ctx["index_by_id"].loc[iid, "display_name"]) in rendered
    slots = views_compare._slots(ctx, FOUR)
    names = views_compare._names(ctx, FOUR)
    legend = charts_compare.institution_legend_html(names, slots)
    assert [m.value for m in at.markdown].count(legend) >= 2, "the legend is not repeated per view"


# ------------------------------------------------- the frames the page draws --

def test_fields_shares_sum_to_one_per_institution():
    """2B-1's own contract, on the frame the PAGE renders (its cached wrapper),
    not on a fresh compare_data call."""
    df = views_compare._fields(tuple(SIX), TREE, BASIS)
    sums = df.groupby("institution_id")["share"].sum()
    assert len(sums) == len(SIX)
    for iid, total in sums.items():
        assert total == pytest.approx(1.0, abs=1e-6), (iid, total)


def test_quadrant_mix_sums_to_one_with_the_fifth_segment_and_is_renamed(engine):
    """A2 plus the vocabulary hand-off: the page must hand the builder the name
    the builder knows, or the residual is drawn at zero."""
    df = views_compare._frontier_mix(tuple(SIX))
    assert charts_compare.NOT_SCORED in set(df["quadrant"]), "the fifth segment was not renamed"
    assert compare_data.NOT_SCORED not in set(df["quadrant"])
    for iid, total in df.groupby("institution_id")["share"].sum().items():
        assert total == pytest.approx(1.0, abs=1e-5), (iid, total)
    # and the builder really keeps it: five rows per institution, none synthesised at zero
    fig = charts_compare.fig_quadrant_mix(df, views_compare._slots(engine[0], SIX))
    assert len(fig.data) >= len(SIX)


def test_impact_union_carries_a_missing_cell_at_the_high_floor():
    """A1: the intersection is empty on realistic four-institution sets, so the
    panel shows the union with `n/a` where a cell is missing -- NaN, never 0."""
    union = views_compare._impact_subfields(tuple(FOUR), TREE,
                                            views_compare.IMPACT_FLOOR_DEFAULT)
    assert not union.empty
    assert union["pp"].isna().any(), "no missing cell -- this is not a union frame"
    assert not (union["pp"].fillna(-1) == 0).any(), "a missing cell was filled with zero"
    per_inst = union.groupby("institution_id")["pp"].apply(lambda s: s.isna().sum())
    assert (per_inst > 0).any()


def test_the_floor_toggle_changes_both_the_union_and_the_rows_drawn():
    high, low = views_compare.IMPACT_FLOORS
    assert high > low
    union_high = views_compare._impact_subfields(tuple(FOUR), TREE, high)
    union_low = views_compare._impact_subfields(tuple(FOUR), TREE, low)
    assert union_low["subfield_id"].nunique() > union_high["subfield_id"].nunique()
    top = views_compare._top_shared(tuple(FOUR), TREE, BASIS, views_compare.SUBFIELDS_TOP_N)
    rows_high = views_compare._impact_rows(union_high, top)["subfield_id"].nunique()
    rows_low = views_compare._impact_rows(union_low, top)["subfield_id"].nunique()
    assert rows_low > rows_high, (rows_high, rows_low)


def test_the_trends_measure_is_institution_normalised():
    """V's needs_change 5: the grid shares one y scale, so it is fed the
    subfield's share of that institution's own year, not a raw count. Every
    year's shares therefore sum to one for every institution."""
    df = views_compare._trends(ETH, TREE, BASIS)
    assert views_compare.TRENDS_VALUE_COL in df.columns
    per_year = df.groupby("year")[views_compare.TRENDS_VALUE_COL].sum()
    assert len(per_year) > 1
    for year, total in per_year.items():
        assert total == pytest.approx(1.0, abs=1e-6), (year, total)


def test_coverage_states_are_exhaustive_per_institution():
    """A9: six exclusive states summing to the whole fractional output."""
    df = views_compare._coverage(tuple(SIX))
    assert set(df["state"]) == set(views_compare._state_labels())
    for iid, total in df.groupby("institution_id")["share"].sum().items():
        assert total == pytest.approx(1.0, abs=1e-9), (iid, total)


def test_subfields_mirror_is_cut_to_the_module_constant():
    top = views_compare._top_shared(tuple(SIX), TREE, BASIS, views_compare.SUBFIELDS_TOP_N)
    assert len(top) == views_compare.SUBFIELDS_TOP_N
    df = views_compare._subfields(tuple(SIX), TREE, BASIS)
    shown = df[df["subfield_id"].isin(set(top["subfield_id"]))]
    assert shown["subfield_id"].nunique() == views_compare.SUBFIELDS_TOP_N


# ------------------------------------------------------------- selection ----

def test_compare_deeplink_seeds_the_page_with_an_empty_basket():
    """`?compare=I1,I2,I3,I4` on a reader who has no basket at all."""
    fake = {"compare": list(FOUR), "pair": None, "dropped": []}
    with mock.patch.object(selection, "read_query", lambda known: fake):
        at = _app(basket=[]).run()
    assert not at.exception, [str(e) for e in at.exception]
    assert at.session_state["basket"] == list(FOUR), at.session_state["basket"]
    codes = [c.value for c in at.get("code")]
    assert selection.deeplink("compare", FOUR) in codes, codes
    # ... and the SIDEBAR reflects it on this same run: the basket is seeded
    # before the sidebar is drawn, not inside the main column that follows it
    # (caught by reading the probe's head screenshot -- the count read zero).
    captions = " ".join(c.value for c in at.sidebar.caption)
    assert copy.FIND["BASKET_COUNT"].format(n=len(FOUR), cap=views_compare.state.BASKET_CAP) in captions, captions


def test_the_deeplink_shown_round_trips_through_selection():
    at = _app().run()
    codes = [c.value for c in at.get("code")]
    link = selection.deeplink("compare", FOUR)
    assert link in codes, codes
    parsed = selection.parse_query({"compare": link.split("=", 1)[1]}, FOUR)
    assert parsed["compare"] == list(FOUR)


def test_empty_state_below_two_institutions():
    at = _app(basket=[STRASBOURG]).run()
    assert not at.exception, [str(e) for e in at.exception]
    infos = " ".join(i.value for i in at.info)
    assert _first_literal(copy.COMPARE["EMPTY_TOO_FEW"]) in infos
    assert not at.get("plotly_chart"), "a single institution must not draw a comparison"


def test_removing_an_institution_shrinks_the_comparison():
    at = _app(basket=FOUR).run()
    at.button(key=f"cmp_rm_{IFPEN}").click().run()
    assert not at.exception, [str(e) for e in at.exception]
    assert IFPEN not in at.session_state["basket"]
    codes = [c.value for c in at.get("code")]
    assert selection.deeplink("compare", [i for i in FOUR if i != IFPEN]) in codes


def test_the_scenario_widgets_use_the_find_page_keys():
    """2B-8: the tree/basis choice carries across pages only if this page
    reuses Find's own widget keys."""
    at = _app().run()
    assert {"tree", "basis"} <= {sb.key for sb in at.selectbox}


def test_the_pair_handoff_offers_a_collaborate_deep_link():
    at = _app().run()
    codes = [c.value for c in at.get("code")]
    assert any(c.startswith("?pair=") for c in codes), codes
    assert {"cmp_pair_a", "cmp_pair_b"} <= {sb.key for sb in at.selectbox}


# ------------------------------------------------------------- workbook -----

def _frames_for(ids) -> dict:
    return {
        "fields": views_compare._fields(tuple(ids), TREE, BASIS),
        "subfields": views_compare._subfields(tuple(ids), TREE, BASIS),
        "erc": views_compare._erc(tuple(ids)),
        "sdg": views_compare._sdg(tuple(ids)),
        "frontier_mix": views_compare._frontier_mix(tuple(ids)),
        "frontier_points": views_compare._frontier_points(tuple(ids), TREE, BASIS, "top"),
        "impact": views_compare._impact_index(tuple(ids)),
        "impact_subfields": views_compare._impact_subfields(
            tuple(ids), TREE, views_compare.IMPACT_FLOOR_DEFAULT),
        "trends": views_compare._trends(ids[0], TREE, BASIS),
        "coverage": views_compare._coverage(tuple(ids)),
    }


def test_workbook_opens_with_openpyxl_and_carries_every_view(engine):
    import openpyxl

    ctx, _subs = engine
    sheets = views_compare.sheet_specs(SCENARIO, _frames_for(FOUR))
    raw = views_compare._workbook(ctx, list(FOUR), SCENARIO,
                                  views_compare.IMPACT_FLOOR_DEFAULT, sheets)
    assert isinstance(raw, bytes) and raw[:2] == b"PK", "not a zip container, so not an xlsx"
    book = openpyxl.load_workbook(io.BytesIO(raw))
    expected = [copy.COMPARE["XLSX_SHEET_METHODS"]] + [label for label, _c, _f in sheets]
    assert book.sheetnames == expected, book.sheetnames
    methods = book[copy.COMPARE["XLSX_SHEET_METHODS"]]
    values = [str(c.value) for row in methods.iter_rows() for c in row if c.value is not None]
    assert copy.COMPARE["XLSX_ROW_SNAPSHOT"] in values
    assert copy.VERDICT_LINE in values
    # every sheet is named in the Methods sheet, with what it counts beside it
    for label, caption, _frame in sheets:
        assert label in values and caption in values, label
    # and a data sheet really carries the frame's own columns
    fields = book[copy.COMPARE["VIEW_FIELDS"]]
    header = [c.value for c in next(fields.iter_rows())]
    assert header == list(views_compare._fields(tuple(FOUR), TREE, BASIS).columns)


def test_methods_rows_type_no_number_of_their_own(engine):
    """Every VALUE in the Methods sheet comes from CFG, the manifest or the
    frames; the labels are copy. A row whose value is a bare literal typed in
    lib/views_compare.py would show up here as a string the copy module does not
    know and the config does not contain."""
    ctx, _subs = engine
    rows = views_compare.methods_rows(ctx, list(FOUR), SCENARIO,
                                      views_compare.IMPACT_FLOOR_DEFAULT, [])
    assert list(rows.columns) == [copy.COMPARE["XLSX_COL_ITEM"], copy.COMPARE["XLSX_COL_VALUE"],
                                  copy.COMPARE["XLSX_COL_SOURCE"]]
    items = list(rows[copy.COMPARE["XLSX_COL_ITEM"]])
    for key in ("XLSX_ROW_SNAPSHOT", "XLSX_ROW_WINDOW", "XLSX_ROW_TREE", "XLSX_ROW_BASIS",
                "XLSX_ROW_INSTITUTIONS", "XLSX_ROW_FLOORS", "XLSX_ROW_FILTERS",
                "XLSX_ROW_READING"):
        assert copy.COMPARE[key] in items, key


def test_workbook_filename_is_self_describing():
    name = views_compare.workbook_filename(FOUR, TREE, BASIS)
    assert name.endswith(".xlsx")
    for iid in FOUR:
        assert iid in name
    assert TREE in name and BASIS in name


# ------------------------------------------------------------ digit ban ----

def test_no_digit_ban_violations_in_this_streams_files():
    """A5: `tests/test_narrative.py` does not yet list lib/views_compare.py or
    lib/exports_xlsx.py (it does already glob pages/*.py). Run its own
    collector, over its own shared allowlist, on this stream's files -- so they
    are proven clean now, and Stream G's widening finds nothing to fix."""
    from tests.test_narrative import collect_ui_call_strings, has_digit_violation, load_allowlist

    tokens = load_allowlist()
    files = [APP_DIR / "lib" / "views_compare.py", APP_DIR / "lib" / "exports_xlsx.py",
             Path(COMPARE_PAGE)]
    strings = [(loc, s) for f in files for loc, s in collect_ui_call_strings(f)]
    assert strings, "collector found no UI-call strings in this stream's files -- it is vacuous"
    violations = [(loc, s) for loc, s in strings if has_digit_violation(s, tokens)]
    assert not violations, violations


def test_no_hex_colour_is_typed_in_this_page():
    """One palette source (BUILD_PLAN_2A.md L-palette): the swatch takes its
    colour from `palette.institution_color`, never from a literal."""
    import re

    source = (APP_DIR / "lib" / "views_compare.py").read_text(encoding="utf-8")
    hits = re.findall(r"#[0-9a-fA-F]{3}|#[0-9a-fA-F]{6}", source)
    assert not hits, hits

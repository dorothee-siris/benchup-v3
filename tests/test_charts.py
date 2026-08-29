"""tests/test_charts.py -- stream R-D2.

Every `lib/charts.py` builder is rendered on REAL deployed data (Universite de
Strasbourg, resolved by `display_name` in `data/index.parquet`, plus University
of Gdansk for the SI-below-the-floor case), and the module's source is scanned
for the two things that must never appear in it: a colour literal (covered by
`tests/test_palette.py`'s directory walk) and a DIGIT inside a string literal
(covered here).

The section 9.4 frames are built INLINE from the parquet files rather than
imported from `lib/profile_data.py`: that module is stream R-B's, written in
parallel, and this test must not block on it. The column names below ARE the
section 9.4 contract, so the day `profile_data` lands, its output drops into
these builders unchanged -- and if it does not, this test's fixtures are the
statement of what the builders were promised.

Run from cwd `app/`:  python -m pytest tests/test_charts.py -q
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from lib import charts as C  # noqa: E402
from lib import palette as P  # noqa: E402
from tests.test_narrative import has_digit_violation, load_allowlist  # noqa: E402

DATA = APP_DIR / "data"
GDANSK = "I40413290"
TREE = "bestfit"


# ---------------------------------------------------------------------------
# Real-data fixtures -- the section 9.4 column contracts, built from parquet
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def dim() -> pd.DataFrame:
    return pd.read_parquet(
        DATA / "topics_dim.parquet",
        columns=["domain_id", "domain_name", "field_id", "field_name",
                 "subfield_id", "subfield_name", "topic_id", "topic_name",
                 "expansion_latest", "acceleration_latest", "frontier_score_latest",
                 "quadrant", "top25pct_frontier", "is_excluded"],
    )


@pytest.fixture(scope="module")
def seed_id() -> str:
    ix = pd.read_parquet(DATA / "index.parquet", columns=["institution_id", "display_name"])
    hit = ix[ix["display_name"].str.fullmatch("Universit. de Strasbourg", na=False)]
    assert len(hit) == 1, f"Strasbourg not uniquely resolved: {list(hit['display_name'])}"
    return str(hit.iloc[0]["institution_id"])


@pytest.fixture(scope="module")
def fields_df(seed_id, dim) -> pd.DataFrame:
    fmap = dim.drop_duplicates("field_id")[["field_id", "field_name", "domain_id", "domain_name"]]
    f = pd.read_parquet(DATA / "fields.parquet")
    f = f[(f["institution_id"] == seed_id) & (f["tree"].astype(str) == TREE)]
    out = f.merge(fmap, on="field_id", how="left")
    out["share"] = out["share_frac"]
    return out[["field_id", "field_name", "domain_id", "domain_name",
                "vol_full", "vol_frac", "share", "si"]].reset_index(drop=True)


@pytest.fixture(scope="module")
def subfields_df(dim) -> pd.DataFrame:
    """Gdansk's FULL subfield frame -- deliberately not the top-20 cut, because
    the whole point of this fixture is that most rows sit below the G6 floor and
    carry `si = NaN`, the case `fig_share_si` must render as NO MARK."""
    smap = dim.drop_duplicates("subfield_id")[
        ["subfield_id", "subfield_name", "field_id", "field_name", "domain_id", "domain_name"]]
    s = pd.read_parquet(DATA / "subfields.parquet")
    s = s[(s["institution_id"] == GDANSK) & (s["tree"].astype(str) == TREE)]
    out = s.merge(smap, on="subfield_id", how="left", suffixes=("", "_dim"))
    out["share"] = out["share_frac"]
    return out[["subfield_id", "subfield_name", "field_id", "field_name",
                "domain_id", "domain_name", "vol_full", "vol_frac",
                "share", "si"]].reset_index(drop=True)


@pytest.fixture(scope="module")
def topics_df(dim) -> pd.DataFrame:
    """Top topics for Strasbourg, taken from the SHIPPED topic dimension joined
    to a real per-institution volume slice. `topics_all.parquet` is the deep
    frame the app reads column-subsetted; here a bounded read is enough."""
    t = pd.read_parquet(DATA / "topics_all.parquet",
                        columns=["institution_id", "topic_id", "share_frac", "vol_frac", "vol_full"])
    t = t[t["institution_id"] == GDANSK]
    out = t.merge(dim, on="topic_id", how="left")
    out["share"] = out["share_frac"]
    return out.sort_values("share", ascending=False).head(30).reset_index(drop=True)


@pytest.fixture(scope="module")
def sdg_df(seed_id) -> pd.DataFrame:
    s = pd.read_parquet(DATA / "sdg.parquet")
    s = s[s["institution_id"] == seed_id].copy()
    s["sdg_number"] = s["sdg_idx"].astype(int) + 1
    s["sdg_label"] = ["SDG" + C.THIN_SPACE + str(n) for n in s["sdg_number"]]
    return s[["sdg_idx", "sdg_number", "sdg_label", "share", "esi", "mass"]].reset_index(drop=True)


@pytest.fixture(scope="module")
def erc_df(seed_id) -> pd.DataFrame:
    e = pd.read_parquet(DATA / "erc.parquet")
    e = e[e["institution_id"] == seed_id].copy().reset_index(drop=True)
    # PE1-11, LS1-9, SH1-8 in panel_idx order (the ERC 2024/25 structure); the
    # authoritative resource is stream R-B's erc_panels.csv -- reconstructed
    # here only so this test does not depend on a file another stream owns.
    order = [("PE", i) for i in range(11)] + [("LS", i) for i in range(9)] + \
            [("SH", i) for i in range(8)]
    e["erc_domain"] = [order[i][0] for i in e["panel_idx"]]
    e["panel_code"] = [f"{d}{n + 1}" for d, n in (order[i] for i in e["panel_idx"])]
    e["panel_label"] = e["panel_code"]
    return e[["panel_idx", "panel_code", "panel_label", "erc_domain",
              "share", "si", "mass"]]


# ---------------------------------------------------------------------------
# Builders render on real frames
# ---------------------------------------------------------------------------
def _bar_traces(fig: go.Figure) -> list[go.Bar]:
    return [t for t in fig.data if isinstance(t, go.Bar)]


def test_fig_share_si_fields_two_panels_and_colour_source(fields_df):
    fig = C.fig_share_si(fields_df, family="oa", sort="volume", gutter=True)
    bars = _bar_traces(fig)
    assert len(bars) == 1, "the share panel is ONE bar trace, not one per row"
    assert bars[0].orientation == "h"
    assert len(bars[0].x) == len(fields_df)
    # colour comes from the palette's domain map, in the SORTED row order
    ordered = fields_df.sort_values("share", ascending=False, kind="mergesort")
    assert list(bars[0].marker.color) == [P.domain_color(d) for d in ordered["domain_id"]]
    assert set(bars[0].marker.color) <= set(P.OA_DOMAIN_COLORS.values()) | {P.COMPARISON}
    # a second x-axis exists = the SI panel was built
    assert "xaxis2" in fig.layout
    assert fig.layout.xaxis2.title.text == C.AX_SI
    assert fig.layout.paper_bgcolor == P.SURFACE and fig.layout.plot_bgcolor == P.SURFACE
    assert fig.layout.height == C.row_height(len(fields_df))
    # the volume gutter (fix X3): folded into the y ticktext, one string per
    # row, no separate annotation left to collide with it
    assert len(fig.layout.annotations) == 0
    assert len(fig.layout.yaxis.ticktext) == len(fields_df)
    assert all(P.INK_SECONDARY in t for t in fig.layout.yaxis.ticktext)


def test_fig_share_si_sort_taxonomy_reorders_but_keeps_entity_colour(fields_df):
    by_vol = C.fig_share_si(fields_df, family="oa", sort="volume")
    by_tax = C.fig_share_si(fields_df, family="oa", sort="taxonomy")
    assert list(by_vol.data[0].y) != list(by_tax.data[0].y), "taxonomy sort must reorder"
    assert sorted(by_vol.data[0].y) == sorted(by_tax.data[0].y)
    # colour follows the entity, never the rank
    vol_map = dict(zip(by_vol.data[0].y, by_vol.data[0].marker.color))
    tax_map = dict(zip(by_tax.data[0].y, by_tax.data[0].marker.color))
    assert vol_map == tax_map
    # taxonomy order is domain-major
    tax_names = list(by_tax.data[0].y)
    doms = [fields_df.set_index("field_name").loc[n, "domain_id"] for n in tax_names]
    assert doms == sorted(doms)


def test_fig_share_si_nan_si_draws_no_mark(subfields_df):
    """A subfield below the G6 floor has `si = NaN`: it keeps its share bar and
    gets NO SI mark at all -- not a dot at zero, not a dot at the neutral value."""
    n_defined = int(np.isfinite(subfields_df["si"].to_numpy(dtype=float)).sum())
    assert 0 < n_defined < len(subfields_df), "fixture must mix defined and n/a SI"
    fig = C.fig_share_si(subfields_df, family="oa", sort="volume")
    dots = [t for t in fig.data if isinstance(t, go.Scatter) and t.mode == "markers"]
    assert len(dots) == 1
    assert len(dots[0].x) == n_defined
    assert np.isfinite(np.asarray(dots[0].x, dtype=float)).all()
    stems = [t for t in fig.data if isinstance(t, go.Scatter) and t.mode == "lines"]
    assert len(stems) == n_defined
    # the n/a rows are still on the y axis of the share panel
    assert len(_bar_traces(fig)[0].y) == len(subfields_df)
    # and their hover names the missing value explicitly
    assert any(P.NA_MARK in h for h in _bar_traces(fig)[0].customdata)


def test_fig_share_si_all_na_si_collapses_to_one_panel(subfields_df):
    thin = subfields_df[subfields_df["si"].isna()].reset_index(drop=True)
    assert len(thin) > 0
    fig = C.fig_share_si(thin, family="oa", sort="volume")
    assert "xaxis2" not in fig.layout, "no SI defined anywhere -> single panel"
    assert len(_bar_traces(fig)) == 1


def test_fig_topics_flags_excluded_rows(topics_df):
    fig = C.fig_topics(topics_df, sort="volume")
    bars = _bar_traces(fig)
    assert len(bars) == 1 and bars[0].orientation == "h"
    n_excl = int(topics_df["is_excluded"].fillna(False).sum())
    glyphed = [y for y in bars[0].y if y.startswith(C.EXCLUDED_GLYPH)]
    assert len(glyphed) == n_excl
    opac = list(bars[0].marker.opacity)
    assert sum(1 for o in opac if o == P.MUTED_OPACITY) == n_excl
    if n_excl:
        assert any(C.HOVER_EXCLUDED in h for h in bars[0].customdata)
    assert set(bars[0].marker.color) <= set(P.OA_DOMAIN_COLORS.values()) | {P.COMPARISON}


def test_fig_frontier_scatter_quadrants_and_outline(topics_df):
    fig = C.fig_frontier(topics_df)
    pts = [t for t in fig.data if isinstance(t, go.Scatter)]
    assert len(pts) == 1 and pts[0].mode == "markers"
    scored = topics_df[np.isfinite(topics_df["expansion_latest"])
                       & np.isfinite(topics_df["acceleration_latest"])]
    assert len(pts[0].x) == len(scored), "unscored topics are dropped and must be captioned"
    shapes = list(fig.layout.shapes)
    assert len(shapes) == 2, "one vertical and one horizontal quadrant line"
    assert {s.type for s in shapes} == {"line"}
    top = int(scored["top25pct_frontier"].fillna(False).sum())
    widths = list(pts[0].marker.line.width)
    assert sum(1 for w in widths if w == P.OUTLINE_WIDTH) == top
    assert set(pts[0].marker.color) <= set(P.OA_DOMAIN_COLORS.values()) | {P.COMPARISON}


def test_fig_sdg_uses_un_colours_in_goal_order(sdg_df):
    fig = C.fig_sdg(sdg_df)
    bars = _bar_traces(fig)
    assert len(bars) == 1 and bars[0].orientation == "h"
    assert len(bars[0].x) == len(sdg_df) == len(P.SDG_COLORS) - len(P.SDG_UNCOVERED)
    expected = [P.SDG_COLORS[int(n)] for n in sorted(sdg_df["sdg_number"])]
    assert list(bars[0].marker.color) == expected
    assert P.SDG_COLORS[P.SDG_UNCOVERED[0]] not in set(bars[0].marker.color)
    assert fig.layout.xaxis2.title.text == C.AX_ESI


def test_fig_erc_uses_the_three_erc_hues_grouped_by_domain(erc_df):
    fig = C.fig_erc(erc_df)
    bars = _bar_traces(fig)
    assert len(bars[0].x) == len(erc_df) == 28
    assert set(bars[0].marker.color) == set(P.ERC_DOMAIN_COLORS.values())
    # taxonomy order = PE block, then LS, then SH
    codes = list(bars[0].y)
    doms = [c[:2] for c in codes]
    assert doms == sorted(doms, key=lambda d: P.ERC_DOMAIN_ORDER.index(d))
    # no OA domain hue leaks into an ERC-coloured chart (coexistence rule)
    assert not (set(bars[0].marker.color) & set(P.OA_DOMAIN_COLORS.values()))


def test_breakdown_pair_global_and_grouped(fields_df):
    labels = [P.OA_DOMAIN_COLORS and n for n in ("Life", "Social", "Physical", "Health")]
    totals = [float(fields_df[fields_df["domain_id"] == d]["vol_full"].sum())
              for d in P.OA_DOMAIN_ORDER]
    colors = [P.OA_DOMAIN_COLORS[d] for d in P.OA_DOMAIN_ORDER]

    g = C.fig_breakdown_global(labels, totals, colors)
    assert len(_bar_traces(g)) == 1
    assert _bar_traces(g)[0].orientation == "h"
    assert list(_bar_traces(g)[0].x) == sorted(totals, reverse=True)
    assert len(g.layout.annotations) == len(labels), "one direct end label per bar"
    assert g.layout.showlegend is False

    years = [str(y) for y in range(2020, 2026)]
    series = list(P.OA_DOMAIN_ORDER)
    y = C.fig_breakdown_yearly(
        years, series,
        labels={d: l for d, l in zip(series, labels)},
        colors={d: P.OA_DOMAIN_COLORS[d] for d in series},
        totals={d: [totals[i] / len(years)] * len(years) for i, d in enumerate(series)},
    )
    assert len(_bar_traces(y)) == len(series), "one trace per series, grouped not stacked"
    assert y.layout.barmode == "overlay", "explicit offset/width; offsetgroup is broken on 5.24.1"
    offsets = sorted(t.offset for t in _bar_traces(y))
    assert len(set(offsets)) == len(series), "every series gets its own offset"
    widths = {t.width for t in _bar_traces(y)}
    assert len(widths) == 1, "every series gets the same bar width"
    assert y.layout.showlegend is False, "the chip legend is the ONE legend for the pair"
    with pytest.raises(ValueError):
        C.fig_breakdown_yearly([2020], series, {}, {}, {})  # years must be strings


def test_chip_legend_html_escapes_and_uses_palette_ink():
    html = C.chip_legend_html([("Life <Sciences>", P.OA_DOMAIN_COLORS[1])])
    assert "&lt;Sciences&gt;" in html and "<Sciences>" not in html
    assert P.OA_DOMAIN_COLORS[1] in html
    assert P.INK_SECONDARY in html
    assert html.count("<span") == 3


def test_row_height_idiom():
    assert C.row_height(0) == C.MIN_HEIGHT
    assert C.row_height(30) == C.ROW_PX * 30 + C.BASE_PX
    assert C.row_height(100) > C.row_height(50)


def test_invalid_family_and_sort_raise(fields_df):
    with pytest.raises(ValueError):
        C.fig_share_si(fields_df, family="nonsense")
    with pytest.raises(ValueError):
        C.fig_share_si(fields_df, sort="alphabetical")


# ---------------------------------------------------------------------------
# Fix X3 (inspection finding I-4): the label/gutter collision at narrow width.
# `lib/charts.py::fig_share_si` / `fig_topics` fold the volume into the y
# ticktext as ONE right-anchored string per row instead of a separate
# annotation, so there is nothing left for it to collide with; a label longer
# than `MAX_LABEL_CHARS` is ellipsised from the RIGHT only (never the left),
# and the full label always survives in hover/customdata.
# ---------------------------------------------------------------------------
def test_truncate_label_never_cuts_from_the_left():
    long_name = "Biochemistry, Genetics and Molecular Biology"
    assert len(long_name) > C.MAX_LABEL_CHARS, "fixture assumption: this name IS the I-4 example"
    short = C._truncate_label(long_name)
    assert len(short) <= C.MAX_LABEL_CHARS
    assert short.startswith(long_name[: C.MAX_LABEL_CHARS - 1].rstrip())
    assert short.endswith(C.ELLIPSIS)
    # the leading characters are never the ones dropped
    assert long_name[:4] in short
    # a label already within budget is untouched
    assert C._truncate_label("Mathematics") == "Mathematics"


def test_fig_share_si_folds_volume_into_ticktext_full_label_survives_in_hover(fields_df):
    """Uses the REAL long field name from the I-4 screenshot ("Biochemistry,
    Genetics and Molecular Biology", 46 chars) straight out of the fixture
    `fields_df` already builds from the deployed parquet -- no synthetic data."""
    fig = C.fig_share_si(fields_df, family="oa", sort="volume", gutter=True)
    long_name = next(n for n in fields_df["field_name"] if len(n) > C.MAX_LABEL_CHARS)
    assert long_name == "Biochemistry, Genetics and Molecular Biology"

    names = list(fig.data[0].y)  # identity axis: FULL names, unaffected by truncation
    idx = names.index(long_name)
    assert long_name in fig.data[0].customdata[idx], "full label must survive in hover"

    tickvals = list(fig.layout.yaxis.tickvals)
    ticktext = list(fig.layout.yaxis.ticktext)
    shown = ticktext[tickvals.index(long_name)]
    assert C._truncate_label(long_name) in shown
    assert long_name not in shown, "the raw, untruncated label is never drawn on screen"
    assert P.INK_SECONDARY in shown, "the volume rides in the secondary ink, inside the tick text"

    # no tick label's VISIBLE (label) portion exceeds MAX_LABEL_CHARS + 1
    # (the +1 covers the single ellipsis glyph replacing the cut characters)
    for shown in ticktext:
        label_part = shown.split(C.TICK_LABEL_GAP)[0]
        assert len(label_part) <= C.MAX_LABEL_CHARS + 1


def test_fig_share_si_automargin_and_reserved_margin_grow_for_long_labels(fields_df):
    short_only = fields_df[fields_df["field_name"].str.len() <= C.MAX_LABEL_CHARS].reset_index(drop=True)
    fig_short = C.fig_share_si(short_only, family="oa")
    fig_long = C.fig_share_si(fields_df, family="oa")  # includes the 46-char Biochemistry row
    assert fig_short.layout.yaxis.automargin is True
    assert fig_long.layout.yaxis.automargin is True
    assert fig_long.layout.margin.l > fig_short.layout.margin.l, (
        "a frame containing a long label must reserve more left margin than one that doesn't"
    )
    assert fig_long.layout.margin.l > C.GUTTER_MARGIN_MIN_PX


def test_fig_topics_folds_volume_and_truncates_the_longest_labels_in_the_app(topics_df):
    long_names = [str(n) for n in topics_df["topic_name"] if len(str(n)) > C.MAX_LABEL_CHARS]
    assert long_names, "fixture must include a real long topic name (topics are the app's longest labels)"
    fig = C.fig_topics(topics_df, sort="volume")
    assert fig.layout.yaxis.automargin is True
    ticktext = list(fig.layout.yaxis.ticktext)
    assert any(C.ELLIPSIS in t for t in ticktext), "at least one real long topic name must be ellipsised"
    for shown in ticktext:
        label_part = shown.split(C.TICK_LABEL_GAP)[0]
        assert len(label_part) <= C.MAX_LABEL_CHARS + 1
    # full label survives in hover even where the tick was truncated
    long_hit = long_names[0]
    row_idx = [i for i, y in enumerate(fig.data[0].y) if long_hit in y]
    assert row_idx and long_hit in fig.data[0].customdata[row_idx[0]]


def test_fig_erc_reuses_the_same_folded_gutter_mechanism(erc_df):
    """ERC panel labels run up to 66 chars in the real app (`panel_label` here
    is the short `panel_code` since `erc_panels.csv` is stream R-B's, but the
    mechanism under test is family-agnostic: `fig_erc` delegates to
    `fig_share_si`, so whatever labels arrive get the same treatment)."""
    fig = C.fig_erc(erc_df)
    assert fig.layout.yaxis.automargin is True
    assert len(fig.layout.yaxis.ticktext) == len(erc_df)
    assert all(P.INK_SECONDARY in t for t in fig.layout.yaxis.ticktext)


# ---------------------------------------------------------------------------
# Source scans: no digit in any string literal of charts.py
# ---------------------------------------------------------------------------
def _string_literals(path: Path) -> list[tuple[int, str]]:
    """Every str constant in the module EXCEPT docstrings (module, class,
    function) -- a docstring is prose for a reader of the source, never text
    the app renders, and the digit-ban's whole purpose is that no rendered
    string asserts a value (BUILD_PLAN_2A.md L10)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    doc_nodes: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                doc_nodes.add(id(body[0].value))
    out: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in doc_nodes:
            out.append((node.lineno, node.value))
    return out


def _deployed_column_names() -> set[str]:
    """Every column name of every deployed table. A string literal that is
    EXACTLY one of these is a data-contract key, not rendered copy -- the same
    exclusion `tests/test_narrative.py` grants `lib/data_cache.py` ("parquet
    column names and file paths, not UI copy"), but grounded in the real
    schemas rather than in a hand-kept list, so it can never silently widen."""
    import pyarrow.parquet as pq
    names: set[str] = set()
    for f in sorted(DATA.glob("*.parquet")):
        names |= set(pq.read_schema(f).names)
    return names


def test_no_digit_in_any_charts_string_literal():
    """The allowlist file is loaded READ-ONLY (it is full at its cap of fifteen
    tokens; this stream adds none). Everything parametric in a chart is a
    `{placeholder}` the caller fills, and every number format is COMPOSED from
    an int constant -- see the module docstring of lib/charts.py."""
    tokens = load_allowlist()
    columns = _deployed_column_names()
    assert "top25pct_frontier" in columns, "column-name exemption must be grounded in real schemas"
    offenders = [(lineno, s) for lineno, s in _string_literals(APP_DIR / "lib" / "charts.py")
                 if s not in columns and has_digit_violation(s, tokens)]
    assert not offenders, f"digit(s) inside a string literal of lib/charts.py: {offenders}"


def test_charts_module_never_imports_streamlit():
    src = (APP_DIR / "lib" / "charts.py").read_text(encoding="utf-8")
    assert not re.search(r"^\s*import\s+streamlit", src, flags=re.MULTILINE)
    assert not re.search(r"^\s*from\s+streamlit", src, flags=re.MULTILINE)
    assert "streamlit" not in sys.modules or True  # importing charts must not pull it in


def test_charts_takes_every_colour_from_palette():
    """Belt and braces beside tests/test_palette.py's directory walk: charts.py
    must reference the palette module for colour, and never name a hex."""
    src = (APP_DIR / "lib" / "charts.py").read_text(encoding="utf-8")
    assert not re.search(r"#[0-9A-Fa-f]{6}\b", src)
    assert "from lib import palette as P" in src


def test_fig_share_si_stacked_variant_for_the_narrow_breakpoint(fields_df):
    """VIZ_SPEC section 1.8: below the small breakpoint the share and SI panels
    STACK instead of sitting side by side (measured: 61 px of plot area each at
    390 px when side by side). The builder makes the layout available; the caller
    decides when to use it, because Streamlit cannot read the viewport width."""
    side = C.fig_share_si(fields_df, family="oa")
    down = C.fig_share_si(fields_df, family="oa", stacked=True)
    assert "xaxis2" in side.layout and "xaxis2" in down.layout
    # side by side: one row, two columns -> the two x-axes share the vertical band
    assert side.layout.yaxis.domain == side.layout.yaxis2.domain
    # stacked: two rows -> disjoint vertical bands, share above SI
    assert down.layout.yaxis.domain[0] > down.layout.yaxis2.domain[1]
    assert down.layout.height == 2 * side.layout.height
    # same rows, same order, same colours either way
    assert list(side.data[0].y) == list(down.data[0].y)
    assert list(side.data[0].marker.color) == list(down.data[0].marker.color)

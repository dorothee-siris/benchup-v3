"""tests/test_charts_compare.py -- Phase 2B, stream V.

Every `lib/charts_compare.py` builder is rendered at k = 2 AND k = 6, and the
module's source is scanned for the two things that must never appear in it: a
colour literal and a DIGIT inside a string literal.

The frames are built INLINE, from the BUILD_PLAN_2B.md section 4 column
contracts (as amended by the wind tunnel's E16), rather than imported from
`lib/compare_data.py`: that module is stream K's, written in parallel, and this
test must not block on it. The column names below ARE the contract, so the day
`compare_data` lands its output drops into these builders unchanged -- and if it
does not, these fixtures are the statement of what the builders were promised.

Two shapes are deliberately built into the fixtures because they are the NORMAL
case on real data and the builders have to survive them:
  * a MISSING cell (institution has no row for a category) -- A1 measured that
    only 3,342 of 7,557 institutions have any floor-30 impact cell and that 40
    of 40 random four-tuples intersect to zero, so the union frame is full of
    holes;
  * a quadrant an institution does not ship at all (one real institution has
    three quadrants, not four) and a `si_status` of every kind.

Run from cwd `app/`:  python -m pytest tests/test_charts_compare.py -q
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

from lib import charts as C                 # noqa: E402
from lib import charts_compare as X         # noqa: E402
from lib import palette as P                # noqa: E402
from tests.test_narrative import has_digit_violation, load_allowlist  # noqa: E402

DATA = APP_DIR / "data"
MODULE = APP_DIR / "lib" / "charts_compare.py"

# Six synthetic institutions with ASCENDING inst_keys that are deliberately NOT
# in id order, so every test exercises the "slots follow inst_key, not the
# order the caller happens to hold" rule.
IDS = ["Iz", "Ia", "Im", "Ib", "Iq", "Ic"]
KEYS = {"Iz": 11, "Ia": 22, "Im": 33, "Ib": 44, "Iq": 55, "Ic": 66}
NAMES = {i: f"Institution {chr(ord('A') + n)}" for n, i in enumerate(IDS)}


def slots_for(k: int) -> dict:
    return P.institution_slots({i: KEYS[i] for i in IDS[:k]})


@pytest.fixture(params=[2, 6], ids=["k_two", "k_six"])
def k(request) -> int:
    return request.param


@pytest.fixture
def slots(k) -> dict:
    return slots_for(k)


@pytest.fixture
def ids(k) -> list:
    return IDS[:k]


# ---------------------------------------------------------------------------
# Inline frames -- the section 4 contracts
# ---------------------------------------------------------------------------
FIELDS = [(11, "Agricultural and Biological Sciences", 1),
          (12, "Arts and Humanities", 2),
          (13, "Biochemistry, Genetics and Molecular Biology", 1),
          (16, "Chemistry", 3),
          (27, "Medicine", 4)]


def fields_long(ids) -> pd.DataFrame:
    rows = []
    for n, iid in enumerate(ids):
        for m, (fid, fname, did) in enumerate(FIELDS):
            share = 0.05 + 0.03 * m + 0.0005 * n    # deliberately CLOSE across
            rows.append(dict(institution_id=iid, field_id=fid, field_name=fname,
                             domain_id=did, vol_full=100 + 10 * m + n,
                             vol_frac=60.0 + 5 * m + n, share=share,
                             si=0.5 + 0.2 * m + 0.005 * n, si_status="solid"))
    return pd.DataFrame(rows)


def subfields_long(ids) -> pd.DataFrame:
    rows = []
    states = ["solid", "thin", "none"]
    for n, iid in enumerate(ids):
        for m in range(6):
            state = states[(n + m) % len(states)]
            rows.append(dict(institution_id=iid, subfield_id=1200 + m,
                             subfield_name=f"Subfield {chr(ord('A') + m)}",
                             field_id=12, domain_id=2,
                             vol_full=50 + m, vol_frac=[40.0, 20.0, 5.0][(n + m) % 3],
                             share=0.02 + 0.01 * m + 0.001 * n,
                             si=1.0 + 0.1 * m, si_status=state))
    # one institution is missing one subfield entirely (the union case)
    return pd.DataFrame(rows).drop(index=[1]).reset_index(drop=True)


def erc_long(ids) -> pd.DataFrame:
    panels = [(0, "LS9", "Biotechnology and Biosystems Engineering", "LS"),
              (5, "PE1", "Mathematics", "PE"),
              (9, "SH2", "Institutions, Values, Environment and Space", "SH")]
    rows = []
    for n, iid in enumerate(ids):
        for idx, code, label, dom in panels:
            rows.append(dict(institution_id=iid, panel_idx=idx, panel_code=code,
                             panel_label=label, erc_domain=dom,
                             share=0.05 + 0.01 * idx + 0.002 * n,
                             si=0.8 + 0.1 * n, mass=40.0 - 12.0 * n,
                             si_status="solid" if n < 2 else "thin"))
    return pd.DataFrame(rows)


def sdg_long(ids) -> pd.DataFrame:
    rows = []
    for n, iid in enumerate(ids):
        for g in range(1, 5):
            rows.append(dict(institution_id=iid, sdg_idx=g - 1, sdg_number=g,
                             sdg_label_numbered=f"SDG {g} - Goal {g}",
                             share=0.03 * g + 0.001 * n, si=1.1 + 0.05 * n,
                             mass=35.0 - 5.0 * n,
                             si_status="solid" if n % 2 == 0 else "thin"))
    return pd.DataFrame(rows)


def frontier_mix(ids, drop_one: bool = True) -> pd.DataFrame:
    quads = ["accelerating_expansion", "decelerating_expansion",
             "accelerating_contraction", "decelerating_contraction"]
    rows = []
    for n, iid in enumerate(ids):
        for q in quads:
            rows.append(dict(institution_id=iid, quadrant=q,
                             share=0.20 + 0.01 * quads.index(q) + 0.005 * n,
                             top25_share=0.19, unscored_share=0.11))
    out = pd.DataFrame(rows)
    if drop_one:   # the real institution that ships only three quadrants
        out = out.drop(index=[3]).reset_index(drop=True)
    return out


def frontier_points(ids) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    rows = []
    for n, iid in enumerate(ids):
        for t in range(20):
            rows.append(dict(institution_id=iid, topic_id=10000 + t,
                             topic_name=f"Topic {t}", subfield_name="Subfield A",
                             expansion_latest=float(rng.normal(0.3 * n, 1.0)),
                             acceleration_latest=float(rng.normal(0.2, 0.8)),
                             vol_full=float(10 + t), vol_frac=float(6 + t),
                             quadrant="accelerating_expansion",
                             top25pct_frontier=bool(t % 4 == 0), is_excluded=False))
    out = pd.DataFrame(rows)
    out.loc[0, "expansion_latest"] = np.nan     # an unscored topic must be dropped
    return out


def impact_index(ids) -> pd.DataFrame:
    return pd.DataFrame([
        dict(institution_id=iid, pp=0.08 + 0.02 * n, ci_low=0.07 + 0.02 * n,
             ci_high=0.09 + 0.02 * n, pp_denominator_frac=2000.0 + 100 * n,
             n_works_full=4000 + 200 * n)
        for n, iid in enumerate(ids)])


def impact_subfields(ids) -> pd.DataFrame:
    rows = []
    for n, iid in enumerate(ids):
        for m in range(4):
            if (n + m) % 3 == 0:        # A1: the union is full of holes
                continue
            rows.append(dict(institution_id=iid, subfield_id=2700 + m,
                             subfield_name=f"Subfield {chr(ord('P') + m)}",
                             pp=0.06 + 0.01 * m + 0.005 * n,
                             ci_low=0.04 + 0.01 * m, ci_high=0.09 + 0.01 * m,
                             n_works_full=120 + m, in_all_ids=False))
    return pd.DataFrame(rows)


TREND_YEARS = ["2020", "2021", "2022", "2023", "2024", "2025"]
TREND_SUBFIELDS = [1200, 1201, 1202]


def trends_frames(ids) -> dict:
    out = {}
    for n, iid in enumerate(ids):
        rows = []
        for sid in TREND_SUBFIELDS:
            for y in TREND_YEARS:
                rows.append(dict(institution_id=iid, year=y, subfield_id=sid,
                                 subfield_name=f"Subfield {sid}",
                                 vol_full=10 + n + int(y) % 7,
                                 vol_frac=6.0 + n))
        out[iid] = pd.DataFrame(rows)
    return out


def coverage(ids) -> pd.DataFrame:
    shares = {"classified_eligible": 0.80, "title_only": 0.10,
              "lang_uncertain": 0.06, "untranslated_grey": 0.03,
              "unusable": 0.005, "retracted_excluded": 0.005}
    return pd.DataFrame([dict(institution_id=iid, state=st, share=v)
                         for iid in ids for st, v in shares.items()])


# ---------------------------------------------------------------------------
# Slots -- the stability rule
# ---------------------------------------------------------------------------
def test_slots_follow_inst_key_not_call_order():
    forward = P.institution_slots({i: KEYS[i] for i in IDS})
    shuffled = P.institution_slots({i: KEYS[i] for i in reversed(IDS)})
    assert forward == shuffled
    # ascending inst_key, so the id with the smallest key owns slot zero
    assert forward["Iz"] == 0 and forward["Ic"] == len(IDS) - 1
    seq = P.institution_slots([KEYS[i] for i in reversed(IDS)])
    assert seq == {KEYS[i]: n for n, i in enumerate(IDS)}


def test_removing_an_institution_does_not_repaint_the_survivors_below_it():
    """The whole point of keying slots on `inst_key`: dropping the LAST-keyed
    institution must leave every other colour where it was."""
    full = P.institution_slots({i: KEYS[i] for i in IDS})
    without_last = P.institution_slots({i: KEYS[i] for i in IDS if i != "Ic"})
    for iid, slot in without_last.items():
        assert full[iid] == slot


def test_slot_colours_never_cycle_past_the_cap():
    assert P.institution_color(P.INSTITUTION_SLOT_MAX) == P.COMPARISON
    assert P.institution_color(P.INSTITUTION_SLOT_MAX + 3) == P.COMPARISON
    assert P.institution_color(None) == P.COMPARISON
    assert P.institution_color(0) == P.INSTITUTION_COLORS[0]


# ---------------------------------------------------------------------------
# Every builder renders at k = 2 and k = 6
# ---------------------------------------------------------------------------
def test_mirror_renders_for_every_family(ids, slots, k):
    cases = [(fields_long(ids), "oa", "volume", len(FIELDS)),
             (subfields_long(ids), "oa", "volume", 6),
             (erc_long(ids), "erc", "taxonomy", 3),
             (sdg_long(ids), "sdg", "taxonomy", 4)]
    for df, family, sort, n_rows in cases:
        fig = X.fig_mirror_dots(df, family=family, slots=slots, names=NAMES, sort=sort)
        assert isinstance(fig, go.Figure)
        # one trace per institution per panel: share + specialisation
        assert len(fig.data) == 2 * k, (family, len(fig.data))
        assert len(fig.layout.yaxis.ticktext) == n_rows
        assert fig.layout.height >= C.MIN_HEIGHT
        assert fig.layout.paper_bgcolor == P.SURFACE
        assert fig.layout.showlegend is False


def test_mirror_marks_carry_the_institution_colour_and_nothing_else(ids, slots, k):
    fig = X.fig_mirror_dots(fields_long(ids), family="oa", slots=slots, names=NAMES)
    wanted = {P.institution_color(s) for s in slots.values()} | {P.SURFACE}
    for tr in fig.data:
        for c in list(tr.marker.color) + list(tr.marker.line.color):
            assert c in wanted, c


def test_mirror_hollow_dot_for_a_thin_cell_and_no_dot_for_none(ids, slots):
    df = subfields_long(ids)
    fig = X.fig_mirror_dots(df, family="oa", slots=slots, names=NAMES)
    si_traces = fig.data[len(slots):]
    drawn = sum(len(tr.x) for tr in si_traces)
    expected = int((df["si_status"] != "none").sum())
    assert drawn == expected
    hollow = sum(1 for tr in si_traces for c in tr.marker.color if c == P.SURFACE)
    assert hollow == int((df["si_status"] == "thin").sum())


def test_mirror_zero_volume_never_gets_a_specialisation_mark(ids, slots):
    df = fields_long(ids)
    df.loc[0, "vol_full"] = 0
    df.loc[0, "vol_frac"] = 0.0
    fig = X.fig_mirror_dots(df, family="oa", slots=slots, names=NAMES)
    drawn = sum(len(tr.x) for tr in fig.data[len(slots):])
    assert drawn == len(df) - 1


def test_mirror_sort_moves_rows_but_never_colours(ids, slots):
    df = fields_long(ids)
    by_volume = X.fig_mirror_dots(df, family="oa", slots=slots, names=NAMES, sort="volume")
    by_taxonomy = X.fig_mirror_dots(df, family="oa", slots=slots, names=NAMES, sort="taxonomy")
    assert list(by_volume.layout.yaxis.ticktext) != list(by_taxonomy.layout.yaxis.ticktext)
    for a, b in zip(by_volume.data, by_taxonomy.data):
        assert set(a.marker.color) == set(b.marker.color)


def test_mirror_rejects_an_unknown_family_or_sort(ids, slots):
    with pytest.raises(ValueError):
        X.fig_mirror_dots(fields_long(ids), family="doctype", slots=slots)
    with pytest.raises(ValueError):
        X.fig_mirror_dots(fields_long(ids), family="oa", slots=slots, sort="alphabetical")


def test_quadrant_mix_always_draws_five_rows_including_not_scored(ids, slots, k):
    fig = X.fig_quadrant_mix(frontier_mix(ids), slots, names=NAMES)
    assert len(fig.data) == k
    assert len(fig.layout.yaxis.ticktext) == len(X.QUADRANT_ORDER) == 5
    assert X.QUADRANT_LABELS[X.NOT_SCORED] in list(fig.layout.yaxis.ticktext)
    # a quadrant an institution does not ship is drawn at zero, never dropped
    assert all(len(tr.x) == len(X.QUADRANT_ORDER) for tr in fig.data)


def test_quadrant_not_scored_is_the_residual_to_one(ids, slots):
    df = frontier_mix(ids, drop_one=False)
    fig = X.fig_quadrant_mix(df, slots, names=NAMES)
    for tr in fig.data:
        assert float(np.sum(tr.x)) == pytest.approx(1.0, abs=1e-9)


def test_frontier_overlay_and_small_multiples(ids, slots, k):
    df = frontier_points(ids)
    overlay = X.fig_frontier_overlay(df, slots, names=NAMES)
    facets = X.fig_frontier_small_multiples(df, slots, names=NAMES)
    assert len(overlay.data) == len(facets.data) == k
    # the unscored topic is dropped from both, and counted by neither
    assert sum(len(t.x) for t in overlay.data) == len(df) - 1
    assert sum(len(t.x) for t in facets.data) == len(df) - 1
    # every bubble clears the mark floor
    for tr in overlay.data:
        assert float(np.min(tr.marker.size)) >= X.MIN_MARK_PX
    # a top-quartile topic is flagged by SHAPE (an INK outline), never a new hue
    outlines = {c for tr in overlay.data for c in tr.marker.line.color}
    assert outlines <= {P.INK, P.SURFACE}


def test_impact_intervals_index_level(ids, slots, k):
    fig = X.fig_impact_intervals(impact_index(ids), slots, names=NAMES)
    # one interval trace and one dot trace per institution
    assert len(fig.data) == 2 * k
    assert len(fig.layout.yaxis.ticktext) == k
    assert fig.layout.xaxis.range[0] == 0


def test_impact_intervals_sort_by_value_or_by_slot(ids, slots, k):
    df = impact_index(ids)
    ranked = X.fig_impact_intervals(df, slots, names=NAMES, sort="volume")
    stable = X.fig_impact_intervals(df, slots, names=NAMES, sort="taxonomy")
    if k > 1:
        assert list(ranked.layout.yaxis.ticktext) != list(stable.layout.yaxis.ticktext)


def test_impact_subfields_leaves_a_missing_cell_blank(ids, slots, k):
    df = impact_subfields(ids)
    fig = X.fig_impact_subfields(df, slots, names=NAMES)
    dots = sum(len(tr.x) for tr in fig.data if tr.mode == "markers")
    assert dots == len(df)            # exactly the cells that exist, never a zero
    assert len(fig.layout.yaxis.ticktext) == df["subfield_id"].nunique()
    # every institution owns its own lane, so an interval cannot hide another
    assert fig.layout.height >= X.compare_row_height(
        df["subfield_id"].nunique(), k)


def test_trends_small_multiples(ids, slots, k):
    frames = trends_frames(ids)
    fig = X.fig_trends_small_multiples(frames, slots, TREND_SUBFIELDS, names=NAMES,
                                       bonus_year=TREND_YEARS[-1])
    # per panel per institution: the solid line plus the dotted bonus-year leg
    assert len(fig.data) == len(TREND_SUBFIELDS) * k * 2
    dotted = [t for t in fig.data if t.line.dash == "dot"]
    assert len(dotted) == len(TREND_SUBFIELDS) * k
    for t in dotted:                    # the partial year's point is HOLLOW
        assert t.marker.color == P.SURFACE
    plain = X.fig_trends_small_multiples(frames, slots, TREND_SUBFIELDS, names=NAMES)
    assert len(plain.data) == len(TREND_SUBFIELDS) * k


def test_trends_needs_at_least_one_subfield(ids, slots):
    with pytest.raises(ValueError):
        X.fig_trends_small_multiples(trends_frames(ids), slots, [], names=NAMES)


def test_coverage_strip_is_the_one_stacked_bar(ids, slots, k):
    fig = X.fig_coverage_strip(coverage(ids), slots, names=NAMES)
    assert fig.layout.barmode == "stack"
    assert len(fig.data) == len(P.GREY_STATE_ORDER) == 6
    assert all(len(tr.x) == k for tr in fig.data)
    # the usable segment wears the institution's own colour; the five grey
    # states wear the ordinal ramp and nothing else
    first = fig.data[0]
    assert set(first.marker.color) == {P.institution_color(s) for s in slots.values()}
    greys = {c for tr in fig.data[1:] for c in tr.marker.color}
    assert greys == set(P.GREY_STATE_COLORS.values())
    # 2 px SURFACE gap between touching segments (the dataviz spacer)
    assert all(tr.marker.line.color == P.SURFACE for tr in fig.data)
    assert all(tr.marker.line.width == P.OUTLINE_WIDTH for tr in fig.data)


def test_legend_is_in_slot_order_and_names_every_institution(ids, slots, k):
    html = X.institution_legend_html({i: NAMES[i] for i in ids}, slots)
    order = [P.institution_color(n) for n in range(k)]
    positions = [html.index(c) for c in order]
    assert positions == sorted(positions)
    for i in ids:
        assert NAMES[i] in html


# ---------------------------------------------------------------------------
# Geometry: the A4 acceptance, satisfied by construction
# ---------------------------------------------------------------------------
def test_lane_split_is_all_or_nothing_and_lanes_are_slot_stable(ids, slots, k):
    """A dodged frame gives institution n the SAME lane in every row -- the
    property that makes a vertical position mean something."""
    fig = X.fig_mirror_dots(fields_long(ids), family="oa", slots=slots, names=NAMES)
    share_traces = fig.data[:k]
    for tr in share_traces:
        offsets = {round(y - round(y), 6) for y in tr.y}
        assert len(offsets) == 1, "one institution, one lane offset, every row"
    if k > 1:
        distinct = {round(list(tr.y)[0] - round(list(tr.y)[0]), 6) for tr in share_traces}
        assert len(distinct) == k, "each institution gets its own lane"


def test_lane_spacing_clears_the_overlap_acceptance(ids, slots, k):
    """Lanes are `LANE_PITCH_PX` apart in the row band, and the figure height is
    built so that one category unit is at least `k x LANE_PITCH_PX` -- so two
    marks of one row can never overlap by more than `OVERLAP_MAX`."""
    fig = X.fig_mirror_dots(fields_long(ids), family="oa", slots=slots, names=NAMES)
    n_rows = len(fig.layout.yaxis.ticktext)
    plot_px = fig.layout.height - C.BASE_PX - C.BASE_PX // 2
    pitch = plot_px / n_rows
    lane_gap_px = pitch / k if k > 1 else pitch
    assert lane_gap_px >= X.DOT_PX * X.OVERLAP_MAX
    assert X.DOT_PX >= X.MIN_MARK_PX


def test_single_lane_frame_is_exactly_as_tall_as_the_profile_panel():
    """A frame with no collision must not pay for the dodge."""
    ids2 = IDS[:2]
    df = fields_long(ids2)
    df.loc[df["institution_id"] == ids2[1], "share"] += 0.30   # far apart
    df.loc[df["institution_id"] == ids2[1], "si"] += 3.0
    fig = X.fig_mirror_dots(df, family="oa", slots=slots_for(2), names=NAMES)
    n = len(FIELDS)
    assert fig.layout.height == C.row_height(n)
    assert X.compare_row_height(n, 1) == C.row_height(n)
    assert X.compare_row_height(n, 6) > C.row_height(n)


def test_every_builder_paints_the_surface_and_hides_the_plotly_legend(ids, slots):
    figs = [X.fig_mirror_dots(fields_long(ids), family="oa", slots=slots, names=NAMES),
            X.fig_quadrant_mix(frontier_mix(ids), slots, names=NAMES),
            X.fig_frontier_overlay(frontier_points(ids), slots, names=NAMES),
            X.fig_frontier_small_multiples(frontier_points(ids), slots, names=NAMES),
            X.fig_impact_intervals(impact_index(ids), slots, names=NAMES),
            X.fig_impact_subfields(impact_subfields(ids), slots, names=NAMES),
            X.fig_trends_small_multiples(trends_frames(ids), slots, TREND_SUBFIELDS,
                                         names=NAMES),
            X.fig_coverage_strip(coverage(ids), slots, names=NAMES)]
    for fig in figs:
        assert fig.layout.paper_bgcolor == P.SURFACE
        assert fig.layout.plot_bgcolor == P.SURFACE
        assert fig.layout.showlegend is False
        assert all(tr.showlegend is False for tr in fig.data)


def test_missing_institution_is_absent_not_zero(ids, slots, k):
    """An institution with no row for a category gets NO mark there -- the
    n/a-never-zero rule (BUILD_PLAN_2A L11) at chart grain."""
    df = subfields_long(ids)
    fig = X.fig_mirror_dots(df, family="oa", slots=slots, names=NAMES)
    drawn = sum(len(tr.x) for tr in fig.data[:k])
    assert drawn == len(df)


# ---------------------------------------------------------------------------
# Source scans
# ---------------------------------------------------------------------------
def _string_literals(path: Path) -> list[tuple[int, str]]:
    """Every str constant EXCEPT docstrings -- the same collector
    `tests/test_charts.py` uses for `lib/charts.py`."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    doc_nodes: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                doc_nodes.add(id(body[0].value))
    return [(n.lineno, n.value) for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and id(n) not in doc_nodes]


def _deployed_column_names() -> set[str]:
    import pyarrow.parquet as pq
    names: set[str] = set()
    for f in sorted(DATA.glob("*.parquet")):
        names |= set(pq.read_schema(f).names)
    return names


def test_no_digit_in_any_charts_compare_string_literal():
    """The allowlist is loaded READ-ONLY and this stream adds nothing to it
    (wind-tunnel E15: the allowlist stays full at fifteen for the whole of 2B).
    Everything parametric is a caller-filled `{placeholder}` and every number
    format is composed from an int constant."""
    tokens = load_allowlist()
    columns = _deployed_column_names()
    assert "top25pct_frontier" in columns, "the column exemption must be grounded in real schemas"
    offenders = [(n, s) for n, s in _string_literals(MODULE)
                 if s not in columns and has_digit_violation(s, tokens)]
    assert not offenders, f"digit(s) inside a string literal of lib/charts_compare.py: {offenders}"


def test_charts_compare_takes_every_colour_from_palette():
    src = MODULE.read_text(encoding="utf-8")
    assert not re.search(r"#[0-9A-Fa-f]{6}\b", src)
    assert "from lib import palette as P" in src


def test_charts_compare_never_imports_streamlit():
    src = MODULE.read_text(encoding="utf-8")
    assert not re.search(r"^\s*import\s+streamlit", src, flags=re.MULTILINE)
    assert not re.search(r"^\s*from\s+streamlit", src, flags=re.MULTILINE)


def test_the_hex_scan_actually_covers_this_module():
    """Non-vacuity guard, the twin of `test_palette.py`'s for `charts.py`: the
    directory walk would pass trivially if this file vanished from it."""
    from tests.test_palette import ALLOWLIST, SCAN_DIRS
    scanned: list[Path] = []
    for d in SCAN_DIRS:
        if d.exists():
            scanned.extend(sorted(d.rglob("*.py")))
    assert MODULE in scanned
    assert MODULE not in ALLOWLIST


# ===========================================================================
# PHASE 2B-R (stream VS) -- the redesigned Compare / Collaborate builders
# ===========================================================================
# Same discipline as the 2B block above: frames are built INLINE from the
# BUILD_PLAN_2BR.md section 4 contracts, so the day `lib/compare_data.py` and
# `lib/collab_data.py` land their output drops in unchanged -- and if it does
# not, these fixtures are the statement of what the builders were promised.
#
# The cardinality changed and so did the fixtures: 2B-R-4 caps Compare at THREE
# institutions, so every builder below is exercised at k = 2 AND k = 3, plus one
# explicit refusal at k = 4.
TAXA = [(11, "Agricultural and Biological Sciences", 1),
        (12, "Arts and Humanities", 2),
        (16, "Chemistry", 3),
        (27, "Medicine", 4)]
ERC_PANELS = [(0, "LS9", "Biotechnology and Biosystems Engineering", "LS"),
              (5, "PE1", "Mathematics", "PE"),
              (9, "SH2", "Institutions, Values, Environment and Space", "SH")]


@pytest.fixture(params=[2, 3], ids=["k_two", "k_three"])
def kc(request) -> int:
    """The COMPARE cardinalities (2B-R-4), not the 2B basket ones."""
    return request.param


@pytest.fixture
def cslots(kc) -> dict:
    return slots_for(kc)


@pytest.fixture
def cids(kc) -> list:
    return IDS[:kc]


def metric_frame(ids, *, ref=None, level="field", hole=True) -> pd.DataFrame:
    rows = []
    for n, iid in enumerate(ids):
        for m, (tid, label, dom) in enumerate(TAXA):
            if hole and n == 0 and m == len(TAXA) - 1:
                continue                       # the missing cell: n/a, never zero
            rows.append(dict(institution_id=iid, taxon_id=tid, taxon_label=label,
                             domain_id=dom,
                             value=0.0 if (n == 1 and m == 0) else 0.05 + 0.03 * m + 0.004 * n,
                             ref_value=(ref if not callable(ref) else ref(m)),
                             denominator=1000 + 10 * m + n))
    d = pd.DataFrame(rows)
    if level == "erc":
        d["taxon_id"] = d["taxon_id"].map({t[0]: p[0] for t, p in zip(TAXA, ERC_PANELS + [ERC_PANELS[0]])})
        d["taxon_label"] = d["taxon_id"].map({p[0]: p[2] for p in ERC_PANELS})
        d["erc_domain"] = d["taxon_id"].map({p[0]: p[3] for p in ERC_PANELS})
        d = d.dropna(subset=["taxon_label"])
    if level == "sdg":
        d["sdg_number"] = (d["taxon_id"] % 7) + 1
        d["taxon_id"] = d["sdg_number"]
        d["taxon_label"] = ["SDG " + str(g) for g in d["sdg_number"]]
    return d.reset_index(drop=True)


def pooled_points(ids) -> pd.DataFrame:
    rng = np.random.default_rng(11)
    rows = []
    owners = list(ids) + [X.SHARED_OWNER]
    for t in range(24):
        rows.append(dict(topic_id=9000 + t, name=f"Topic {t}",
                         x=float(rng.normal(0.6, 0.9)), y=float(rng.normal(0.4, 0.7)),
                         combined_vol=float(10 + 3 * t),
                         owner=owners[t % len(owners)],
                         top25pct_frontier=bool(t % 3 == 0)))
    out = pd.DataFrame(rows)
    out.loc[0, "x"] = np.nan             # an unscored topic must be dropped
    return out


def shared_long(ids) -> pd.DataFrame:
    """The 20:1 imbalance A/B #8 is about, plus a balanced row and a hole."""
    rows = []
    for t in range(5):
        for n, iid in enumerate(ids):
            if t == 4 and n == 0:
                continue
            vol = (20.0 if n == 0 else 1.0) if t == 0 else float(6 + t + n)
            rows.append(dict(institution_id=iid, topic_id=8000 + t,
                             name=f"Shared topic {t}", vol=vol))
    return pd.DataFrame(rows)


PULSE_YEARS = ["2020", "2021", "2022", "2023", "2024", "2025"]


def pulse_frame() -> pd.DataFrame:
    return pd.DataFrame({"year": PULSE_YEARS,
                         "co_pubs": [12.0, 15.0, 0.0, 19.0, 22.0, 9.0]})


# --------------------------------------------------------- fig_metric_bars ---
def test_metric_bars_render_for_every_metric(cids, cslots, kc):
    for metric in X.METRICS:
        fig = X.fig_metric_bars(metric_frame(cids), metric, cids, slots=cslots,
                                names=NAMES, level="field")
        assert len(fig.data) == kc, metric
        assert fig.layout.barmode == "overlay"
        assert fig.layout.paper_bgcolor == P.SURFACE
        assert fig.layout.showlegend is False
        assert len(fig.layout.yaxis.ticktext) == len(TAXA)


def test_metric_bars_refuse_a_fourth_institution():
    """2B-R-4 is a HARD cap and the builder refuses rather than truncating: a
    figure that silently drew three of four would disagree with its own
    caption, legend and export."""
    ids4 = IDS[:4]
    with pytest.raises(ValueError):
        X.fig_metric_bars(metric_frame(ids4), "share", ids4, slots=slots_for(4),
                          names=NAMES)
    with pytest.raises(ValueError):
        X.fig_metric_bars(metric_frame(IDS[:2]), "breadth", IDS[:2], slots=slots_for(2))
    with pytest.raises(ValueError):
        X.fig_metric_bars(metric_frame(IDS[:2]), "share", IDS[:2], slots=slots_for(2),
                          level="topic")


def test_every_drawn_bar_carries_its_value_label(cids, cslots):
    """The one thing the k = 6 dot mirror could not do, and the reason A/B #7
    reopened the form question: the number is ON the mark."""
    d = metric_frame(cids)
    fig = X.fig_metric_bars(d, "share", cids, slots=cslots, names=NAMES)
    drawn = sum(len(tr.x) for tr in fig.data)
    labelled = sum(len(tr.text) for tr in fig.data)
    assert drawn == labelled == len(d)
    assert all(tr.textposition == "outside" for tr in fig.data)
    assert all(t for tr in fig.data for t in tr.text), "no label may be empty"


def test_metric_bars_missing_cell_is_absent_and_a_real_zero_is_labelled(cids, cslots):
    """n/a never zero (BUILD_PLAN_2A L11) at chart grain -- and its converse:
    a measured zero must still be visible as a number."""
    d = metric_frame(cids)
    fig = X.fig_metric_bars(d, "share", cids, slots=cslots, names=NAMES)
    assert sum(len(tr.x) for tr in fig.data) == len(d) == len(TAXA) * len(cids) - 1
    zeros = [(x, t) for tr in fig.data for x, t in zip(tr.x, tr.text) if x == 0]
    assert len(zeros) == 1 and zeros[0][1], "a genuine zero keeps its value label"


def test_metric_bars_colour_is_the_institution_and_only_the_institution(cids, cslots):
    fig = X.fig_metric_bars(metric_frame(cids), "share", cids, slots=cslots, names=NAMES)
    wanted = {P.institution_color(s) for s in cslots.values()}
    assert {tr.marker.color for tr in fig.data} == wanted
    assert all(tr.marker.line.color == P.SURFACE for tr in fig.data)


def test_metric_bars_never_thinner_than_the_target(cids, cslots, kc):
    """`BAR_PX` is an arithmetic property of `metric_row_height`, not a hope
    about the row count -- the 2B wind tunnel's 2.6 px bars were the same
    picture drawn into a band sized for dots."""
    for n_rows in (4, 26, 60):
        h = X.metric_row_height(n_rows, kc)
        plot = h - C.BASE_PX - C.BASE_PX // 2
        one_bar = (plot / n_rows) * X.BAR_GROUP_SPAN * X.BAR_GROUP_FILL / kc
        assert one_bar >= X.MIN_MARK_PX, (n_rows, kc, one_bar)
    assert X.BAR_PX >= X.MIN_MARK_PX


# ------------------------------------------------------- the label accents ---
def test_erc_and_sdg_labels_carry_the_official_taxonomy_accent(cids, cslots):
    """2B-R-8: taxonomy colour on the ROW LABEL, institution colour on the
    MARK, and never the reverse."""
    for level, expected in (("erc", set(P.ERC_DOMAIN_COLORS.values())),
                            ("sdg", set(P.SDG_COLORS.values()))):
        fig = X.fig_metric_bars(metric_frame(cids, level=level), "share", cids,
                                slots=cslots, names=NAMES, level=level)
        ticks = "".join(fig.layout.yaxis.ticktext)
        assert X.ACCENT_GLYPH in ticks
        assert any(c in ticks for c in expected), level
        # the one-way rule: no institution hue ever reaches a label
        for s in cslots.values():
            assert P.institution_color(s) not in ticks


def test_field_and_subfield_labels_take_no_accent(cids, cslots):
    """A family with no OFFICIAL colour borrows none -- an accent is worth its
    ink only where the reader already knows the palette from outside the app."""
    for level in ("field", "subfield"):
        fig = X.fig_metric_bars(metric_frame(cids), "share", cids, slots=cslots,
                                names=NAMES, level=level)
        assert X.ACCENT_GLYPH not in "".join(fig.layout.yaxis.ticktext)


def test_label_accent_resolver_is_the_one_entry_point():
    assert P.label_accent_color("erc", "PE") == P.ERC_DOMAIN_COLORS["PE"]
    assert P.label_accent_color("sdg", 7) == P.SDG_COLORS[7]
    for family in ("oa", "doctype", "institution", None):
        assert P.label_accent_color(family, 1) == P.COMPARISON
    assert set(P.LABEL_ACCENT_FAMILIES) == {"erc", "sdg"}


# ---------------------------------------------------------- the reference ---
def test_constant_reference_is_one_rule_and_a_varying_one_is_per_row(cids, cslots):
    flat = X.fig_metric_bars(metric_frame(cids, ref=0.06), "share", cids,
                             slots=cslots, names=NAMES)
    rules = [s for s in flat.layout.shapes
             if s.type == "line" and getattr(s.line, "dash", None) == "dash"]
    varying = X.fig_metric_bars(metric_frame(cids, ref=lambda m: 0.02 + 0.01 * m),
                                "share", cids, slots=cslots, names=NAMES)
    dashes = [s for s in varying.layout.shapes
              if s.type == "line" and getattr(s.line, "dash", None) == "dash"]
    assert len(rules) == 1, "a constant reference is ONE rule across the panel"
    assert len(dashes) == len(TAXA), "a varying reference is one dash per row"
    # ...and the per-row dashes really do sit at different x values
    assert len({round(float(s.x0), 6) for s in dashes}) == len(TAXA)


def test_si_defaults_to_the_neutral_reference_and_volume_invents_none(cids, cslots):
    si = X.fig_metric_bars(metric_frame(cids), "si", cids, slots=cslots, names=NAMES)
    assert any(s.type == "line" and s.x0 == C.SI_NEUTRAL for s in si.layout.shapes)
    bare = metric_frame(cids).drop(columns=["ref_value"])
    vol = X.fig_metric_bars(bare, "vol_top10", cids, slots=cslots, names=NAMES)
    assert not [s for s in vol.layout.shapes if getattr(s.line, "dash", None) == "dash"]


def test_a_signed_metric_gets_the_bold_zero_and_a_two_sided_range(cids, cslots):
    d = metric_frame(cids)
    d.loc[d.index % 2 == 0, "value"] = -d["value"]
    fig = X.fig_metric_bars(d, "dynamics", cids, slots=cslots, names=NAMES)
    assert fig.layout.xaxis.range[0] < 0
    bold = [s for s in fig.layout.shapes
            if s.line.color == P.INK and s.line.width == X.BOLD_AXIS_PX]
    assert len(bold) == 1


# --------------------------------------------------------- the pooled map ---
def test_frontier_map_draws_each_topic_once(cids, cslots):
    d = pooled_points(cids)
    fig = X.fig_frontier_map(d, slots=cslots, names=NAMES)
    assert sum(len(tr.x) for tr in fig.data) == len(d) - 1   # the unscored one
    colors = {tr.marker.color for tr in fig.data}
    assert P.SHARED_FRONTIER in colors
    assert colors - {P.SHARED_FRONTIER} <= {P.institution_color(s) for s in cslots.values()}


def test_frontier_map_has_bold_black_origin_rules_that_stay_in_range(cids, cslots):
    fig = X.fig_frontier_map(pooled_points(cids), slots=cslots, names=NAMES)
    bold = [s for s in fig.layout.shapes
            if s.line.color == P.INK and s.line.width == X.BOLD_AXIS_PX]
    assert len(bold) == 2
    for axis in (fig.layout.xaxis, fig.layout.yaxis):
        assert axis.range[0] <= C.FRONTIER_ORIGIN <= axis.range[1]


def test_frontier_map_top_n_keeps_the_largest_and_the_shared_cloud_is_on_top(cids, cslots):
    fig = X.fig_frontier_map(pooled_points(cids), 10, slots=cslots, names=NAMES)
    assert sum(len(tr.x) for tr in fig.data) == 10
    assert fig.data[-1].marker.color == P.SHARED_FRONTIER
    for tr in fig.data:
        assert float(np.min(tr.marker.size)) >= X.MIN_MARK_PX
        assert set(tr.marker.line.color) <= {P.INK, P.SURFACE}


# ------------------------------------------------- the shared-frontier bars ---
def test_diverging_at_two_institutions_puts_one_side_left_of_zero(cslots):
    ids2 = IDS[:2]
    slots2 = slots_for(2)
    fig = X.fig_diverging_shared(shared_long(ids2), ids2, slots=slots2, names=NAMES)
    assert len(fig.data) == 2
    assert min(fig.data[0].x) < 0 and min(fig.data[1].x) >= 0
    # the ticks carry ABSOLUTE values: a negative count would be a lie
    assert all(not str(t).startswith("-") for t in fig.layout.xaxis.ticktext)
    bold = [s for s in fig.layout.shapes
            if s.line.color == P.INK and s.line.width == X.BOLD_AXIS_PX]
    assert len(bold) == 1


def test_grouped_at_three_institutions_and_refused_at_four():
    ids3, ids4 = IDS[:3], IDS[:4]
    fig = X.fig_diverging_shared(shared_long(ids3), ids3, slots=slots_for(3), names=NAMES)
    assert len(fig.data) == 3
    assert all(x >= 0 for tr in fig.data for x in tr.x)
    with pytest.raises(ValueError):
        X.fig_diverging_shared(shared_long(ids4), ids4, slots=slots_for(4), names=NAMES)


def test_shared_rows_rank_by_combined_volume_and_a_hole_stays_a_hole():
    ids2 = IDS[:2]
    d = shared_long(ids2)
    fig = X.fig_diverging_shared(d, ids2, slots=slots_for(2), names=NAMES)
    assert sum(len(tr.x) for tr in fig.data) == len(d)
    top = d.groupby("topic_id")["vol"].sum().idxmax()
    assert d[d["topic_id"] == top]["name"].iloc[0] in str(fig.layout.yaxis.ticktext[0])


# ---------------------------------------------------------------- the pulse ---
def test_pulse_marks_the_partial_year_hollow_and_stars_its_tick():
    fig = X.fig_pulse(pulse_frame(), bonus_year=PULSE_YEARS[-1])
    assert len(fig.data) == 2
    full, bonus = fig.data
    assert full.marker.color == P.SHARED_FRONTIER
    assert bonus.marker.color == P.SURFACE
    assert bonus.marker.line.color == P.SHARED_FRONTIER
    assert list(fig.layout.xaxis.ticktext)[-1] == PULSE_YEARS[-1] + X.PARTIAL_YEAR_GLYPH
    assert list(fig.layout.xaxis.ticktext)[0] == PULSE_YEARS[0]


def test_pulse_keeps_a_real_zero_year_on_the_axis():
    fig = X.fig_pulse(pulse_frame())
    assert sum(len(tr.x) for tr in fig.data) == len(PULSE_YEARS)
    assert 0.0 in list(fig.data[0].y)
    assert fig.layout.showlegend is False


def test_pulse_wears_no_institution_colour():
    """The joint corpus belongs to neither side, so it takes the one hue no
    institution owns."""
    fig = X.fig_pulse(pulse_frame(), bonus_year=PULSE_YEARS[-1])
    used = {tr.marker.color for tr in fig.data} | {tr.marker.line.color for tr in fig.data}
    assert not (used & set(P.INSTITUTION_COLORS))


# --------------------------------------------------------- the legend strip ---
def test_legend_strip_is_slot_ordered_and_can_name_the_shared_hue(cids, cslots, kc):
    html = X.legend_strip(cids, slots=cslots, names=NAMES, shared=True)
    order = [P.institution_color(n) for n in range(kc)] + [P.SHARED_FRONTIER]
    assert [html.index(c) for c in order] == sorted(html.index(c) for c in order)
    for i in cids:
        assert NAMES[i] in html
    assert X.LABEL_SHARED in html
    assert P.SHARED_FRONTIER not in X.legend_strip(cids, slots=cslots, names=NAMES)


def test_every_2br_builder_paints_the_surface_and_hides_the_plotly_legend(cids, cslots):
    figs = [X.fig_metric_bars(metric_frame(cids), "share", cids, slots=cslots, names=NAMES),
            X.fig_frontier_map(pooled_points(cids), slots=cslots, names=NAMES),
            X.fig_diverging_shared(shared_long(cids), cids, slots=cslots, names=NAMES),
            X.fig_pulse(pulse_frame(), bonus_year=PULSE_YEARS[-1])]
    for fig in figs:
        assert fig.layout.paper_bgcolor == P.SURFACE
        assert fig.layout.plot_bgcolor == P.SURFACE
        assert fig.layout.showlegend is False
        assert all(tr.showlegend is False for tr in fig.data)


# ----------------------------------------------------------- palette additions ---
def test_shared_frontier_is_not_an_institution_and_not_chrome():
    upper = {c.upper() for c in P.INSTITUTION_COLORS}
    assert P.SHARED_FRONTIER.upper() not in upper
    assert P.SHARED_FRONTIER.upper() != P.FOCAL.upper()
    assert P.SHARED_FRONTIER.upper() != P.COMPARISON.upper()
    others = ([v.upper() for v in P.OA_DOMAIN_COLORS.values()]
              + [v.upper() for v in P.ERC_DOMAIN_COLORS.values()]
              + [v.upper() for v in P.DOCTYPE_COLORS.values()]
              + [v.upper() for v in P.SDG_COLORS.values()]
              + [v.upper() for v in P.GREY_STATE_COLORS.values()])
    assert P.SHARED_FRONTIER.upper() not in others
    assert P.institution_color(P.INSTITUTION_SLOT_MAX) != P.SHARED_FRONTIER


def test_viz_spec_has_rejected_alternative_per_2br_view_row():
    """Section 2 quater carries the same obligation as sections 2 and 2 ter."""
    spec = (APP_DIR / "docs" / "VIZ_SPEC.md").read_text(encoding="utf-8")
    rows_2br = len(re.findall(r"^### 4\.\d+", spec, flags=re.MULTILINE))
    assert rows_2br >= 8, f"expected the 2B-R view rows in VIZ_SPEC, found {rows_2br}"
    find_rows = len(re.findall(r"^### 2\.\d+", spec, flags=re.MULTILINE))
    compare_rows = len(re.findall(r"^### 3\.\d+", spec, flags=re.MULTILINE))
    assert spec.count("Rejected alternative:") >= find_rows + compare_rows + rows_2br

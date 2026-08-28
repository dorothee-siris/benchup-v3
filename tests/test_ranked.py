"""
Tests for `lib/ranked.py` (BUILD_PLAN_2A.md Stream D1, eval tier B).

Pure-function tests only (`format_rows`, `depth_caption`, `format_concordance`,
`concordance_caption`) -- no Streamlit server, run directly:
    python -m pytest tests/test_ranked.py -q
"""
from __future__ import annotations

import math
from pathlib import Path

import pytest

from lib.app_config import CFG
from lib.engine import DEFAULT_LENSES, build_rows, build_substrates, concordance, load_context, rank_all
from lib.ranked import concordance_caption, depth_caption, format_concordance, format_rows

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
SEED = "I40413290"  # University of Gdansk
DEPTH = 30
N = 30
WINDOW_START, WINDOW_END = CFG["window"]


@pytest.fixture(scope="module")
def engine():
    ctx = load_context(DATA_DIR)
    subs = build_substrates(ctx)
    r = rank_all(ctx, subs, SEED)
    return ctx, r


@pytest.fixture(scope="module")
def l1_rows(engine):
    ctx, r = engine
    return build_rows(r["L1"], ctx, DEPTH, r)


def test_format_rows_row_count_and_ranks(l1_rows):
    df = format_rows(l1_rows, lens="L1", depth=DEPTH)
    assert len(df) >= DEPTH  # DEPTH rows, or more if ties extend the cut (never fewer)
    ranks = df["rank"].tolist()
    assert ranks[0] == 1
    # competition ranks: non-decreasing, gaps only where ties precede
    for prev, cur in zip(ranks, ranks[1:]):
        assert cur >= prev
    # gaps are only ever (number of rows tied at prev rank), never an arbitrary jump
    seen = {}
    for rk in ranks:
        seen[rk] = seen.get(rk, 0) + 1
    expected_next = 1
    for rk in sorted(seen):
        assert rk == expected_next, f"rank {rk} is not a valid competition rank position"
        expected_next = rk + seen[rk]


def test_format_rows_link_has_seed_free_id_and_window_years(l1_rows):
    df = format_rows(l1_rows, lens="L1", depth=DEPTH)
    assert SEED not in df["institution_id"].tolist(), "self must be excluded (rank_all excludes seed)"
    for link, iid in zip(df["institution_link"], df["institution_id"]):
        assert iid in link
        assert f"{WINDOW_START}-{WINDOW_END}" in link
        assert "authorships.institutions.id:" in link


def test_format_rows_no_nan_score_and_str_type(l1_rows):
    df = format_rows(l1_rows, lens="L1", depth=DEPTH)
    assert df["score"].notna().all()
    assert df["score"].between(0, 1, inclusive="both").all()
    assert df["type"].map(lambda v: isinstance(v, str)).all()
    assert df["type"].dtype == object


def test_depth_caption_parametric():
    cap = depth_caption(30, 7556, 30)
    assert "30" in cap
    assert "7556" in cap
    other_digits = [c for c in cap if c.isdigit()]
    # every digit present must belong to one of the two numbers passed in
    allowed = set("30") | set("7556")
    assert set(other_digits) <= allowed
    # and both full numbers appear as substrings, not just their digits scattered
    assert "top 30" in cap
    assert "of 7556" in cap


def test_depth_caption_with_ties():
    cap = depth_caption(32, 7556, 30, n_tied_extra=2)
    assert "32" in cap and "7556" in cap and "30" in cap and "2" in cap


@pytest.fixture(scope="module")
def conc_rows(engine):
    ctx, r = engine
    return concordance(ctx, r, DEFAULT_LENSES, N)


def test_format_concordance_k_le_n_and_hit_list_len(conc_rows):
    df = format_concordance(conc_rows, lenses=DEFAULT_LENSES, N=N)
    assert len(df) > 0
    n_lenses = len(DEFAULT_LENSES)
    for _, row in df.iterrows():
        assert 1 <= row["k"] <= row["n"] <= n_lenses
        hit_list = [h for h in row["hit_lenses"].split(", ") if h]
        assert len(hit_list) == row["k"]


def test_concordance_caption_parametric():
    cap = concordance_caption(8, 30, 50)
    assert "8" in cap and "30" in cap and "50" in cap

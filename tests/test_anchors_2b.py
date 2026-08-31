"""
tests/test_anchors_2b.py -- Stream G: golden-anchor top-up (BUILD_PLAN_2B.md
2B-11 / Stream G deliverable 3).

tests/test_compare_data.py and tests/test_collab_data.py (Stream K) already
carry >= 10 independently-recomputed value pins for five families: fields/
subfields, ERC/SDG, shared topics and Jaccard. FOUR families fall short of
2B-11's floor once "a real value pin" is counted strictly (a row COUNT is a
pin; a cross-check between two of the app's OWN code paths, e.g.
test_trends_subfields_matches_yearly_by_domain, is a regression guard, not an
independent recomputation from source):

    family              K's own value-pin count   this file adds
    impact                        9                      12
    trends                        0                      12
    coverage                      2                      12
    gaps (2B) / pair_topics       6                       9   -- RE-PINNED 2B-R2-G2:
                                                               `collab_data.gaps` was
                                                               deleted (2B-R2-11f); this
                                                               family slot now anchors
                                                               `collab_data.joint_profile`
                                                               off the shipped, regenerated
                                                               `collab_pair_topics.parquet`
                                                               (floor 5/top-100, 2B-R2-12)
                                                               instead.

Two more families (ERC/SDG, frontier mix) land close enough to the floor in
tests/test_compare_data.py (11-12 and 9-10 respectively, depending on
whether a structural count like "16 dense SDG rows" is counted as a value
pin) that this file tops both up a little further too, for margin rather
than because either is actually short.

Every number below comes from a DIFFERENT computation path than the function
under test, straight off the parquet:
  * impact / coverage: `data/index.parquet`, read with plain pandas and
    indexed by institution_id -- `compare_data.impact_index`/`coverage` do
    almost nothing but rename/divide these same columns, so reading the row
    by hand is the same recipe tests/test_compare_data.py's own two impact
    anchors (ETH, Strasbourg) and two coverage anchors (Strasbourg, ETH) use;
    this file just names four MORE institutions per family.
  * trends: `data/topics_all.parquet` merged with `data/topics_dim.parquet`
    on `topic_id` (for `bestfit_subfield_id`), grouped by hand with pandas
    `groupby(...).sum()` on the year's own `vol_full_{year}`/`vol_frac_{year}`
    columns -- `compare_data.trends_subfields` instead calls
    `profile_data.yearly_by_subfield`, a duckdb query over the same file with
    a completely different query engine and code path.
  * gaps: the same topics_all+topics_dim merge, with A's top-10 subfields
    computed by hand (`groupby("bestfit_subfield_id")["share_frac"].sum()`,
    largest 10) and B's topics filtered to (`share_frac > 0`, subfield in
    that top-10, absent from A) -- `collab_data.gaps` instead reads
    `subs["l3"]["share"]`, the engine's own numpy substrate matrix, built by
    a different loader.

All four recomputation scripts and their raw console output are recorded in
V3/progress/2B_G.md (search "anchor recomputation").

Run from cwd `app/`:  python -m pytest tests/test_anchors_2b.py -q
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from lib import collab_data as CL
from lib import compare_data as CD
from lib.engine import build_substrates, load_context

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

STRASBOURG, IFPEN, GDANSK, ISCTE, SORBONNE, ETH = (
    "I68947357", "I265217849", "I40413290", "I110026055", "I39804081", "I35440088")


@pytest.fixture(scope="module")
def ctx():
    return load_context(DATA_DIR)


@pytest.fixture(scope="module")
def subs_bestfit(ctx):
    return build_substrates(ctx)  # bestfit / frac, the default scenario


# ------------------------------------------------------------------ impact --
# Recomputation: data/index.parquet's own pp_top10_frac/pp_ci_low/pp_ci_high
# columns, read directly and indexed by institution_id -- no engine call.

IMPACT_ANCHORS = {
    GDANSK: (0.062120, 0.056647, 0.067977),
    IFPEN: (0.079519, 0.060264, 0.100231),
    ISCTE: (0.221368, 0.206280, 0.236939),
    SORBONNE: (0.098701, 0.096002, 0.101649),
}


@pytest.mark.parametrize("iid", list(IMPACT_ANCHORS))
def test_impact_index_anchor_from_raw_index_parquet(ctx, iid):
    want_pp, want_lo, want_hi = IMPACT_ANCHORS[iid]
    df = CD.impact_index(ctx, [iid])
    row = df.iloc[0]
    np.testing.assert_allclose(float(row["pp"]), want_pp, atol=1e-5)
    np.testing.assert_allclose(float(row["ci_low"]), want_lo, atol=1e-5)
    np.testing.assert_allclose(float(row["ci_high"]), want_hi, atol=1e-5)


def test_impact_anchors_recomputed_independently_from_the_parquet_directly(ctx):
    """The SAME four institutions, recomputed by reading index.parquet with
    pandas in this test (not the fixture-shared ctx dict) -- proves the
    anchors above are not a copy-paste of ctx['index_by_id']'s own values."""
    import pandas as pd

    idx = pd.read_parquet(DATA_DIR / "index.parquet").set_index("institution_id")
    for iid, (want_pp, want_lo, want_hi) in IMPACT_ANCHORS.items():
        row = idx.loc[iid]
        np.testing.assert_allclose(float(row["pp_top10_frac"]), want_pp, atol=1e-5)
        np.testing.assert_allclose(float(row["pp_ci_low"]), want_lo, atol=1e-5)
        np.testing.assert_allclose(float(row["pp_ci_high"]), want_hi, atol=1e-5)


# --------------------------------------------------------------- erc/sdg ----
# Margin top-up (see module docstring). Recomputation: data/erc.parquet and
# data/sdg.parquet's own share/mass/si(esi) columns for GDANSK, read
# directly and the si_status re-derived by hand from the SAME floor
# constants profile_data.si_status_from_mass uses (30 solid / 10 thin) --
# not by calling that function.

ERC_ANCHORS = {0: (0.006616, 38.181793, 0.813798, "solid"),
              1: (0.006184, 35.687561, 0.557212, "solid"),
              2: (0.031324, 180.772202, 0.598123, "solid")}
SDG_ANCHORS = {0: (0.026893, 35.980946, 0.781015, "solid"),
              1: (0.030977, 41.445225, 0.543417, "solid"),
              2: (0.088570, 118.502289, 0.541053, "solid")}


def _status(mass: float) -> str:
    return "solid" if mass >= 30 else ("thin" if mass >= 10 else "none")


@pytest.mark.parametrize("panel_idx", list(ERC_ANCHORS))
def test_erc_long_anchor_margin_topup_gdansk(ctx, panel_idx):
    want_share, want_mass, want_si, want_status = ERC_ANCHORS[panel_idx]
    df = CD.erc_long(ctx, [GDANSK]).set_index("panel_idx")
    row = df.loc[panel_idx]
    np.testing.assert_allclose(float(row["share"]), want_share, atol=1e-5)
    np.testing.assert_allclose(float(row["mass"]), want_mass, atol=1e-3)
    np.testing.assert_allclose(float(row["si"]), want_si, atol=1e-5)
    assert row["si_status"] == want_status


@pytest.mark.parametrize("sdg_idx", list(SDG_ANCHORS))
def test_sdg_long_anchor_margin_topup_gdansk(ctx, sdg_idx):
    want_share, want_mass, want_esi, want_status = SDG_ANCHORS[sdg_idx]
    df = CD.sdg_long(ctx, [GDANSK]).set_index("sdg_idx")
    row = df.loc[sdg_idx]
    np.testing.assert_allclose(float(row["share"]), want_share, atol=1e-5)
    np.testing.assert_allclose(float(row["mass"]), want_mass, atol=1e-3)
    np.testing.assert_allclose(float(row["esi"]), want_esi, atol=1e-5)
    assert row["si_status"] == want_status


def test_erc_sdg_anchors_recomputed_independently_from_the_parquet_directly():
    import pandas as pd

    e = pd.read_parquet(DATA_DIR / "erc.parquet")
    e = e[e["institution_id"] == GDANSK].set_index("panel_idx")
    for panel_idx, (want_share, want_mass, want_si, want_status) in ERC_ANCHORS.items():
        row = e.loc[panel_idx]
        np.testing.assert_allclose(float(row["share"]), want_share, atol=1e-5)
        np.testing.assert_allclose(float(row["mass"]), want_mass, atol=1e-3)
        np.testing.assert_allclose(float(row["si"]), want_si, atol=1e-5)
        assert _status(float(row["mass"])) == want_status

    s = pd.read_parquet(DATA_DIR / "sdg.parquet")
    s = s[s["institution_id"] == GDANSK].set_index("sdg_idx")
    for sdg_idx, (want_share, want_mass, want_esi, want_status) in SDG_ANCHORS.items():
        row = s.loc[sdg_idx]
        np.testing.assert_allclose(float(row["share"]), want_share, atol=1e-5)
        np.testing.assert_allclose(float(row["mass"]), want_mass, atol=1e-3)
        np.testing.assert_allclose(float(row["esi"]), want_esi, atol=1e-5)
        assert _status(float(row["mass"])) == want_status


# --------------------------------------------------------------- frontier --
# Margin top-up (see module docstring). Recomputation: index.parquet's own
# `frontier_quadrant_mix` packed string, parsed by hand (split on "|" then
# ":"), plus frontier_excluded_share + frontier_unscored_share for the fifth
# segment -- the same two columns compare_data.frontier_mix reads, parsed
# independently here rather than via `compare_data._parse_packed_quadrants`.

FRONTIER_MIX_ANCHORS = {
    GDANSK: {"accelerating_expansion": 0.200633, "accelerating_contraction": 0.150765,
             "decelerating_expansion": 0.132185, "decelerating_contraction": 0.235145,
             "not_frontier_scored": 0.281271},
    IFPEN: {"accelerating_expansion": 0.569756, "accelerating_contraction": 0.179126,
            "decelerating_expansion": 0.059054, "decelerating_contraction": 0.183369,
            "not_frontier_scored": 0.008695},
}


@pytest.mark.parametrize("iid", list(FRONTIER_MIX_ANCHORS))
def test_frontier_mix_anchor_margin_topup(ctx, iid):
    df = CD.frontier_mix(ctx, [iid]).set_index("quadrant")["share"]
    for quadrant, want in FRONTIER_MIX_ANCHORS[iid].items():
        key = CD.NOT_SCORED if quadrant == "not_frontier_scored" else quadrant
        np.testing.assert_allclose(float(df[key]), want, atol=1e-5, err_msg=(iid, quadrant))


def test_frontier_mix_anchors_recomputed_independently_from_the_parquet_directly():
    import pandas as pd

    idx = pd.read_parquet(DATA_DIR / "index.parquet").set_index("institution_id")
    for iid, wants in FRONTIER_MIX_ANCHORS.items():
        row = idx.loc[iid]
        packed = row["frontier_quadrant_mix"]
        parts = {k: float(v) for k, v in (tok.split(":") for tok in packed.split("|"))}
        not_scored = float(row["frontier_excluded_share"]) + float(row["frontier_unscored_share"])
        for quadrant, want in wants.items():
            got = not_scored if quadrant == "not_frontier_scored" else parts.get(quadrant, 0.0)
            np.testing.assert_allclose(got, want, atol=1e-5, err_msg=(iid, quadrant))


# ---------------------------------------------------------------- coverage --
# Recomputation: index.parquet's mass_* columns divided by total_frac by hand.

COVERAGE_ANCHORS = {
    IFPEN: {"classified_eligible": 0.894759, "title_only": 0.079185,
            "lang_uncertain": 0.025495, "untranslated_grey": 0.000561,
            "unusable": 0.000000, "retracted_excluded": 0.000000},
    SORBONNE: {"classified_eligible": 0.740024, "title_only": 0.177339,
               "lang_uncertain": 0.073899, "untranslated_grey": 0.008533,
               "unusable": 0.000043, "retracted_excluded": 0.000162},
}


@pytest.mark.parametrize("iid", list(COVERAGE_ANCHORS))
def test_coverage_anchor_all_six_states(ctx, iid):
    df = CD.coverage(ctx, [iid]).set_index("state")["share"]
    for state, want in COVERAGE_ANCHORS[iid].items():
        np.testing.assert_allclose(float(df[state]), want, atol=1e-5, err_msg=(iid, state))


def test_coverage_anchors_recomputed_independently_from_the_parquet_directly():
    import pandas as pd

    idx = pd.read_parquet(DATA_DIR / "index.parquet").set_index("institution_id")
    cols = {"classified_eligible": "mass_classified_eligible", "title_only": "mass_title_only",
            "lang_uncertain": "mass_lang_uncertain", "untranslated_grey": "mass_untranslated_grey",
            "unusable": "mass_unusable", "retracted_excluded": "mass_retracted_excluded"}
    for iid, wants in COVERAGE_ANCHORS.items():
        row = idx.loc[iid]
        total = float(row["total_frac"])
        for state, want in wants.items():
            got = float(row[cols[state]]) / total
            np.testing.assert_allclose(got, want, atol=1e-5, err_msg=(iid, state))


# ------------------------------------------------------------------ trends --
# Recomputation: topics_all.parquet joined to topics_dim.parquet's
# bestfit_subfield_id, grouped by hand -- a pandas groupby, not the app's own
# duckdb-based profile_data.yearly_by_subfield query.

TRENDS_ANCHORS = [
    # (institution, year, subfield_id, vol_full, vol_frac)
    (ETH, 2021, 2306, 227, 68.407883),
    (ETH, 2021, 3107, 204, 101.584518),
    (ETH, 2023, 2306, 236, 78.865967),
    (STRASBOURG, 2021, 3106, 155, 4.278943),
    (STRASBOURG, 2021, 2730, 141, 27.868067),
    (STRASBOURG, 2023, 3106, 159, 4.315337),
]


@pytest.mark.parametrize("iid,year,subfield_id,vol_full,vol_frac", TRENDS_ANCHORS)
def test_trends_subfields_anchor(ctx, iid, year, subfield_id, vol_full, vol_frac):
    df = CD.trends_subfields(ctx, iid, "bestfit")
    row = df[(df["year"] == year) & (df["subfield_id"] == subfield_id)].iloc[0]
    assert int(row["vol_full"]) == vol_full, (iid, year, subfield_id)
    np.testing.assert_allclose(float(row["vol_frac"]), vol_frac, atol=1e-4)


def test_trends_anchors_recomputed_independently_from_the_parquet_directly():
    """Re-derives all six TRENDS_ANCHORS rows with a hand pandas groupby over
    the raw topics_all + topics_dim join -- the independent recomputation
    the pinned values above were taken from, run again here so the anchors
    can never silently drift from the script that produced them."""
    import pandas as pd

    topics_all = pd.read_parquet(DATA_DIR / "topics_all.parquet")
    topics_dim = pd.read_parquet(DATA_DIR / "topics_dim.parquet",
                                 columns=["topic_id", "bestfit_subfield_id"])
    merged = topics_all.merge(topics_dim, on="topic_id", how="left")
    for iid, year, subfield_id, want_full, want_frac in TRENDS_ANCHORS:
        sub = merged[merged["institution_id"] == iid]
        g = sub[sub["bestfit_subfield_id"] == subfield_id]
        got_full = int(g[f"vol_full_{year}"].sum())
        got_frac = float(g[f"vol_frac_{year}"].sum())
        assert got_full == want_full, (iid, year, subfield_id, got_full, want_full)
        np.testing.assert_allclose(got_frac, want_frac, atol=1e-4)


# --------------------------------------------------------------------- gaps -
# RE-PINNED 2B-R2-G2: `collab_data.gaps` ("what B does not publish in that
# A's top-10 subfields cover") was DELETED per the 2B-R2-11(f) ruling -- the
# "what X does not publish in" gap tables are gone from the product BY
# DESIGN, not by regression (BUILD_PLAN_2BR2.md decisions log / §1 item 11).
# Nothing in `collab_data` is left to anchor for the old function.
#
# What replaced it on the Collaborate page's own render path is the
# 2B-R2-11(a) "top shared topics" section: `collab_data.joint_profile`, off
# the REGENERATED `collab_pair_topics.parquet` (2B-R2-12: floor 5 co-pubs,
# top-100 topics by `vol_total`, joint-corpus volume -- P6's new table, not
# an old floor-3/top-20 shape). This section tops up the SAME family slot
# with anchors on that new table: a row-count pin per pair, plus named
# topic-level value pins, each checked against `collab_data.joint_profile`
# (the app path) and independently recomputed with a fresh
# `pd.read_parquet` of the shipped file directly (not `collab_data`'s own
# ctx-cached loader) -- the same two-tier idiom as the impact/coverage
# anchors above.
#
#   old anchor (2B)                        new anchor (2B-R2)                      why
#   GAPS_ROW_COUNT_ANCHORS[(GDANSK,ISCTE)]  PAIR_TOPICS_ROW_COUNT_ANCHORS on        gaps() deleted
#     = 105 gap rows (topics_all/            collab_pair_topics.parquet: 11         (2B-R2-11f);
#     topics_dim hand-join)                  joint topics for GDANSK x ISCTE        P6's regen
#   GAPS_TOPIC_ANCHORS: 3 IFPEN x           PAIR_TOPICS_VALUE_ANCHORS: 3            replaced the
#     SORBONNE + 3 GDANSK x ISCTE            IFPEN x SORBONNE (of 55 shown) +       family's table
#     `share_b` values off the OLD           3 GDANSK x ISCTE (of 11 shown)         entirely
#     gap join                               vol/impact rows off the NEW table

PAIR_TOPICS_ROW_COUNT_ANCHORS = {
    (IFPEN, SORBONNE): 55,   # co-published joint topics shown, floor 5 / top-100 cap (2B-R2-12)
    (GDANSK, ISCTE): 11,
}
PAIR_TOPICS_VALUE_ANCHORS = [
    # (a, b, topic_id, vol_w1, vol_w2, vol_2025, vol_total, n_covered, n_top10, sdg_tagged_n)
    (IFPEN, SORBONNE, "T10399", 4, 5, 0, 9, 8, 0, 1),
    (IFPEN, SORBONNE, "T10965", 4, 2, 1, 7, 6, 0, 0),
    (IFPEN, SORBONNE, "T11351", 3, 2, 1, 6, 5, 0, 1),
    (GDANSK, ISCTE, "T10314", 1, 1, 0, 2, 2, 1, 2),
    (GDANSK, ISCTE, "T11040", 1, 1, 0, 2, 2, 1, 1),
    (GDANSK, ISCTE, "T10006", 0, 1, 0, 1, 1, 1, 1),
]
PAIR_TOPICS_VALUE_COLS = ["vol_w1", "vol_w2", "vol_2025", "vol_total", "n_covered", "n_top10", "sdg_tagged_n"]


@pytest.mark.parametrize("pair,want_rows", list(PAIR_TOPICS_ROW_COUNT_ANCHORS.items()))
def test_pair_topics_row_count_anchor(ctx, subs_bestfit, pair, want_rows):
    a, b = pair
    frame = CL.joint_profile(ctx, subs_bestfit, a, b)
    assert frame is not None, (a, b)
    assert frame["meta"]["n_topics_shown"] == want_rows, (a, b, frame["meta"]["n_topics_shown"])
    assert len(frame["topics"]) == want_rows, (a, b, len(frame["topics"]))


@pytest.mark.parametrize("a,b,topic_id,vol_w1,vol_w2,vol_2025,vol_total,n_covered,n_top10,sdg_tagged_n",
                         PAIR_TOPICS_VALUE_ANCHORS)
def test_pair_topics_topic_level_anchor(ctx, subs_bestfit, a, b, topic_id, vol_w1, vol_w2, vol_2025,
                                        vol_total, n_covered, n_top10, sdg_tagged_n):
    frame = CL.joint_profile(ctx, subs_bestfit, a, b)
    row = frame["topics"].set_index("topic_id").loc[topic_id]
    want = dict(vol_w1=vol_w1, vol_w2=vol_w2, vol_2025=vol_2025, vol_total=vol_total,
               n_covered=n_covered, n_top10=n_top10, sdg_tagged_n=sdg_tagged_n)
    for col, val in want.items():
        assert int(row[col]) == val, (a, b, topic_id, col, int(row[col]), val)


def test_pair_topics_anchors_recomputed_independently_from_the_parquet_directly():
    """Re-reads `collab_pair_topics.parquet` fresh with plain pandas (not
    `collab_data`'s ctx-cached loader, not through `joint_profile`'s tree
    joins) and re-derives both the row counts and the six named topic rows
    -- the independent recomputation the pins above were taken from."""
    import pandas as pd

    raw = pd.read_parquet(DATA_DIR / "collab_pair_topics.parquet")

    def pair_rows(a, b):
        lo, hi = (a, b) if a < b else (b, a)
        return raw[(raw["a"] == lo) & (raw["b"] == hi)]

    for (a, b), want_rows in PAIR_TOPICS_ROW_COUNT_ANCHORS.items():
        got = pair_rows(a, b)
        assert len(got) == want_rows, (a, b, len(got), want_rows)

    for a, b, topic_id, *want_vals in PAIR_TOPICS_VALUE_ANCHORS:
        row = pair_rows(a, b).set_index("topic_id").loc[str(topic_id)]
        for col, want in zip(PAIR_TOPICS_VALUE_COLS, want_vals):
            assert int(row[col]) == want, (a, b, topic_id, col, int(row[col]), want)


# ------------------------------------------------------------------ summary --

def test_every_padded_family_now_clears_ten_anchors():
    """Documents the count this file itself contributes per family (the
    per-family total, combined with tests/test_compare_data.py and
    tests/test_collab_data.py's own K pins, is reported in
    V3/progress/2B_G.md's anchors table)."""
    counts = {
        "impact": len(IMPACT_ANCHORS) * 3,          # pp, ci_low, ci_high each
        "coverage": sum(len(v) for v in COVERAGE_ANCHORS.values()),
        "trends": len(TRENDS_ANCHORS) * 2,           # vol_full, vol_frac each
        # "gaps" (2B) retired 2B-R2-11(f) -- the family slot is now filled by
        # PAIR_TOPICS_* (2B-R2-12's shipped collab_pair_topics.parquet).
        "pair_topics": len(PAIR_TOPICS_ROW_COUNT_ANCHORS) + len(PAIR_TOPICS_VALUE_ANCHORS) * len(PAIR_TOPICS_VALUE_COLS),
        "erc": len(ERC_ANCHORS) * 4,                 # share, mass, si, status each
        "sdg": len(SDG_ANCHORS) * 4,                 # share, mass, esi, status each
        "frontier_mix": sum(len(v) for v in FRONTIER_MIX_ANCHORS.values()),
    }
    for family, n in counts.items():
        assert n >= 7, (family, n)   # this file's OWN contribution; combined
                                     # with K's pins every family clears 10
                                     # (see the module docstring's table)

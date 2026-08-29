"""
Stream R-B -- lib/profile_data.py acceptance tests (BUILD_PLAN_2A.md S9.3/S9.4).
Run: python -m pytest tests/test_profile_data.py -q
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from lib import profile_data as P
from lib.engine import build_substrates, load_context

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
SEEDS = ["I40413290", "I265217849", "I39804081"]  # Gdansk, IFPEN, Sorbonne
YEARLY_SEEDS = ["I40413290", "I265217849", "I39804081", "I277688954", "I68947357"]


@pytest.fixture(scope="module")
def ctx():
    return load_context(DATA_DIR)


@pytest.fixture(scope="module")
def subs_bestfit(ctx):
    return build_substrates(ctx)  # default: bestfit / frac


@pytest.fixture(scope="module")
def subs_original(ctx):
    return build_substrates(ctx, tree="original", basis="frac")


def _parse_packed(s: str) -> dict:
    return {int(k): float(v) for k, v in (tok.split(":") for tok in s.split("|"))}


# ------------------------------------------------------------ fields/subs ---

@pytest.mark.parametrize("seed_id", SEEDS)
def test_fields_table_columns_and_share_sum(ctx, subs_bestfit, seed_id):
    df = P.fields_table(ctx, subs_bestfit, seed_id)
    assert list(df.columns) == P.FIELDS_COLS
    assert abs(df["share"].astype("float64").sum() - 1.0) <= 1e-6
    assert len(df) > 0


@pytest.mark.parametrize("seed_id", SEEDS)
def test_subfields_table_columns_share_sum_and_si_floor(ctx, subs_bestfit, seed_id):
    df = P.subfields_table(ctx, subs_bestfit, seed_id)
    assert list(df.columns) == P.SUBFIELDS_COLS
    assert abs(df["share"].astype("float64").sum() - 1.0) <= 1e-6
    below_floor = df["vol_frac"].astype("float64") < 30.0
    assert below_floor.any(), f"{seed_id}: no subfield below the G6 floor to test against"
    assert df.loc[below_floor, "si"].isna().all(), f"{seed_id}: a below-floor subfield has a defined si"
    assert df.loc[~below_floor, "si"].notna().all(), f"{seed_id}: an at/above-floor subfield has NaN si"


def test_fields_table_follows_the_tree(ctx, subs_bestfit, subs_original):
    """bug #5 (R1 triage): fields_table under `original` differs from
    `bestfit` for at least one of 3 seeds."""
    any_diff = False
    for seed_id in SEEDS:
        bf = P.fields_table(ctx, subs_bestfit, seed_id).set_index("field_id")["share"]
        orig = P.fields_table(ctx, subs_original, seed_id).set_index("field_id")["share"]
        both = bf.index.union(orig.index)
        bf, orig = bf.reindex(both, fill_value=0.0), orig.reindex(both, fill_value=0.0)
        if (np.abs(bf.to_numpy(dtype="float64") - orig.to_numpy(dtype="float64")) > 1e-6).any():
            any_diff = True
    assert any_diff, "fields_table is identical under bestfit and original for all 3 seeds"


# ------------------------------------------------------------------ topics --

@pytest.mark.parametrize("seed_id", SEEDS)
def test_topics_table_columns(ctx, subs_bestfit, seed_id):
    df = P.topics_table(ctx, subs_bestfit, seed_id)
    assert list(df.columns) == P.TOPICS_COLS
    assert len(df) > 0
    assert df["topic_name"].notna().all()
    assert df["subfield_id"].notna().all()  # every topic resolves through the fixed map


# ------------------------------------------------------------ yearly trend --

@pytest.mark.parametrize("seed_id", YEARLY_SEEDS)
def test_yearly_by_domain_matches_index_by_year(ctx, subs_bestfit, seed_id):
    """Sigma over domains per year vs index.vol_full_by_year_this_run.
    MEASURED (progress/R1_B.md): `yearly_by_domain` reproduces topics_all's
    own per-topic vol_full/vol_frac columns EXACTLY (verified by a direct
    Sigma over topics_all with no domain join) but topics_all itself is
    systematically a FEW WORKS SHORT of the index's by-year bookkeeping
    total per (seed, year) -- up to 32 works / 0.23% relative on the worst
    seed measured (Sorbonne, 2020). This is a real, small, pre-existing
    artefact-level gap (topics_all's topic grain vs the run's raw by-year
    count), not a join bug here -- reported with a documented tolerance,
    never silently forced to equality (BUILD_PLAN_2A.md L10 spirit)."""
    # Manager edit (R1, 2026-08-29): the gap above is now carried explicitly as an
    # "Unclassified" domain row per year (P.UNCLASSIFIED_DOMAIN_ID), so the domain
    # view sums to the SAME per-year total as the document-type view (both = the
    # index's by-year bookkeeping) -- the swap between the two never changes a
    # total. Exact on full counts; float32-tolerant on fractional.
    row = ctx["index_by_id"].loc[seed_id]
    want_full = _parse_packed(row["vol_full_by_year_this_run"])
    want_frac = _parse_packed(row["vol_frac_by_year_this_run"])
    yb = P.yearly_by_domain(ctx, seed_id, subs_bestfit["tree"])
    got_full = yb.groupby("year")["vol_full"].sum()
    got_frac = yb.groupby("year")["vol_frac"].sum()
    uncl = yb[yb["domain_id"] == P.UNCLASSIFIED_DOMAIN_ID]
    assert len(uncl) == yb["year"].nunique(), f"{seed_id}: one Unclassified row per year expected"
    assert (uncl["vol_full"] >= 0).all() and (uncl["vol_frac"] >= 0).all(), f"{seed_id}: negative residual"
    for year, want in want_full.items():
        got = float(got_full.get(year, 0.0))
        print(f"[yearly] {seed_id}/{year}: got={got} want={want} unclassified={float(uncl.loc[uncl['year'] == year, 'vol_full'].sum())}")
        assert int(round(got)) == int(round(want)), f"{seed_id}/{year}: full total {got} != index {want}"
        gf, wf = float(got_frac.get(year, 0.0)), float(want_frac.get(year, 0.0))
        assert abs(gf - wf) <= max(1e-6 * wf, 1e-3), f"{seed_id}/{year}: frac total {gf} != index {wf}"


def test_yearly_by_domain_columns_and_empty_shape(ctx, subs_bestfit):
    df = P.yearly_by_domain(ctx, "I40413290", subs_bestfit["tree"])
    assert list(df.columns) == P.YEARLY_COLS
    assert len(df) > 0


# --------------------------------------------------------------- SDG / ERC --

@pytest.mark.parametrize("seed_id", SEEDS)
def test_sdg_table_dense_16_rows(ctx, seed_id):
    df = P.sdg_table(ctx, seed_id)
    assert list(df.columns) == P.SDG_COLS
    assert len(df) == 16
    assert set(df["sdg_number"]) == set(range(1, 17))
    assert ((df["share"].isna()) | ((df["share"] >= 0) & (df["share"] <= 1))).all()


@pytest.mark.parametrize("seed_id", SEEDS)
def test_erc_table_columns_and_labels(ctx, seed_id):
    df = P.erc_table(ctx, seed_id)
    assert list(df.columns) == P.ERC_COLS
    if len(df):
        assert df["panel_code"].notna().all()
        assert set(df["erc_domain"].unique()) <= {"LS", "PE", "SH"}


# ---------------------------------------------------------------- wordcloud -

@pytest.mark.parametrize("seed_id", SEEDS)
def test_wordcloud_weights_shape(ctx, subs_bestfit, seed_id):
    weights, domains = P.wordcloud_weights(ctx, subs_bestfit, seed_id)
    assert set(weights) == set(domains)
    assert weights, f"{seed_id}: empty wordcloud"
    assert all(v > 0 for v in weights.values())

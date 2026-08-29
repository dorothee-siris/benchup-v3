"""
app/lib/compare_data.py -- Compare-view data frames over N (2-6) institutions
(BenchUp v3 Sprint 2 Phase 2B, Stream K; BUILD_PLAN_2B.md S4 interface
contracts, wind-tunnelled amendments A1/A2/A3/A9 in S0).

Pure functions, no Streamlit import: every function takes the engine's `ctx`
(+ often `subs`, one scenario's substrates from `lib.engine.substrates.
build_substrates`) and a list of institution ids, and returns a plain pandas
DataFrame. Every `*_long` frame carries `institution_id` FIRST and is sorted
by (`institution_id`, its own key) -- BUILD_PLAN_2B.md S4 E16 -- so
`lib/charts_compare.py` (Stream V) and `lib/views_compare.py` (Stream C)
build on these columns by name.

Nothing here recomputes a formula `lib/profile_data.py` or the engine already
owns: the `*_long` builders are thin per-institution loops over
`profile_data.*_table` (S2B-2 "SI always mass-paired" reuses the SAME
`si_status`/unfloored-si machinery the Find profile already ships), and
`frontier_mix`/`impact_subfields`/`coverage` read the shipped `index.parquet`
/ `impact_cells.parquet` columns directly (S8 "no new artefact table in 2B").
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import profile_data as P
from .engine.substrates import load_impact_cells

# Fixed 4-quadrant vocabulary parsed out of index.frontier_quadrant_mix
# (Wind Tunnel 2B #3: one institution -- I4210143641, ORFEO-CINQA Research
# Network -- ships only 3 of the 4 entries; a missing quadrant is 0.0 by
# construction, never a dropped row).
QUADRANTS = ["accelerating_expansion", "accelerating_contraction",
             "decelerating_expansion", "decelerating_contraction"]
NOT_SCORED = "not_frontier_scored"  # A2: frontier_excluded_share + frontier_unscored_share; ONE vocabulary shared with charts_compare.NOT_SCORED (manager fix 2026-08-29, C needs_change #1)

FIELDS_LONG_COLS = ["institution_id"] + P.FIELDS_COLS
SUBFIELDS_LONG_COLS = ["institution_id"] + P.SUBFIELDS_COLS
ERC_LONG_COLS = ["institution_id"] + P.ERC_COLS
SDG_LONG_COLS = ["institution_id"] + P.SDG_COLS
FRONTIER_MIX_COLS = ["institution_id", "quadrant", "share", "top25_share"]
FRONTIER_POINTS_COLS = ["institution_id", "topic_id", "topic_name", "subfield_name",
                        "expansion_latest", "acceleration_latest", "vol_full", "vol_frac",
                        "quadrant", "top25pct_frontier", "is_excluded"]
IMPACT_INDEX_COLS = ["institution_id", "pp", "ci_low", "ci_high"]
IMPACT_SUBFIELDS_COLS = ["institution_id", "subfield_id", "subfield_name", "pp", "ci_low",
                        "ci_high", "n_works_full", "in_all_ids"]
TOP_SHARED_SUBFIELDS_COLS = ["subfield_id", "subfield_name", "field_id", "field_name",
                            "domain_id", "domain_name", "summed_share"]
IMPACT_CELL_FLOORS = (10, 30)  # data_contract.yaml impact_cells.parquet: floor in {10, 30}

# A9: the six mass_* grey states + classified-eligible, sum to total_frac EXACTLY (WT-2B #7).
COVERAGE_COLUMN_BY_STATE = {
    "classified_eligible": "mass_classified_eligible",
    "title_only": "mass_title_only",
    "lang_uncertain": "mass_lang_uncertain",
    "untranslated_grey": "mass_untranslated_grey",
    "unusable": "mass_unusable",
    "retracted_excluded": "mass_retracted_excluded",
}
COVERAGE_COLS = ["institution_id", "state", "share"]


def _concat_sorted(frames: list[pd.DataFrame], sort_cols: list[str], cols: list[str]) -> pd.DataFrame:
    if not frames:
        return pd.DataFrame(columns=cols)
    out = pd.concat(frames, ignore_index=True)
    return out.sort_values(sort_cols).reset_index(drop=True).reindex(columns=cols)


# ------------------------------------------------------------ fields/subs ---

def fields_long(ctx: dict, subs: dict, ids: list[str]) -> pd.DataFrame:
    """`profile_data.fields_table` per id, stacked, `institution_id` first."""
    frames = []
    for iid in ids:
        df = P.fields_table(ctx, subs, iid)
        df.insert(0, "institution_id", iid)
        frames.append(df)
    return _concat_sorted(frames, ["institution_id", "field_id"], FIELDS_LONG_COLS)


def subfields_long(ctx: dict, subs: dict, ids: list[str]) -> pd.DataFrame:
    """`profile_data.subfields_table` per id (unfloored si + si_status,
    L34/S2B-2), stacked, `institution_id` first."""
    frames = []
    for iid in ids:
        df = P.subfields_table(ctx, subs, iid)
        df.insert(0, "institution_id", iid)
        frames.append(df)
    return _concat_sorted(frames, ["institution_id", "subfield_id"], SUBFIELDS_LONG_COLS)


def erc_long(ctx: dict, ids: list[str]) -> pd.DataFrame:
    """`profile_data.erc_table` per id, stacked, `institution_id` first."""
    frames = []
    for iid in ids:
        df = P.erc_table(ctx, iid)
        df.insert(0, "institution_id", iid)
        frames.append(df)
    return _concat_sorted(frames, ["institution_id", "panel_idx"], ERC_LONG_COLS)


def sdg_long(ctx: dict, ids: list[str]) -> pd.DataFrame:
    """`profile_data.sdg_table` per id (dense 16 rows each), stacked,
    `institution_id` first."""
    frames = []
    for iid in ids:
        df = P.sdg_table(ctx, iid)
        df.insert(0, "institution_id", iid)
        frames.append(df)
    return _concat_sorted(frames, ["institution_id", "sdg_idx"], SDG_LONG_COLS)


# --------------------------------------------------------------- frontier ---

def _parse_packed_quadrants(packed) -> dict[str, float]:
    """'quadrant:share|quadrant:share|...' -> {quadrant: share}."""
    if not isinstance(packed, str) or not packed:
        return {}
    out = {}
    for tok in packed.split("|"):
        k, v = tok.split(":")
        out[k] = float(v)
    return out


def frontier_mix(ctx: dict, ids: list[str]) -> pd.DataFrame:
    """Per institution: the 4 fixed quadrant shares (0.0 for a quadrant
    absent from the packed string, WT-2B #3) plus a fifth `not_scored`
    segment = `frontier_excluded_share + frontier_unscored_share` (A2) --
    Sigma(share) per institution == 1.0 within 1e-6 (asserted here; the
    4-quadrant-alone sum has a median of 0.967 and a min of 0.128, WT-2B
    #4)."""
    rows = []
    for iid in ids:
        row = ctx["index_by_id"].loc[iid]
        shares = _parse_packed_quadrants(row["frontier_quadrant_mix"])
        not_scored = float(row["frontier_excluded_share"]) + float(row["frontier_unscored_share"])
        top25 = float(row["frontier_top25_share"])
        for q in QUADRANTS:
            rows.append({"institution_id": iid, "quadrant": q, "share": shares.get(q, 0.0),
                        "top25_share": top25})
        rows.append({"institution_id": iid, "quadrant": NOT_SCORED, "share": not_scored,
                    "top25_share": top25})
    out = pd.DataFrame(rows, columns=FRONTIER_MIX_COLS)
    totals = out.groupby("institution_id")["share"].sum().astype("float64")
    bad = totals[(totals - 1.0).abs() > 1e-6]
    assert bad.empty, f"frontier_mix does not sum to 1 per institution: {bad.to_dict()}"
    return out


def frontier_points(ctx: dict, subs: dict, ids: list[str], mode: str) -> pd.DataFrame:
    """Scored-topics-only rows for the frontier scatter (2B-3): `mode="top"`
    = each institution's `rank_volume <= 200` (top-200-by-volume-on-the-
    current-basis, L33); `mode="emerging"` = `top25pct_frontier == True`
    (global top-quartile `frontier_score_latest`). Both modes pre-filter to
    scored topics (`quadrant` not null) -- `top25pct_frontier` is NULL, never
    False, for an unscored topic (810 of 4,516), so filtering on `quadrant`
    first keeps the emerging-mode boolean test unambiguous."""
    assert mode in ("top", "emerging"), f"unknown frontier_points mode: {mode!r}"
    frames = []
    for iid in ids:
        df = P.topics_table(ctx, subs, iid)
        df = df[df["quadrant"].notna()]
        if mode == "top":
            df = df[df["rank_volume"] <= 200]
        else:
            df = df[df["top25pct_frontier"] == True]  # noqa: E712 -- scored-only, so no NA here
        df = df.copy()
        df.insert(0, "institution_id", iid)
        frames.append(df)
    return _concat_sorted(frames, ["institution_id", "topic_id"], FRONTIER_POINTS_COLS)


# ------------------------------------------------------------------ impact --

def impact_index(ctx: dict, ids: list[str]) -> pd.DataFrame:
    """Index-level PP(top10%) + bootstrap CI per institution (2B-4)."""
    rows = []
    for iid in ids:
        row = ctx["index_by_id"].loc[iid]
        rows.append({
            "institution_id": iid,
            "pp": None if pd.isna(row["pp_top10_frac"]) else float(row["pp_top10_frac"]),
            "ci_low": None if pd.isna(row["pp_ci_low"]) else float(row["pp_ci_low"]),
            "ci_high": None if pd.isna(row["pp_ci_high"]) else float(row["pp_ci_high"]),
        })
    return pd.DataFrame(rows, columns=IMPACT_INDEX_COLS)


def impact_subfields(ctx: dict, ids: list[str], tree: str, floor: int = 30) -> pd.DataFrame:
    """The UNION of subfields ANY compared institution clears at `floor`
    (A1: only 3,342/7,557 institutions have any floor-30 cell at all, median
    2 -- an INTERSECTION-based panel is empty on realistic 4-institution
    sets, e.g. IFPEN + 3 L1 peers). One row per (institution, subfield) in
    the union, `pp`/`ci_low`/`ci_high`/`n_works_full` = NaN (never 0) where
    that institution has no cell there; `in_all_ids` flags the subfields
    every compared institution DOES clear."""
    assert floor in IMPACT_CELL_FLOORS, f"impact_cells only ships floors {IMPACT_CELL_FLOORS}, got {floor}"
    cells = load_impact_cells(ctx)
    sub = cells[(cells["tree"].astype(str) == tree) & (cells["floor"] == floor)
                & (cells["institution_id"].isin(ids))]
    name_map = P._subfield_field_domain_map(ctx)[["subfield_id", "subfield_name"]]

    union_subfield_ids = sorted(int(s) for s in sub["subfield_id"].unique())
    n_ids = len(ids)
    rows = []
    for sid in union_subfield_ids:
        cell_rows = sub[sub["subfield_id"] == sid].set_index("institution_id")
        in_all = len(cell_rows) == n_ids
        for iid in ids:
            if iid in cell_rows.index:
                r = cell_rows.loc[iid]
                rows.append({"institution_id": iid, "subfield_id": sid,
                            "pp": float(r["pp_top10_frac"]), "ci_low": float(r["pp_ci_low"]),
                            "ci_high": float(r["pp_ci_high"]), "n_works_full": int(r["n_works_full"]),
                            "in_all_ids": in_all})
            else:
                rows.append({"institution_id": iid, "subfield_id": sid, "pp": np.nan,
                            "ci_low": np.nan, "ci_high": np.nan, "n_works_full": np.nan,
                            "in_all_ids": in_all})
    out = pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["institution_id", "subfield_id", "pp", "ci_low", "ci_high", "n_works_full", "in_all_ids"])
    out = out.merge(name_map, on="subfield_id", how="left")
    return out.sort_values(["institution_id", "subfield_id"]).reset_index(drop=True).reindex(
        columns=IMPACT_SUBFIELDS_COLS)


# ------------------------------------------------------------------ trends --

def trends_subfields(ctx: dict, iid: str, tree: str) -> pd.DataFrame:
    """`year, subfield_id, subfield_name, vol_full, vol_frac` for ONE
    institution -- a thin wrapper over `profile_data.yearly_by_subfield`
    (the subfield-grain generalisation of `yearly_by_domain`, same duckdb
    predicate-pushdown query, same "Unclassified" residual convention so the
    per-year total matches the domain-grain view exactly)."""
    return P.yearly_by_subfield(ctx, iid, tree)


# ------------------------------------------------------- shared subfields ---

def top_shared_subfields(ctx: dict, subs: dict, ids: list[str], n: int) -> pd.DataFrame:
    """The `n` subfields with the largest SUMMED share across the compared
    set (A3: the INTERSECTION of per-institution top-6 lists collapses to 1
    subfield for a realistic 6-institution set -- summed share is the
    variant that survives contact with real data)."""
    l1 = subs["l1"]
    cats = np.asarray(l1["cats"])
    idxs = [ctx["id_pos"][iid] for iid in ids]
    summed = l1["share"][idxs, :].sum(axis=0).astype("float64")
    order = np.argsort(-summed, kind="stable")[:n]
    rows = [{"subfield_id": int(cats[j]), "summed_share": float(summed[j])} for j in order]
    out = pd.DataFrame(rows, columns=["subfield_id", "summed_share"])
    out = out.merge(P._subfield_field_domain_map(ctx), on="subfield_id", how="left")
    return out.reindex(columns=TOP_SHARED_SUBFIELDS_COLS)


# ------------------------------------------------------------------ grey ----

def coverage(ctx: dict, ids: list[str]) -> pd.DataFrame:
    """Institution-level grey-accounting strip: the SIX `mass_*` states
    (classified-eligible + the five grey states, A9) as a share of
    `total_frac` -- Sigma(share) per institution == 1.0 EXACTLY (WT-2B #7:
    the six columns sum to `total_frac` for all 7,557 institutions, max
    relative error 0.0)."""
    rows = []
    for iid in ids:
        row = ctx["index_by_id"].loc[iid]
        total = float(row["total_frac"])
        for state, col in COVERAGE_COLUMN_BY_STATE.items():
            share = (float(row[col]) / total) if total > 0 else np.nan
            rows.append({"institution_id": iid, "state": state, "share": share})
    out = pd.DataFrame(rows, columns=COVERAGE_COLS)
    totals = out.groupby("institution_id")["share"].sum().astype("float64")
    bad = totals[(totals - 1.0).abs() > 1e-6]
    assert bad.empty, f"coverage does not sum to 1 per institution: {bad.to_dict()}"
    return out

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

from pathlib import Path

import numpy as np
import pandas as pd

from . import profile_data as P
from .engine.substrates import load_impact_cells

# ---------------------------------------------------------------------------
# 2B-R (Phase 2B-R, Stream CD; BUILD_PLAN_2BR.md S1 2B-R-5/6/7/8/9, S4)
# additions below: `overview` (2B-R-7 KPI row), `metric_frame` (2B-R-5/6/8
# "Compare by" metric selector across field/subfield/erc/sdg taxa) and
# `frontier_pooled`/`shared_frontier` (2B-R-9 two frontier charts). All read
# the THREE new field/sdg-cross artefacts (`sdg_fields.parquet`,
# `sdg_year.parquet`, `impact_fields.parquet`, 2B-R-15/A7/A8) via lazy
# ctx-cached loaders (same idiom as `profile_data._topics_dim_extra` and
# `engine.substrates.load_impact_cells` -- read once, cache on the mutable
# `ctx` dict, never a Streamlit import in this module).
# ---------------------------------------------------------------------------

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


# ============================================================================
# 2B-R additions (Stream CD, BUILD_PLAN_2BR.md S4)
# ============================================================================

# ------------------------------------------------------------ new loaders ---

def _load_sdg_fields(ctx: dict) -> pd.DataFrame:
    """Lazy, ctx-cached (`sdg_fields.parquet`, 2B-R-15/A7): institution x sdg
    x field x tree, fractional SDG-tagged mass, full 2020-2025 run window;
    `field_id == -1` is the explicit 'untopiced' residual row."""
    if "sdg_fields_df" not in ctx:
        ctx["sdg_fields_df"] = pd.read_parquet(Path(ctx["data_dir"]) / "sdg_fields.parquet")
    return ctx["sdg_fields_df"]


def _load_sdg_year(ctx: dict) -> pd.DataFrame:
    """Lazy, ctx-cached (`sdg_year.parquet`, 2B-R-15/A7): institution x sdg x
    year (2020-2025), fractional SDG-tagged mass -- tree-independent."""
    if "sdg_year_df" not in ctx:
        ctx["sdg_year_df"] = pd.read_parquet(Path(ctx["data_dir"]) / "sdg_year.parquet")
    return ctx["sdg_year_df"]


def _load_impact_fields(ctx: dict) -> pd.DataFrame:
    """Lazy, ctx-cached (`impact_fields.parquet`, 2B-R-15/A8): institution x
    field (26) x tree x floor bootstrap PP(top10%) cells -- the SAME per-work
    top-10% flag as `impact_cells.parquet`, rolled up to field grain."""
    if "impact_fields_df" not in ctx:
        ctx["impact_fields_df"] = pd.read_parquet(Path(ctx["data_dir"]) / "impact_fields.parquet")
    return ctx["impact_fields_df"]


IMPACT_FIELD_FLOORS = (10, 30)  # data_contract.yaml impact_fields.parquet: floor in {10, 30}, same as IMPACT_CELL_FLOORS


# ---------------------------------------------------------------- overview --

OVERVIEW_COLS = ["institution_id", "vol_full", "vol_frac", "sdg_share", "frontier_top25_share",
                "pp", "ci_low", "ci_high", "intl_share", "company_share"]


def overview(ctx: dict, ids: list[str]) -> pd.DataFrame:
    """2B-R-7 Compare-overview KPI row per institution -- ALL nine values are
    read straight off `index.parquet` (no recomputation): `vol_full`/
    `vol_frac` = `total_full_2020_2024`/`total_frac_2020_2024` (the CORE
    analytical window, 2020-2024 -- the SAME window `intl_share`/
    `company_share` are denominated on, per contract; NOT the whole-run
    2020-2025 total `index.total_frac` carries); `sdg_share` =
    `sdg_tagged_share` (institution-level, already the exact 'of SDG-eligible
    mass, how much got >=1 SDG keyword hit' fraction the contract verifies);
    `frontier_top25_share`, `pp`/`ci_low`/`ci_high` (=`pp_top10_frac`/
    `pp_ci_low`/`pp_ci_high`), `intl_share`, `company_share` are shipped
    verbatim. A null source cell (e.g. `pp_top10_frac` for an institution
    with too few articles+reviews) becomes `None`, never 0 (n/a convention)."""
    rows = []
    for iid in ids:
        row = ctx["index_by_id"].loc[iid]

        def _val(col):
            v = row[col]
            return None if pd.isna(v) else float(v)

        rows.append({
            "institution_id": iid,
            "vol_full": _val("total_full_2020_2024"),
            "vol_frac": _val("total_frac_2020_2024"),
            "sdg_share": _val("sdg_tagged_share"),
            "frontier_top25_share": _val("frontier_top25_share"),
            "pp": _val("pp_top10_frac"),
            "ci_low": _val("pp_ci_low"),
            "ci_high": _val("pp_ci_high"),
            "intl_share": _val("intl_share"),
            "company_share": _val("company_share"),
        })
    return pd.DataFrame(rows, columns=OVERVIEW_COLS)


# ------------------------------------------------------------- metric_frame -

METRIC_FRAME_COLS = ["institution_id", "taxon_id", "taxon_label", "value", "ref_value", "denominator"]
METRICS = ("share", "vol_top10", "pp", "sdg_share", "dynamics", "si")
LEVELS = ("field", "subfield", "erc", "sdg")

# 2B-R-6: dynamics windows, named everywhere they are used (contract + UI).
# 2025 is EXCLUDED from both windows (the labelled bonus year).
DYNAMICS_W1 = (2020, 2022)  # mean annual volume, window 1 (3 years)
DYNAMICS_W2 = (2023, 2024)  # mean annual volume, window 2 (2 years)
DYNAMICS_DENOM_NOTE = (
    "% change = (mean annual volume, 2023-2024 [window 2, 2 yrs]) minus (mean annual volume, "
    "2020-2022 [window 1, 3 yrs]), divided by window 1's mean -- both windows named per 2B-R-6; "
    "2025 (bonus year) excluded from both; n/a when window 1's mean is 0 (denominator-zero guard)."
)

# 2B-R-5/8: unavailable (metric, level) combinations -- reason is surfaced on
# the returned empty frame's `.attrs["reason"]` so the CP page can hide the
# option instead of rendering an empty chart.
UNAVAILABLE_REASON = {
    ("vol_top10", "subfield"): "impact_fields.parquet is field-grain only this phase; subfield-level top-10% volume not wired (use the Find profile's impact_cells panel instead)",
    ("pp", "subfield"): "impact_fields.parquet is field-grain only this phase; subfield-level PP not wired here (use the Find profile's impact_cells panel instead)",
    ("sdg_share", "subfield"): "sdg_fields.parquet is field-grain only -- no subfield-grain SDG mass table shipped this phase",
    ("vol_top10", "erc"): "no impact (top-10%) artefact shipped for ERC panels",
    ("pp", "erc"): "no impact (top-10%) artefact shipped for ERC panels",
    ("sdg_share", "erc"): "'% SDG-tagged' is not defined for the ERC taxonomy",
    ("dynamics", "erc"): "no ERC x year artefact shipped this phase",
    ("vol_top10", "sdg"): "impact_fields does not cross with SDG; no SDG x impact artefact shipped",
    ("pp", "sdg"): "impact_fields does not cross with SDG; no SDG x impact artefact shipped",
    ("sdg_share", "sdg"): "'% SDG-tagged' is not meaningful when the taxon IS the SDG",
    ("si", "sdg"): "2B-R-8 excludes SI from the SDG metric selector (SDG's own specialisation column is `esi`, a different metric -- see profile_data.sdg_table)",
}


def metric_frame_available(metric: str, level: str) -> bool:
    """True iff `metric_frame(..., level, metric)` returns real rows for at
    least some institution -- the CP page's 'hide this option' check, callable
    without touching data (no ctx/ids needed)."""
    assert metric in METRICS, f"unknown metric {metric!r}"
    assert level in LEVELS, f"unknown level {level!r}"
    return (metric, level) not in UNAVAILABLE_REASON


def _dynamics_value(vol_by_year: dict) -> float:
    w1 = float(np.mean([vol_by_year.get(y, 0.0) for y in range(DYNAMICS_W1[0], DYNAMICS_W1[1] + 1)]))
    w2 = float(np.mean([vol_by_year.get(y, 0.0) for y in range(DYNAMICS_W2[0], DYNAMICS_W2[1] + 1)]))
    if w1 <= 0:
        return np.nan
    return (w2 - w1) / w1


def _share_frame(ctx, subs, ids, level, field_id=None) -> pd.DataFrame:
    if level == "field":
        base = fields_long(ctx, subs, ids).rename(columns={"field_id": "taxon_id", "field_name": "taxon_label"})
        denom = "own total mass across ALL fields in this scenario (Sigma_field share == 1)"
    elif level == "subfield":
        base = subfields_long(ctx, subs, ids)
        base = base[base["field_id"] == field_id].rename(
            columns={"subfield_id": "taxon_id", "subfield_name": "taxon_label"})
        denom = "own total mass across ALL subfields in this scenario (Sigma_subfield share == 1, not just this field's subfields)"
    elif level == "erc":
        base = erc_long(ctx, ids).rename(columns={"panel_idx": "taxon_id", "panel_label": "taxon_label"})
        denom = "own ERC-classified fractional mass (index.erc_classified_mass_frac); Sigma(share) <= 1, single-label-dominant"
    else:  # sdg
        base = sdg_long(ctx, ids).rename(columns={"sdg_idx": "taxon_id", "sdg_label": "taxon_label"})
        denom = "own SDG-tagged fractional mass; MULTI-LABEL (a work can carry several SDGs) -- Sigma(share) over the 16 SDGs can exceed 1"
    out = base[["institution_id", "taxon_id", "taxon_label", "share"]].rename(columns={"share": "value"})
    out["ref_value"] = None
    out["denominator"] = denom
    return out.reindex(columns=METRIC_FRAME_COLS)


def _si_frame(ctx, subs, ids, level, field_id=None) -> pd.DataFrame:
    if level == "field":
        base = fields_long(ctx, subs, ids).rename(columns={"field_id": "taxon_id", "field_name": "taxon_label"})
        denom = "population mean share among institutions with nonzero mass in this field (no floor at field grain)"
    elif level == "subfield":
        base = subfields_long(ctx, subs, ids)
        base = base[base["field_id"] == field_id].rename(
            columns={"subfield_id": "taxon_id", "subfield_name": "taxon_label"})
        denom = "population mean share among institutions with nonzero mass in this subfield (unfloored recompute, R2 L34 -- equals the ratified floored subfields.si wherever that is itself defined)"
    else:  # erc
        base = erc_long(ctx, ids).rename(columns={"panel_idx": "taxon_id", "panel_label": "taxon_label"})
        denom = "population mean share among institutions with nonzero mass in this ERC panel (no floor observed)"
    out = base[["institution_id", "taxon_id", "taxon_label", "si"]].rename(columns={"si": "value"})
    out["ref_value"] = 1.0  # 2B-R-5: SI reference line is always 1
    out["denominator"] = denom
    return out.reindex(columns=METRIC_FRAME_COLS)


def _field_dynamics_frame(ctx, subs, ids) -> pd.DataFrame:
    """Field-grain dynamics: `profile_data.yearly_by_subfield`'s per-year
    subfield volumes (already tested against the domain-grain total, R1)
    rolled up to FIELD via the fixed subfield->field map -- no new duckdb
    query, no new opinion about the per-year numbers themselves. The
    'Unclassified' residual row (subfield_id `P.UNCLASSIFIED_DOMAIN_ID`) has
    no field and folds into its own pseudo-field 0/'Unclassified', exactly
    as `yearly_by_domain`/`yearly_by_subfield` already do at their own grain."""
    vol_col = "vol_full" if subs["basis"] == "full" else "vol_frac"
    sub_field_map = P._subfield_field_domain_map(ctx)[["subfield_id", "field_id", "field_name"]]
    rows = []
    for iid in ids:
        yb = P.yearly_by_subfield(ctx, iid, subs["tree"]).merge(sub_field_map, on="subfield_id", how="left")
        yb["field_id"] = yb["field_id"].fillna(P.UNCLASSIFIED_DOMAIN_ID).astype(int)
        yb["field_name"] = yb["field_name"].fillna(P.UNCLASSIFIED_DOMAIN_NAME)
        for (fid, fname), g in yb.groupby(["field_id", "field_name"]):
            # a field bundles several subfields -- SUM their same-year volumes
            # first (multiple subfield rows can share one year), never a
            # naive dict(zip(...)) which would silently keep only the last
            # subfield's value per year.
            vol_by_year = g.groupby("year")[vol_col].sum().to_dict()
            rows.append({"institution_id": iid, "taxon_id": int(fid), "taxon_label": fname,
                        "value": _dynamics_value(vol_by_year), "ref_value": None,
                        "denominator": DYNAMICS_DENOM_NOTE})
    return pd.DataFrame(rows, columns=METRIC_FRAME_COLS)


def _subfield_dynamics_frame(ctx, subs, ids, field_id) -> pd.DataFrame:
    """Subfield-grain dynamics within ONE field (the drill mode) -- same
    per-year source as `_field_dynamics_frame`, no rollup, filtered to the
    subfields belonging to `field_id` under `subs['tree']`."""
    vol_col = "vol_full" if subs["basis"] == "full" else "vol_frac"
    sfd = P._subfield_field_domain_map(ctx)
    wanted = set(sfd.loc[sfd["field_id"] == field_id, "subfield_id"])
    rows = []
    for iid in ids:
        yb = P.yearly_by_subfield(ctx, iid, subs["tree"])
        yb = yb[yb["subfield_id"].isin(wanted)]
        for sid, g in yb.groupby("subfield_id"):
            vol_by_year = dict(zip(g["year"], g[vol_col]))
            rows.append({"institution_id": iid, "taxon_id": int(sid), "taxon_label": g["subfield_name"].iloc[0],
                        "value": _dynamics_value(vol_by_year), "ref_value": None,
                        "denominator": DYNAMICS_DENOM_NOTE})
    return pd.DataFrame(rows, columns=METRIC_FRAME_COLS)


def _sdg_dynamics_frame(ctx, ids) -> pd.DataFrame:
    """SDG-grain dynamics from `sdg_year.parquet` (institution x sdg x year,
    fractional SDG-tagged mass) -- DENSE 16 rows per institution (matching
    `profile_data.sdg_table`'s own convention: a SDG absent from `sdg_year`
    for this institution is 'n/a', not a dropped row)."""
    sdg_year_df = _load_sdg_year(ctx)
    labels = P._sdg_labels(ctx)[["sdg_idx", "sdg_label"]]
    note = DYNAMICS_DENOM_NOTE + " Volumes are sdg_year.mass (fractional, SDG-tagged, multi-label, tree-independent)."
    rows = []
    for iid in ids:
        d = sdg_year_df[sdg_year_df["institution_id"] == iid]
        for _, lab in labels.iterrows():
            sidx = int(lab["sdg_idx"])
            g = d[d["sdg_idx"] == sidx]
            vol_by_year = dict(zip(g["year"], g["mass"])) if len(g) else {}
            rows.append({"institution_id": iid, "taxon_id": sidx, "taxon_label": lab["sdg_label"],
                        "value": _dynamics_value(vol_by_year), "ref_value": None, "denominator": note})
    return pd.DataFrame(rows, columns=METRIC_FRAME_COLS)


def _field_impact_ref_means(ctx, tree, floor) -> pd.Series:
    """Population mean `pp_top10_frac` per field, over ALL institutions
    shipping that (field, tree, floor) cell in `impact_fields.parquet` --
    the 'index PP' reference line (2B-R-5), computed once per (tree, floor)
    and cached on ctx (164,477 rows total, cheap to group once)."""
    key = f"_impact_fields_mean_pp_{tree}_{floor}"
    if key not in ctx:
        f = _load_impact_fields(ctx)
        sub = f[(f["tree"].astype(str) == tree) & (f["floor"] == floor)]
        ctx[key] = sub.groupby("field_id")["pp_top10_frac"].mean()
    return ctx[key]


def _field_pp_frame(ctx, ids, tree, floor, want_vol: bool) -> pd.DataFrame:
    """Field-grain `pp` or `vol_top10` from `impact_fields.parquet`. Missing
    cell (this institution has no impact_fields row for this field/tree/
    floor) means the field is simply ABSENT from the returned frame for that
    institution -- never a 0 or NaN placeholder row (this table is sparse-
    to-candidate-cells, unlike sdg.parquet's dense convention)."""
    assert floor in IMPACT_FIELD_FLOORS, f"impact_fields.parquet only ships floors {IMPACT_FIELD_FLOORS}, got {floor}"
    f = _load_impact_fields(ctx)
    sub = f[(f["tree"].astype(str) == tree) & (f["floor"] == floor) & (f["institution_id"].isin(ids))]
    name_map = P._field_domain_map(ctx)[["field_id", "field_name"]]
    ref_means = _field_impact_ref_means(ctx, tree, floor) if not want_vol else None

    rows = []
    for iid in ids:
        r = sub[sub["institution_id"] == iid]
        for _, row in r.iterrows():
            fid = int(row["field_id"])
            fname_rows = name_map.loc[name_map["field_id"] == fid, "field_name"]
            fname = fname_rows.iloc[0] if len(fname_rows) else str(fid)
            if want_vol:
                value = float(row["pp_top10_frac"]) * float(row["n_works_full"])
                denom = (f"pp_top10_frac x n_works_full (field-grain, tree={tree}, floor={floor}; "
                        "n_works_full = full work count, articles+reviews, 2020-2024)")
                ref = None
            else:
                value = float(row["pp_top10_frac"])
                denom = f"pp_denominator_frac (fractional mass, articles+reviews, 2020-2024, field grain, tree={tree}, floor={floor})"
                ref = float(ref_means.get(fid, np.nan))
            rows.append({"institution_id": iid, "taxon_id": fid, "taxon_label": fname,
                        "value": value, "ref_value": ref, "denominator": denom})
    return pd.DataFrame(rows, columns=METRIC_FRAME_COLS)


SDG_SHARE_FIELD_DENOM_NOTE = (
    "numerator = SDG-tagged fractional mass summed across all 16 SDGs for this field (sdg_fields.mass, "
    "MULTI-LABEL -- a work tagged with >=1 SDG counts toward each, matching sdg.parquet's own convention; "
    "excludes the untopiced field_id=-1 residual), full 2020-2025 run window; denominator = the field's "
    "total fractional mass over the SAME full 2020-2025 run window (subs['fields_df'].vol_frac, tree-aware, "
    "matches index.total_frac's window) -- BOTH windows are the full run (2020-2025), NOT the 2020-2024 "
    "core window intl_share/company_share/vol_full use elsewhere in Compare (2B-R-15/A7, window named per brief)."
)


def _sdg_share_field_frame(ctx, subs, ids, tree) -> pd.DataFrame:
    sdg_fields_df = _load_sdg_fields(ctx)
    sub = sdg_fields_df[(sdg_fields_df["tree"].astype(str) == tree) & (sdg_fields_df["institution_id"].isin(ids))
                        & (sdg_fields_df["field_id"] != -1)]
    tagged = sub.groupby(["institution_id", "field_id"])["mass"].sum()
    field_mass = subs["fields_df"].set_index(["institution_id", "field_id"])["vol_frac"]
    name_map = P._field_domain_map(ctx)[["field_id", "field_name"]]

    rows = []
    for iid in ids:
        fids = sorted(int(x) for x in sub.loc[sub["institution_id"] == iid, "field_id"].unique())
        for fid in fids:
            fm = float(field_mass.get((iid, fid), 0.0))
            num = float(tagged.get((iid, fid), 0.0))
            value = (num / fm) if fm > 0 else np.nan
            fname_rows = name_map.loc[name_map["field_id"] == fid, "field_name"]
            fname = fname_rows.iloc[0] if len(fname_rows) else str(fid)
            rows.append({"institution_id": iid, "taxon_id": fid, "taxon_label": fname,
                        "value": value, "ref_value": None, "denominator": SDG_SHARE_FIELD_DENOM_NOTE})
    return pd.DataFrame(rows, columns=METRIC_FRAME_COLS)


def metric_frame(ctx: dict, subs: dict, ids: list[str], level: str, metric: str, *,
                 field_id: int | None = None, tree: str | None = None, floor: int = 30) -> pd.DataFrame:
    """2B-R-5/6/8 the ONE 'Compare by' metric selector, generalised over
    every (level, metric) combination the Compare page needs:

      level='field'                -> taxon = 26 fields, all 6 metrics available.
      level='subfield'             -> taxon = subfields of ONE `field_id` (required); share/si/dynamics only.
      level='erc'                  -> taxon = 28 ERC panels; share/si only.
      level='sdg'                  -> taxon = 16 SDGs; share/dynamics only.

    An unavailable (metric, level) pair (see `UNAVAILABLE_REASON`) returns an
    EMPTY `METRIC_FRAME_COLS` frame with `.attrs["reason"]` set -- check
    `metric_frame_available(metric, level)` first, or `df.empty` +
    `df.attrs.get("reason")` after the call; never raises for a merely-
    unsupported combination (only an unknown `level`/`metric` string raises).

    `tree` defaults to `subs['tree']` (only matters for the `pp`/`vol_top10`/
    `sdg_share` field-level metrics, which read the tree-carrying
    `impact_fields.parquet`/`sdg_fields.parquet` directly rather than
    `subs`'s own dense matrices); `floor` (10 or 30) only applies to `pp`/
    `vol_top10`."""
    assert level in LEVELS, f"unknown level {level!r}"
    assert metric in METRICS, f"unknown metric {metric!r}"
    if level == "subfield":
        assert field_id is not None, "level='subfield' needs field_id (drill within one field)"
    tree = tree or subs["tree"]

    if not metric_frame_available(metric, level):
        out = pd.DataFrame(columns=METRIC_FRAME_COLS)
        out.attrs["reason"] = UNAVAILABLE_REASON[(metric, level)]
        return out

    if metric == "share":
        return _share_frame(ctx, subs, ids, level, field_id)
    if metric == "si":
        return _si_frame(ctx, subs, ids, level, field_id)
    if metric == "dynamics":
        if level == "field":
            return _field_dynamics_frame(ctx, subs, ids)
        if level == "subfield":
            return _subfield_dynamics_frame(ctx, subs, ids, field_id)
        return _sdg_dynamics_frame(ctx, ids)  # level == "sdg" (erc has no dynamics, marked unavailable)
    if metric == "pp":
        return _field_pp_frame(ctx, ids, tree, floor, want_vol=False)  # level == "field" only (asserted available)
    if metric == "vol_top10":
        return _field_pp_frame(ctx, ids, tree, floor, want_vol=True)
    if metric == "sdg_share":
        return _sdg_share_field_frame(ctx, subs, ids, tree)
    raise AssertionError("unreachable")  # pragma: no cover


# ------------------------------------------------------------- frontier 2B-R

def _frontier_pool_frame(ctx: dict, subs: dict, ids: list[str]) -> pd.DataFrame:
    """ALL of `ids`' 2B-3 'emerging' frontier topics (`top25pct_frontier ==
    True`), pooled into ONE row per topic, sorted by `combined_vol`
    descending, no cap -- `frontier_pooled`/`shared_frontier` both build on
    this. Columns: `topic_id`, `name`, `x` (`expansion_latest`), `y`
    (`acceleration_latest`), `combined_vol`, `owner` (one of `ids` when only
    that institution holds nonzero volume on the topic, else `"shared"` when
    >=2 of `ids` do -- 2B-R-9: at N=3 ids this yields '3 exclusive + 1
    shared' = 4 categories, never more), plus one `vol_<institution_id>`
    column per id in `ids`'s own order (0.0, never NaN, for an id absent
    from that topic)."""
    cols = ["topic_id", "name", "x", "y", "combined_vol", "owner"] + [f"vol_{i}" for i in ids]
    pts = frontier_points(ctx, subs, ids, "emerging")
    if pts.empty:
        return pd.DataFrame(columns=cols)

    vol_col = "vol_full" if subs["basis"] == "full" else "vol_frac"
    per_id = pts.pivot_table(index="topic_id", columns="institution_id", values=vol_col,
                             aggfunc="sum", fill_value=0.0).reindex(columns=ids, fill_value=0.0)
    combined_vol = per_id.sum(axis=1)
    n_holders = (per_id > 0).sum(axis=1)
    owner = np.where(n_holders.to_numpy() >= 2, "shared", per_id.idxmax(axis=1).to_numpy())

    meta = pts.groupby("topic_id").agg(
        name=("topic_name", "first"), x=("expansion_latest", "first"), y=("acceleration_latest", "first"))
    out = meta.join(per_id)
    out["combined_vol"] = combined_vol
    out["owner"] = owner
    out = out.reset_index().rename(columns={i: f"vol_{i}" for i in ids})
    return out.sort_values("combined_vol", ascending=False).reset_index(drop=True).reindex(columns=cols)


def frontier_pooled(ctx: dict, subs: dict, ids: list[str], top_n: int) -> pd.DataFrame:
    """2B-R-9 chart 1 ('frontier map'): the pooled top-25% frontier topics
    across `ids`, capped to the `top_n` largest by `combined_vol` (the
    panel's slider, default N picked by the calling page)."""
    return _frontier_pool_frame(ctx, subs, ids).head(top_n).reset_index(drop=True)


def shared_frontier(ctx: dict, subs: dict, ids: list[str]) -> pd.DataFrame:
    """2B-R-9 chart 2 ('who holds the shared frontier'): the same pooled
    frame restricted to `owner == "shared"` (>=2 of `ids` hold nonzero
    volume there), sorted by `combined_vol` descending, UNCAPPED -- the
    diverging paired-bar list shows every shared topic, not a top-N slice
    (the page may still cap it for display, but this function does not)."""
    df = _frontier_pool_frame(ctx, subs, ids)
    return df[df["owner"] == "shared"].reset_index(drop=True)

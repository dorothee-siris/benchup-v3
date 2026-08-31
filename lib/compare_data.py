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

import duckdb
import numpy as np
import pandas as pd

from . import palette as PAL
from . import profile_data as P
from .app_config import CFG
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

# 2B-R2-3/4/5 (A5): the v3 contract adds FIVE columns to the v2 six -- one
# taxonomy-grouping pair (`domain_id`/`domain_order`, consumed by
# `charts_compare._metric_rows`/`_row_rules`), one universal volume gutter
# (`vol_display`, 2B-R2-3: EVERY chart's gutter shows raw volume on the
# CURRENT basis, incl. the Dynamics "2.1 -> 0.4/yr" raw-delta STRING) and its
# low-volume marker companion (`vol_full_annual_mean`, 2B-R2-4: hollow +
# dagger below `charts_compare.LOW_VOLUME_FLOOR`), plus `vol_top10` (2B-R2-3:
# retired as a selector TAB, kept AS DATA -- populated on the `pp` field frame
# only, NaN everywhere else, so the PP view's gutter/hover can still show "x
# publications in the world top decile" without a second lookup). A metric/
# level that cannot derive one of the five (see each builder's own docstring)
# ships NaN/None there, never a fabricated number -- absence, not zero.
METRIC_FRAME_COLS = ["institution_id", "taxon_id", "taxon_label", "value", "ref_value", "denominator",
                     "domain_id", "domain_order", "vol_display", "vol_full_annual_mean", "vol_top10"]
METRICS = ("share", "vol_top10", "pp", "sdg_share", "dynamics", "si", "vol")
LEVELS = ("field", "subfield", "erc", "sdg")

# --------------------------------------------------------- taxonomy order ---
# 2B-R2-5 (WT claim #19): the fixed display-domain order per level, read off
# the SAME palette module `charts_compare.fig_metric_bars` colours its row
# accents from -- one taxonomy order, one place it is spelled out.
_OA_DOMAIN_ORDER_MAP = {d: i for i, d in enumerate(PAL.OA_DOMAIN_ORDER)}     # {1:0, 2:1, 3:2, 4:3}
_ERC_DOMAIN_ORDER_MAP = {d: i for i, d in enumerate(PAL.ERC_DOMAIN_ORDER)}   # {"PE":0, "LS":1, "SH":2}
SDG_DOMAIN_ID = -1
# SDG carries no taxonomy DOMAIN (2B-R2-5 "SDG numeric"): every SDG row ships
# the SAME `domain_id` (this sentinel) so `charts_compare._row_rules` never
# draws a domain-boundary rule between two SDG rows -- `domain_order` (the
# SDG's own numeric goal number, `sdg_number`) supplies the plain numeric
# order by itself.

# ----------------------------------------------------------- volume basis ---
# 2B-R2-3's "raw volume on the CURRENT basis" / 2B-R2-4's "mean annual FULL
# volume" both anchor on config.yaml's analytical window (D1) -- the SAME
# 2020-2024 core window `fields.parquet`/`subfields.parquet`/`impact_fields.
# parquet` are already built on (window_conventions.core_window,
# docs/data_contract.yaml), so `vol_full / N_CORE_YEARS` is a mean-annual-FULL
# figure without any new query for the field/subfield/pp frames.
CORE_WINDOW = tuple(CFG["window"])            # (2020, 2024)
N_CORE_YEARS = CORE_WINDOW[1] - CORE_WINDOW[0] + 1   # 5

# 2B-R-6: dynamics windows, named everywhere they are used (contract + UI).
# 2025 is EXCLUDED from both windows (the labelled bonus year).
DYNAMICS_W1 = (2020, 2022)  # mean annual volume, window 1 (3 years)
DYNAMICS_W2 = (2023, 2024)  # mean annual volume, window 2 (2 years)
DYNAMICS_DENOM_NOTE = (
    "Percent change = (mean annual volume, 2023-2024) minus (mean annual volume, 2020-2022), "
    "divided by the 2020-2022 mean; 2025 (a partial, bonus year) is excluded from both periods; "
    "shown as n/a when the 2020-2022 mean is zero, never as a divide-by-zero result."
)

# 2B-R2-13 plain-language sweep (A4): reason is surfaced on the returned empty
# frame's `.attrs["reason"]` so the page can hide the option instead of
# rendering an empty chart -- every string here is written for an external
# reader: no plan codes, no artefact filenames, no mention of a pipeline.
UNAVAILABLE_REASON = {
    ("vol_top10", "subfield"): "Publications in the world top decile are only shown at field level here -- see the Find profile for subfield-level detail.",
    ("pp", "subfield"): "Publications in the world top decile are only shown at field level here -- see the Find profile for subfield-level detail.",
    ("sdg_share", "subfield"): "SDG-tagged share is only shown at field level.",
    ("vol_top10", "erc"): "Publications in the world top decile are not available for ERC research panels.",
    ("pp", "erc"): "Publications in the world top decile are not available for ERC research panels.",
    ("sdg_share", "erc"): "SDG-tagged share is not defined for ERC research panels.",
    ("dynamics", "erc"): "Change over time needs year-by-year data, which is not available for ERC research panels.",
    ("vol_top10", "sdg"): "Publications in the world top decile are not available crossed with the SDGs.",
    ("pp", "sdg"): "Publications in the world top decile are not available crossed with the SDGs.",
    ("sdg_share", "sdg"): "SDG-tagged share is not meaningful when the row is already a Sustainable Development Goal.",
    ("si", "sdg"): "Specialisation is not shown here for the SDGs -- see the SDG view's own goal-specialisation figure instead.",
    ("vol", "field"): "Volume: shown in the chart gutter instead of as a tab.",
    ("vol", "subfield"): "Volume: shown in the chart gutter instead of as a tab.",
}


def metric_frame_available(metric: str, level: str) -> bool:
    """True iff `metric_frame(..., level, metric)` returns real rows for at
    least some institution -- the CP page's 'hide this option' check, callable
    without touching data (no ctx/ids needed)."""
    assert metric in METRICS, f"unknown metric {metric!r}"
    assert level in LEVELS, f"unknown level {level!r}"
    return (metric, level) not in UNAVAILABLE_REASON


def _window_mean(vol_by_year: dict, window: tuple[int, int]) -> float:
    return float(np.mean([vol_by_year.get(y, 0.0) for y in range(window[0], window[1] + 1)]))


def _dynamics_value(vol_by_year: dict) -> float:
    w1 = _window_mean(vol_by_year, DYNAMICS_W1)
    w2 = _window_mean(vol_by_year, DYNAMICS_W2)
    if w1 <= 0:
        return np.nan
    return (w2 - w1) / w1


DYNAMICS_ARROW = "\N{RIGHTWARDS ARROW}"


def _num(v) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return float("nan")
    return f


def _dynamics_delta_str(w1: float, w2: float) -> str:
    """2B-R2-4's raw-delta gutter string, e.g. '2.1 -> 0.4/yr' -- the mean
    annual volume of window 1 THEN window 2 (arrival order, never re-sorted:
    the reader is meant to see which end is which), one decimal place. This
    is what `charts_compare._gutter_value` prints VERBATIM once it fails the
    is-a-number test (a designed fallback, not a workaround -- see that
    function's own docstring)."""
    return f"{_num(w1):.1f} {DYNAMICS_ARROW} {_num(w2):.1f}/yr"


def _annual_full_mean(w1_full: float, w2_full: float) -> float:
    """Mean annual FULL volume over the WHOLE 5-year core window (2B-R2-4's
    low-volume floor is always on the FULL basis, never fractional): a
    3-year/2-year weighted mean of the two dynamics windows, algebraically
    identical to SUM(vol_full, 2020..2024) / 5."""
    w1_full, w2_full = _num(w1_full), _num(w2_full)
    if not (np.isfinite(w1_full) and np.isfinite(w2_full)):
        return np.nan
    return (w1_full * (DYNAMICS_W1[1] - DYNAMICS_W1[0] + 1)
            + w2_full * (DYNAMICS_W2[1] - DYNAMICS_W2[0] + 1)) / N_CORE_YEARS


def _vol_full_annual_mean_from_col(vol_full) -> float:
    """Field/subfield share-family frames: `vol_full` already ships on the
    2020-2024 core window (`fields.parquet`/`subfields.parquet`, config.yaml
    window_analytical) -- no new query, just a division."""
    f = _num(vol_full)
    return f / N_CORE_YEARS if np.isfinite(f) else np.nan


def _domain_cols_for(base: pd.DataFrame, level: str) -> tuple[pd.Series, pd.Series]:
    """(domain_id, domain_order) for the SHARE/SI/vol frame family (A5/WT
    #19). `field`/`subfield` bases already carry `domain_id` (`fields_long`/
    `subfields_long` -> FIXED, tree-independent field->domain map) -- this
    was always there, `metric_frame` simply never carried it through to its
    six-column output. `erc` uses `erc_domain` (PE/LS/SH); `sdg` has no
    taxonomy domain at all (2B-R2-5 "SDG numeric") so every row ships the
    SAME `SDG_DOMAIN_ID` sentinel (no domain-boundary rule ever fires) and
    `domain_order` is the SDG's own `sdg_number`."""
    if level in ("field", "subfield"):
        dom = pd.to_numeric(base["domain_id"], errors="coerce")
        return dom, dom.map(_OA_DOMAIN_ORDER_MAP)
    if level == "erc":
        dom = base["erc_domain"].astype(str)
        return dom, dom.map(_ERC_DOMAIN_ORDER_MAP)
    # sdg
    dom = pd.Series(SDG_DOMAIN_ID, index=base.index)
    return dom, pd.to_numeric(base["sdg_number"], errors="coerce")


def _vol_display_col_for(level: str, basis: str) -> str:
    """Which already-present column IS the current-basis raw volume (2B-R2-3)
    for the share/si frame family: fields/subfields ship both `vol_full` and
    `vol_frac`; erc/sdg ship one fractional `mass` column only (no full/frac
    toggle exists at that grain)."""
    if level in ("field", "subfield"):
        return "vol_full" if basis == "full" else "vol_frac"
    return "mass"


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
    out["domain_id"], out["domain_order"] = _domain_cols_for(base, level)
    vcol = _vol_display_col_for(level, subs.get("basis"))
    out["vol_display"] = base[vcol]
    out["vol_full_annual_mean"] = (base["vol_full"].map(_vol_full_annual_mean_from_col)
                                   if level in ("field", "subfield") else np.nan)
    out["vol_top10"] = None
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
    out["domain_id"], out["domain_order"] = _domain_cols_for(base, level)
    vcol = _vol_display_col_for(level, subs.get("basis"))
    out["vol_display"] = base[vcol]
    out["vol_full_annual_mean"] = (base["vol_full"].map(_vol_full_annual_mean_from_col)
                                   if level in ("field", "subfield") else np.nan)
    out["vol_top10"] = None
    return out.reindex(columns=METRIC_FRAME_COLS)


ERC_VOL_DENOM_NOTE = (
    "The raw fractional volume of work classified into this ERC research panel -- a headline "
    "count, not a share, so there is no separate denominator: a work's ERC volume splits evenly "
    "across every panel it clears the threshold for."
)
SDG_VOL_DENOM_NOTE = (
    "The raw fractional volume of work tagged to this goal (a work tagged with more than one "
    "Sustainable Development Goal counts in full toward each), over the full 2020-2025 window -- "
    "not the 2020-2024 window used elsewhere in Compare (for example, publication volume, "
    "international share, and industry share)."
)


def _vol_frame(ctx, ids, level) -> pd.DataFrame:
    """2B-R-8 gap fix: ERC 'Volume' / SDG 'Volume tagged' -- the raw
    fractional MASS underlying each taxon's `share` (contrast `share`, which
    divides by the institution's own classified/tagged total). ERC reads
    `erc.parquet.mass` (2020-2024-ish classified-mass basis, same as
    `erc_long`'s own `mass` column, unchanged here); SDG reads
    `sdg.parquet.mass`, whose basis is the FULL 2020-2025 run window --
    NAMED explicitly in `SDG_VOL_DENOM_NOTE` since it differs from the
    2020-2024 core window most other Compare KPIs use."""
    if level == "erc":
        base = erc_long(ctx, ids).rename(columns={"panel_idx": "taxon_id", "panel_label": "taxon_label"})
        denom = ERC_VOL_DENOM_NOTE
    else:  # sdg
        base = sdg_long(ctx, ids).rename(columns={"sdg_idx": "taxon_id", "sdg_label": "taxon_label"})
        denom = SDG_VOL_DENOM_NOTE
    out = base[["institution_id", "taxon_id", "taxon_label", "mass"]].rename(columns={"mass": "value"})
    out["ref_value"] = None  # raw volume carries no reference line (2B-R-5: SI=1/index-PP only)
    out["denominator"] = denom
    out["domain_id"], out["domain_order"] = _domain_cols_for(base, level)
    out["vol_display"] = base["mass"]  # this metric IS the raw volume -- gutter mirrors the bar
    out["vol_full_annual_mean"] = np.nan  # no by-year full-count table at erc/sdg grain (not derivable)
    out["vol_top10"] = None
    return out.reindex(columns=METRIC_FRAME_COLS)


def _dynamics_population_ref(ctx, level: str, tree: str | None, basis: str | None) -> pd.Series:
    """2B-R2-4's Dynamics reference line: the population MEAN of the dynamics
    % VALUE itself (not of a volume), among institutions whose window-1 mean
    annual volume is > 0 (the same 0-safe population `_dynamics_value` uses
    per institution), one mean per taxon x tree x basis. Computed at RUNTIME
    via duckdb over `topics_all.parquet` for field/subfield (WT 2BR2 claim
    #15, MEASURED 132-157 ms cold, 133-138 ms warm on the real file across
    all three trees -- 'warm-cheap, no new artefact' per Sec 0 A6) and via a
    plain pandas pivot over the much smaller `sdg_year.parquet` for `sdg`
    (tree/basis-independent -- SDG mass carries no full/frac toggle).
    Cached on `ctx` per (level, tree, basis)."""
    key = f"_dyn_ref_{level}_{tree}_{basis}"
    if key in ctx:
        return ctx[key]

    if level == "sdg":
        df = _load_sdg_year(ctx)
        piv = df.pivot_table(index=["institution_id", "sdg_idx"], columns="year",
                             values="mass", aggfunc="sum", fill_value=0.0)
        w1 = piv.reindex(columns=range(DYNAMICS_W1[0], DYNAMICS_W1[1] + 1), fill_value=0.0).mean(axis=1)
        w2 = piv.reindex(columns=range(DYNAMICS_W2[0], DYNAMICS_W2[1] + 1), fill_value=0.0).mean(axis=1)
        dyn = ((w2 - w1) / w1).where(w1 > 0)
        ref = dyn.groupby(level="sdg_idx").mean()
        ctx[key] = ref
        return ref

    tree_col = f"{tree}_subfield_id"
    dim = ctx["topics_dim_df"][["topic_id", tree_col]].rename(columns={tree_col: "subfield_id"})
    if level == "field":
        sfd = P._subfield_field_domain_map(ctx)[["subfield_id", "field_id"]]
        dim = dim.merge(sfd, on="subfield_id", how="left")
        dim["key_col"] = dim["field_id"].fillna(P.UNCLASSIFIED_DOMAIN_ID).astype(int)
    else:  # subfield
        dim["key_col"] = dim["subfield_id"].fillna(P.UNCLASSIFIED_DOMAIN_ID).astype(int)
    map_df = dim[["topic_id", "key_col"]]

    vcol = "vol_full" if basis == "full" else "vol_frac"
    sum1 = " + ".join(f"{vcol}_{y}" for y in range(DYNAMICS_W1[0], DYNAMICS_W1[1] + 1))
    sum2 = " + ".join(f"{vcol}_{y}" for y in range(DYNAMICS_W2[0], DYNAMICS_W2[1] + 1))
    con = duckdb.connect()
    try:
        con.register("_topic_key", map_df)
        ta_posix = Path(ctx["topics_all_path"]).as_posix()
        sql = f"""
            WITH j AS (
                SELECT ta.inst_key AS inst_key, tk.key_col AS key_col,
                       SUM({sum1}) AS w1_sum, SUM({sum2}) AS w2_sum
                FROM read_parquet('{ta_posix}') ta
                JOIN _topic_key tk ON ta.topic_id = tk.topic_id
                WHERE tk.key_col != {P.UNCLASSIFIED_DOMAIN_ID}
                GROUP BY ta.inst_key, tk.key_col
            )
            SELECT key_col, AVG((w2_sum / 2.0 - w1_sum / 3.0) / (w1_sum / 3.0)) AS ref_mean
            FROM j
            WHERE w1_sum > 0
            GROUP BY key_col
        """
        out = con.sql(sql).df()
    finally:
        con.close()
    ref = out.set_index("key_col")["ref_mean"]
    ctx[key] = ref
    return ref


def _attach_dynamics_ref(ctx, out: pd.DataFrame, level: str, tree: str | None, basis: str | None) -> pd.DataFrame:
    """Populate `ref_value` on an already-built dynamics frame from
    `_dynamics_population_ref` -- a plain per-row lookup by `taxon_id`, kept
    OUT of the per-institution loops above so the (potentially uncached)
    population duckdb pass runs at most once per (level, tree, basis)."""
    if out.empty:
        return out
    ref = _dynamics_population_ref(ctx, level, tree, basis)
    out["ref_value"] = out["taxon_id"].map(ref)
    return out


def _field_dynamics_frame(ctx, subs, ids) -> pd.DataFrame:
    """Field-grain dynamics: `profile_data.yearly_by_subfield`'s per-year
    subfield volumes (already tested against the domain-grain total, R1)
    rolled up to FIELD via the fixed subfield->field map -- no new duckdb
    query for the VALUE itself, no new opinion about the per-year numbers.

    2B-R2-4: the 'Unclassified' residual row (subfield_id/field_id `P.
    UNCLASSIFIED_DOMAIN_ID`) is EXCLUDED here (dropped BEFORE grouping,
    never rendered with a dynamics value) -- unlike `yearly_by_domain`/
    `yearly_by_subfield`, which keep it as an explicit reconciling row for
    their own SUM-to-total invariant; Dynamics has no such invariant to
    protect and the user ruled the row out entirely.

    `vol_display`/`vol_full_annual_mean` are built from a SEPARATE FULL-basis
    year rollup (`vol_full`, never `vol_col`) alongside the basis-dependent
    `value`, because 2B-R2-4's raw-delta gutter and low-volume floor are
    BOTH defined on the full count regardless of which basis the chart is
    plotting."""
    vol_col = "vol_full" if subs["basis"] == "full" else "vol_frac"
    sub_field_map = P._subfield_field_domain_map(ctx)[["subfield_id", "field_id", "field_name"]]
    field_domain = P._field_domain_map(ctx).set_index("field_id")["domain_id"]
    rows = []
    for iid in ids:
        yb = P.yearly_by_subfield(ctx, iid, subs["tree"]).merge(sub_field_map, on="subfield_id", how="left")
        yb["field_id"] = yb["field_id"].fillna(P.UNCLASSIFIED_DOMAIN_ID).astype(int)
        yb["field_name"] = yb["field_name"].fillna(P.UNCLASSIFIED_DOMAIN_NAME)
        yb = yb[yb["field_id"] != P.UNCLASSIFIED_DOMAIN_ID]  # 2B-R2-4: Unclassified excluded
        for (fid, fname), g in yb.groupby(["field_id", "field_name"]):
            # a field bundles several subfields -- SUM their same-year volumes
            # first (multiple subfield rows can share one year), never a
            # naive dict(zip(...)) which would silently keep only the last
            # subfield's value per year.
            vol_by_year = g.groupby("year")[vol_col].sum().to_dict()
            full_by_year = g.groupby("year")["vol_full"].sum().to_dict()
            w1_full, w2_full = _window_mean(full_by_year, DYNAMICS_W1), _window_mean(full_by_year, DYNAMICS_W2)
            dom = field_domain.get(int(fid))
            rows.append({"institution_id": iid, "taxon_id": int(fid), "taxon_label": fname,
                        "value": _dynamics_value(vol_by_year), "ref_value": None,
                        "denominator": DYNAMICS_DENOM_NOTE,
                        "domain_id": dom, "domain_order": _OA_DOMAIN_ORDER_MAP.get(dom),
                        "vol_display": _dynamics_delta_str(w1_full, w2_full),
                        "vol_full_annual_mean": _annual_full_mean(w1_full, w2_full),
                        "vol_top10": None})
    out = pd.DataFrame(rows, columns=METRIC_FRAME_COLS)
    return _attach_dynamics_ref(ctx, out, "field", subs["tree"], subs["basis"])


def _subfield_dynamics_frame(ctx, subs, ids, field_id) -> pd.DataFrame:
    """Subfield-grain dynamics within ONE field (the drill mode) -- same
    per-year source as `_field_dynamics_frame`, no rollup, filtered to the
    subfields belonging to `field_id` under `subs['tree']`. Same 2B-R2-4
    Unclassified-exclusion and FULL-basis gutter/floor rule as the field
    grain (the Unclassified pseudo-subfield never belongs to a real
    `field_id`, so `wanted` already excludes it by construction)."""
    vol_col = "vol_full" if subs["basis"] == "full" else "vol_frac"
    sfd = P._subfield_field_domain_map(ctx)
    wanted = set(sfd.loc[sfd["field_id"] == field_id, "subfield_id"])
    sub_domain = sfd.set_index("subfield_id")["domain_id"]
    rows = []
    for iid in ids:
        yb = P.yearly_by_subfield(ctx, iid, subs["tree"])
        yb = yb[yb["subfield_id"].isin(wanted)]
        for sid, g in yb.groupby("subfield_id"):
            vol_by_year = dict(zip(g["year"], g[vol_col]))
            full_by_year = dict(zip(g["year"], g["vol_full"]))
            w1_full, w2_full = _window_mean(full_by_year, DYNAMICS_W1), _window_mean(full_by_year, DYNAMICS_W2)
            dom = sub_domain.get(int(sid))
            rows.append({"institution_id": iid, "taxon_id": int(sid), "taxon_label": g["subfield_name"].iloc[0],
                        "value": _dynamics_value(vol_by_year), "ref_value": None,
                        "denominator": DYNAMICS_DENOM_NOTE,
                        "domain_id": dom, "domain_order": _OA_DOMAIN_ORDER_MAP.get(dom),
                        "vol_display": _dynamics_delta_str(w1_full, w2_full),
                        "vol_full_annual_mean": _annual_full_mean(w1_full, w2_full),
                        "vol_top10": None})
    out = pd.DataFrame(rows, columns=METRIC_FRAME_COLS)
    return _attach_dynamics_ref(ctx, out, "subfield", subs["tree"], subs["basis"])


def _sdg_dynamics_frame(ctx, ids) -> pd.DataFrame:
    """SDG-grain dynamics from `sdg_year.parquet` (institution x sdg x year,
    fractional SDG-tagged mass) -- DENSE 16 rows per institution (matching
    `profile_data.sdg_table`'s own convention: a SDG absent from `sdg_year`
    for this institution is 'n/a', not a dropped row). No Unclassified row
    exists at this grain (nothing to exclude).

    `vol_full_annual_mean` is NaN throughout: `sdg_year.parquet` ships one
    FRACTIONAL `mass` column, never a full-count-by-year column (no such
    table exists for SDG, see docs/data_contract.yaml) -- so the 2B-R2-4
    low-volume marker is NOT derivable here and simply never fires, which is
    the documented gap (never a fabricated full count). `vol_display` falls
    back to the SAME fractional mass for its raw-delta string, disclosed in
    the denominator note."""
    sdg_year_df = _load_sdg_year(ctx)
    labels = P._sdg_labels(ctx)[["sdg_idx", "sdg_label", "sdg_number"]]
    note = (DYNAMICS_DENOM_NOTE + " Volumes are sdg_year.mass (fractional, SDG-tagged, multi-label, "
           "tree-independent) -- no full-count-by-year table exists for SDG, so the raw-delta gutter "
           "and the low-volume marker are both on this FRACTIONAL basis here, unlike every other level.")
    rows = []
    for iid in ids:
        d = sdg_year_df[sdg_year_df["institution_id"] == iid]
        for _, lab in labels.iterrows():
            sidx = int(lab["sdg_idx"])
            g = d[d["sdg_idx"] == sidx]
            vol_by_year = dict(zip(g["year"], g["mass"])) if len(g) else {}
            w1, w2 = _window_mean(vol_by_year, DYNAMICS_W1), _window_mean(vol_by_year, DYNAMICS_W2)
            rows.append({"institution_id": iid, "taxon_id": sidx, "taxon_label": lab["sdg_label"],
                        "value": _dynamics_value(vol_by_year), "ref_value": None, "denominator": note,
                        "domain_id": SDG_DOMAIN_ID, "domain_order": int(lab["sdg_number"]),
                        "vol_display": _dynamics_delta_str(w1, w2), "vol_full_annual_mean": np.nan,
                        "vol_top10": None})
    out = pd.DataFrame(rows, columns=METRIC_FRAME_COLS)
    return _attach_dynamics_ref(ctx, out, "sdg", None, None)


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
    to-candidate-cells, unlike sdg.parquet's dense convention).

    `vol_display`/`vol_full_annual_mean` read `n_works_full` (the SAME full
    work-count denominator the `want_vol` branch already multiplies by) --
    this function receives no `subs`/basis (impact_fields carries no
    fractional-volume column beyond `pp_denominator_frac`, which is
    articles+reviews-only and not comparable to the all-doctype `vol_frac`
    the share family gutters), so its gutter is FULL-basis regardless of the
    page's frac/full toggle, documented here rather than silently varying.
    `vol_top10` (2B-R2-3: retired as a selector tab, kept AS DATA) is
    populated ONLY on the `pp` branch -- the `vol_top10` metric's own frame
    already carries that number as `value` and does not need a duplicate."""
    assert floor in IMPACT_FIELD_FLOORS, f"impact_fields.parquet only ships floors {IMPACT_FIELD_FLOORS}, got {floor}"
    f = _load_impact_fields(ctx)
    sub = f[(f["tree"].astype(str) == tree) & (f["floor"] == floor) & (f["institution_id"].isin(ids))]
    name_map = P._field_domain_map(ctx)[["field_id", "field_name", "domain_id"]]
    ref_means = _field_impact_ref_means(ctx, tree, floor) if not want_vol else None

    rows = []
    for iid in ids:
        r = sub[sub["institution_id"] == iid]
        for _, row in r.iterrows():
            fid = int(row["field_id"])
            name_row = name_map.loc[name_map["field_id"] == fid]
            fname = name_row["field_name"].iloc[0] if len(name_row) else str(fid)
            dom = int(name_row["domain_id"].iloc[0]) if len(name_row) else None
            n_full = float(row["n_works_full"])
            vol_top10 = float(row["pp_top10_frac"]) * n_full
            if want_vol:
                value = vol_top10
                denom = (f"pp_top10_frac x n_works_full (field-grain, tree={tree}, floor={floor}; "
                        "n_works_full = full work count, articles+reviews, 2020-2024)")
                ref = None
                vt10 = None
            else:
                value = float(row["pp_top10_frac"])
                denom = f"pp_denominator_frac (fractional mass, articles+reviews, 2020-2024, field grain, tree={tree}, floor={floor})"
                ref = float(ref_means.get(fid, np.nan))
                vt10 = vol_top10
            rows.append({"institution_id": iid, "taxon_id": fid, "taxon_label": fname,
                        "value": value, "ref_value": ref, "denominator": denom,
                        "domain_id": dom, "domain_order": _OA_DOMAIN_ORDER_MAP.get(dom),
                        "vol_display": n_full, "vol_full_annual_mean": n_full / N_CORE_YEARS,
                        "vol_top10": vt10})
    return pd.DataFrame(rows, columns=METRIC_FRAME_COLS)


SDG_SHARE_FIELD_DENOM_NOTE = (
    "Numerator: SDG-tagged fractional volume summed across all 16 goals for this field (a work "
    "tagged with more than one goal counts in full toward each); denominator: the field's total "
    "fractional volume. Both over the full 2020-2025 window -- not the 2020-2024 window used "
    "elsewhere in Compare (for example, publication volume, international share, and industry share)."
)


def _load_fields_raw(ctx: dict) -> pd.DataFrame:
    """Lazy, ctx-cached: `fields.parquet` read fresh (institution_id, field_id,
    vol_full, vol_frac only) -- used ONLY by the SDG-share population
    reference below, which needs every institution's field mass, not just
    the compared set `subs['fields_df']` was built for."""
    if "fields_raw_df" not in ctx:
        ctx["fields_raw_df"] = pd.read_parquet(
            Path(ctx["data_dir"]) / "fields.parquet",
            columns=["institution_id", "field_id", "vol_full", "vol_frac"])
    return ctx["fields_raw_df"]


def _sdg_share_field_ref_means(ctx: dict, tree: str) -> pd.Series:
    """2B-R2-4 reference line for SDG-tagged share: the population mean of
    the SAME ratio `_sdg_share_field_frame` computes per institution (tagged
    mass / field mass), among institutions with nonzero field mass, per
    field x tree. `fields.parquet` is BESTFIT-tree-only (its own grain note)
    so this reference is computed against that one basis regardless of
    `tree` -- the same approximation WT 2BR2 claim #15 measured and cleared
    ('SDG-tagged share per field x tree (join to fields.parquet): 112/94
    ms'). Cached per tree on ctx (a plain pandas groupby, no duckdb needed at
    this row count -- 1.7M sdg_fields rows x 150K fields rows)."""
    key = f"_sdgshare_ref_{tree}"
    if key in ctx:
        return ctx[key]
    sdg_fields_df = _load_sdg_fields(ctx)
    sub = sdg_fields_df[(sdg_fields_df["tree"].astype(str) == tree) & (sdg_fields_df["field_id"] != -1)]
    tagged = sub.groupby(["institution_id", "field_id"])["mass"].sum()
    fields_raw = _load_fields_raw(ctx).set_index(["institution_id", "field_id"])["vol_frac"]
    # `fields.parquet` ships nonzero-mass (institution, field) rows only (its
    # own grain note) -- so its own index IS "nonzero field mass", and a
    # left-join from it (never the other way) is what keeps a
    # tagged-but-zero-field-mass ghost cell out of the population.
    aligned = fields_raw.to_frame("field_mass").join(tagged.rename("tagged"), how="left")
    aligned["tagged"] = aligned["tagged"].fillna(0.0)
    aligned["ratio"] = aligned["tagged"] / aligned["field_mass"]
    ref = aligned.reset_index().groupby("field_id")["ratio"].mean()
    ctx[key] = ref
    return ref


def _sdg_share_field_frame(ctx, subs, ids, tree) -> pd.DataFrame:
    sdg_fields_df = _load_sdg_fields(ctx)
    sub = sdg_fields_df[(sdg_fields_df["tree"].astype(str) == tree) & (sdg_fields_df["institution_id"].isin(ids))
                        & (sdg_fields_df["field_id"] != -1)]
    tagged = sub.groupby(["institution_id", "field_id"])["mass"].sum()
    field_mass = subs["fields_df"].set_index(["institution_id", "field_id"])["vol_frac"]
    field_mass_full = subs["fields_df"].set_index(["institution_id", "field_id"])["vol_full"]
    name_map = P._field_domain_map(ctx)[["field_id", "field_name", "domain_id"]]
    ref_means = _sdg_share_field_ref_means(ctx, tree)

    rows = []
    for iid in ids:
        fids = sorted(int(x) for x in sub.loc[sub["institution_id"] == iid, "field_id"].unique())
        for fid in fids:
            fm = float(field_mass.get((iid, fid), 0.0))
            fm_full = float(field_mass_full.get((iid, fid), 0.0))
            num = float(tagged.get((iid, fid), 0.0))
            value = (num / fm) if fm > 0 else np.nan
            name_row = name_map.loc[name_map["field_id"] == fid]
            fname = name_row["field_name"].iloc[0] if len(name_row) else str(fid)
            dom = int(name_row["domain_id"].iloc[0]) if len(name_row) else None
            rows.append({"institution_id": iid, "taxon_id": fid, "taxon_label": fname,
                        "value": value, "ref_value": float(ref_means.get(fid, np.nan)),
                        "denominator": SDG_SHARE_FIELD_DENOM_NOTE,
                        "domain_id": dom, "domain_order": _OA_DOMAIN_ORDER_MAP.get(dom),
                        "vol_display": fm, "vol_full_annual_mean": fm_full / N_CORE_YEARS,
                        "vol_top10": None})
    return pd.DataFrame(rows, columns=METRIC_FRAME_COLS)


def metric_frame(ctx: dict, subs: dict, ids: list[str], level: str, metric: str, *,
                 field_id: int | None = None, tree: str | None = None, floor: int = 30) -> pd.DataFrame:
    """2B-R-5/6/8 the ONE 'Compare by' metric selector, generalised over
    every (level, metric) combination the Compare page needs:

      level='field'                -> taxon = 26 fields, all of {share,vol_top10,pp,sdg_share,dynamics,si}.
      level='subfield'             -> taxon = subfields of ONE `field_id` (required); share/si/dynamics only.
      level='erc'                  -> taxon = 28 ERC panels; share/si/vol (2B-R-8 'Volume').
      level='sdg'                  -> taxon = 16 SDGs; share/dynamics/vol (2B-R-8 'Volume tagged').

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
    if metric == "vol":
        return _vol_frame(ctx, ids, level)  # level in {"erc", "sdg"} only (field/subfield marked unavailable)
    raise AssertionError("unreachable")  # pragma: no cover


# ------------------------------------------------------------- frontier 2B-R

FRONTIER_POOLS = ("volume", "elite")
# 2B-R2-10 pool selector. "volume" (default) = the 2B-R-9 pool, unchanged:
# every compared institution's top-quartile-frontier topics (`top25pct_
# frontier == True`), ranked by combined volume. "elite" = a STRICTER,
# GLOBAL topic set -- only topics in the top-10% by `frontier_score_latest`
# across ALL 3,706 scored topics (WT 2BR2 claim #22 rules the cut GLOBAL,
# never over the compared basket's own topics, "so the pool does not change
# when a reader edits the basket"). top-10% is a subset of top-25% by
# construction (a stricter percentile cutoff on the same score), so filtering
# `frontier_points(..., "emerging")`'s own already-top25 rows down to the
# elite id set is exact, not an approximation -- no second topics_table scan.
ELITE_FRONTIER_PERCENTILE = 0.90


def _elite_frontier_topic_ids(ctx: dict) -> frozenset:
    """2B-R2-10 pool="elite": topic ids in the GLOBAL top-10% by
    `frontier_score_latest`, cut over every topic that HAS a score (3,706 of
    4,516 -- `is_frontier_scored`), never the compared institutions' own
    footprint. Cached on ctx (one `topics_dim.parquet` read + one quantile)."""
    if "_elite_frontier_topic_ids" not in ctx:
        extra = P._topics_dim_extra(ctx)
        scores = pd.to_numeric(extra["frontier_score_latest"], errors="coerce")
        scored = scores.dropna()
        cutoff = float(scored.quantile(ELITE_FRONTIER_PERCENTILE)) if len(scored) else np.inf
        ctx["_elite_frontier_topic_ids"] = frozenset(extra.loc[scores >= cutoff, "topic_id"])
    return ctx["_elite_frontier_topic_ids"]


def _frontier_pool_frame(ctx: dict, subs: dict, ids: list[str], pool: str = "volume") -> pd.DataFrame:
    """ALL of `ids`' eligible frontier topics under `pool` (2B-R2-10),
    pooled into ONE row per topic, sorted by `combined_vol` descending, no
    cap -- `frontier_pooled`/`shared_frontier` both build on this. Columns:
    `topic_id`, `name`, `x` (`expansion_latest`), `y` (`acceleration_
    latest`), `combined_vol`, `owner` (one of `ids` when only that
    institution holds nonzero volume on the topic, else `"shared"` when >=2
    of `ids` do -- 2B-R-9: at N=3 ids this yields '3 exclusive + 1 shared' =
    4 categories, never more), `domain_id` (WT 2BR2 claim #21: the topic's
    FIXED OpenAlex domain, for 2B-R2-10's colour-by-domain toggle -- tree-
    independent, so it never moves when the tree scenario changes), plus one
    `vol_<institution_id>` column per id in `ids`'s own order (0.0, never
    NaN, for an id absent from that topic)."""
    assert pool in FRONTIER_POOLS, f"pool must be one of {FRONTIER_POOLS}, got {pool!r}"
    cols = ["topic_id", "name", "x", "y", "combined_vol", "owner", "domain_id"] + [f"vol_{i}" for i in ids]
    pts = frontier_points(ctx, subs, ids, "emerging")
    if pool == "elite":
        pts = pts[pts["topic_id"].isin(_elite_frontier_topic_ids(ctx))]
    if pts.empty:
        return pd.DataFrame(columns=cols)

    vol_col = "vol_full" if subs["basis"] == "full" else "vol_frac"
    per_id = pts.pivot_table(index="topic_id", columns="institution_id", values=vol_col,
                             aggfunc="sum", fill_value=0.0).reindex(columns=ids, fill_value=0.0)
    combined_vol = per_id.sum(axis=1)
    n_holders = (per_id > 0).sum(axis=1)
    owner = np.where(n_holders.to_numpy() >= 2, "shared", per_id.idxmax(axis=1).to_numpy())

    topic_domain = ctx["topics_dim_df"].set_index("topic_id")["domain_id"]
    meta = pts.groupby("topic_id").agg(
        name=("topic_name", "first"), x=("expansion_latest", "first"), y=("acceleration_latest", "first"))
    meta["domain_id"] = topic_domain.reindex(meta.index)
    out = meta.join(per_id)
    out["combined_vol"] = combined_vol
    out["owner"] = owner
    out = out.reset_index().rename(columns={i: f"vol_{i}" for i in ids})
    return out.sort_values("combined_vol", ascending=False).reset_index(drop=True).reindex(columns=cols)


def frontier_pooled(ctx: dict, subs: dict, ids: list[str], top_n: int, pool: str = "volume") -> pd.DataFrame:
    """2B-R-9 chart 1 ('frontier map'): the pooled eligible frontier topics
    across `ids` under `pool` (2B-R2-10: "volume" = top-25%-frontier topics
    ranked by combined volume, the 2B-R-9 default; "elite" = only topics in
    the GLOBAL top-10% by `frontier_score_latest`), capped to the `top_n`
    largest by `combined_vol` (the panel's slider, default N picked by the
    calling page)."""
    return _frontier_pool_frame(ctx, subs, ids, pool).head(top_n).reset_index(drop=True)


def shared_frontier(ctx: dict, subs: dict, ids: list[str], pool: str = "volume") -> pd.DataFrame:
    """2B-R-9 chart 2 ('who holds the shared frontier'): the same pooled
    frame restricted to `owner == "shared"` (>=2 of `ids` hold nonzero
    volume there), sorted by `combined_vol` descending, UNCAPPED -- the
    diverging paired-bar list shows every shared topic, not a top-N slice
    (the page may still cap it for display, but this function does not)."""
    df = _frontier_pool_frame(ctx, subs, ids, pool)
    return df[df["owner"] == "shared"].reset_index(drop=True)

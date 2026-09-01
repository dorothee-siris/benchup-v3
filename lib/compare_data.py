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

2C (Stream CD5, BUILD_PLAN_2C.md S3 CD5): `metric_frame` v5 adds the `fwci`
metric at all four grains, reading `fwci_taxa.parquet`/`fwci_taxa_ref.
parquet` (pipeline step 18, Stream P8) -- and adds ONE new `METRIC_FRAME_COLS`
column, `fwci_mean` (hover-only, D2), which every OTHER metric ships as
`None`. See the "2C additions" section above `metric_frame` for the `fwci`
machinery itself.
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


# 2BR3 CD4 item 7 (BUILD_PLAN_2BR3.md SS1.5 "'Trends in the 6 subfields'
# DELETED"): `trends_subfields()` and its implicit column contract
# (`profile_data.SUBFIELD_YEARLY_COLS`, unchanged there) are REMOVED --
# `views_compare._view_trends`/`_trends` (VC's own fence) is the only
# consumer (WT_2BR3.md SS5.7 deleted-code map: a clean 4-hop chain entirely
# inside VC/CD4's own fences, no cross-stream break). The corresponding
# `tests/test_compare_data.py::test_trends_subfields_*` tests are removed
# with it (this plan, CD4 item 7/8).

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
    """Lazy, ctx-cached (`sdg_year.parquet` v2, SS2.2): institution x sdg x
    year (2020-2025 on disk), `mass_frac`/`mass_full` -- tree-independent."""
    if "sdg_year_df" not in ctx:
        ctx["sdg_year_df"] = pd.read_parquet(Path(ctx["data_dir"]) / "sdg_year.parquet")
    return ctx["sdg_year_df"]


def _sdg_year_window_mass(ctx: dict, ids: list[str]) -> pd.DataFrame:
    """`sdg_year.parquet` v2, window-sliced to `CORE_WINDOW` (2020-2024,
    item 1 -- Compare's SDG 'Volume tagged' + SDG dynamics both move here off
    the whole-run `sdg.parquet.mass`), summed per (institution_id, sdg_idx),
    BOTH `mass_frac` and `mass_full` carried through so a caller picks its
    own basis column without a second read."""
    df = _load_sdg_year(ctx)
    sub = df[df["institution_id"].isin(ids) & df["year"].between(CORE_WINDOW[0], CORE_WINDOW[1])]
    return sub.groupby(["institution_id", "sdg_idx"], as_index=False)[["mass_frac", "mass_full"]].sum()


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
#
# v5 (2C, Stream CD5, D2): ONE column added, `fwci_mean` -- the FWCI metric's
# hover-only mean (median is the bar, `value`; mean rides beside it for the
# hover's "mean + covered works" line, D2 ruling). Float64 nullable, populated
# ONLY on the `fwci` metric's own frame; every other builder ships `None`
# here (mechanical -- absence, not zero, same convention as `vol_top10`
# above). `fwci` itself is BASIS-PINNED (full/binary attribution always,
# decisions log 2026-09-01): unlike PP (whose `value` is basis-invariant but
# whose gutter still toggles between two pre-existing columns), FWCI's
# `value`/`vol_display`/`denominator` never move with `subs['basis']` at all
# -- `_fwci_frame` below does not even read `subs`.
METRIC_FRAME_COLS = ["institution_id", "taxon_id", "taxon_label", "value", "fwci_mean", "ref_value",
                     "denominator", "denom_value", "domain_id", "domain_order", "vol_display",
                     "vol_full_annual_mean", "vol_top10"]
METRICS = ("share", "vol_top10", "pp", "sdg_share", "dynamics", "si", "vol", "fwci")
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

# 2BR3 CD4 (BUILD_PLAN_2BR3.md SS2.5, "metric_frame v4"): `denom_value`
# (Float64, nullable) is the NUMBER a hover prints beside `value` -- the real
# denominator that produced it, computed directly (never back-divided
# value/vol_display, which would be 0/0=NaN for every legitimately-zero
# row and violate "finite wherever value is finite"). A metric with no
# natural count-style denominator (si -- a ratio against a population MEAN,
# not a share of a knowable total; vol/vol_top10 -- themselves raw counts,
# not ratios) ships NaN here deliberately (absence, not a fabricated number).
def _grain_total_by_institution(base: pd.DataFrame, vcol: str) -> pd.Series:
    """Per-institution SUM of `vcol` across EVERY taxon row in `base` (before
    any field_id/etc. filter) -- the share family's own true denominator:
    for field/subfield this is exact by construction (Sigma_taxon share == 1,
    tested elsewhere in this suite); for erc/sdg it is the sum of the taxon
    rows actually shipped, which can be a slight underestimate of the true
    classified/tagged total when a residual exists outside any taxon row
    (documented approximation, not silently assumed exact)."""
    return base.groupby("institution_id")[vcol].sum().astype("float64")


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
    """Which already-present column IS the current-basis raw volume: fields/
    subfields ship both `vol_full` and `vol_frac`. `erc_long`/`sdg_long`
    (thin wrappers over `profile_data.erc_table`/`sdg_table`) still only
    carry the ONE fractional `mass` column each -- 2BR3 CD4 does NOT touch
    `profile_data.py`'s column contract (out of fence), so the erc/sdg
    MASS_FULL toggle (SS2.5 "ERC/SDG frames honor the basis toggle via the
    new mass_full columns") is applied by `_vol_frame`/`_sdg_dynamics_frame`
    reading the raw parquet directly, NOT through this helper -- this
    function stays 'mass' for erc/sdg (the share/si families, which this
    helper serves, are fractional-only by design regardless of basis)."""
    if level in ("field", "subfield"):
        return "vol_full" if basis == "full" else "vol_frac"
    return "mass"


def _share_denom_value(ctx, subs, ids, level, base_filtered: pd.DataFrame) -> pd.Series:
    """v4 `denom_value` for the share family (SS2.5): a per-institution SUM
    computed independently of any single row (never value-back-division, see
    `_grain_total_by_institution`'s own docstring). field/subfield share the
    SAME institution total mass across the WHOLE taxonomy at that grain
    (subfield needs the UNFILTERED base, not just the drilled field's own
    subfields -- its own denominator note says so); erc/sdg sum their own
    (sparse/dense) taxon rows."""
    vcol = _vol_display_col_for(level, subs.get("basis"))
    if level == "field":
        totals = _grain_total_by_institution(base_filtered, vcol)
    elif level == "subfield":
        totals = _grain_total_by_institution(subfields_long(ctx, subs, ids), vcol)
    elif level == "erc":
        totals = _grain_total_by_institution(erc_long(ctx, ids), vcol)
    else:  # sdg
        totals = _grain_total_by_institution(sdg_long(ctx, ids), vcol)
    return base_filtered["institution_id"].map(totals)


def _share_frame(ctx, subs, ids, level, field_id=None) -> pd.DataFrame:
    if level == "field":
        base = fields_long(ctx, subs, ids).rename(columns={"field_id": "taxon_id", "field_name": "taxon_label"})
        denom = ("own total mass across ALL fields in this scenario (Sigma_field share == 1); "
                 "whole-run window (2020-2025), unlike the top-decile and SDG panels' 2020-2024 window")
    elif level == "subfield":
        base = subfields_long(ctx, subs, ids)
        base = base[base["field_id"] == field_id].rename(
            columns={"subfield_id": "taxon_id", "subfield_name": "taxon_label"})
        denom = ("own total mass across ALL subfields in this scenario (Sigma_subfield share == 1, "
                 "not just this field's subfields); whole-run window (2020-2025), unlike the "
                 "top-decile and SDG panels' 2020-2024 window")
    elif level == "erc":
        base = erc_long(ctx, ids).rename(columns={"panel_idx": "taxon_id", "panel_label": "taxon_label"})
        denom = "own ERC-classified fractional mass (index.erc_classified_mass_frac); Sigma(share) <= 1, single-label-dominant"
    else:  # sdg
        base = sdg_long(ctx, ids).rename(columns={"sdg_idx": "taxon_id", "sdg_label": "taxon_label"})
        denom = "own SDG-tagged fractional mass; MULTI-LABEL (a work can carry several SDGs) -- Sigma(share) over the 16 SDGs can exceed 1"
    out = base[["institution_id", "taxon_id", "taxon_label", "share"]].rename(columns={"share": "value"})
    out["ref_value"] = None
    out["denominator"] = denom
    out["denom_value"] = _share_denom_value(ctx, subs, ids, level, base)
    out["domain_id"], out["domain_order"] = _domain_cols_for(base, level)
    vcol = _vol_display_col_for(level, subs.get("basis"))
    out["vol_display"] = base[vcol]
    out["vol_full_annual_mean"] = (base["vol_full"].map(_vol_full_annual_mean_from_col)
                                   if level in ("field", "subfield") else np.nan)
    out["vol_top10"] = None
    out["fwci_mean"] = None  # v5: hover-only, fwci metric only (D2)
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
    out["denom_value"] = np.nan  # SI is a ratio against a population MEAN, not a share of a knowable total -- no count-style denominator to print (v4 SS2.5: absence, not a fabricated number)
    out["domain_id"], out["domain_order"] = _domain_cols_for(base, level)
    vcol = _vol_display_col_for(level, subs.get("basis"))
    out["vol_display"] = base[vcol]
    out["vol_full_annual_mean"] = (base["vol_full"].map(_vol_full_annual_mean_from_col)
                                   if level in ("field", "subfield") else np.nan)
    out["vol_top10"] = None
    out["fwci_mean"] = None  # v5: hover-only, fwci metric only (D2)
    return out.reindex(columns=METRIC_FRAME_COLS)


ERC_VOL_DENOM_NOTE = (
    "The raw volume of work classified into this ERC research panel, on the current basis -- a "
    "headline count, not a share, so there is no separate denominator: a work's ERC volume splits "
    "evenly across every panel it clears the threshold for."
)
SDG_VOL_DENOM_NOTE = (
    "The raw volume of work tagged to this goal (a work tagged with more than one Sustainable "
    "Development Goal counts in full toward each), summed over 2020-2024 on the current basis -- "
    "the SAME core window the rest of Compare uses (sourced from sdg_year.parquet, not the "
    "whole-run sdg.parquet mass)."
)


def _erc_mass_full_by_institution_panel(ctx: dict) -> pd.Series:
    """Lazy, ctx-cached: `erc.parquet`'s `mass_full` column (v2, SS2.2)
    indexed by (institution_id, panel_idx) -- read straight off `ctx[
    'erc_df']` (load_context/the fixture builder both load erc.parquet
    unfiltered, so any v2 column rides along without profile_data.py ever
    needing to reindex it through -- CD4 stays out of that fence). Falls
    back to an all-NaN series when `mass_full` is absent (today's real
    erc.parquet, pre-P7): a graceful degrade, never a KeyError."""
    key = "_erc_mass_full_by_panel"
    if key not in ctx:
        raw = ctx["erc_df"]
        if "mass_full" in raw.columns:
            ctx[key] = raw.set_index(["institution_id", "panel_idx"])["mass_full"]
        else:
            ctx[key] = pd.Series(dtype="float64")
    return ctx[key]


def _vol_frame(ctx, subs, ids, level) -> pd.DataFrame:
    """2B-R-8 gap fix, basis-toggle-aware since 2BR3 CD4 (SS2.5 "ERC/SDG
    frames honor the basis toggle via the new mass_full columns"): ERC
    'Volume' / SDG 'Volume tagged' -- the raw MASS underlying each taxon's
    `share`. ERC reads `erc.parquet.mass`/`mass_full` (basis-toggled, v2);
    SDG now reads `sdg_year.parquet` window-sliced 2020-2024 (item 1 -- moved
    off `sdg.parquet`'s whole-run 2020-2025 mass, see `SDG_VOL_DENOM_NOTE`),
    dense 16 rows, `mass_frac`/`mass_full` basis-toggled."""
    basis = (subs or {}).get("basis", "frac")
    if level == "erc":
        base = erc_long(ctx, ids).rename(columns={"panel_idx": "taxon_id", "panel_label": "taxon_label"})
        full_by_panel = _erc_mass_full_by_institution_panel(ctx)
        if basis == "full" and not full_by_panel.empty:
            value = pd.Series(
                [float(full_by_panel.get((iid, pid), np.nan))
                 for iid, pid in zip(base["institution_id"], base["taxon_id"])],
                index=base.index)
        else:
            value = base["mass"].astype("float64")
        out = base[["institution_id", "taxon_id", "taxon_label"]].copy()
        out["value"] = value
        out["denominator"] = ERC_VOL_DENOM_NOTE
        out["domain_id"], out["domain_order"] = _domain_cols_for(base, level)
    else:  # sdg -- sdg_year.parquet v2, window-sliced 2020-2024, basis-toggled
        vcol = "mass_full" if basis == "full" else "mass_frac"
        win = _sdg_year_window_mass(ctx, ids)
        labels = P._sdg_labels(ctx)[["sdg_idx", "sdg_label", "sdg_number"]]
        rows = []
        for iid in ids:
            d = win[win["institution_id"] == iid].set_index("sdg_idx")
            for _, lab in labels.iterrows():
                sidx = int(lab["sdg_idx"])
                v = float(d.loc[sidx, vcol]) if sidx in d.index else 0.0
                rows.append({"institution_id": iid, "taxon_id": sidx, "taxon_label": lab["sdg_label"],
                            "value": v, "denominator": SDG_VOL_DENOM_NOTE,
                            "domain_id": SDG_DOMAIN_ID, "domain_order": int(lab["sdg_number"])})
        out = pd.DataFrame(rows)
    out["ref_value"] = None  # raw volume carries no reference line (2B-R-5: SI=1/index-PP only)
    out["denom_value"] = np.nan  # a raw volume IS the count -- not a ratio, so no separate denominator (v4 SS2.5)
    out["vol_display"] = out["value"]  # this metric IS the raw volume -- gutter mirrors the bar
    out["vol_full_annual_mean"] = np.nan  # no by-year full-count table at erc/sdg TAXON grain (not derivable)
    out["vol_top10"] = None
    out["fwci_mean"] = None  # v5: hover-only, fwci metric only (D2)
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
        vcol = "mass_full" if basis == "full" else "mass_frac"
        piv = df.pivot_table(index=["institution_id", "sdg_idx"], columns="year",
                             values=vcol, aggfunc="sum", fill_value=0.0)
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

    `vol_display` (the raw-delta gutter string) is now built from the SAME
    `vol_col` as `value` (2BR3 item 1 fix -- this WAS the "-16.4% beside
    3.7 -> 4.5/yr" bug, WT_2BR3.md task 6 #2b: value and gutter silently
    disagreeing in basis). `vol_full_annual_mean` (the low-volume FLOOR
    marker) stays on the SEPARATE FULL-basis rollup regardless of toggle --
    unchanged, the floor is deliberately never basis-dependent."""
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
            vol_by_year = g.groupby("year")[vol_col].sum().to_dict()      # CURRENT basis -- value AND gutter
            full_by_year = g.groupby("year")["vol_full"].sum().to_dict()  # FULL basis -- floor marker ONLY
            w1, w2 = _window_mean(vol_by_year, DYNAMICS_W1), _window_mean(vol_by_year, DYNAMICS_W2)
            w1_full, w2_full = _window_mean(full_by_year, DYNAMICS_W1), _window_mean(full_by_year, DYNAMICS_W2)
            dom = field_domain.get(int(fid))
            rows.append({"institution_id": iid, "taxon_id": int(fid), "taxon_label": fname,
                        "value": _dynamics_value(vol_by_year), "fwci_mean": None, "ref_value": None,
                        "denominator": DYNAMICS_DENOM_NOTE, "denom_value": w1 if w1 > 0 else np.nan,
                        "domain_id": dom, "domain_order": _OA_DOMAIN_ORDER_MAP.get(dom),
                        "vol_display": _dynamics_delta_str(w1, w2),
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
            vol_by_year = dict(zip(g["year"], g[vol_col]))      # CURRENT basis -- value AND gutter (item-1 fix)
            full_by_year = dict(zip(g["year"], g["vol_full"]))  # FULL basis -- floor marker ONLY
            w1, w2 = _window_mean(vol_by_year, DYNAMICS_W1), _window_mean(vol_by_year, DYNAMICS_W2)
            w1_full, w2_full = _window_mean(full_by_year, DYNAMICS_W1), _window_mean(full_by_year, DYNAMICS_W2)
            dom = sub_domain.get(int(sid))
            rows.append({"institution_id": iid, "taxon_id": int(sid), "taxon_label": g["subfield_name"].iloc[0],
                        "value": _dynamics_value(vol_by_year), "fwci_mean": None, "ref_value": None,
                        "denominator": DYNAMICS_DENOM_NOTE, "denom_value": w1 if w1 > 0 else np.nan,
                        "domain_id": dom, "domain_order": _OA_DOMAIN_ORDER_MAP.get(dom),
                        "vol_display": _dynamics_delta_str(w1, w2),
                        "vol_full_annual_mean": _annual_full_mean(w1_full, w2_full),
                        "vol_top10": None})
    out = pd.DataFrame(rows, columns=METRIC_FRAME_COLS)
    return _attach_dynamics_ref(ctx, out, "subfield", subs["tree"], subs["basis"])


def _sdg_dynamics_frame(ctx, subs, ids) -> pd.DataFrame:
    """SDG-grain dynamics, basis-toggle-aware since 2BR3 CD4 (item 1): reads
    `sdg_year.parquet` v2's `mass_frac`/`mass_full` on `subs['basis']`,
    window-sliced 2020-2024 (2025 excluded, same convention as every other
    level's dynamics windows -- `sdg_year.parquet` ships 2020-2025 on disk,
    the slice is applied here, not upstream). DENSE 16 rows per institution
    (matching `profile_data.sdg_table`'s own convention). No Unclassified row
    exists at this grain (nothing to exclude).

    `vol_full_annual_mean` (the low-volume floor marker) is now POPULATED --
    v2's `mass_full` finally makes it derivable here (v3's NaN-always gap is
    closed); it stays on the FULL basis regardless of the page's toggle, the
    same convention `_field_dynamics_frame`/`_field_pp_frame` already use."""
    sdg_year_df = _load_sdg_year(ctx)
    labels = P._sdg_labels(ctx)[["sdg_idx", "sdg_label", "sdg_number"]]
    vcol = "mass_full" if subs["basis"] == "full" else "mass_frac"
    note = (DYNAMICS_DENOM_NOTE + " Volumes are sdg_year.mass_frac/mass_full on the CURRENT basis, "
           "all doc types, window-sliced 2020-2024 -- sdg.parquet's whole-run 2020-2025 mass is no "
           "longer used for this figure.")
    rows = []
    for iid in ids:
        d = sdg_year_df[(sdg_year_df["institution_id"] == iid)
                        & sdg_year_df["year"].between(CORE_WINDOW[0], CORE_WINDOW[1])]
        for _, lab in labels.iterrows():
            sidx = int(lab["sdg_idx"])
            g = d[d["sdg_idx"] == sidx]
            vol_by_year = dict(zip(g["year"], g[vcol])) if len(g) else {}
            full_by_year = dict(zip(g["year"], g["mass_full"])) if len(g) else {}
            w1, w2 = _window_mean(vol_by_year, DYNAMICS_W1), _window_mean(vol_by_year, DYNAMICS_W2)
            w1_full, w2_full = _window_mean(full_by_year, DYNAMICS_W1), _window_mean(full_by_year, DYNAMICS_W2)
            rows.append({"institution_id": iid, "taxon_id": sidx, "taxon_label": lab["sdg_label"],
                        "value": _dynamics_value(vol_by_year), "fwci_mean": None, "ref_value": None,
                        "denominator": note, "denom_value": w1 if w1 > 0 else np.nan,
                        "domain_id": SDG_DOMAIN_ID, "domain_order": int(lab["sdg_number"]),
                        "vol_display": _dynamics_delta_str(w1, w2),
                        "vol_full_annual_mean": _annual_full_mean(w1_full, w2_full),
                        "vol_top10": None})
    out = pd.DataFrame(rows, columns=METRIC_FRAME_COLS)
    return _attach_dynamics_ref(ctx, out, "sdg", None, subs["basis"])


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


def _field_pp_frame(ctx, ids, tree, floor, want_vol: bool, basis: str = "frac") -> pd.DataFrame:
    """Field-grain `pp` or `vol_top10` from `impact_fields.parquet`. Missing
    cell (this institution has no impact_fields row for this field/tree/
    floor) means the field is simply ABSENT from the returned frame for that
    institution -- never a 0 or NaN placeholder row (this table is sparse-
    to-candidate-cells, unlike sdg.parquet's dense convention).

    `vol_display`/`denom_value` (the PP gutter) now follow `basis` (2BR3
    item 1/SS2.5: "PP gutter = pp_denominator_frac when basis=frac /
    n_works_full when full" -- BOTH already ship on `impact_fields.parquet`,
    confirmed 2026-08-31 via a live schema dump; this metric is ALWAYS on the
    articles+reviews basis regardless of which one is picked, only the
    NUMBER shown switches). `vol_full_annual_mean` (the low-volume FLOOR
    marker) stays on `n_works_full` unconditionally -- never basis-dependent,
    same convention as the dynamics frames. `vol_top10` (2B-R2-3: retired as
    a selector tab, kept AS DATA) is populated ONLY on the `pp` branch."""
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
            gutter = float(row["pp_denominator_frac"]) if basis == "frac" else n_full  # item 1 basis toggle
            vol_top10 = float(row["pp_top10_frac"]) * n_full
            if want_vol:
                value = vol_top10
                denom = (f"pp_top10_frac x n_works_full (field-grain, tree={tree}, floor={floor}; "
                        "n_works_full = full work count, articles+reviews, 2020-2024)")
                ref = None
                vt10 = None
                denom_value = None  # vol_top10 IS the count -- no separate ratio denominator (v4 SS2.5)
                # D4 audit fix (2C/CD5): `value` here is ALWAYS n_full-derived
                # (the denom note above says so), regardless of `basis` -- the
                # shared `gutter` variable, however, toggles to
                # pp_denominator_frac under basis="frac", a DIFFERENT count on
                # a DIFFERENT basis than the bar it would sit under. That is
                # exactly the class of silent value/gutter basis mix D4 rules
                # out. `vol_top10` has no selector tab (SELECTOR_METRICS
                # excludes it) so this was inert for any rendered chart, but
                # the frame is a real, callable, testable surface -- gutter
                # now mirrors the bar directly (the same "vol_display = value"
                # convention `_vol_frame` already uses for raw-count metrics),
                # never a second, basis-toggled number.
                vol_display = value
            else:
                value = float(row["pp_top10_frac"])
                denom = (f"pp_denominator_frac / n_works_full (articles+reviews, 2020-2024, field grain, "
                        f"tree={tree}, floor={floor}, on the current basis)")
                ref = float(ref_means.get(fid, np.nan))
                vt10 = vol_top10
                denom_value = gutter  # literally what pp_top10_frac divides by, on the current basis
                vol_display = gutter
            rows.append({"institution_id": iid, "taxon_id": fid, "taxon_label": fname,
                        "value": value, "fwci_mean": None, "ref_value": ref, "denominator": denom,
                        "denom_value": denom_value,
                        "domain_id": dom, "domain_order": _OA_DOMAIN_ORDER_MAP.get(dom),
                        "vol_display": vol_display, "vol_full_annual_mean": n_full / N_CORE_YEARS,
                        "vol_top10": vt10})
    return pd.DataFrame(rows, columns=METRIC_FRAME_COLS)


SDG_SHARE_FIELD_DENOM_NOTE = (
    "Numerator: the field's DISTINCT SDG-tagged volume (a work counts once toward this field even "
    "when it carries more than one Sustainable Development Goal); denominator: the field's total "
    "volume. Both articles+reviews, 2020-2024, on the SAME window and the SAME basis as the page's "
    "current toggle -- no window mismatch between numerator and denominator."
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


def _sdg_share_field_ref_means(ctx: dict, tree: str, basis: str) -> pd.Series:
    """2BR3 item 2 fix: population mean of the SAME corrected ratio
    `_sdg_share_field_frame` computes per institution (field's DISTINCT
    SDG-tagged mass / field mass, `sdg_fields.parquet` v2's `mass_any_<basis>`
    -- never the OLD per-goal-summed `mass`, which is the 264.8%-bug
    mechanism WT_2BR3.md task 5.2 pins), among institutions with nonzero
    field mass, per field x tree x basis. `fields.parquet` is BESTFIT-tree-
    only (its own grain note) so this reference is computed against that one
    basis regardless of `tree` (the same approximation WT 2BR2 claim #15
    cleared). Cached per (tree, basis) on ctx."""
    key = f"_sdgshare_ref_{tree}_{basis}"
    if key in ctx:
        return ctx[key]
    sdg_fields_df = _load_sdg_fields(ctx)
    numer_col = "mass_any_full" if basis == "full" else "mass_any_frac"
    vol_col = "vol_full" if basis == "full" else "vol_frac"
    sub = sdg_fields_df[(sdg_fields_df["tree"].astype(str) == tree) & (sdg_fields_df["field_id"] != -1)]
    tagged = sub.groupby(["institution_id", "field_id"])[numer_col].sum()  # v2 grain has no sdg_idx to double-count over
    fields_raw = _load_fields_raw(ctx).set_index(["institution_id", "field_id"])[vol_col]
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


SDG_SHARE_EPS = 1e-6  # v2's numerator/denominator are matched-window/matched-basis -- value must be <= 1 + this


def _sdg_share_field_frame(ctx, subs, ids, tree) -> pd.DataFrame:
    """2BR3 item 2 fix: numerator = `sdg_fields.mass_any_<basis>` (v2,
    DISTINCT-tagged -- a work with 3 goals contributes once, not 3x, closing
    the 264.8%-share bug WT_2BR3.md task 5.2 traces to the OLD per-goal
    `groupby(institution_id, field_id)["mass"].sum()`); denominator = the
    field's own vol on the SAME basis as the numerator and the SAME 2020-2024
    window -- asserted `<= 1 + SDG_SHARE_EPS` HERE, not left to a caller."""
    basis = subs["basis"]
    numer_col = "mass_any_full" if basis == "full" else "mass_any_frac"
    vol_col = "vol_full" if basis == "full" else "vol_frac"
    sdg_fields_df = _load_sdg_fields(ctx)
    sub = sdg_fields_df[(sdg_fields_df["tree"].astype(str) == tree) & (sdg_fields_df["institution_id"].isin(ids))
                        & (sdg_fields_df["field_id"] != -1)]
    tagged = sub.groupby(["institution_id", "field_id"])[numer_col].sum()
    field_mass = subs["fields_df"].set_index(["institution_id", "field_id"])[vol_col]
    field_mass_full = subs["fields_df"].set_index(["institution_id", "field_id"])["vol_full"]
    name_map = P._field_domain_map(ctx)[["field_id", "field_name", "domain_id"]]
    ref_means = _sdg_share_field_ref_means(ctx, tree, basis)

    rows = []
    for iid in ids:
        fids = sorted(int(x) for x in sub.loc[sub["institution_id"] == iid, "field_id"].unique())
        for fid in fids:
            fm = float(field_mass.get((iid, fid), 0.0))          # denominator, current basis
            fm_full = float(field_mass_full.get((iid, fid), 0.0))  # floor marker source, always full
            num = float(tagged.get((iid, fid), 0.0))              # numerator, DISTINCT-tagged, same basis
            value = (num / fm) if fm > 0 else np.nan
            assert not (value is not None and value == value and value > 1.0 + SDG_SHARE_EPS), (
                f"SDG share > 1 (item-2 regression): institution={iid} field={fid} basis={basis} "
                f"num={num} denom={fm} value={value}")
            name_row = name_map.loc[name_map["field_id"] == fid]
            fname = name_row["field_name"].iloc[0] if len(name_row) else str(fid)
            dom = int(name_row["domain_id"].iloc[0]) if len(name_row) else None
            rows.append({"institution_id": iid, "taxon_id": fid, "taxon_label": fname,
                        "value": value, "fwci_mean": None, "ref_value": float(ref_means.get(fid, np.nan)),
                        "denominator": SDG_SHARE_FIELD_DENOM_NOTE, "denom_value": fm if fm > 0 else np.nan,
                        "domain_id": dom, "domain_order": _OA_DOMAIN_ORDER_MAP.get(dom),
                        "vol_display": fm, "vol_full_annual_mean": fm_full / N_CORE_YEARS,
                        "vol_top10": None})
    return pd.DataFrame(rows, columns=METRIC_FRAME_COLS)


# ============================================================================
# 2C additions (Stream CD5, BUILD_PLAN_2C.md S3 CD5; D2/D3/D4/D14) -- the
# `fwci` metric, all FOUR grains, from `fwci_taxa.parquet`/`fwci_taxa_ref.
# parquet` (pipeline step 18, Stream P8, untouched here -- CD5 only READS
# what P8 shipped). BASIS-PINNED throughout: `_fwci_frame` takes no `subs`
# argument at all, so `value`/`vol_display`/`denominator` cannot vary with
# the page's full/frac toggle even by accident (decisions log 2026-09-01:
# FWCI is FULL/binary attribution always, "matches Collaborate's shipped
# FWCI-median convention"). Field/subfield are additionally TREE-PINNED
# (bestfit only, WT_2C.md claim 2 adjustment #1) -- disclosed in
# `FWCI_DENOM_NOTE`, never silently ignored.
# ============================================================================

FWCI_GRAIN_WORD = {"field": "field", "subfield": "subfield", "sdg": "goal", "erc": "panel"}
# D3/WT_2C.md claim 1: the hover reference label names the GRAIN, never says
# "average" (the corpus MEAN is pinned near 1.0 by construction and would
# misread as a neutral baseline next to a MEDIAN bar). `sdg`/`erc` use the
# reader-facing words ("goal"/"panel") the rest of Compare already uses for
# those taxa, not the internal grain code.


def fwci_ref_label(level: str) -> str:
    """VC hover hook (D2 item 2/D3): the exact, grain-specific reference-line
    sentence -- "European median work in this field/subfield/goal/panel".
    This is a PER-FRAME constant, not a per-row column (every row of one
    `_fwci_frame(..., level)` call shares the same grain), so it rides beside
    the frame rather than inside `METRIC_FRAME_COLS` -- VC calls this
    directly (or reads `FWCI_REF_LABEL[level]`) instead of `charts_compare.
    HOVER_REFERENCE` (the generic, hardcoded "index reference" string PP/
    SDG-share/Dynamics share -- not swappable per grain, and wrong for a
    work-level median statistic, WT_2C.md claim 1's own recommendation)."""
    assert level in LEVELS, f"unknown level {level!r}"
    return f"European median work in this {FWCI_GRAIN_WORD[level]}"


FWCI_REF_LABEL = {level: fwci_ref_label(level) for level in LEVELS}  # VC convenience: a plain dict, same strings


def _fwci_denom_note(level: str) -> str:
    """The full FWCI disclosure sentence (D2 item 1): covered CORE-AR works
    only, articles+reviews 2020-2024, FULL/binary attribution, bestfit-only
    at field/subfield (the tree toggle does not move this metric), the
    ERC-grain 7.3% coverage gap named on ERC frames only, n_covered<3 never
    shown (a property of `fwci_taxa.parquet` itself, P8 -- restated here so
    the caption never has to guess why a taxon is simply absent)."""
    note = (
        "Median FWCI (Field-Weighted Citation Impact) over this institution's covered CORE-AR "
        "works (articles & reviews, 2020-2024, FULL/binary attribution -- a work counts once per "
        "institution present regardless of collaboration weight); taxa covered by fewer than 3 "
        "such works are not shown."
    )
    if level in ("field", "subfield"):
        note += (" Field and subfield FWCI use the bestfit taxonomy only -- unlike every other "
                 "metric here, the tree toggle does not change this figure.")
    if level == "erc":
        note += (" ERC-panel FWCI carries a measured ~7.3% coverage gap: not every CORE-AR work "
                 "has a matching ERC-panel classification.")
    return note


FWCI_DENOM_NOTE = {level: _fwci_denom_note(level) for level in LEVELS}


def _load_fwci_taxa(ctx: dict) -> pd.DataFrame:
    """Lazy, ctx-cached: `fwci_taxa.parquet` (P8) -- one row per (institution_
    id, grain, taxon_id), n_covered>=3 only (the source table's own floor,
    never re-applied here)."""
    if "fwci_taxa_df" not in ctx:
        ctx["fwci_taxa_df"] = pd.read_parquet(Path(ctx["data_dir"]) / "fwci_taxa.parquet")
    return ctx["fwci_taxa_df"]


def _load_fwci_taxa_ref(ctx: dict) -> pd.DataFrame:
    """Lazy, ctx-cached: `fwci_taxa_ref.parquet` (P8, D3) -- the European
    corpus-wide reference MEDIAN per (grain, taxon_id), NOT institution
    filtered, no floor (every taxon that appears at least once in the CORE-AR
    corpus ships a row here, INCLUDING the 27 rows where `eu_median_work_
    fwci == 0.0` -- a genuine humanities citation-practice fact, P8 deviation
    #2/WT_2C.md claim 1, never dropped, coerced or treated as missing)."""
    if "fwci_taxa_ref_df" not in ctx:
        ctx["fwci_taxa_ref_df"] = pd.read_parquet(Path(ctx["data_dir"]) / "fwci_taxa_ref.parquet")
    return ctx["fwci_taxa_ref_df"]


def _fwci_taxon_labels(ctx: dict, level: str) -> pd.DataFrame:
    """taxon_id -> taxon_label (+ the ONE extra column `_domain_cols_for`
    needs at this level: `domain_id` for field, `domain_id`+`field_id` for
    subfield, `erc_domain` for erc, `sdg_number` for sdg) -- the SAME source
    tables `_share_frame`/`_si_frame` already read for their own taxon names,
    so a label never drifts between metrics. Full (unfiltered by any one
    field), so subfield drilling happens the SAME way `_share_frame` does it
    -- filter the MERGED frame by `field_id` afterwards, not this lookup."""
    if level == "field":
        m = P._field_domain_map(ctx)[["field_id", "field_name", "domain_id"]]
        return m.rename(columns={"field_id": "taxon_id", "field_name": "taxon_label"})
    if level == "subfield":
        m = P._subfield_field_domain_map(ctx)[["subfield_id", "subfield_name", "field_id", "domain_id"]]
        return m.rename(columns={"subfield_id": "taxon_id", "subfield_name": "taxon_label"})
    if level == "sdg":
        m = P._sdg_labels(ctx)[["sdg_idx", "sdg_label", "sdg_number"]]
        return m.rename(columns={"sdg_idx": "taxon_id", "sdg_label": "taxon_label"})
    # erc
    m = P._erc_panels(ctx)[["panel_idx", "panel_label", "erc_domain"]]
    return m.rename(columns={"panel_idx": "taxon_id", "panel_label": "taxon_label"})


def _fwci_frame(ctx: dict, ids: list[str], level: str, field_id: int | None = None) -> pd.DataFrame:
    """FWCI metric frame, all four grains (D2/D3/D4). BASIS-PINNED: no `subs`
    argument at all -- `value`/`vol_display`/`denominator` cannot move with
    the page's full/frac toggle (decisions log 2026-09-01).

    `value` = `fwci_median` (the bar, D2 ruling). `fwci_mean` = the hover-only
    companion (v5 new column). `denom_value` = `vol_display` =
    `vol_full_annual_mean`-input = `n_covered` (the hover denominator AND the
    D6 hatch-trigger column, decisions log 2026-09-01 D6 amendment -- FWCI
    behaves like PP's `n_works_full`, genuinely per-row, never like Share's
    institution-constant `denom_value`). `ref_value` is the SAME (grain,
    taxon_id) row of `fwci_taxa_ref.parquet`, merged (never back-computed, so
    a real 0.0 flows through a plain join untouched -- no truthiness test
    anywhere near it, per the 27-taxa-are-legitimately-zero fact above)."""
    taxa = _load_fwci_taxa(ctx)
    sub = taxa[(taxa["grain"] == level) & (taxa["institution_id"].isin(ids))]
    labels = _fwci_taxon_labels(ctx, level)
    base = sub.merge(labels, on="taxon_id", how="left", validate="m:1")
    missing = base[base["taxon_label"].isna()]
    assert missing.empty, (
        f"fwci_taxa.parquet ships a {level} taxon_id with no matching label: "
        f"{sorted(missing['taxon_id'].unique().tolist())}")
    if level == "subfield":
        assert field_id is not None, "level='subfield' needs field_id (drill within one field)"
        base = base[base["field_id"] == field_id]

    ref = _load_fwci_taxa_ref(ctx)
    ref = ref[ref["grain"] == level][["taxon_id", "eu_median_work_fwci"]]
    base = base.merge(ref, on="taxon_id", how="left", validate="m:1")

    n_covered = base["n_covered"].astype("float64")
    out = pd.DataFrame({
        "institution_id": base["institution_id"],
        "taxon_id": base["taxon_id"].astype(int),
        "taxon_label": base["taxon_label"],
        "value": base["fwci_median"].astype("float64"),
        "fwci_mean": base["fwci_mean"].astype("float64"),
        "ref_value": base["eu_median_work_fwci"].astype("float64"),
        "denominator": FWCI_DENOM_NOTE[level],
        "denom_value": n_covered,
        "vol_display": n_covered,
        "vol_full_annual_mean": n_covered / N_CORE_YEARS,
        "vol_top10": None,
    }, index=base.index)
    out["domain_id"], out["domain_order"] = _domain_cols_for(base, level)
    return out.sort_values(["institution_id", "taxon_id"]).reset_index(drop=True).reindex(columns=METRIC_FRAME_COLS)


def metric_frame(ctx: dict, subs: dict, ids: list[str], level: str, metric: str, *,
                 field_id: int | None = None, tree: str | None = None, floor: int = 30) -> pd.DataFrame:
    """2B-R-5/6/8 the ONE 'Compare by' metric selector, generalised over
    every (level, metric) combination the Compare page needs:

      level='field'                -> taxon = 26 fields, all of {share,vol_top10,pp,sdg_share,dynamics,si,fwci}.
      level='subfield'             -> taxon = subfields of ONE `field_id` (required); share/si/dynamics/fwci only.
      level='erc'                  -> taxon = 28 ERC panels; share/si/vol/fwci (2B-R-8 'Volume').
      level='sdg'                  -> taxon = 16 SDGs; share/dynamics/vol/fwci (2B-R-8 'Volume tagged').

    `fwci` (2C, Stream CD5, D2/D3) is available at ALL FOUR grains, is
    BASIS-PINNED (ignores `subs['basis']` entirely -- decisions log
    2026-09-01) and field/subfield are additionally bestfit-tree-only
    (`tree`/`subs['tree']` have no effect on this metric, disclosed in its
    own `denominator` note, never silently ignored).

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
    tree = tree or (subs or {}).get("tree", "bestfit")
    basis = (subs or {}).get("basis", "frac")  # v4 SS2.5: pp/vol_top10/vol/sdg-dynamics now basis-toggle-aware too

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
        return _sdg_dynamics_frame(ctx, subs or {"basis": basis}, ids)  # level == "sdg" (erc has no dynamics, marked unavailable)
    if metric == "pp":
        return _field_pp_frame(ctx, ids, tree, floor, want_vol=False, basis=basis)  # level == "field" only (asserted available)
    if metric == "vol_top10":
        return _field_pp_frame(ctx, ids, tree, floor, want_vol=True, basis=basis)
    if metric == "sdg_share":
        return _sdg_share_field_frame(ctx, subs, ids, tree)
    if metric == "vol":
        return _vol_frame(ctx, subs, ids, level)  # level in {"erc", "sdg"} only (field/subfield marked unavailable)
    if metric == "fwci":
        return _fwci_frame(ctx, ids, level, field_id)  # basis-pinned (D4/D2): subs never reaches this branch
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

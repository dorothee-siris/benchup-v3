"""
app/lib/badges.py -- umbrella/aggregate, type-corrected and catch-all badges
(Sprint 2 Phase 2A, Stream F). Pure functions over the institution index /
engine row dicts -- no Streamlit import.

Umbrella and type-corrected are asserted MUTUALLY EXCLUSIVE on any one row
(BUILD_PLAN_2A.md L7, WT #14): the umbrella rule reads the PATCHED `type`
column (config.yaml umbrella_badge.basis_column), never `type_openalex`,
specifically because the `type_openalex` basis would flag Sciences Po,
CentraleSupelec and EHESS -- all three type-corrected TO education -- as
umbrellas at the same time their own badge says "this is really education".
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from lib import copy, palette
from lib.app_config import CFG
from lib.search import normalize

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
UMBRELLA_SUPPLEMENT_PATH = DATA_DIR / "overrides" / "umbrella_supplement.csv"


def umbrella_flags(index_df: pd.DataFrame) -> pd.Series:
    """type in CFG umbrella_badge.types AND total_full_2020_2024 > multiplier x
    the (country_code, type) median -- both read on the PATCHED `type` column,
    median computed over the WHOLE index, not just the candidate rows (M5.7)
    -- OR named in overrides/umbrella_supplement.csv (matched on institution_id
    where present, else on normalised display_name). Returned indexed by
    institution_id."""
    cfg = CFG["umbrella_badge"]
    type_col = index_df[cfg["basis_column"]].astype(str)
    country_col = index_df["country_code"].astype(str)
    medians = index_df.groupby([country_col, type_col])["total_full_2020_2024"].transform("median")
    rule_flag = type_col.isin(cfg["types"]) & (index_df["total_full_2020_2024"] > cfg["multiplier"] * medians)

    supplement = pd.read_csv(UMBRELLA_SUPPLEMENT_PATH)
    by_id = set(supplement["institution_id"].dropna())
    by_name = {normalize(n) for n in supplement["display_name"].dropna()}
    name_hit = index_df["display_name"].map(normalize).isin(by_name)
    supplement_flag = index_df["institution_id"].isin(by_id) | name_hit

    flags = rule_flag | supplement_flag
    return pd.Series(flags.to_numpy(), index=index_df["institution_id"].to_numpy(), name="is_umbrella")


def umbrella_medians(index_df: pd.DataFrame) -> dict:
    """(country_code, type) -> median total_full_2020_2024 over the whole
    index -- what the umbrella tooltip compares a flagged row against."""
    cfg = CFG["umbrella_badge"]
    type_col = index_df[cfg["basis_column"]].astype(str)
    country_col = index_df["country_code"].astype(str)
    med = index_df.groupby([country_col, type_col])["total_full_2020_2024"].median()
    return {key: float(v) for key, v in med.items()}


def type_corrected_badge(row) -> str | None:
    """CFG type_overrides.ui_badge formatted with the ORIGINAL type, whenever
    `type != type_openalex` (both compared as str). Works on either a raw
    index_df row (type_openalex always populated) or an engine evidence dict
    (type_openalex already None-clamped when equal to type)."""
    type_oa = row["type_openalex"]
    if type_oa is None or pd.isna(type_oa):
        return None
    t, t_oa = str(row["type"]), str(type_oa)
    if t == t_oa:
        return None
    return CFG["type_overrides"]["ui_badge"].format(type_openalex=t_oa)


def catchall_tooltip(share) -> str:
    """CFG-free formatting wrapper around copy.CATCHALL_TOOLTIP: NaN/None ->
    palette.NA_MARK, never 0 (BUILD_PLAN_2A.md L11)."""
    if share is None or pd.isna(share):
        return copy.CATCHALL_TOOLTIP.format(share=palette.NA_MARK)
    return copy.CATCHALL_TOOLTIP.format(share=f"{float(share):.1%}")


def badges_for(row, flags: pd.Series, medians: dict) -> list[str]:
    """Text labels for one row's badge cell. Raises if the row would carry
    BOTH an umbrella and a type-corrected badge (BUILD_PLAN_2A.md L7 hard
    invariant, never a styling preference)."""
    iid = row["institution_id"]
    is_umbrella = bool(flags.get(iid, False))
    corrected = type_corrected_badge(row)
    assert not (is_umbrella and corrected), (
        f"{iid}: umbrella and type-corrected badges both apply to one row -- "
        f"BUILD_PLAN_2A.md L7 forbids this (WT #14)")
    out = []
    if is_umbrella:
        out.append(copy.UMBRELLA_BADGE_LABEL)
    if corrected:
        out.append(corrected)
    return out

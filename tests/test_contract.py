"""tests/test_contract.py -- Class-1 data-contract invariants over app/data/ (run with cwd=app/).

Covers: contract_check.check() clean (every declared file/column/dtype/key present, no
undeclared drop); fields/subfields shares sum to 1; erc.share sums <= 1; sdg.share per-row
bounds; the 16-id type-override set identity; topics_dim exclusion reason-code coverage;
impact_cells and index PP confidence-interval ordering; umbrella_supplement.csv shape.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CONTRACT_PATH = ROOT / "docs" / "data_contract.yaml"

sys.path.insert(0, str(ROOT / "ops"))
from contract_check import check  # noqa: E402


@pytest.fixture(scope="module")
def contract() -> dict:
    return yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))


def _read(fname: str) -> pd.DataFrame:
    path = DATA_DIR / fname
    if path.suffix == ".csv":
        return pd.read_csv(path)
    return pd.read_parquet(path)


def test_contract_check_clean(contract: dict) -> None:
    """Every declared file present, every declared column/dtype/key verified, no undeclared
    drop vs source_manifest.json's table_schemas. This single check covers 10 tables (8 parquet
    + 2 override csv)."""
    violations = check(DATA_DIR, contract)
    assert violations == [], "\n".join(violations)


def test_fields_shares_sum_to_one() -> None:
    fields = _read("fields.parquet")
    for col in ("share_frac", "share_full"):
        s = fields.groupby("institution_id", observed=True)[col].sum().astype("float64")
        max_dev = float((s - 1).abs().max())
        print(f"fields.{col}: max|sum-1| over {len(s)} institutions = {max_dev:.3e}")
        assert max_dev <= 1e-6


def test_subfields_shares_sum_to_one() -> None:
    subfields = _read("subfields.parquet")
    for col in ("share_frac", "share_full"):
        s = subfields.groupby("institution_id", observed=True)[col].sum().astype("float64")
        max_dev = float((s - 1).abs().max())
        print(f"subfields.{col}: max|sum-1| over {len(s)} institutions = {max_dev:.3e}")
        assert max_dev <= 1e-6


def test_erc_share_sum_le_one() -> None:
    erc = _read("erc.parquet")
    s = erc.groupby("institution_id", observed=True)["share"].sum().astype("float64")
    print(f"erc.share sum per institution: max={s.max():.7f}, min={s.min():.7f}, n={len(s)}")
    assert s.max() <= 1 + 1e-6


def test_sdg_share_bounds_per_row() -> None:
    sdg = _read("sdg.parquet")
    lo, hi = float(sdg["share"].min()), float(sdg["share"].max())
    print(f"sdg.share per-row range over {len(sdg)} rows: [{lo}, {hi}]")
    assert lo >= 0 - 1e-6
    assert hi <= 1 + 1e-6
    per_inst_sum = sdg.groupby("institution_id", observed=True)["share"].sum().astype("float64")
    print(f"sdg.share sum per institution (multi-label, NOT bounded by 1): max={per_inst_sum.max():.4f}")


def test_type_override_id_set() -> None:
    index = _read("index.parquet")
    overrides = _read("overrides/type_overrides.csv")
    type_s = index["type"].astype(str)
    type_openalex_s = index["type_openalex"].astype(str)
    diff_ids = set(index.loc[type_s != type_openalex_s, "institution_id"])
    locked_ids = set(overrides.loc[overrides["locked"] == True, "institution_id"])  # noqa: E712
    print(f"type-patched institution_ids: {len(diff_ids)} (index) vs {len(locked_ids)} (overrides, locked=True)")
    assert diff_ids == locked_ids
    assert len(diff_ids) == 16
    assert "I4210153845" in diff_ids
    funder_row = overrides.loc[overrides["institution_id"] == "I4210153845"].iloc[0]
    assert funder_row["type_override"] == "funder"


def test_topics_dim_exclusion_reason_codes() -> None:
    td = _read("topics_dim.parquet")
    excluded = td[td["is_excluded"] == True]  # noqa: E712
    non_excluded = td[td["is_excluded"] == False]  # noqa: E712
    print(f"topics_dim: {len(excluded)} excluded (811-list), {len(non_excluded)} not excluded")
    assert excluded["exclusion_reason_code"].notna().all()
    assert non_excluded["exclusion_reason_code"].isna().all()


def test_impact_cells_ci_ordering() -> None:
    ic = _read("impact_cells.parquet")
    ok_low = (ic["pp_ci_low"] <= ic["pp_top10_frac"] + 1e-6).all()
    ok_high = (ic["pp_top10_frac"] <= ic["pp_ci_high"] + 1e-6).all()
    print(f"impact_cells CI ordering over {len(ic)} rows: low<=pp {ok_low}, pp<=high {ok_high}")
    assert ok_low and ok_high


def test_index_ci_ordering() -> None:
    idx = _read("index.parquet")
    mask = idx["pp_top10_frac"].notna()
    sub = idx.loc[mask]
    ok_low = (sub["pp_ci_low"] <= sub["pp_top10_frac"] + 1e-6).all()
    ok_high = (sub["pp_top10_frac"] <= sub["pp_ci_high"] + 1e-6).all()
    print(f"index CI ordering over {mask.sum()}/{len(idx)} non-null rows: low<=pp {ok_low}, pp<=high {ok_high}")
    assert ok_low and ok_high


def test_umbrella_supplement_shape() -> None:
    supp = _read("overrides/umbrella_supplement.csv")
    print(f"umbrella_supplement.csv: {len(supp)} rows, columns={list(supp.columns)}")
    assert list(supp.columns) == ["display_name", "institution_id", "note"]
    assert len(supp) >= 24

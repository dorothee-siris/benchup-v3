"""
Shared REAL-DATA loader for the R1 (stream R-D2) A/B prototypes -- throwaway,
`design-system/ab/**` only, never imported by anything shipped.

Builds the BUILD_PLAN_2A.md section 9.4 frames straight from the deployed
parquet files. It deliberately does NOT import `lib.profile_data` (stream R-B
is writing that in parallel and it may not exist yet) -- the column contract is
reproduced here by hand, exactly as section 9.4 declares it, so the prototypes
and `tests/test_charts.py` exercise the same shapes the real functions will
return.

Seeds (both named in the R-D2 brief):
  I68947357  Universite de Strasbourg  (resolved by display_name in index.parquet)
  I40413290  University of Gdansk
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

APP_ROOT = Path(__file__).resolve().parent.parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

DATA = APP_ROOT / "data"

STRASBOURG = "I68947357"
GDANSK = "I40413290"
TREE = "bestfit"
BASIS_COL = "share_frac"


def _dim() -> pd.DataFrame:
    return pd.read_parquet(
        DATA / "topics_dim.parquet",
        columns=["domain_id", "domain_name", "field_id", "field_name",
                 "subfield_id", "subfield_name"],
    )


def resolve_strasbourg() -> str:
    """Resolve Universite de Strasbourg by display_name (R-D2 brief)."""
    ix = pd.read_parquet(DATA / "index.parquet", columns=["institution_id", "display_name"])
    hit = ix[ix["display_name"].str.contains("Strasbourg", case=False, na=False)]
    hit = hit[hit["display_name"].str.startswith(("Universit", "Univers"))]
    return str(hit.iloc[0]["institution_id"])


def fields_table(iid: str, tree: str = TREE, basis_col: str = BASIS_COL) -> pd.DataFrame:
    """section 9.4 `profile_data.fields_table` columns."""
    fmap = _dim().drop_duplicates("field_id")[
        ["field_id", "field_name", "domain_id", "domain_name"]]
    f = pd.read_parquet(DATA / "fields.parquet")
    f = f[(f["institution_id"] == iid) & (f["tree"].astype(str) == tree)]
    out = f.merge(fmap, on="field_id", how="left")
    out["share"] = out[basis_col]
    return out[["field_id", "field_name", "domain_id", "domain_name",
                "vol_full", "vol_frac", "share", "si"]].reset_index(drop=True)


def subfields_table(iid: str, tree: str = TREE, basis_col: str = BASIS_COL) -> pd.DataFrame:
    """section 9.4 `profile_data.subfields_table` columns (si NaN below the G6 floor)."""
    smap = _dim().drop_duplicates("subfield_id")[
        ["subfield_id", "subfield_name", "field_id", "field_name", "domain_id", "domain_name"]]
    s = pd.read_parquet(DATA / "subfields.parquet")
    s = s[(s["institution_id"] == iid) & (s["tree"].astype(str) == tree)]
    out = s.merge(smap, on="subfield_id", how="left", suffixes=("", "_dim"))
    out["share"] = out[basis_col]
    return out[["subfield_id", "subfield_name", "field_id", "field_name",
                "domain_id", "domain_name", "vol_full", "vol_frac",
                "share", "si"]].reset_index(drop=True)


def top_subfields(iid: str, n: int = 20, **kw) -> pd.DataFrame:
    return subfields_table(iid, **kw).sort_values("share", ascending=False).head(n).reset_index(drop=True)

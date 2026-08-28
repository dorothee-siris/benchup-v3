"""
app/lib/exports.py -- CSV export of a (filtered) lens ranking (Sprint 2 Phase
2A, Stream F). Pure functions, no Streamlit import: `ranked.py`/`views_find.py`
call these to get bytes for `st.download_button`.
"""
from __future__ import annotations

import pandas as pd

_COLUMNS = ["rank", "institution_id", "display_name", "country_code", "type",
            "total_full_2020_2024", "lens_score", "evidence"]


def _evidence_str(row: dict) -> str:
    """Compact text rendering of whatever evidence fields a row carries --
    `shape_top3_fields` (present on every lens row via `base_evidence`) if
    nothing more specific applies."""
    fields = row.get("shape_top3_fields") or []
    if fields:
        return "; ".join(f"{f['field_name']} ({f['share']:.1%})" for f in fields)
    return ""


def ranking_csv(rows, *, seed_id, lens, tree, basis, snapshot, filters_label) -> bytes:
    """Full (filtered) ranking as CSV bytes: original competition ranks
    preserved (gaps kept, never renumbered -- VIZ_SPEC S1.7), plus constant
    columns so the file is self-describing outside the app."""
    records = []
    for r in rows:
        records.append({
            "rank": r["rank"],
            "institution_id": r["institution_id"],
            "display_name": r["display_name"],
            "country_code": r["country_code"],
            "type": r["type"],
            "total_full_2020_2024": r.get("total_full_2020_2024"),
            "lens_score": r.get("lens_score"),
            "evidence": _evidence_str(r),
        })
    df = pd.DataFrame(records, columns=_COLUMNS)
    df["seed_id"] = seed_id
    df["lens"] = lens
    df["tree"] = tree
    df["basis"] = basis
    df["snapshot"] = snapshot
    df["filters"] = filters_label
    return df.to_csv(index=False).encode("utf-8")


def ranking_filename(seed_id: str, lens: str, tree: str, basis: str, filtered: bool) -> str:
    """`benchup_{seed}_{lens}_{tree}_{basis}[_filtered].csv` -- VIZ_SPEC S1.7."""
    suffix = "_filtered" if filtered else ""
    return f"benchup_{seed_id}_{lens}_{tree}_{basis}{suffix}.csv"

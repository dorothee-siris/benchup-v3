"""
The shared ranked-table component for every `tbl-lens-ranked` tab and the
concordance overview (VIZ_SPEC.md S2.3, S2.4). Consumed by Stream E.

Implements the Stream D1 A/B verdict (`design-system/ab/AB_VERDICT.md`,
`docs/VIZ_SPEC.md` S4):
  - A/B #1 winner: `st.column_config.ProgressColumn` for the lens score,
    never a Plotly ranked-dot chart, in every ordinary lens tab.
  - A/B #2 winner: a k-of-n table with a hit-lens-chip text column, never a
    full rank matrix, for the concordance overview.

Refinement R1 (BUILD_PLAN_2A.md S9.2 L22, gate-2A feedback #7/#8/#10): the
badge column is gone (badges now live on the seed profile header only --
L7/L17); every table carries two size columns (full, fractional); the
evidence cell is the lens-specific text the engine computes
(`row["evidence_text"]`, L21/S9.4 -- "top field" no longer fits every lens);
country is shown by its English name (`lib.countries.name`), with the raw
code kept as a hidden column for anything downstream that still wants it.

Pure functions (`format_rows`, `depth_caption`, `format_concordance`,
`concordance_caption`) take engine output and return `pandas.DataFrame`/`str`
-- no Streamlit import, testable headlessly (`tests/test_ranked.py`). The two
render functions own the Streamlit widget calls only.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from lib import copy, countries
from lib.app_config import CFG
from lib.engine import RANK_VISIBLE_MAX
from lib.palette import NA_MARK

WINDOW_START, WINDOW_END = CFG["window"]
NOT_IN_TOPN = "--"  # A/B #2 winner's matrix cell language is unused here (k-count
                     # table won); kept only as the "candidate outside a lens's
                     # visible rank" mark inside the rank_under text below.

# `lib.links` is Stream R-B's module, written in the same wave as this one
# (BUILD_PLAN_2A.md S9.3 R-F2 brief: "use try/except so both orders of
# completion work"). Prefer it once it exists; fall back to the same literal
# builder this file shipped before R1 otherwise.
# NEEDS_CHANGE (progress/R1_F2.md): once R-B has landed for real, drop this
# fallback and the try/except -- `_works_link` should just be
# `from lib.links import works_url as _works_link`.
try:
    from lib.links import works_url as _works_link
except ImportError:
    def _works_link(institution_id: str) -> str:
        """OpenAlex works deep link, window years from CFG (BUILD_PLAN_2A.md
        L10 -- never a typed literal). Fallback only -- see the note above."""
        return (f"https://openalex.org/works?filter=authorships.institutions.id:"
                f"{institution_id},publication_year:{WINDOW_START}-{WINDOW_END}")


def _fmt_size(value) -> str:
    """Thousands separator; NA_MARK for missing (BUILD_PLAN_2A.md L11: n/a never 0)."""
    if value is None or pd.isna(value):
        return NA_MARK
    return f"{value:,.0f}"


def _rank_under_text(row: dict) -> str:
    """'L1 #4 - L3 #7' style secondary reference; '>50' beyond RANK_VISIBLE_MAX
    (engine already caps at RANK_VISIBLE_MAX and returns None past it)."""
    ref = row.get("rank_under_other_lenses")
    if not ref:
        return NA_MARK
    parts = []
    for ln in ("L1", "L3"):
        r = ref.get(ln, {}).get("rank")
        parts.append(f"{ln} #{r}" if r is not None else f"{ln} >{RANK_VISIBLE_MAX}")
    return " · ".join(parts)


def format_rows(rows: list[dict], *, lens: str, depth: int) -> pd.DataFrame:
    """Pure transform: engine `build_rows(...)` output -> the one DataFrame
    shape every `tbl-lens-ranked` render shares (VIZ_SPEC.md S2.4).

    R1/L22: no `badges` kwarg any more; two size columns (`size_full`,
    `size_frac`); `evidence` is whatever lens-specific text the caller set on
    `row["evidence_text"]` (R-B's `evidence.rows_evidence`, wired in by E2),
    NA_MARK when absent or empty -- never a generic "top field" line."""
    out = []
    for row in rows:
        iid = row["institution_id"]
        code = str(row["country_code"])
        out.append({
            "rank": row["rank"],
            "institution": row["display_name"],
            "institution_link": _works_link(iid),
            "country": countries.name(code),
            "country_code": code,
            "type": str(row["type"]),
            "size_full": _fmt_size(row.get("total_full_2020_2024")),
            "size_frac": _fmt_size(row.get("total_frac_2020_2024")),
            "score": row.get("lens_score"),
            "evidence": row.get("evidence_text") or NA_MARK,
            "rank_under": _rank_under_text(row),
            "institution_id": iid,
        })
    df = pd.DataFrame(out)
    df.attrs["lens"] = lens
    df.attrs["depth"] = depth
    return df


def depth_caption(shown: int, total_ranked: int, depth: int, n_tied_extra: int = 0) -> str:
    """VIZ_SPEC.md S2.6, parametric (BUILD_PLAN_2A.md L10 -- no typed digit)."""
    tied = f", +{n_tied_extra} tied" if n_tied_extra else ""
    return (f"Showing the top {shown} of {total_ranked} ranked institutions "
            f"(depth {depth}{tied}) -- search the tail below or download the full ranking.")


def render_ranked_table(df: pd.DataFrame, *, key: str, score_form: str = "progress"):
    """`st.dataframe` per the A/B #1 winner: ProgressColumn score, LinkColumn
    institution, hidden id/country_code, NO badge column (R1/L22). Returns
    the selected `institution_id`s (multi-row select) so the caller can offer
    "Add selected to basket" -- composition (calling `state.add`) stays with
    Stream E."""
    assert score_form == "progress", "A/B #1 winner is ProgressColumn (docs/VIZ_SPEC.md S4)"
    # LinkColumn's `display_text` is one fixed string/regex for the WHOLE column
    # (Streamlit API), not a per-row substitution -- so the institution NAME
    # stays a plain TextColumn and the deep link is its own "OpenAlex works"
    # LinkColumn next to it, both visible in the same row.
    event = st.dataframe(
        df,
        hide_index=True,
        width="stretch",  # manager fix 2026-08-29: use_container_width deprecated in 1.61 (warning flood)
        on_select="rerun",
        selection_mode="multi-row",
        key=key,
        column_order=["rank", "institution", "institution_link", "country", "type",
                      "size_full", "size_frac", "score", "evidence", "rank_under"],
        column_config={
            "rank": st.column_config.NumberColumn("Rank"),
            "institution": st.column_config.TextColumn("Institution"),
            "institution_link": st.column_config.LinkColumn(
                "OpenAlex works", display_text="Works ->"),
            "institution_id": None,
            "country": st.column_config.TextColumn("Country"),
            "country_code": None,
            "type": st.column_config.TextColumn("Type"),
            "size_full": st.column_config.TextColumn(copy.FIND["COL_SIZE_FULL"]),
            "size_frac": st.column_config.TextColumn(copy.FIND["COL_SIZE_FRAC"]),
            "score": st.column_config.ProgressColumn(
                "Score", min_value=0, max_value=1, format="percent"),  # manager fix 2026-08-29: printf spec on a 0-1 score printed "1%"
            "evidence": st.column_config.TextColumn(copy.FIND["COL_EVIDENCE"]),
            "rank_under": st.column_config.TextColumn("Rank under"),
        },
    )
    rows_sel = event.selection.rows if event and event.selection else []
    return [df.iloc[i]["institution_id"] for i in rows_sel]


def format_concordance(rows: list[dict], *, lenses: list[str], N: int) -> pd.DataFrame:
    """Pure transform: engine `concordance(...)` rows -> the A/B #2 winner's
    k-of-n + hit-lens-chip table (VIZ_SPEC.md S2.3, S4). R1/L22: two size
    columns, country by name (code hidden)."""
    out = []
    for row in rows:
        code = str(row["country_code"])
        out.append({
            "institution": row["display_name"],
            "institution_link": _works_link(row["institution_id"]),
            "country": countries.name(code),
            "country_code": code,
            "type": str(row["type"]),
            "k": row["k"],
            "n": row["n"],
            "k_of_n": f"{row['k']} of {row['n']}",
            "hit_lenses": ", ".join(row["hit_lenses"]),
            "size_full": _fmt_size(row.get("total_full_2020_2024")),
            "size_frac": _fmt_size(row.get("total_frac_2020_2024")),
            "institution_id": row["institution_id"],
        })
    df = pd.DataFrame(out)
    df.attrs["N"] = N
    df.attrs["lenses"] = list(lenses)
    return df


def concordance_caption(n_defined: int, N: int, n_rows: int) -> str:
    """Parametric (BUILD_PLAN_2A.md L10): states N and n per VIZ_SPEC.md S1.6/S2.3."""
    # manager fix 2026-08-29 (Stream G finding): the engine's concordance returns the
    # tie-inclusive top-50 INCLUDING k=1 rows, so the caption must not assert a k floor.
    return (f"{n_rows} candidates, ranked by how many of the {n_defined} lenses defined "
            f"for this seed place them in their top-{N} (the k column).")


def render_concordance_table(df: pd.DataFrame, *, key: str):
    """`st.dataframe` per the A/B #2 winner: k-of-n + hit-lens chip text.
    Returns selected `institution_id`s, same contract as `render_ranked_table`."""
    event = st.dataframe(
        df,
        hide_index=True,
        width="stretch",  # manager fix 2026-08-29: use_container_width deprecated in 1.61 (warning flood)
        on_select="rerun",
        selection_mode="multi-row",
        key=key,
        column_order=["institution", "institution_link", "country", "type", "k_of_n",
                      "hit_lenses", "size_full", "size_frac"],
        column_config={
            "institution": st.column_config.TextColumn("Institution"),
            "institution_link": st.column_config.LinkColumn(
                "OpenAlex works", display_text="Works ->"),
            "institution_id": None,
            "k": None,
            "n": None,
            "country": st.column_config.TextColumn("Country"),
            "country_code": None,
            "type": st.column_config.TextColumn("Type"),
            "k_of_n": st.column_config.TextColumn("k of n"),
            "hit_lenses": st.column_config.TextColumn("Hit lenses", width="large"),
            "size_full": st.column_config.TextColumn(copy.FIND["COL_SIZE_FULL"]),
            "size_frac": st.column_config.TextColumn(copy.FIND["COL_SIZE_FRAC"]),
        },
    )
    rows_sel = event.selection.rows if event and event.selection else []
    return [df.iloc[i]["institution_id"] for i in rows_sel]

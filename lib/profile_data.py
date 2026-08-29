"""
app/lib/profile_data.py -- per-institution profile tables for the R1 Profile
section (BUILD_PLAN_2A.md S9.2 L17, S9.3 R-B, S9.4 interface contracts).

Pure functions, no Streamlit import: every function takes the engine's `ctx`
(+ often `subs`, one scenario's substrates) and an `institution_id`, and
returns a plain pandas DataFrame with EXACTLY the S9.4 column contract --
`lib/charts.py` (Stream R-D2) and `lib/views_find.py` (Stream R-E2) build on
these columns by name, so nothing here is free to rename or drop one.

Tree-awareness: `fields_table`/`subfields_table` read `subs["fields_df"]` /
`subs["subfields_df"]` -- the SAME scenario frames `lib/engine/substrates.py`
already computes for the L0/L1 lenses (`derive_shapes` output, or the shipped
`fields.parquet` on the default scenario) -- so `share` follows `subs["basis"]`
and `si` is the scenario's own (basis-appropriate, G6-floored at subfield
grain) column, never recomputed here. `topics_table` resolves a topic's
tree-aware subfield/field/domain from `topics_dim.parquet`'s `{tree}_subfield_id`
through the FIXED subfield->field->domain map (subfield->field never changes
per tree, `trees_agg.subfield_to_field_map`).
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from .engine.derive import _detect_year_cols
from .engine.substrates import _topic_share_values

FIELDS_COLS = ["field_id", "field_name", "domain_id", "domain_name", "vol_full", "vol_frac", "share", "si"]
SUBFIELDS_COLS = ["subfield_id", "subfield_name"] + FIELDS_COLS
TOPICS_COLS = ["topic_id", "topic_name", "subfield_id", "subfield_name", "field_id", "field_name",
              "domain_id", "domain_name", "vol_full", "vol_frac", "share", "is_excluded",
              "frontier_score_latest", "expansion_latest", "acceleration_latest", "quadrant",
              "top25pct_frontier"]
YEARLY_COLS = ["year", "domain_id", "domain_name", "vol_full", "vol_frac"]
SDG_COLS = ["sdg_idx", "sdg_number", "sdg_label", "share", "esi", "mass"]
ERC_COLS = ["panel_idx", "panel_code", "panel_label", "erc_domain", "share", "si", "mass"]


# --------------------------------------------------------- cached lookups ---

def _field_domain_map(ctx: dict) -> pd.DataFrame:
    """field_id -> field_name/domain_id/domain_name -- FIXED (tree-independent),
    26 rows, cached on ctx."""
    if "field_domain_map" not in ctx:
        td = ctx["topics_dim_df"]
        ctx["field_domain_map"] = (
            td[["field_id", "field_name", "domain_id", "domain_name"]].drop_duplicates()
        )
    return ctx["field_domain_map"]


def _subfield_field_domain_map(ctx: dict) -> pd.DataFrame:
    """subfield_id -> subfield_name/field_id/field_name/domain_id/domain_name
    -- FIXED (tree-independent, `trees_agg.subfield_to_field_map`'s own
    invariant), 252 rows, cached on ctx."""
    if "subfield_field_domain_map" not in ctx:
        td = ctx["topics_dim_df"]
        ctx["subfield_field_domain_map"] = (
            td[["subfield_id", "subfield_name", "field_id", "field_name", "domain_id", "domain_name"]]
            .drop_duplicates()
        )
    return ctx["subfield_field_domain_map"]


def _topics_dim_extra(ctx: dict) -> pd.DataFrame:
    """The columns `load_context`'s narrow `topics_dim_df` does NOT carry:
    `topic_name` and the ACCORD frontier score columns -- a second, narrow
    read of `topics_dim.parquet`, cached on ctx (S9.3 R-B: 'load lazily, cache
    on ctx')."""
    if "topics_dim_extra_df" not in ctx:
        ctx["topics_dim_extra_df"] = pd.read_parquet(
            Path(ctx["data_dir"]) / "topics_dim.parquet",
            columns=["topic_id", "topic_name", "frontier_score_latest", "expansion_latest",
                     "acceleration_latest", "quadrant"],
        )
    return ctx["topics_dim_extra_df"]


def _erc_panels(ctx: dict) -> pd.DataFrame:
    if "erc_panels_df" not in ctx:
        from .engine.evidence import RESOURCES
        ctx["erc_panels_df"] = pd.read_csv(RESOURCES / "erc_panels.csv")
    return ctx["erc_panels_df"]


def _sdg_labels(ctx: dict) -> pd.DataFrame:
    if "sdg_labels_df" not in ctx:
        from .engine.evidence import RESOURCES
        ctx["sdg_labels_df"] = pd.read_csv(RESOURCES / "sdg_labels.csv")
    return ctx["sdg_labels_df"]


def _year_cols(ctx: dict) -> list[int]:
    """Years present in `topics_all.parquet`'s schema (vol_full_<year> AND
    vol_frac_<year>), detected once and cached -- never a hardcoded year list
    (BUILD_PLAN_2A.md L10)."""
    if "topics_all_year_cols" not in ctx:
        con = duckdb.connect()
        cols = con.sql(
            f"SELECT * FROM read_parquet('{Path(ctx['topics_all_path']).as_posix()}') LIMIT 0"
        ).columns
        con.close()
        ctx["topics_all_year_cols"] = _detect_year_cols(cols)
    return ctx["topics_all_year_cols"]


# ------------------------------------------------------------ fields/subs ---

def fields_table(ctx: dict, subs: dict, iid: str) -> pd.DataFrame:
    """One row per field this institution has nonzero mass in, scenario-aware
    (`subs['fields_df']`): share on `subs['basis']`, si with NO floor at
    field grain (data_contract.yaml)."""
    share_col = "share_frac" if subs["basis"] == "frac" else "share_full"
    df = subs["fields_df"]
    row = df[df["institution_id"] == iid]
    out = row.merge(_field_domain_map(ctx), on="field_id", how="left")
    out = out.rename(columns={share_col: "share"})
    return out.reindex(columns=FIELDS_COLS).reset_index(drop=True)


def subfields_table(ctx: dict, subs: dict, iid: str) -> pd.DataFrame:
    """Same as `fields_table` at the subfield grain; si is NaN below the G6
    floor on `vol_frac` (the scenario frame already carries this)."""
    share_col = "share_frac" if subs["basis"] == "frac" else "share_full"
    df = subs["subfields_df"]
    row = df[df["institution_id"] == iid]
    fd = _subfield_field_domain_map(ctx)[["subfield_id", "subfield_name"]]
    out = row.merge(fd, on="subfield_id", how="left").merge(_field_domain_map(ctx), on="field_id", how="left")
    out = out.rename(columns={share_col: "share"})
    return out.reindex(columns=SUBFIELDS_COLS).reset_index(drop=True)


# ------------------------------------------------------------------ topics --

def topics_table(ctx: dict, subs: dict, iid: str) -> pd.DataFrame:
    """One row per topic this institution has ANY mass in (`topics_all`),
    tree-aware subfield/field/domain (`subs['tree']`'s own `{tree}_subfield_id`
    resolved through the FIXED subfield->field->domain map), share on
    `subs['basis']` (frac = `topics_all.share_frac` verbatim; full = the
    vol_full-normalised share `substrates._topic_share_values` already
    computes for L3/F1)."""
    idx = ctx["id_pos"][iid]
    mask = ctx["ta_inst"] == idx
    topic_pos = ctx["ta_topic"][mask]
    share_vals = _topic_share_values(ctx, subs["basis"])[mask]
    topic_ids = np.asarray(ctx["topic_ids"], dtype=object)[topic_pos]

    df = pd.DataFrame({
        "topic_id": topic_ids,
        "vol_full": ctx["ta_vol_full"][mask],
        "vol_frac": ctx["ta_vol_frac"][mask],
        "share": share_vals,
    })

    tree_col = f"{subs['tree']}_subfield_id"
    dim = ctx["topics_dim_df"][["topic_id", tree_col, "is_excluded", "top25pct_frontier"]].rename(
        columns={tree_col: "subfield_id"})
    dim = dim.merge(_topics_dim_extra(ctx), on="topic_id", how="left")
    out = df.merge(dim, on="topic_id", how="left")
    out = out.merge(_subfield_field_domain_map(ctx), on="subfield_id", how="left")
    return out.reindex(columns=TOPICS_COLS).reset_index(drop=True)


# ------------------------------------------------------------ yearly trend --

def yearly_by_domain(ctx: dict, iid: str, tree: str) -> pd.DataFrame:
    """(year, domain_id, domain_name, vol_full, vol_frac) via a single duckdb
    query over `topics_all.parquet`, filtered by this institution's `inst_key`
    (predicate pushdown -- warm target < 150 ms). `tree` picks which
    `{tree}_subfield_id` -> FIXED domain map resolves each topic's domain."""
    years = _year_cols(ctx)
    if not years:
        return pd.DataFrame(columns=YEARLY_COLS)

    inst_key = int(ctx["index_by_id"].loc[iid, "inst_key"])
    tree_col = f"{tree}_subfield_id"
    topic_domain = ctx["topics_dim_df"][["topic_id", tree_col]].rename(columns={tree_col: "subfield_id"})
    topic_domain = topic_domain.merge(
        _subfield_field_domain_map(ctx)[["subfield_id", "domain_id", "domain_name"]],
        on="subfield_id", how="left")[["topic_id", "domain_id", "domain_name"]]

    con = duckdb.connect()
    con.register("_topic_domain", topic_domain)
    ta_posix = Path(ctx["topics_all_path"]).as_posix()
    year_cols_sql = ", ".join(f"vol_full_{y}, vol_frac_{y}" for y in years)
    year_select = ", ".join(f"SUM(vol_full_{y}) AS vol_full_{y}, SUM(vol_frac_{y}) AS vol_frac_{y}"
                            for y in years)
    # Filter INSIDE the scanned CTE (not after the join) so duckdb's parquet
    # reader gets `inst_key = ?` as its own predicate -- row-group pruning on
    # this 533 MB file is what keeps this under the 150 ms warm budget.
    sql = f"""
        WITH ta_filtered AS (
            SELECT topic_id, {year_cols_sql}
            FROM read_parquet('{ta_posix}')
            WHERE inst_key = {inst_key}
        )
        SELECT td.domain_id, td.domain_name, {year_select}
        FROM ta_filtered ta
        JOIN _topic_domain td USING (topic_id)
        GROUP BY td.domain_id, td.domain_name
    """
    wide = con.sql(sql).df()
    con.close()

    rows = []
    for _, r in wide.iterrows():
        for y in years:
            rows.append({"year": y, "domain_id": r["domain_id"], "domain_name": r["domain_name"],
                        "vol_full": r[f"vol_full_{y}"], "vol_frac": r[f"vol_frac_{y}"]})
    out = pd.DataFrame(rows, columns=YEARLY_COLS)

    # Manager edit (R1, 2026-08-29): topics_all only holds works that carry a
    # primary topic, so Sigma over domains runs a few works short of the index's
    # own by-year totals (measured up to 0.23 %, progress/R1_B.md). The yearly
    # breakdown is SWAPPABLE with the document-type view, whose totals ARE the
    # index totals -- so the residual is carried as an explicit
    # "Unclassified" domain (id 0, Lorraine's UNCLASSIFIED_DOMAIN_ID convention)
    # and both views sum to the same number per year. Never negative: a
    # float32 rounding excess is clipped at 0.
    row = ctx["index_by_id"].loc[iid]
    tot_full = _parse_packed_years(row["vol_full_by_year_this_run"])
    tot_frac = _parse_packed_years(row["vol_frac_by_year_this_run"])
    resid = []
    for y in years:
        got_full = float(out.loc[out["year"] == y, "vol_full"].sum())
        got_frac = float(out.loc[out["year"] == y, "vol_frac"].sum())
        resid.append({"year": y, "domain_id": UNCLASSIFIED_DOMAIN_ID, "domain_name": UNCLASSIFIED_DOMAIN_NAME,
                      "vol_full": max(int(round(tot_full.get(y, got_full) - got_full)), 0),
                      "vol_frac": max(tot_frac.get(y, got_frac) - got_frac, 0.0)})
    return pd.concat([out, pd.DataFrame(resid, columns=YEARLY_COLS)], ignore_index=True)


UNCLASSIFIED_DOMAIN_ID = 0
UNCLASSIFIED_DOMAIN_NAME = "Unclassified"


def _parse_packed_years(packed) -> dict[int, float]:
    """'YEAR:value|YEAR:value|...' (index.vol_*_by_year_this_run) -> {year: value}."""
    if not isinstance(packed, str) or not packed:
        return {}
    out = {}
    for tok in packed.split("|"):
        y, v = tok.split(":")
        out[int(y)] = float(v)
    return out


# --------------------------------------------------------------- SDG / ERC --

def sdg_table(ctx: dict, iid: str) -> pd.DataFrame:
    """DENSE 16-row SDG profile (`sdg.parquet` ships all 16 per institution,
    data_contract.yaml) joined to `resources/sdg_labels.csv`."""
    row = ctx["sdg_df"][ctx["sdg_df"]["institution_id"] == iid]
    out = row.merge(_sdg_labels(ctx), on="sdg_idx", how="right")  # right join: 16 rows even if iid is thin
    out["institution_id"] = iid
    return out.reindex(columns=SDG_COLS).reset_index(drop=True)


def erc_table(ctx: dict, iid: str) -> pd.DataFrame:
    """Sparse (nonzero-mass panels only, matching `erc.parquet`'s own
    convention) ERC profile joined to `resources/erc_panels.csv`."""
    row = ctx["erc_df"][ctx["erc_df"]["institution_id"] == iid]
    out = row.merge(_erc_panels(ctx), on="panel_idx", how="left")
    return out.reindex(columns=ERC_COLS).reset_index(drop=True)


# ---------------------------------------------------------------- wordcloud -

def wordcloud_weights(ctx: dict, subs: dict, iid: str) -> tuple[dict, dict]:
    """`({subfield_name: vol on subs['basis']}, {subfield_name: domain_id})`
    over subfields with vol > 0 -- vol, not share (VIZ_SPEC wordcloud caption
    'size = works on the current basis')."""
    vol_col = "vol_frac" if subs["basis"] == "frac" else "vol_full"
    df = subs["subfields_df"]
    row = df[(df["institution_id"] == iid) & (df[vol_col] > 0)]
    fd = _subfield_field_domain_map(ctx)[["subfield_id", "subfield_name", "domain_id"]]
    row = row.merge(fd, on="subfield_id", how="left")
    weights = dict(zip(row["subfield_name"], row[vol_col].astype(float)))
    domains = dict(zip(row["subfield_name"], row["domain_id"]))
    return weights, domains

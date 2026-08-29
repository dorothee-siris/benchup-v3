"""
Shared REAL-DATA loader for the Phase 2B (stream V) A/B prototypes and the
shipped-builder render -- throwaway, `design-system/ab/**` only, never imported
by anything shipped.

It builds the BUILD_PLAN_2B.md section 4 frames (as amended by the wind tunnel's
E16) straight from the deployed parquet files. It deliberately does NOT import
`lib.compare_data` / `lib.collab_data`: stream K is writing those in parallel
and they may not exist yet. The column contract is reproduced here by hand,
exactly as section 4 declares it, so the prototypes and
`tests/test_charts_compare.py` exercise the same shapes the real functions will
return -- and if K's output ever differs, these fixtures are the statement of
what the builders were promised.

The six institutions are the ones named in the stream V brief:
  I110026055  Iscte - Instituto Universitario de Lisboa   (PT, small)
  I35440088   ETH Zurich                                  (CH, large, high impact)
  I39804081   Sorbonne Universite                         (FR, very large)
  I40413290   University of Gdansk                        (PL, mid)
  I4210127572 IMT Atlantique                              (FR, tiny, technical)
  I68947357   Universite de Strasbourg                    (FR, large)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

APP_ROOT = Path(__file__).resolve().parent.parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

DATA = APP_ROOT / "data"
RESOURCES = APP_ROOT / "lib" / "engine" / "resources"

IDS = ["I110026055", "I35440088", "I39804081",
       "I40413290", "I4210127572", "I68947357"]
TREE = "bestfit"
BASIS_COL = "share_frac"
YEARS = ("2020", "2021", "2022", "2023", "2024", "2025")
BONUS_YEAR = "2025"

SI_FLOOR_SOLID = 30.0   # lib/profile_data.py, L34 display floors
SI_FLOOR_THIN = 10.0

QUADRANTS = ("accelerating_expansion", "decelerating_expansion",
             "accelerating_contraction", "decelerating_contraction")
GREY_STATES = ("classified_eligible", "title_only", "lang_uncertain",
               "untranslated_grey", "unusable", "retracted_excluded")


def _si_status(mass) -> pd.Series:
    m = pd.to_numeric(pd.Series(mass), errors="coerce").fillna(0.0)
    return pd.Series(np.select([m >= SI_FLOOR_SOLID, m >= SI_FLOOR_THIN],
                               ["solid", "thin"], default="none"),
                     index=m.index, dtype=object)


def dim() -> pd.DataFrame:
    return pd.read_parquet(DATA / "topics_dim.parquet")


def index_rows(ids=IDS) -> pd.DataFrame:
    ix = pd.read_parquet(DATA / "index.parquet")
    return ix[ix["institution_id"].isin(ids)].reset_index(drop=True)


def slots_and_names(ids=IDS):
    from lib import palette as P
    ix = index_rows(ids)
    slots = P.institution_slots(dict(zip(ix["institution_id"], ix["inst_key"])))
    names = dict(zip(ix["institution_id"], ix["display_name"]))
    return slots, names


# --------------------------------------------------------------- mirrors ----
def fields_long(ids=IDS, tree=TREE, basis_col=BASIS_COL) -> pd.DataFrame:
    d = dim()
    fmap = d.drop_duplicates("field_id")[["field_id", "field_name", "domain_id"]]
    f = pd.read_parquet(DATA / "fields.parquet")
    f = f[f["institution_id"].isin(ids) & (f["tree"].astype(str) == tree)]
    out = f.merge(fmap, on="field_id", how="left")
    out["share"] = out[basis_col]
    out["si_status"] = np.where(out["vol_frac"].fillna(0) > 0, "solid", "none")
    return out[["institution_id", "field_id", "field_name", "domain_id",
                "vol_full", "vol_frac", "share", "si", "si_status"]].reset_index(drop=True)


def subfields_long(ids=IDS, tree=TREE, basis_col=BASIS_COL, top_n=20) -> pd.DataFrame:
    """A3: top-N by the share SUMMED ACROSS the compared set, not the
    intersection of per-institution top lists (which is 1 subfield at k = 6)."""
    d = dim()
    smap = d.drop_duplicates("subfield_id")[
        ["subfield_id", "subfield_name", "field_id", "domain_id"]]
    s = pd.read_parquet(DATA / "subfields.parquet")
    s = s[s["institution_id"].isin(ids) & (s["tree"].astype(str) == tree)]
    out = s.merge(smap, on="subfield_id", how="left", suffixes=("", "_dim"))
    out["share"] = out[basis_col]
    out["si_status"] = _si_status(out["vol_frac"]).to_numpy()
    keep = (out.groupby("subfield_id")["share"].sum()
               .sort_values(ascending=False).head(top_n).index)
    out = out[out["subfield_id"].isin(keep)]
    return out[["institution_id", "subfield_id", "subfield_name", "field_id",
                "domain_id", "vol_full", "vol_frac", "share", "si",
                "si_status"]].reset_index(drop=True)


def erc_long(ids=IDS) -> pd.DataFrame:
    panels = pd.read_csv(RESOURCES / "erc_panels.csv")
    e = pd.read_parquet(DATA / "erc.parquet")
    e = e[e["institution_id"].isin(ids)].copy()
    e["si_status"] = _si_status(e["mass"]).to_numpy()
    out = e.merge(panels, on="panel_idx", how="left")
    return out[["institution_id", "panel_idx", "panel_code", "panel_label",
                "erc_domain", "share", "si", "mass", "si_status"]].reset_index(drop=True)


def sdg_long(ids=IDS) -> pd.DataFrame:
    labels = pd.read_csv(RESOURCES / "sdg_labels.csv")
    g = pd.read_parquet(DATA / "sdg.parquet")
    g = g[g["institution_id"].isin(ids)].copy()
    g["si_status"] = _si_status(g["mass"]).to_numpy()
    out = g.merge(labels, on="sdg_idx", how="left")
    out = out.rename(columns={"esi": "si"})
    return out[["institution_id", "sdg_idx", "sdg_number", "sdg_label_numbered",
                "share", "si", "mass", "si_status"]].reset_index(drop=True)


# -------------------------------------------------------------- frontier ----
def frontier_mix(ids=IDS) -> pd.DataFrame:
    ix = index_rows(ids)
    rows = []
    for _, r in ix.iterrows():
        have = {}
        for tok in str(r["frontier_quadrant_mix"]).split("|"):
            if ":" in tok:
                k, v = tok.split(":")
                have[k] = float(v)
        for q in QUADRANTS:
            rows.append({"institution_id": r["institution_id"], "quadrant": q,
                         "share": have.get(q, 0.0),
                         "top25_share": float(r["frontier_top25_share"]),
                         "unscored_share": float(r["frontier_unscored_share"])
                         + float(r["frontier_excluded_share"])})
    return pd.DataFrame(rows)


def frontier_points(ids=IDS, tree=TREE, top_n=200) -> pd.DataFrame:
    d = dim()
    sub_col = f"{tree}_subfield_id"
    dd = d[["topic_id", "topic_name", "subfield_id", "subfield_name",
            "expansion_latest", "acceleration_latest", "quadrant",
            "top25pct_frontier", "is_excluded", sub_col]]
    t = pd.read_parquet(DATA / "topics_all.parquet",
                        columns=["institution_id", "topic_id", "vol_full", "vol_frac"],
                        filters=[("institution_id", "in", ids)])
    t = (t.sort_values("vol_full", ascending=False)
           .groupby("institution_id", sort=False).head(top_n))
    out = t.merge(dd, on="topic_id", how="left")
    return out[["institution_id", "topic_id", "topic_name", "subfield_name",
                "expansion_latest", "acceleration_latest", "vol_full", "vol_frac",
                "quadrant", "top25pct_frontier", "is_excluded"]].reset_index(drop=True)


# ---------------------------------------------------------------- impact ----
def impact_index(ids=IDS) -> pd.DataFrame:
    ix = index_rows(ids)
    out = ix.rename(columns={"pp_top10_frac": "pp", "pp_ci_low": "ci_low",
                             "pp_ci_high": "ci_high", "total_frac": "pp_denominator_frac",
                             "total_full_2020_2024": "n_works_full"})
    return out[["institution_id", "pp", "ci_low", "ci_high",
                "pp_denominator_frac", "n_works_full"]].reset_index(drop=True)


def impact_subfields(ids=IDS, tree=TREE, floor=30) -> pd.DataFrame:
    """A1: the UNION of the subfields ANY compared institution clears, with
    `in_all_ids` flagging the (rare) rows every institution holds."""
    d = dim().drop_duplicates("subfield_id")[["subfield_id", "subfield_name"]]
    c = pd.read_parquet(DATA / "impact_cells.parquet")
    c = c[c["institution_id"].isin(ids) & (c["tree"].astype(str) == tree)
          & (c["floor"] == floor)]
    out = c.merge(d, on="subfield_id", how="left")
    counts = out.groupby("subfield_id")["institution_id"].nunique()
    out["in_all_ids"] = out["subfield_id"].map(counts).eq(len(ids))
    out = out.rename(columns={"pp_top10_frac": "pp", "pp_ci_low": "ci_low",
                              "pp_ci_high": "ci_high"})
    return out[["institution_id", "subfield_id", "subfield_name", "pp", "ci_low",
                "ci_high", "n_works_full", "in_all_ids"]].reset_index(drop=True)


# ---------------------------------------------------------------- trends ----
def trends_subfields(ids=IDS, tree=TREE, subfield_ids=None) -> pd.DataFrame:
    d = dim()
    sub_col = f"{tree}_subfield_id"
    smap = d[["topic_id", sub_col]].rename(columns={sub_col: "subfield_id"})
    names = d.drop_duplicates("subfield_id")[["subfield_id", "subfield_name"]]
    cols = ["institution_id", "topic_id"] + [f"vol_{b}_{y}" for y in YEARS for b in ("full", "frac")]
    t = pd.read_parquet(DATA / "topics_all.parquet", columns=cols,
                        filters=[("institution_id", "in", ids)])
    t = t.merge(smap, on="topic_id", how="left")
    if subfield_ids is not None:
        t = t[t["subfield_id"].isin(list(subfield_ids))]
    agg = t.groupby(["institution_id", "subfield_id"], sort=False).sum(numeric_only=True).reset_index()
    rows = []
    for y in YEARS:
        part = agg[["institution_id", "subfield_id", f"vol_full_{y}", f"vol_frac_{y}"]].copy()
        part.columns = ["institution_id", "subfield_id", "vol_full", "vol_frac"]
        part["year"] = y
        rows.append(part)
    out = pd.concat(rows, ignore_index=True).merge(names, on="subfield_id", how="left")
    return out[["institution_id", "year", "subfield_id", "subfield_name",
                "vol_full", "vol_frac"]].reset_index(drop=True)


def top_shared_subfields(ids=IDS, tree=TREE, n=6) -> list[int]:
    """A3 again, for the trends grid: the N subfields with the largest SUMMED
    share across the compared set."""
    s = pd.read_parquet(DATA / "subfields.parquet")
    s = s[s["institution_id"].isin(ids) & (s["tree"].astype(str) == tree)]
    return (s.groupby("subfield_id")["share_frac"].sum()
             .sort_values(ascending=False).head(n).index.tolist())


# -------------------------------------------------------------- coverage ----
def coverage(ids=IDS) -> pd.DataFrame:
    """A9: SIX states (five grey + classified-eligible) whose `mass_*` columns
    sum to `total_frac` exactly; returned as shares of that total."""
    ix = index_rows(ids)
    rows = []
    for _, r in ix.iterrows():
        total = float(r["total_frac"]) or 1.0
        for state in GREY_STATES:
            rows.append({"institution_id": r["institution_id"], "state": state,
                         "share": float(r[f"mass_{state}"]) / total})
    return pd.DataFrame(rows)

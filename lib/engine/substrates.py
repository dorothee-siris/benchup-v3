"""
app/lib/engine/substrates.py -- population context + per-scenario substrate
matrices (Sprint 2 Phase 2A, Stream B).

Ports `evals/campaign/gen_lists_recall.py`'s `load_everything` and its
`build_*_substrate` family, plus `evals/campaign_v2/gen_lists_v2.py`'s L0
substrate and `build_catchall_811_share`. Arithmetic is copied, not rewritten;
every deviation is listed in VENDORED_engine.md. The two that matter here:

  * `topics_all` is read with FIVE columns only (`inst_key, topic_id,
    share_frac, vol_frac, vol_full`) -- BUILD_PLAN_2A.md S2 / WT #7: the full
    frame is 533 MB deep, 366 MB of it object strings. `institution_id` is
    therefore NOT available, so the L3/F1 dense matrices are filled by integer
    position (inst_key -> row, topic_id -> column) instead of
    `lens_lib.build_dense_matrix`'s `pivot_table(index="institution_id")`.
    (institution_id, topic_id) is the primary key of that table, so a pivot
    with `aggfunc="sum"` and a positional scatter produce the SAME matrix;
    uniqueness is asserted at load, not assumed. Column order is
    `sorted(topic_id)` -- byte-identical to `lens_lib.topic_matrices`' own
    `cats`.

  * `basis` is threaded through every shape-grain lens (L0/L1/C1 pick
    share_frac vs share_full; L3/F1 use share_frac vs a vol_full-normalised
    share). ERC/SDG artefacts (L4-L7) are fractional-only and carry
    `basis_applies=False`.

Population order is `index.parquet` row order (= `inst_key` ascending =
`institution_id` ascending), asserted at load (L14). Every matrix is reindexed
to it, so the stable argsort tie-break in `lenses.py` is reproducible.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import lens_lib as L
from .l2_vectors import _raw_scenario, l2_vectors
from .derive import derive_shapes
from .trees_agg import G6_FLOOR

DEFAULT_TREE = "bestfit"
DEFAULT_BASIS = "frac"
DEFAULT_SCENARIO = (DEFAULT_TREE, DEFAULT_BASIS, False)  # tree, basis, exclude_811 (R2.20)

TOPICS_ALL_COLS = ["inst_key", "topic_id", "share_frac", "vol_frac", "vol_full"]
TOPICS_DIM_COLS = ["topic_id", "subfield_id", "subfield_name", "field_id", "field_name",
                   "domain_id", "domain_name", "is_excluded", "top25pct_frontier",
                   "original_subfield_id", "conservative_subfield_id", "bestfit_subfield_id"]

# L4-L7 read ERC/SDG artefacts, which the pipeline only ever ships on the
# fractional basis -- the basis toggle does not apply to them (L5 of the plan).
BASIS_APPLIES = {"L0": True, "L1": True, "C1": True, "L3": True, "F1": True, "L2f": True,
                 "L4": False, "L5": False, "L6": False, "L7": False}


# --------------------------------------------------------------- context ----

def load_context(data_dir) -> dict:
    """Loads every table the engine needs from a deployed `app/data/` folder.
    `impact_cells` is NOT loaded here (only the aspirational/impact views need
    it -- see `load_impact_cells`)."""
    data_dir = Path(data_dir)
    index_df = pd.read_parquet(data_dir / "index.parquet")

    # ---- L14: population order = index.parquet row order = inst_key ascending
    # = institution_id ascending. Asserted, never assumed: every matrix below is
    # reindexed to this order and every tie-break is stable by that position.
    assert index_df["inst_key"].is_monotonic_increasing, \
        "index.parquet is not in ascending inst_key order (L14)"
    assert index_df["institution_id"].is_monotonic_increasing, \
        "index.parquet is not in ascending institution_id order (L14)"

    inst_ids = index_df["institution_id"].tolist()
    id_pos = {iid: i for i, iid in enumerate(inst_ids)}
    inst_keys = index_df["inst_key"].to_numpy(dtype=np.int64)
    key_pos = np.full(int(inst_keys.max()) + 1, -1, dtype=np.int32)
    key_pos[inst_keys] = np.arange(len(inst_ids), dtype=np.int32)

    topics_dim_df = pd.read_parquet(data_dir / "topics_dim.parquet", columns=TOPICS_DIM_COLS)
    erc_df = pd.read_parquet(data_dir / "erc.parquet")
    sdg_df = pd.read_parquet(data_dir / "sdg.parquet")
    fields_df = pd.read_parquet(data_dir / "fields.parquet")
    subfields_df = pd.read_parquet(data_dir / "subfields.parquet")

    # ---- topics_all: five columns, topic_id mapped to an int position once ----
    ta = pd.read_parquet(data_dir / "topics_all.parquet", columns=TOPICS_ALL_COLS)
    topic_ids = sorted(ta["topic_id"].unique().tolist())  # == lens_lib.topic_matrices' cats
    topic_pos = {t: i for i, t in enumerate(topic_ids)}
    ta_inst = key_pos[ta["inst_key"].to_numpy(dtype=np.int64)]
    ta_topic = ta["topic_id"].map(topic_pos).to_numpy(dtype=np.int32)
    ta_share = ta["share_frac"].to_numpy()
    ta_vol_frac = ta["vol_frac"].to_numpy()
    ta_vol_full = ta["vol_full"].to_numpy()
    del ta
    assert (ta_inst >= 0).all(), "topics_all carries an inst_key absent from index.parquet"
    combo = ta_inst.astype(np.int64) * len(topic_ids) + ta_topic
    assert len(np.unique(combo)) == len(combo), \
        "(institution, topic) is not unique in topics_all -- positional scatter would drop mass"
    del combo

    subfield_name_by_id, _ = L.load_subfield_codebook()
    field_name_by_id = L.load_field_name_map(topics_dim_df)

    return {
        "data_dir": data_dir,
        "topics_all_path": data_dir / "topics_all.parquet",
        "topics_dim_path": data_dir / "topics_dim.parquet",
        "index_df": index_df, "index_by_id": index_df.set_index("institution_id"),
        "inst_ids": inst_ids, "id_pos": id_pos, "n": len(inst_ids), "key_pos": key_pos,
        "erc_df": erc_df, "sdg_df": sdg_df, "fields_df": fields_df, "subfields_df": subfields_df,
        "topics_dim_df": topics_dim_df,
        "topic_ids": topic_ids, "topic_pos": topic_pos,
        "ta_inst": ta_inst, "ta_topic": ta_topic, "ta_share": ta_share,
        "ta_vol_frac": ta_vol_frac, "ta_vol_full": ta_vol_full,
        "subfield_name_by_id": subfield_name_by_id, "field_name_by_id": field_name_by_id,
    }


def load_impact_cells(ctx: dict) -> pd.DataFrame:
    """Lazy: only the per-subfield impact views need this 6 MB table."""
    if "impact_cells_df" not in ctx:
        ctx["impact_cells_df"] = pd.read_parquet(ctx["data_dir"] / "impact_cells.parquet")
    return ctx["impact_cells_df"]


# ------------------------------------------------------- dense helpers ------

def _grain_matrix(df: pd.DataFrame, tree: str, inst_ids: list, cat_col: str, share_col: str) -> dict:
    """`lens_lib.field_matrices`/`subfield_matrices`' own recipe, with the share
    column as a parameter (they hard-code share_frac): filter to the tree, take
    `sorted(unique(cat))` as the category axis, densify with
    `lens_lib.build_dense_matrix`."""
    d = df[df["tree"].astype(str) == tree]
    cats = sorted(d[cat_col].unique().tolist())
    share, _ = L.build_dense_matrix(d, inst_ids, cat_col, share_col, cats)
    return {"share": share, "cats": cats}


def _topic_matrix(ctx: dict, values: np.ndarray, keep_cols: np.ndarray | None = None) -> np.ndarray:
    """Positional equivalent of `lens_lib.build_dense_matrix` on the topic
    grain (see module docstring). `keep_cols` is a sorted array of topic
    positions to restrict to (F1's frontier subset); columns keep that sorted
    order, matching `sorted(frontier_ids)`.

    MEMORY ORDER IS LOAD-BEARING, not cosmetic: `build_dense_matrix` ends in
    `wide.to_numpy(...)` on a homogeneous DataFrame, which hands back an
    F-CONTIGUOUS array, and `np.minimum(...).sum(axis=1)` accumulates float32
    in memory order -- so a C-ordered copy of the SAME matrix returns a
    different L3 score (measured on the Gdansk/Lodz pair: 0.5925397 C-order
    vs 0.5925411 F-order, 1.4e-6 apart, i.e. outside the golden's 1e-6
    tolerance). These arrays are therefore allocated order="F"."""
    n = ctx["n"]
    rows, cols = ctx["ta_inst"], ctx["ta_topic"]
    if keep_cols is None:
        mat = np.zeros((n, len(ctx["topic_ids"])), dtype=np.float32, order="F")
        mat[rows, cols] = values
        return mat
    col_of = np.full(len(ctx["topic_ids"]), -1, dtype=np.int32)
    col_of[keep_cols] = np.arange(len(keep_cols), dtype=np.int32)
    mapped = col_of[cols]
    keep = mapped >= 0
    mat = np.zeros((n, len(keep_cols)), dtype=np.float32, order="F")
    mat[rows[keep], mapped[keep]] = values[keep]
    return mat


def _topic_share_values(ctx: dict, basis: str) -> np.ndarray:
    """Per-(institution, topic) share on the requested basis. basis='frac' is
    `topics_all.share_frac` verbatim (what the golden campaign used); basis=
    'full' is the vol_full-normalised share (BUILD_PLAN_2A.md Stream B)."""
    if basis == "frac":
        return ctx["ta_share"]
    tot = np.zeros(ctx["n"], dtype=np.float64)
    np.add.at(tot, ctx["ta_inst"], ctx["ta_vol_full"].astype(np.float64))
    denom = tot[ctx["ta_inst"]]
    with np.errstate(invalid="ignore", divide="ignore"):
        v = np.divide(ctx["ta_vol_full"].astype(np.float64), denom,
                      out=np.zeros(len(denom), dtype=np.float64), where=denom > 0)
    return v.astype(np.float32)


# ---------------------------------------------------------- substrates -----

def build_substrates(ctx: dict, tree: str = DEFAULT_TREE, basis: str = DEFAULT_BASIS) -> dict:
    """All ten lens substrates for one (tree, basis) scenario.

    L1/C1 always come from `derive_shapes` -- the SAME call
    `gen_lists_recall.build_l1_c1_substrate` makes -- and NOT from the shipped
    `subfields.parquet`: the two agree only to float32 (measured: 130,420 of
    770,871 share_frac cells differ, max 6e-8), which is inside the Tier-A
    identity tolerance but can move a tie at a top-50 cut. L0 on the DEFAULT
    scenario comes from the shipped `fields.parquet`, because that is what
    `gen_lists_v2.py` used and what the golden lists pin; any other scenario
    uses the `fields` frame that same `derive_shapes` call returns.
    """
    inst_ids = ctx["inst_ids"]
    is_default = (tree, basis) == (DEFAULT_TREE, DEFAULT_BASIS)
    share_col = "share_frac" if basis == "frac" else "share_full"

    derived_sub, derived_fld = derive_shapes(
        ctx["topics_all_path"], ctx["topics_dim_path"], tree=tree, basis=basis,
        exclude_811=False, index_institution_ids=None, g6_floor=G6_FLOOR,
    )

    subs = {"tree": tree, "basis": basis, "basis_applies": dict(BASIS_APPLIES)}

    # L0 -- field grain (26 fields; gen_lists_v2 deviation note 1: not 19)
    fields_df_scenario = ctx["fields_df"] if is_default else derived_fld
    subs["l0"] = _grain_matrix(fields_df_scenario, tree, inst_ids, "field_id",
                               "share_frac" if is_default else share_col)

    # L1 / C1 -- subfield grain
    subs["l1"] = _grain_matrix(derived_sub, tree, inst_ids, "subfield_id", share_col)

    # profile_data (R1 L17): the scenario's OWN fields/subfields frames, tree-
    # filtered, kept for `si` and per-institution profile tables -- exactly
    # the frame the L0/L1 lenses above just read (BUILD_PLAN_2A.md S9.3 R-B).
    subs["fields_df"] = fields_df_scenario[fields_df_scenario["tree"].astype(str) == tree]
    subs["subfields_df"] = derived_sub[derived_sub["tree"].astype(str) == tree]

    # L3 -- topic grain
    topic_vals = _topic_share_values(ctx, basis)
    subs["l3"] = {"share": _topic_matrix(ctx, topic_vals), "cats": ctx["topic_ids"]}

    # F1 -- frontier topics only (gen_lists_recall.build_f1_substrate)
    td = ctx["topics_dim_df"]
    frontier_ids = set(td.loc[td["top25pct_frontier"] == True, "topic_id"])  # noqa: E712
    excluded_ids = set(td.loc[td["is_excluded"] == True, "topic_id"])  # noqa: E712
    f1_cats = sorted(frontier_ids)
    keep_cols = np.array([ctx["topic_pos"][t] for t in f1_cats], dtype=np.int32)
    subs["f1"] = {"share": _topic_matrix(ctx, topic_vals, keep_cols), "cats": f1_cats,
                  "n_frontier_topics": len(frontier_ids),
                  "excluded_and_frontier_topic_ids": sorted(frontier_ids & excluded_ids)}
    del topic_vals

    # L2f -- L2 continuous form, candidate (f): papers >= 30
    # (gen_lists_recall.build_l2f_substrate, verbatim)
    df = l2_vectors(ctx["topics_all_path"], ctx["topics_dim_path"], tree=tree, basis=basis,
                        exclude_811=False, variant="f", params={})
    cats = sorted(df["subfield_id"].unique().tolist())
    eligible_f, _ = L.build_dense_matrix(df.assign(_e=df["eligible"].astype(float)), inst_ids,
                                         "subfield_id", "_e", cats)
    si_wide = df.pivot_table(index="institution_id", columns="subfield_id", values="si",
                             aggfunc="mean").reindex(index=inst_ids, columns=cats)
    si_mat = si_wide.to_numpy(dtype=np.float64)
    eligible_b = eligible_f > 0.5
    excess_raw = np.where(eligible_b, np.maximum(np.nan_to_num(si_mat, nan=0.0) - 1.0, 0.0), 0.0)
    row_sum = excess_raw.sum(axis=1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        excess = np.divide(excess_raw, row_sum, out=np.zeros_like(excess_raw), where=row_sum > 0)
    subs["l2f"] = {"excess": excess.astype(np.float32), "eligible": eligible_b, "cats": cats}
    del df, si_wide, si_mat, excess_raw, excess
    _raw_scenario.cache_clear()  # frees the unfloored derive_shapes frame (~130 MB)

    # L4 / L5 -- ERC panels (fractional-only artefact)
    erc_mats = L.erc_matrices(ctx["erc_df"], inst_ids)
    subs["l4"] = {"share": erc_mats["share_frac"], "cats": erc_mats["cats"]}
    subs["l5"] = {"excess": L.excess_profile_matrix(erc_mats["si"]), "si": erc_mats["si"],
                  "cats": erc_mats["cats"]}

    # L6 / L7 -- SDGs (fractional-only artefact; `share` is MULTI-LABEL)
    sdg_mats = L.sdg_matrices(ctx["sdg_df"], inst_ids)
    raw_share = sdg_mats["share_frac"]
    row_sum = raw_share.sum(axis=1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        profile = np.divide(raw_share, row_sum, out=np.zeros_like(raw_share, dtype=np.float64),
                            where=row_sum > 0)
    subs["l6"] = {"profile": profile.astype(np.float32), "raw_share": raw_share,
                  "cats": sdg_mats["cats"]}
    subs["l7"] = {"excess": L.excess_profile_matrix(sdg_mats["si"]), "esi": sdg_mats["si"],
                  "cats": sdg_mats["cats"]}

    return subs

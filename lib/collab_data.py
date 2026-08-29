"""
app/lib/collab_data.py -- Collaborate-view data frames for exactly ONE pair
of institutions, A -> B directional (BenchUp v3 Sprint 2 Phase 2B, Stream K;
BUILD_PLAN_2B.md S2B-7).

Pure functions, no Streamlit import. `shared_topics`/`gaps`/`breadth_jaccard`
all read `subs["l3"]["share"]` (BUILD_PLAN_2A.md's topic-grain substrate,
tree-invariant since topics are the base grain the tree never re-buckets) --
the SAME matrix `lib/engine/lenses.py`'s L3 lens scores overlap on, so
`shared_topics`' Sigma(min_share) equals the engine's own L3 score for the
pair on `subs`'s basis, exactly (no further division for L3 --
`lib/engine/evidence.py`'s LENS_MATRIX branch).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import profile_data as P

SHARED_TOPICS_COLS = ["topic_id", "topic_name", "subfield_name", "share_a", "share_b",
                      "min_share", "keywords", "top25pct_frontier"]
GAPS_COLS = ["topic_id", "topic_name", "subfield_name", "share_b", "top25pct_frontier"]
TOP10_N = 10  # 2B-7 / evals/aspirational_R2/gen.py::build_complement's own top-10-subfields anchor


def _topic_keywords_map(ctx: dict) -> dict:
    """Lazy, cached on ctx (same idiom as `profile_data._topics_dim_extra`):
    `topics_dim.parquet`'s `keywords` column (`|`-joined, 0 nulls/empties of
    4,516, Wind Tunnel 2B #9) is NOT part of the narrow `TOPICS_DIM_COLS`
    `load_context` keeps."""
    if "topic_keywords_by_id" not in ctx:
        df = pd.read_parquet(Path(ctx["data_dir"]) / "topics_dim.parquet",
                             columns=["topic_id", "keywords"])
        ctx["topic_keywords_by_id"] = dict(zip(df["topic_id"], df["keywords"]))
    return ctx["topic_keywords_by_id"]


def _topic_subfield_map(ctx: dict, tree: str) -> pd.DataFrame:
    """topic_id -> subfield_id under the given tree (`{tree}_subfield_id`,
    already carried on `ctx['topics_dim_df']` -- BUILD_PLAN_2A.md's fixed
    subfield->field->domain nesting means the NAME lookup for that id is
    tree-independent, `profile_data._subfield_field_domain_map`)."""
    tree_col = f"{tree}_subfield_id"
    return ctx["topics_dim_df"][["topic_id", tree_col]].rename(columns={tree_col: "subfield_id"})


def _top10_subfield_ids(subs: dict, idx: int) -> set:
    """The institution's own top-10 subfields by L1 share (nonzero only),
    same recipe as `evals/aspirational_R2/gen.py::build_complement`'s
    `top10_subfield_ids` (argsort desc on `subs['l1']['share']`)."""
    l1_cats = subs["l1"]["cats"]
    l1_row = subs["l1"]["share"][idx]
    order = np.argsort(-l1_row, kind="stable")
    return {l1_cats[i] for i in order[:TOP10_N] if l1_row[i] > 0}


def _label_topics(ctx: dict, tree: str, df: pd.DataFrame) -> pd.DataFrame:
    """Common topic_id -> (subfield_name, topic_name, top25pct_frontier)
    join used by both `shared_topics` and `gaps`."""
    dim = ctx["topics_dim_df"][["topic_id", "top25pct_frontier"]].merge(
        _topic_subfield_map(ctx, tree), on="topic_id", how="left")
    out = df.merge(dim, on="topic_id", how="left")
    out = out.merge(P._subfield_field_domain_map(ctx)[["subfield_id", "subfield_name"]],
                    on="subfield_id", how="left")
    out = out.merge(P._topics_dim_extra(ctx)[["topic_id", "topic_name"]], on="topic_id", how="left")
    return out


def shared_topics(ctx: dict, subs: dict, a: str, b: str) -> pd.DataFrame:
    """Topics BOTH institutions hold any mass in (`min_share > 0`) -- the
    exact cells the engine's own L3 lens sums over: Sigma(min_share) here ==
    the L3 histogram-intersection score for the pair on `subs`'s basis,
    tree-invariant (L3 is topic-grain, WT-2B #10)."""
    a_idx, b_idx = ctx["id_pos"][a], ctx["id_pos"][b]
    l3 = subs["l3"]
    share_a = l3["share"][a_idx].astype("float64")
    share_b = l3["share"][b_idx].astype("float64")
    cats = np.asarray(l3["cats"], dtype=object)
    mins = np.minimum(share_a, share_b)
    mask = mins > 0

    df = pd.DataFrame({"topic_id": cats[mask], "share_a": share_a[mask],
                       "share_b": share_b[mask], "min_share": mins[mask]})
    df = _label_topics(ctx, subs["tree"], df)
    df["keywords"] = df["topic_id"].map(_topic_keywords_map(ctx))
    return df.sort_values("min_share", ascending=False).reset_index(drop=True).reindex(
        columns=SHARED_TOPICS_COLS)


def gaps(ctx: dict, subs: dict, a: str, b: str) -> pd.DataFrame:
    """B's topics inside A's top-10 subfields (by A's own L1 share) that A
    itself lacks (`share_a == 0` on the L3 matrix) -- the complementarity
    formula from `evals/aspirational_R2/gen.py::build_complement`, reused
    for one named pair instead of a full-population scan. The symmetric call
    is `gaps(ctx, subs, b, a)`."""
    a_idx, b_idx = ctx["id_pos"][a], ctx["id_pos"][b]
    top10 = _top10_subfield_ids(subs, a_idx)
    if not top10:
        return pd.DataFrame(columns=GAPS_COLS)

    l3 = subs["l3"]
    share_a = l3["share"][a_idx].astype("float64")
    share_b = l3["share"][b_idx].astype("float64")
    cats = np.asarray(l3["cats"], dtype=object)
    mask = (share_b > 0) & (share_a == 0)

    df = pd.DataFrame({"topic_id": cats[mask], "share_b": share_b[mask]})
    df = df.merge(_topic_subfield_map(ctx, subs["tree"]), on="topic_id", how="left")
    df = df[df["subfield_id"].isin(top10)]
    df = _label_topics(ctx, subs["tree"], df.drop(columns=["subfield_id"]))
    return df.sort_values("share_b", ascending=False).reset_index(drop=True).reindex(columns=GAPS_COLS)


def _topic_membership(ctx: dict, subs: dict, idx: int, min_full: int) -> "np.ndarray":
    """Boolean over the topic axis: the institution 'is present' in a topic.
    min_full <= 0 -> any nonzero share (K's original rule); min_full >= 1 ->
    at least `min_full` FULL-counted publications on the topic (manager fix
    2026-08-29 after WT-2B E5: a topic touched by a single co-authored paper
    is not breadth -- the Collaborate page passes 2 and says so)."""
    if min_full <= 0:
        return subs["l3"]["share"][idx] > 0
    mask = ctx["ta_inst"] == idx
    cols = ctx["ta_topic"][mask][ctx["ta_vol_full"][mask] >= min_full]
    out = np.zeros(len(ctx["topic_ids"]), dtype=bool)
    out[cols] = True
    return out


def breadth_jaccard(ctx: dict, subs: dict, a: str, b: str, min_full: int = 0) -> dict:
    """Unweighted Jaccard over topics with nonzero share on `subs`'s basis --
    deliberately answers a DIFFERENT question from `shared_topics` (topic
    FOOTPRINT overlap, not mass-weighted overlap). No extra floor: BUILD_
    PLAN_2B.md S0 "confirmed unchanged" -- topics_all carries no dust rows
    that would need one for this purpose."""
    a_idx, b_idx = ctx["id_pos"][a], ctx["id_pos"][b]
    l3 = subs["l3"]["share"]
    set_a = _topic_membership(ctx, subs, a_idx, min_full)
    set_b = _topic_membership(ctx, subs, b_idx, min_full)
    n_a, n_b = int(set_a.sum()), int(set_b.sum())
    n_shared = int((set_a & set_b).sum())
    union = n_a + n_b - n_shared
    jaccard = (n_shared / union) if union > 0 else 0.0
    return {"jaccard": jaccard, "n_a": n_a, "n_b": n_b, "n_shared": n_shared}

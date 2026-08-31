"""
app/lib/collab_data.py -- Collaborate-view data frames for exactly ONE pair
of institutions, A -> B directional (BenchUp v3 Sprint 2 Phase 2B, Stream K;
BUILD_PLAN_2B.md S2B-7).

Pure functions, no Streamlit import. `shared_topics`/`breadth_jaccard` both
read `subs["l3"]["share"]` (BUILD_PLAN_2A.md's topic-grain substrate,
tree-invariant since topics are the base grain the tree never re-buckets) --
the SAME matrix `lib/engine/lenses.py`'s L3 lens scores overlap on, so
`shared_topics`' Sigma(min_share) equals the engine's own L3 score for the
pair on `subs`'s basis, exactly (no further division for L3 --
`lib/engine/evidence.py`'s LENS_MATRIX branch).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import compare_data as CD
from . import links
from . import palette as PAL
from . import profile_data as P

SHARED_TOPICS_COLS = ["topic_id", "topic_name", "subfield_name", "share_a", "share_b",
                      "min_share", "keywords", "top25pct_frontier"]
# 2B-R2-11(f): the OLD `gaps()`/`GAPS_COLS` "what B publishes that A doesn't"
# table is DELETED this round (its own loader was `_top10_subfield_ids` below,
# also removed) -- `untapped()` further down is the ruled replacement: not a
# footprint gap, an EXPECTED-vs-OBSERVED joint-output gap.


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


def _label_topics(ctx: dict, tree: str, df: pd.DataFrame) -> pd.DataFrame:
    """Common topic_id -> (subfield_name, topic_name, top25pct_frontier)
    join used by `shared_topics` and `untapped`."""
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


# ============================================================================
# 2B-R additions (Stream CD, BUILD_PLAN_2BR.md S1 2B-R-10, S4) -- the four
# Collaborate v2 sections over ONE pair (a, b), from the NEW `collab_pairs.
# parquet`/`collab_pair_topics.parquet` pair artefacts (2B-R-15/A1/A2). Both
# tables key on (a, b) with `a` the LEXICOGRAPHICALLY SMALLER institution_id
# (the table's OWN convention) -- every function below accepts (a, b) in the
# CALLER's own order and re-orients whatever it reads back, so a caller never
# has to know or care which of its two ids happens to sort first.
# ============================================================================

def _load_collab_pairs(ctx: dict) -> pd.DataFrame:
    """Lazy, ctx-cached (`collab_pairs.parquet` v2, BUILD_PLAN_2BR3.md SS2.2):
    ALL a<b indexed-institution pairs with >=1 co-published work 2020-2025
    (floor 1 -- WT A1 refutes a floor here), `copubs_2020..copubs_2025`
    (all-types, pulse's own window, naming kept per WT_2BR3.md SS0 -- NOT a
    typo), `core_total`/`c1`/`c2` (CORE-AR, articles+reviews 2020-2024),
    `n_top10`/`n_covered`/`n_sdg`/`fwci_median` (CORE-AR), `rank_in_a`/
    `rank_in_b` (recomputed on CORE-AR, ranks computed before any floor),
    `mom_class`/`mom_rr`/`mom_p` (SS2.3, pipeline-classified), plus
    `erc_top_panel`/`erc_top_panel_n`/`erc_labelled_n` carried forward on
    their CURRENT basis (WT_2BR3.md SS0 gap g: moved here from
    collab_pair_topics v1, the pair-level ERC header now has a schema home)."""
    if "collab_pairs_df" not in ctx:
        ctx["collab_pairs_df"] = pd.read_parquet(Path(ctx["data_dir"]) / "collab_pairs.parquet")
    return ctx["collab_pairs_df"]


def _load_collab_pair_topics(ctx: dict) -> pd.DataFrame:
    """Lazy, ctx-cached (`collab_pair_topics.parquet` v2): top-
    `PAIR_TOPICS_TOP_N` joint topics (PRIMARY bestfit topic only) per pair
    with `core_total >= PAIR_TOPICS_FLOOR`, CORE-AR `vol`/`vol_w1`/`vol_w2`,
    `n_top10`/`n_covered`/`n_sdg`/`fwci_median`/`mom_class`. `erc_top_panel`/
    etc. are GONE from this table since v2 -- see `_load_collab_pairs`."""
    if "collab_pair_topics_df" not in ctx:
        ctx["collab_pair_topics_df"] = pd.read_parquet(Path(ctx["data_dir"]) / "collab_pair_topics.parquet")
    return ctx["collab_pair_topics_df"]


def _load_collab_topic_vols(ctx: dict) -> pd.DataFrame:
    """Lazy, ctx-cached (`collab_topic_vols.parquet` NEW, SS2.2): (a, b,
    topic_id, vol) UNCAPPED per qualifying pair, CORE-AR -- the item-4 fix
    for `untapped()`'s `joint_observed` (was reading the top-100-CAPPED
    `collab_pair_topics`, silently zeroing out any shared topic outside the
    cap, WT_2BR3.md task 5.7 / SS0 task 6 #11)."""
    if "collab_topic_vols_df" not in ctx:
        ctx["collab_topic_vols_df"] = pd.read_parquet(Path(ctx["data_dir"]) / "collab_topic_vols.parquet")
    return ctx["collab_topic_vols_df"]


def _load_collab_facts(ctx: dict) -> dict:
    """Lazy, ctx-cached (`collab_facts.json` NEW, SS2.2): the momentum
    constants (med/w1/w2/band/alpha/elig_min/weak_base_max/new_min_c2/
    dormant_min_c1/basis) `momentum_display` may need for its message text."""
    if "collab_facts" not in ctx:
        with open(Path(ctx["data_dir"]) / "collab_facts.json") as f:
            ctx["collab_facts"] = json.load(f)
    return ctx["collab_facts"]


PULSE_YEARS = list(range(2020, 2026))  # collab_pairs' own window (2020-2025 incl. the 2025 bonus year)
PULSE_YEARLY_COLS = ["year", "copubs"]


def _num(v) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return float("nan")
    return f


ARROW_UP, ARROW_DOWN, ARROW_FLAT = "up", "down", "flat"
ARROW_DEADBAND = 0.5
# 2B-R2-11(d): per-row direction arrows compare the MEAN ANNUAL volume of
# window 1 (2020-2022, /3) against window 2 (2023-2024, /2) -- never the raw
# window sums, which cover different numbers of years and are not
# comparable as-is. A change smaller than this deadband (half a joint
# publication per year) reads "flat" rather than flipping direction on
# noise -- the windows themselves are named in the caller's tooltip, not
# here (this module returns the arrow only, never composes the sentence).


def _arrow(vol_w1, vol_w2) -> str:
    w1_annual, w2_annual = _num(vol_w1) / 3.0, _num(vol_w2) / 2.0
    if not (np.isfinite(w1_annual) and np.isfinite(w2_annual)):
        return ARROW_FLAT
    delta = w2_annual - w1_annual
    if abs(delta) < ARROW_DEADBAND:
        return ARROW_FLAT
    return ARROW_UP if delta > 0 else ARROW_DOWN


def _taxon_url(a: str, b: str, level: str, taxon_id) -> str:
    return links.copubs_taxon_url(a, b, level, taxon_id)


def pulse(ctx: dict, a: str, b: str) -> dict | None:
    """2B-R-10 S1 (Relationship pulse). Reads ONE row of `collab_pairs.
    parquet` (regardless of the table's own a<b ordering) and returns it in
    the CALLER's (a, b) orientation:

      yearly            -- DataFrame[year, copubs], 2020-2025 (2025 labelled
                            the bonus year by the caller/page, same
                            convention as topics_all/doctype_by_year).
      copubs_total       -- SUM over 2020-2025, full counting.
      share_of_a/b       -- copubs_total / that side's own total FULL-counted
                            works over the SAME 2020-2025 window (index.
                            vol_full_by_year_this_run summed over all 6
                            years) -- NOT total_full_2020_2024's 5-year core
                            window; see `denominator_note`.
      rank_in_a          -- dense rank (1=highest) of `b` among ALL of `a`'s
                            partners by copubs_total, computed BEFORE any
                            floor (2B-R-15) -- re-oriented from the table's
                            own rank_in_a/rank_in_b when the caller's (a, b)
                            is the table's (b, a).
      rank_in_b          -- dense rank of `a` among ALL of `b`'s partners.

    Returns `None` when the pair has never co-published at all (absent from
    `collab_pairs`, which ships floor 1 -- absent truly means zero, 2BR A1).
    Pinned anchor: `pulse(ctx, "I1294671590", "I68947357")` (CNRS, Strasbourg
    -- the table's own a<b order) -> copubs_total 12694, rank_in_a 16,
    rank_in_b 1 (manager-verified fact, BUILD_PLAN_2BR.md CD brief)."""
    pairs = _load_collab_pairs(ctx)
    lo, hi = (a, b) if a < b else (b, a)
    row = pairs[(pairs["a"] == lo) & (pairs["b"] == hi)]
    if row.empty:
        return None
    row = row.iloc[0]
    swapped = a != lo  # caller's `a` is the table's `b`

    yearly = pd.DataFrame({"year": PULSE_YEARS, "copubs": [int(row[f"copubs_{y}"]) for y in PULSE_YEARS]},
                          columns=PULSE_YEARLY_COLS)
    rank_in_a = int(row["rank_in_b"] if swapped else row["rank_in_a"])
    rank_in_b = int(row["rank_in_a"] if swapped else row["rank_in_b"])

    idx = ctx["index_by_id"]
    denom_a = sum(P._parse_packed_years(idx.loc[a, "vol_full_by_year_this_run"]).get(y, 0.0) for y in PULSE_YEARS)
    denom_b = sum(P._parse_packed_years(idx.loc[b, "vol_full_by_year_this_run"]).get(y, 0.0) for y in PULSE_YEARS)
    total = int(row["copubs_total"])

    return {
        "a": a, "b": b, "yearly": yearly, "copubs_total": total,
        "share_of_a": (total / denom_a) if denom_a > 0 else np.nan,
        "share_of_b": (total / denom_b) if denom_b > 0 else np.nan,
        "denominator_a": denom_a, "denominator_b": denom_b,
        "denominator_note": ("Each side's share of co-publications is out of its OWN total full-counted "
                             "publications, 2020-2025 (the same 6-year window as the co-publication count "
                             "itself) -- not the shorter 2020-2024 window used for some other Compare figures."),
        "rank_in_a": rank_in_a, "rank_in_b": rank_in_b,
    }


PAIR_TOPICS_FLOOR = 5    # 2B-R2-12: collab_pair_topics/collab_pair_fields ship only for pairs with copubs_total >= this
PAIR_TOPICS_TOP_N = 100  # 2B-R2-12: top-100 joint topics per pair by vol_total (slider-ready, up to this cap)

# 2BR3 CD4 item 3 (WT_2BR3.md SS0 fence correction (c)/(d) -- the stale-
# constant trap named explicitly in this plan's CD4 acceptance): `vol_total`
# -> `vol` (CORE-AR, no `vol_2025` component -- DROPPED, not renamed) and
# `sdg_tagged_n` -> `n_sdg`. `fwci_median`/`mom_class` ride on the per-topic
# row (collab_pair_topics v2 carries them natively) but are NOT summable, so
# they are in JOINT_TOPICS_COLS (per-row) but deliberately absent from
# JOINT_ROLLUP_VALUE_COLS (the groupby().sum() rollup to field/subfield
# grain inside `joint_profile` below) -- `field_breakdown()`'s own table is
# the authoritative source for a field's real fwci_median/mom_class.
JOINT_TOPICS_COLS = ["topic_id", "topic_name", "subfield_id", "subfield_name", "field_id", "field_name",
                     "domain_id", "domain_name", "vol_w1", "vol_w2", "vol",
                     "n_covered", "n_top10", "n_sdg", "fwci_median", "mom_class", "arrow", "url"]
JOINT_ROLLUP_VALUE_COLS = ["vol_w1", "vol_w2", "vol", "n_covered", "n_top10", "n_sdg"]
# n_top10/n_covered/n_sdg are ADDITIVE counts -- summing them over a
# rollup's shown topics is exact for THOSE topics, same lower-bound caveat
# as every other rollup column here (see `meta.note`).

MEAN_CITATIONS_NOTE = (
    "Mean citations is shown at field level only (see the field breakdown) -- the topic-level "
    "table does not carry it, to keep its file size within budget."
)


def joint_profile(ctx: dict, subs: dict, a: str, b: str) -> dict | None:
    """Joint corpus, on the top-100/floor-5 `collab_pair_topics.parquet` v2
    (CORE-AR, SS2.1). Field/subfield/domain names are resolved TREE-AWARE
    (`subs['tree']`'s own `{tree}_subfield_id`) even though `topic_id` itself
    never changes -- only which subfield a topic rolls into does.

    Returns `None` when the pair's `core_total` is below `PAIR_TOPICS_FLOOR`
    (or the pair never co-published) -- both `PAIR_TOPICS_FLOOR` and
    `PAIR_TOPICS_TOP_N` are public module constants so a caller can render
    'below the floor of {F}' without a second lookup.

    On a hit, returns:
      topics       -- one row per joint topic (<= PAIR_TOPICS_TOP_N rows,
                      slider-ready -- a caller may `.head(n)` for n <=
                      PAIR_TOPICS_TOP_N), sorted by `vol` (CORE-AR) descending,
                      each with an `n_top10`/`n_covered` impact pair ("x of
                      y covered joint works in the world top decile" --
                      NEVER divide n_top10 by vol, only by n_covered), a
                      w1-vs-w2 `arrow` (`_arrow`, deadband documented there),
                      per-topic `fwci_median`/`mom_class` and a live OpenAlex
                      `url` restricted to this topic. `mean_citations` is NOT
                      a column here -- `meta.mean_citations_note` says why.
      fields       -- topics rolled up to field grain (sum of the additive
                      window/impact/sdg columns over the SHOWN topics only --
                      see `meta.note`; for the AUTHORITATIVE, uncapped field
                      numbers with `mean_citations`-superseding `fwci_median`,
                      use `field_breakdown`).
      subfields    -- topics rolled up to subfield grain, same caveat.
      sdg_tagged_total -- sum of n_sdg over the shown topics (a LOWER BOUND
                      on the pair's true joint SDG-tagged count, because of
                      the top-N cap).
      erc          -- PAIR-LEVEL dict (erc_top_panel/panel_n/labelled_n),
                      now read from `collab_pairs.parquet` v2 (WT_2BR3.md
                      SS0 gap g -- this info moved off collab_pair_topics,
                      which carries no erc_* columns since v2); `None` when
                      the pair has no collab_pairs row at all (should not
                      happen once `rows` above is non-empty, defensive only).
                      `denominator_note` states the labelled-work convention:
                      NEVER divide panel_n by copubs_total, only by
                      labelled_n.
      meta         -- {floor, top_n_cap, n_topics_shown, note, mean_citations_note}."""
    topics = _load_collab_pair_topics(ctx)
    lo, hi = (a, b) if a < b else (b, a)
    rows = topics[(topics["a"] == lo) & (topics["b"] == hi)]
    if rows.empty:
        return None

    tree_col = f"{subs['tree']}_subfield_id"
    dim = ctx["topics_dim_df"][["topic_id", tree_col]].rename(columns={tree_col: "subfield_id"})
    sfd = P._subfield_field_domain_map(ctx)
    extra = P._topics_dim_extra(ctx)[["topic_id", "topic_name"]]

    df = rows.merge(dim, on="topic_id", how="left").merge(sfd, on="subfield_id", how="left") \
             .merge(extra, on="topic_id", how="left")
    df = df.sort_values("vol", ascending=False).reset_index(drop=True)
    df["arrow"] = [_arrow(w1, w2) for w1, w2 in zip(df["vol_w1"], df["vol_w2"])]
    df["url"] = [_taxon_url(a, b, "topic", t) for t in df["topic_id"]]
    topics_out = df.reindex(columns=JOINT_TOPICS_COLS)

    fields_out = (df.groupby(["field_id", "field_name"], as_index=False)[JOINT_ROLLUP_VALUE_COLS].sum()
                    .sort_values("vol", ascending=False).reset_index(drop=True))
    subfields_out = (df.groupby(["subfield_id", "subfield_name", "field_id", "field_name"], as_index=False)
                       [JOINT_ROLLUP_VALUE_COLS].sum()
                       .sort_values("vol", ascending=False).reset_index(drop=True))

    pairs = _load_collab_pairs(ctx)
    prow = pairs[(pairs["a"] == lo) & (pairs["b"] == hi)]
    erc = None
    if len(prow):
        p0 = prow.iloc[0]
        erc = {
            "panel_idx": p0["erc_top_panel"], "panel_n": int(p0["erc_top_panel_n"]),
            "labelled_n": int(p0["erc_labelled_n"]),
            "denominator_note": ("Of the labelled share of joint works with an ERC-panel prediction "
                                 "(panel_n / labelled_n) -- never divide by the total co-publication count."),
        }
    return {
        "a": a, "b": b, "topics": topics_out, "fields": fields_out, "subfields": subfields_out,
        "sdg_tagged_total": int(df["n_sdg"].sum()), "erc": erc,
        "meta": {"floor": PAIR_TOPICS_FLOOR, "top_n_cap": PAIR_TOPICS_TOP_N, "n_topics_shown": len(topics_out),
                "note": (f"The top {PAIR_TOPICS_TOP_N} joint topics by volume are shown -- the pair's true "
                        "topic diversity may exceed this cap; sdg_tagged_total and the field/subfield "
                        "rollups sum ONLY the shown topics, a lower bound."),
                "mean_citations_note": MEAN_CITATIONS_NOTE},
    }


FIELD_BREAKDOWN_COLS = ["field_id", "field_name", "domain_id", "domain_name", "vol_w1", "vol_w2",
                        "vol", "n_covered", "n_top10", "n_sdg", "fwci_median", "mom_class", "arrow", "url"]
FIELD_BREAKDOWN_NOTE = (
    "Field mix uses the repaired (best-fit) taxonomy only and does not change with the tree toggle."
)


def _load_collab_pair_fields(ctx: dict) -> pd.DataFrame:
    """Lazy, ctx-cached: `collab_pair_fields.parquet` v2 -- pair x field,
    UNCAPPED (every field the pair has any joint mass in), bestfit tree
    only, same a<b/floor-5 qualifying-pair convention as
    `collab_pair_topics`. The ONE source `field_breakdown` reads; unlike
    `joint_profile`'s own field rollup (a lower bound over its top-100
    topics), this table is the AUTHORITATIVE per-field total. `mean_citations`
    is GONE (SS2.2: "DROPPED, superseded by FWCI") -- `fwci_median` is the
    only per-field impact figure now."""
    if "collab_pair_fields_df" not in ctx:
        ctx["collab_pair_fields_df"] = pd.read_parquet(Path(ctx["data_dir"]) / "collab_pair_fields.parquet")
    return ctx["collab_pair_fields_df"]


def field_breakdown(ctx: dict, a: str, b: str) -> pd.DataFrame:
    """The field breakdown of the joint corpus -- one row per field the pair
    has any joint CORE-AR mass in, from `collab_pair_fields.parquet` v2
    (UNCAPPED, bestfit-tree-only -- `.attrs['note']` carries that caveat for
    the caller's caption, and `.attrs['floor']` the qualifying-pair floor).
    Sorted by `vol` (CORE-AR) descending; empty (with the right columns) when
    the pair never co-published or falls below `PAIR_TOPICS_FLOOR`. Each row
    carries `fwci_median`/`mom_class`, an `arrow` (`_arrow`) and a live
    OpenAlex `url` restricted to this field. The DATA function survives 2BR3
    unchanged in shape (only its column contract moves) -- only the TABLE
    RENDERER that used to sit on top of it is retired (WT_2BR3.md SS0
    ratification, CD4 acceptance: 'field_breakdown() the DATA function
    SURVIVES... only VL's table renderer dies')."""
    fields = _load_collab_pair_fields(ctx)
    lo, hi = (a, b) if a < b else (b, a)
    rows = fields[(fields["a"] == lo) & (fields["b"] == hi)]
    name_map = P._field_domain_map(ctx)[["field_id", "field_name", "domain_id", "domain_name"]]
    out = rows.merge(name_map, on="field_id", how="left")
    if len(out):
        out["arrow"] = [_arrow(w1, w2) for w1, w2 in zip(out["vol_w1"], out["vol_w2"])]
        out["url"] = [_taxon_url(a, b, "field", int(fid)) for fid in out["field_id"]]
    else:
        out["arrow"], out["url"] = pd.Series(dtype=object), pd.Series(dtype=object)
    out = out.sort_values("vol", ascending=False).reset_index(drop=True).reindex(columns=FIELD_BREAKDOWN_COLS)
    out.attrs["note"] = FIELD_BREAKDOWN_NOTE
    out.attrs["floor"] = PAIR_TOPICS_FLOOR
    return out


def _joint_vol_by_topic(ctx: dict, a: str, b: str) -> dict:
    """topic_id -> vol (CORE-AR, TRUE, UNCAPPED) for the pair (a, b), from
    `collab_topic_vols.parquet` NEW (item 4 fix -- was reading the top-100-
    CAPPED `collab_pair_topics`, silently returning 0 for any shared topic
    outside the cap and inflating `untapped()`'s gaps; WT_2BR3.md task 5.7 /
    SS0 task 6 #11 confirm this exact mechanism). Empty dict when the pair
    has no qualifying rows at all."""
    vols = _load_collab_topic_vols(ctx)
    lo, hi = (a, b) if a < b else (b, a)
    rows = vols[(vols["a"] == lo) & (vols["b"] == hi)]
    return dict(zip(rows["topic_id"], rows["vol"]))


UNTAPPED_COLS = ["topic_id", "topic_name", "subfield_id", "subfield_name", "vol_a", "vol_b",
                "joint_observed", "joint_expected", "gap", "url"]
SIBLING_COLS = ["subfield_id", "subfield_name", "topic_id", "topic_name", "vol_a", "vol_b"]


def untapped(ctx: dict, subs: dict, a: str, b: str, top_n: int = 100) -> dict:
    """2B-R2-11(a)/(f) Untapped potential -- the RULED REPLACEMENT for the
    deleted "what B publishes that A doesn't" footprint-gap table: this is
    an EXPECTED-vs-OBSERVED joint-output gap, a different and more useful
    question. Shared topics (`shared_topics`'s own `min_share > 0` rule, L3
    topic grain, tree/basis-aware via `subs`) where the pair's REALISED
    joint output is below a simple EXPECTED baseline:

        k = pair_copubs_total / min(a_total, b_total)      (pulse's own
                                                             denominators,
                                                             the smaller side)
        joint_expected(topic) = k * min(vol_a(topic), vol_b(topic))
        gap = joint_expected - joint_observed

    Reading: 'if this pair collaborated on this topic at the SAME overall
    rate they collaborate institution-wide (k), we would expect this many
    joint works there'. `joint_observed` comes from `collab_pair_topics`
    (0 for a shared topic outside the pair's shown top-100, or for a pair
    entirely below `PAIR_TOPICS_FLOOR` -- both a genuine 'untapped' signal
    here, not a data gap). Rows are kept only where `gap > 0`, sorted
    descending, capped at `top_n` (2B-R2-11: default 100, slider-ready --
    pass a smaller `top_n` for the page's slider). Each row carries a live
    OpenAlex `url` restricted to this topic.

    `siblings`: for the subfields appearing in the untapped list, every
    OTHER topic in that subfield (`topics_dim`, tree-aware) that EITHER side
    already holds nonzero volume in but which is NOT itself one of the
    pair's `shared_topics` -- adjacent topics the pair could plausibly
    extend collaboration into, uncapped, sorted by (subfield, vol_a, vol_b)
    descending."""
    shared = shared_topics(ctx, subs, a, b)
    if shared.empty:
        return {"topics": pd.DataFrame(columns=UNTAPPED_COLS), "siblings": pd.DataFrame(columns=SIBLING_COLS),
               "k": np.nan}

    vol_col = "vol_full" if subs["basis"] == "full" else "vol_frac"
    ta = P.topics_table(ctx, subs, a)[["topic_id", vol_col]].rename(columns={vol_col: "vol_a"})
    tb = P.topics_table(ctx, subs, b)[["topic_id", vol_col]].rename(columns={vol_col: "vol_b"})
    # `shared_topics`' own SHARED_TOPICS_COLS carries subfield_NAME only --
    # this function additionally needs subfield_id (for the sibling lookup
    # below), so join it back in via the same tree-aware map `shared_topics`
    # itself uses internally.
    subfield_ids = _topic_subfield_map(ctx, subs["tree"])
    df = shared[["topic_id", "topic_name", "subfield_name"]].merge(
        subfield_ids, on="topic_id", how="left").merge(
        ta, on="topic_id", how="left").merge(tb, on="topic_id", how="left")
    df[["vol_a", "vol_b"]] = df[["vol_a", "vol_b"]].fillna(0.0)

    pulse_ab = pulse(ctx, a, b)
    a_total = float(pulse_ab["denominator_a"]) if pulse_ab else 0.0
    b_total = float(pulse_ab["denominator_b"]) if pulse_ab else 0.0
    copubs_total = float(pulse_ab["copubs_total"]) if pulse_ab else 0.0
    smaller = min(a_total, b_total) if (a_total > 0 and b_total > 0) else 0.0
    k = (copubs_total / smaller) if smaller > 0 else 0.0

    joint = _joint_vol_by_topic(ctx, a, b)
    df["joint_observed"] = df["topic_id"].map(joint).fillna(0.0)
    df["joint_expected"] = k * np.minimum(df["vol_a"], df["vol_b"])
    df["gap"] = df["joint_expected"] - df["joint_observed"]
    df = df[df["gap"] > 0].sort_values("gap", ascending=False).head(top_n).reset_index(drop=True)
    df["url"] = [_taxon_url(a, b, "topic", t) for t in df["topic_id"]]
    topics_out = df.reindex(columns=UNTAPPED_COLS)

    subfield_ids = set(int(s) for s in topics_out["subfield_id"].dropna().unique())
    tree_col = f"{subs['tree']}_subfield_id"
    dim = ctx["topics_dim_df"][["topic_id", tree_col]].rename(columns={tree_col: "subfield_id"})
    dim = dim[dim["subfield_id"].isin(subfield_ids) & ~dim["topic_id"].isin(set(shared["topic_id"]))]
    extra = P._topics_dim_extra(ctx)[["topic_id", "topic_name"]]
    sfd_names = P._subfield_field_domain_map(ctx)[["subfield_id", "subfield_name"]]
    sib = dim.merge(extra, on="topic_id", how="left").merge(sfd_names, on="subfield_id", how="left") \
             .merge(ta, on="topic_id", how="left").merge(tb, on="topic_id", how="left")
    sib[["vol_a", "vol_b"]] = sib[["vol_a", "vol_b"]].fillna(0.0)
    sib = sib[(sib["vol_a"] > 0) | (sib["vol_b"] > 0)]
    siblings_out = sib.reindex(columns=SIBLING_COLS).sort_values(
        ["subfield_id", "vol_a", "vol_b"], ascending=[True, False, False]).reset_index(drop=True)

    return {"topics": topics_out, "siblings": siblings_out, "k": k}


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


# ============================================================================
# 2BR3 CD4 items 5/6 (BUILD_PLAN_2BR3.md SS2.3 momentum, SS1.6 reciprocity)
# ============================================================================

# Merged (manager, 2BR3 wave-1 close): palette.py is the ONE source of momentum
# hexes/glyphs; this module keeps only its ladder's "neutral" bucket alias
# (ns/new/dormant/weak all share palette's ns entry).
MOMENTUM_COLORS = {"up": PAL.MOMENTUM_COLORS["up"], "down": PAL.MOMENTUM_COLORS["down"],
                   "stable": PAL.MOMENTUM_COLORS["stable"], "neutral": PAL.MOMENTUM_COLORS["ns"]}
MOMENTUM_GLYPH = {"up": PAL.MOMENTUM_GLYPHS["up"], "down": PAL.MOMENTUM_GLYPHS["down"],
                  "stable": PAL.MOMENTUM_GLYPHS["stable"], "neutral": PAL.MOMENTUM_GLYPHS["ns"]}
MOMENTUM_CLAMP_PCT = 999.0  # SS2.3: delta_pct display-clamped at "> +999 %" (one-sided -- rr>=0 bounds delta at -100%)
MOMENTUM_NULL_TEXT = "—"


def _mom_num(v) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return float("nan")
    return f


def momentum_display(mom_class, mom_rr, mom_p, c1, c2, facts: dict) -> tuple[str, str, str]:
    """SS2.3's 9-case Lorraine momentum display ladder -- a PURE formatting
    function over an ALREADY-CLASSIFIED pair/field/topic row (`mom_class`/
    `mom_rr`/`mom_p` are pipeline outputs from `collab_pairs`/
    `collab_pair_fields`/`collab_pair_topics` v2; this function never
    reclassifies, and `c1`/`c2`/`facts` are accepted for signature parity
    with the brief and future message-text branches but are not needed by
    today's 9 cases -- classification already happened upstream). Returns
    `(text, hex_colour, glyph)`; colour is NEVER the only signal -- text and
    glyph always accompany it (WT_2BR3.md task 2.8's mandatory rule, the
    sharpest REFUTED finding in this Wind Tunnel pass).

    The 9 cases: null/unclassified -> '—' neutral; 'weak' (0<c1<5, no
    %) -> 'weak base'; 'new' -> 'new'; 'dormant' -> 'dormant'; 'ns' (demoted
    by the two-proportion z-test) -> 'n.s.'; 'up' normal -> signed no-decimal
    '+NN%'; 'up' beyond the clamp -> '> +999%'; 'down' -> signed no-decimal
    '-NN%'; 'stable' -> signed no-decimal '+NN%' (a real number inside the
    +-25% band, unlike the four label-only neutral states above)."""
    if mom_class is None or (isinstance(mom_class, float) and np.isnan(mom_class)):
        return MOMENTUM_NULL_TEXT, MOMENTUM_COLORS["neutral"], MOMENTUM_GLYPH["neutral"]
    mc = str(mom_class)
    if mc == "weak":
        return "weak base", MOMENTUM_COLORS["neutral"], MOMENTUM_GLYPH["neutral"]
    if mc == "new":
        return "new", MOMENTUM_COLORS["neutral"], MOMENTUM_GLYPH["neutral"]
    if mc == "dormant":
        return "dormant", MOMENTUM_COLORS["neutral"], MOMENTUM_GLYPH["neutral"]
    if mc == "ns":
        return "n.s.", MOMENTUM_COLORS["neutral"], MOMENTUM_GLYPH["neutral"]
    if mc not in ("up", "down", "stable"):
        raise AssertionError(f"unknown mom_class {mom_class!r}")
    rr = _mom_num(mom_rr)
    if not np.isfinite(rr):
        return MOMENTUM_NULL_TEXT, MOMENTUM_COLORS["neutral"], MOMENTUM_GLYPH["neutral"]
    delta_pct = (rr - 1.0) * 100.0
    if mc == "up" and delta_pct > MOMENTUM_CLAMP_PCT:
        return "> +999%", MOMENTUM_COLORS["up"], MOMENTUM_GLYPH["up"]
    return f"{delta_pct:+.0f}%", MOMENTUM_COLORS[mc], MOMENTUM_GLYPH[mc]


def pair_momentum(ctx: dict, a: str, b: str) -> dict | None:
    """Pair-header momentum verdict (SS2.3): reads `collab_pairs.parquet`
    v2's own `mom_class`/`mom_rr`/`mom_p`/`c1`/`c2` (already classified
    upstream -- ONE drift correction per run, per SS2.3) plus each side's own
    CORE-AR window totals (`index.total_ar_full_w1/w2`, SS2.2) for the
    evidence block's d1/d2, re-oriented to the CALLER's (a, b) like every
    other pair-table read in this module. Returns `None` when the pair has
    no `collab_pairs` row at all (never co-published)."""
    pairs = _load_collab_pairs(ctx)
    lo, hi = (a, b) if a < b else (b, a)
    row = pairs[(pairs["a"] == lo) & (pairs["b"] == hi)]
    if row.empty:
        return None
    row = row.iloc[0]
    idx = ctx["index_by_id"]
    d1 = float(idx.loc[a, "total_ar_full_w1"]) + float(idx.loc[b, "total_ar_full_w1"])
    d2 = float(idx.loc[a, "total_ar_full_w2"]) + float(idx.loc[b, "total_ar_full_w2"])
    c1, c2 = float(row["c1"]), float(row["c2"])
    facts = _load_collab_facts(ctx)
    text, color, glyph = momentum_display(row.get("mom_class"), row.get("mom_rr"), row.get("mom_p"), c1, c2, facts)
    return {
        "a": a, "b": b, "mom_class": row.get("mom_class"), "mom_rr": _mom_num(row.get("mom_rr")),
        "mom_p": _mom_num(row.get("mom_p")), "c1": c1, "c2": c2, "d1": d1, "d2": d2,
        "text": text, "color": color, "glyph": glyph,
    }


RECIPROCITY_COLS = ["field_id", "field_name", "domain_id", "domain_name", "x", "y", "joint_vol"]


def reciprocity_frame(ctx: dict, subs: dict, a: str, b: str) -> pd.DataFrame:
    """"Strategic reciprocity by field" (SS1.6, Lorraine port, HONEST
    both-sides variant per the brainstorm root-cause note -- Lorraine's own
    x-axis builder divides pair co-works by the PARTNER's total, which is in
    tension with its own copy; BenchUp implements the version that matches
    what the chart actually claims to show): per field with joint CORE-AR
    volume > 0, `x` = that field's share of B's OWN corpus, `y` = that
    field's share of A's OWN corpus (both `fields.parquet`, current tree/
    basis-aware via `subs` -- `compare_data.fields_long`, never recomputed
    here), `joint_vol` = the pair's CORE-AR joint volume in that field
    (`field_breakdown`'s own `vol`, the authoritative uncapped source, never
    the topic-rollup lower bound). One row per qualifying field; SYMMETRIC by
    construction -- swapping (a, b) swaps (x, y) and leaves `joint_vol`
    unchanged (field_breakdown is itself a<b-orientation-invariant)."""
    fb = field_breakdown(ctx, a, b)
    fb = fb[fb["vol"] > 0]
    if fb.empty:
        return pd.DataFrame(columns=RECIPROCITY_COLS)
    fl = CD.fields_long(ctx, subs, [a, b])
    a_share = fl[fl["institution_id"] == a].set_index("field_id")["share"]
    b_share = fl[fl["institution_id"] == b].set_index("field_id")["share"]
    out = fb[["field_id", "field_name", "domain_id", "domain_name", "vol"]].rename(columns={"vol": "joint_vol"})
    out["x"] = out["field_id"].map(b_share).fillna(0.0)  # field's share of B's OWN corpus
    out["y"] = out["field_id"].map(a_share).fillna(0.0)  # field's share of A's OWN corpus
    return out.reindex(columns=RECIPROCITY_COLS).sort_values("joint_vol", ascending=False).reset_index(drop=True)

"""
tests/fixtures/fixture_ctx.py -- CD4 (BUILD_PLAN_2BR3.md) fixture-context
builder. Hand-builds a MINIMAL `ctx`/`subs` pair (the same dict shapes
`lib.engine.substrates.load_context`/`build_substrates` produce) directly
from the small files `build_fixtures.py` writes, instead of running the full
engine (derive_shapes/l2_vectors) -- CD4's changed functions only ever touch
a handful of ctx/subs keys (see BUILD_PLAN_2BR3.md CD4 brief), so this is a
faithful, much cheaper substitute for fixture-scale tests. `lib.engine.
substrates._topic_share_values`/`_topic_matrix` ARE reused verbatim for the
L3 topic matrix (shared_topics/untapped's own dependency) so that piece is
never hand-duplicated.

DATA_DIR here holds the v2-schema fixtures (sdg_fields/sdg_year/erc/
collab_*/collab_topic_vols/collab_facts.json) CD4's rewritten
compare_data.py/collab_data.py consume -- see build_fixtures.py's own
docstring for the full institution/topic/field layout.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from lib.engine import substrates as ES

DATA_DIR = Path(__file__).resolve().parent / "data"

IA, IB, IC = "I9000001", "I9000002", "I9000003"
INST_IDS = [IA, IB, IC]

# T3 exists ONLY here (never in topics_all.parquet -- see build_fixtures.py):
# raw per-topic volumes for `profile_data.topics_table` (untapped()'s vol_a/
# vol_b) and the share values feeding the L3 substrate.
TOPIC_VOL_FRAC = {
    (IA, "T1"): 60.0, (IA, "T2"): 25.0, (IA, "T3"): 40.0,
    (IB, "T1"): 32.0, (IB, "T2"): 5.0, (IB, "T3"): 35.0,
    (IC, "T1"): 30.0, (IC, "T2"): 20.0, (IC, "T3"): 1.0,
}
# T3's vol is deliberately LARGE relative to T1/T2 (unlike a real topic's
# footprint) so that untapped()'s k * min(vol_a, vol_b) expected baseline
# clears its collab_topic_vols.parquet observed value of 2 -- a positive gap
# is what proves the topic reaches the returned `topics` frame at all,
# letting the fixture test check WHICH joint_observed number it carries
# (item 4: uncapped table, not the top-100-capped one that omits T3).
TOPIC_SHARE_FRAC = {
    (IA, "T1"): 0.6, (IA, "T2"): 0.3, (IA, "T3"): 0.1,
    (IB, "T1"): 0.5, (IB, "T2"): 0.2, (IB, "T3"): 0.3,
    (IC, "T1"): 0.4, (IC, "T2"): 0.4, (IC, "T3"): 0.2,
}
INST_KEY = {IA: 1, IB: 2, IC: 3}

# Momentum denominators (SS2.2 index.parquet v2 `total_ar_full_w1/w2`) --
# chosen so pair_momentum(IA, IB) exercises the "up" branch of the ladder
# with a clean r/rr the fixture doesn't need to reproduce (mom_class/mom_rr/
# mom_p are DATA on collab_pairs.parquet, classified upstream -- see
# build_fixtures.py).
INDEX_ROWS = {
    IA: dict(inst_key=1, total_ar_full_w1=300.0, total_ar_full_w2=220.0,
             erc_classified_mass_frac=35.0, sdg_classified_mass_frac=40.0,
             vol_full_by_year_this_run="2020:130.0|2021:130.0|2022:130.0|2023:190.0|2024:190.0",
             vol_frac_by_year_this_run="2020:15.0|2021:15.0|2022:15.0|2023:20.0|2024:20.0"),
    IB: dict(inst_key=2, total_ar_full_w1=150.0, total_ar_full_w2=140.0,
             erc_classified_mass_frac=10.0, sdg_classified_mass_frac=8.0,
             vol_full_by_year_this_run="2020:36.0|2021:36.0|2022:36.0|2023:24.0|2024:24.0",
             vol_frac_by_year_this_run="2020:9.0|2021:9.0|2022:9.0|2023:5.0|2024:5.0"),
    IC: dict(inst_key=3, total_ar_full_w1=100.0, total_ar_full_w2=100.0,
             erc_classified_mass_frac=20.0, sdg_classified_mass_frac=15.0,
             vol_full_by_year_this_run="2020:40.0|2021:40.0|2022:40.0|2023:40.0|2024:40.0",
             vol_frac_by_year_this_run="2020:10.0|2021:10.0|2022:10.0|2023:10.0|2024:10.0"),
}

ERC_ROWS = [
    {"institution_id": IA, "panel_idx": 0, "share": 0.4, "mass": 14.0, "mass_full": 28.0, "si": 1.1},
    {"institution_id": IB, "panel_idx": 0, "share": 0.6, "mass": 6.0, "mass_full": 12.0, "si": 0.9},
]
SDG_ROWS = [
    {"institution_id": IA, "sdg_idx": 0, "share": 0.4, "esi": 1.0, "mass": 10.0},
    {"institution_id": IA, "sdg_idx": 1, "share": 0.2, "esi": 1.0, "mass": 5.0},
    {"institution_id": IB, "sdg_idx": 0, "share": 0.5, "esi": 1.0, "mass": 6.0},
]


def build_ctx() -> dict:
    ctx: dict = {"data_dir": DATA_DIR, "topics_all_path": DATA_DIR / "topics_all.parquet"}

    ctx["index_by_id"] = pd.DataFrame.from_dict(INDEX_ROWS, orient="index")
    ctx["index_by_id"].index.name = "institution_id"

    topics_dim_df = pd.read_parquet(DATA_DIR / "topics_dim.parquet")
    ctx["topics_dim_df"] = topics_dim_df

    ctx["erc_df"] = pd.DataFrame(ERC_ROWS)
    ctx["sdg_df"] = pd.DataFrame(SDG_ROWS)

    ctx["id_pos"] = {iid: i for i, iid in enumerate(INST_IDS)}
    ctx["inst_ids"] = INST_IDS
    ctx["n"] = len(INST_IDS)

    topic_ids = sorted({t for (_, t) in TOPIC_VOL_FRAC})  # ["T1", "T2", "T3"]
    topic_pos = {t: i for i, t in enumerate(topic_ids)}
    ctx["topic_ids"] = topic_ids
    ctx["topic_pos"] = topic_pos

    keys = list(TOPIC_VOL_FRAC.keys())
    ctx["ta_inst"] = np.array([ctx["id_pos"][iid] for iid, _ in keys], dtype=np.int32)
    ctx["ta_topic"] = np.array([topic_pos[t] for _, t in keys], dtype=np.int32)
    ctx["ta_vol_frac"] = np.array([TOPIC_VOL_FRAC[k] for k in keys], dtype=np.float64)
    ctx["ta_vol_full"] = ctx["ta_vol_frac"] * 2.0
    ctx["ta_share"] = np.array([TOPIC_SHARE_FRAC[k] for k in keys], dtype=np.float64)

    with open(DATA_DIR / "collab_facts.json") as f:
        ctx["collab_facts"] = json.load(f)  # pre-warm the same cache key _load_collab_facts uses

    return ctx


def _scenario_frames(ctx: dict, tree: str = "bestfit"):
    fields_df = pd.read_parquet(DATA_DIR / "fields.parquet")
    subfields_df = pd.read_parquet(DATA_DIR / "subfields.parquet")
    return (fields_df[fields_df["tree"] == tree].reset_index(drop=True),
            subfields_df[subfields_df["tree"] == tree].reset_index(drop=True))


def build_subs(ctx: dict, tree: str = "bestfit", basis: str = "frac") -> dict:
    fields_df, subfields_df = _scenario_frames(ctx, tree)
    topic_vals = ES._topic_share_values(ctx, basis)
    l3 = {"share": ES._topic_matrix(ctx, topic_vals), "cats": ctx["topic_ids"]}
    return {"tree": tree, "basis": basis, "fields_df": fields_df, "subfields_df": subfields_df, "l3": l3}

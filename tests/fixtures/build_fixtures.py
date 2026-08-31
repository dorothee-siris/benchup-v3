"""
tests/fixtures/build_fixtures.py -- CD4 (BUILD_PLAN_2BR3.md, Phase 2B-R3)
fixture builder: writes SMALL parquet/json files under tests/fixtures/data/
that satisfy the SS2.2 v2 schemas P7 will produce for real. CD4 tests against
these now; the manager re-runs the suite against real artefacts once P7
lands (BUILD_PLAN_2BR3.md S4 W3).

Three fake institutions (IA/IB/IC), two fields (each with exactly one
subfield, so field-grain and subfield-grain dynamics numbers are identical --
deliberate, keeps hand-verified anchors simple), two topics (T1/T2) that
drive the on-disk topics_all.parquet (used by the yearly-by-subfield duckdb
queries), plus a THIRD topic T3 that exists ONLY in the in-memory L3/topics_
table arrays a conftest fixture builds directly (see tests/fixtures/
fixture_ctx.py) -- T3 never appears in topics_all.parquet, so it cannot
perturb the hand-verified dynamics anchors, but it IS a real shared topic
between IA/IB with a joint volume that is NOT in collab_pair_topics.parquet
(simulating the top-100 cap) while IS in collab_topic_vols.parquet (the new
uncapped companion) -- the exact case item 4's untapped() fix targets.

Run: python build_fixtures.py   (from this folder, or any cwd -- paths are
relative to this file)
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parent / "data"
OUT.mkdir(parents=True, exist_ok=True)

IA, IB, IC = "I9000001", "I9000002", "I9000003"
YEARS = [2020, 2021, 2022, 2023, 2024]  # CFG["window"] core window, 5 years

# ---------------------------------------------------------------------------
# fields.parquet / subfields.parquet (UNCHANGED schema per SS2.2 -- one
# subfield per field here, so subfield-grain reproduces field-grain exactly).
# ---------------------------------------------------------------------------
FIELD_META = {1: ("Field One", 1, "Domain Alpha"), 2: ("Field Two", 2, "Domain Beta")}
SUBFIELD_META = {101: (1, "Subfield One-A"), 201: (2, "Subfield Two-A"), 102: (1, "Subfield One-B")}

# institution -> field_id -> (vol_frac_total, vol_full_total) -- vol_full is
# ALWAYS exactly 2x vol_frac here (deliberate: isolates the basis TOGGLE
# effect on denom_value/vol_display to plain magnitude, ratios/shares stay
# identical across bases, so a test can tell the two apart by NUMBER alone).
FIELD_VOL = {
    IA: {1: 60.0, 2: 25.0},
    IB: {1: 32.0, 2: 5.0},
    IC: {1: 30.0, 2: 20.0},
}
FIELD_SI = {1: 1.2, 2: 0.7}


def _fields_rows():
    rows = []
    for iid, by_field in FIELD_VOL.items():
        total_frac = sum(by_field.values())
        total_full = total_frac * 2.0
        for fid, vfrac in by_field.items():
            fname, dom_id, dom_name = FIELD_META[fid]
            vfull = vfrac * 2.0
            rows.append({
                "inst_key": {IA: 1, IB: 2, IC: 3}[iid], "institution_id": iid, "field_id": fid,
                "tree": "bestfit", "vol_frac": vfrac, "vol_full": vfull,
                "share_frac": vfrac / total_frac, "share_full": vfull / total_full,
                "si": FIELD_SI[fid],
            })
    return rows


def _subfields_rows():
    """One subfield per field (101<->field1, 201<->field2) -- IDENTICAL
    numbers to fields.parquet by construction (subfield IS the field here).
    Subfield 102 (field1) carries ZERO mass everywhere -- it exists only so
    topics_dim can place T3 somewhere without perturbing any institution's
    field/subfield totals (T3 never appears in topics_all.parquet)."""
    rows = []
    fld_rows = {(r["institution_id"], r["field_id"]): r for r in _fields_rows()}
    for iid in (IA, IB, IC):
        for sid, (fid, sname) in SUBFIELD_META.items():
            if sid == 102:
                continue  # zero-mass everywhere, never shipped as a nonzero-mass row
            fr = fld_rows[(iid, fid)]
            rows.append({**fr, "subfield_id": sid, "subfield_name": sname})
    return rows


fields_df = pd.DataFrame(_fields_rows())
fields_df.to_parquet(OUT / "fields.parquet", index=False)

subfields_df = pd.DataFrame(_subfields_rows())
subfields_df.to_parquet(OUT / "subfields.parquet", index=False)

# ---------------------------------------------------------------------------
# topics_dim.parquet -- T1 (subfield 101/field1), T2 (subfield 201/field2),
# T3 (subfield 102/field1, ZERO mass in topics_all -- see module docstring).
# ---------------------------------------------------------------------------
TOPIC_META = {
    "T1": (101, "Topic One", False, False),
    "T2": (201, "Topic Two", False, False),
    "T3": (102, "Topic Three", False, False),
}
topics_dim_rows = []
for tid, (sid, tname, is_excl, frontier) in TOPIC_META.items():
    fid, sname = SUBFIELD_META[sid]
    fname, dom_id, dom_name = FIELD_META[fid]
    topics_dim_rows.append({
        "topic_id": tid, "subfield_id": sid, "subfield_name": sname, "field_id": fid,
        "field_name": fname, "domain_id": dom_id, "domain_name": dom_name,
        "is_excluded": is_excl, "top25pct_frontier": frontier,
        "original_subfield_id": sid, "conservative_subfield_id": sid, "bestfit_subfield_id": sid,
        "topic_name": tname, "frontier_score_latest": 0.2, "expansion_latest": 0.0,
        "acceleration_latest": 0.0, "quadrant": None,
        "keywords": f"{tname.lower()}|keyword-two|keyword-three",
    })
topics_dim_df = pd.DataFrame(topics_dim_rows)
topics_dim_df.to_parquet(OUT / "topics_dim.parquet", index=False)

# ---------------------------------------------------------------------------
# topics_all.parquet -- T1/T2 ONLY (T3 deliberately absent, see docstring),
# per-year vol_full_<y>/vol_frac_<y> for the 5-year core window. These are
# the hand-verified DYNAMICS anchors: IA/T1 W1=10.0->W2=15.0 (+50%), IA/T2
# flat (0%), IB/T1 W1=8.0->W2=4.0 (-50%), IB/T2 flat/near-zero (low-volume
# floor case), IC flat both fields.
# ---------------------------------------------------------------------------
PER_YEAR_FRAC = {
    (IA, "T1"): [10, 10, 10, 15, 15],
    (IA, "T2"): [5, 5, 5, 5, 5],
    (IB, "T1"): [8, 8, 8, 4, 4],
    (IB, "T2"): [1, 1, 1, 1, 1],
    (IC, "T1"): [6, 6, 6, 6, 6],
    (IC, "T2"): [4, 4, 4, 4, 4],
}
INST_KEY = {IA: 1, IB: 2, IC: 3}

ta_rows = []
for (iid, tid), vals in PER_YEAR_FRAC.items():
    row = {"inst_key": INST_KEY[iid], "topic_id": tid}
    for y, v in zip(YEARS, vals):
        row[f"vol_frac_{y}"] = float(v)
        row[f"vol_full_{y}"] = float(v) * 2.0
    ta_rows.append(row)
topics_all_df = pd.DataFrame(ta_rows)
topics_all_df.to_parquet(OUT / "topics_all.parquet", index=False)

# Cross-check the per-field totals above equal the per-year sums (fields.parquet
# and topics_all.parquet must agree for the dynamics tests' anchors to hold).
for iid, by_field in FIELD_VOL.items():
    for fid, want in by_field.items():
        tid = "T1" if fid == 1 else "T2"
        got = sum(PER_YEAR_FRAC[(iid, tid)])
        assert got == want, (iid, fid, got, want)

# ---------------------------------------------------------------------------
# sdg_fields.parquet v2 -- institution x field_id x tree: mass_any_frac/full
# (distinct-tagged, matched-window numerator for the item-2 SDG-share fix).
# IA/field2 is the value==1.0 edge case (assert value <= 1+eps must still pass).
# ---------------------------------------------------------------------------
SDG_FIELDS_ANY = {
    (IA, 1): 24.0, (IA, 2): 25.0,
    (IB, 1): 16.0, (IB, 2): 0.0,
    (IC, 1): 15.0, (IC, 2): 10.0,
}
sdg_fields_rows = [
    {"institution_id": iid, "field_id": fid, "tree": "bestfit",
     "mass_any_frac": v, "mass_any_full": v * 2.0}
    for (iid, fid), v in SDG_FIELDS_ANY.items()
]
pd.DataFrame(sdg_fields_rows).to_parquet(OUT / "sdg_fields.parquet", index=False)

# ---------------------------------------------------------------------------
# sdg_year.parquet v2 -- institution x sdg_idx x year (2020-2025 on disk,
# functions window-slice to 2020-2024): mass_frac, mass_full. sdg_idx 1 for
# IB is all-zero (w1<=0 -> NaN dynamics value, a real fixture edge case).
# ---------------------------------------------------------------------------
SDG_YEAR_FRAC = {
    (IA, 0): [4, 4, 4, 6, 6, 6],
    (IA, 1): [1, 1, 1, 1, 1, 1],
    (IB, 0): [3, 3, 3, 1, 1, 1],
    (IB, 1): [0, 0, 0, 0, 0, 0],
}
ALL_YEARS = YEARS + [2025]
sdg_year_rows = []
for (iid, sidx), vals in SDG_YEAR_FRAC.items():
    for y, v in zip(ALL_YEARS, vals):
        sdg_year_rows.append({"institution_id": iid, "sdg_idx": sidx, "year": y,
                              "mass_frac": float(v), "mass_full": float(v) * 2.0})
pd.DataFrame(sdg_year_rows).to_parquet(OUT / "sdg_year.parquet", index=False)

# ---------------------------------------------------------------------------
# impact_fields.parquet -- UNCHANGED schema (SS2.2 lists it unchanged); real
# columns confirmed 2026-08-31 via a live schema dump of app/data/impact_fields
# .parquet: pp_denominator_frac + n_works_full both already exist.
# ---------------------------------------------------------------------------
IMPACT_FIELDS = {
    (IA, 1): dict(pp=0.25, lo=0.20, hi=0.30, denom_frac=60.0, n_full=120.0),
    (IA, 2): dict(pp=0.10, lo=0.05, hi=0.15, denom_frac=25.0, n_full=50.0),
    (IB, 1): dict(pp=0.40, lo=0.30, hi=0.50, denom_frac=32.0, n_full=64.0),
    (IC, 1): dict(pp=0.20, lo=0.15, hi=0.25, denom_frac=30.0, n_full=60.0),
}
impact_rows = [
    {"institution_id": iid, "field_id": fid, "tree": "bestfit", "floor": 30,
     "pp_top10_frac": d["pp"], "pp_ci_low": d["lo"], "pp_ci_high": d["hi"],
     "pp_denominator_frac": d["denom_frac"], "n_works_full": d["n_full"]}
    for (iid, fid), d in IMPACT_FIELDS.items()
]
pd.DataFrame(impact_rows).to_parquet(OUT / "impact_fields.parquet", index=False)

# ---------------------------------------------------------------------------
# collab_pairs.parquet v2 -- ONE pair, a=IA < b=IB. mom_class/mom_rr/mom_p
# are DATA here (pipeline-classified upstream, per SS2.3 -- CD4's
# momentum_display() only FORMATS an already-classified row, never
# reclassifies), chosen so momentum_display(...) == ("+50%", up-green, up-glyph).
# ---------------------------------------------------------------------------
copubs = {2020: 5, 2021: 5, 2022: 5, 2023: 3, 2024: 3, 2025: 2}
core_total = sum(copubs[y] for y in YEARS)  # 21 (2025 excluded, CORE-AR)
c1 = copubs[2020] + copubs[2021] + copubs[2022]  # 15
c2 = copubs[2023] + copubs[2024]                 # 6
pairs_row = {
    "a": IA, "b": IB, **{f"copubs_{y}": copubs[y] for y in ALL_YEARS},
    "copubs_total": sum(copubs.values()), "core_total": core_total, "c1": c1, "c2": c2,
    "n_top10": 4, "n_covered": 18, "n_sdg": 3, "fwci_median": 1.15,
    "rank_in_a": 1, "rank_in_b": 1,
    "mom_class": "up", "mom_rr": 1.5, "mom_p": 0.01,
    "erc_top_panel": "PE3", "erc_top_panel_n": 5, "erc_labelled_n": 20,
}
pd.DataFrame([pairs_row]).to_parquet(OUT / "collab_pairs.parquet", index=False)

# ---------------------------------------------------------------------------
# collab_pair_fields.parquet v2 / collab_pair_topics.parquet v2 -- vol1+vol2
# == core_total (21) by construction; T1<->field1, T2<->field2 (1:1, same
# numbers on both tables -- a deliberate cross-check, not a requirement).
# ---------------------------------------------------------------------------
pair_fields_rows = [
    {"a": IA, "b": IB, "field_id": 1, "vol": 15, "vol_w1": 10, "vol_w2": 5,
     "n_top10": 3, "n_covered": 12, "n_sdg": 2, "fwci_median": 1.2, "mom_class": "up"},
    {"a": IA, "b": IB, "field_id": 2, "vol": 6, "vol_w1": 4, "vol_w2": 2,
     "n_top10": 1, "n_covered": 5, "n_sdg": 1, "fwci_median": 0.9, "mom_class": "down"},
]
pd.DataFrame(pair_fields_rows).to_parquet(OUT / "collab_pair_fields.parquet", index=False)

pair_topics_rows = [
    {"a": IA, "b": IB, "topic_id": "T1", "vol": 15, "vol_w1": 10, "vol_w2": 5,
     "n_top10": 3, "n_covered": 12, "n_sdg": 2, "fwci_median": 1.2, "mom_class": "up"},
    {"a": IA, "b": IB, "topic_id": "T2", "vol": 6, "vol_w1": 4, "vol_w2": 2,
     "n_top10": 1, "n_covered": 5, "n_sdg": 1, "fwci_median": 0.9, "mom_class": "down"},
    # T3 is DELIBERATELY ABSENT here (simulates the top-100 cap) -- present
    # only in collab_topic_vols.parquet below. This is the exact case item 4
    # targets: untapped()'s joint_observed must come from the UNCAPPED table.
]
pd.DataFrame(pair_topics_rows).to_parquet(OUT / "collab_pair_topics.parquet", index=False)

# ---------------------------------------------------------------------------
# collab_topic_vols.parquet NEW -- UNCAPPED true joint volumes, incl. T3
# (vol=2, absent from collab_pair_topics above).
# ---------------------------------------------------------------------------
topic_vols_rows = [
    {"a": IA, "b": IB, "topic_id": "T1", "vol": 15},
    {"a": IA, "b": IB, "topic_id": "T2", "vol": 6},
    {"a": IA, "b": IB, "topic_id": "T3", "vol": 2},
]
pd.DataFrame(topic_vols_rows).to_parquet(OUT / "collab_topic_vols.parquet", index=False)

# ---------------------------------------------------------------------------
# collab_facts.json NEW
# ---------------------------------------------------------------------------
facts = {"med": 1.0, "w1": [2020, 2022], "w2": [2023, 2024], "band": 0.25, "alpha": 0.05,
         "elig_min": 10, "weak_base_max": 4, "new_min_c2": 5, "dormant_min_c1": 5, "basis": "CORE-AR"}
with open(OUT / "collab_facts.json", "w") as f:
    json.dump(facts, f, indent=2)

print(f"wrote fixtures to {OUT}")
for p in sorted(OUT.iterdir()):
    print(" ", p.name)

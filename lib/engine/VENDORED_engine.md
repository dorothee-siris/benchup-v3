# VENDORED — `app/lib/engine/` (BenchUp v3, Sprint 2 Phase 2A, Stream B)

Provenance for the engine only. Stream C merges this file into `app/docs/VENDORED.md`.
Everything below was **copied**, not rewritten: the numbers this app shows are the numbers
`evals/campaign_v2/gen_lists_v2.py` produced, and `tests/test_golden_lenses.py` pins that
(37 seeds × 10 lenses + concordance + aspirational + seed card, 37/37 PASS).

Source root: `V3/` (paths below are relative to it). Snapshot of the sources: 2026-08-29.

---

## 1. Module map — source → destination

| Source | What was taken | Destination | Form |
|---|---|---|---|
| `pipeline/agg/trees_agg.py` | module docstring, `TREES`, `G6_FLOOR`, `subfield_to_field_map` | `trees_agg.py` | verbatim slice |
| `pipeline/agg/derive.py` | `_posix`, `_detect_year_cols`, `_cast_output`, `derive_shapes`, `VALID_BASES` + the whole docstring | `derive.py` | verbatim, `__main__` self-test dropped |
| `pipeline/agg/l2_variants.py` | `VALID_VARIANTS`, `_apply_variant`, `_raw_scenario`, `_dense_from_scenario`, `l2_vectors` | `l2_vectors.py` | verbatim slices, new import header |
| `evals/analysis_eu/lens_lib.py` | whole file (loaders, `build_dense_matrix`, `subfield_matrices`, `field_matrices`, `topic_matrices`, `erc_matrices`, `sdg_matrices`, `histogram_intersection_row`, `excess_profile`, `specialisation_mask`, `jaccard_set_row`, `top_k_excluding_self`, `topk_overlap`, `D19_SEEDS`, `SDG_LABELS`, codebook loaders) | `lens_lib.py` | verbatim + path/import fixes |
| `evals/analysis_eu/r2/lens_lib_r2.py` | `excess_profile_matrix` | appended to `lens_lib.py` | verbatim |
| `evals/campaign/gen_lists_recall.py` | `load_everything` (→ `load_context`), `build_l1_c1_substrate`, `build_l3_substrate`, `build_l2f_substrate`, `build_l5_substrate`, `build_l6_substrate`, `build_l7_substrate`, `build_f1_substrate` (→ `substrates.build_substrates`); `rank_map`, `is_degenerate`, `parse_shape_top3`, `base_evidence`, `rank_under_l1_l3`, `build_seed_card` (→ `lenses.py`) | `substrates.py`, `lenses.py` | formulas verbatim, IO/CLI removed |
| `evals/campaign_v2/gen_lists_v2.py` | L0 substrate, `full_sorted_positive`, `top_n_ids_with_ties`/`top_n_pairs_with_ties` (→ `cut_with_ties`), `competition_ranks`, `cut_rows_with_ties`, `base_evidence_v2`, `build_rows_v2` (→ `build_rows`), `build_c1_for_seed`, `build_concordance` (→ `concordance`), `build_aspirational_v2` (→ `aspirational`), `build_catchall_811_share` (→ `catchall_811_share`), `process_seed`'s per-lens branches + reason strings (→ `rank_all`), `RANK_VISIBLE_MAX = 50`, `get_peak_rss_gb` (→ the identity test) | `lenses.py`, `tests/test_engine_identity.py` | formulas verbatim |

### Resources copied into `resources/`

| Source | Destination | Read by |
|---|---|---|
| `reference/taxonomy_repair_v1.3/openalex_subfield_codebook_v1.csv` (308 KB) | `resources/openalex_subfield_codebook_v1.csv` | `lens_lib.load_subfield_codebook` → subfield names on the seed card and C1 evidence |
| `evals/erc_calibration/id2label_verification.json` (1.5 KB) | `resources/erc_id2label_verification.json` | `lens_lib.load_erc_labels` → the 28 ERC panel labels (L4/L5 display) |

Grepped for every `Path(`, `read_csv`, `read_parquet`, `json.load` in the sources: the only
non-artefact files they open are those two. `field_name_by_id` comes from `topics_dim.parquet`
(shipped in `app/data/`), and the SDG labels are an in-module constant (`lens_lib.SDG_LABELS`).

### Golden fixtures copied into `app/tests/golden/`

| Source | Destination |
|---|---|
| `evals/campaign_v2/lists/I*.json` (37 files; `_RUN_SUMMARY.json` / `INDEX.md` excluded) | `tests/golden/lists/` |
| `evals/face_validity_ids.json` | `tests/golden/d19.json` |
| `evals/campaign_v2/panel_v2.json` | `tests/golden/panel_v2.json` |

---

## 2. Deviations from the sources — every one

### Mechanical (no arithmetic touched)

1. **Imports.** `sys.path.insert` surgery and the `V3_ROOT`-relative imports of the eval
   scripts are replaced by package-relative imports (`from .trees_agg import …`,
   `from . import lens_lib as L`). `lens_lib.V3_ROOT` becomes
   `RESOURCES = Path(__file__).parent / "resources"`; its two file paths now point there.
2. **CLI / IO / rendering removed.** `derive.py`'s `__main__` self-test, `l2_variants`'
   campaign runner + self-test + CLI, and the two generators' markdown renderers,
   checkpointing, `_RUN_SUMMARY.json` writing, external-peer marking (`resolved.json`,
   `external_tier`, `external_hits_by_depth`) and seed-pool loading are **not** ported —
   they are eval-campaign scaffolding, not app behaviour.
3. **`RANK_VISIBLE_MAX = 50`** is a module constant in `lenses.py` rather than
   `gen_lists_v2`'s import-time monkey-patch of `gen_lists_recall`. Same value, same effect.
4. **`base_evidence`** merges `gen_lists_recall.base_evidence` and
   `gen_lists_v2.base_evidence_v2` into one function (v2 only added the `type_openalex`
   line). The golden rows carry the v2 shape, which is what the app emits.
5. **Streamlit-free.** No `streamlit` import anywhere under `engine/` (asserted by grep).

### Parametrised where the generators hard-coded

6. **Lens set.** `rank_all(ctx, subs, seed_id, lenses)` takes the lens list;
   `concordance(ctx, rankings, lenses, N)` takes both the lens set and N. The golden runs
   with `{L1,L3,F1,L2f,L4,L5,L6}` at N∈{10,20,30}; the app's default overview will use the
   8 enabled default lenses (`DEFAULT_LENSES`, L3 of the plan). `GOLDEN_CONCORDANCE_LENSES`
   preserves the generator's own 7 for the regression.
7. **`tree` / `basis`.** The generators only ever built the default scenario
   (bestfit/frac/811-included). `build_substrates(ctx, tree, basis)` threads both through:
   L0/L1/C1 pick `share_frac` vs `share_full`; L2f passes `basis` to `l2_vectors` (whose own
   docstring already generalises it); L3/F1 use `share_frac` on the fractional basis and a
   **vol_full-normalised share** on the full basis (see §3 note 1).
8. **`basis_applies`.** `subs["basis_applies"]` marks L4/L5/L6/L7 `False` — the ERC and SDG
   artefacts are fractional-only, so the basis toggle is inert for them (L5 of the plan).
9. **`pool` / `depth` parameters.** `aspirational(..., pool=50)` and `build_rows(..., depth)`
   expose what `gen_lists_v2` hard-coded as `DEPTH = 50`.
10. **`cut_with_ties(sorted_ids, sorted_scores, n)`** is `top_n_ids_with_ties` +
    `top_n_pairs_with_ties` fused into one id/score-pair function (same cut rule, same
    "never pad" behaviour). `top_n_pairs_with_ties` is kept alongside it, verbatim.

### Data-layer deviations (the ones that could move a number — all measured)

11. **`topics_all` is read with FIVE columns** (`inst_key, topic_id, share_frac, vol_frac,
    vol_full`) instead of the whole table (BUILD_PLAN_2A §2 / WT #7: 533 MB deep, 366 MB of
    it object strings). `institution_id` is therefore absent, so the L3 / F1 / catch-all
    computations key on the **integer institution position** (`inst_key` → row via a lookup
    array) rather than on `institution_id`:
    - `lens_lib.build_dense_matrix`'s `pivot_table(index="institution_id", aggfunc="sum")`
      becomes a positional scatter (`substrates._topic_matrix`). `(institution_id, topic_id)`
      is the primary key of `topics_all`, so a summing pivot and a scatter give the same
      matrix — **uniqueness is asserted at load**, not assumed. Column axis is
      `sorted(topic_id)`, identical to `lens_lib.topic_matrices`' own `cats`.
      Verified: the scattered matrix is **bit-identical** to `topic_matrices`' output
      (0 differing cells of 7 557 × 4 516).
    - `build_catchall_811_share`'s `groupby("institution_id")["share_frac"].sum()` becomes a
      `np.bincount` on the position, accumulating in float64 rather than pandas float32.
      Difference ≈1e-9, well inside the golden's 1e-6 (37/37 seeds PASS on
      `card.catchall_811_share`).
12. **MEMORY ORDER IS LOAD-BEARING (found the hard way, do not "clean up").**
    `build_dense_matrix` ends in `wide.to_numpy(...)` on a homogeneous DataFrame, which
    returns an **F-contiguous** array; `np.minimum(...).sum(axis=1)` accumulates float32 in
    memory order, so the same matrix in C order gives a different L3 score
    (Gdańsk × Łódź: **0.5925397** C-order vs **0.5925411** F-order — 1.4e-6 apart, i.e.
    outside the golden tolerance). `substrates._topic_matrix` therefore allocates
    `order="F"`. Every other substrate still goes through `build_dense_matrix` and inherits
    the layout automatically.
13. **L1/C1 always come from `derive_shapes`, never from the shipped `subfields.parquet`** —
    even on the default scenario, where BUILD_PLAN_2A's Stream B row suggested the shipped
    table. Measured reason: the two agree only to float32 (**130 420 of 770 871 `share_frac`
    cells differ, max 6.0e-8**), which passes the Tier-A identity check but can move a tie at
    a top-50 cut. `gen_lists_recall.build_l1_c1_substrate` used `derive_shapes`, so the
    golden pins the derived values. Cost of the choice: 1.5 s inside a 5–7 s cold load.
14. **L0 on the DEFAULT scenario comes from the shipped `fields.parquet`** (`share_frac`),
    because that is what `gen_lists_v2.main` used and what the golden pins; any other
    (tree, basis) uses the `fields` frame the same `derive_shapes` call returns. Asymmetric
    with note 13 on purpose — both halves follow the golden.
15. **`impact_cells.parquet` is not loaded by `load_context`** (`load_impact_cells(ctx)` is
    lazy). The aspirational lens reads `pp_top10_frac` / `pp_ci_low` / `pp_ci_high` from
    `index.parquet`, exactly as `build_aspirational_v2` does.
16. **`l2_vectors._raw_scenario.cache_clear()`** is called at the end of
    `build_substrates`, freeing the unfloored `derive_shapes` frame (~130 MB) once the L2f
    matrices exist. The upstream `functools.lru_cache(maxsize=8)` is otherwise untouched.
17. **`exclude_811` is hard-wired to `False`.** The 811 toggle was removed from the UI
    (L5 of the plan); `derive_shapes`/`l2_vectors` keep the parameter.

### Documented upstream nuances preserved (not deviations — listed so nobody "fixes" them)

- The **G6 floor stays on `vol_frac`** regardless of `basis` (derive.py's own basis-
  generalisation note). L2f's own eligibility floor is on **papers** (`vol_full ≥ 30`,
  candidate (f)) — a different floor, in `l2_variants`, unchanged.
- The **mean-share population** is "institutions with a NONZERO row for that subfield",
  not the whole index (derive.py's second documented nuance).
- **`si` is NaN below the floor** and must stay NaN (not 0) so the excess-profile logic can
  tell "no SI" from "SI == 0".
- **`sdg.share` is MULTI-LABEL** (sums > 1 per institution): L6 renormalises to a profile
  before the overlap; L7 uses the `esi` column, which `lens_lib.sdg_matrices` returns under
  the generic dict key `si`.
- **L0 spans 26 fields, not 19** (gen_lists_v2 deviation note 1: no 19-field cut exists in
  the shipped taxonomy).
- **`build_seed_card`'s top-5 uses `np.argsort(-row)` without `kind="stable"`** while
  `build_c1_for_seed`'s top-20 uses `kind="stable"`. Copied as-is, asymmetry included.
- **Concordance's mean-rank tie-break averages only over the lenses that hit the candidate**
  at that N (gen_lists_v2 interpretive note 4).
- **Aspirational rows stay in L1-overlap order**, never re-sorted by PP (L4 of the plan).

---

## 3. Known limits of the Tier-A identity check

1. **`basis="full"` is not cross-checked against anything.** `trees_agg` never ships a
   full-basis `si`, so there is no reference table (derive.py flags this itself). The tests
   only assert that shares still sum to 1 per institution under `basis="full"`. The
   vol_full-normalised topic share used by L3/F1 on that basis is likewise new here.
2. **One G6-floor boundary cell.** For `tree=original`, exactly **1 cell of 756 484** has
   `vol_frac == 30.0` in float32 and falls on opposite sides of `vol_frac >= 30` between
   `trees_agg` (float64 pandas over the raw corpus) and `derive_shapes` (duckdb over the
   topic grain) — so its `si` is a value in one and NaN in the other.
   `conservative`: 0. Shipped `bestfit`: 0. The test tolerates *only* mismatches whose
   `vol_frac` is on the floor, prints the count, and fails on any other NaN-pattern change.
3. **Cell-level float32 noise is expected and reported, not asserted away.** The test prints
   the number of cells that differ *at all*: 367 166 (bestfit vs shipped), 368 129
   (original), 368 861 (conservative) — out of ~4.6 M compared values each. Every one is
   inside a symmetric relative tolerance of 1e-6; the worst measured is **1.2e-7**
   (a float32 ulp).
4. `np.allclose`'s asymmetric `rtol * |b|` is **not** used: the test computes
   `|a-b| / max(|a|,|b|)` so a derived zero cannot divide the tolerance away.

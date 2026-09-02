"""tests/test_ram_budget.py -- BUILD_PLAN_2E.md Stream T (RAM fit for
Streamlit Community Cloud, ~2.7 GB cap) permanent gate.

RSS-SENSITIVE, like `test_engine_identity.py::test_budgets` -- run this file
ISOLATED, never mixed into the main pytest sweep. `test_full_loader_sweep_
rss_delta` needs a clean just-imported baseline: a shared process that
already ran other test files (which themselves call `lib.data_cache`
loaders, e.g. `test_pages.py`) would read stale-warm frames and pass
vacuously regardless of what this stream actually shipped. Gate ladder
convention (BUILD_PLAN_2E.md Stream T): the main run excludes this whole
file (`--ignore=tests/test_ram_budget.py`, mirroring test_budgets' own
`--deselect`), then it runs on its own:

    python -m pytest tests/test_ram_budget.py -q -s

Data-driven, no fixtures -- reads the REAL app/data directly, same
convention as test_repack_2e.py.

Covers (BUILD_PLAN_2E.md E8 Stream T brief, tasks 1.1-1.3):
  1. test_frame_census_under_budget       -- every remaining data_cache.py
     loader + engine.substrates.load_context, summed memory_usage(deep=True)
     of every returned/held DataFrame, < FRAME_BUDGET_MB.
  2. test_collab_parquets_never_loaded_whole -- Stream B's duckdb pushdown
     contract: no whole-table collab_* loader survives on data_cache, and a
     single-pair slice never returns more than a few hundred rows.
  3. test_full_loader_sweep_rss_delta     -- process-level fallback for the
     dtype-sentinel ask (test_repack_2e.py already parametrizes ID-column/
     float64 checks over EVERY deployed parquet, index/impact_taxa/subfields
     included -- a 3-table repeat here would be a pure duplicate, so per the
     brief this asserts the process-level number instead): WorkingSetSize
     delta between a just-imported baseline and after firing the full loader
     sweep, in ONE process, < RSS_DELTA_BUDGET_MB.

TEST ORDER IS LOAD-BEARING: the RSS-delta test MUST run before anything else
in this file calls a data_cache loader or load_context, or its baseline is
already warm. Python/pytest collect test functions in file definition
order (no reordering plugin in this suite, confirmed against conftest.py) --
`test_full_loader_sweep_rss_delta` is therefore defined FIRST.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT / "ops"))

from lib import collab_data as CDL  # noqa: E402
from lib import data_cache as DC  # noqa: E402
from lib.engine.substrates import load_context  # noqa: E402
from rss_probe import process_rss_mb  # noqa: E402

DATA_DIR = APP_ROOT / "data"

# Every remaining lib/data_cache.py loader that returns a DataFrame (E5/E4
# deleted the three whole-table collab_* loaders and impact_fields() --
# `manifest()` returns a dict, not a frame, and is deliberately excluded).
DATAFRAME_LOADERS = ["index", "fields", "subfields", "topics_dim", "erc", "sdg", "impact_cells",
                     "topics_all_slim", "doctype_by_year", "sdg_fields", "sdg_year"]

# Measured 2026-09-02 (post Streams P+B, this stream's own calibration,
# V3/evals/gate_2E/calibrate_ram.py): data_cache's 11 loaders sum to 134.82 MB,
# load_context's 7 frame-valued ctx entries sum to 71.58 MB -- 206.39 MB
# total, ~2.9x headroom under this ceiling.
FRAME_BUDGET_MB = 600.0

# Measured 2026-09-02 (same calibration run, import-time baseline matching
# this file's own module-level imports): full loader sweep RSS delta 475.55
# MB WorkingSetSize -- ~1.9x headroom under this ceiling. Brief-given
# threshold (BUILD_PLAN_2E.md E8 Stream T task 1.3), not independently
# recalibrated.
RSS_DELTA_BUDGET_MB = 900.0

COLLAB_PAIR_ROW_CAP = 5000
# E1's own anchor pair (BUILD_PLAN_2E.md E1: "3 pairs incl. Ifremer x NIOZ").
IFREMER_ID, NIOZ_ID = "I154202486", "I4210107283"


def test_full_loader_sweep_rss_delta():
    """MUST run first in this file (see module docstring) -- WorkingSetSize
    delta between a just-imported baseline and after firing every
    DATAFRAME_LOADERS entry plus load_context, in ONE process. A collab
    parquet accidentally loaded whole again (3.4-15.4M rows) would blow this
    budget by an order of magnitude; the frame-census test below cannot catch
    that on its own since it inspects only the OBJECTS this stream's own
    loaders return, not incidental process-wide allocation."""
    baseline = process_rss_mb()
    assert baseline is not None, "could not read baseline process RSS (ctypes GetProcessMemoryInfo failed)"

    for name in DATAFRAME_LOADERS:
        getattr(DC, name)()
    load_context(DATA_DIR)

    after = process_rss_mb()
    assert after is not None, "could not read post-sweep process RSS"
    delta_ws = after[0] - baseline[0]
    print(f"[ram] full loader sweep RSS delta: {delta_ws:.2f} MB "
          f"(baseline {baseline[0]:.2f} MB, after {after[0]:.2f} MB, budget {RSS_DELTA_BUDGET_MB} MB)")
    assert delta_ws < RSS_DELTA_BUDGET_MB, (
        f"loader sweep RSS delta {delta_ws:.2f} MB >= budget {RSS_DELTA_BUDGET_MB} MB")


def test_frame_census_under_budget():
    """Every lib/data_cache.py loader (DATAFRAME_LOADERS) + lib/engine/
    substrates.load_context, fired on the REAL app/data -- summed
    DataFrame.memory_usage(deep=True) across every returned/held frame must
    stay under FRAME_BUDGET_MB. Runs AFTER the RSS-delta test above by
    definition order -- reuses whatever `st.cache_resource` already warmed,
    which is correct here: this test measures absolute frame size, not
    incremental cost, so cache state does not affect its result."""
    total = 0.0
    detail: dict[str, float] = {}
    for name in DATAFRAME_LOADERS:
        df = getattr(DC, name)()
        mb = df.memory_usage(deep=True).sum() / (1024 ** 2)
        detail[f"data_cache.{name}"] = mb
        total += mb

    ctx = load_context(DATA_DIR)
    for k, v in ctx.items():
        if isinstance(v, pd.DataFrame):
            mb = v.memory_usage(deep=True).sum() / (1024 ** 2)
            detail[f"ctx.{k}"] = mb
            total += mb

    print(f"[ram] frame census: {total:.2f} MB (budget {FRAME_BUDGET_MB} MB)")
    for k, mb in sorted(detail.items(), key=lambda kv: -kv[1]):
        print(f"  {k:<24} {mb:8.2f} MB")
    assert total < FRAME_BUDGET_MB, f"frame census {total:.2f} MB >= budget {FRAME_BUDGET_MB} MB"


def test_collab_parquets_never_loaded_whole():
    """Stream B (E4): the four Collaborate parquets (`collab_pairs`,
    `collab_pair_topics`, `collab_pair_fields`, `collab_topic_vols`) are gone
    from data_cache's public surface, and a single-pair duckdb pushdown never
    returns more than a few dozen rows -- never the 3.4-15.4M-row whole
    table. Measured 2026-09-02 for the Ifremer x NIOZ pair: collab_pairs 1
    row, collab_pair_topics 25, collab_topic_vols 25, collab_pair_fields 5 --
    all far under the COLLAB_PAIR_ROW_CAP sanity ceiling."""
    for attr in ("collab_pairs", "collab_pair_topics", "collab_pair_fields", "collab_topic_vols"):
        assert not hasattr(DC, attr), (
            f"lib.data_cache still exposes {attr}() -- Stream B was to delete this whole-table loader")

    ctx = {"data_dir": DATA_DIR}
    for table in ("collab_pairs", "collab_pair_topics", "collab_topic_vols", "collab_pair_fields"):
        df = CDL._collab_pair_slice(ctx, table, IFREMER_ID, NIOZ_ID)
        print(f"[ram] {table} slice for Ifremer x NIOZ: {len(df)} row(s)")
        assert len(df) < COLLAB_PAIR_ROW_CAP, (
            f"{table}: {len(df)} rows >= {COLLAB_PAIR_ROW_CAP} pair-slice sanity cap "
            f"(a whole-table read would return millions)")

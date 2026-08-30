"""
Centralized data loading with Streamlit caching (adapted from Lorraine Phase 2
Streamlit/lib/data_cache.py). Every path is __file__-relative, so the app runs
identically regardless of the launch cwd. `@st.cache_resource` loads each table once
and shares it across pages/reruns for the life of the process.

topics_all.parquet is 533 MB, mostly object-string columns not needed by the app's
substrate builders (BUILD_PLAN_2A.md §2) -- topics_all_slim() reads only the four
columns the engine actually consumes, so the full frame is never materialized here.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

TOPICS_ALL_SLIM_COLUMNS = ["inst_key", "topic_id", "share_frac", "vol_frac", "vol_full"]


@st.cache_resource
def index() -> pd.DataFrame:
    """Institution index: identity, type (patched), country, size, links. One row per institution."""
    return pd.read_parquet(DATA_DIR / "index.parquet")


@st.cache_resource
def fields() -> pd.DataFrame:
    """Field-grain shape/SI per institution x tree (L0 substrate)."""
    return pd.read_parquet(DATA_DIR / "fields.parquet")


@st.cache_resource
def subfields() -> pd.DataFrame:
    """Subfield-grain shape/SI per institution x tree (L1/L2f substrate)."""
    return pd.read_parquet(DATA_DIR / "subfields.parquet")


@st.cache_resource
def topics_dim() -> pd.DataFrame:
    """Topic taxonomy dimension: domain/field/subfield/topic names, frontier scores, is_excluded."""
    return pd.read_parquet(DATA_DIR / "topics_dim.parquet")


@st.cache_resource
def erc() -> pd.DataFrame:
    """ERC panel shares/mass/SI per institution (L4/L5 substrate)."""
    return pd.read_parquet(DATA_DIR / "erc.parquet")


@st.cache_resource
def sdg() -> pd.DataFrame:
    """SDG shares/ESI/mass per institution (L6/L7 substrate)."""
    return pd.read_parquet(DATA_DIR / "sdg.parquet")


@st.cache_resource
def impact_cells() -> pd.DataFrame:
    """Bootstrap PP(top10%) cells with CI, keyed by institution x subfield x tree x floor."""
    return pd.read_parquet(DATA_DIR / "impact_cells.parquet")


@st.cache_resource
def topics_all_slim() -> pd.DataFrame:
    """topics_all.parquet column-subsetted to what the engine needs (L3/F1 substrate).

    The full frame is 533 MB, mostly object strings (BUILD_PLAN_2A.md §2) -- reading only
    these four columns keeps this the one place the app ever touches that file.
    """
    return pd.read_parquet(DATA_DIR / "topics_all.parquet", columns=TOPICS_ALL_SLIM_COLUMNS)


@st.cache_resource
def doctype_by_year() -> pd.DataFrame:
    """Document-type volumes per institution x year (R1 artefact, BUILD_PLAN_2A.md
    S9.2 L24; built by V3/pipeline/09c_doctype_by_year.py, stream R-S5).

    Columns: `inst_key int32, institution_id str, year int16, doc_type
    category{article,book,book-chapter,letter,review}, vol_full int32,
    vol_frac float32`.

    Grain: institution x year x doc_type and **SPARSE** -- 141,182 rows, NOT a
    dense 7,557 x 6 x 5 cube: a cell with zero works has NO row at all (four
    institutions even lack every year but 2020). Never assume presence; the
    yearly-breakdown consumer fills a missing (year, type) cell with zero
    itself, so a series absent for a seed still renders its empty group
    (VIZ_SPEC S2.14 "a missing year is data").

    `doc_type` is a CATEGORY dtype -- cast `.astype(str)` before any `.map()`
    (Assembly Line gotcha: `.map(...).fillna(...)` raises on a categorical).
    """
    return pd.read_parquet(DATA_DIR / "doctype_by_year.parquet")


@st.cache_resource
def collab_pairs() -> pd.DataFrame:
    """ALL a<b indexed-institution pairs, 2020-2025, floor 1 (2BR P2/2B-R-15/
    A1; `pipeline/15_collab_pass.py`). Columns: `a, b` (institution_id,
    lexicographic a<b), `copubs_2020..copubs_2025, copubs_total` (full
    counting), `rank_in_a, rank_in_b` (dense rank by copubs_total, computed
    BEFORE any floor). 3,581,332 rows, 26.2 MB."""
    return pd.read_parquet(DATA_DIR / "collab_pairs.parquet")


@st.cache_resource
def collab_pair_topics() -> pd.DataFrame:
    """Top-20 joint topics (primary topic only) per pair with `copubs_total
    >= 3` (2BR P2/2B-R-15/A2). Columns: `a, b, topic_id, vol_w1 (2020-2022),
    vol_w2 (2023-2024), vol_2025, vol_total, sdg_tagged_n, erc_top_panel,
    erc_top_panel_n, erc_labelled_n` (the three erc_* columns are PAIR-LEVEL,
    repeated on every row of the pair). 12,352,398 rows, 58.8 MB."""
    return pd.read_parquet(DATA_DIR / "collab_pair_topics.parquet")


@st.cache_resource
def sdg_fields() -> pd.DataFrame:
    """Institution x sdg x field x tree, fractional SDG-tagged mass, full
    2020-2025 run window (2BR P3/2B-R-15/A7; `pipeline/16_crosses.py`).
    `field_id == -1` is the explicit 'untopiced' residual row (a work with
    SDG-tagged mass but no primary topic, ~0.14% of the corpus) -- never
    silently folded into a real field. 1,736,925 rows, 5.9 MB."""
    return pd.read_parquet(DATA_DIR / "sdg_fields.parquet")


@st.cache_resource
def sdg_year() -> pd.DataFrame:
    """Institution x sdg x year (2020-2025), fractional SDG-tagged mass,
    tree-independent (2BR P3/2B-R-15/A7). SUM over all 6 years equals
    `sdg.parquet`'s own `mass` for the same (institution, sdg) -- confirming
    `sdg.parquet`'s basis is the full 6-year run window, not the 5-year
    2020-2024 core window. 427,687 rows, 1.7 MB."""
    return pd.read_parquet(DATA_DIR / "sdg_year.parquet")


@st.cache_resource
def impact_fields() -> pd.DataFrame:
    """Institution x field (26) x tree x floor bootstrap PP(top10%) cells
    (2BR P3/2B-R-15/A8; `pipeline/16_crosses.py`) -- the SAME per-work
    top-10% flag as `impact_cells.parquet` (subfield grain), rolled up to
    field grain. Ships all 3 trees and floors {10, 30}. 164,477 rows, 3.1 MB."""
    return pd.read_parquet(DATA_DIR / "impact_fields.parquet")


@st.cache_resource
def manifest() -> dict:
    """Deploy-time MANIFEST.json if Stream C's ops/deploy.py has run, else the pre-staged
    source_manifest.json (BUILD_PLAN_2A.md Data flow: MANIFEST/source_manifest fallback)."""
    path = DATA_DIR / "MANIFEST.json"
    if not path.is_file():
        path = DATA_DIR / "source_manifest.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

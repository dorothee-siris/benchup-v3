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
def manifest() -> dict:
    """Deploy-time MANIFEST.json if Stream C's ops/deploy.py has run, else the pre-staged
    source_manifest.json (BUILD_PLAN_2A.md Data flow: MANIFEST/source_manifest fallback)."""
    path = DATA_DIR / "MANIFEST.json"
    if not path.is_file():
        path = DATA_DIR / "source_manifest.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

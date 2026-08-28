"""
Shared loader for the D1 A/B prototypes (throwaway; design-system/ab/** only --
never imported by lib/ranked.py or anything shipped). Caches the engine load
per prototype process with @st.cache_resource (manager-verified pattern,
BUILD_PLAN_2A.md Stream D1 brief).
"""
from __future__ import annotations

import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

import streamlit as st  # noqa: E402

from lib import engine as E  # noqa: E402

SEED = "I40413290"  # University of Gdansk (BUILD_PLAN_2A.md Stream D1 brief)


@st.cache_resource
def load_rankings():
    ctx = E.load_context(str(APP_ROOT / "data"))
    subs = E.build_substrates(ctx)
    r = E.rank_all(ctx, subs, SEED)
    return ctx, r

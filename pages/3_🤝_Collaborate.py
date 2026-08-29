"""
The Collaborate tab (Sprint 2 Phase 2B, Stream L). Deliberately thin, same
shape as pages/1_<magnifying-glass>_Find.py: page config, the basket re-seed
every page needs (lib/state.py's own docstring), then the whole view, which
lives in lib/views_collab.py.
"""
from __future__ import annotations

import streamlit as st

from lib import state
from lib import views_collab

st.set_page_config(page_title="BenchUp v3 - Collaborate", layout="wide")
state.ensure()
views_collab.render()

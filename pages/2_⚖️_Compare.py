"""
The Compare tab (Sprint 2 Phase 2B, Stream C). Deliberately thin, the same
shape as pages/1_<magnifying-glass>_Find.py and pages/3_<handshake>_Collaborate.py:
page config, the basket re-seed every page needs (lib/state.py's own docstring),
then the whole view, which lives in lib/views_compare.py.
"""
from __future__ import annotations

import streamlit as st

from lib import state
from lib import views_compare

st.set_page_config(page_title="BenchUp v3 - Compare", layout="wide")
state.ensure()
views_compare.render()

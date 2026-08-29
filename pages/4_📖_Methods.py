"""
The Methods page (Sprint 2 Phase 2B, Stream M). Deliberately thin, same shape
as pages/1_(magnifying-glass)_Find.py: page config, the basket re-seed every
page needs (lib/state.py's own docstring), then the whole view, which lives
in lib/views_methods.py.

Filename stays `4_(open-book)_Methods.py` (manager decision, BUILD_PLAN_2B.md
S3 row M / evals/wind_tunnel_2B.md claim on filenames): Streamlit derives the
sidebar nav label from the FILE name, so this is what keeps the short nav
label and the deep links stable while the EDITORIAL label ("How it is
built", copy.NAV["METHODS_LABEL"]) appears as this page's own title and on
the Menu card instead.
"""
from __future__ import annotations

import streamlit as st

from lib import state
from lib import views_methods

st.set_page_config(page_title="BenchUp v3 - How it is built", layout="wide")
state.ensure()
views_methods.render()

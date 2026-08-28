"""
Landing page. Nav cards are enumerated from pages/ at runtime (Lorraine Phase 2 Menu.py
pattern): a dimension is a live st.page_link once a file matching its word exists under
pages/, otherwise it renders greyed with "Phase 2B" -- so this file never hardcodes a
filename that a later stream has not built yet.
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from lib import state
from lib.app_config import CFG
from lib.data_cache import index, manifest

st.set_page_config(page_title="BenchUp v3", layout="wide")
state.ensure()

st.title("BenchUp v3")
st.caption(
    "A thematic benchmarking tool for European research institutions: find who resembles "
    "a given institution, compare institutions side by side, and explore collaboration "
    "patterns -- across independent lenses, never a single ranking."
)
st.markdown("**Candidates for review, not a verdict.**")

st.markdown("---")

PAGES_DIR = Path(__file__).parent / "pages"
_existing_pages = [p.name for p in PAGES_DIR.glob("*.py")] if PAGES_DIR.is_dir() else []

DIMENSIONS = [
    ("Find", "Search for an institution and see who resembles it across independent lenses."),
    ("Compare", "Place institutions side by side across the same lenses."),
    ("Collaborate", "Explore partnership and co-authorship patterns."),
]

with st.container(key="nav_cards"):
    cols = st.columns(len(DIMENSIONS), gap="medium")
    for col, (word, blurb) in zip(cols, DIMENSIONS):
        match = next((fn for fn in _existing_pages if word.lower() in fn.lower()), None)
        with col:
            with st.container(border=True, key=f"nav_card_{word.lower()}"):
                if match:
                    st.markdown(f"**{word}**")
                    st.caption(blurb)
                    st.page_link(f"pages/{match}", label=f"Open {word}")
                else:
                    st.markdown(f":grey[**{word}**]")
                    st.caption(blurb)
                    st.caption(":grey[Phase 2B]")

st.markdown("---")

_manifest = manifest()
_snapshot_label = _manifest.get("snapshot") or CFG.get("snapshot", "n/a")
_generated_at = _manifest.get("generated_at", "n/a")
st.caption(
    f"Snapshot: {_snapshot_label} (generated {_generated_at}) -- {len(index())} "
    "institutions in the index."
)

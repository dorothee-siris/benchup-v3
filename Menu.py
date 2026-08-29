"""
Landing page. Nav cards are enumerated from pages/ at runtime (Lorraine Phase 2 Menu.py
pattern): a dimension is a live st.page_link once a file matching its word exists under
pages/, otherwise it renders greyed with "Phase 2B" -- so this file never hardcodes a
filename that a later stream has not built yet.

Stream M (Phase 2B, 2B-10): four cards in narrative order (Find -> Compare -> Collaborate
-> Methods), editorial labels/blurbs from copy.NAV rather than the bare dimension word.
The MATCH word (used only to find the live page file under pages/, exactly the 2A
mechanism) stays the plain word -- it must be a substring of the file's own name
("1_(magnifying-glass)_Find.py", "4_(open-book)_Methods.py", ...), which an editorial
label like "How it is built" is not. C and L (Compare/Collaborate pages) may not exist
yet when this runs: the existing exists-under-pages/ check handles that exactly as it did
for Compare/Collaborate in 2A, unchanged here.
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from lib import copy, state
from lib.app_config import CFG
from lib.data_cache import index, manifest

st.set_page_config(page_title="BenchUp v3", layout="wide")
state.ensure()

st.title(copy.NAV["MENU_HEADER"])
st.caption(copy.NAV["MENU_INTRO"])
st.markdown(f"**{copy.VERDICT_LINE}**")

st.markdown("---")

PAGES_DIR = Path(__file__).parent / "pages"
_existing_pages = [p.name for p in PAGES_DIR.glob("*.py")] if PAGES_DIR.is_dir() else []

DIMENSIONS = [
    ("Find", copy.NAV["FIND_LABEL"], copy.NAV["FIND_BLURB"]),
    ("Compare", copy.NAV["COMPARE_LABEL"], copy.NAV["COMPARE_BLURB"]),
    ("Collaborate", copy.NAV["COLLAB_LABEL"], copy.NAV["COLLAB_BLURB"]),
    ("Methods", copy.NAV["METHODS_LABEL"], copy.NAV["METHODS_BLURB"]),
]

with st.container(key="nav_cards"):
    cols = st.columns(len(DIMENSIONS), gap="medium")
    for col, (word, label, blurb) in zip(cols, DIMENSIONS):
        match = next((fn for fn in _existing_pages if word.lower() in fn.lower()), None)
        with col:
            with st.container(border=True, key=f"nav_card_{word.lower()}"):
                if match:
                    st.markdown(f"**{label}**")
                    st.caption(blurb)
                    st.page_link(f"pages/{match}", label=f"Open {label}")
                else:
                    st.markdown(f":grey[**{label}**]")
                    st.caption(blurb)
                    st.caption(":grey[Phase 2B]")

st.markdown("---")

_manifest = manifest()
_snapshot_label = _manifest.get("snapshot") or CFG.get("snapshot", "n/a")
_generated_at = (_manifest.get("source_manifest_generated_at") or _manifest.get("generated_at")
                 or _manifest.get("deployed_at") or "n/a")  # deploy.py MANIFEST vs source_manifest keys (manager fix 2026-08-29)
st.caption(
    f"Snapshot: {_snapshot_label} (generated {_generated_at}) -- {len(index())} "
    "institutions in the index."
)

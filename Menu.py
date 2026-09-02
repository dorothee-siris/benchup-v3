"""
Landing page. Nav cards are enumerated from pages/ at runtime (Lorraine Phase 2 Menu.py
pattern): a dimension is a live st.page_link once a file matching its word exists under
pages/.

Stream M (Phase 2B, 2B-10): four cards in narrative order (Find -> Compare -> Collaborate
-> Methods), editorial labels/blurbs from copy.NAV rather than the bare dimension word.
The MATCH word (used only to find the live page file under pages/, exactly the 2A
mechanism) stays the plain word -- it must be a substring of the file's own name
("1_(magnifying-glass)_Find.py", "4_(open-book)_Methods.py", ...), which an editorial
label like "How it is built" is not.

2D (stream MT4, press audit J2): the earlier greyed-fallback branch for a dimension whose
page file does not exist yet is GONE. All four page files have been stable for three
phases running, so the fallback's own literal build-phase name ("Phase 2B") sat one page
rename or deploy hiccup away from being the first thing a reader saw on a broken card --
a real risk with no offsetting benefit once the app itself is this settled. A card whose
page file ever went missing again would still render its label and blurb, just with no
live link, rather than a stale internal phase name.
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from lib import copy, selection, state
from lib.data_cache import index, manifest
from lib.exports import data_date_label
from lib.palette import NA_MARK

SEP = "·"   # middle dot, the separator every other caption in the app uses

st.set_page_config(page_title="BenchUp v3", layout="wide")
state.ensure()
# 2BR3 SEL, plan §1 item 1: the shared sidebar search + basket lives on every
# page, landing page included -- a reader can start shortlisting before ever
# opening Find.
selection.render_sidebar()

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
                st.markdown(f"**{label}**")
                st.caption(blurb)
                if match:
                    st.page_link(f"pages/{match}", label=f"Open {label}")

st.markdown("---")

# 2B-R-12: the snapshot LABEL ("august_2026") and its generated timestamp are
# both gone from the page -- an internal artefact name and a machine stamp told
# a reader nothing they could act on. What replaces them is what they were
# standing in for: how many institutions the index holds, and the date the data
# was harvested. Both are read at run time (the index length, the manifest's own
# source stamp) so no digit is typed here.
_manifest = manifest()
_stamp = (_manifest.get("source_manifest_generated_at") or _manifest.get("generated_at")
          or _manifest.get("deployed_at"))  # deploy.py MANIFEST vs source_manifest keys
st.caption(copy.FIND["DATA_CAPTION"].format(
    n_institutions=f"{len(index()):,}", sep=SEP,
    date=data_date_label(_stamp, NA_MARK)))

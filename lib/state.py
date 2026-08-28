"""
Cross-page session state: the basket, and the persistence kwarg every keyed sidebar
widget in other streams must carry.

Lorraine Phase 2 lib/controls.py lines 184-222 (read verbatim before touching this file):
a widget's value resets to its coded default on every page switch unless the widget itself
is given `persist_state="session"` -- Streamlit's per-page widget-id hashing means a plain
session_state write-through does not reliably reattach across more than one page hop.
`persist_state` is documented on selectbox/checkbox/radio/multiselect/slider/text widgets,
but NOT on buttons (BUILD_PLAN_2A.md §2) -- so the basket, which is built by button clicks,
is deliberately NOT a widget at all: it is a plain `st.session_state["basket"]` list, a
non-widget key that Streamlit already shares across pages by default (no persist_state
exists for it, and none is needed).
"""
from __future__ import annotations

import streamlit as st

# Every keyed sidebar widget other streams build (tree, basis, depth, C1, L7, post-filters)
# must pass this as **PERSIST to survive a page switch: st.selectbox(..., key="tree",
# **state.PERSIST).
PERSIST = dict(persist_state="session")


def ensure() -> None:
    """setdefault the basket. Call at the top of every page, before reading st.session_state["basket"]."""
    st.session_state.setdefault("basket", [])


def add(iid: str) -> None:
    ensure()
    if iid not in st.session_state["basket"]:
        st.session_state["basket"].append(iid)


def remove(iid: str) -> None:
    ensure()
    if iid in st.session_state["basket"]:
        st.session_state["basket"].remove(iid)


def items() -> list[str]:
    ensure()
    return st.session_state["basket"]


def clear() -> None:
    ensure()
    st.session_state["basket"].clear()

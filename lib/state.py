"""
Cross-page session state: the basket, and the persistence kwarg every keyed sidebar
widget in other streams must carry.

Lorraine Phase 2 lib/controls.py lines 184-222 (read verbatim before touching this file):
a widget's value resets to its coded default on every page switch unless the widget itself
is given `persist_state="session"` -- Streamlit's per-page widget-id hashing means a plain
session_state write-through does not reliably reattach across more than one page hop.
`persist_state` is documented on selectbox/checkbox/radio/multiselect/slider/text widgets,
but NOT on buttons (BUILD_PLAN_2A.md S2) -- so the basket, which is built by button clicks,
is deliberately NOT a widget at all: it is a plain `st.session_state["basket"]` list, a
non-widget key that Streamlit already shares across pages by default (no persist_state
exists for it, and none is needed).

2B-8 (Sprint 2 Phase 2B, Stream S): Compare reads N up to BASKET_CAP institutions off this
same list, so the basket now enforces a cap and carries a stable USER order (`move`/
`reorder`) distinct from any table rank -- Compare/Collaborate mirror that order, they never
re-sort the compared set themselves.
"""
from __future__ import annotations

import streamlit as st

from lib.app_config import CFG

# Every keyed sidebar widget other streams build (tree, basis, depth, C1, L7, post-filters)
# must pass this as **PERSIST to survive a page switch: st.selectbox(..., key="tree",
# **state.PERSIST).
PERSIST = dict(persist_state="session")

# 2B-8: Compare is 2-6 institutions (BUILD_PLAN_2B.md decision 2B-1). `config.yaml` carries
# an ADDITIVE `basket_cap` key (`# 2B-8`) so the number lives with the rest of the ruled
# config rather than only here; a config snapshot that predates that key (an older deploy,
# a stray test fixture) falls back to this module constant instead of raising -- BASKET_CAP
# is read once at import time, same as every other CFG-derived module constant in this app.
BASKET_CAP: int = int(CFG.get("basket_cap", 6))

# 2BR (A13/2B-R-4): Compare itself is capped at 3, hard -- separate from the
# 6-slot basket (a shortlist) above. Config-backed the same way, additive
# `compare_cap` key in config.yaml, same import-time-constant convention.
COMPARE_CAP: int = int(CFG.get("compare_cap", 3))


def ensure() -> None:
    """setdefault the basket. Call at the top of every page, before reading st.session_state["basket"]."""
    st.session_state.setdefault("basket", [])


def add(iid: str) -> bool:
    """Append `iid` to the basket. Returns True when the basket now contains `iid` --
    whether because it was just appended or because it was already present (a repeat add
    is a harmless no-op, not a failure) -- and False only when `iid` is NEW and the basket
    is already at BASKET_CAP, in which case NOTHING changes: never raises, never silently
    drops. Callers (lib/views_find.py's add sites) show `copy.FIND["BASKET_FULL"]` on a
    False return; this function itself carries no Streamlit output, so it stays plain and
    unit-testable (tests/test_selection.py, tests/test_pages.py)."""
    ensure()
    basket = st.session_state["basket"]
    if iid in basket:
        return True
    if len(basket) >= BASKET_CAP:
        return False
    basket.append(iid)
    return True


def is_full() -> bool:
    """True once the basket holds BASKET_CAP institutions -- a read-only check other
    streams (Compare's own add-by-search) can use to disable a control before the click
    rather than after it."""
    ensure()
    return len(st.session_state["basket"]) >= BASKET_CAP


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


def move(iid: str, direction: int) -> None:
    """Swap `iid` with its neighbour one step earlier (`direction < 0`) or later
    (`direction > 0`) in the basket's own list -- the stable USER order 2B-8's Compare/
    Collaborate mirrors read (never a table rank, never alphabetical). A no-op when `iid`
    is absent or already sits at the edge `direction` points towards."""
    ensure()
    basket = st.session_state["basket"]
    if iid not in basket:
        return
    i = basket.index(iid)
    j = i + (1 if direction > 0 else -1)
    if 0 <= j < len(basket):
        basket[i], basket[j] = basket[j], basket[i]


def reorder(new_order: list[str]) -> None:
    """Replace the basket's order wholesale with `new_order` (e.g. a drag-reordered list
    from Compare). Only ids ALREADY in the basket are kept from `new_order` -- reordering
    is not a side door into the cap or the add/remove contract -- and any basket id missing
    from `new_order` is appended at the end, so an item is never lost silently."""
    ensure()
    basket = st.session_state["basket"]
    current = set(basket)
    ordered = [iid for iid in new_order if iid in current]
    ordered += [iid for iid in basket if iid not in ordered]
    basket[:] = ordered

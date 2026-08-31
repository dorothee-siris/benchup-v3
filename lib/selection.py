"""
app/lib/selection.py -- basket/query-param parsing and deep-link helpers
(Sprint 2 Phase 2B, Stream S; BUILD_PLAN_2B.md decision 2B-8, S4, amendment A11).

2BR3 (Phase 2B-R3, Stream SEL, plan §3 SEL / ruling 1): this module also now
owns the ONE shared sidebar search + basket component (`render_sidebar`,
called by every page: Menu.py and lib/views_find.py this wave, lib/
views_compare.py and lib/views_collab.py once VC/VL rewire in wave 2) and the
slots API (`slots_row`) Compare/Collaborate build their side-by-side pickers
from. Those two functions DO import Streamlit at module scope (this file is
no longer Streamlit-free end to end) -- every function that predates them
stays a plain, unit-testable function taking its Streamlit-sourced arguments
in (`known_ids`, `params`, a basket list), never reaching for `st.*` itself,
so `tests/test_selection.py` keeps testing most of this file with no running
app. `read_query` remains the thin wrapper that touches `st.query_params`
directly; `render_sidebar`/`slots_row` are the two NEW touchpoints, and their
own docstrings say so.

Every function below `render_sidebar` up to it is plain Python -- no
Streamlit import, no CFG read, no data-file read -- except `read_query`, the
ONE thin wrapper that actually touches `st.query_params`; its import is
LOCAL to that function so the rest of this module stays importable and
unit-testable with no Streamlit runtime (the scope fence on this file,
BUILD_PLAN_2B.md S3).

A11: on Streamlit 1.61.1, `st.query_params.get("compare")` collapses
repeated `?compare=A&compare=B` keys into ONE comma-joined string ("A,B"),
the LAST such key wins if the URL repeats the key outright -- Streamlit's
own behaviour, not this module's. `parse_ids` accepts that comma-joined
shape directly (and, for testability and for callers that already hold a
Python list -- e.g. `state.items()` -- a list too).

An id that the caller's `known_ids` does not recognise (a stale link, a
retired institution, a typo) is DROPPED, never raised on and never kept: a
shared link that names one bad id still opens on the rest, and the dropped
id is reported back so a caller can disclose it rather than fail silently.

2BR (A13/2B-R-4): Compare's own cap is `state.COMPARE_CAP` (3, hard), separate
from the 6-slot `state.BASKET_CAP` -- `compare_ids` below is cap-generic (the
caller passes whichever cap applies) and now ALSO reports how many ids were
cut by the cap, so a page can render 'showing 3 of {n}, capped'. Neither this
module nor `state.py` filters on `index.pool_excluded` -- 2B-R-3/A6 rules that
flag out of CANDIDATE POOLS only; a Compare/Collaborate id is a real,
already-picked institution, so `known_ids` here must be the FULL index id set
(pool-excluded ids included), never a pool-filtered subset.
"""
from __future__ import annotations


def parse_ids(value, known_ids) -> tuple[list[str], list[str]]:
    """`value` is a comma-joined string or an iterable of ids. Returns
    `(kept, dropped)`: `kept` is de-duplicated, first-seen order, filtered
    to `known_ids`; `dropped` is every id that failed that filter, same
    order. `None` or an empty string yields `([], [])`."""
    if not value:
        return [], []
    if isinstance(value, str):
        raw = [v.strip() for v in value.split(",")]
    else:
        raw = [str(v).strip() for v in value]
    known = set(known_ids)
    seen: set[str] = set()
    kept: list[str] = []
    dropped: list[str] = []
    for iid in raw:
        if not iid or iid in seen:
            continue
        seen.add(iid)
        (kept if iid in known else dropped).append(iid)
    return kept, dropped


def parse_query(params, known_ids) -> dict:
    """`params` is anything with a `.get` (a plain dict in tests, or
    `st.query_params` itself) that the CALLER has already obtained -- this
    function touches no Streamlit API, only `read_query` below does.

    Returns `{"compare": [...], "pair": (a, b) | None, "dropped": [...]}`.
    `pair` needs BOTH of `?pair=`'s two ids to survive the `known_ids`
    filter, else `None` -- a half-valid pair link is not a page to render.
    `dropped` merges both params' casualties, de-duplicated, `compare`'s
    order first."""
    compare_kept, compare_dropped = parse_ids(params.get("compare"), known_ids)
    pair_kept, pair_dropped = parse_ids(params.get("pair"), known_ids)
    pair = (pair_kept[0], pair_kept[1]) if len(pair_kept) >= 2 else None
    dropped = list(compare_dropped)
    for d in pair_dropped:
        if d not in dropped:
            dropped.append(d)
    return {"compare": compare_kept, "pair": pair, "dropped": dropped}


def read_query(known_ids) -> dict:
    """The ONE Streamlit touchpoint in this module: reads `st.query_params`
    live and hands it straight to `parse_query`. Local import so every other
    function in this file stays free of a Streamlit dependency."""
    import streamlit as st

    return parse_query(st.query_params, known_ids)


def compare_ids(basket, query, known_ids, cap: int) -> list[str]:
    """2B-8: the Compare id set on first load. `query` wins (a shared link
    should show what it names), the basket fills any remaining slots; both
    are re-validated against `known_ids` and de-duplicated across each
    other, in QUERY-then-BASKET order, capped at `cap`. `basket` and `query`
    each accept either shape `parse_ids` accepts (comma string or list).

    UNCHANGED return shape (plain list) -- the already-shipped Phase 2B
    `lib/views_compare.py` calls this directly and iterates the result as a
    flat id list; 2BR's `compare_ids_capped` below is the ADDITIVE sibling
    that also reports the truncation count, for the 2B-R Compare rebuild
    (Stream CP) to adopt without breaking the page that ships until then."""
    q_kept, _ = parse_ids(query, known_ids)
    b_kept, _ = parse_ids(basket, known_ids)
    seen: set[str] = set()
    out: list[str] = []
    for iid in (*q_kept, *b_kept):
        if iid in seen:
            continue
        seen.add(iid)
        out.append(iid)
        if len(out) >= cap:
            break
    return out


def compare_ids_capped(basket, query, known_ids, cap: int) -> tuple[list[str], int]:
    """2BR A13/2B-R-4: SAME query-then-basket, deduplicated resolution as
    `compare_ids`, but ALSO reports how many additional deduplicated, known
    ids existed beyond `cap` -- `state.COMPARE_CAP` (3, hard) is the cap the
    2B-R Compare page passes. Returns `(ids, n_truncated)`: `ids` is capped
    at `cap`; `n_truncated` is 0 when nothing was cut. A page uses
    `n_truncated` to render its own 'showing 3 of {3 + n_truncated}, capped'
    copy line (2B-R-4) rather than this module typing that string."""
    q_kept, _ = parse_ids(query, known_ids)
    b_kept, _ = parse_ids(basket, known_ids)
    seen: set[str] = set()
    combined: list[str] = []
    for iid in (*q_kept, *b_kept):
        if iid in seen:
            continue
        seen.add(iid)
        combined.append(iid)
    return combined[:cap], max(0, len(combined) - cap)


def pair_from(ids, a: str | None = None, b: str | None = None):
    """The Collaborate pair picker's default. Returns `(a, b)` when both are
    given, distinct, and present in `ids`; otherwise the first two of `ids`
    in `ids`'s own order. `None` when fewer than two candidates exist
    either way (a compared set of one, or an empty one)."""
    if a and b and a != b and a in ids and b in ids:
        return (a, b)
    if len(ids) >= 2:
        return (ids[0], ids[1])
    return None


def deeplink(kind: str, ids) -> str:
    """The query-string half of a shareable link: `deeplink("compare", [I1,
    I2])` -> `"?compare=I1,I2"`, `deeplink("pair", [A, B])` -> `"?pair=A,B"`.
    The exact shape `parse_query` (via `read_query`) reads back -- this
    module owns both ends of the round trip."""
    return f"?{kind}=" + ",".join(ids)


# ============================================================================
# 2BR3 SEL (plan §3 SEL / ruling 1): the shared sidebar search + basket, and
# the slots API. See the module docstring for the Streamlit-import note.
# ============================================================================

SEARCH_TOP_N = 10  # WT_2BR3.md task 1 verdict: a SHORT list/dropdown, never
                    # the raw 7,557-option selectbox (relevance-refuted, not
                    # speed-refuted -- lib/search.py's own token-ranked engine
                    # feeds this instead).

SLOT_EMPTY = ""  # sentinel "no pick" option for a slot selectbox -- every real
                  # institution_id in this app is an OpenAlex "I..." string, so
                  # an empty string can never collide with one.


def hit_label(hit: dict) -> str:
    """name . country (by NAME) . type . size -- the one result-row label the
    shared sidebar search uses, moved here from the old per-view `_hit_label`
    (`lib/views_find.py`, R1/L22) so Find and, once wave 2 rewires them,
    Compare/Collaborate all read one row format instead of three near-copies.
    `hit` is one dict from `lib.search.search`'s own return shape."""
    from lib import countries
    from lib.palette import NA_MARK

    total = hit.get("total_full_2020_2024")
    size = NA_MARK if total is None or total != total else f"{total:,.0f}"  # NaN != NaN
    return (f"{hit['display_name']} · {countries.name(str(hit['country_code']))} · "
           f"{hit['type']} · {size}")


def render_sidebar() -> None:
    """The ONE sidebar search + basket, live on every page (plan §1 item 1):
    a text search feeding `lib.search`'s existing token-ranked engine (WT
    2BR3 task 1: relevance-superior to a raw 7,557-option selectbox) into a
    SHORT list of up to SEARCH_TOP_N hits, each with its OWN one-click add
    button -- never the old two-step "pick in a selectbox, then click a
    separate Add button" (`lib/views_find.py`'s retired `_sidebar_basket`,
    WT_2BR3.md §5.7 views_find.py:370-398). The basket underneath lists every
    added institution with an always-visible remove control (state.BASKET_CAP
    is enforced by `state.add` itself; this function only surfaces the
    message on a blocked add).

    2BR3 wave-1 note: Compare and Collaborate still render their OWN sidebar
    basket widgets this wave (their pre-2BR3 code, kept RUNNING as a
    deprecation shim so those two pages stay importable against the old flow)
    -- only Menu.py and lib/views_find.py call this function until wave 2
    (VC/VL) replaces those call sites with it too."""
    import streamlit as st

    from lib import copy, state
    from lib.data_cache import index
    from lib.search import build_search_index, search

    sb = st.sidebar
    idx_df = index()
    search_idx = build_search_index(idx_df)  # cheap (pandas, no I/O); called
                                              # once per script run like every
                                              # other page-level rebuild here

    sb.header(copy.FIND["SIDEBAR_SEARCH_HEADER"])
    query = sb.text_input(copy.FIND["SEED_SEARCH_LABEL"], key="sidebar_search_query",
                          **state.PERSIST)
    hits = search(query, search_idx, k=SEARCH_TOP_N) if query else []
    if query and not hits:
        sb.caption(copy.SEARCH_EMPTY_TEMPLATE.format(query=query))
    basket = state.items()
    for hit in hits:
        iid = hit["id"]
        c1, c2 = sb.columns([4, 1])
        c1.caption(hit_label(hit))
        already = iid in basket
        if c2.button(copy.FIND["SIDEBAR_ADD_BUTTON"], key=f"sidebar_add_{iid}",
                    help=copy.FIND["SIDEBAR_ADD_HELP"], disabled=already):
            if state.add(iid):
                st.rerun()
            else:
                sb.warning(copy.FIND["BASKET_FULL"].format(cap=state.BASKET_CAP))

    sb.divider()
    sb.header(copy.FIND["BASKET_HEADER"])
    items = state.items()
    sb.caption(copy.FIND["BASKET_COUNT"].format(n=len(items), cap=state.BASKET_CAP))
    if not items:
        sb.caption(copy.FIND["BASKET_EMPTY"])
        return
    names = idx_df.set_index("institution_id")["display_name"]
    for iid in list(items):
        c1, c2 = sb.columns([4, 1])
        c1.write(str(names.get(iid, iid)))
        if c2.button(copy.FIND["BASKET_REMOVE"], key=f"sidebar_rm_{iid}",
                    help=copy.FIND["BASKET_REMOVE"]):
            state.remove(iid)
            st.rerun()
    if sb.button(copy.FIND["BASKET_CLEAR"], key="sidebar_basket_clear"):
        state.clear()
        st.rerun()


def _slot_key(view: str, i: int) -> str:
    return f"slot_{view}_{i}"


def _slot_param(view: str) -> str:
    """Which existing deep-link query param a view's slots hydrate from and
    write back to: 'pair' for Collaborate (the existing ?pair= shape, 2
    slots), 'compare' for every other slotted view -- plan §1.1 'existing
    param names kept'."""
    return "pair" if view == "collab" else "compare"


def resolve_slot_hydration(param_value, known_ids, n: int) -> list[str]:
    """The pure rule behind `slots_row`'s first-load hydration: `param_value`
    (a raw `?compare=`/`?pair=` query value, or None) parsed and filtered
    against `known_ids` exactly like `parse_ids`, kept to the first `n`, and
    padded with SLOT_EMPTY -- exactly the list `slots_row` seeds each slot's
    session state to on a fresh session. Split out from `slots_row` so the
    hydration RULE is unit-testable with no Streamlit runtime; `slots_row`
    itself (session-state writes, the basket add, the widgets, the URL
    write-back) is exercised end to end by an AppTest/Playwright proof."""
    kept, _ = parse_ids(param_value, known_ids)
    kept = kept[:n]
    return kept + [SLOT_EMPTY] * (n - len(kept))


def slots_row(view: str, n: int) -> list[str | None]:
    """`slots_row(view, n)` -> a list of length `n`, one institution_id or
    `None` per slot (plan §3 SEL). Renders `n` side-by-side `st.selectbox`
    slots whose OPTIONS are the current basket only (plus an empty choice) --
    views never search from here, they only pick from what the sidebar
    already basketed. Each slot's pick persists in session state per (view,
    index), so Compare's 3 slots and Collaborate's 2 keep independent
    assignments even though both draw from the SAME basket, and both survive
    a page switch via `state.PERSIST` like every other keyed widget in this
    app.

    Deep-link hydration runs ONCE per (view) per session: on the first call,
    the view's own existing query param (`?compare=` for every view except
    Collaborate's `?pair=`, plan §1.1 'existing param names kept') is parsed
    against the FULL institution index, its ids are folded into the basket
    (`state.add` -- a shared link opens correctly even for a reader whose
    basket is empty) and become that first run's slot picks; every later run
    reads session state only, so a reader's own later edit to a slot is never
    fought by the URL. After every render, the resolved (non-empty) picks are
    written back to the SAME param, so the address bar always names the
    CURRENT slots; an all-empty set of slots removes the param rather than
    writing an empty one.

    Enforces and messages the two caps named in plan §1.6: Compare needs at
    least two FILLED slots to have anything to render (`st.info`, never a
    hard stop -- the caller still gets its `n`-length list back and decides
    what "render" means with fewer); Collaborate always renders exactly 2
    selectboxes (the caller passes `n=2`) and this function's own message
    names the "pick two" requirement the same way. The basket's own
    state.BASKET_CAP is `state.add`'s concern, not this function's.

    STREAMLIT TOUCHPOINT: this function follows the same "set session_state
    directly, then instantiate the widget with `key=` alone (no `index=`)"
    pattern `lib/views_collab.py::_pair_picker` already uses (a `key` whose
    session_state is set AND an `index=` argument on the SAME widget call is
    a Streamlit conflict) -- never add an `index=`/`value=` kwarg to the
    selectbox call below without re-reading this note."""
    import streamlit as st

    from lib import copy, state
    from lib.data_cache import index

    param = _slot_param(view)
    hydrated_key = f"_slots_hydrated_{view}"
    idx_df = index()

    if not st.session_state.get(hydrated_key):
        known_ids = set(idx_df["institution_id"])
        seeded = resolve_slot_hydration(st.query_params.get(param), known_ids, n)
        for iid in seeded:
            if iid != SLOT_EMPTY:
                state.add(iid)
        for i in range(n):
            st.session_state[_slot_key(view, i)] = seeded[i]
        st.session_state[hydrated_key] = True

    basket = state.items()
    options = [SLOT_EMPTY, *basket]
    names = idx_df.set_index("institution_id")["display_name"]

    def _fmt(iid: str) -> str:
        return copy.FIND["SLOT_EMPTY_LABEL"] if iid == SLOT_EMPTY else str(names.get(iid, iid))

    cols = st.columns(n)
    picks: list[str | None] = []
    for i, col in enumerate(cols):
        key = _slot_key(view, i)
        if st.session_state.get(key) not in options:
            st.session_state[key] = SLOT_EMPTY  # a basket removal can orphan a pick
        pick = col.selectbox(copy.FIND["SLOT_LABEL"].format(n=i + 1), options,
                             format_func=_fmt, key=key, **state.PERSIST)
        picks.append(None if pick == SLOT_EMPTY else pick)

    filled = [p for p in picks if p]
    if view == "collab":
        if len(filled) < 2:
            st.info(copy.FIND["SLOT_NEED_COLLAB"])
    elif len(filled) < 2:
        st.info(copy.FIND["SLOT_NEED_COMPARE"])

    if filled:
        st.query_params[param] = ",".join(filled)
    elif param in st.query_params:
        del st.query_params[param]

    return picks

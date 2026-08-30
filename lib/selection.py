"""
app/lib/selection.py -- basket/query-param parsing and deep-link helpers
(Sprint 2 Phase 2B, Stream S; BUILD_PLAN_2B.md decision 2B-8, S4, amendment A11).

Every function below is plain Python -- no Streamlit import, no CFG read, no
data-file read -- except `read_query`, the ONE thin wrapper that actually
touches `st.query_params`; its import is LOCAL to that function so the rest
of this module stays importable and unit-testable with no Streamlit runtime
(the scope fence on this file, BUILD_PLAN_2B.md S3).

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

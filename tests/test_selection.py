"""
tests/test_selection.py -- Stream S (BUILD_PLAN_2B.md decision 2B-8, S3):
unit tests for lib/state.py's basket cap/order and lib/selection.py's
query-param and deep-link helpers, plus one AppTest proof that the Find
page itself shows the cap message on a blocked add.

2BR3 (Phase 2B-R3, Stream SEL, plan §3 SEL): extended for the shared sidebar
search + basket (`selection.render_sidebar`, cap widened 6 -> 10) and the
slots API (`selection.slots_row` / the pure `resolve_slot_hydration` rule
behind its deep-link hydration).

Run from cwd `app/`:  python -m pytest tests/test_selection.py -q
"""
from __future__ import annotations

from pathlib import Path

from lib import copy, selection, state
from lib.selection import resolve_slot_hydration

APP_DIR = Path(__file__).resolve().parents[1]
FIND_PAGE = str(APP_DIR / "pages" / "1_\U0001F50E_Find.py")

KNOWN = {"A", "B", "C", "D", "E", "F", "G", "H"}


# ------------------------------------------------------------- state.py -----

def test_compare_cap_is_three_and_distinct_from_basket_cap():
    """2BR A13/2B-R-4: Compare is capped at 3, hard. 2BR3 SEL ruling 1 widens
    the shared basket 6 -> 10 (ONE sidebar search + basket for every page)."""
    assert state.COMPARE_CAP == 3
    assert state.BASKET_CAP == 10


def test_collab_cap_is_two():
    """2BR3 SEL, plan §1.6: Collaborate reads exactly two institutions, a
    plain structural constant (not config-backed like COMPARE_CAP)."""
    assert state.COLLAB_CAP == 2


def _fresh_basket(ids=()):
    """Resets the live st.session_state singleton to an empty (or seeded)
    basket. Works outside a running Streamlit script ("bare mode" -- a
    stderr warning, not an error, confirmed against this Streamlit build):
    state.py's own functions read/write nothing but this same singleton, so
    no mock is needed to unit-test them directly."""
    import streamlit as st

    st.session_state.clear()
    if ids:
        st.session_state["basket"] = list(ids)


def test_add_fills_up_to_cap_then_returns_false():
    _fresh_basket()
    for i in range(state.BASKET_CAP):
        assert state.add(f"I{i}") is True
    assert state.is_full()
    assert len(state.items()) == state.BASKET_CAP

    # the (cap + 1)-th NEW id is refused, never raised on, basket unchanged
    before = list(state.items())
    assert state.add("I_overflow") is False
    assert state.items() == before


def test_add_repeat_of_an_already_basketed_id_is_a_no_op_success():
    _fresh_basket(ids=[f"I{i}" for i in range(state.BASKET_CAP)])
    before = list(state.items())
    assert state.add("I0") is True  # already present -- True, not a cap failure
    assert state.items() == before  # unchanged, no duplicate


def test_remove_then_add_frees_a_slot():
    _fresh_basket(ids=[f"I{i}" for i in range(state.BASKET_CAP)])
    state.remove("I0")
    assert not state.is_full()
    assert state.add("I_new") is True
    assert state.is_full()


def test_move_swaps_neighbours_and_is_a_noop_at_the_edge():
    _fresh_basket(ids=["A", "B", "C"])
    state.move("B", -1)
    assert state.items() == ["B", "A", "C"]
    state.move("B", 1)
    assert state.items() == ["A", "B", "C"]
    state.move("A", -1)  # already first -- no-op
    assert state.items() == ["A", "B", "C"]
    state.move("Z", -1)  # absent -- no-op, never raises
    assert state.items() == ["A", "B", "C"]


def test_reorder_keeps_only_present_ids_and_appends_the_rest():
    _fresh_basket(ids=["A", "B", "C"])
    state.reorder(["C", "A", "Z"])  # "Z" is not in the basket -- dropped
    assert state.items() == ["C", "A", "B"]  # "B" missing from new_order -- appended


# --------------------------------------------------------- selection.py -----

def test_parse_ids_comma_string():
    kept, dropped = selection.parse_ids("A,B,C", KNOWN)
    assert kept == ["A", "B", "C"]
    assert dropped == []


def test_parse_ids_list_input():
    kept, dropped = selection.parse_ids(["A", "B"], KNOWN)
    assert kept == ["A", "B"]


def test_parse_ids_deduplicates_first_seen_order():
    kept, _ = selection.parse_ids("A,B,A,C,B", KNOWN)
    assert kept == ["A", "B", "C"]


def test_parse_ids_drops_unknown_and_reports_them():
    kept, dropped = selection.parse_ids("A,X,B,Y", KNOWN)
    assert kept == ["A", "B"]
    assert dropped == ["X", "Y"]


def test_parse_ids_empty_and_none():
    assert selection.parse_ids(None, KNOWN) == ([], [])
    assert selection.parse_ids("", KNOWN) == ([], [])


def test_parse_query_pair_needs_both_ids_valid():
    params = {"pair": "A,X"}  # X is unknown -- half a pair
    out = selection.parse_query(params, KNOWN)
    assert out["pair"] is None
    assert "X" in out["dropped"]

    out2 = selection.parse_query({"pair": "A,B"}, KNOWN)
    assert out2["pair"] == ("A", "B")


def test_parse_query_compare_and_pair_together():
    out = selection.parse_query({"compare": "A,B,C", "pair": "B,C"}, KNOWN)
    assert out["compare"] == ["A", "B", "C"]
    assert out["pair"] == ("B", "C")


def test_parse_query_missing_keys_are_empty():
    out = selection.parse_query({}, KNOWN)
    assert out == {"compare": [], "pair": None, "dropped": []}


def test_compare_ids_query_wins_then_basket_fills_capped():
    basket = ["D", "E", "F", "G"]
    query = "A,B"
    out = selection.compare_ids(basket, query, KNOWN, cap=3)
    assert out == ["A", "B", "D"]  # query first, basket fills the remaining slot, capped


def test_compare_ids_dedupes_across_query_and_basket():
    out = selection.compare_ids(["A", "B"], "B,C", KNOWN, cap=6)
    assert out == ["B", "C", "A"]


def test_compare_ids_drops_unknown_from_either_side():
    out = selection.compare_ids(["A", "ZZZ"], "YYY,B", KNOWN, cap=6)
    assert out == ["B", "A"]


# --------------------------------------------------- compare_ids_capped -----
# 2BR A13/2B-R-4: additive sibling of compare_ids (unchanged above) -- the
# already-shipped Phase 2B lib/views_compare.py calls compare_ids directly
# and iterates a flat list, so that signature must not change; the 2B-R
# Compare rebuild (Stream CP) adopts compare_ids_capped instead.

def test_compare_ids_capped_query_wins_then_basket_fills_and_reports_cut():
    """4 candidates (A,B from query; D,E,F,G from basket) = 6 combined,
    capped at 3 -- 3 are cut (E, F, G)."""
    basket = ["D", "E", "F", "G"]
    query = "A,B"
    out, n_truncated = selection.compare_ids_capped(basket, query, KNOWN, cap=3)
    assert out == ["A", "B", "D"]
    assert n_truncated == 3


def test_compare_ids_capped_dedupes_across_query_and_basket_no_truncation():
    out, n_truncated = selection.compare_ids_capped(["A", "B"], "B,C", KNOWN, cap=6)
    assert out == ["B", "C", "A"]
    assert n_truncated == 0


def test_compare_ids_capped_drops_unknown_from_either_side():
    out, n_truncated = selection.compare_ids_capped(["A", "ZZZ"], "YYY,B", KNOWN, cap=6)
    assert out == ["B", "A"]
    assert n_truncated == 0


def test_compare_ids_capped_truncation_count_at_the_2br_cap():
    """2BR A13: state.COMPARE_CAP == 3 -- 5 known candidates capped at 3
    reports n_truncated == 2, surviving ids in query-then-basket order."""
    out, n_truncated = selection.compare_ids_capped(["C", "D", "E"], "A,B", KNOWN, cap=state.COMPARE_CAP)
    assert out == ["A", "B", "C"]
    assert n_truncated == 2


def test_compare_ids_capped_matches_compare_ids_ids_half():
    """compare_ids_capped's `ids` half is byte-identical to compare_ids on
    the same inputs -- one function is not quietly a different resolution
    order from the other."""
    basket, query = ["D", "E", "F"], "A,B"
    plain = selection.compare_ids(basket, query, KNOWN, cap=3)
    capped_ids, _ = selection.compare_ids_capped(basket, query, KNOWN, cap=3)
    assert plain == capped_ids


def test_pair_from_explicit_pair_when_valid():
    assert selection.pair_from(["A", "B", "C"], a="B", b="C") == ("B", "C")


def test_pair_from_defaults_to_first_two():
    assert selection.pair_from(["A", "B", "C"]) == ("A", "B")


def test_pair_from_ignores_explicit_pick_outside_ids():
    assert selection.pair_from(["A", "B"], a="Z", b="B") == ("A", "B")


def test_pair_from_none_when_fewer_than_two():
    assert selection.pair_from(["A"]) is None
    assert selection.pair_from([]) is None


def test_deeplink_round_trips_through_parse_query():
    link = selection.deeplink("compare", ["A", "B", "C"])
    assert link == "?compare=A,B,C"
    qs = link.lstrip("?")
    key, value = qs.split("=", 1)
    out = selection.parse_query({key: value}, KNOWN)
    assert out["compare"] == ["A", "B", "C"]

    link2 = selection.deeplink("pair", ["A", "B"])
    key2, value2 = link2.lstrip("?").split("=", 1)
    out2 = selection.parse_query({key2: value2}, KNOWN)
    assert out2["pair"] == ("A", "B")


# ------------------------------------------------------ Find page proof -----

def test_find_page_shows_cap_message_on_a_blocked_add():
    """2B-8 / 2BR3 SEL end to end: a basket already at state.BASKET_CAP
    refuses an eleventh id added through the SHARED sidebar search (WT
    2BR3 task 1: `lib.selection.render_sidebar`, one-click add per result
    row -- replaces the old per-view "add a comparator" select+button flow
    this test used to drive), the basket is left unchanged, and the exact
    copy.FIND["BASKET_FULL"] string (with the real cap) renders as a
    sidebar warning -- no rerun stands between the click and this
    assertion (`render_sidebar`'s blocked branch skips st.rerun()
    precisely so this is observable in one .run())."""
    from streamlit.testing.v1 import AppTest

    # Real institution ids (not the seed, not the id searched for below):
    # render_sidebar looks each one up by display_name, so a placeholder
    # string would crash the render before the cap logic runs.
    real_ids = ["I100063501", "I100066346", "I100288624", "I100296615",
                "I100445878", "I100532134", "I100749904", "I100930933",
                "I101202996", "I101343708"]
    assert len(real_ids) == state.BASKET_CAP, "fixture must match the real cap"
    dummy_basket = real_ids
    at = AppTest.from_file(FIND_PAGE, default_timeout=120)
    at.session_state["seed_id"] = "I68947357"  # Strasbourg, gate-2A drive seed
    at.session_state["basket"] = list(dummy_basket)
    at.run()
    assert not at.exception, [str(e) for e in at.exception]
    assert at.session_state["basket"] == dummy_basket

    at.sidebar.text_input(key="sidebar_search_query").set_value("Gdansk").run()
    assert not at.exception, [str(e) for e in at.exception]
    add_button = next(b for b in at.sidebar.button if b.key == "sidebar_add_I40413290")
    add_button.click().run()
    assert not at.exception, [str(e) for e in at.exception]

    assert at.session_state["basket"] == dummy_basket, at.session_state["basket"]
    expected = copy.FIND["BASKET_FULL"].format(cap=state.BASKET_CAP)
    messages = [w.value for w in at.sidebar.warning]
    assert expected in messages, messages


def test_find_page_sidebar_search_add_then_remove():
    """2BR3 SEL end to end, the OTHER half of the shared sidebar: an empty
    basket, a search that returns a real hit, one click adds it (no
    intermediate pick step), and the remove control on the basket row takes
    it back out -- both observed through the SAME AppTest instance so the add
    and the remove are proven against the identical widget tree."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(FIND_PAGE, default_timeout=120)
    at.session_state["basket"] = []
    at.run()
    assert not at.exception, [str(e) for e in at.exception]

    at.sidebar.text_input(key="sidebar_search_query").set_value("IFPEN").run()
    assert not at.exception, [str(e) for e in at.exception]
    add_button = next(b for b in at.sidebar.button if b.key == "sidebar_add_I265217849")
    add_button.click().run()
    assert not at.exception, [str(e) for e in at.exception]
    assert at.session_state["basket"] == ["I265217849"], at.session_state["basket"]

    rm_button = next(b for b in at.sidebar.button if b.key == "sidebar_rm_I265217849")
    rm_button.click().run()
    assert not at.exception, [str(e) for e in at.exception]
    assert at.session_state["basket"] == [], at.session_state["basket"]


# ------------------------------------------------------- slots API (2BR3) ---
# 2BR3 SEL, plan §3 SEL: lib.selection.slots_row and the pure hydration rule
# behind it. slots_row itself needs a Streamlit runtime (st.columns/
# selectbox/query_params); resolve_slot_hydration is the pure rule split out
# specifically so it is unit-testable with none.

def test_resolve_slot_hydration_parses_and_pads():
    out = resolve_slot_hydration("A,B", KNOWN, 3)
    assert out == ["A", "B", selection.SLOT_EMPTY]


def test_resolve_slot_hydration_truncates_to_n():
    out = resolve_slot_hydration("A,B,C,D", KNOWN, 2)
    assert out == ["A", "B"]


def test_resolve_slot_hydration_drops_unknown_ids():
    out = resolve_slot_hydration("A,ZZZ,B", KNOWN, 3)
    assert out == ["A", "B", selection.SLOT_EMPTY]


def test_resolve_slot_hydration_none_value_is_all_empty():
    assert resolve_slot_hydration(None, KNOWN, 2) == [selection.SLOT_EMPTY] * 2


def test_slots_row_hydrates_from_url_fills_basket_and_persists_across_rerun():
    """slots_row end to end (AppTest.from_function, no real page needed):
    first run with `?compare=A,B` hydrates both slots AND folds A/B into the
    basket; a second .run() with NO query params must NOT re-hydrate (the
    session flag guards it) -- the slots stay exactly where the reader last
    left them, proving the persistence half of the acceptance."""
    from streamlit.testing.v1 import AppTest

    def _app():
        import streamlit as st

        from lib import selection, state

        state.ensure()
        picks = selection.slots_row("compare", 3)
        st.session_state["_picks_seen"] = picks

    at = AppTest.from_function(_app, default_timeout=60)
    at.query_params["compare"] = "I265217849,I40413290"
    at.run()
    assert not at.exception, [str(e) for e in at.exception]
    assert at.session_state["_picks_seen"] == ["I265217849", "I40413290", None]
    assert at.session_state["basket"] == ["I265217849", "I40413290"]
    assert at.query_params["compare"] == ["I265217849,I40413290"]

    # Reader manually fills slot 3 (their own edit, no query param involved):
    # options are SLOT_EMPTY plus the basket, so the LAST option is always a
    # real id here (the basket holds A and B, both non-empty).
    slot3 = at.selectbox(key="slot_compare_2")
    assert len(slot3.options) >= 2, slot3.options
    slot3.select_index(len(slot3.options) - 1).run()
    assert not at.exception, [str(e) for e in at.exception]
    third = at.session_state["_picks_seen"][2]
    assert third is not None, at.session_state["_picks_seen"]
    assert at.query_params["compare"] == [f"I265217849,I40413290,{third}"]


def test_slots_row_collab_uses_pair_param_and_two_slots():
    from streamlit.testing.v1 import AppTest

    def _app():
        import streamlit as st

        from lib import selection, state

        state.ensure()
        picks = selection.slots_row("collab", 2)
        st.session_state["_picks_seen"] = picks

    at = AppTest.from_function(_app, default_timeout=60)
    at.query_params["pair"] = "I265217849,I40413290"
    at.run()
    assert not at.exception, [str(e) for e in at.exception]
    assert at.session_state["_picks_seen"] == ["I265217849", "I40413290"]
    assert "compare" not in at.query_params
    assert at.query_params["pair"] == ["I265217849,I40413290"]

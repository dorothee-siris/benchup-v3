"""
tests/test_selection.py -- Stream S (BUILD_PLAN_2B.md decision 2B-8, S3):
unit tests for lib/state.py's basket cap/order and lib/selection.py's
query-param and deep-link helpers, plus one AppTest proof that the Find
page itself shows the cap message on a blocked add.

Run from cwd `app/`:  python -m pytest tests/test_selection.py -q
"""
from __future__ import annotations

from pathlib import Path

from lib import copy, selection, state

APP_DIR = Path(__file__).resolve().parents[1]
FIND_PAGE = str(APP_DIR / "pages" / "1_\U0001F50E_Find.py")

KNOWN = {"A", "B", "C", "D", "E", "F", "G", "H"}


# ------------------------------------------------------------- state.py -----

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
    """2B-8 end to end: a basket already at state.BASKET_CAP refuses a
    seventh id added through the sidebar's "add a comparator" flow, the
    basket is left unchanged, and the exact copy.FIND["BASKET_FULL"] string
    (with the real cap) renders as a sidebar warning -- no rerun stands
    between the click and this assertion (lib/views_find.py's blocked
    branch skips st.rerun() precisely so this is observable in one .run())."""
    from streamlit.testing.v1 import AppTest

    # Real institution ids (not the seed, not the id searched for below):
    # _sidebar_basket looks each one up by `.loc[iid, "display_name"]", so a
    # placeholder string would crash the render before the cap logic runs.
    real_ids = ["I100063501", "I100066346", "I100288624", "I100296615",
                "I100445878", "I100532134"]
    assert len(real_ids) == state.BASKET_CAP, "fixture must match the real cap"
    dummy_basket = real_ids
    at = AppTest.from_file(FIND_PAGE, default_timeout=120)
    at.session_state["seed_id"] = "I68947357"  # Strasbourg, gate-2A drive seed
    at.session_state["basket"] = list(dummy_basket)
    at.run()
    assert not at.exception, [str(e) for e in at.exception]
    assert at.session_state["basket"] == dummy_basket

    at.sidebar.text_input(key="basket_query").set_value("Gdansk").run()
    assert not at.exception, [str(e) for e in at.exception]
    at.sidebar.selectbox(key="basket_pick").select_index(0).run()
    assert not at.exception, [str(e) for e in at.exception]
    at.sidebar.button(key="basket_add").click().run()
    assert not at.exception, [str(e) for e in at.exception]

    assert at.session_state["basket"] == dummy_basket, at.session_state["basket"]
    expected = copy.FIND["BASKET_FULL"].format(cap=state.BASKET_CAP)
    messages = [w.value for w in at.sidebar.warning]
    assert expected in messages, messages

"""
app/lib/views_collab.py -- render functions for the Collaborate page (Sprint 2
Phase 2B, Stream L; BUILD_PLAN_2B.md decisions 2B-7 / 2B-8, amendments A7, A10,
A11, and the interface contract in S4).

COMPOSITION ONLY, same rule as lib/views_find.py: every frame comes from
`lib/collab_data.py`, every id/pair rule from `lib/selection.py`, every URL from
`lib/links.py`, every string from `lib/copy.py`, every colour from
`lib/palette.py`. Nothing here recomputes a number and nothing here types one
into a rendered string (BUILD_PLAN_2A.md L10, enforced by
tests/test_narrative.py once Stream G widens its scope to lib/views_*.py).

PAGE SHAPE (2B-R-10, phase 2B-R): FOUR sections over the pair A <-> B, built on
the NEW pair artefacts (`collab_pairs.parquet`, `collab_pair_topics.parquet`)
through `lib/collab_data.py`'s `pulse` / `joint_profile` / `untapped`:

  1. the relationship pulse -- joint publications per year (`charts_compare.
     fig_pulse`, partial year starred), each side's joint share of its OWN
     output with both denominators named, and the two ranks in their two
     directions (`rank_in_a` = where B sits among A's partners);
  2. what the two publish on together -- the joint corpus by field, subfield
     and topic, its SDG share, its frontier topics and its top ERC panel, or,
     for a pair under the topic floor, the honest notice and nothing invented;
  3. where the two overlap without publishing together -- the untapped-topic
     table with its formula written out, the sibling topics beside it, and the
     2B tables (topic overlap, the two directional gap lists, breadth) kept
     underneath, because they answer the same reader's question;
  4. the link-outs -- both institutions' publications and the pair's
     co-publications, live on OpenAlex.

The pair picker, the swap button, the `?pair=` deep link and the hand-off from
Compare are UNCHANGED from 2B. ONE chart module is imported now (stream VS's
`fig_pulse` + `legend_strip`, which did not exist when this file was first
written); everything else is still tables, and the palette borrow for identity
swatches stays guarded (`_swatches`).

SIDEBAR: counting & taxonomy (the SAME widget keys `tree` / `basis` the Find
page uses, so the scenario carries across pages) + a READ-ONLY basket with a
link back to Find (the add/remove affordances stay on Find, which owns them).

PERFORMANCE (2B-14: warm rerun < 1.5 s; A10)
  `views_find._bundle` / `views_find._subs` are reused BY IMPORT, not copied, so
  the engine context (2.5 s) and each (tree, basis) substrate (4.6 s) load once
  per process and are shared with the Find page rather than paid again here.
  A tree/basis flip pays `build_substrates` once, behind the spinner A10 asks
  for. The three frames are `@st.cache_data` keyed on (a, b, tree, basis) --
  ctx/subs are unhashable and are never cache_data arguments.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from lib import charts_compare as X
from lib import collab_data, copy, countries, links, profile_data, selection, state
from lib import palette as P
from lib.app_config import CFG
from lib.compare_data import DYNAMICS_W1, DYNAMICS_W2
from lib.palette import NA_MARK
from lib.search import search
from lib.views_find import BONUS_STAR, SEP, _bundle, _hit_label, _sidebar_scenario, _subs

# The en dash between the two ends of a window label ("2020-2025" rendered with
# a real dash). The YEARS themselves are never typed here: they come from
# `collab_data.PULSE_YEARS`, `lib.compare_data`'s dynamics windows and CFG.
DASH = "\N{EN DASH}"

# A pulse difference smaller than this reads as "the same annual rate" rather
# than as a direction: the two windows are 3 and 2 years long, so a few papers
# of noise on a small pair would otherwise be rendered as a trend. Stated on the
# page through `COLLAB["PULSE_TREND_NOTE"]`, never typed into a caption.
TREND_BAND = 0.10

# The breadth floor (manager fix on K's `breadth_jaccard`, Wind Tunnel 2B E5): a
# topic counts towards an institution's footprint once it carries at least this
# many FULL-counted publications, so a single co-authored paper is not breadth.
# A module constant, never a digit inside a caption -- `COLLAB["BREADTH_FLOOR"]`
# takes it as `{min_pubs}`.
BREADTH_MIN_FULL = 2

# Shares are portfolio fractions in the per-mille range, so the tables show them
# as percentages with two decimals. Streamlit's printf `format=` does NOT scale
# the value (the R1 manager fix on lib/ranked.py's ProgressColumn measured a 0-1
# score printing as "1%"), so the DISPLAY frame carries share x PCT_SCALE and
# the CSV keeps the raw fraction.
PCT_SCALE = 100
PCT_FORMAT = "%.2f%%"

# Frontier flag rendering: a glyph, its absence, or n/a for a topic that carries
# no frontier score at all (BUILD_PLAN_2A.md L11 -- n/a is never 0 and never a
# silent False).
FRONTIER_MARK = "▲"      # black up-pointing triangle
FRONTIER_BLANK = ""

# The institution-identity swatch (2B-1 / A8), shown only when stream V's
# palette additions exist at runtime -- see `_swatches`.
SWATCH_MARK = "●"        # black circle, tinted by the palette colour

KEYWORD_JOIN = ", "           # topics_dim.keywords ships "|"-delimited

# The plain (non-widget) session key holding institutions added by name on THIS
# page: the basket belongs to Find (2A L-basket rule), and a Collaborate reader
# must be able to pull in a second institution without editing it.
EXTRA_KEY = "collab_extra"

FIND_PAGE = "pages/1_\U0001F50E_Find.py"


# ------------------------------------------------------------- frames -------
# One @st.cache_data per table, keyed on the HASHABLE scenario identity
# (a, b, tree, basis). `st.expander` bodies execute even when collapsed and every
# widget touch reruns the whole script, so an uncached frame would be recomputed
# on every keystroke in the search box.

@st.cache_data(show_spinner=False, max_entries=24)
def _shared_frame(a: str, b: str, tree: str, basis: str) -> pd.DataFrame:
    return collab_data.shared_topics(_bundle()["ctx"], _subs(tree, basis), a, b)


@st.cache_data(show_spinner=False, max_entries=24)
def _gaps_frame(a: str, b: str, tree: str, basis: str) -> pd.DataFrame:
    """B's topics inside A's strongest subfields that A itself lacks. The
    symmetric table is this same function called with the ids swapped -- the
    page calls it BOTH ways (2B-7)."""
    return collab_data.gaps(_bundle()["ctx"], _subs(tree, basis), a, b)


@st.cache_data(show_spinner=False, max_entries=24)
def _breadth(a: str, b: str, tree: str, basis: str) -> dict:
    """Unweighted topic-footprint Jaccard, with the publication floor
    BREADTH_MIN_FULL -- passed explicitly here (K's default is 0) and stated on
    the page, because the number moves a lot with it."""
    return collab_data.breadth_jaccard(_bundle()["ctx"], _subs(tree, basis), a, b,
                                       min_full=BREADTH_MIN_FULL)


# --- 2B-R-10: the three pair frames. `pulse` needs no substrate (it reads one
# row of `collab_pairs` plus the index), so it is keyed on the pair alone and
# survives a tree/basis flip; the other two are tree/basis-aware.

@st.cache_data(show_spinner=False, max_entries=48)
def _pulse_frame(a: str, b: str) -> dict | None:
    return collab_data.pulse(_bundle()["ctx"], a, b)


@st.cache_data(show_spinner=False, max_entries=24)
def _joint_frame(a: str, b: str, tree: str, basis: str) -> dict | None:
    """`None` means BELOW THE TOPIC FLOOR (or never co-published) -- the page
    renders the honest notice rather than an empty table (2B-R-10)."""
    return collab_data.joint_profile(_bundle()["ctx"], _subs(tree, basis), a, b)


@st.cache_data(show_spinner=False, max_entries=24)
def _untapped_frame(a: str, b: str, tree: str, basis: str) -> dict:
    return collab_data.untapped(_bundle()["ctx"], _subs(tree, basis), a, b)


# --------------------------------------------------------- formatting -------

def _pct(value) -> str:
    if value is None or pd.isna(value):
        return NA_MARK
    return f"{float(value):.1%}"


def _count(value) -> str:
    if value is None or pd.isna(value):
        return NA_MARK
    return f"{value:,.0f}"


def _frontier_glyph(value) -> str:
    """True -> glyph, False -> blank, missing -> n/a. `top25pct_frontier` is a
    pandas BooleanDtype column, so `pd.NA` reaches here as a real third state
    (the topic carries no frontier score), never as False."""
    if value is None or pd.isna(value):
        return NA_MARK
    return FRONTIER_MARK if bool(value) else FRONTIER_BLANK


def _keywords_text(value) -> str:
    """`topics_dim.keywords` is a "|"-joined string (K's own note: 0 nulls of
    4,516). Cast through str() first -- a categorical or a pd.NA would break
    `.replace` (Assembly Line gotcha)."""
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return NA_MARK
    return KEYWORD_JOIN.join(p for p in str(value).split("|") if p)


def _name(ctx: dict, iid: str) -> str:
    return str(ctx["index_by_id"].loc[iid, "display_name"])


def _window(years) -> str:
    """"first{dash}last" for a window handed in as a (start, end) pair or as a
    list of years. The years come from `collab_data.PULSE_YEARS` and
    `lib.compare_data`'s dynamics constants, so no window is ever typed here."""
    ys = list(years)
    return f"{ys[0]}{DASH}{ys[-1]}"


def _window_mean(yearly: pd.DataFrame, window) -> float:
    """Mean annual joint volume over an inclusive (start, end) year window,
    read off the pulse frame the chart itself draws."""
    by_year = dict(zip(yearly["year"], yearly["copubs"]))
    years = range(window[0], window[1] + 1)
    return float(sum(float(by_year.get(y, 0.0)) for y in years) / len(list(years)))


def _trend_line(yearly: pd.DataFrame) -> str:
    """The one plain-language pulse sentence (2B-R-10). It is a DATA question,
    answered by comparing the two dynamics windows the rest of the tool already
    uses (`compare_data.DYNAMICS_W1`/`W2`, 2020-2022 against 2023-2024, partial
    year excluded), and phrased in neutral vocabulary: a direction and a size,
    never a judgement about the relationship."""
    w1 = _window_mean(yearly, DYNAMICS_W1)
    w2 = _window_mean(yearly, DYNAMICS_W2)
    words = {"w1": _window(DYNAMICS_W1), "w2": _window(DYNAMICS_W2)}
    if not w1 > 0:
        return copy.COLLAB["PULSE_TREND_NA"].format(**words)
    change = (w2 - w1) / w1
    if abs(change) < TREND_BAND:
        key = "PULSE_TREND_FLAT"
    else:
        key = "PULSE_TREND_UP" if change > 0 else "PULSE_TREND_DOWN"
    return copy.COLLAB[key].format(pct=_pct(abs(change)), **words)


def _slots(ctx: dict, ids: list[str]) -> dict:
    """`{institution_id: slot}` by ascending `inst_key` (A8), the same
    assignment `_swatches` and the Compare page use, so the legend chip and the
    identity dot of an institution are the same colour on both pages."""
    return P.institution_slots({iid: ctx["index_by_id"].loc[iid, "inst_key"] for iid in ids})


def _frontier_flags(ctx: dict) -> dict:
    """topic_id -> `top25pct_frontier`, a LOOKUP on the dimension table the
    engine context already holds (`shared_topics` joins the same column for its
    own frontier glyph). Nothing is computed: `collab_pair_topics` simply does
    not carry the flag, and the joint-topic table needs it."""
    dim = ctx["topics_dim_df"]
    return dict(zip(dim["topic_id"], dim["top25pct_frontier"]))


def _erc_panel_label(ctx: dict, panel_code) -> str:
    """The ERC panel's readable name for the code `collab_pair_topics` carries
    (`erc_top_panel`, e.g. the physical-sciences engineering panel), read off
    the same `resources/erc_panels.csv` the profile's own ERC table joins."""
    if panel_code is None or (not isinstance(panel_code, str) and pd.isna(panel_code)):
        return NA_MARK
    panels = profile_data._erc_panels(ctx)
    hit = panels[panels["panel_code"].astype(str) == str(panel_code)]
    if hit.empty:
        return str(panel_code)
    return f"{panel_code} {SEP} {hit.iloc[0]['panel_label']}"


# ------------------------------------------------------------- sidebar ------

def _sidebar_basket(bundle: dict) -> None:
    """READ-ONLY here: the basket is built on Find, which owns its add/remove
    controls (Stream S's fence). This page shows what is in it, because it is
    where the pair picker's options come from, and links back to the page that
    can change it."""
    sb, names = st.sidebar, bundle["ctx"]["index_by_id"]
    sb.header(copy.FIND["BASKET_HEADER"])
    items = state.items()
    sb.caption(copy.FIND["BASKET_COUNT"].format(n=len(items), cap=state.BASKET_CAP))
    if not items:
        sb.caption(copy.FIND["BASKET_EMPTY"])
    else:
        for iid in items:
            sb.write(str(names.loc[iid, "display_name"]))
    # `st.page_link` needs the multi-page registry, which only exists when the
    # app is entered through Menu.py. Run this ONE page on its own (AppTest,
    # `streamlit run pages/3_...py`, the acceptance probe) and Streamlit raises
    # a KeyError on its own page table -- so the link degrades to its label
    # rather than taking the whole page down with it.
    try:
        sb.page_link(FIND_PAGE, label=copy.NAV["FIND_LABEL"])
    except Exception:
        sb.caption(copy.NAV["FIND_LABEL"])


# ------------------------------------------------------- header + pair ------

def _header(bundle: dict) -> None:
    """Title and lead from `copy.NAV` (2B-10's editorial labels), the standing
    verdict line, and the index-size caption. The snapshot STRING is gone
    app-wide (2B-R-12, stream FA): `FIND["SNAPSHOT_CAPTION"]` now carries the
    institution count alone, and the date lives on the menu page."""
    st.title(copy.NAV["COLLAB_LABEL"])
    st.subheader(copy.NAV["COLLAB_LEAD"])
    st.caption(copy.COLLAB["PAGE_INTRO_PAIR"])
    st.markdown(f"**{copy.VERDICT_LINE}**")
    st.caption(copy.FIND["SNAPSHOT_CAPTION"].format(
        n_institutions=f"{len(bundle['index_df']):,}"))


def _extras() -> list[str]:
    st.session_state.setdefault(EXTRA_KEY, [])
    return st.session_state[EXTRA_KEY]


def _candidates(bundle: dict) -> list[str]:
    """Everything the pair picker may choose from, in a stable order: the
    basket (its own user order, 2B-8), then whatever a deep link named, then
    whatever Compare's hand-off button just stashed in `st.session_state["pair"]`
    (read here, NOT popped -- `_pair_picker` below is the one place that
    consumes it, after this function has already folded its ids into the
    option list `st.selectbox` needs them in), then whatever was added by name
    on this page. De-duplicated, and filtered to ids the index really
    carries."""
    known = bundle["ctx"]["id_pos"]
    query = selection.read_query(known)
    session_pair = st.session_state.get("pair") or ()
    out: list[str] = []
    seen: set[str] = set()
    pair = query["pair"] or ()
    for iid in (*state.items(), *pair, *session_pair, *_extras()):
        if iid in known and iid not in seen:
            seen.add(iid)
            out.append(iid)
    return out


def _add_by_name(bundle: dict) -> None:
    """The "add a comparator" affordance, same shape as Find's: a free-text box,
    a selectbox over the hits, and the pick lands in this page's own extras list
    (never in the basket -- that would silently spend one of its slots)."""
    query = st.text_input(copy.COMPARE["ADD_LABEL"], key="collab_query", **state.PERSIST)
    hits = search(query, bundle["search_idx"]) if query else []
    if query and not hits:
        st.caption(copy.SEARCH_EMPTY_TEMPLATE.format(query=query))
    if not hits:
        return
    pick = st.selectbox(copy.COLLAB["PAIR_PICK"], [h["id"] for h in hits],
                        format_func=lambda i: _hit_label(hits, i), key="collab_pick")
    extras = _extras()
    if pick and pick not in extras and pick not in state.items():
        extras.append(pick)
        st.rerun()


def _swap() -> None:
    """`on_click` callback: writing a widget key is legal inside a callback and
    illegal after the widget has been instantiated, which is why the swap is a
    callback rather than a button body plus `st.rerun()`."""
    a, b = st.session_state.get("pair_a"), st.session_state.get("pair_b")
    st.session_state["pair_a"], st.session_state["pair_b"] = b, a


def default_pair(candidates: list[str], query_pair, known, session_pair=None) -> tuple | None:
    """Pure: the pair the page opens on. `session_pair` -- Compare's hand-off
    button's `st.session_state["pair"]`, already popped by the caller -- wins
    FIRST when both its ids are known: it is the reader's own most recent
    in-session action, the fix for a hand-off that used to drop the session
    entirely (progress/2B_X.md). Next a `?pair=` deep link wins (a shared link
    should show what it names, A11 / 2B-8), then the first two candidates in
    their own order. `None` when fewer than two are available."""
    for pair in (session_pair, query_pair):
        if pair and len(pair) >= 2:
            a, b = pair[0], pair[1]
            if a != b and a in known and b in known:
                return (a, b)
    return selection.pair_from(candidates)


def _pair_picker(bundle: dict, candidates: list[str]) -> tuple | None:
    """The directional A -> B picker. Returns `(a, b)`, or None when the page
    has nothing to read yet."""
    ctx = bundle["ctx"]
    st.subheader(copy.COLLAB["PAIR_HEADER"])
    st.caption(copy.COLLAB["PAIR_PROMPT"])
    _add_by_name(bundle)
    if len(candidates) < 2:
        st.info(copy.COLLAB["EMPTY_NO_PAIR"])
        return None

    query = selection.read_query(ctx["id_pos"])
    # Popped HERE, once: a hand-off is a one-time seed for the render right
    # after the hop, never a standing override that would keep fighting a
    # reader's own later edit to the selectboxes below (progress/2B_X.md).
    # `_candidates` above already read this same key (without popping) to
    # fold its ids into the option list, so a hop always resolves to a value
    # `st.selectbox` accepts.
    session_pair = st.session_state.pop("pair", None)
    default = default_pair(candidates, query["pair"], ctx["id_pos"], session_pair)
    # A stored selection that is no longer among the options would make
    # st.selectbox raise, so it is dropped rather than defended against later.
    # A just-consumed `session_pair` FORCES both boxes to the hand-off's pair
    # even when an earlier Collaborate visit this session left them on some
    # other pair that still happens to validate -- otherwise the widgets' own
    # `persist_state` would win and a second hand-off would silently do
    # nothing.
    for key, fallback in (("pair_a", default[0]), ("pair_b", default[1])):
        if session_pair or st.session_state.get(key) not in candidates:
            st.session_state[key] = fallback

    cols = st.columns([2, 2, 1])
    label = lambda i: _name(ctx, i)  # noqa: E731  (one-line format_func, both boxes)
    a = cols[0].selectbox(copy.COLLAB["PAIR_A_LABEL"], candidates, format_func=label,
                          key="pair_a", **state.PERSIST)
    b = cols[1].selectbox(copy.COLLAB["PAIR_B_LABEL"], candidates, format_func=label,
                          key="pair_b", **state.PERSIST)
    cols[2].button(copy.COLLAB["PAIR_SWAP_BUTTON"], help=copy.COLLAB["PAIR_SWAP_HELP"],
                   on_click=_swap, key="pair_swap")
    if a == b:
        st.info(copy.COLLAB["EMPTY_SAME"])
        return None
    st.caption(copy.COLLAB["DEEPLINK_LABEL"])
    st.code(selection.deeplink("pair", [a, b]), language=None)
    return (a, b)


# -------------------------------------------------------- header strip ------

def _swatches(ctx: dict, ids: list[str]) -> dict:
    """`{institution_id: css colour}` from the 2B-1 identity family, or `{}`
    when stream V's palette additions are not present at runtime. Slots are
    assigned by ascending `inst_key` inside `palette.institution_slots` (A8),
    never by the order this page holds the pair in -- so the swatch of an
    institution does not change when the reader swaps A and B."""
    if not (hasattr(P, "INSTITUTION_COLORS") and hasattr(P, "institution_slots")
            and hasattr(P, "institution_color")):
        return {}
    try:
        keys = {i: ctx["index_by_id"].loc[i, "inst_key"] for i in ids}
        slots = P.institution_slots(keys)
        return {i: P.institution_color(slots[i]) for i in ids}
    except Exception:  # a palette shape this page does not know: show no swatch
        return {}


def _identity(col, ctx: dict, iid: str, colour: str | None) -> None:
    row = ctx["index_by_id"].loc[iid]
    # A coloured GLYPH, not a styled box: an inline box would need pixel/percent
    # lengths, i.e. typed digits inside a string a Streamlit call renders, which
    # is exactly what the digit-ban forbids (BUILD_PLAN_2A.md L10). The only
    # value interpolated here is the palette's own colour.
    dot = f'<span style="color:{colour}">{SWATCH_MARK}</span> ' if colour else ""
    col.markdown(f"{dot}**{_name(ctx, iid)}**", unsafe_allow_html=True)
    col.caption(f"{str(row['type'])} {SEP} {countries.name(str(row['country_code']))}")
    col.caption(f"{copy.FIND['COL_SIZE_FULL']}: {_count(row['total_full_2020_2024'])} {SEP} "
                f"{copy.FIND['COL_SIZE_FRAC']}: {_count(row['total_frac_2020_2024'])}")


def _header_strip(bundle: dict, a: str, b: str) -> None:
    """Both institutions side by side: who they are, where they are, how big
    they are. The three OpenAlex link-outs used to sit here; 2B-R-10 gives them
    their own closing section (`_render_links`), because a reader reaches for
    them after the four readings, not before."""
    ctx = bundle["ctx"]
    with st.container(key="collab_header", border=True):
        colours = _swatches(ctx, [a, b])
        cols = st.columns(2)
        _identity(cols[0], ctx, a, colours.get(a))
        _identity(cols[1], ctx, b, colours.get(b))


def _render_links(bundle: dict, a: str, b: str) -> None:
    """Section four (2B-R-10): the two per-institution works links and the ONE
    co-publication link (A7: the comma-joined repeated
    `authorships.institutions.id` filter, which OpenAlex ANDs; the `+` form is
    forbidden and `lib/links.py` never builds it). This section renders for
    every pair, below-floor ones included -- it is the whole answer when the
    topic detail cannot be shown."""
    ctx = bundle["ctx"]
    st.subheader(copy.COLLAB["LINKS_HEADER"])
    st.caption(copy.COLLAB["LINKS_INTRO"])
    with st.container(key="collab_links"):
        link_cols = st.columns(3)
        for col, iid in zip(link_cols, (a, b)):
            col.link_button(copy.COLLAB["LINK_PUBS"].format(name=_name(ctx, iid)),
                            links.works_url(iid), help=copy.FIND["LINK_OPENALEX_HELP"])
        link_cols[2].link_button(copy.COLLAB["LINK_COPUBS"], links.copubs_url(a, b),
                                 help=copy.FIND["LINK_OPENALEX_HELP"])


# -------------------------------------------------------------- tables ------

def _download(df: pd.DataFrame, *, label: str, name: str, key: str) -> None:
    """Streamlit 1.61 accepts a zero-arg callable for `data`, so the CSV is
    encoded only when someone actually clicks (the lib/views_find.py pattern).
    The RAW frame goes out -- fractions, not the display percentages."""
    st.download_button(label, lambda: df.to_csv(index=False).encode("utf-8"),
                       mime="text/csv", file_name=name, key=key)


def _shared_display(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame({
        "topic": df["topic_name"].astype(str),
        "subfield": df["subfield_name"].astype(str),
        "share_a": df["share_a"] * PCT_SCALE,
        "share_b": df["share_b"] * PCT_SCALE,
        "min_share": df["min_share"] * PCT_SCALE,
        "frontier": df["top25pct_frontier"].map(_frontier_glyph),
        "keywords": df["keywords"].map(_keywords_text),
    })
    return out


def _render_shared(bundle: dict, a: str, b: str, scenario: dict) -> None:
    ctx = bundle["ctx"]
    st.subheader(copy.COLLAB["SHARED_HEADER"])
    df = _shared_frame(a, b, scenario["tree"], scenario["basis"])
    if df.empty:
        st.info(copy.COLLAB["EMPTY_SHARED"].format(a=_name(ctx, a), b=_name(ctx, b)))
        return
    st.dataframe(
        _shared_display(df), hide_index=True, width="stretch", key="tbl_shared",
        column_order=["topic", "subfield", "share_a", "share_b", "min_share",
                      "frontier", "keywords"],
        column_config={
            "topic": st.column_config.TextColumn(copy.COLLAB["SHARED_COL_TOPIC"],
                                                 width="medium"),
            "subfield": st.column_config.TextColumn(copy.COLLAB["SHARED_COL_SUBFIELD"]),
            "share_a": st.column_config.NumberColumn(copy.COLLAB["SHARED_COL_SHARE_A"],
                                                     format=PCT_FORMAT),
            "share_b": st.column_config.NumberColumn(copy.COLLAB["SHARED_COL_SHARE_B"],
                                                     format=PCT_FORMAT),
            "min_share": st.column_config.NumberColumn(copy.COLLAB["SHARED_COL_MIN"],
                                                       format=PCT_FORMAT),
            "frontier": st.column_config.TextColumn(copy.COLLAB["SHARED_COL_FRONTIER"],
                                                    help=copy.COLLAB["GAPS_FRONTIER_HELP"]),
            "keywords": st.column_config.TextColumn(copy.COLLAB["SHARED_COL_KEYWORDS"],
                                                    width="large",
                                                    help=copy.COLLAB["SHARED_KEYWORDS_HELP"]),
        },
    )
    # The score is COMPUTED from the frame on screen, never typed: summing the
    # smaller of the two shares over every shared topic IS the engine's own L3
    # histogram-intersection score for this pair (K's engine-identity anchor).
    st.caption(copy.COLLAB["SHARED_CAPTION"].format(score=f"{df['min_share'].sum():.3f}"))
    st.caption(copy.COLLAB["SHARED_ROWS"].format(n=f"{len(df):,}"))
    _download(df, label=copy.COLLAB["DOWNLOAD_SHARED"],
              name=f"benchup_collab_shared_{a}_{b}_{scenario['tree']}_{scenario['basis']}.csv",
              key="dl_shared")


def _gaps_display(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "topic": df["topic_name"].astype(str),
        "subfield": df["subfield_name"].astype(str),
        "share_b": df["share_b"] * PCT_SCALE,
        "frontier": df["top25pct_frontier"].map(_frontier_glyph),
        "keywords": df["topic_id"].map(_gap_keywords(_bundle()["ctx"])),
    })


def _gap_keywords(ctx: dict):
    """`collab_data.gaps` does not carry the keyword column (its contract is
    five columns), so the same lazy `topics_dim.keywords` map `shared_topics`
    uses is read here through collab_data's own accessor rather than
    re-reading the parquet."""
    kw = collab_data._topic_keywords_map(ctx)
    return lambda tid: _keywords_text(kw.get(tid))


def _render_gaps(bundle: dict, a: str, b: str, scenario: dict, *, key: str) -> None:
    """One direction: what B publishes in, inside A's strongest subfields, that
    A does not. Called twice with the ids swapped (2B-7's symmetric table)."""
    ctx = bundle["ctx"]
    name_a, name_b = _name(ctx, a), _name(ctx, b)
    st.subheader(copy.COLLAB["GAPS_HEADER"].format(a=name_a))
    df = _gaps_frame(a, b, scenario["tree"], scenario["basis"])
    if df.empty:
        st.info(copy.COLLAB["EMPTY_GAPS"].format(a=name_a, b=name_b))
        return
    st.dataframe(
        _gaps_display(df), hide_index=True, width="stretch", key=f"tbl_{key}",
        column_order=["topic", "subfield", "share_b", "frontier", "keywords"],
        column_config={
            "topic": st.column_config.TextColumn(copy.COLLAB["GAPS_COL_TOPIC"],
                                                 width="medium"),
            "subfield": st.column_config.TextColumn(copy.COLLAB["GAPS_COL_SUBFIELD"]),
            "share_b": st.column_config.NumberColumn(copy.COLLAB["GAPS_COL_SHARE"],
                                                     format=PCT_FORMAT),
            "frontier": st.column_config.TextColumn(copy.COLLAB["GAPS_COL_FRONTIER"],
                                                    help=copy.COLLAB["GAPS_FRONTIER_HELP"]),
            "keywords": st.column_config.TextColumn(copy.COLLAB["SHARED_COL_KEYWORDS"],
                                                    width="large",
                                                    help=copy.COLLAB["SHARED_KEYWORDS_HELP"]),
        },
    )
    st.caption(copy.COLLAB["GAPS_CAPTION"].format(a=name_a, b=name_b))
    _download(df, label=copy.COLLAB["DOWNLOAD_GAPS"],
              name=f"benchup_collab_gaps_{a}_{b}_{scenario['tree']}_{scenario['basis']}.csv",
              key=f"dl_{key}")


def _render_breadth(a: str, b: str, scenario: dict) -> None:
    st.subheader(copy.COLLAB["BREADTH_HEADER"])
    res = _breadth(a, b, scenario["tree"], scenario["basis"])
    if res["n_a"] == 0 and res["n_b"] == 0:
        st.info(copy.COLLAB["EMPTY_BREADTH"])
        return
    st.markdown(copy.COLLAB["BREADTH_LINE"].format(
        jaccard=_pct(res["jaccard"]), n_shared=f"{res['n_shared']:,}",
        n_a=f"{res['n_a']:,}", n_b=f"{res['n_b']:,}"))
    st.caption(copy.COLLAB["BREADTH_FLOOR"].format(min_pubs=BREADTH_MIN_FULL))


# ------------------------------------------- 1. the relationship pulse ------

def _render_pulse(bundle: dict, a: str, b: str) -> dict | None:
    """Section one (2B-R-10): the pair's joint publications per year, each
    side's joint share of its OWN output with both denominators named, the two
    ranks in their two directions, and one plain-language line about the
    movement. Returns the pulse frame so the sections below can reuse the joint
    total rather than read the same row twice."""
    ctx = bundle["ctx"]
    st.subheader(copy.COLLAB["PULSE_HEADER"])
    row = _pulse_frame(a, b)
    if row is None:
        st.info(copy.COLLAB["EMPTY_PULSE"].format(a=_name(ctx, a), b=_name(ctx, b)))
        return None

    names = {a: _name(ctx, a), b: _name(ctx, b)}
    # The pulse bar belongs to NEITHER institution (a co-publication is the
    # pair's), so the strip carries both identity chips AND the shared chip the
    # bars are actually drawn in -- 2B-R-12's legend-above-every-chart rule.
    with st.container(key="collab_legend"):
        st.markdown(X.legend_strip([a, b], slots=_slots(ctx, [a, b]), names=names,
                                   shared=True, shared_label=copy.COLLAB["LEGEND_JOINT"]),
                    unsafe_allow_html=True)
    st.plotly_chart(X.fig_pulse(row["yearly"], value_col="copubs",
                                bonus_year=str(CFG["bonus_year"]),
                                axis_title=copy.COLLAB["PULSE_AXIS"]),
                    width="stretch", key="fig_pulse")
    st.caption(copy.COLLAB["PULSE_CHART_CAPTION"].format(bonus_year=CFG["bonus_year"],
                                                         star=BONUS_STAR))

    cols = st.columns(3)
    cols[0].metric(copy.COLLAB["PULSE_TOTAL_LABEL"], _count(row["copubs_total"]))
    cols[1].metric(copy.COLLAB["PULSE_SHARE_LABEL"].format(name=names[a]), _pct(row["share_of_a"]))
    cols[2].metric(copy.COLLAB["PULSE_SHARE_LABEL"].format(name=names[b]), _pct(row["share_of_b"]))
    st.caption(copy.COLLAB["PULSE_SHARE_DENOM"].format(
        window=_window(collab_data.PULSE_YEARS), name_a=names[a], name_b=names[b],
        vol_a=_count(row["denominator_a"]), vol_b=_count(row["denominator_b"])))
    # DIRECTION: `rank_in_a` is where B sits among A's OWN partners (verified
    # against the shipped table: CNRS is Strasbourg's first partner, Strasbourg
    # is CNRS's sixteenth), so it is rendered as B's rank, never as A's.
    st.markdown(copy.COLLAB["PULSE_RANK_LINE"].format(
        name_a=names[a], name_b=names[b],
        rank_of_b=_count(row["rank_in_a"]), rank_of_a=_count(row["rank_in_b"])))
    st.markdown(_trend_line(row["yearly"]))
    st.caption(copy.COLLAB["PULSE_TREND_NOTE"].format(
        w1=_window(DYNAMICS_W1), w2=_window(DYNAMICS_W2), band=_pct(TREND_BAND),
        bonus_year=CFG["bonus_year"], star=BONUS_STAR))
    return row


# ----------------------------------------------- 2. the joint corpus --------

JOINT_VALUE_ORDER = ["vol_total", "vol_w1", "vol_w2", "vol_2025", "sdg_tagged_n"]
VOL_FORMAT = "%.1f"     # fractional volumes in the untapped table (see PCT_FORMAT's note)


def _joint_value_config() -> dict:
    """The five value columns every joint-corpus table shares, with the two
    dynamics windows and the partial year named IN the header rather than in a
    caption a reader has to hold in mind while scanning."""
    return {
        "vol_total": st.column_config.NumberColumn(copy.COLLAB["JOINT_COL_VOL"]),
        "vol_w1": st.column_config.NumberColumn(
            copy.COLLAB["JOINT_COL_W1"].format(w1=_window(DYNAMICS_W1))),
        "vol_w2": st.column_config.NumberColumn(
            copy.COLLAB["JOINT_COL_W2"].format(w2=_window(DYNAMICS_W2))),
        "vol_2025": st.column_config.NumberColumn(
            copy.COLLAB["JOINT_COL_BONUS"].format(bonus_year=CFG["bonus_year"], star=BONUS_STAR)),
        "sdg_tagged_n": st.column_config.NumberColumn(copy.COLLAB["JOINT_COL_SDG"]),
    }


def _render_joint(bundle: dict, a: str, b: str, scenario: dict, pulse_row: dict | None) -> None:
    """Section two (2B-R-10): what the pair's shared publications are about.

    BELOW THE FLOOR the section renders the honest notice and nothing else --
    no empty table, no zero. The joint total is already on screen above and the
    link-outs are still below, which is exactly what the notice promises."""
    ctx = bundle["ctx"]
    st.subheader(copy.COLLAB["JOINT_HEADER"])
    prof = _joint_frame(a, b, scenario["tree"], scenario["basis"])
    if prof is None:
        n_copubs = pulse_row["copubs_total"] if pulse_row else 0
        st.info(copy.COLLAB["TOPIC_BELOW_FLOOR_NOTICE"].format(
            n_copubs=_count(n_copubs), floor=collab_data.PAIR_TOPICS_FLOOR))
        return

    meta = prof["meta"]
    st.caption(copy.COLLAB["JOINT_INTRO"].format(cap=meta["top_n_cap"], floor=meta["floor"]))
    value_config = _joint_value_config()

    st.markdown(f"**{copy.COLLAB['JOINT_FIELDS_HEADER']}**")
    st.dataframe(prof["fields"], hide_index=True, width="stretch", key="tbl_joint_fields",
                 column_order=["field_name", *JOINT_VALUE_ORDER],
                 column_config={"field_name": st.column_config.TextColumn(
                     copy.COLLAB["JOINT_COL_FIELD"], width="medium"), **value_config})
    st.caption(copy.COLLAB["JOINT_WINDOW_NOTE"].format(
        w1=_window(DYNAMICS_W1), w2=_window(DYNAMICS_W2)))

    with st.expander(copy.COLLAB["JOINT_SUBFIELDS_HEADER"]):
        st.dataframe(prof["subfields"], hide_index=True, width="stretch", key="tbl_joint_subfields",
                     column_order=["subfield_name", "field_name", *JOINT_VALUE_ORDER],
                     column_config={
                         "subfield_name": st.column_config.TextColumn(
                             copy.COLLAB["JOINT_COL_SUBFIELD"], width="medium"),
                         "field_name": st.column_config.TextColumn(copy.COLLAB["JOINT_COL_FIELD"]),
                         **value_config})

    topics = prof["topics"].copy()
    flags = topics["topic_id"].map(_frontier_flags(ctx))
    topics["frontier"] = flags.map(_frontier_glyph)
    st.markdown(f"**{copy.COLLAB['JOINT_TOPICS_HEADER']}**")
    st.dataframe(topics, hide_index=True, width="stretch", key="tbl_joint_topics",
                 column_order=["topic_name", "subfield_name", *JOINT_VALUE_ORDER, "frontier"],
                 column_config={
                     "topic_name": st.column_config.TextColumn(copy.COLLAB["JOINT_COL_TOPIC"],
                                                               width="medium"),
                     "subfield_name": st.column_config.TextColumn(copy.COLLAB["JOINT_COL_SUBFIELD"]),
                     "frontier": st.column_config.TextColumn(copy.COLLAB["JOINT_COL_FRONTIER"],
                                                             help=copy.COLLAB["GAPS_FRONTIER_HELP"]),
                     **value_config})

    shown = float(pd.to_numeric(topics["vol_total"], errors="coerce").sum())
    tagged = int(prof["sdg_tagged_total"])
    st.markdown(copy.COLLAB["JOINT_SDG_LINE"].format(
        n_tagged=_count(tagged), n_shown=_count(shown),
        share=_pct(tagged / shown if shown > 0 else None)))
    st.markdown(copy.COLLAB["JOINT_FRONTIER_LINE"].format(
        n_frontier=_count(int(flags.eq(True).sum()))))

    # ERC: the panel share is read of the LABELLED works only (2BR A9); the
    # caption names what fraction of the joint corpus carries a label at all,
    # so the two denominators are never confused for one another.
    erc = prof["erc"]
    labelled, panel_n = erc["labelled_n"], erc["panel_n"]
    if labelled > 0:
        st.markdown(copy.COLLAB["JOINT_ERC_LINE"].format(
            panel=_erc_panel_label(ctx, erc["panel_idx"]), n_panel=_count(panel_n),
            n_labelled=_count(labelled), share=_pct(panel_n / labelled)))
        total = pulse_row["copubs_total"] if pulse_row else 0
        st.caption(copy.COLLAB["JOINT_ERC_CAPTION"].format(
            pct=_pct(labelled / total if total else None)))
    else:
        st.caption(copy.COLLAB["EMPTY_JOINT_ERC"])


# ------------------------------------------- 3. untapped potential ----------

def _render_untapped(bundle: dict, a: str, b: str, scenario: dict) -> None:
    """Section three (2B-R-10): topics both institutions hold where the joint
    output is below what the pair's OWN overall collaboration rate would
    predict, the adjacent topics beside them, and the 2B tables (the two
    directional gap lists, the weighted topic overlap, the breadth line) kept
    underneath because they answer the same reader's question."""
    ctx = bundle["ctx"]
    name_a, name_b = _name(ctx, a), _name(ctx, b)
    st.subheader(copy.COLLAB["UNTAPPED_HEADER"])
    res = _untapped_frame(a, b, scenario["tree"], scenario["basis"])
    topics = res["topics"]
    if topics.empty:
        st.info(copy.COLLAB["EMPTY_UNTAPPED"])
    else:
        st.dataframe(
            topics, hide_index=True, width="stretch", key="tbl_untapped",
            column_order=["topic_name", "subfield_name", "vol_a", "vol_b",
                          "joint_observed", "joint_expected", "gap"],
            column_config={
                "topic_name": st.column_config.TextColumn(copy.COLLAB["UNTAPPED_COL_TOPIC"],
                                                          width="medium"),
                "subfield_name": st.column_config.TextColumn(copy.COLLAB["UNTAPPED_COL_SUBFIELD"]),
                "vol_a": st.column_config.NumberColumn(
                    copy.COLLAB["UNTAPPED_COL_VOL_SIDE"].format(name=name_a), format=VOL_FORMAT),
                "vol_b": st.column_config.NumberColumn(
                    copy.COLLAB["UNTAPPED_COL_VOL_SIDE"].format(name=name_b), format=VOL_FORMAT),
                "joint_observed": st.column_config.NumberColumn(
                    copy.COLLAB["UNTAPPED_COL_OBSERVED"], format=VOL_FORMAT),
                "joint_expected": st.column_config.NumberColumn(
                    copy.COLLAB["UNTAPPED_COL_EXPECTED"], format=VOL_FORMAT),
                "gap": st.column_config.NumberColumn(copy.COLLAB["UNTAPPED_COL_GAP"],
                                                     format=VOL_FORMAT)})
        st.caption(copy.COLLAB["UNTAPPED_CAPTION"].format(k=_pct(res["k"])))
        st.caption(copy.COLLAB["UNTAPPED_RATE_NOTE"].format(
            window=_window(collab_data.PULSE_YEARS)))
        _download(topics, label=copy.COLLAB["DOWNLOAD_UNTAPPED"],
                  name=f"benchup_collab_untapped_{a}_{b}_{scenario['tree']}_{scenario['basis']}.csv",
                  key="dl_untapped")

    siblings = res["siblings"]
    if not siblings.empty:
        with st.expander(copy.COLLAB["SIBLINGS_HEADER"]):
            st.caption(copy.COLLAB["SIBLINGS_CAPTION"].format(n=_count(len(siblings))))
            st.dataframe(
                siblings, hide_index=True, width="stretch", key="tbl_siblings",
                column_order=["topic_name", "subfield_name", "vol_a", "vol_b"],
                column_config={
                    "topic_name": st.column_config.TextColumn(copy.COLLAB["SIBLINGS_COL_TOPIC"],
                                                              width="medium"),
                    "subfield_name": st.column_config.TextColumn(
                        copy.COLLAB["SIBLINGS_COL_SUBFIELD"]),
                    "vol_a": st.column_config.NumberColumn(
                        copy.COLLAB["UNTAPPED_COL_VOL_SIDE"].format(name=name_a), format=VOL_FORMAT),
                    "vol_b": st.column_config.NumberColumn(
                        copy.COLLAB["UNTAPPED_COL_VOL_SIDE"].format(name=name_b), format=VOL_FORMAT)})

    _render_gaps(bundle, a, b, scenario, key="gaps_a")
    _render_gaps(bundle, b, a, scenario, key="gaps_b")
    with st.expander(copy.COLLAB["SHARED_EXPANDER"]):
        _render_shared(bundle, a, b, scenario)
    _render_breadth(a, b, scenario)


# -------------------------------------------------------------- render ------

def render() -> None:
    """The whole Collaborate page. Computation order: sidebar scenario (so the
    tree/basis a reader carried from Find is read before anything is built) ->
    header -> pair picker -> substrates (behind A10's spinner) -> the four
    sections of 2B-R-10, in the order a reader meets the partnership: how much,
    about what, what is missing, where to read it."""
    bundle = _bundle()
    scenario = _sidebar_scenario()
    _sidebar_basket(bundle)
    _header(bundle)
    pair = _pair_picker(bundle, _candidates(bundle))
    if pair is None:
        return
    a, b = pair
    # A10: a tree/basis flip pays build_substrates ONCE (measured 4.6 s, cached,
    # at most three scenarios live); every other rerun finds it warm. The
    # spinner's copy says exactly that instead of leaving the page blank.
    with st.spinner(copy.COMPARE["SPINNER_SCENARIO"]):
        _subs(scenario["tree"], scenario["basis"])
    _header_strip(bundle, a, b)
    pulse_row = _render_pulse(bundle, a, b)
    _render_joint(bundle, a, b, scenario, pulse_row)
    _render_untapped(bundle, a, b, scenario)
    _render_links(bundle, a, b)

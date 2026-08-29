"""
tests/ui/smoke.py -- Playwright smoke test against the LIVE Streamlit server
(BUILD_PLAN_2A.md Stream H; extended for Refinement R1 stream R-H2, then for
Refinement R2 stream R2-H3 against S10.2 L29-L36 / S10.3's R2-H3 row).
Cross-page persistence is the load-bearing claim: the basket (a plain,
non-widget session_state list) and every keyed widget (persist_state="session")
-- INCLUDING the ones R1 moved out of the sidebar and the two R2 added
(`frontier_mode`, `breakdown_dim`) -- must survive real Menu<->Find navigation
with their widget KEYS unchanged.

R2 changes to this file (BUILD_PLAN_2A.md L29-L36): the sidebar's two
selectboxes now render DISPLAY labels (`copy.TREE_LABELS`/`BASIS_LABELS`) --
picking an option in the dropdown means clicking the LABEL text, never the
internal value, and the "Filtered by..." strip names the label too; the
profile carries eight `.benchup-kpi` tiles (`lib/tiles.py`), each with two
`.benchup-kpi-sub` sublines, the second always containing "index median"; the
Top-subfields panel lost its sort control and is cut at `SUBFIELDS_TOP_N`; the
frontier panel gained a `frontier_mode` segmented control INSIDE a collapsed
`st.expander` (its body still executes and its Plotly figure still mounts
while collapsed -- see the DOM-facts note below, this is what makes reading
its point count without re-opening it after a hop safe); tabs carry
`copy.LENS_NAMES` text ("L1 . Subfield overlap") instead of a bare code; a
"How to read the lenses" expander sits at the head of the Benchmark section.

Navigation uses the app's OWN sidebar nav link (`[data-testid="stSidebarNav"] a`)
for every Menu<->Find hop -- NEVER `page.goto()` for a persistence check.
`page.goto()` tears down and recreates the browser's WebSocket session, which
silently resets exactly the state a persistence test exists to catch and
produces a FALSE FAILURE (Lorraine Phase 2 tests/ui/smoke.py; Portfolio
Mapping INSPECTION_PLAYBOOK.md "Known pitfalls"). `goto` IS used for the very
first page load (a fresh/standalone load is what it is) and, deliberately,
inside `_find_undefined_l2f_seed`'s throwaway process (not this one).

All selectors are locale-independent: `.st-key-<key>` classes from the keyed
widgets/containers `app/lib/views_find.py` and `Menu.py` already emit,
`[role=...]`, `[data-testid=...]` -- text is read only via `textContent`
(never `innerText`, which is empty for a Streamlit tab panel that is not the
currently active one, AND empty for a collapsed `st.expander` body even though
that body's own DOM nodes exist -- confirmed by Stream E's probe,
app/ops/_probe_find.py) and only to ASSERT content, never to locate an element
(locating uses keyed classes, roles or DOM position -- e.g. "the second radio
option" -- never a literal label). Panel/tile/lens LABELS compared for exact
text are HARDCODED literals in this file (not imported from `lib/copy.py`):
importing the very string under test would make a renamed label compare
against itself and pass vacuously -- the point of non-vacuity proof (b) below.
`st.dataframe` renders a canvas grid with no real text nodes for cell values,
so row-level facts (the basket count, the seed heading, the strip, a CSV's own
header row) are read from captions/keyed containers/a real downloaded file,
never from a table cell.

Usage:
    python tests/ui/smoke.py --port 8611
    python tests/ui/smoke.py --port 8612 --app-dir "<throwaway copy of app/>"

Exit 0 iff every check passes, 1 otherwise. Prints one PASS/FAIL line per
check. Stdout is ASCII-only (cp1252 console) -- the SEP characters below are
the only non-ASCII bytes in this file, matched only against browser-rendered
UTF-8 text, never printed to stdout inside a PASS/FAIL message on their own.
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

import openpyxl
from playwright.sync_api import TimeoutError as PWTimeoutError
from playwright.sync_api import sync_playwright

DEFAULT_APP_DIR = Path(__file__).resolve().parents[2]  # tests/ui/smoke.py -> app/
WIDTHS = [1920, 1280, 390]
GDANSK_QUERY = "gdansk"
GDANSK_TAB_COUNT = 10          # Overview + 8 default lenses + Aspirational
L7_ON_TAB_COUNT = 11           # ... + the L7 toggle's own tab
ACTION_TIMEOUT_MS = 30_000     # time-box every wait so a hang FAILS, never blocks

SEP = "·"  # middle dot, matches lib/copy.py's own separator

# R2/L34: the top-subfields panel's display cut, hardcoded (not imported from
# lib/views_find.py) so a changed cut is a genuine DOM-vs-expectation mismatch,
# same reasoning as PANEL_LABELS below.
SUBFIELDS_TOP_N = 30

# R2/L30/L31: the profile's 2 x 4 (rendered as 4 rows x 2, VIZ_SPEC S2.11
# deviation) KPI tile grid, `lib/tiles.py`'s TILE_CLASS/SUBLINE_CLASS hooks.
N_TILES = 8

# R2/L29: the six profile chart panels, keyed `panel_<name>`, with their
# `copy.FIND["PANEL_*"]` header text (lib/copy.py) -- HARDCODED here (not
# re-imported from the app under test) so a renamed label in a throwaway copy
# is a real DOM-vs-expectation mismatch, never a comparison against itself.
# "Top {n} subfields" is filled with SUBFIELDS_TOP_N above, the one place this
# file types that number, mirroring how `lib/views_find.py::PANEL_LABEL_ARGS`
# fills the same template on the app side without ever typing it into copy.py.
PANEL_LABELS = [
    ("fields", "Fields"),
    ("subfields", f"Top {SUBFIELDS_TOP_N} subfields"),
    ("topics", "Top topics"),
    ("frontier", "Frontier positioning"),
    ("sdg", "SDG profile"),
    ("erc", "ERC profile"),
]

# R2/L29: sidebar display labels and the strip's rendering of an off-default
# taxonomy -- hardcoded literals from `lib/copy.py`'s TREE_LABELS/BASIS_LABELS/
# STRIP_TREE, same non-vacuity reasoning as PANEL_LABELS.
TREE_LABEL_BESTFIT = "Repaired taxonomy (best fit, default)"
TREE_LABEL_ORIGINAL = "OpenAlex taxonomy as published"
BASIS_LABEL_FRAC = "Fractional counting"
STRIP_TREE_ORIGINAL = f"taxonomy: {TREE_LABEL_ORIGINAL}"

# R2/L29: the lens guide header and the first default lens's tab label
# ([L0, L1, L3, F1, L2f, L4, L5, L6] per config.yaml `lenses.default`, so the
# first lens TAB after Overview is L0). Hardcoded literals from `lib/copy.py`.
LENS_GUIDE_HEADER = "How to read the lenses"
LENS0_TAB_TEXT = f"L0 {SEP} Field overlap"
LENS_LEGEND_SUBSTR = "see the lens guide above"

# R2/L33: the frontier panel's second mode button, by POSITION (nth(1)), never
# by its label text (same idiom as `breakdown_dim` below) -- both are
# `st.segmented_control`s and render as a row of real <button> elements.
FRONTIER_MODE_TOP_IDX, FRONTIER_MODE_EMERGING_IDX = 0, 1
BREAKDOWN_DOMAIN_IDX, BREAKDOWN_DOCTYPE_IDX = 0, 1

RESULTS: list[tuple[bool, str]] = []
PORT = 8611
BASE_URL = "http://127.0.0.1:8611"

# ---------------------------------------------------------------------------
# Phase 2B (BUILD_PLAN_2B.md Stream H): the full four-page narrative journey,
# Menu -> Find -> Compare -> Collaborate -> Methods (2B-10's order), appended
# after every R2 check above still passes. Distinct from the R2 "Basket"
# section (Sorbonne, Bologna, left in place -- untouched): this journey
# CLEARS the basket and rebuilds it from the Gdansk seed's own L1 (subfield
# overlap) ranking, so the compared set is a real top-overlap peer group
# rather than three arbitrary names, then walks it through Compare,
# Collaborate (via the real hand-off link) and Methods.
#
# Every label compared for exact text below is a HARDCODED literal (same
# non-vacuity reasoning as PANEL_LABELS above): copy.NAV's four narrative
# labels for the Menu cards, and the K/collab_data column-order contract from
# BUILD_PLAN_2B.md S4 for the shared-topics CSV header.
NAV_CARD_LABELS = ["Find peers", "Compare", "Collaborate", "How it is built"]
NAV_COMPARE, NAV_COLLAB, NAV_METHODS = "Compare", "Collaborate", "Methods"

COMPARE_MIN_FIGURES = 7        # ops/_probe_compare.py's own acceptance floor
CMP_FACETS_IDX, CMP_OVERLAY_IDX = 0, 1     # cmp_frontier_form: [facets, overlay]
CMP_FLOOR_HIGH_IDX, CMP_FLOOR_LOW_IDX = 0, 1  # cmp_impact_floor: IMPACT_FLOORS = (30, 10)

XLSX_METHODS_SHEET = "Methods"  # copy.COMPARE["XLSX_SHEET_METHODS"], hardcoded
XLSX_MIN_SHEETS = 8             # brief's floor; the shipped workbook carries 11 (10 views + Methods)

COLLAB_LINK_PREFIX = "/Collaborate"

# BUILD_PLAN_2B.md S4, the K -> V/C/L interface contract's own column order for
# `collab_data.shared_topics(...)`, hardcoded rather than imported from
# lib.collab_data.SHARED_TOPICS_COLS: importing the very constant the CSV
# export is built from would make this check compare that module against
# itself and pass vacuously if either drifted together.
SHARED_TOPICS_HEADER = ("topic_id,topic_name,subfield_name,share_a,share_b,"
                        "min_share,keywords,top25pct_frontier")

METHODS_MIN_SECTIONS = 10
PLACEHOLDER_RE = re.compile(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}")


def check(ok: bool, message: str) -> bool:
    RESULTS.append((bool(ok), message))
    print(("PASS: " if ok else "FAIL: ") + message)
    return bool(ok)


def fail_section(name: str, exc: Exception) -> None:
    check(False, f"{name}: raised {type(exc).__name__}: {exc}")


# ------------------------------------------------------------- server -------

def _wait_for_port(port: int, timeout: float = 60.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.5)
    return False


def _start_server(app_dir: Path, port: int) -> subprocess.Popen:
    # DEVNULL, not PIPE: every rerun logs a `use_container_width` deprecation
    # per st.dataframe call, which fills an unread pipe buffer and blocks the
    # server mid-probe (app/ops/_probe_find.py's own note).
    return subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "Menu.py",
         "--server.headless", "true", "--server.port", str(port),
         "--browser.gatherUsageStats", "false"],
        cwd=str(app_dir), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)


def _stop_server(server: subprocess.Popen) -> None:
    server.terminate()
    try:
        server.wait(timeout=10)
    except subprocess.TimeoutExpired:
        server.kill()
        server.wait(timeout=10)


# --------------------------------------------------------- DOM helpers ------

def _settle(page, ms: int = 2500) -> None:
    page.wait_for_timeout(ms)


def _wait_for(page, predicate, timeout_ms: int = 15_000, interval_ms: int = 300) -> bool:
    """Poll `predicate()` instead of a blind sleep -- needed after a scenario
    switch (tree/basis), which pays a real, measured cold `build_substrates`
    cost (~4.6 s, progress/R1_E2.md) the FIRST time that (tree, basis) pair is
    hit in this server process. A fixed `_settle` long enough for that one
    rebuild would be needlessly slow for every other, already-warm, rerun."""
    deadline = time.time() + timeout_ms / 1000
    while time.time() < deadline:
        if predicate():
            return True
        page.wait_for_timeout(interval_ms)
    return False


def _all_text(page, selector: str) -> str:
    """textContent (not innerText) joined across every match -- reads content
    inside an inactive Streamlit tab panel too (st.tabs runs every tab body
    every rerun; only the active panel has non-empty innerText), and inside a
    collapsed `st.expander` body (same story: the body executes and mounts,
    only the visual display folds -- lib/views_find.py's own docstring)."""
    return page.evaluate(
        "(sel) => Array.from(document.querySelectorAll(sel)).map(e => e.textContent).join('|')",
        selector)


def _full_page_text(page) -> str:
    """The whole body's textContent -- reaches text inside a collapsed
    `st.expander` too (see `_all_text`'s note), which a scoped selector like
    `[data-testid="stCaptionContainer"]` also would, but this is the broadest
    net for a page-wide "this string appears nowhere" negative claim."""
    return page.evaluate("document.body.textContent") or ""


def _no_exception(page, label: str) -> bool:
    return check(page.locator('[data-testid="stException"]').count() == 0,
                 f"{label}: no Streamlit exception on the page")


def _open_select(page, key: str) -> None:
    """Open a keyed selectbox: click it, wait for its (portal-rendered) option
    list. Streamlit 1.61's selectbox is a react-aria ComboBox, not a BaseWeb
    select -- `[data-baseweb='select']` always misses on this build, so the
    fallback (clicking the widget's own container) is what actually runs.
    That click reliably opens the listbox the FIRST time a given widget
    instance is used, but a SECOND, already-focused round on the SAME widget
    (e.g. a second sequential name typed into the same sidebar search box)
    can leave `aria-expanded="false"` after an identical click -- confirmed
    by reproduction (fill a second query into `basket_query`/`basket_pick`
    after one successful add: the click opens nothing, `ArrowDown` recovers
    it every time). `ArrowDown` is react-aria's own keyboard-accessible way
    to open a focused combobox, so it is the fallback here rather than a
    longer sleep or a second click, neither of which reproducibly recovers
    it."""
    loc = page.locator(f".st-key-{key} [data-baseweb='select']")
    if loc.count() == 0:
        loc = page.locator(f".st-key-{key}")
    loc.first.click(timeout=ACTION_TIMEOUT_MS)
    try:
        page.wait_for_selector('[role="option"]', timeout=3000)
    except PWTimeoutError:
        page.keyboard.press("ArrowDown")
        page.wait_for_selector('[role="option"]', timeout=ACTION_TIMEOUT_MS)


def _pick_option(page, text: str | None = None) -> None:
    opts = page.locator('[role="option"]')
    target = opts.filter(has_text=text).first if text else opts.first
    target.click(timeout=ACTION_TIMEOUT_MS)


def _selectbox_value(page, key: str) -> str:
    """A keyed selectbox's CURRENT selection -- the react-aria ComboBox
    input's own `value` property, not the container's text (measured on this
    build, ops/_probe_find.py::_selectbox_text: `inner_text`/`textContent` on
    the container returns the widget LABEL alone, never the selection)."""
    return page.locator(f".st-key-{key} input").first.input_value()


def _ensure_sidebar_open(page) -> None:
    """At a narrow viewport Streamlit collapses the sidebar (and its nav
    links) behind a hamburger control; open it first so the nav is
    interactable. A no-op when the sidebar is already expanded."""
    ctrl = page.locator('[data-testid="stSidebarCollapsedControl"] button, '
                         '[data-testid="stSidebarCollapsedControl"]')
    if ctrl.count() and ctrl.first.is_visible():
        ctrl.first.click(timeout=ACTION_TIMEOUT_MS)
        page.wait_for_timeout(500)


def _ensure_expander_open(page, key: str, probe_selector: str) -> None:
    """Open a keyed `st.expander` if its content is not currently visible.
    Every panel's/expander's body EXECUTES every rerun regardless of the
    expander's visual state (lib/views_find.py docstring), but that visual
    open/closed state resets to the coded `expanded=` default on the very next
    rerun -- so this is called before every interaction inside one, never
    assumed to still be open from an earlier action."""
    probe = page.locator(probe_selector).first
    if probe.count() == 0 or not probe.is_visible():
        page.locator(f".st-key-{key} summary").first.click(timeout=ACTION_TIMEOUT_MS)
        page.wait_for_timeout(700)


def _click_nav(page, label: str) -> None:
    """Real in-app sidebar nav-link click -- the ONLY way this file changes
    page for a persistence check (see module docstring). At a narrow (mobile)
    viewport the just-opened drawer can still be settling when Playwright's
    actionability check runs ("element is outside of the viewport"); scroll
    it into view and, failing that, force the click -- it is still a real
    click on the app's own nav link, never a `goto`."""
    _ensure_sidebar_open(page)
    link = page.locator('[data-testid="stSidebarNav"] a').filter(has_text=label).first
    link.wait_for(state="visible", timeout=ACTION_TIMEOUT_MS)
    try:
        link.click(timeout=ACTION_TIMEOUT_MS)
    except Exception:
        # A mobile drawer positions its nav links via a CSS transform, which
        # can put Playwright's own geometry check outside the viewport even
        # once the element is scrolled in and visually clickable. Dispatch a
        # real DOM click on the exact element instead -- still a genuine
        # click on the app's own link, never a `goto`.
        link.evaluate("el => el.click()")
    _settle(page, 3000)


def _basket_count(page) -> int:
    """One `key=f"rm_{iid}"` remove button per basket item (lib/views_find.py
    `_sidebar_basket`); partial-class match, same idiom as Stream A's own
    probe (`[class*='st-key-nav_card_']`)."""
    return page.locator('[class*="st-key-rm_"]').count()


def _seed_heading(page) -> str:
    return page.locator(".st-key-profile h3").first.text_content() or ""


def _strip_text(page) -> str:
    return _all_text(page, ".st-key-strip")


def _chip_legend(page) -> str:
    """The ONE chip legend the breakdown pair shares -- `charts.chip_legend_html`
    is the only markup on the page with a `flex-wrap` inline style, so this
    finds it without matching any user-facing string (ops/_probe_find.py's
    own idiom)."""
    return _all_text(page, '.st-key-profile div[style*="flex-wrap"]')


def _frontier_points(page) -> int:
    """Total marker count across the frontier scatter's own Plotly traces --
    read off the LIVE figure object (`el.data`), so the mode swap is verified
    on what is actually PLOTTED rather than on a caption the page prints. This
    reads correctly whether the `panel_frontier` expander is currently open or
    collapsed: the figure still mounts either way (module docstring)."""
    return page.evaluate(
        "(() => { const el = document.querySelector("
        "'.st-key-panel_frontier .js-plotly-plot');"
        " if (!el || !el.data) return -1;"
        " return el.data.reduce((a, t) => a + ((t.x && t.x.length) || 0), 0); })()")


def _erc_grid_tick_count(page) -> int:
    """R2/L34: the unit grid on the ERC panel's SI axis is drawn by setting
    `tickvals` at every integer up to the axis max (`lib/charts.py::fig_share_si`
    -- plotly draws a gridline at each tickval when `showgrid` stays at its
    default True, so the tick COUNT on that axis is the grid-line count). The
    SI axis is the LAST `xaxis*` key in the figure's own layout object (the
    share panel is `xaxis`, the SI panel is `xaxis2`) -- read directly off the
    live Plotly figure, not off a caption."""
    return page.evaluate(
        "(() => { const el = document.querySelector("
        "'.st-key-panel_erc .js-plotly-plot');"
        " if (!el || !el.layout) return -1;"
        " const keys = Object.keys(el.layout).filter(k => /^xaxis/.test(k)).sort();"
        " if (!keys.length) return 0;"
        " const ax = el.layout[keys[keys.length - 1]];"
        " return (ax && ax.tickvals) ? ax.tickvals.length : 0; })()")


def _search_and_pick(page, query: str, pick_key: str = "seed_pick",
                      query_key: str = "seed_query", option_text: str | None = None) -> None:
    box = page.locator(f".st-key-{query_key} input").first
    box.click(timeout=ACTION_TIMEOUT_MS)
    box.fill(query)
    box.press("Enter")
    _settle(page, 2500)
    _open_select(page, pick_key)
    _pick_option(page, option_text)
    _settle(page, 3000)


# ------------------------------------------------------ undefined-L2f seed --

def _find_undefined_l2f_seed(app_dir: Path, tree: str = "original") -> tuple[str, str] | None:
    """Smallest-first scan: the smaller an institution, the more likely L2f's
    own floor-of-papers-per-cell rule leaves it undefined. `tree="original"`
    matches the scenario the smoke flow has set by the time it reaches this
    check (Settings section)."""
    sys.path.insert(0, str(app_dir))
    from lib.data_cache import index
    from lib.engine import build_substrates, load_context, rank_all

    idx = index().sort_values("total_full_2020_2024")
    ctx = load_context(str(app_dir / "data"))
    subs = build_substrates(ctx, tree)
    for row in idx.itertuples(index=False):
        ranking = rank_all(ctx, subs, row.institution_id)
        l2f = ranking.get("L2f")
        if l2f and l2f.get("undefined"):
            return row.institution_id, row.display_name
    return None


# ------------------------------------------------------------- sections -----

def check_menu(page) -> None:
    page.goto(BASE_URL, wait_until="domcontentloaded")
    page.wait_for_selector('[data-testid="stSidebarNav"]', state="attached", timeout=ACTION_TIMEOUT_MS)
    _settle(page, 2000)
    check(page.get_by_role("heading").count() >= 1, "Menu: heading present")
    nav = page.locator(".st-key-nav_cards")
    check(nav.count() >= 1, "Menu: .st-key-nav_cards container present")
    cards = nav.locator("[class*='st-key-nav_card_']")
    # Manager fix 2026-08-29: on a COLD server the container can be present before
    # its cards have mounted (seen once: "found 0" on the first run after startup,
    # 105/105 on the re-run). Wait for the first card, then count -- a genuine
    # absence still fails the check below after the timeout.
    try:
        cards.first.wait_for(state="visible", timeout=ACTION_TIMEOUT_MS)
    except Exception:  # noqa: BLE001 -- the count check reports the failure
        pass
    check(cards.count() >= 3, f"Menu: >=3 nav cards (found {cards.count()})")
    find_link = nav.locator("a").filter(has_text="Find")
    check(find_link.count() >= 1, "Menu: Find card is live (st.page_link anchor present)")

    # 2B-10: all four narrative-order cards (Find peers, Compare, Collaborate,
    # How it is built) are live -- none renders the greyed ":grey[...]"
    # fallback Menu.py uses for a dimension whose page file does not exist yet.
    # A greyed card carries NO `st.page_link` anchor (only styled markdown +
    # caption text, which Streamlit's `:color[]` syntax renders as coloured
    # text, not a literal string in the DOM) -- so "none greyed" is proven
    # structurally, by anchor count, never by hunting for ":grey[" text.
    check(cards.count() == len(NAV_CARD_LABELS),
          f"Menu: exactly {len(NAV_CARD_LABELS)} nav cards render (found {cards.count()})")
    live_links = nav.locator("a")
    check(live_links.count() == len(NAV_CARD_LABELS),
          f"Menu: all {len(NAV_CARD_LABELS)} cards are live st.page_link anchors, none greyed "
          f"(found {live_links.count()} anchors, expected {len(NAV_CARD_LABELS)})")
    for label in NAV_CARD_LABELS:
        check(live_links.filter(has_text=label).count() >= 1,
              f"Menu: a live card links to {label!r}")
    _no_exception(page, "Menu")


def check_find_search(page) -> None:
    _click_nav(page, "Find")
    box = page.locator(".st-key-seed_query input")
    box.first.wait_for(state="visible", timeout=ACTION_TIMEOUT_MS)
    check(box.count() >= 1, "Find: seed search input present (.st-key-seed_query)")
    box.first.click(timeout=ACTION_TIMEOUT_MS)
    box.first.fill(GDANSK_QUERY)
    box.first.press("Enter")
    _settle(page, 2500)
    check(page.locator(".st-key-seed_pick").count() >= 1,
          "Find: results selectbox appeared after typing 'gdansk'")
    _open_select(page, "seed_pick")
    _pick_option(page)
    page.wait_for_selector('[role="tab"]', timeout=ACTION_TIMEOUT_MS)
    _settle(page, 3000)
    heading = _seed_heading(page)
    check("Gda" in heading, f"Find: seed profile heading contains 'Gda' (got {heading!r})")
    tabs = page.locator('[role="tab"]').count()
    check(tabs == GDANSK_TAB_COUNT, f"Find: default tab count is {GDANSK_TAB_COUNT} (got {tabs})")
    _no_exception(page, "Find (Gdansk seed)")


def _add_comparator(page, name: str) -> None:
    _search_and_pick(page, name, pick_key="basket_pick", query_key="basket_query")
    page.locator(".st-key-basket_add button").first.click(timeout=ACTION_TIMEOUT_MS)
    _settle(page, 2500)


def check_basket(page) -> None:
    _add_comparator(page, "Sorbonne")
    n1 = _basket_count(page)
    check(n1 == 1, f"Basket: 1 item after adding Sorbonne (got {n1})")
    _add_comparator(page, "Bologna")
    n2 = _basket_count(page)
    check(n2 == 2, f"Basket: 2 items after adding Bologna (got {n2})")
    _no_exception(page, "Basket add flow")


# --------------------------------------------------- controls / sidebar -----

def check_controls_placement(page) -> None:
    """L16: the sidebar holds ONLY the scenario selects (tree, basis) and
    the basket; depth/C1/L7/post-filters render in the MAIN area's controls
    row at the head of the Benchmark section, with their widget KEYS
    unchanged. The post-filters expander reveals the type/country filters,
    the country multiselect shows country NAMES, not codes. R2/L29: the
    scenario selectboxes render DISPLAY labels, never the internal value."""
    sidebar = page.locator('[data-testid="stSidebar"]')
    check(sidebar.locator(".st-key-tree").count() >= 1, "Sidebar: .st-key-tree (scenario) present")
    check(sidebar.locator(".st-key-basis").count() >= 1, "Sidebar: .st-key-basis (scenario) present")
    check(sidebar.locator(".st-key-depth").count() == 0, "Sidebar: no .st-key-depth")
    check(sidebar.locator(".st-key-f_types").count() == 0, "Sidebar: no .st-key-f_types")
    check(sidebar.locator(".st-key-c1_on").count() == 0, "Sidebar: no .st-key-c1_on")

    check(page.locator(".st-key-depth").count() >= 1,
          "Controls row: .st-key-depth renders in the main area")
    check(page.locator(".st-key-c1_on").count() >= 1,
          "Controls row: .st-key-c1_on renders in the main area")
    check(page.locator(".st-key-l7_on").count() >= 1,
          "Controls row: .st-key-l7_on renders in the main area")

    # R2/L29: the tree/basis selectboxes show their DISPLAY label; the
    # internal value never reaches the reader.
    tree_val = _selectbox_value(page, "tree")
    check(tree_val == TREE_LABEL_BESTFIT,
          f"Sidebar: taxonomy selectbox shows the default DISPLAY label (got {tree_val!r})")
    check("bestfit" not in tree_val, "Sidebar: the internal taxonomy value never appears")
    basis_val = _selectbox_value(page, "basis")
    check(basis_val == BASIS_LABEL_FRAC,
          f"Sidebar: counting-basis selectbox shows the default DISPLAY label (got {basis_val!r})")
    check("frac" not in basis_val.replace(BASIS_LABEL_FRAC, ""),
          "Sidebar: the internal counting-basis value never appears")

    _ensure_expander_open(page, "postfilters", ".st-key-f_types input")
    check(page.locator(".st-key-f_types").count() >= 1,
          "Post-filters expander: reveals .st-key-f_types")
    check(page.locator(".st-key-f_countries").count() >= 1,
          "Post-filters expander: reveals .st-key-f_countries")

    cinp = page.locator(".st-key-f_countries input").first
    cinp.click(timeout=ACTION_TIMEOUT_MS)
    cinp.fill("Fra")
    page.wait_for_selector('[role="option"]', timeout=ACTION_TIMEOUT_MS)
    opt = page.locator('[role="option"]').filter(has_text="France")
    check(opt.count() >= 1, "Country filter: typing 'Fra' surfaces an option containing 'France'")
    page.keyboard.press("Escape")
    _settle(page, 500)
    cinp.fill("")
    _no_exception(page, "Controls placement / sidebar labels / post-filters")


# ----------------------------------------------------------- R2 profile -----

def check_profile_and_panels(page) -> dict:
    """R2/L30-L34: the profile container, its 8 KPI tiles (each with an index
    baseline subline), its wordcloud, its six chart-panel expanders (exact
    labels), the top-subfields cut with no sort control, the SDG panel's
    numbered labels, the ERC panel's unit grid, the frontier panel's two
    modes, and the breakdown pair's segmented control.

    Returns `{"frontier_points": int, "breakdown_legend": str}`, the OFF-
    DEFAULT values this function deliberately leaves the page in (frontier
    mode swapped to "emerging", breakdown swapped to "Document type") -- the
    persistence checks compare against these exact values after later
    Menu<->Find hops instead of resetting them back here."""
    check(page.locator(".st-key-profile").count() == 1,
          "Profile: .st-key-profile container renders exactly once")
    check(page.locator('.st-key-profile [data-testid="stImage"] img').count() >= 1,
          "Profile: subfield wordcloud renders as an <img>")

    # ---- R2/L30/L31: the 8 KPI tiles -------------------------------------
    tiles = page.locator(".st-key-profile .benchup-kpi")
    check(tiles.count() == N_TILES, f"Profile: {N_TILES} KPI tiles render (found {tiles.count()})")
    sublines = page.locator(".st-key-profile .benchup-kpi-sub")
    n_sub = sublines.count()
    check(n_sub == N_TILES * 2, f"Profile: every tile carries two sublines (found {n_sub})")
    sub_texts = [sublines.nth(i).text_content() or "" for i in range(n_sub)]
    n_baseline = sum(1 for t in sub_texts if "index median" in t)
    check(n_baseline == N_TILES,
          f"Profile: every tile's second subline reads 'index median ...' (found {n_baseline} of {N_TILES})")
    check("Key figures" in _full_page_text(page), "Profile: 'Key figures' header renders")
    # R2/L32: the retired coverage line's ERC-classified-share phrase must not
    # leak anywhere on the page (its items were relocated into panel captions
    # under different wording -- lib/views_find.py `_erc_share`/CAPTION_ERC).
    check("ERC-classified share" not in _full_page_text(page),
          "Profile: the retired coverage-line phrase 'ERC-classified share' is nowhere on the page")

    # ---- R2/L29/L34: the six panels, exact labels -------------------------
    for name, label in PANEL_LABELS:
        summary = page.locator(f".st-key-panel_{name} summary").first
        check(summary.count() >= 1, f"Panel '{name}': expander present (.st-key-panel_{name})")
        # EXACT match, not a substring: `st.expander`'s summary text is the
        # label plus a leading icon-font ligature (e.g. "keyboard_arrow_right")
        # that varies by open/closed state -- stripped here so the comparison
        # is against the label alone. A substring check would let "Fields
        # Overview" satisfy an expected "Fields" and never catch a rename.
        raw = (summary.text_content() or "").strip()
        clean = raw.replace("keyboard_arrow_right", "").replace("keyboard_arrow_down", "").strip()
        check(clean == label, f"Panel '{name}': header label is exactly {label!r} (got {raw!r})")

    # ---- R2/L34: top subfields, no sort control, cut at SUBFIELDS_TOP_N --
    _ensure_expander_open(page, "panel_subfields", ".st-key-fig_subfields")
    _settle(page, 1500)
    fig = page.locator(".st-key-fig_subfields .js-plotly-plot").first
    check(fig.count() >= 1 and fig.is_visible(),
          "Panel Top subfields: opening it reveals a visible Plotly figure")
    check(page.locator(".st-key-panel_subfields .st-key-sort_subfields").count() == 0,
          "Panel Top subfields: carries NO sort control (R2/L34)")
    sf_ticks = page.locator(".st-key-fig_subfields .ytick")
    n_sf = sf_ticks.count()
    check(0 < n_sf <= SUBFIELDS_TOP_N,
          f"Panel Top subfields: {n_sf} y-tick group(s), within (0, {SUBFIELDS_TOP_N}]")

    # ---- R2/L36: SDG numbered labels --------------------------------------
    _ensure_expander_open(page, "panel_sdg", ".st-key-fig_sdg")
    _settle(page, 1500)
    sdg_ticks = page.locator(".st-key-fig_sdg .ytick")
    n_sdg = sdg_ticks.count()
    # Read the GROUP's textContent (not `.ytick text`): a wrapped two-line
    # label (`wrap_label`'s `<br>`) renders as separate <tspan> children of
    # one <text> node, and the GROUP's textContent concatenates every line
    # reliably regardless of how plotly splits them across nodes.
    sdg_texts = [sdg_ticks.nth(i).text_content() or "" for i in range(n_sdg)]
    non_sdg = [t for t in sdg_texts if not t.strip().startswith("SDG")]
    check(n_sdg > 0 and not non_sdg,
          f"Panel SDG profile: all {n_sdg} y-tick labels start with 'SDG' (offenders: {non_sdg})")

    # ---- R2/L34: ERC panel unit grid on the SI axis -----------------------
    _ensure_expander_open(page, "panel_erc", ".st-key-sort_erc [data-testid='stRadioOption']")
    _settle(page, 1500)
    n_grid = _erc_grid_tick_count(page)
    check(n_grid >= 1, f"Panel ERC profile: unit grid present on the SI axis ({n_grid} grid line(s))")

    # ---- R2/L33: frontier panel, two modes --------------------------------
    _ensure_expander_open(page, "panel_frontier", ".st-key-frontier_mode button")
    _settle(page, 1500)
    top_points = _frontier_points(page)
    check(top_points > 0, f"Panel Frontier positioning: default mode plots points ({top_points})")
    page.locator(".st-key-frontier_mode button").nth(FRONTIER_MODE_EMERGING_IDX).click(
        timeout=ACTION_TIMEOUT_MS)
    _settle(page, 4000)
    emerging_points = _frontier_points(page)
    check(emerging_points > 0 and emerging_points != top_points,
          f"Panel Frontier positioning: the mode control changes the plotted point count "
          f"({top_points} -> {emerging_points})")
    # Deliberately LEFT on "emerging": the persistence checks assert this
    # exact value survives later Menu<->Find hops (see this function's
    # docstring and README "R2 additions").

    # ---- R2/L30: the breakdown pair's shared segmented control ------------
    before_legend = _chip_legend(page)
    check(bool(before_legend.strip()), "Breakdown: chip legend renders")
    page.locator(".st-key-breakdown_dim button").nth(BREAKDOWN_DOCTYPE_IDX).click(
        timeout=ACTION_TIMEOUT_MS)
    _settle(page, 4000)
    after_legend = _chip_legend(page)
    check(after_legend != before_legend and bool(after_legend.strip()),
          "Breakdown: segmented control swaps the chip legend (domain <-> document type)")
    check(page.locator(".st-key-fig_breakdown_global .js-plotly-plot").first.is_visible()
          and page.locator(".st-key-fig_breakdown_yearly .js-plotly-plot").first.is_visible(),
          "Breakdown: both plotly figures still render after the swap")
    caption = _all_text(page, '[data-testid="stCaptionContainer"]')
    check("bonus year" in caption, "Breakdown: bonus-year caption is present")
    # Deliberately LEFT on "Document type": see this function's docstring.

    _no_exception(page, "Profile / panels")
    return {"frontier_points": emerging_points, "breakdown_legend": after_legend}


def check_benchmark_lens_guide(page) -> None:
    """R2/L29: the "How to read the lenses" expander at the head of the
    Benchmark section (one line per shown lens, >= 8 by default), tabs
    carrying `copy.LENS_NAMES` text, and the Overview's legend caption
    pointing back at the guide."""
    _ensure_expander_open(page, "lens_guide", ".st-key-lens_guide strong")
    summary = page.locator(".st-key-lens_guide summary").first
    raw = (summary.text_content() or "").strip()
    clean = raw.replace("keyboard_arrow_right", "").replace("keyboard_arrow_down", "").strip()
    check(clean == LENS_GUIDE_HEADER,
          f"Lens guide: header label is exactly {LENS_GUIDE_HEADER!r} (got {raw!r})")
    n_lines = page.locator(".st-key-lens_guide strong").count()
    check(n_lines >= 8, f"Lens guide: at least 8 lens lines render (found {n_lines})")

    tabs = page.locator('[role="tab"]')
    first_lens_text = tabs.nth(1).text_content() or ""
    check(LENS0_TAB_TEXT in first_lens_text,
          f"Tabs: the first default-lens tab carries its LENS_NAMES text "
          f"(expected {LENS0_TAB_TEXT!r} in {first_lens_text!r})")

    caption = _all_text(page, '[data-testid="stCaptionContainer"]')
    check(LENS_LEGEND_SUBSTR in caption,
          f"Overview: the legend caption points at the lens guide (looking for {LENS_LEGEND_SUBSTR!r})")
    _no_exception(page, "Benchmark lens guide")


# ----------------------------------------------------------- R1 tables -----

def _download_csv_header(page, click_selector: str) -> str:
    with page.expect_download(timeout=ACTION_TIMEOUT_MS) as dl_info:
        page.locator(click_selector).click(timeout=ACTION_TIMEOUT_MS)
    download = dl_info.value
    path = download.path()
    with open(path, "r", encoding="utf-8") as fh:
        return fh.readline()


def check_tables_and_export(page) -> None:
    """VIZ_SPEC S1.7/S2.5, L22: a lens's ranked table renders; its CSV export
    carries `total_frac_2020_2024`, `country` (the NAME column) and `evidence`
    but never a `badge` column (badges moved to the profile header only); the
    Aspirational tab renders its own table. Lens CODES stay the CSV/table key
    material (L29: codes are stable identifiers) even though the TAB text now
    carries the lens's name."""
    tabs = page.locator('[role="tab"]')
    tabs.nth(1).click(timeout=ACTION_TIMEOUT_MS)  # first default lens tab (L0)
    _settle(page, 2000)
    check(page.locator('.st-key-tbl_L0 [data-testid="stDataFrame"]').count() >= 1,
          "Lens table: L0's ranked table renders (.st-key-tbl_L0)")

    header = _download_csv_header(page, ".st-key-dl_L0 button")
    check("total_frac_2020_2024" in header, f"CSV export: header carries total_frac_2020_2024 ({header!r})")
    check("country" in header, f"CSV export: header carries country ({header!r})")
    check("evidence" in header, f"CSV export: header carries evidence ({header!r})")
    check("badge" not in header, f"CSV export: header carries NO badge column ({header!r})")

    tabs.last.click(timeout=ACTION_TIMEOUT_MS)  # Aspirational
    _settle(page, 2500)
    check(page.locator('.st-key-tbl_aspirational [data-testid="stDataFrame"]').count() >= 1,
          "Aspirational tab: its own table renders (.st-key-tbl_aspirational)")
    tabs.nth(0).click(timeout=ACTION_TIMEOUT_MS)  # back to Overview
    _settle(page, 1500)
    _no_exception(page, "Tables / export")


# ------------------------------------------------------------- settings ----

def check_settings(page) -> None:
    """R2: the settings a reader would touch on a first visit -- all in the
    Benchmark controls row/expander instead of the sidebar -- set here BEFORE
    the persistence hops (depth to max, L7 on, a type filter picked, tree
    switched to its non-default DISPLAY label). `frontier_mode` and
    `breakdown_dim` are ALREADY off-default from check_profile_and_panels and
    are left untouched here -- see that function's docstring."""
    before = _all_text(page, '[data-testid="stCaptionContainer"]')

    _ensure_expander_open(page, "postfilters", ".st-key-f_types input")
    tinp = page.locator(".st-key-f_types input").first
    tinp.click(timeout=ACTION_TIMEOUT_MS)
    tinp.fill("education")
    page.wait_for_selector('[role="option"]', timeout=ACTION_TIMEOUT_MS)
    page.locator('[role="option"]').filter(has_text="education").first.click(timeout=ACTION_TIMEOUT_MS)
    _settle(page, 3500)

    page.locator('.st-key-depth [data-testid="stRadioOption"]').last.click(timeout=ACTION_TIMEOUT_MS)
    _settle(page, 3000)
    after = _all_text(page, '[data-testid="stCaptionContainer"]')
    check(before != after, "Settings: depth caption changed after switching depth to its max")

    # R2/L29: the option clicked in the dropdown is the DISPLAY label, not the
    # internal value "original" -- `format_func` changes what is rendered in
    # the option list too.
    _open_select(page, "tree")
    _pick_option(page, TREE_LABEL_ORIGINAL)
    # tree="original" is a NEW (tree, basis) pair for this server process --
    # its substrates build cold (~4.6 s measured), so this waits for actual
    # tab re-render rather than a blind sleep (a fixed 3 s here was an
    # intermittent flake on a cold throwaway copy, unrelated to any mutation).
    _wait_for(page, lambda: page.locator('[role="tab"]').count() >= GDANSK_TAB_COUNT)
    _settle(page, 1000)

    page.locator(".st-key-l7_on label").first.click(timeout=ACTION_TIMEOUT_MS)
    _wait_for(page, lambda: page.locator('[role="tab"]').count() == L7_ON_TAB_COUNT)
    _settle(page, 800)
    tabs = page.locator('[role="tab"]').count()
    check(tabs == L7_ON_TAB_COUNT, f"Settings: L7 tab appeared, tab count is {L7_ON_TAB_COUNT} (got {tabs})")

    check(page.locator(".st-key-strip").count() >= 1, "Settings: off-default strip is visible")
    strip = _strip_text(page)
    check(STRIP_TREE_ORIGINAL in strip,
          f"Settings: strip shows the taxonomy's DISPLAY label (looking for {STRIP_TREE_ORIGINAL!r} "
          f"in {strip!r})")
    check("original" not in strip.replace(TREE_LABEL_ORIGINAL, ""),
          "Settings: the internal taxonomy value never appears in the strip")
    check("depth = 50" in strip, f"Settings: strip mentions depth = 50 (strip: {strip!r})")
    check("type: " in strip and "education" in strip,
          f"Settings: strip mentions the type filter (strip: {strip!r})")
    _no_exception(page, "Settings")


def _capture_persisted_state(page) -> dict:
    # `_ensure_expander_open` guarantees the frontier figure is mounted and
    # readable regardless of whatever visual open/closed state a fresh page
    # mount coded it to -- see `_frontier_points`'s own docstring for why
    # reading it without this call should already be safe, and why this call
    # is still made (belt and suspenders around that claim).
    _ensure_expander_open(page, "panel_frontier", ".st-key-frontier_mode button")
    return {"basket": _basket_count(page), "tabs": page.locator('[role="tab"]').count(),
            "heading": _seed_heading(page), "strip": _strip_text(page),
            "frontier_points": _frontier_points(page), "breakdown_legend": _chip_legend(page)}


def _assert_persisted(state: dict, tag: str, expect: dict) -> None:
    check(state["basket"] == 2, f"{tag}: basket still lists 2 items (got {state['basket']})")
    check(state["tabs"] == L7_ON_TAB_COUNT,
          f"{tag}: L7 tab still present, tab count {L7_ON_TAB_COUNT} (got {state['tabs']})")
    check("Gda" in state["heading"], f"{tag}: seed still selected, heading 'Gda...' (got {state['heading']!r})")
    check(STRIP_TREE_ORIGINAL in state["strip"], f"{tag}: taxonomy's display label still in the strip")
    check("depth = 50" in state["strip"], f"{tag}: depth still at max in the strip")
    check("type: " in state["strip"] and "education" in state["strip"],
          f"{tag}: type filter (education) still active in the strip")
    fp_expected = expect.get("frontier_points")
    check(fp_expected is not None and state["frontier_points"] == fp_expected,
          f"{tag}: frontier_mode still shows its off-default (emerging) point count "
          f"(expected {fp_expected}, got {state['frontier_points']})")
    bl_expected = expect.get("breakdown_legend")
    check(bool(bl_expected) and state["breakdown_legend"] == bl_expected,
          f"{tag}: breakdown_dim still shows the swapped (document-type) chip legend")


def check_persistence(page, expect: dict) -> None:
    """The load-bearing claim: basket + every keyed widget -- INCLUDING the
    ones R1 relocated from the sidebar into the controls row/expander AND the
    two R2 added (`frontier_mode`, `breakdown_dim`) -- survive real Menu<->Find
    hops (4 hops total: Menu, Find, Menu, Find), with a second-visit re-mount
    check at the 2-hop midpoint (a bug that only shows up on a widget's SECOND
    mount is a real, documented failure mode -- Portfolio Mapping
    INSPECTION_PLAYBOOK.md family 3)."""
    _assert_persisted(_capture_persisted_state(page), "Persistence: baseline captured before any hop", expect)

    _click_nav(page, "Menu")
    _no_exception(page, "Menu (hop 1 of 4)")
    _click_nav(page, "Find")
    _no_exception(page, "Find (hop 2 of 4, second-visit re-mount)")
    _assert_persisted(_capture_persisted_state(page), "Persistence: 2nd Find visit (re-mount check)", expect)

    _click_nav(page, "Menu")
    _no_exception(page, "Menu (hop 3 of 4)")
    _click_nav(page, "Find")
    _no_exception(page, "Find (hop 4 of 4, final)")
    _assert_persisted(_capture_persisted_state(page), "Persistence: 3rd Find visit (after 4 hops)", expect)


def check_type_filter_clear(page) -> None:
    """The type filter set in Settings and proven to survive the hops above
    can also be CLEARED, and the strip stops naming it once it is."""
    strip = _strip_text(page)
    check("type: " in strip and "education" in strip,
          f"Type filter: still active going into the clear check (strip: {strip!r})")
    _ensure_expander_open(page, "postfilters", ".st-key-f_types input")

    tag_close = page.locator(".st-key-f_types [data-baseweb='tag'] [role='button'], "
                              ".st-key-f_types [data-baseweb='tag'] svg")
    if tag_close.count():
        tag_close.first.click(timeout=ACTION_TIMEOUT_MS)
    else:
        page.locator(".st-key-f_types input").first.click(timeout=ACTION_TIMEOUT_MS)
        page.keyboard.press("Backspace")
    _settle(page, 3500)
    strip2 = _strip_text(page)
    check("education" not in strip2, f"Type filter: strip no longer names it after clearing (strip: {strip2!r})")
    _no_exception(page, "Type filter cleared")


def check_undefined_lens(page, seed_id: str, seed_name: str) -> None:
    _search_and_pick(page, seed_name)
    heading = _seed_heading(page)
    check(len(heading) > 0, f"Undefined lens: seed '{seed_name}' ({seed_id}) loaded, heading present")
    tab = page.locator('[role="tab"]').filter(has_text="L2f").first
    check(tab.count() >= 1, "Undefined lens: L2f tab present")
    tab.click(timeout=ACTION_TIMEOUT_MS)
    _settle(page, 1500)
    text = _all_text(page, '[role="tabpanel"]')
    check("L2f" in text and "cannot be computed for this seed" in text,
          f"Undefined lens: L2f undefined message present for {seed_name}")
    _no_exception(page, "Undefined L2f seed")


def check_subfields_panel_no_overlap(page, width: int) -> None:
    """R2/L34/L35 (this stream's adaptation of fix X3's finding I-4): bounding-
    box proof that opening the TOP-SUBFIELDS panel at this width never lets a
    y-axis tick label collide with anything, now that a long subfield name can
    WRAP onto two lines (L35's `wrap_label`) instead of being ellipsised. A
    wrapped label renders as separate `<tspan>` children of ONE `<text>` node,
    so this reads and bounding-boxes the `.ytick` GROUP (not `.ytick text`):
    the group's own bounding box correctly spans both lines, and its
    textContent concatenates every tspan reliably. Every `.ytick` box must lie
    fully inside its plot's own `.main-svg`, never clipped past the left edge
    (where the old collision put the leading characters underneath the volume
    gutter) and never overflowing the right edge either. A page-level
    scrollWidth check cannot see this: it is a collision INSIDE one chart's
    own layout, not a page overflow."""
    fig = page.locator(".st-key-fig_subfields .js-plotly-plot").first
    fig.wait_for(state="visible", timeout=ACTION_TIMEOUT_MS)
    plot_box = fig.locator(".main-svg").first.bounding_box()
    if plot_box is None:
        check(False, f"Top-subfields panel {width}px: could not read the plot's own .main-svg bounding box")
        return
    ticks = fig.locator(".ytick")
    n = ticks.count()
    plot_left = plot_box["x"]
    plot_right = plot_box["x"] + plot_box["width"]
    offenders = []
    for i in range(n):
        box = ticks.nth(i).bounding_box()
        if box is None:
            continue
        text = ticks.nth(i).text_content() or ""
        # a 1px slack absorbs sub-pixel rounding, never a real clip/overflow
        if box["x"] < plot_left - 1:
            offenders.append(f"{text!r} clipped at left (x={box['x']:.1f} < plot left {plot_left:.1f})")
        elif box["x"] + box["width"] > plot_right + 1:
            offenders.append(f"{text!r} overflows right "
                             f"(right={box['x'] + box['width']:.1f} > plot right {plot_right:.1f})")
    check(n > 0 and not offenders,
          f"Top-subfields panel {width}px: {n} y-tick group(s) all stay inside the plot's own svg"
          + (f" -- offenders: {offenders}" if offenders else ""))


def check_screenshots(browser, shot_dir: Path) -> None:
    """At each width, the seed is loaded AND the Top-subfields panel is opened
    before the scrollWidth assertion -- the widest real state the page can be
    in, not just the collapsed default.

    A bounding-box no-overlap check on the open Top-subfields panel runs at
    390 px AND 1280 px (R2/L34/L35's wrapped, two-line ticks); a plain
    (non-full-page) top-of-page screenshot at 1280 px, scrolled to y=0 with
    the seed loaded but BEFORE any panel is opened; and a dedicated 390 px
    screenshot with the Top-subfields panel open."""
    shot_dir.mkdir(parents=True, exist_ok=True)
    for width in WIDTHS:
        page = browser.new_page(viewport={"width": width, "height": 900})
        page.set_default_timeout(ACTION_TIMEOUT_MS)
        try:
            page.goto(BASE_URL, wait_until="domcontentloaded")
            page.wait_for_selector('[data-testid="stSidebarNav"]', state="attached",
                                    timeout=ACTION_TIMEOUT_MS)
            _settle(page, 1500)
            scroll = page.evaluate("document.documentElement.scrollWidth")
            inner = page.evaluate("window.innerWidth")
            check(scroll <= inner + 2, f"Menu {width}px: scrollWidth {scroll} <= innerWidth+2 {inner + 2}")
            p = shot_dir / f"smoke_menu_{width}.png"
            page.screenshot(path=str(p), full_page=True)
            check(p.is_file(), f"Menu {width}px: screenshot written ({p.name})")

            _click_nav(page, "Find")
            _search_and_pick(page, GDANSK_QUERY)

            if width == 1280:
                # The untouched top of the page -- header/tiles/wordcloud --
                # BEFORE any expander is opened, viewport-only (not full_page)
                # so it is actually scrolled to y=0, not just stitched in as
                # the top slice of a taller image.
                page.evaluate("window.scrollTo(0, 0)")
                _settle(page, 500)
                top_p = shot_dir / "smoke_find_top_1280.png"
                page.screenshot(path=str(top_p), full_page=False)
                check(top_p.is_file(), f"Find top-of-page 1280px: screenshot written ({top_p.name})")

            _ensure_expander_open(page, "panel_subfields", ".st-key-fig_subfields")
            _settle(page, 1500)
            scroll = page.evaluate("document.documentElement.scrollWidth")
            inner = page.evaluate("window.innerWidth")
            check(scroll <= inner + 2, f"Find {width}px: scrollWidth {scroll} <= innerWidth+2 {inner + 2}")
            p2 = shot_dir / f"smoke_find_{width}.png"
            page.screenshot(path=str(p2), full_page=True)
            check(p2.is_file(), f"Find {width}px: screenshot written ({p2.name})")

            if width in (390, 1280):
                check_subfields_panel_no_overlap(page, width)
            if width == 390:
                subfields_p = shot_dir / "smoke_find_subfields_390.png"
                page.screenshot(path=str(subfields_p), full_page=True)
                check(subfields_p.is_file(),
                      f"Find Top-subfields panel 390px: screenshot written ({subfields_p.name})")
        except Exception as exc:  # noqa: BLE001 -- one width's failure must not skip the rest
            fail_section(f"Screenshots at {width}px", exc)
        finally:
            page.close()


# ------------------------------------------------ Phase 2B: the full journey --

def _n_plotly(page) -> int:
    return page.locator(".js-plotly-plot").count()


def _settle_figures(page, target: int, timeout_ms: int = 60_000) -> int:
    """Streamlit streams elements in, so a figure count climbs for a while
    after the first plot appears (ops/_probe_compare.py's own `_settle`
    documents the same fact for this page). Poll until the count reaches the
    floor and holds for 3 checks running, rather than a blind sleep -- the
    same reasoning as `_wait_for` above, applied to a count instead of a
    boolean predicate."""
    deadline = time.time() + timeout_ms / 1000
    last, stable = -1, 0
    while time.time() < deadline:
        now = _n_plotly(page)
        stable = stable + 1 if now == last and now >= target else 0
        last = now
        if stable >= 3:
            break
        page.wait_for_timeout(800)
    page.wait_for_timeout(1000)
    return last


def _sidebar_basket_n(page) -> int | None:
    """The `{n} of {cap} added` sidebar caption (copy.FIND["BASKET_COUNT"]),
    read wherever it renders: Find's own editable basket AND Compare/
    Collaborate's read-only mirror share the exact same template. Necessary
    because `_basket_count` (this file's existing helper) counts `rm_{iid}`
    remove buttons, which exist ONLY on Find's editable list -- Compare and
    Collaborate render the basket read-only (a plain `sb.write` per name, no
    remove button), so they need a different signal for the same fact."""
    text = _all_text(page, '[data-testid="stSidebar"] [data-testid="stCaptionContainer"]')
    m = re.search(r"(\d+) of \d+ added", text)
    return int(m.group(1)) if m else None


def _add_l1_candidates(page) -> list[dict]:
    """Downloads the seed's own L1 (subfield-overlap) ranking CSV and returns
    the top 3 rows' `{institution_id, display_name}` -- REAL top-overlap
    peers of the seed, not three names picked out of thin air. `st.tabs`
    keeps every tab's body mounted every rerun (module docstring), so the L1
    download button already exists in the DOM before the tab is clicked into;
    it is clicked anyway for a realistic sequence and so the export reflects
    whatever is visibly on screen."""
    tab = page.locator('[role="tab"]').filter(has_text="L1").first
    tab.click(timeout=ACTION_TIMEOUT_MS)
    _settle(page, 1500)
    with page.expect_download(timeout=ACTION_TIMEOUT_MS) as dl_info:
        page.locator(".st-key-dl_L1 button").first.click(timeout=ACTION_TIMEOUT_MS)
    path = dl_info.value.path()
    with open(path, "r", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    return [{"institution_id": r["institution_id"], "display_name": r["display_name"]}
            for r in rows[:3] if r.get("institution_id")]


def check_journey_basket(page) -> list[dict]:
    """BUILD_PLAN_2B.md Stream H brief: search Gdansk, add 3 candidates off
    the L1 table plus the seed itself, both via the SAME sidebar add box the
    existing "Basket" section above already exercises (`_add_comparator`) --
    basket = 4. The basket is cleared first: the R2 "Basket" section above
    left Sorbonne + Bologna in it, and `check_undefined_lens` moved the seed
    away from Gdansk, so this is a genuine fresh start, not a continuation."""
    clear_btn = page.locator(".st-key-basket_clear button")
    if clear_btn.count():
        clear_btn.first.click(timeout=ACTION_TIMEOUT_MS)
        _settle(page, 1500)
    _search_and_pick(page, GDANSK_QUERY)
    heading = _seed_heading(page)
    check("Gda" in heading,
          f"Journey: seed re-loaded to Gdansk before building the basket (got {heading!r})")
    candidates = _add_l1_candidates(page)
    check(len(candidates) == 3, f"Journey: read 3 candidates off the L1 CSV (got {len(candidates)})")
    for row in candidates:
        _add_comparator(page, row["display_name"])
    _add_comparator(page, GDANSK_QUERY)  # the seed itself, same sidebar add box
    n = _basket_count(page)
    check(n == 4, f"Journey: basket holds 4 (3 L1 candidates + the seed itself), got {n}")
    _no_exception(page, "Journey basket (L1 candidates + seed)")
    return candidates


def _compare_deeplink_ids(page) -> list[str]:
    """The `?compare=` deep link `_selection` prints via `st.code` -- located
    by its own fixed prefix (a data-contract string, 2B-8), never by DOM
    position, since a second `st.code` (the `?pair=` hand-off link) appears
    lower on the same page once >= 2 institutions are compared."""
    loc = page.locator('[data-testid="stCode"]').filter(has_text="?compare=").first
    if loc.count() == 0:
        return []
    text = loc.text_content() or ""
    if "?compare=" not in text:
        return []
    return text.split("?compare=", 1)[1].strip().split(",")


def check_compare_journey(page, candidates: list[dict]) -> dict:
    """The Compare leg: strip + legend + figure floor, the frontier Layout
    control, the impact floor toggle, the workbook, the deep link, reorder,
    remove. Returns `{"remaining_ids": [...]}` (unused downstream today, kept
    for a future stream that wants the post-removal id set without re-reading
    the page)."""
    _click_nav(page, NAV_COMPARE)
    _settle_figures(page, COMPARE_MIN_FIGURES)
    _no_exception(page, "Compare (initial render)")

    names = [c["display_name"] for c in candidates]
    strip = _all_text(page, ".st-key-compare_strip")
    for name in names:
        check(name in strip, f"Compare: strip names the L1 candidate {name!r}")
    check("Gda" in strip, f"Compare: strip also names the seed institution (strip[:200]={strip[:200]!r})")

    legend_hits = page.evaluate(
        "(names) => Array.from(document.querySelectorAll('[data-testid=\"stMarkdownContainer\"]'))"
        ".filter(e => names.every(n => e.textContent.includes(n))"
        " && e.querySelectorAll('span').length >= names.length * 2).length",
        names)
    check(legend_hits >= 1,
          f"Compare: at least one legend strip carries all {len(names)} named L1 candidates "
          f"with >= 2 swatches each (found {legend_hits} such strips)")

    n_figs = _n_plotly(page)
    check(n_figs >= COMPARE_MIN_FIGURES,
          f"Compare: >= {COMPARE_MIN_FIGURES} plotly figures render ({n_figs})")

    ids4 = _compare_deeplink_ids(page)
    check(len(ids4) == 4, f"Compare: the deep link names exactly 4 ids (got {len(ids4)}: {ids4})")
    l1_ids = [c["institution_id"] for c in candidates]
    check(all(i in ids4 for i in l1_ids),
          f"Compare: the deep link carries all 3 L1 candidate ids ({l1_ids} vs {ids4})")

    # --- the frontier Layout control: facets <-> overlay ---------------------
    facets_panels = page.evaluate(
        "(() => { const e = document.querySelector('.st-key-cmp_frontier_plot');"
        " return e ? e.querySelectorAll('g.subplot').length : -1; })()")
    check(facets_panels > 1, f"Compare: frontier defaults to small multiples ({facets_panels} panels)")
    page.locator(".st-key-cmp_frontier_form button").nth(CMP_OVERLAY_IDX).click(timeout=ACTION_TIMEOUT_MS)
    _settle(page, 2500)
    overlay_panels = page.evaluate(
        "(() => { const e = document.querySelector('.st-key-cmp_frontier_plot');"
        " return e ? e.querySelectorAll('g.subplot').length : -1; })()")
    check(overlay_panels == 1, f"Compare: the Layout control switches to one overlay plane ({overlay_panels})")
    page.locator(".st-key-cmp_frontier_form button").nth(CMP_FACETS_IDX).click(timeout=ACTION_TIMEOUT_MS)
    _settle(page, 2500)

    # --- the impact floor toggle ----------------------------------------------
    before_caps = _all_text(page, '[data-testid="stCaptionContainer"]')
    page.locator('.st-key-cmp_impact_floor [data-testid="stRadioOption"]').nth(
        CMP_FLOOR_LOW_IDX).click(timeout=ACTION_TIMEOUT_MS)
    _settle(page, 2500)
    after_caps = _all_text(page, '[data-testid="stCaptionContainer"]')
    check(before_caps != after_caps, "Compare: the impact floor toggle changes the page's captions")
    page.locator('.st-key-cmp_impact_floor [data-testid="stRadioOption"]').nth(
        CMP_FLOOR_HIGH_IDX).click(timeout=ACTION_TIMEOUT_MS)
    _settle(page, 2500)

    # --- the workbook ----------------------------------------------------------
    with page.expect_download(timeout=120_000) as dl_info:
        page.locator(".st-key-dl_workbook button").first.click(timeout=ACTION_TIMEOUT_MS)
    raw = Path(dl_info.value.path()).read_bytes()
    check(raw[:2] == b"PK", "Compare: the workbook downloads as a real xlsx container")
    book = openpyxl.load_workbook(io.BytesIO(raw))
    check(len(book.sheetnames) >= XLSX_MIN_SHEETS,
          f"Compare: the workbook carries >= {XLSX_MIN_SHEETS} sheets ({len(book.sheetnames)}: "
          f"{book.sheetnames})")
    check(XLSX_METHODS_SHEET in book.sheetnames,
          f"Compare: the workbook carries a {XLSX_METHODS_SHEET!r} sheet ({book.sheetnames})")

    # --- reorder: Down on the FIRST row changes the printed selection order ---
    before_ids = _compare_deeplink_ids(page)
    page.locator('[class*="st-key-cmp_down_"] button').first.click(timeout=ACTION_TIMEOUT_MS)
    _settle(page, 2000)
    after_ids = _compare_deeplink_ids(page)
    check(len(after_ids) == len(before_ids) == 4 and after_ids != before_ids
          and set(after_ids) == set(before_ids),
          f"Compare: Down on the first row changes the selection order, same 4 ids "
          f"({before_ids} -> {after_ids})")

    # --- remove one -> 3 names -------------------------------------------------
    page.locator('[class*="st-key-cmp_rm_"] button').first.click(timeout=ACTION_TIMEOUT_MS)
    _settle_figures(page, COMPARE_MIN_FIGURES)
    remaining_ids = _compare_deeplink_ids(page)
    check(len(remaining_ids) == 3, f"Compare: removing one institution leaves 3 (got {len(remaining_ids)})")
    _no_exception(page, "Compare (after reorder + remove)")
    return {"remaining_ids": remaining_ids}


def _pair_deeplink_ids(page) -> list[str]:
    loc = page.locator('[data-testid="stCode"]').filter(has_text="?pair=").first
    if loc.count() == 0:
        return []
    text = loc.text_content() or ""
    if "?pair=" not in text:
        return []
    return text.split("?pair=", 1)[1].strip().split(",")


def check_handoff(page, context) -> None:
    """2B-8's hand-off: force the Compare hand-off's B selectbox to the LAST
    option (with 3 candidates remaining, the default pair is the first two --
    picking the third guarantees a NON-default pair), then follow the
    rendered link with a REAL click -- located by its own `href` prefix
    (`/Collaborate?pair=`, a data-contract string), never by a button label,
    since `st.link_button` renders with no `key=` here. Proves the query
    string the link actually carries is what opens on Collaborate, which a
    click on the picker's own (unchanged) default pair could not distinguish
    from "the picker's default happens to also be Collaborate's default"."""
    _open_select(page, "cmp_pair_b")
    page.locator('[role="option"]').last.click(timeout=ACTION_TIMEOUT_MS)
    _settle(page, 2000)

    # Located by PATH + "carries a query string" (`[href*="?"]`), never by the
    # exact `?pair=` key: Streamlit's OWN sidebar nav also emits a plain
    # `a[href="/Collaborate"]` (no query) for the page-to-page link, which a
    # bare `href^="/Collaborate"` locator would match FIRST in DOM order (the
    # sidebar renders above the main column) -- the `[href*="?"]` clause rules
    # that one out while staying immune to a renamed query key (proof (a)
    # below renames it), so the failure that mutation produces shows up in
    # the ID-EXTRACTION checks just below, not in "does the link even exist".
    link = page.locator(f'a[href^="{COLLAB_LINK_PREFIX}"][href*="?"]').first
    check(link.count() >= 1, "Compare: the hand-off link renders (a[href^=/Collaborate][href*=?])")
    href = link.get_attribute("href") or ""
    picked_ids = href.split("pair=", 1)[1].split(",") if "pair=" in href else []
    check(len(picked_ids) == 2 and picked_ids[0] != picked_ids[1],
          f"Compare: the hand-off link names two distinct ids ({href!r})")

    target_attr = link.get_attribute("target") or ""
    if target_attr == "_blank":
        with context.expect_page(timeout=ACTION_TIMEOUT_MS) as new_page_info:
            link.click(timeout=ACTION_TIMEOUT_MS)
        collab_page = new_page_info.value
        opened_new_tab = True
    else:
        link.click(timeout=ACTION_TIMEOUT_MS)
        collab_page = page
        opened_new_tab = False
    collab_page.set_default_timeout(ACTION_TIMEOUT_MS)
    collab_page.wait_for_selector('[data-testid="stDataFrame"]', timeout=ACTION_TIMEOUT_MS)
    _settle(collab_page, 2500)

    landed_ids = _pair_deeplink_ids(collab_page)
    check(landed_ids == picked_ids,
          f"Collaborate: opened on the SAME pair the hand-off link named ({picked_ids} -> {landed_ids})")
    _no_exception(collab_page, "Collaborate (opened from the Compare hand-off)")

    # --- swap flips the order --------------------------------------------------
    collab_page.locator(".st-key-pair_swap button").first.click(timeout=ACTION_TIMEOUT_MS)
    _settle(collab_page, 2000)
    swapped_ids = _pair_deeplink_ids(collab_page)
    check(swapped_ids == list(reversed(landed_ids)),
          f"Collaborate: swap flips A and B ({landed_ids} -> {swapped_ids})")

    # --- the shared-topics caption + its CSV header ----------------------------
    caps = _all_text(collab_page, '[data-testid="stCaptionContainer"]')
    check(bool(re.search(r"\d\.\d{3}", caps)),
          "Collaborate: a shared-topics caption carries the 3-decimal overlap score "
          "(copy.COLLAB['SHARED_CAPTION']'s own {score:.3f} format)")
    header = _download_csv_header(collab_page, ".st-key-dl_shared button")
    check(header.strip() == SHARED_TOPICS_HEADER,
          f"Collaborate: shared-topics CSV header matches the K contract ({header!r})")

    if opened_new_tab:
        collab_page.close()


def check_methods_journey(page) -> None:
    _click_nav(page, NAV_METHODS)
    page.wait_for_selector('[data-testid="stExpander"]', timeout=ACTION_TIMEOUT_MS)
    _settle(page, 1500)

    n_sections = page.locator('[data-testid="stExpander"]').count()
    check(n_sections >= METHODS_MIN_SECTIONS,
          f"Methods: >= {METHODS_MIN_SECTIONS} section expanders render ({n_sections})")

    body = _full_page_text(page)
    leftover = PLACEHOLDER_RE.findall(body)
    check(not leftover, f"Methods: no unresolved {{placeholder}} text on the page (found {leftover[:5]})")

    with page.expect_download(timeout=ACTION_TIMEOUT_MS) as dl_info:
        page.locator(".st-key-dl_methods_note button").first.click(timeout=ACTION_TIMEOUT_MS)
    raw = Path(dl_info.value.path()).read_bytes()
    check(len(raw) > 500, f"Methods: the source-note Markdown download is a real document ({len(raw)} bytes)")
    _no_exception(page, "Methods")


def check_narrative_persistence(page) -> dict:
    """2B-10's narrative order, hopped with real sidebar nav clicks: the
    tree/basis scenario Find carries (switched to its non-default DISPLAY
    label back in check_settings) reads the same on Compare and
    Collaborate's own `.st-key-tree`/`.st-key-basis` sidebar selects. Methods
    renders NEITHER control -- `views_methods.render()` never calls
    `_sidebar_scenario()` or `_sidebar_basket()`, a real gap from the
    brief's assumption that all three downstream pages show them (see this
    stream's progress note) -- so Methods gets only the exception check here.
    The basket's `{n} of {cap} added` sidebar count is read (never
    re-editable) on Compare/Collaborate; returning to Find shows the Gdansk
    seed still loaded and the SAME count on Find's own editable list."""
    _click_nav(page, NAV_COMPARE)
    _settle(page, 1500)
    tree_c, basis_c = _selectbox_value(page, "tree"), _selectbox_value(page, "basis")
    check(tree_c == TREE_LABEL_ORIGINAL,
          f"Compare: sidebar taxonomy still {TREE_LABEL_ORIGINAL!r} (got {tree_c!r})")
    check(basis_c == BASIS_LABEL_FRAC,
          f"Compare: sidebar counting basis still {BASIS_LABEL_FRAC!r} (got {basis_c!r})")
    n_compare = _sidebar_basket_n(page)
    check(n_compare is not None, f"Compare: sidebar basket count is readable (caption gave {n_compare!r})")

    _click_nav(page, NAV_COLLAB)
    _settle(page, 1500)
    tree_l, basis_l = _selectbox_value(page, "tree"), _selectbox_value(page, "basis")
    check(tree_l == TREE_LABEL_ORIGINAL,
          f"Collaborate: sidebar taxonomy still {TREE_LABEL_ORIGINAL!r} (got {tree_l!r})")
    check(basis_l == BASIS_LABEL_FRAC,
          f"Collaborate: sidebar counting basis still {BASIS_LABEL_FRAC!r} (got {basis_l!r})")
    n_collab = _sidebar_basket_n(page)
    check(n_compare is not None and n_compare == n_collab,
          f"Basket: the sidebar count agrees on Compare and Collaborate ({n_compare} vs {n_collab})")

    _click_nav(page, NAV_METHODS)
    _settle(page, 1000)
    _no_exception(page, "Methods (persistence hop)")

    _click_nav(page, "Find")
    _settle(page, 1500)
    heading = _seed_heading(page)
    check("Gda" in heading, f"Find: returning from Methods still shows the Gdansk seed (got {heading!r})")
    n_find = _basket_count(page)
    check(n_compare is not None and n_find == n_compare,
          f"Basket: {n_find} items on Find matches the {n_compare} the sidebar reported on "
          f"Compare/Collaborate")
    return {"n_basket": n_find}


def check_journey_widths(page, shot_dir: Path) -> None:
    """Compare at three widths (390 needs the drawer opened, same idiom as
    `check_screenshots` above); one screenshot each for Collaborate and
    Methods at 1280 px. Uses `page.set_viewport_size` on the SAME page/session
    throughout -- a fresh `browser.new_page()` would open a new WebSocket
    session with an EMPTY basket, exactly the false-failure `page.goto()`
    produces for a persistence check (module docstring)."""
    shot_dir.mkdir(parents=True, exist_ok=True)
    _click_nav(page, NAV_COMPARE)
    _settle_figures(page, COMPARE_MIN_FIGURES)
    for width in WIDTHS:
        page.set_viewport_size({"width": width, "height": 900})
        _settle(page, 1000)
        if width == 390:
            _ensure_sidebar_open(page)
        scroll = page.evaluate("document.documentElement.scrollWidth")
        inner = page.evaluate("window.innerWidth")
        check(scroll <= inner + 2, f"Compare {width}px: scrollWidth {scroll} <= innerWidth+2 {inner + 2}")
        p = shot_dir / f"smoke_compare_{width}.png"
        page.screenshot(path=str(p), full_page=True)
        check(p.is_file(), f"Compare {width}px: screenshot written ({p.name})")
    page.set_viewport_size({"width": 1280, "height": 900})
    _settle(page, 800)

    _click_nav(page, NAV_COLLAB)
    _settle(page, 2000)
    scroll = page.evaluate("document.documentElement.scrollWidth")
    inner = page.evaluate("window.innerWidth")
    check(scroll <= inner + 2, f"Collaborate 1280px: scrollWidth {scroll} <= innerWidth+2 {inner + 2}")
    p = shot_dir / "smoke_collab_1280.png"
    page.screenshot(path=str(p), full_page=True)
    check(p.is_file(), f"Collaborate 1280px: screenshot written ({p.name})")

    _click_nav(page, NAV_METHODS)
    _settle(page, 1500)
    scroll = page.evaluate("document.documentElement.scrollWidth")
    inner = page.evaluate("window.innerWidth")
    check(scroll <= inner + 2, f"Methods 1280px: scrollWidth {scroll} <= innerWidth+2 {inner + 2}")
    p = shot_dir / "smoke_methods_1280.png"
    page.screenshot(path=str(p), full_page=True)
    check(p.is_file(), f"Methods 1280px: screenshot written ({p.name})")


# ------------------------------------------------------------------ main ----

def main() -> int:
    global PORT, BASE_URL
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8611)
    parser.add_argument("--app-dir", type=str, default=None,
                         help="app/ root to target (default: this file's own app/); "
                              "pass a throwaway copy for the non-vacuity proofs.")
    args = parser.parse_args()
    PORT = args.port
    BASE_URL = f"http://127.0.0.1:{PORT}"
    app_dir = Path(args.app_dir).resolve() if args.app_dir else DEFAULT_APP_DIR
    shot_dir = app_dir / "tests" / "ui" / "screenshots"

    server = _start_server(app_dir, PORT)
    profile_expect: dict = {}
    journey: dict = {}
    try:
        if not _wait_for_port(PORT, timeout=90.0):
            check(False, f"server did not open port {PORT} within timeout")
            return 1

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.set_default_timeout(ACTION_TIMEOUT_MS)

            def _run_profile_panels() -> None:
                profile_expect.update(check_profile_and_panels(page) or {})

            sections = [
                ("Menu", lambda: check_menu(page)),
                ("Find search", lambda: check_find_search(page)),
                ("Basket", lambda: check_basket(page)),
                ("Controls placement", lambda: check_controls_placement(page)),
                ("Profile / panels", _run_profile_panels),
                ("Benchmark lens guide", lambda: check_benchmark_lens_guide(page)),
                ("Tables / export", lambda: check_tables_and_export(page)),
                ("Settings", lambda: check_settings(page)),
                ("Persistence", lambda: check_persistence(page, profile_expect)),
                ("Type filter clear", lambda: check_type_filter_clear(page)),
            ]
            for name, fn in sections:
                try:
                    fn()
                except Exception as exc:  # noqa: BLE001 -- one section's crash must not hang the run
                    fail_section(name, exc)

            try:
                undefined = _find_undefined_l2f_seed(app_dir)
                if undefined is None:
                    check(False, "Undefined lens: no institution with an undefined L2f was found")
                else:
                    check_undefined_lens(page, *undefined)
            except Exception as exc:  # noqa: BLE001
                fail_section("Undefined lens", exc)

            # Phase 2B (BUILD_PLAN_2B.md Stream H): the full four-page journey,
            # Menu -> Find -> Compare -> Collaborate -> Methods, on the SAME
            # page/session the checks above already built up -- a fresh
            # `browser.new_page()` here would open a new WebSocket session
            # with an empty basket, the same false-failure a `page.goto()`
            # produces for a persistence check (module docstring).
            def _run_compare_journey() -> None:
                journey.update(check_compare_journey(page, journey.get("candidates", [])) or {})

            journey_sections = [
                ("Journey: basket (L1 candidates + seed)",
                 lambda: journey.__setitem__("candidates", check_journey_basket(page))),
                ("Journey: Compare page", _run_compare_journey),
                ("Journey: hand-off to Collaborate", lambda: check_handoff(page, page.context)),
                ("Journey: Methods page", lambda: check_methods_journey(page)),
                ("Journey: narrative persistence", lambda: check_narrative_persistence(page)),
                ("Journey: widths + screenshots", lambda: check_journey_widths(page, shot_dir)),
            ]
            for name, fn in journey_sections:
                try:
                    fn()
                except Exception as exc:  # noqa: BLE001 -- one section's crash must not hang the run
                    fail_section(name, exc)

            page.close()
            check_screenshots(browser, shot_dir)
            browser.close()
    finally:
        _stop_server(server)

    failed = [m for ok, m in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)} of {len(RESULTS)} checks passed")
    if failed:
        for m in failed:
            print("FAILED:", m)
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())

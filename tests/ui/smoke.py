"""
tests/ui/smoke.py -- Playwright smoke test against the LIVE Streamlit server
(BUILD_PLAN_2A.md Stream H; extended for Refinement R1 stream R-H2 against
S9.2 L16-L22 / S9.3's R-H2 row). Cross-page persistence is the load-bearing
claim: the basket (a plain, non-widget session_state list) and every keyed
widget (persist_state="session") -- INCLUDING the ones R1 moved out of the
sidebar into the Benchmark section's controls row -- must survive real
Menu<->Find navigation with their widget KEYS unchanged.

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
currently active one -- confirmed by Stream E's own probe, app/ops/_probe_find.py)
and only to ASSERT content, never to locate an element (locating uses keyed
classes, roles or DOM position -- e.g. "the second radio option" -- never a
literal label). `st.dataframe` renders a canvas grid with no real text nodes
for cell values, so row-level facts (the basket count, the seed heading, the
strip, a CSV's own header row) are read from captions/keyed containers/a real
downloaded file, never from a table cell.

Usage:
    python tests/ui/smoke.py --port 8611
    python tests/ui/smoke.py --port 8612 --app-dir "<throwaway copy of app/>"

Exit 0 iff every check passes, 1 otherwise. Prints one PASS/FAIL line per
check. Stdout is ASCII-only (cp1252 console).
"""
from __future__ import annotations

import argparse
import socket
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

DEFAULT_APP_DIR = Path(__file__).resolve().parents[2]  # tests/ui/smoke.py -> app/
WIDTHS = [1920, 1280, 390]
GDANSK_QUERY = "gdansk"
GDANSK_TAB_COUNT = 10          # Overview + 8 default lenses + Aspirational
L7_ON_TAB_COUNT = 11           # ... + the L7 toggle's own tab
ACTION_TIMEOUT_MS = 30_000     # time-box every wait so a hang FAILS, never blocks

# R1/L17: the six profile chart panels, keyed `panel_<name>`, with their
# `copy.FIND["PANEL_*"]` header text (lib/copy.py) -- hardcoded here (not
# re-imported from the app under test) so a renamed label in a throwaway copy
# is a real DOM-vs-expectation mismatch, never a comparison against itself.
PANEL_LABELS = [
    ("fields", "Fields"),
    ("subfields", "Top subfields"),
    ("topics", "Top topics"),
    ("frontier", "Frontier positioning"),
    ("sdg", "SDG profile"),
    ("erc", "ERC profile"),
]

RESULTS: list[tuple[bool, str]] = []
PORT = 8611
BASE_URL = "http://127.0.0.1:8611"


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
    every rerun; only the active panel has non-empty innerText)."""
    return page.evaluate(
        "(sel) => Array.from(document.querySelectorAll(sel)).map(e => e.textContent).join('|')",
        selector)


def _no_exception(page, label: str) -> bool:
    return check(page.locator('[data-testid="stException"]').count() == 0,
                 f"{label}: no Streamlit exception on the page")


def _open_select(page, key: str) -> None:
    """Open a keyed BaseWeb selectbox: click it, wait for its (portal-rendered)
    option list."""
    loc = page.locator(f".st-key-{key} [data-baseweb='select']")
    if loc.count() == 0:
        loc = page.locator(f".st-key-{key}")
    loc.first.click(timeout=ACTION_TIMEOUT_MS)
    page.wait_for_selector('[role="option"]', timeout=ACTION_TIMEOUT_MS)


def _pick_option(page, text: str | None = None) -> None:
    opts = page.locator('[role="option"]')
    target = opts.filter(has_text=text).first if text else opts.first
    target.click(timeout=ACTION_TIMEOUT_MS)


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
    R1's `_post_filters`/`_profile_panels` bodies EXECUTE every rerun
    regardless of the expander's visual state (lib/views_find.py docstring),
    but that visual open/closed state resets to the coded `expanded=` default
    on the very next rerun -- so this is called before every interaction
    inside one, never assumed to still be open from an earlier action."""
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


# ----------------------------------------------------- R1 controls layout ---

def check_controls_placement(page) -> None:
    """R1/L16: the sidebar holds ONLY the scenario selects (tree, basis) and
    the basket; depth/C1/L7/post-filters render in the MAIN area's controls
    row at the head of the Benchmark section, with their widget KEYS
    unchanged. The post-filters expander reveals the type/country filters,
    and the country multiselect shows country NAMES, not codes."""
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
    _no_exception(page, "Controls placement / post-filters")


# ----------------------------------------------------------- R1 profile -----

def check_profile_and_panels(page) -> None:
    """R1/L17: the profile container, its wordcloud, its six chart-panel
    expanders (labels intact), the breakdown segmented control, and the
    per-panel sort toggle changing what the Fields chart actually shows."""
    check(page.locator(".st-key-profile").count() == 1,
          "Profile: .st-key-profile container renders exactly once")
    check(page.locator('.st-key-profile [data-testid="stImage"] img').count() >= 1,
          "Profile: subfield wordcloud renders as an <img>")

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
        check(clean == label, f"Panel '{name}': header label is exactly '{label}' (got {raw!r})")

    before_legend = _all_text(page, '.st-key-profile div[style*="flex-wrap"]')
    check(bool(before_legend.strip()), "Breakdown: chip legend renders")
    page.locator(".st-key-breakdown_dim button").nth(1).click(timeout=ACTION_TIMEOUT_MS)
    _settle(page, 4000)
    after_legend = _all_text(page, '.st-key-profile div[style*="flex-wrap"]')
    check(after_legend != before_legend and bool(after_legend.strip()),
          "Breakdown: segmented control swaps the chip legend (domain <-> document type)")
    check(page.locator(".st-key-fig_breakdown_global .js-plotly-plot").first.is_visible()
          and page.locator(".st-key-fig_breakdown_yearly .js-plotly-plot").first.is_visible(),
          "Breakdown: both plotly figures still render after the swap")
    caption = _all_text(page, '[data-testid="stCaptionContainer"]')
    check("bonus year" in caption, "Breakdown: bonus-year caption is present")
    page.locator(".st-key-breakdown_dim button").nth(0).click(timeout=ACTION_TIMEOUT_MS)
    _settle(page, 3000)

    _ensure_expander_open(page, "panel_fields", ".st-key-sort_fields [data-testid='stRadioOption']")
    _settle(page, 1500)
    fig = page.locator(".st-key-fig_fields .js-plotly-plot").first
    check(fig.count() >= 1 and fig.is_visible(),
          "Panel Fields: opening it reveals a visible Plotly figure")
    before_tick = page.locator(".st-key-fig_fields .ytick text").first.text_content() or ""
    page.locator('.st-key-sort_fields [data-testid="stRadioOption"]').nth(1).click(timeout=ACTION_TIMEOUT_MS)
    _settle(page, 2500)
    after_tick = page.locator(".st-key-fig_fields .ytick text").first.text_content() or ""
    check(bool(before_tick) and bool(after_tick) and before_tick != after_tick,
          f"Panel Fields: the sort toggle changes the first y-axis label ({before_tick!r} -> {after_tick!r})")
    page.locator('.st-key-sort_fields [data-testid="stRadioOption"]').nth(0).click(timeout=ACTION_TIMEOUT_MS)
    _settle(page, 2500)
    _no_exception(page, "Profile / panels")


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
    Aspirational tab renders its own table."""
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
    """R1: the settings a reader would touch on a first visit -- all now in
    the Benchmark controls row/expander instead of the sidebar -- set here
    BEFORE the persistence hops (S9.3 R-H2: depth to max, L7 on, a type
    filter picked, tree switched)."""
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

    _open_select(page, "tree")
    _pick_option(page, "original")
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
    check("tree = original" in strip, f"Settings: strip mentions tree = original (strip: {strip!r})")
    check("depth = 50" in strip, f"Settings: strip mentions depth = 50 (strip: {strip!r})")
    check("type = " in strip and "education" in strip,
          f"Settings: strip mentions the type filter (strip: {strip!r})")
    _no_exception(page, "Settings")


def _capture_persisted_state(page) -> dict:
    return {"basket": _basket_count(page), "tabs": page.locator('[role="tab"]').count(),
            "heading": _seed_heading(page), "strip": _strip_text(page)}


def _assert_persisted(state: dict, tag: str) -> None:
    check(state["basket"] == 2, f"{tag}: basket still lists 2 items (got {state['basket']})")
    check(state["tabs"] == L7_ON_TAB_COUNT,
          f"{tag}: L7 tab still present, tab count {L7_ON_TAB_COUNT} (got {state['tabs']})")
    check("Gda" in state["heading"], f"{tag}: seed still selected, heading 'Gda...' (got {state['heading']!r})")
    check("depth = 50" in state["strip"], f"{tag}: depth still at max in the strip")
    check("tree = original" in state["strip"], f"{tag}: tree still 'original' in the strip")
    check("type = " in state["strip"] and "education" in state["strip"],
          f"{tag}: type filter (education) still active in the strip")


def check_persistence(page) -> None:
    """The load-bearing claim: basket + every keyed widget -- INCLUDING the
    ones R1 relocated from the sidebar into the controls row/expander --
    survive real Menu<->Find hops (4 hops total: Menu, Find, Menu, Find), with
    a second-visit re-mount check at the 2-hop midpoint (a bug that only shows
    up on a widget's SECOND mount is a real, documented failure mode --
    Portfolio Mapping INSPECTION_PLAYBOOK.md family 3)."""
    _assert_persisted(_capture_persisted_state(page), "Persistence: baseline captured before any hop")

    _click_nav(page, "Menu")
    _no_exception(page, "Menu (hop 1 of 4)")
    _click_nav(page, "Find")
    _no_exception(page, "Find (hop 2 of 4, second-visit re-mount)")
    _assert_persisted(_capture_persisted_state(page), "Persistence: 2nd Find visit (re-mount check)")

    _click_nav(page, "Menu")
    _no_exception(page, "Menu (hop 3 of 4)")
    _click_nav(page, "Find")
    _no_exception(page, "Find (hop 4 of 4, final)")
    _assert_persisted(_capture_persisted_state(page), "Persistence: 3rd Find visit (after 4 hops)")


def check_type_filter_clear(page) -> None:
    """The type filter set in Settings and proven to survive the hops above
    can also be CLEARED, and the strip stops naming it once it is."""
    strip = _strip_text(page)
    check("type = " in strip and "education" in strip,
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
    check("L2f" in text and "is undefined for this seed" in text,
          f"Undefined lens: L2f undefined message present for {seed_name}")
    _no_exception(page, "Undefined L2f seed")


def check_fields_panel_no_overlap(page, width: int) -> None:
    """Fix X3 (inspection finding I-4): bounding-box proof that opening the
    Fields panel at this width never lets a y-axis tick label collide with
    anything. `lib/charts.py::fig_share_si` now folds the volume INTO the tick
    text as one right-anchored string (so there is nothing separate left to
    merge into it) and reserves its own left margin from the longest resulting
    string -- this check is the thing that would have failed before that fix:
    every `.ytick text` must lie fully inside its plot's own `.main-svg`, never
    clipped past the left edge (where the old collision put the leading
    characters underneath the volume gutter) and never overflowing the right
    edge either. A page-level scrollWidth check cannot see this: it is a
    collision INSIDE one chart's own layout, not a page overflow."""
    fig = page.locator(".st-key-fig_fields .js-plotly-plot").first
    fig.wait_for(state="visible", timeout=ACTION_TIMEOUT_MS)
    plot_box = fig.locator(".main-svg").first.bounding_box()
    if plot_box is None:
        check(False, f"Fields panel {width}px: could not read the plot's own .main-svg bounding box")
        return
    ticks = fig.locator(".ytick text")
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
          f"Fields panel {width}px: {n} y-tick label(s) all stay inside the plot's own svg"
          + (f" -- offenders: {offenders}" if offenders else ""))


def check_screenshots(browser, shot_dir: Path) -> None:
    """R1: at each width, the seed is loaded AND one profile panel is opened
    before the scrollWidth assertion (S9.3 R-H2's own acceptance line) -- the
    widest real state the page can be in, not just the collapsed default.

    Fix X3 additions: a bounding-box no-overlap check on the open Fields panel
    at 390 px AND 1280 px (finding I-4); a plain (non-full-page) top-of-page
    screenshot at 1280 px, scrolled to y=0 with the seed loaded but BEFORE any
    panel is opened, since every R1 glance screenshot happened to be scrolled
    past the profile header/tiles/coverage/wordcloud (finding I-5); and a
    dedicated 390 px screenshot with the Fields panel open."""
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
                # I-5: the untouched top of the page -- header/tiles/coverage/
                # wordcloud -- BEFORE any expander is opened, viewport-only
                # (not full_page) so it is actually scrolled to y=0, not just
                # stitched in as the top slice of a taller image.
                page.evaluate("window.scrollTo(0, 0)")
                _settle(page, 500)
                top_p = shot_dir / "smoke_find_top_1280.png"
                page.screenshot(path=str(top_p), full_page=False)
                check(top_p.is_file(), f"Find top-of-page 1280px: screenshot written ({top_p.name})")

            _ensure_expander_open(page, "panel_fields",
                                  ".st-key-sort_fields [data-testid='stRadioOption']")
            _settle(page, 1500)
            scroll = page.evaluate("document.documentElement.scrollWidth")
            inner = page.evaluate("window.innerWidth")
            check(scroll <= inner + 2, f"Find {width}px: scrollWidth {scroll} <= innerWidth+2 {inner + 2}")
            p2 = shot_dir / f"smoke_find_{width}.png"
            page.screenshot(path=str(p2), full_page=True)
            check(p2.is_file(), f"Find {width}px: screenshot written ({p2.name})")

            if width in (390, 1280):
                check_fields_panel_no_overlap(page, width)
            if width == 390:
                fields_p = shot_dir / "smoke_find_fields_390.png"
                page.screenshot(path=str(fields_p), full_page=True)
                check(fields_p.is_file(), f"Find Fields panel 390px: screenshot written ({fields_p.name})")
        except Exception as exc:  # noqa: BLE001 -- one width's failure must not skip the rest
            fail_section(f"Screenshots at {width}px", exc)
        finally:
            page.close()


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
    try:
        if not _wait_for_port(PORT, timeout=90.0):
            check(False, f"server did not open port {PORT} within timeout")
            return 1

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.set_default_timeout(ACTION_TIMEOUT_MS)

            sections = [
                ("Menu", lambda: check_menu(page)),
                ("Find search", lambda: check_find_search(page)),
                ("Basket", lambda: check_basket(page)),
                ("Controls placement", lambda: check_controls_placement(page)),
                ("Profile / panels", lambda: check_profile_and_panels(page)),
                ("Tables / export", lambda: check_tables_and_export(page)),
                ("Settings", lambda: check_settings(page)),
                ("Persistence", lambda: check_persistence(page)),
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

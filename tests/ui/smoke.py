"""
tests/ui/smoke.py -- Playwright smoke test against the LIVE Streamlit server
(BUILD_PLAN_2A.md Stream H). Cross-page persistence is the load-bearing claim:
the basket (a plain, non-widget session_state list) and every keyed sidebar
widget (persist_state="session") must survive real Menu<->Find navigation.

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
and only to ASSERT content, never to locate an element. `st.dataframe` renders
a canvas grid with no real text nodes for cell values, so row-level facts
(the basket count, the seed heading, the strip) are read from captions/keyed
containers, never from a table cell.

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
    return page.locator(".st-key-seed_card h3").first.text_content() or ""


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
    """Smallest-first scan (BUILD_PLAN_2A.md Stream H brief): the smaller an
    institution, the more likely L2f's own floor-of-papers-per-cell rule
    leaves it undefined. `tree="original"` matches the scenario the smoke
    flow has set by the time it reaches this check (Settings section)."""
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
    check("Gda" in heading, f"Find: seed card heading contains 'Gda' (got {heading!r})")
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


def check_settings(page) -> None:
    before = _all_text(page, '[data-testid="stCaptionContainer"]')
    page.locator('.st-key-depth [data-testid="stRadioOption"]').last.click(timeout=ACTION_TIMEOUT_MS)
    _settle(page, 3000)
    after = _all_text(page, '[data-testid="stCaptionContainer"]')
    check(before != after, "Settings: depth caption changed after switching depth to its max")

    _open_select(page, "tree")
    _pick_option(page, "original")
    _settle(page, 3000)

    page.locator(".st-key-l7_on label").first.click(timeout=ACTION_TIMEOUT_MS)
    _settle(page, 3500)
    tabs = page.locator('[role="tab"]').count()
    check(tabs == L7_ON_TAB_COUNT, f"Settings: L7 tab appeared, tab count is {L7_ON_TAB_COUNT} (got {tabs})")

    check(page.locator(".st-key-strip").count() >= 1, "Settings: off-default strip is visible")
    strip = _strip_text(page)
    check("tree = original" in strip, f"Settings: strip mentions tree = original (strip: {strip!r})")
    check("depth = 50" in strip, f"Settings: strip mentions depth = 50 (strip: {strip!r})")
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


def check_persistence(page) -> None:
    """The load-bearing claim: basket + every keyed sidebar widget survive
    real Menu<->Find hops (4 hops total: Menu, Find, Menu, Find), with a
    second-visit re-mount check at the 2-hop midpoint (a bug that only shows
    up on a widget's SECOND mount is a real, documented failure mode --
    Portfolio Mapping INSPECTION_PLAYBOOK.md family 3)."""
    baseline = _capture_persisted_state(page)
    check(baseline["basket"] == 2 and baseline["tabs"] == L7_ON_TAB_COUNT,
          "Persistence: baseline captured before any hop")

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


def check_type_filter(page) -> None:
    inp = page.locator(".st-key-f_types input").first
    inp.click(timeout=ACTION_TIMEOUT_MS)
    inp.fill("education")
    page.wait_for_selector('[role="option"]', timeout=ACTION_TIMEOUT_MS)
    page.locator('[role="option"]').filter(has_text="education").first.click(timeout=ACTION_TIMEOUT_MS)
    _settle(page, 3500)
    strip = _strip_text(page)
    check("type = " in strip and "education" in strip,
          f"Type filter: strip names the type filter (strip: {strip!r})")
    _no_exception(page, "Type filter applied")

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


def check_screenshots(browser, shot_dir: Path) -> None:
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
            scroll = page.evaluate("document.documentElement.scrollWidth")
            inner = page.evaluate("window.innerWidth")
            check(scroll <= inner + 2, f"Find {width}px: scrollWidth {scroll} <= innerWidth+2 {inner + 2}")
            p2 = shot_dir / f"smoke_find_{width}.png"
            page.screenshot(path=str(p2), full_page=True)
            check(p2.is_file(), f"Find {width}px: screenshot written ({p2.name})")
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
                ("Settings", lambda: check_settings(page)),
                ("Persistence", lambda: check_persistence(page)),
                ("Type filter", lambda: check_type_filter(page)),
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

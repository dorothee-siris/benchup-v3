"""
Acceptance probe for the Compare page (BUILD_PLAN_2B.md Stream C, decisions
2B-1 ... 2B-6, 2B-13, 2B-14, amendments A2, A9, A10, A11). Same shape as
ops/_probe_collab.py: start `streamlit run pages/2_<scales>_Compare.py` as a
subprocess, drive it headless with Playwright, ALWAYS terminate the server.

Selectors are locale-independent -- the `st-key-<key>` classes the page's own
keyed widgets and containers emit, plus `[data-testid=...]`. Nothing is asserted
against a canvas: the workbook is checked by DOWNLOADING it and opening it with
openpyxl, and the figures are checked by counting plotly roots and subplots,
never by reading marks.

The comparison is injected through the real `?compare=A,B,C,D` query parameter
the shipped deep link produces (`lib/selection.deeplink`), so this probe covers
the live URL path tests/test_pages_compare.py can only reach by patching.

Usage:  python ops/_probe_compare.py [--port 8605]
Exit 0 when every check passes; 1 otherwise. Stdout is ASCII-only (cp1252
console).
"""
from __future__ import annotations

import argparse
import io
import socket
import subprocess
import sys
import time
from pathlib import Path

import openpyxl
from playwright.sync_api import sync_playwright

APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))

from lib import copy, views_compare  # noqa: E402  (needs APP_DIR on sys.path first)

PAGE = "pages/2_⚖️_Compare.py"
DEFAULT_PORT = 8605
IDS = ["I68947357", "I40413290", "I265217849", "I110026055"]
SHOT_DIR = APP_DIR / "tests" / "ui" / "screenshots"
WIDTHS = [1920, 1280, 390]
SHOT_HEIGHT_PX = 2400   # full_page=True is a no-op on Streamlit's scroll container, so the
                        # VIEWPORT is the screenshot. The wide widths get a tall one (the page
                        # runs to some twelve thousand pixels at k = 4, so no single frame holds
                        # it -- this reaches the subfield mirror), and 390 px keeps the head.
TALL_SHOT_PX = 5600
HEAD_SHOT_PX = 900      # the true above-the-fold view at 1280 px
MIN_FIGURES = 7         # fields, subfields, ERC, SDG, quadrant, frontier, impact,
                        # impact by subfield, trends, coverage -- the acceptance floor

PORT = DEFAULT_PORT
RESULTS: list[tuple[bool, str]] = []


def check(ok: bool, message: str) -> bool:
    RESULTS.append((bool(ok), message))
    print(("PASS: " if ok else "FAIL: ") + message)
    return bool(ok)


def _wait_for_port(port: int, timeout: float = 60.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.5)
    return False


def _load(page) -> None:
    page.goto(f"http://127.0.0.1:{PORT}/?compare=" + ",".join(IDS),
              wait_until="domcontentloaded")
    page.wait_for_selector(".js-plotly-plot", timeout=240_000)
    _settle(page)


def _settle(page, target: int = MIN_FIGURES, timeout_ms: int = 180_000) -> int:
    """Streamlit streams its elements, so the figure count climbs for a while
    after the first plot appears. Wait for it to reach the acceptance floor and
    then stop changing, rather than sleeping a guessed number of seconds."""
    deadline = time.time() + timeout_ms / 1000.0
    last, stable = -1, 0
    while time.time() < deadline:
        now = _n_figures(page)
        stable = stable + 1 if now == last and now >= target else 0
        last = now
        if stable >= 3:
            break
        page.wait_for_timeout(1000)
    page.wait_for_timeout(1500)
    return last


def _n_figures(page) -> int:
    return page.locator(".js-plotly-plot").count()


def _text_of(page, selector: str) -> str:
    return page.evaluate(
        "(sel) => { const e = document.querySelector(sel); return e ? e.textContent : ''; }",
        selector)


def _captions(page) -> str:
    return page.evaluate(
        "Array.from(document.querySelectorAll('[data-testid=\"stCaptionContainer\"]'))"
        ".map(e => e.textContent).join('|')")


def _names() -> dict:
    ctx = views_compare._bundle()["ctx"]
    return {i: str(ctx["index_by_id"].loc[i, "display_name"]) for i in IDS}


def _n_frontier_subplots(page) -> int:
    """Panels inside the frontier figure: the faceted form is one subplot per
    institution, the overlay is exactly one plane (V's A/B #6)."""
    return page.evaluate(
        "(() => { const e = document.querySelector('.st-key-cmp_frontier_plot');"
        " return e ? e.querySelectorAll('g.subplot').length : -1; })()")


def _click_option(page, container_key: str, text: str) -> None:
    """Click one option of a keyed segmented control / radio, then wait for the
    rerun to finish redrawing (a rerun rebuilds every figure on the page, so the
    count dips before it comes back)."""
    page.locator(f".st-key-{container_key}").get_by_text(text, exact=False).first.click()
    page.wait_for_timeout(2000)
    _settle(page)


def _n_legends(page, names) -> int:
    """Legend strips: a markdown container whose text names every compared
    institution and which carries the chip spans. `charts.chip_legend_html`
    writes inline styles the browser normalises, so the count is taken on
    STRUCTURE and TEXT, never on an attribute substring."""
    return page.evaluate(
        "(names) => Array.from(document.querySelectorAll('[data-testid=\"stMarkdownContainer\"]'))"
        ".filter(e => names.every(n => e.textContent.includes(n))"
        " && e.querySelectorAll('span').length >= names.length * 2).length",
        list(names))


def _probe_page(page) -> None:
    _load(page)
    names = _names()

    strip = _text_of(page, ".st-key-compare_strip")
    for iid, name in names.items():
        check(name in strip, f"the institution strip names {iid}")

    legends = _n_legends(page, list(names.values()))
    check(legends >= 2,
          f"the institution legend is rendered above each view ({legends} strips found)")

    n_figs = _n_figures(page)
    check(n_figs >= MIN_FIGURES, f"the page draws its views ({n_figs} figures, floor "
                                 f"{MIN_FIGURES})")

    code = page.evaluate(
        "Array.from(document.querySelectorAll('[data-testid=\"stCode\"]'))"
        ".map(e => e.textContent).join('|')")
    check("?compare=" + ",".join(IDS) in code,
          "the page prints the comparison deep link it was opened with")
    check("?pair=" in code, "the page prints a Collaborate deep link for the chosen pair")

    # --- the frontier form control (V's A/B #6 ruling) ---------------------
    facets = _n_frontier_subplots(page)
    check(facets > 1, f"the frontier view defaults to small multiples ({facets} panels)")
    _click_option(page, "cmp_frontier_form", copy.COMPARE["FRONTIER_FORM_OVERLAY"])
    overlay = _n_frontier_subplots(page)
    check(overlay == 1, f"the overlay mode draws ONE plane ({overlay} panels)")
    check(copy.COMPARE["CAPTION_FRONTIER_OVERLAY"][:60] in _captions(page),
          "the overlay caption states what the single plane hides")
    _click_option(page, "cmp_frontier_form", copy.COMPARE["FRONTIER_FORM_FACETS"])
    check(_n_frontier_subplots(page) > 1, "the control switches back to the panels")

    # --- the impact floor toggle (A1) --------------------------------------
    before = _impact_caption(page)
    low = min(views_compare.IMPACT_FLOORS)
    _click_option(page, "cmp_impact_floor",
                  copy.COMPARE["IMPACT_FLOOR_OPTION"].format(floor=low))
    after = _impact_caption(page)
    check(bool(before) and bool(after) and before != after,
          f"the floor toggle changes the impact caption ({before!r} -> {after!r})")


def _impact_caption(page) -> str:
    """The per-subfield impact caption, found by its LONGEST fixed segment: the
    subfields mirror's own caption also opens with the same two words, so a
    first-segment match would silently read the wrong line."""
    import re

    segments = [t for t in re.split(r"\{[^{}]*\}", copy.COMPARE["CAPTION_IMPACT_SHOWN"])
                if t.strip()]
    marker = max(segments, key=len).strip()
    for text in _captions(page).split("|"):
        if marker in text:
            return text.strip()
    return ""


def _probe_download(page) -> None:
    """The workbook, taken through the page's real download button, opened with
    openpyxl: one sheet per view plus the Methods sheet (2B-13)."""
    _load(page)
    with page.expect_download(timeout=120_000) as info:
        page.locator(".st-key-dl_workbook button").first.click()
    path = Path(info.value.path())
    raw = path.read_bytes()
    check(raw[:2] == b"PK", "the workbook downloads as a real xlsx container")
    book = openpyxl.load_workbook(io.BytesIO(raw))
    check(book.sheetnames[0] == copy.COMPARE["XLSX_SHEET_METHODS"],
          f"the first sheet is the Methods sheet ({book.sheetnames[:1]})")
    expected = len(views_compare.SLUGS) + 1
    check(len(book.sheetnames) == expected,
          f"the workbook carries a sheet per view plus Methods ({len(book.sheetnames)} of "
          f"{expected})")
    values = [str(c.value) for row in book[book.sheetnames[0]].iter_rows()
              for c in row if c.value is not None]
    check(copy.VERDICT_LINE in values, "the Methods sheet carries the standing reading line")


def _probe_widths(browser) -> None:
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    for width in WIDTHS:
        height = TALL_SHOT_PX if width >= 1280 else SHOT_HEIGHT_PX
        page = browser.new_page(viewport={"width": width, "height": height})
        _load(page)
        scroll = page.evaluate("document.documentElement.scrollWidth")
        inner = page.evaluate("window.innerWidth")
        check(scroll <= inner + 2,
              f"{width} px: scrollWidth {scroll} <= innerWidth+2 {inner + 2}")
        path = SHOT_DIR / f"c_compare_{width}.png"
        page.screenshot(path=str(path), full_page=True)
        print("Saved screenshot:", path)
        check(path.is_file(), f"{width} px: screenshot written")
        page.close()
    page = browser.new_page(viewport={"width": 1280, "height": HEAD_SHOT_PX})
    _load(page)
    top = SHOT_DIR / "c_compare_top_1280.png"
    page.screenshot(path=str(top), full_page=False)
    print("Saved screenshot:", top)
    check(top.is_file(), "1280 px: the page head, above the fold")
    page.close()


def main() -> int:
    global PORT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help="port to run the Streamlit server on")
    PORT = parser.parse_args().port

    server = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", PAGE,
         "--server.headless", "true", "--server.port", str(PORT)],
        cwd=str(APP_DIR), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    try:
        if not _wait_for_port(PORT):
            print("FAIL: server did not open port", PORT)
            return 1
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(viewport={"width": 1280, "height": 1000},
                                          accept_downloads=True)
            page = context.new_page()
            _probe_page(page)
            _probe_download(page)
            page.close()
            context.close()
            _probe_widths(browser)
            browser.close()
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=10)
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

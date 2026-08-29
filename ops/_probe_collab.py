"""
Acceptance probe for the Collaborate page (BUILD_PLAN_2B.md Stream L, decisions
2B-7 / 2B-8, amendments A7 and A11). Same shape as ops/_probe_find.py: start
`streamlit run pages/3_<handshake>_Collaborate.py` as a subprocess, drive it
headless with Playwright, ALWAYS terminate the server.

Selectors are locale-independent -- the `st-key-<key>` classes the page's own
keyed widgets and containers emit, plus `[data-testid=...]`. The three tables are
`st.dataframe`, i.e. CANVAS grids: the Assembly Line gotcha list forbids
`inner_text` assertions on them, so their content is checked through the page's
own CSV download and through the captions the page prints beside them, never by
reading cells off the canvas.

The pair is injected through the real `?pair=A,B` query parameter the shipped
deep link produces (`lib/selection.deeplink`), so this probe covers the live URL
path that tests/test_pages_collab.py can only reach by patching.

Usage:  python ops/_probe_collab.py [--port 8604]
Exit 0 when every check passes; 1 otherwise. Stdout is ASCII-only (cp1252
console).
"""
from __future__ import annotations

import argparse
import csv
import io
import socket
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))

from lib import views_collab  # noqa: E402  (needs APP_DIR on sys.path first)
from lib.collab_data import SHARED_TOPICS_COLS  # noqa: E402

PAGE = "pages/3_\U0001F91D_Collaborate.py"
DEFAULT_PORT = 8604
A_ID = "I68947357"   # Universite de Strasbourg
B_ID = "I40413290"   # University of Gdansk
SHOT_DIR = APP_DIR / "tests" / "ui" / "screenshots"
WIDTHS = [1920, 1280, 390]
SHOT_HEIGHT_PX = 2400   # see _probe_widths in ops/_probe_find.py: full_page=True is a no-op
N_TABLES = 3            # shared topics + the two directional gap tables (2B-7)

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
    """Open the page on the deep link the app's own share control prints."""
    page.goto(f"http://127.0.0.1:{PORT}/?pair={A_ID},{B_ID}", wait_until="domcontentloaded")
    page.wait_for_selector('[data-testid="stDataFrame"]', timeout=180_000)
    page.wait_for_timeout(2500)


def _n_tables(page) -> int:
    return page.locator('[data-testid="stDataFrame"]').count()


def _header_text(page) -> str:
    """textContent of the page's own bordered header container (`key=
    "collab_header"`), which is where both institutions and the link-outs live."""
    return page.evaluate(
        "(() => { const e = document.querySelector('.st-key-collab_header');"
        " return e ? e.textContent : ''; })()")


def _copub_href(page) -> str:
    return page.evaluate(
        "(() => { const a = Array.from(document.querySelectorAll('a[href]'))"
        ".find(x => (x.getAttribute('href') || '').split('authorships.institutions.id').length > 2);"
        " return a ? a.getAttribute('href') : ''; })()")


def _captions(page) -> str:
    return page.evaluate(
        "Array.from(document.querySelectorAll('[data-testid=\"stCaptionContainer\"]'))"
        ".map(e => e.textContent).join('|')")


def _probe_page(page) -> None:
    _load(page)
    check(_n_tables(page) == N_TABLES,
          f"the three 2B-7 tables render ({_n_tables(page)} found)")

    names = _institution_names()
    header = _header_text(page)
    for iid, name in names.items():
        check(name in header, f"header strip names {iid}")

    href = _copub_href(page)
    want = f"authorships.institutions.id:{A_ID},authorships.institutions.id:{B_ID}"
    check(want in href, "co-publication link uses the comma-joined repeated filter (A7)")
    check("+" not in href.split("filter=")[-1].split("&")[0],
          "co-publication link does NOT use the forbidden `+` form (A7)")

    # The deep link the page prints must be the one that opened it.
    code = page.evaluate(
        "Array.from(document.querySelectorAll('[data-testid=\"stCode\"]'))"
        ".map(e => e.textContent).join('|')")
    check(f"?pair={A_ID},{B_ID}" in code, "the page prints the pair deep link it was opened with")

    caps = _captions(page)
    check(str(views_collab.BREADTH_MIN_FULL) in caps,
          "the breadth caption states the publication floor the page passes")

    # The pair picker's own widgets exist and are keyed as the tests expect.
    for key in ("pair_a", "pair_b", "pair_swap", "tree", "basis"):
        check(page.locator(f".st-key-{key}").count() > 0, f"widget `{key}` renders")


def _probe_download(page) -> None:
    """The shared-topics CSV, taken through the page's real download button:
    header row and a data row, checked against the frame contract K published
    (`collab_data.SHARED_TOPICS_COLS`)."""
    _load(page)
    with page.expect_download(timeout=60_000) as info:
        page.locator(".st-key-dl_shared button").first.click()
    path = info.value.path()
    text = Path(path).read_text(encoding="utf-8")
    rows = list(csv.reader(io.StringIO(text)))
    check(bool(rows) and rows[0] == SHARED_TOPICS_COLS,
          f"shared-topics CSV header is the K contract ({rows[0] if rows else 'no rows'})")
    check(len(rows) > 1, f"shared-topics CSV carries data rows ({max(len(rows) - 1, 0)})")


def _probe_widths(browser) -> None:
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    for width in WIDTHS:
        page = browser.new_page(viewport={"width": width, "height": SHOT_HEIGHT_PX})
        _load(page)
        scroll = page.evaluate("document.documentElement.scrollWidth")
        inner = page.evaluate("window.innerWidth")
        check(scroll <= inner + 2,
              f"{width} px: scrollWidth {scroll} <= innerWidth+2 {inner + 2}")
        path = SHOT_DIR / f"l_collab_{width}.png"
        page.screenshot(path=str(path), full_page=True)
        print("Saved screenshot:", path)
        check(path.is_file(), f"{width} px: screenshot written")
        page.close()


def _institution_names() -> dict:
    ctx = views_collab._bundle()["ctx"]
    return {i: str(ctx["index_by_id"].loc[i, "display_name"]) for i in (A_ID, B_ID)}


def _recompute_check() -> None:
    """Read the topic-overlap score back out of the page's OWN frame and check
    it against the engine's L3 lens score for the pair -- the identity the
    shared-topics caption asserts on screen (2B-7 / K's engine-identity
    anchor). Server-side, after the browser is gone."""
    from lib.engine import rank_all

    ctx = views_collab._bundle()["ctx"]
    subs = views_collab._subs("bestfit", "frac")
    page_score = float(views_collab._shared_frame(A_ID, B_ID, "bestfit", "frac")["min_share"].sum())
    engine_score = float(rank_all(ctx, subs, A_ID)["L3"]["scores"][ctx["id_pos"][B_ID]])
    check(abs(page_score - engine_score) < 1e-6,
          f"shared-topics min-sum {page_score:.6f} == engine L3 score {engine_score:.6f}")


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
    _recompute_check()
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

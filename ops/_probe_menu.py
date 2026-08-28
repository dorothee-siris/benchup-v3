"""
Foundations probe for Menu.py, run before any page exists (BUILD_PLAN_2A.md Stream A
build step 8). Starts `streamlit run Menu.py` as a subprocess, drives it headless with
Playwright, asserts a minimal render contract, then ALWAYS terminates the server.

Locale-independent selectors only (roles, the `st-key-nav_cards` class from Menu.py's
own keyed container) -- never literal UI strings, per the Assembly Line gotcha list.
Exit 0 on all checks passing, 1 otherwise; the running server is never left behind.
"""
from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

APP_DIR = Path(__file__).resolve().parent.parent
PORT = 8601
SCREENSHOT_PATH = APP_DIR / "tests" / "ui" / "screenshots" / "menu_probe_1280.png"


def _wait_for_port(port: int, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.5)
    return False


def main() -> int:
    SCREENSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "Menu.py",
            "--server.headless",
            "true",
            "--server.port",
            str(PORT),
        ],
        cwd=str(APP_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    failures: list[str] = []
    try:
        if not _wait_for_port(PORT):
            print("FAIL: server did not open port", PORT, "within timeout")
            return 1

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"http://127.0.0.1:{PORT}", wait_until="networkidle")
            page.wait_for_timeout(1500)

            # 1. a heading is present (role-based, locale-independent)
            headings = page.get_by_role("heading")
            if headings.count() < 1:
                failures.append("no heading found on the page")
            else:
                print("PASS: heading present, count =", headings.count())

            # 2. nav cards render inside the keyed container (class st-key-nav_cards,
            # BUILD_PLAN_2A.md Stream A build step 7 -- three st.container(border=True)
            # cards nested inside st.container(key="nav_cards"))
            nav_container = page.locator(".st-key-nav_cards")
            if nav_container.count() < 1:
                failures.append("st-key-nav_cards container not found")
            else:
                cards = nav_container.locator("[class*='st-key-nav_card_']")
                if cards.count() < 3:
                    failures.append(f"expected >=3 nav cards, found {cards.count()}")
                else:
                    print("PASS: nav cards rendered, count =", cards.count())

            # 3. no horizontal overflow at 1280 px
            scroll_width = page.evaluate("document.documentElement.scrollWidth")
            inner_width = page.evaluate("window.innerWidth")
            if scroll_width > inner_width + 2:
                failures.append(f"horizontal overflow: scrollWidth={scroll_width} innerWidth={inner_width}")
            else:
                print(f"PASS: scrollWidth {scroll_width} <= innerWidth+2 {inner_width + 2}")

            page.screenshot(path=str(SCREENSHOT_PATH), full_page=True)
            print("Saved screenshot:", SCREENSHOT_PATH)

            browser.close()
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=10)

    if failures:
        for f in failures:
            print("FAIL:", f)
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())

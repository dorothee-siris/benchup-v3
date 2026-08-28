"""
Launches each A/B prototype on its own port, screenshots headless (Playwright),
then terminates the server -- reuses ops/_probe_menu.py's launch/wait/terminate
pattern (BUILD_PLAN_2A.md Stream D1 brief: "reuse the pattern for your
prototypes"). Screenshots land next to this file (design-system/ab/*.png).

Usage: python run_ab.py            -- all four prototypes at 1280x900
       python run_ab.py <prefix> <width,width,...>  -- one prototype, extra widths
       (prefix in {ab1_a, ab1_b, ab2_a, ab2_b})
"""
from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

AB_DIR = Path(__file__).resolve().parent
APP_DIR = AB_DIR.parent.parent

SIZES = {"1280": (1280, 900), "1920": (1920, 900), "390": (390, 844)}
JOBS = {
    "ab1_a": ("design-system/ab/proto_ab1_a.py", 8621),
    "ab1_b": ("design-system/ab/proto_ab1_b.py", 8622),
    "ab2_a": ("design-system/ab/proto_ab2_a.py", 8623),
    "ab2_b": ("design-system/ab/proto_ab2_b.py", 8624),
}


def _wait_for_port(port: int, timeout: float = 40.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.5)
    return False


def run_one(script_rel: str, port: int, out_prefix: str, widths: list[str]) -> bool:
    server = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", script_rel,
         "--server.headless", "true", "--server.port", str(port)],
        cwd=str(APP_DIR), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    ok = True
    try:
        if not _wait_for_port(port):
            out, _ = server.communicate(timeout=5) if server.poll() is not None else (b"", b"")
            print(f"FAIL: {script_rel} did not open port {port}. Output: {out[:2000]}")
            return False
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for w in widths:
                width, height = SIZES[w]
                page = browser.new_page(viewport={"width": width, "height": height})
                page.goto(f"http://127.0.0.1:{port}", wait_until="networkidle")
                # Wait for the actual data grid to paint (robust completion signal --
                # checking for the ABSENCE of the "Running" spinner text raced with
                # React re-renders and produced false-negative "already done" reads).
                page.wait_for_selector('[data-testid="stDataFrame"]', state="visible", timeout=120000)
                if page.locator(".js-plotly-plot").count() > 0:
                    page.wait_for_selector(".js-plotly-plot .scatterlayer", state="visible", timeout=15000)
                page.wait_for_timeout(1000)
                out_path = AB_DIR / f"{out_prefix}_{w}.png"
                page.screenshot(path=str(out_path), full_page=False)
                print("Saved", out_path)
                page.close()
            browser.close()
    except Exception as e:
        print(f"FAIL: {script_rel} raised: {e}")
        ok = False
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=10)
    return ok


def main() -> int:
    if len(sys.argv) == 3:
        prefix, widths_csv = sys.argv[1], sys.argv[2]
        script, port = JOBS[prefix]
        ok = run_one(script, port, prefix, widths_csv.split(","))
        print(f"{'PASS' if ok else 'FAIL'}: {prefix}")
        return 0 if ok else 1

    all_ok = True
    for prefix, (script, port) in JOBS.items():
        ok = run_one(script, port, prefix, ["1280"])
        all_ok = all_ok and ok
        print(f"{'PASS' if ok else 'FAIL'}: {script}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())

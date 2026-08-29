"""
R1 (stream R-D2) A/B runner -- ONE Streamlit server, four variants selected by
the `?variant=` query parameter, Playwright screenshot per variant, then a
clean terminate. Same launch/wait/terminate pattern as run_ab.py (stream D1)
and ops/_probe_menu.py; kaleido is NOT installed and is not to be added, so the
PNGs come from a real browser paint, not from a static image export.

Usage (cwd `app/`):  python design-system/ab/run_ab_r1.py [--port 8631]
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
SCRIPT = "design-system/ab/proto_r1.py"
VARIANTS = ["ab3_a", "ab3_b", "ab4_a", "ab4_b"]
if "--ship" in sys.argv:
    SCRIPT = "design-system/ab/proto_ship.py"
    VARIANTS = ["r1_shipped_builders"]
SIZES = {"1280": (1280, 900), "390": (390, 844)}


def _wait_for_port(port: int, timeout: float = 60.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.5)
    return False


def main() -> int:
    port = 8631
    if "--port" in sys.argv:
        port = int(sys.argv[sys.argv.index("--port") + 1])
    widths = ["1280"]
    if "--widths" in sys.argv:
        widths = sys.argv[sys.argv.index("--widths") + 1].split(",")
    server = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", SCRIPT,
         "--server.headless", "true", "--server.port", str(port)],
        cwd=str(APP_DIR), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    ok = True
    try:
        if not _wait_for_port(port):
            out = server.stdout.read(4000) if server.stdout else b""
            print(f"FAIL: server did not open port {port}: {out!r}")
            return 1
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for w in widths:
              width, height = SIZES[w]
              page = browser.new_page(viewport={"width": width, "height": height})
              for v in VARIANTS:
                  try:
                      page.goto(f"http://127.0.0.1:{port}/?variant={v}", wait_until="networkidle")
                      page.wait_for_selector(".js-plotly-plot", state="visible", timeout=120000)
                      page.wait_for_selector(".js-plotly-plot .barlayer", state="attached", timeout=30000)
                      page.wait_for_timeout(1500)
                      out_path = AB_DIR / f"{v}_{w}.png"
                      page.screenshot(path=str(out_path), full_page=False)
                      # Measured criteria, read off the live DOM rather than eyeballed.
                      metrics = page.evaluate(
                          """() => {
                            const plots = [...document.querySelectorAll('.js-plotly-plot')];
                            const vh = window.innerHeight;
                            const first = plots[0];
                            const r = first.getBoundingClientRect();
                            const bars = [...first.querySelectorAll('.barlayer .point path')];
                            const anns = [...first.querySelectorAll('.annotation-text')];
                            const yticks = [...first.querySelectorAll('.yaxislayer-above .ytick text')];
                            const above = yticks.filter(t => t.getBoundingClientRect().bottom <= vh).length;
                            const plotArea = first.querySelector('.nsewdrag');
                            const pa = plotArea ? plotArea.getBoundingClientRect() : null;
                            const clipped = anns.filter(a => pa && a.getBoundingClientRect().right > pa.right + 1).length;
                            const longest = bars.reduce((m, b) => Math.max(m, b.getBoundingClientRect().width), 0);
                            return {
                              n_plots: plots.length,
                              plot_w: Math.round(r.width), plot_h: Math.round(r.height),
                              plot_area_w: pa ? Math.round(pa.width) : null,
                              y_labels: yticks.length, y_labels_above_fold: above,
                              n_bars: bars.length, n_annotations: anns.length,
                              annotations_clipped: clipped,
                              longest_bar_px: Math.round(longest),
                              scroll_ok: document.documentElement.scrollWidth <= window.innerWidth + 2,
                            };
                          }"""
                      )
                      print(f"{v}: saved {out_path.name}  {metrics}")
                  except Exception as e:  # noqa: BLE001
                      print(f"FAIL: {v} raised: {e}")
                      ok = False
            browser.close()
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=10)
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

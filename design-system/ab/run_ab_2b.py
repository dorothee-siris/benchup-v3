"""
Phase 2B (stream V) A/B runner -- ONE Streamlit server, variants selected by
`?variant=`, a Playwright screenshot per variant, then a clean terminate. Same
launch / wait / measure / terminate pattern as `run_ab_r1.py`; kaleido is NOT
installed and is not to be added, so the PNGs come from a real browser paint.

What it MEASURES, rather than eyeballs (the A4 acceptance):
  min_mark_px      the smallest rendered mark, floor 8 px
  max_overlap_frac the largest overlap between two marks OF ONE ROW, expressed
                   as a fraction of a mark's own diameter; ceiling 0.5
  span_px          how far the eye must travel to compare every institution on
                   ONE category -- the criterion that separates a dot row from
                   a small-multiples grid
Rows are resolved from geometry, not guessed: a mark's row index is
floor((y_centre - plot_top) / row_pitch) with row_pitch = plot_height / n_rows.

Usage (cwd `app/`):  python design-system/ab/run_ab_2b.py [--port 8641] [--ship]
"""
from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

AB_DIR = Path(__file__).resolve().parent
APP_DIR = AB_DIR.parent.parent
SCRIPT = "design-system/ab/proto_2b.py"

# variant -> (n_rows for the row-clustering, marks selector, viewport height)
VARIANTS = {
    "ab5_a": dict(rows=26, kind="scatter", height=2600),
    "ab5_b": dict(rows=26, kind="bar", height=1200),
    "ab6_a": dict(rows=0, kind="scatter", height=1000, occlusion=True),
    "ab6_a2": dict(rows=0, kind="scatter", height=1000, occlusion=True),
    "ab6_aq": dict(rows=0, kind="scatter", height=1000, occlusion=True),
    "ab6_a3": dict(rows=0, kind="scatter", height=1000, occlusion=True),
    "ab6_b": dict(rows=0, kind="scatter", height=1000, occlusion=True),
}
SHIP = {"2b_shipped_builders": dict(rows=0, kind="scatter", height=9900)}

MEASURE_JS = """
(cfg) => {
  const plots = [...document.querySelectorAll('.js-plotly-plot')];
  const isBar = cfg.kind === 'bar';
  const traceSel = isBar ? '.barlayer .trace' : '.scatterlayer .trace';
  const out = {n_plots: plots.length, per_plot: []};
  let minMark = Infinity, maxOverlap = 0, spans = [], nMarks = 0, nTraces = 0;
  let crossPairs = 0, occluded = 0, allMarks = [];
  plots.forEach((plot, pi) => {
    const area = plot.querySelector('.nsewdrag');
    const pa = area ? area.getBoundingClientRect() : plot.getBoundingClientRect();
    const traces = [...plot.querySelectorAll(traceSel)];
    nTraces += traces.length;
    let marks = [];
    traces.forEach((tr, ti) => {
      [...tr.querySelectorAll('path')].forEach(p2 => {
        const r = p2.getBoundingClientRect();
        if (r.width <= 0 && r.height <= 0) return;
        // a BAR's mark size is its THICKNESS (its length is the datum); a DOT's
        // is its diameter
        const size = isBar ? r.height : Math.min(r.width, r.height);
        if (size <= 0) return;
        marks.push({x: r.left + r.width / 2, y: r.top + r.height / 2,
                    w: r.width, h: r.height, size: size, t: pi + '.' + ti});
      });
    });
    nMarks += marks.length;
    marks.forEach(m => { minMark = Math.min(minMark, m.size); });
    allMarks = allMarks.concat(marks);
    if (cfg.rows > 0 && marks.length) {
      const pitch = pa.height / cfg.rows;
      const byRow = {};
      marks.forEach(m => {
        const ri = Math.floor((m.y - pa.top) / pitch);
        (byRow[ri] = byRow[ri] || []).push(m);
      });
      Object.values(byRow).forEach(row => {
        let top = Infinity, bot = -Infinity;
        row.forEach(m => { top = Math.min(top, m.y - m.h / 2); bot = Math.max(bot, m.y + m.h / 2); });
        if (row.length > 1) spans.push(bot - top);
        for (let i = 0; i < row.length; i++) for (let j = i + 1; j < row.length; j++) {
          const a = row[i], b = row[j];
          const d = Math.hypot(a.x - b.x, a.y - b.y);
          const diam = (a.size + b.size) / 2;
          maxOverlap = Math.max(maxOverlap, Math.max(0, 1 - d / diam));
        }
      });
    }
    out.per_plot.push({i: pi, w: Math.round(pa.width), h: Math.round(pa.height),
                       marks: marks.length, traces: traces.length});
  });
  // CROSS-INSTITUTION OCCLUSION: a mark whose centre is covered by a mark of a
  // DIFFERENT trace has lost its identity to the reader. Small multiples make
  // this zero by construction; an overlay is judged on how far above zero it is.
  if (cfg.occlusion) {
    for (let i = 0; i < allMarks.length; i++) {
      const a = allMarks[i];
      let hit = false;
      for (let j = 0; j < allMarks.length && !hit; j++) {
        if (i === j) continue;
        const b = allMarks[j];
        if (a.t === b.t) continue;
        crossPairs++;
        const d = Math.hypot(a.x - b.x, a.y - b.y);
        if (d < (a.size + b.size) / 4) hit = true;
      }
      if (hit) occluded++;
    }
    out.cross_occluded_frac = allMarks.length
      ? Math.round(occluded / allMarks.length * 1000) / 1000 : null;
  }
  if (cfg.rows > 0 && isBar) {
    // a category's bars sit in SIX different panels of one figure, so the span
    // the eye must cross to compare them is the figure's own vertical extent
    const fr = plots[0].getBoundingClientRect();
    spans = [fr.height];
  }
  spans.sort((a, b) => a - b);
  out.n_marks = nMarks;
  out.n_traces = nTraces;
  out.min_mark_px = isFinite(minMark) ? Math.round(minMark * 10) / 10 : null;
  out.max_overlap_frac = Math.round(maxOverlap * 1000) / 1000;
  out.span_px = spans.length ? Math.round(spans[Math.floor(spans.length / 2)]) : null;
  out.fig_h = plots.length ? Math.round(plots[0].getBoundingClientRect().height) : null;
  out.doc_h = Math.round(document.documentElement.scrollHeight);
  out.scroll_ok = document.documentElement.scrollWidth <= window.innerWidth + 2;
  return out;
}
"""


def _wait_for_port(port: int, timeout: float = 90.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.5)
    return False


def main() -> int:
    port = 8641
    if "--port" in sys.argv:
        port = int(sys.argv[sys.argv.index("--port") + 1])
    variants = SHIP if "--ship" in sys.argv else VARIANTS
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
            for name, cfg in variants.items():
                try:
                    page = browser.new_page(viewport={"width": 1280, "height": cfg["height"]})
                    page.goto(f"http://127.0.0.1:{port}/?variant={name}", wait_until="networkidle")
                    page.wait_for_selector(".js-plotly-plot", state="visible", timeout=180000)
                    page.wait_for_timeout(2500)
                    out_path = AB_DIR / f"{name}_1280.png"
                    page.screenshot(path=str(out_path), full_page=False)
                    metrics = page.evaluate(MEASURE_JS, cfg)
                    print(f"{name}: saved {out_path.name}  {json.dumps(metrics)}")
                    page.close()
                except Exception as e:  # noqa: BLE001
                    print(f"FAIL: {name} raised: {e}")
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

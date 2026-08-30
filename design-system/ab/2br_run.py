"""Phase 2B-R (stream VS) A/B runner -- ONE Streamlit server, a Playwright
screenshot and a DOM measurement per variant, then a clean terminate.

Same launch / wait / measure / terminate pattern as `run_ab_2b.py`; kaleido is
NOT installed and is not to be added, so every PNG is a real browser paint.

WHAT IT MEASURES, per A/B, off the live DOM -- nothing here is eyeballed:

  A/B #7  min_mark_px       the smallest rendered mark (a BAR's mark size is its
                            THICKNESS, a DOT's its diameter), floor 8
          span_px           how far the eye travels to compare all three
                            institutions on ONE category row
          n_value_labels    value labels drawn ON the marks (the thing the dot
                            row cannot do at all)
          fig_h             figure height, the price of the form

  A/B #8  occluded_frac     the share of bubbles whose CENTRE is covered by any
                            other bubble (both variants are pooled, so this, not
                            the 2B cross-trace figure, is the comparable number)
          bar_gap_px        |length(A) - length(B)| in px for the LOPSIDED probe
                            topic and for the BALANCED one -- how much of the
                            imbalance the paired bars actually put on screen
          fills             the two probe topics' rendered fill colours in the
                            gradient variant, so their perceptual distance can be
                            put through the dataviz validator (the same tool the
                            palette is built with) instead of guessed

  A/B #9  label_gap_px      median distance from a value label's near edge to
                            the mark it belongs to
          label_collisions  pairs of value labels whose boxes overlap

Usage (cwd `app/`):
    python design-system/ab/2br_run.py [--port 8643] [--ship]
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
SCRIPT = "design-system/ab/2br_proto.py"

VARIANTS = {
    "2br_ab7_a": dict(rows=26, kind="bar", height=2200, labels=True),
    "2br_ab7_b": dict(rows=26, kind="scatter", height=2200, labels=True),
    "2br_ab8_a": dict(rows=14, kind="mixed", height=1800, occlusion=True, labels=True),
    "2br_ab8_b": dict(rows=0, kind="scatter", height=900, occlusion=True),
    "2br_ab9_a": dict(rows=26, kind="bar", height=2200, labels=True),
    "2br_ab9_b": dict(rows=26, kind="bar", height=2200, labels=True),
}
SLIDER = {
    "2br_ab8_n40": dict(rows=0, kind="scatter", height=900, occlusion=True),
    "2br_ab8_n60": dict(rows=0, kind="scatter", height=900, occlusion=True),
    "2br_ab8_n80": dict(rows=0, kind="scatter", height=900, occlusion=True),
}
SHIP = {"2br_shipped_builders": dict(rows=0, kind="mixed", height=6200, labels=True)}
QUERY = {k: k.replace("2br_", "") for k in list(VARIANTS) + list(SLIDER)}
QUERY.update({"2br_shipped_builders": "ship"})

MEASURE_JS = """
(cfg) => {
  const plots = [...document.querySelectorAll('.js-plotly-plot')];
  const out = {n_plots: plots.length, per_plot: []};
  let minMark = Infinity, spans = [], nMarks = 0, nTraces = 0, nLabels = 0;
  let allMarks = [], labelBoxes = [], labelGaps = [], fills = [], barLens = [];
  plots.forEach((plot, pi) => {
    const area = plot.querySelector('.nsewdrag');
    const pa = area ? area.getBoundingClientRect() : plot.getBoundingClientRect();
    const bars = [...plot.querySelectorAll('.barlayer .trace')];
    const dots = [...plot.querySelectorAll('.scatterlayer .trace')];
    const traces = bars.concat(dots);
    nTraces += traces.length;
    let marks = [];
    traces.forEach((tr, ti) => {
      const isBar = tr.closest('.barlayer') !== null;
      [...tr.querySelectorAll('path')].forEach(p2 => {
        const r = p2.getBoundingClientRect();
        if (r.width <= 0 && r.height <= 0) return;
        const size = isBar ? r.height : Math.min(r.width, r.height);
        if (size <= 0) return;
        marks.push({x: r.left + r.width / 2, y: r.top + r.height / 2,
                    w: r.width, h: r.height, size: size, bar: isBar,
                    left: r.left, right: r.right,
                    fill: p2.getAttribute('style') || p2.getAttribute('fill') || '',
                    t: pi + '.' + ti});
        if (isBar) barLens.push({y: r.top + r.height / 2, len: r.width, t: pi + '.' + ti});
      });
      // value labels drawn ON the marks (plotly puts them in .bartext / .textpoint)
      [...tr.querySelectorAll('.bartext, .textpoint text, text.bartext')].forEach(tx => {
        const r = tx.getBoundingClientRect();
        if (r.width <= 0) return;
        nLabels++;
        labelBoxes.push({x: r.left + r.width / 2, y: r.top + r.height / 2,
                         l: r.left, r: r.right, t: r.top, b: r.bottom});
      });
    });
    // pooled-centre labels are ANNOTATIONS, not bar text
    [...plot.querySelectorAll('.annotation-text')].forEach(tx => {
      const r = tx.getBoundingClientRect();
      if (r.width <= 0) return;
      nLabels++;
      labelBoxes.push({x: r.left + r.width / 2, y: r.top + r.height / 2,
                       l: r.left, r: r.right, t: r.top, b: r.bottom});
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
      });
    }
    out.per_plot.push({i: pi, w: Math.round(pa.width), h: Math.round(pa.height),
                       marks: marks.length, traces: traces.length});
  });
  // LABEL GEOMETRY: nearest mark edge to each label box, and label-label overlaps
  if (cfg.labels) {
    labelBoxes.forEach(L => {
      let best = Infinity;
      allMarks.forEach(m => {
        const dy = Math.abs(m.y - L.y);
        if (dy > Math.max(m.h, 2)) return;              // not this row
        const gap = L.l >= m.right ? L.l - m.right
                  : (L.r <= m.left ? m.left - L.r : 0);  // 0 = label sits on the mark
        best = Math.min(best, gap);
      });
      if (isFinite(best)) labelGaps.push(best);
    });
    let coll = 0;
    for (let i = 0; i < labelBoxes.length; i++)
      for (let j = i + 1; j < labelBoxes.length; j++) {
        const a = labelBoxes[i], b = labelBoxes[j];
        if (a.l < b.r && b.l < a.r && a.t < b.b && b.t < a.b) coll++;
      }
    out.label_collisions = coll;
    labelGaps.sort((x, y) => x - y);
    out.label_gap_px_median = labelGaps.length
      ? Math.round(labelGaps[Math.floor(labelGaps.length / 2)] * 10) / 10 : null;
    out.label_gap_px_max = labelGaps.length
      ? Math.round(labelGaps[labelGaps.length - 1] * 10) / 10 : null;
  }
  if (cfg.occlusion) {
    let occ = 0;
    for (let i = 0; i < allMarks.length; i++) {
      const a = allMarks[i];
      if (a.bar) continue;
      let hit = false;
      for (let j = 0; j < allMarks.length && !hit; j++) {
        if (i === j) continue;
        const b = allMarks[j];
        if (b.bar) continue;
        const d = Math.hypot(a.x - b.x, a.y - b.y);
        if (d < (a.size + b.size) / 4) hit = true;
      }
      if (hit) occ++;
    }
    const dots = allMarks.filter(m => !m.bar).length;
    out.occluded_frac = dots ? Math.round(occ / dots * 1000) / 1000 : null;
    out.n_bubbles = dots;
    // the fill of the LARGEST and SMALLEST-fraction bubbles, for the gradient run
    const withFill = allMarks.filter(m => !m.bar && m.fill);
    out.fill_sample = withFill.slice(0, 400).map(m => m.fill.match(/fill: ?(rgb\\([^)]*\\)|#[0-9a-fA-F]{6})/))
      .filter(Boolean).map(m => m[1]);
  }
  // paired-bar imbalance: for every row, the two longest bar lengths
  if (cfg.rows > 0 && barLens.length) {
    const byRow = {};
    barLens.forEach(b => { const k = Math.round(b.y); (byRow[k] = byRow[k] || []).push(b.len); });
    const gaps = Object.values(byRow).filter(v => v.length > 1)
      .map(v => { v.sort((a, b) => b - a); return Math.round((v[0] - v[v.length - 1]) * 10) / 10; });
    gaps.sort((a, b) => a - b);
    out.bar_gap_px_min = gaps.length ? gaps[0] : null;
    out.bar_gap_px_max = gaps.length ? gaps[gaps.length - 1] : null;
    out.bar_gap_px_median = gaps.length ? gaps[Math.floor(gaps.length / 2)] : null;
  }
  spans.sort((a, b) => a - b);
  out.n_marks = nMarks;
  out.n_traces = nTraces;
  out.n_value_labels = nLabels;
  out.min_mark_px = isFinite(minMark) ? Math.round(minMark * 10) / 10 : null;
  out.span_px = spans.length ? Math.round(spans[Math.floor(spans.length / 2)]) : null;
  out.fig_h = plots.length ? Math.round(plots[0].getBoundingClientRect().height) : null;
  out.doc_h = Math.round(document.documentElement.scrollHeight);
  out.scroll_ok = document.documentElement.scrollWidth <= window.innerWidth + 2;
  return out;
}
"""


def _wait_for_port(port: int, timeout: float = 120.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.5)
    return False


def main() -> int:
    port = 8643
    if "--port" in sys.argv:
        port = int(sys.argv[sys.argv.index("--port") + 1])
    variants = VARIANTS
    if "--ship" in sys.argv:
        variants = dict(SLIDER, **SHIP)
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
                    page.goto(f"http://127.0.0.1:{port}/?variant={QUERY[name]}",
                              wait_until="networkidle")
                    page.wait_for_selector(".js-plotly-plot", state="visible", timeout=240000)
                    page.wait_for_timeout(3000)
                    out_path = AB_DIR / f"{name}_1280.png"
                    page.screenshot(path=str(out_path), full_page=False)
                    metrics = page.evaluate(MEASURE_JS, cfg)
                    metrics.pop("fill_sample", None) if name != "2br_ab8_b" else None
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

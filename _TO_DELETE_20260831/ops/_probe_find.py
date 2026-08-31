"""
Acceptance probe for the Find page (BUILD_PLAN_2A.md Stream E; extended for
Refinement R1 by stream R-E2 against S9.2 L16-L23). Same shape as
ops/_probe_menu.py: start `streamlit run pages/1_<emoji>_Find.py` as a
subprocess, drive it headless with Playwright, ALWAYS terminate the server.

Selectors are locale-independent: the `st-key-<key>` classes the page's own
keyed widgets/containers emit, `[role="tab"]`, `[data-testid=...]` -- never
literal UI strings, and never `inner_text` on a table (st.dataframe is a canvas
grid; the Assembly Line gotcha list forbids text assertions on it, so row-level
facts are checked against the engine/CSV instead, at the end).

The seed is injected through the page's own `?seed=<id>` query parameter, which
`views_find.render()` reads ONCE into `st.session_state["seed_id"]`.

R1 checks added here: the profile container renders; the six chart panels are
expanders and one of them really holds a Plotly figure once opened; the
benchmark controls live in the MAIN area and no longer in the sidebar; the
breakdown segmented control swaps the chip legend; the wordcloud <img> exists.

R2 checks added by stream E3 (BUILD_PLAN_2A.md S10.2 L29-L34): the profile's
row 1 is three columns with the wordcloud in the third; there are eight KPI
tiles; the frontier panel's segmented control really changes how many points
the scatter plots (read off the live Plotly trace, not off a caption); the
sidebar selectboxes render display LABELS, not internal values.

Usage:  python ops/_probe_find.py [--port 8602]
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

from playwright.sync_api import sync_playwright

APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))

from lib import copy as ui_copy  # noqa: E402  (needs APP_DIR on sys.path first)
PAGE = "pages/1_\U0001F50E_Find.py"
DEFAULT_PORT = 8602
SEEDS = ["I40413290", "I265217849", "I277688954"]
SHOT_SEED = "I68947357"   # Universite de Strasbourg -- the R1 reference seed
GOLD_SEED = "I40413290"   # University of Gdansk -- the seed the L1 golden pins
SHOT_DIR = APP_DIR / "tests" / "ui" / "screenshots"
WIDTHS = [1920, 1280, 390]
SHOT_HEIGHT_PX = 2400   # see _probe_widths: full_page=True is a no-op here
TALL_SHOT_PX = 5600     # inspection I-4: match _probe_compare so full pages ship in the artifact
N_DEFAULT_TABS = 10   # Overview + the 8 default lenses + Aspirational
N_TOGGLED_TABS = 12   # ... + C1 + L7
N_PANELS = 6          # Fields, Top subfields, Top topics, Frontier, SDG, ERC
N_TILES = 6           # 2B-R2-6: 2 x 3 card grid (publications, SDG, frontier,
                      # PPtop10, international co-pubs, industrial co-pubs)
CRASH_SEED = "I154202486"   # Ifremer -- umbrella AND type-corrected, the profile
                            # that crashed at gate 2B-R (2B-R2-1a)
GOLD_RANK1 = ("I34250744", 0.793119)

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


def _captions(page) -> str:
    """textContent (not innerText) so captions inside inactive tab panels count."""
    return page.evaluate(
        "Array.from(document.querySelectorAll('[data-testid=\"stCaptionContainer\"]'))"
        ".map(e => e.textContent).join('|')")


def _chip_legend(page) -> str:
    """The ONE chip legend the breakdown pair shares -- `charts.chip_legend_html`
    is the only markup on the page with a `flex-wrap` inline style, so this
    finds it without matching any user-facing string."""
    return page.evaluate(
        "Array.from(document.querySelectorAll('.st-key-profile div[style*=\"flex-wrap\"]'))"
        ".map(e => e.textContent).join('|')")


def _row1_columns(page) -> int:
    """How many COLUMNS the profile's first horizontal block has. `:scope >`
    keeps the count on that block's own children, so the nested `st.columns`
    the KPI grid builds inside column 2 cannot inflate it."""
    return page.evaluate(
        "(() => { const b = document.querySelector("
        "'.st-key-profile [data-testid=\"stHorizontalBlock\"]');"
        " return b ? b.querySelectorAll(':scope > [data-testid=\"stColumn\"]').length : -1;"
        "})()")


def _row1_images(page) -> int:
    return page.evaluate(
        "(() => { const b = document.querySelector("
        "'.st-key-profile [data-testid=\"stHorizontalBlock\"]');"
        " return b ? b.querySelectorAll('[data-testid=\"stImage\"] img').length : -1;"
        "})()")


def _selectbox_text(page, key: str) -> str:
    """A sidebar selectbox's rendered LABEL plus its CURRENT selection. The
    selection is the react-aria ComboBox input's `value`, not text content."""
    root = f'[data-testid="stSidebar"] .st-key-{key}'
    label = page.locator(root).first.inner_text()
    value = page.locator(f"{root} input").first.input_value()
    return f"{label} {value}"


def _frontier_points(page) -> int:
    """Total marker count across the frontier scatter's own Plotly traces --
    read off the live figure object, so the mode swap is verified on what is
    actually PLOTTED rather than on a caption the page prints."""
    return page.evaluate(
        "(() => { const el = document.querySelector("
        "'.st-key-panel_frontier .js-plotly-plot');"
        " if (!el || !el.data) return -1;"
        " return el.data.reduce((a, t) => a + ((t.x && t.x.length) || 0), 0); })()")


def _frontier_signature(page) -> str:
    """The plotted TOPIC SET's signature (per-trace x values, rounded), not the
    point count: 2B-R-13's single shared top-N slider means both frontier modes
    can tie on COUNT while plotting different topics (2BR_H.md; inspection I-3)."""
    return page.evaluate(
        "(() => { const el = document.querySelector("
        "'.st-key-panel_frontier .js-plotly-plot');"
        " if (!el || !el.data) return '';"
        " return el.data.map(t => (t.x || []).map(v => Number(v).toFixed(4)).join(','))"
        ".join('|'); })()")


def _load(page, seed: str) -> None:
    page.goto(f"http://127.0.0.1:{PORT}/?seed={seed}", wait_until="domcontentloaded")
    page.wait_for_selector('[role="tab"]', timeout=180_000)
    page.wait_for_timeout(3000)


def _probe_seed(page, seed: str) -> None:
    _load(page, seed)
    check(page.locator('[data-testid="stException"]').count() == 0,
          f"{seed}: no Streamlit exception element on the page")
    tabs = page.locator('[role="tab"]').count()
    check(tabs >= N_DEFAULT_TABS, f"{seed}: tab count {tabs} >= {N_DEFAULT_TABS}")
    check(tabs == N_DEFAULT_TABS,
          f"{seed}: optional-lens tabs absent by default (tab count is exactly {N_DEFAULT_TABS})")


def _probe_profile(page) -> None:
    """R1/L17 + R2/L30-L34: the profile section's grid, its tiles, its
    wordcloud, its six panels and the frontier panel's two modes."""
    _load(page, SHOT_SEED)
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    top_shot = SHOT_DIR / "e3_find_top_1280.png"
    page.screenshot(path=str(top_shot))          # viewport only: y = 0, seed loaded
    print("Saved screenshot:", top_shot)
    check(top_shot.is_file(), "top-of-page screenshot written at 1280 px with the seed loaded")

    check(page.locator(".st-key-profile").count() == 1,
          "the profile container renders exactly once")
    cols = _row1_columns(page)
    check(cols == 2, f"the profile's row 1 is two columns - cards | identity+cloud (found {cols})")
    imgs = _row1_images(page)
    check(imgs >= 1, f"the wordcloud <img> sits inside that row-1 block (found {imgs})")
    tiles = page.locator(".st-key-profile .benchup-kpi").count()
    check(tiles == N_TILES, f"the profile carries {N_TILES} KPI cards (found {tiles})")
    subs = page.locator(".st-key-profile .benchup-kpi-sub").count()
    check(subs == N_TILES,
          f"every card carries exactly one small line (found {subs} for {N_TILES} cards)")
    # 2B-R2-6: FIVE of the six small lines are the index baseline; the sixth is
    # the publications card's fractional-counting note, which carries its own
    # hook inside that same line.
    notes = page.locator(".st-key-profile .benchup-kpi-value2").count()
    check(notes == 1,
          f"exactly one card (publications) carries the fractional note (found {notes})")
    check(_captions(page).find(ui_copy.FIND["COVERAGE_LINE"].split("{")[0].strip()) == -1,
          "the retired coverage line is nowhere on the page")

    panels = [f".st-key-panel_{n}" for n in
              ("fields", "subfields", "topics", "frontier", "sdg", "erc")]
    present = sum(1 for sel in panels if page.locator(sel).count() >= 1)
    check(present == N_PANELS, f"the six chart panels are keyed expanders (found {present})")

    # Open the Top-subfields panel (the panel R2/L34 rewrote) and check a real
    # Plotly figure is VISIBLE inside it -- the body renders collapsed too
    # (st.expander folds the display, not the execution), so visibility, not
    # presence, is the meaningful assertion.
    page.locator(".st-key-panel_subfields summary").first.click()
    page.wait_for_timeout(2500)
    fig = page.locator(".st-key-panel_subfields .js-plotly-plot").first
    check(fig.count() >= 1 and fig.is_visible(),
          "opening the Top-subfields panel reveals a Plotly figure inside it")
    check(page.locator(".st-key-panel_subfields .st-key-sort_subfields").count() == 0,
          "the Top-subfields panel carries NO sort control (R2/L34)")
    shot = SHOT_DIR / "e3_find_subfields_open_1280.png"
    page.screenshot(path=str(shot), full_page=True)
    print("Saved screenshot:", shot)
    check(shot.is_file(), "screenshot written with the Top-subfields panel open")

    # L33: the frontier panel's segmented control hands `fig_frontier` a
    # different frame, so the scatter must plot a different number of points.
    page.locator(".st-key-panel_frontier summary").first.click()
    page.wait_for_timeout(3000)
    before_pts = _frontier_points(page)
    check(before_pts > 0, f"the frontier scatter plots points in its default mode ({before_pts})")
    before_sig = _frontier_signature(page)
    page.locator(".st-key-frontier_mode button").nth(1).click()
    page.wait_for_timeout(5000)
    after_pts = _frontier_points(page)
    after_sig = _frontier_signature(page)
    check(after_pts > 0 and after_sig != before_sig,
          f"the frontier mode control changes the plotted topic set "
          f"({before_pts} -> {after_pts} points; signatures differ)")
    page.locator(".st-key-frontier_mode button").nth(0).click()
    page.wait_for_timeout(3000)

    # The segmented control swaps the identity family for BOTH figures at once,
    # so the ONE shared chip legend must change with it.
    before = _chip_legend(page)
    check(bool(before.strip()), "the breakdown pair renders a chip legend")
    page.locator(".st-key-breakdown_dim button").nth(1).click()
    page.wait_for_timeout(4000)
    after = _chip_legend(page)
    check(after != before,
          "the breakdown segmented control swaps the chip legend (domain <-> document type)")
    page.locator(".st-key-breakdown_dim button").nth(0).click()
    page.wait_for_timeout(3000)


def _probe_controls(page) -> None:
    """R1/L16: the benchmark controls live in the MAIN area, with UNCHANGED
    widget keys, and the sidebar no longer carries them."""
    _load(page, SHOT_SEED)
    for key in ("depth", "c1_on", "l7_on", "postfilters"):
        check(page.locator(f".st-key-{key}").count() >= 1,
              f"controls-row widget `{key}` renders in the page")
        check(page.locator(f'[data-testid="stSidebar"] .st-key-{key}').count() == 0,
              f"controls-row widget `{key}` is NOT in the sidebar any more")
    for key in ("tree", "basis"):
        check(page.locator(f'[data-testid="stSidebar"] .st-key-{key}').count() >= 1,
              f"counting & taxonomy control `{key}` stays in the sidebar")
    # R2/L29: the sidebar shows a display LABEL; the internal value never
    # reaches the reader. A Streamlit selectbox is a react-aria ComboBox, so its
    # CURRENT selection lives in the input's `value` property and not in the
    # element's text (measured on this build: inner_text returns the widget
    # LABEL alone) -- `_selectbox_text` reads both, which is what makes the
    # negative half of this check meaningful too.
    tree_text = _selectbox_text(page, "tree")
    check(ui_copy.TREE_LABELS["bestfit"] in tree_text,
          "the taxonomy selectbox renders its display label, not the internal value")
    check("bestfit" not in tree_text,
          "the internal taxonomy value never appears in the sidebar")
    basis_text = _selectbox_text(page, "basis")
    check(ui_copy.BASIS_LABELS["frac"] in basis_text,
          "the counting-basis selectbox renders its display label")
    check("frac" not in basis_text.replace(ui_copy.BASIS_LABELS["frac"], ""),
          "the internal counting-basis value never appears in the sidebar")

    before = _captions(page)
    for key in ("c1_on", "l7_on"):
        page.locator(f".st-key-{key} label").first.click()
        page.wait_for_timeout(4000)
    tabs = page.locator('[role="tab"]').count()
    check(tabs == N_TOGGLED_TABS,
          f"C1 and L7 toggles add their own tabs (tab count is {tabs}, expected {N_TOGGLED_TABS})")
    check(page.locator('[data-testid="stException"]').count() == 0,
          "no Streamlit exception after enabling the optional lenses")
    page.locator('.st-key-depth [data-testid="stRadioOption"]').nth(1).click()
    page.wait_for_timeout(4000)
    check(_captions(page) != before, "the depth caption changed when depth switched to its max")
    check(page.locator(".st-key-strip").count() >= 1,
          "the off-default strip appears once a control leaves its default")

    # The post-filters live one click down, inside their own expander.
    page.locator(".st-key-postfilters summary").first.click()
    page.wait_for_timeout(1500)
    page.locator(".st-key-f_types input").first.click()
    page.wait_for_timeout(800)
    page.keyboard.press("Enter")
    page.wait_for_timeout(5000)
    check(page.locator(".st-key-strip").count() >= 1,
          "the strip is still rendered with a type post-filter active")
    check(page.locator('[data-testid="stException"]').count() == 0,
          "no Streamlit exception after applying a type post-filter")


def _probe_crash_seed(browser) -> None:
    """2B-R2-1a: the profile that took the app down at gate 2B-R (Ifremer is
    both an umbrella and type-corrected). Rendered at all three widths, with
    the type correction asserted in its INLINE form -- the badge that used to
    carry it is gone, so a page that merely renders is not enough: the
    information has to still be there.

    The expected string is COMPOSED from `lib/copy.py` and the index's own two
    type columns, never typed here."""
    import pandas as pd

    row = pd.read_parquet(APP_DIR / "data" / "index.parquet",
                          columns=["institution_id", "type", "type_openalex"])
    row = row.loc[row["institution_id"] == CRASH_SEED].iloc[0]
    expected = ui_copy.FIND["IDENTITY_TYPE_CORRECTED"].format(
        kind=str(row["type"]), star="*", was=str(row["type_openalex"]))
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    for width in WIDTHS:
        page = browser.new_page(viewport={"width": width,
                                          "height": TALL_SHOT_PX if width >= 1280 else SHOT_HEIGHT_PX})
        _load(page, CRASH_SEED)
        check(page.locator('[data-testid="stException"]').count() == 0,
              f"{width} px: the formerly crashing profile renders with no exception")
        text = page.locator('[data-testid="stMain"]').inner_text()
        check(expected in text,
              f"{width} px: the type correction renders inline ({expected})")
        check(page.locator(".st-key-profile .benchup-kpi").count() == N_TILES,
              f"{width} px: the crash seed carries {N_TILES} cards")
        scroll = page.evaluate("document.documentElement.scrollWidth")
        inner = page.evaluate("window.innerWidth")
        check(scroll <= inner + 2,
              f"{width} px (crash seed): scrollWidth {scroll} <= innerWidth+2 {inner + 2}")
        path = SHOT_DIR / f"fa3_find_ifremer_{width}.png"
        page.screenshot(path=str(path), full_page=True)
        print("Saved screenshot:", path)
        check(path.is_file(), f"{width} px: crash-seed screenshot written")
        page.close()


def _probe_widths(browser) -> None:
    # A TALL viewport, not `full_page=True`: Streamlit's content scrolls inside
    # `[data-testid="stMain"]` rather than `document.body`, so Playwright's
    # full-page capture silently returns the viewport alone (measured by stream
    # R2-D on the same build). A 2400 px viewport is what actually puts the
    # whole profile section -- identity, the eight tiles and the breakdown pair
    # -- into the screenshot a reviewer reads.
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    for width in WIDTHS:
        page = browser.new_page(viewport={"width": width, "height": TALL_SHOT_PX if width >= 1280 else SHOT_HEIGHT_PX})
        _load(page, SHOT_SEED)
        scroll = page.evaluate("document.documentElement.scrollWidth")
        inner = page.evaluate("window.innerWidth")
        check(scroll <= inner + 2,
              f"{width} px: scrollWidth {scroll} <= innerWidth+2 {inner + 2}")
        path = SHOT_DIR / f"fa3_find_{width}.png"
        page.screenshot(path=str(path), full_page=True)
        print("Saved screenshot:", path)
        check(path.is_file(), f"{width} px: screenshot written")
        page.close()


def _recompute_check() -> None:
    """Read rank 1 back out of the L1 CSV the page's own export path produces
    (engine -> evidence -> exports.ranking_csv -> pandas), and compare with the
    golden. Also asserts the R1 export columns are present and populated."""
    sys.path.insert(0, str(APP_DIR))
    import pandas as pd

    from lib.engine import build_rows, build_substrates, load_context, rank_all
    from lib.engine.evidence import rows_evidence
    from lib.exports import ranking_csv

    ctx = load_context(str(APP_DIR / "data"))
    subs = build_substrates(ctx)
    rankings = rank_all(ctx, subs, GOLD_SEED)
    l1 = rankings["L1"]
    rows = build_rows(l1, ctx, len(l1["sorted_ids"]), rankings, subs)
    head = rows[:50]
    texts = rows_evidence(ctx, subs, "L1", GOLD_SEED, [r["institution_id"] for r in head])
    for r in head:
        r["evidence_text"] = texts.get(r["institution_id"])
    blob = ranking_csv(rows, seed_id=GOLD_SEED, lens="L1", tree=subs["tree"], basis=subs["basis"],
                       snapshot="", filters_label="")
    df = pd.read_csv(io.BytesIO(blob))
    top = df.iloc[0]
    print(f"RECOMPUTE: L1 rank {top['rank']} = {top['institution_id']} "
          f"score {top['lens_score']:.6f} (golden {GOLD_RANK1[0]} {GOLD_RANK1[1]:.6f})")
    check(str(top["institution_id"]) == GOLD_RANK1[0]
          and abs(float(top["lens_score"]) - GOLD_RANK1[1]) < 1e-3,
          "L1 rank-1 read back from the export CSV matches the golden row")
    check({"country", "total_frac_2020_2024", "evidence"} <= set(df.columns),
          "the export CSV carries the R1 columns (country name, fractional size, evidence)")
    check(bool(str(top["evidence"]).strip()),
          "the lens-specific evidence cell is populated on the top row")


def main() -> int:
    global PORT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help="port to run the Streamlit server on")
    PORT = parser.parse_args().port

    server = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", PAGE,
         "--server.headless", "true", "--server.port", str(PORT)],
        # DEVNULL, not PIPE: a deprecation warning per rerun would otherwise
        # fill an unread pipe buffer and block the server mid-probe.
        cwd=str(APP_DIR), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    try:
        if not _wait_for_port(PORT):
            print("FAIL: server did not open port", PORT)
            return 1
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 1000})
            for seed in SEEDS:
                _probe_seed(page, seed)
            _probe_profile(page)
            page.close()
            page = browser.new_page(viewport={"width": 1280, "height": 1000})
            _probe_controls(page)
            page.close()
            _probe_widths(browser)
            _probe_crash_seed(browser)
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

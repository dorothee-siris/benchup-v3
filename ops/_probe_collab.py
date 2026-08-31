"""
Acceptance probe for the Collaborate page (BUILD_PLAN_2BR.md stream LP,
decision 2B-R-10). Same shape as ops/_probe_find.py: start `streamlit run
pages/3_<handshake>_Collaborate.py` as a subprocess, drive it headless with
Playwright, ALWAYS terminate the server.

WHAT THIS PROBE IS FOR. Every number the page prints outside a dataframe canvas
is READ BACK OUT OF THE RENDERED DOM and compared with a fresh
`lib/collab_data.py` recompute of the SAME pair: the joint total, both joint
shares and their denominators, both ranks IN THEIR TWO DIRECTIONS, the joint
corpus's SDG line, the ERC panel line and its labelled denominator, and the
untapped rate. A caption that silently stops matching its own frame fails here.

Selectors are locale-independent -- the `st-key-<key>` classes the page's own
keyed widgets and containers emit, plus `[data-testid=...]`. The dataframes are
CANVAS grids: the Assembly Line gotcha list forbids `inner_text` assertions on
them, so their content is checked through the page's own CSV download and
through the markdown/captions printed beside them, never by reading cells.

TWO PAIRS ARE DRIVEN:
  * Universite de Strasbourg x CNRS -- the manager-verified anchor (12,694
    joint works; CNRS is Strasbourg's FIRST partner, Strasbourg is CNRS's
    SIXTEENTH: the rank direction this page has to render the right way round);
  * Universite de Strasbourg x Bavarian Academy of Sciences and Humanities -- a
    REAL sub-floor pair (2 joint works, under `collab_data.PAIR_TOPICS_FLOOR`),
    which must render the honest notice, no joint tables, and still every
    link-out.

Usage:  python ops/_probe_collab.py [--port 8604]
Exit 0 when every check passes; 1 otherwise. Stdout is ASCII-only (cp1252
console).
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))

from lib import collab_data, copy, links, views_collab  # noqa: E402
from lib.app_config import CFG  # noqa: E402
from lib.collab_data import UNTAPPED_COLS  # noqa: E402

PAGE = "pages/3_\U0001F91D_Collaborate.py"
DEFAULT_PORT = 8604
A_ID = "I68947357"        # Universite de Strasbourg
B_ID = "I1294671590"      # CNRS -- Strasbourg's own first partner
SUB_B_ID = "I109144446"   # Bavarian Academy of Sciences and Humanities: 2 joint works
SHOT_DIR = APP_DIR / "tests" / "ui" / "screenshots"
WIDTHS = [1920, 1280, 390]
SHOT_HEIGHT_PX = 2400   # see _probe_widths in ops/_probe_find.py: full_page=True is a no-op
TALL_SHOT_PX = 5600     # inspection I-4: match _probe_compare so all 4 sections ship in the artifact

# joint fields + joint subfields + joint topics + untapped + siblings + the two
# directional gap tables + the weighted topic overlap (2B-R-10 sections 2 and 3)
N_TABLES = 8
# a below-floor pair loses the three joint-corpus tables and nothing else
N_TABLES_BELOW_FLOOR = 5

TREE, BASIS = "bestfit", "frac"   # config defaults, i.e. what the page opens on

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


def _load(page, a: str = A_ID, b: str = B_ID) -> None:
    """Open the page on the deep link the app's own share control prints."""
    page.goto(f"http://127.0.0.1:{PORT}/?pair={a},{b}", wait_until="domcontentloaded")
    page.wait_for_selector('[data-testid="stDataFrame"]', timeout=240_000)
    page.wait_for_timeout(3000)


def _text(page) -> str:
    """The page's rendered text, markdown emphasis stripped so a `**bold**`
    template compares against what a reader actually sees."""
    return page.evaluate("document.body.innerText")


def _container_text(page, key: str) -> str:
    """textContent of the element the given widget/container key emits. The key
    is interpolated INTO the expression rather than passed as an argument:
    Playwright reads an arrow-function string as a function to serialise, not as
    a call, and the argument form silently returned an empty string here."""
    return page.evaluate(
        "(() => { const e = document.querySelector('.st-key-%s');"
        " return e ? e.textContent : ''; })()" % key)


def _hrefs(page) -> list:
    return page.evaluate(
        "Array.from(document.querySelectorAll('a[href]')).map(a => a.getAttribute('href'))")


def _plain(template: str) -> str:
    return template.replace("**", "")


def _matches_template(rendered: str, template: str) -> bool:
    """The rendered sentence is this copy template with its placeholders
    filled: the template becomes a regex, `{placeholder}` becomes `.*`."""
    pattern = "".join(".*" if part.startswith("{") else re.escape(part)
                      for part in re.split(r"(\{[^{}]*\})", template) if part)
    return re.fullmatch(pattern, _plain(rendered)) is not None


# 2B-R-10: the pulse line answers a DATA question in neutral vocabulary. These
# are the words a reader must never find there.
JUDGEMENT_WORDS = ("dying", "healthy", "weak", "strong", "poor", "disappoint",
                   "failing", "vibrant", "thriving")


def _names() -> dict:
    ctx = views_collab._bundle()["ctx"]
    return {i: str(ctx["index_by_id"].loc[i, "display_name"]) for i in (A_ID, B_ID, SUB_B_ID)}


# ---------------------------------------------------------- the anchor pair --

def _probe_pulse(page, text: str, names: dict) -> dict:
    """Section one, read back against a fresh `collab_data.pulse` recompute."""
    ctx = views_collab._bundle()["ctx"]
    p = collab_data.pulse(ctx, A_ID, B_ID)

    check(page.locator(".st-key-fig_pulse").count() > 0, "the pulse chart renders")
    chart = _container_text(page, "fig_pulse")
    star = f"{CFG['bonus_year']}{views_collab.BONUS_STAR}"
    check(star in chart, f"the pulse x-axis stars the partial year ({star})")
    check(str(collab_data.PULSE_YEARS[0]) in chart,
          "the pulse x-axis starts at the window's first year")

    legend = _container_text(page, "collab_legend")
    check(names[A_ID] in legend, "the legend strip names institution A")
    check(names[B_ID] in legend, "the legend strip names institution B")
    check(copy.COLLAB["LEGEND_JOINT"] in legend,
          "the legend strip carries the shared chip the pulse bars are drawn in")

    check(views_collab._count(p["copubs_total"]) in text,
          f"the joint total on the page is collab_data's own ({p['copubs_total']})")
    check(views_collab._pct(p["share_of_a"]) in text, "A's joint share is rendered")
    check(views_collab._pct(p["share_of_b"]) in text, "B's joint share is rendered")
    denom = copy.COLLAB["PULSE_SHARE_DENOM"].format(
        window=views_collab._window(collab_data.PULSE_YEARS),
        name_a=names[A_ID], name_b=names[B_ID],
        vol_a=views_collab._count(p["denominator_a"]),
        vol_b=views_collab._count(p["denominator_b"]))
    check(denom in text, "both share denominators and their window are named on the page")

    rank_line = _plain(copy.COLLAB["PULSE_RANK_LINE"].format(
        name_a=names[A_ID], name_b=names[B_ID],
        rank_of_b=views_collab._count(p["rank_in_a"]),
        rank_of_a=views_collab._count(p["rank_in_b"])))
    check(rank_line in text, "the two ranks are rendered in their two directions")
    check(p["rank_in_a"] == 1 and p["rank_in_b"] == 16,
          f"rank DIRECTION anchor: B is A's #{p['rank_in_a']}, A is B's #{p['rank_in_b']}")

    trend = views_collab._trend_line(p["yearly"])
    check(trend in text, "the plain-language pulse line matches the window comparison")
    check(any(_matches_template(trend, copy.COLLAB[k])
              for k in ("PULSE_TREND_UP", "PULSE_TREND_FLAT", "PULSE_TREND_DOWN",
                        "PULSE_TREND_NA")),
          "the pulse line is one of the four neutral trend templates")
    check(not any(w in trend.lower() for w in JUDGEMENT_WORDS),
          "the pulse line uses no value-judgement vocabulary")
    return p


def _probe_joint(page, text: str, pulse_row: dict) -> None:
    """Section two, read back against `collab_data.joint_profile`."""
    ctx = views_collab._bundle()["ctx"]
    subs = views_collab._subs(TREE, BASIS)
    prof = collab_data.joint_profile(ctx, subs, A_ID, B_ID)

    intro = copy.COLLAB["JOINT_INTRO"].format(cap=prof["meta"]["top_n_cap"],
                                              floor=prof["meta"]["floor"])
    check(intro in text, "the joint corpus discloses BOTH the topic floor and the top-N cap")

    shown = float(prof["topics"]["vol_total"].sum())
    tagged = int(prof["sdg_tagged_total"])
    sdg = copy.COLLAB["JOINT_SDG_LINE"].format(
        n_tagged=views_collab._count(tagged), n_shown=views_collab._count(shown),
        share=views_collab._pct(tagged / shown if shown > 0 else None))
    check(sdg in text, "the joint SDG line matches the shown-topic recompute")

    erc = prof["erc"]
    line = _plain(copy.COLLAB["JOINT_ERC_LINE"].format(
        panel=views_collab._erc_panel_label(ctx, erc["panel_idx"]),
        n_panel=views_collab._count(erc["panel_n"]),
        n_labelled=views_collab._count(erc["labelled_n"]),
        share=views_collab._pct(erc["panel_n"] / erc["labelled_n"])))
    check(line in text, "the ERC panel line divides by the LABELLED count, not the joint total")
    cap = copy.COLLAB["JOINT_ERC_CAPTION"].format(
        pct=views_collab._pct(erc["labelled_n"] / pulse_row["copubs_total"]))
    check(cap in text, "the ERC caption names the labelled denominator as a share of the pair")

    n_frontier = int(prof["topics"]["topic_id"].map(
        views_collab._frontier_flags(ctx)).eq(True).sum())
    check(copy.COLLAB["JOINT_FRONTIER_LINE"].format(
        n_frontier=views_collab._count(n_frontier)) in text,
        "the frontier count over the joint topics matches the dimension table")


def _probe_untapped(page, text: str) -> None:
    ctx = views_collab._bundle()["ctx"]
    subs = views_collab._subs(TREE, BASIS)
    res = collab_data.untapped(ctx, subs, A_ID, B_ID)
    check(copy.COLLAB["UNTAPPED_CAPTION"].format(k=views_collab._pct(res["k"])) in text,
          "the untapped caption renders CD's own rate k")
    check(copy.COLLAB["UNTAPPED_RATE_NOTE"].format(
        window=views_collab._window(collab_data.PULSE_YEARS)) in text,
        "the untapped caption names the window the rate is measured over")
    check(not res["topics"].empty and len(res["topics"]) <= 20,
          f"the untapped frame is non-empty and capped ({len(res['topics'])} rows)")


def _probe_links(page, names: dict) -> None:
    hrefs = _hrefs(page)
    check(links.works_url(A_ID) in hrefs, "section four links A's own publications")
    check(links.works_url(B_ID) in hrefs, "section four links B's own publications")
    copub = links.copubs_url(A_ID, B_ID)
    check(copub in hrefs, "section four links the pair's co-publications")
    want = f"authorships.institutions.id:{A_ID},authorships.institutions.id:{B_ID}"
    check(want in copub, "co-publication link uses the comma-joined repeated filter (A7)")
    check("+" not in copub.split("filter=")[-1].split("&")[0],
          "co-publication link does NOT use the forbidden `+` form (A7)")


def _probe_page(page) -> None:
    _load(page)
    names = _names()
    text = _text(page)
    n = page.locator('[data-testid="stDataFrame"]').count()
    check(n == N_TABLES, f"the eight 2B-R-10 tables render ({n} found)")
    header = _container_text(page, "collab_header")
    check(names[A_ID] in header, "header strip names institution A")
    check(names[B_ID] in header, "header strip names institution B")

    pulse_row = _probe_pulse(page, text, names)
    _probe_joint(page, text, pulse_row)
    _probe_untapped(page, text)
    _probe_links(page, names)

    code = page.evaluate(
        "Array.from(document.querySelectorAll('[data-testid=\"stCode\"]'))"
        ".map(e => e.textContent).join('|')")
    check(f"?pair={A_ID},{B_ID}" in code, "the page prints the pair deep link it was opened with")
    check(str(views_collab.BREADTH_MIN_FULL) in text,
          "the breadth caption still states the publication floor the page passes")
    for key in ("pair_a", "pair_b", "pair_swap", "tree", "basis"):
        check(page.locator(f".st-key-{key}").count() > 0, f"widget `{key}` renders")


def _probe_below_floor(page) -> None:
    """A REAL sub-floor pair: topline + honest notice + link-outs, and no
    invented topic detail."""
    _load(page, A_ID, SUB_B_ID)
    text = _text(page)
    ctx = views_collab._bundle()["ctx"]
    p = collab_data.pulse(ctx, A_ID, SUB_B_ID)
    check(p is not None and p["copubs_total"] < collab_data.PAIR_TOPICS_FLOOR,
          f"the probe's sub-floor pair really is under the floor ({p['copubs_total']} joint works)")
    notice = copy.COLLAB["TOPIC_BELOW_FLOOR_NOTICE"].format(
        n_copubs=views_collab._count(p["copubs_total"]), floor=collab_data.PAIR_TOPICS_FLOOR)
    check(notice in text, "the below-floor pair renders the honest notice with its own numbers")
    check(copy.COLLAB["JOINT_INTRO"].split("{")[0].strip() not in text,
          "no joint-corpus tables are described for a below-floor pair")
    n = page.locator('[data-testid="stDataFrame"]').count()
    check(n == N_TABLES_BELOW_FLOOR,
          f"the three joint-corpus tables are absent below the floor ({n} tables)")
    check(page.locator(".st-key-fig_pulse").count() > 0,
          "the topline pulse still renders below the floor")
    check(views_collab._count(p["copubs_total"]) in text,
          "the joint total is still shown below the floor")
    check(links.copubs_url(A_ID, SUB_B_ID) in _hrefs(page),
          "the co-publication link still works below the floor")


def _probe_download(page) -> None:
    """The untapped CSV, taken through the page's real download button, checked
    against CD's published frame contract."""
    _load(page)
    with page.expect_download(timeout=60_000) as info:
        page.locator(".st-key-dl_untapped button").first.click()
    rows = list(csv.reader(io.StringIO(Path(info.value.path()).read_text(encoding="utf-8"))))
    check(bool(rows) and rows[0] == UNTAPPED_COLS,
          f"untapped CSV header is the CD contract ({rows[0] if rows else 'no rows'})")
    check(len(rows) > 1, f"untapped CSV carries data rows ({max(len(rows) - 1, 0)})")


def _probe_widths(browser) -> None:
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    for width in WIDTHS:
        page = browser.new_page(viewport={"width": width, "height": TALL_SHOT_PX if width >= 1280 else SHOT_HEIGHT_PX})
        _load(page)
        scroll = page.evaluate("document.documentElement.scrollWidth")
        inner = page.evaluate("window.innerWidth")
        check(scroll <= inner + 2,
              f"{width} px: scrollWidth {scroll} <= innerWidth+2 {inner + 2}")
        path = SHOT_DIR / f"lp_collab_{width}.png"
        page.screenshot(path=str(path), full_page=True)
        print("Saved screenshot:", path)
        check(path.is_file(), f"{width} px: screenshot written")
        page.close()


def _recompute_check() -> None:
    """Server-side, after the browser is gone: the topic-overlap identity the
    (now nested) shared table's caption asserts -- summing the smaller of the
    two shares over every shared topic IS the engine's own L3 lens score."""
    from lib.engine import rank_all

    ctx = views_collab._bundle()["ctx"]
    subs = views_collab._subs(TREE, BASIS)
    page_score = float(views_collab._shared_frame(A_ID, B_ID, TREE, BASIS)["min_share"].sum())
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
            _probe_below_floor(page)
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

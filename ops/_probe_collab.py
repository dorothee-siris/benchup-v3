"""
Acceptance probe for the Collaborate page (BUILD_PLAN_2BR2.md stream LP3,
decision 2B-R2-11). Same shape as ops/_probe_find.py: start `streamlit run
pages/3_<handshake>_Collaborate.py` as a subprocess, drive it headless with
Playwright, ALWAYS terminate the server.

WHAT THIS PROBE IS FOR. Every number the page prints is READ BACK OUT OF THE
RENDERED DOM and compared with a fresh `lib/collab_data.py` recompute of the
SAME pair: the joint total, both joint shares and their denominators, both ranks
IN THEIR TWO DIRECTIONS, the field chart's own bar values and row labels, every
cell of the field table, the topic table's impact pairs, its arrows and its
per-row links, the goal and panel lines and the untapped rate. A caption or a
cell that silently stops matching its own frame fails here.

2B-R2-11 made that possible for the tables too: they are hand-built HTML now
(`data-table` / `data-row` / `data-domain` / `data-arrow`), not canvas grids, so
the probe reads what a reader sees instead of inferring it from a CSV.

Selectors are locale-independent -- the `st-key-<key>` classes the page's own
keyed widgets and containers emit, the `data-*` hooks the tables carry, and
`[data-testid=...]`.

TWO PAIRS ARE DRIVEN:
  * Universite de Strasbourg x CNRS -- the manager-verified anchor (CNRS is
    Strasbourg's FIRST partner, Strasbourg is CNRS's SIXTEENTH: the rank
    direction this page has to render the right way round);
  * Universite de Strasbourg x Bavarian Academy of Sciences and Humanities -- a
    REAL sub-floor pair (2 joint works, under the floor of five the pair tables
    now ship with), which must render the shared honest notice, no field or
    topic breakdown, and still every link-out.

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

from lib import charts, collab_data, copy, links, palette, views_collab  # noqa: E402
from lib.app_config import CFG  # noqa: E402
from lib.collab_data import FIELD_BREAKDOWN_COLS, JOINT_TOPICS_COLS, UNTAPPED_COLS  # noqa: E402

PAGE = "pages/3_\U0001F91D_Collaborate.py"
DEFAULT_PORT = 8604
A_ID = "I68947357"        # Universite de Strasbourg
B_ID = "I1294671590"      # CNRS -- Strasbourg's own first partner
SUB_B_ID = "I109144446"   # Bavarian Academy of Sciences and Humanities: 2 joint works
SHOT_DIR = APP_DIR / "tests" / "ui" / "screenshots"
WIDTHS = [1920, 1280, 390]
SHOT_HEIGHT_PX = 2400   # see _probe_widths in ops/_probe_find.py: full_page=True is a no-op
TALL_SHOT_PX = 5600     # match _probe_compare so every section ships in the artifact

TABLES = ("collab_fields", "collab_topics", "collab_untapped", "collab_siblings")
TABLES_BELOW_FLOOR = ("collab_untapped", "collab_siblings")

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
    page.wait_for_selector('[data-table="collab_untapped"]', timeout=240_000)
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


def _container_html(page, key: str) -> str:
    return page.evaluate(
        "(() => { const e = document.querySelector('.st-key-%s');"
        " return e ? e.innerHTML : ''; })()" % key)


def _table_html(page, name: str) -> str:
    return page.evaluate(
        "(() => { const e = document.querySelector('[data-table=\"%s\"]');"
        " return e ? e.outerHTML : ''; })()" % name)


def _rows(page, name: str) -> int:
    return page.locator(f'[data-table="{name}"] tbody tr[data-row]').count()


def _cells(page, name: str, selector: str, attr: str) -> list:
    return page.evaluate(
        "(() => Array.from(document.querySelectorAll('[data-table=\"%s\"] %s'))"
        ".map(e => e.getAttribute('%s')))()" % (name, selector, attr))


def _chip_colours(page, name: str) -> list:
    return page.evaluate(
        "(() => Array.from(document.querySelectorAll('[data-table=\"%s\"] .bu-chip'))"
        ".map(e => e.getAttribute('data-domain') + '|' + getComputedStyle(e).backgroundColor))()"
        % name)


def _hrefs(page) -> list:
    return page.evaluate(
        "Array.from(document.querySelectorAll('a[href]')).map(a => a.getAttribute('href'))")


def _titles(page) -> str:
    return page.evaluate(
        "Array.from(document.querySelectorAll('[title]')).map(e => e.getAttribute('title')).join(' | ')")


def _rgb(hex_colour: str) -> str:
    h = hex_colour.lstrip("#")
    return "rgb(%d, %d, %d)" % tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _plain(template: str) -> str:
    return template.replace("**", "")


def _matches_template(rendered: str, template: str) -> bool:
    """The rendered sentence is this copy template with its placeholders
    filled: the template becomes a regex, `{placeholder}` becomes `.*`."""
    pattern = "".join(".*" if part.startswith("{") else re.escape(part)
                      for part in re.split(r"(\{[^{}]*\})", template) if part)
    return re.fullmatch(pattern, _plain(rendered)) is not None


# The pulse line answers a DATA question in neutral vocabulary. These are the
# words a reader must never find there.
JUDGEMENT_WORDS = ("dying", "healthy", "weak", "strong", "poor", "disappoint",
                   "failing", "vibrant", "thriving")


def _ctx():
    return views_collab._bundle()["ctx"]


def _names() -> dict:
    ctx = _ctx()
    return {i: str(ctx["index_by_id"].loc[i, "display_name"]) for i in (A_ID, B_ID, SUB_B_ID)}


# ---------------------------------------------------------- the anchor pair --

def _probe_pulse(page, text: str, names: dict) -> dict:
    """Section one, read back against a fresh `collab_data.pulse` recompute."""
    p = collab_data.pulse(_ctx(), A_ID, B_ID)

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


def _probe_fields(page, text: str) -> None:
    """Section two (2B-R2-11a): the NEW field-breakdown chart and the table
    under it, both read back against `collab_data.field_breakdown`."""
    fields = collab_data.field_breakdown(_ctx(), A_ID, B_ID)
    check(not fields.empty, f"the pair x field frame is non-empty ({len(fields)} fields)")

    check(page.locator(".st-key-fig_fields").count() > 0, "the field breakdown chart renders")
    chart_text = _container_text(page, "fig_fields")
    top = fields.iloc[0]
    check(str(top["field_name"]) in chart_text,
          f"the chart's row labels carry the largest field ({top['field_name']})")
    check(charts._fmt_vol(float(top["vol_total"])) in chart_text,
          f"the chart writes the largest field's own value ({top['vol_total']})")
    second = fields.iloc[1]
    check(charts._fmt_vol(float(second["vol_total"])) in chart_text,
          f"the chart writes the second field's own value ({second['vol_total']})")
    check(copy.COLLAB["PULSE_AXIS"] in chart_text, "the chart's value axis is titled")

    chart_html = _container_html(page, "fig_fields")
    wanted = {palette.domain_color(d) for d in fields["domain_id"]}
    seen = {c for c in wanted
            if c.lower() in chart_html.lower() or _rgb(c) in chart_html}
    check(seen == wanted,
          f"every domain colour reaches the chart's row labels ({len(seen)} of {len(wanted)})")
    inst = {c for c in palette.INSTITUTION_COLORS
            if c.lower() in chart_html.lower() or _rgb(c) in chart_html}
    check(not inst, "no institution hue is drawn in the pair's own chart")

    markup = _table_html(page, "collab_fields")
    check(bool(markup), "the field table renders as readable markup")
    check(_rows(page, "collab_fields") == len(fields),
          f"the field table shows every field ({_rows(page, 'collab_fields')} of {len(fields)})")
    domains = [d for d in _cells(page, "collab_fields", ".bu-chip", "data-domain")]
    check(domains == [str(int(d)) for d in fields["domain_id"]],
          "each field row carries its own domain chip, in the frame's order")
    colours = _chip_colours(page, "collab_fields")
    want_colours = [f"{int(d)}|{_rgb(palette.domain_color(d))}" for d in fields["domain_id"]]
    check(colours == want_colours, "every chip is painted the OpenAlex domain's own colour")

    check(copy.COLLAB["COL_TOP10_VALUE"].format(
        n_top10=views_collab._count(top["n_top10"]),
        n_covered=views_collab._count(top["n_covered"])) in markup,
        f"the impact pair reads x of y covered ({top['n_top10']} of {top['n_covered']})")
    check(views_collab._count(top["mean_citations"]) in markup,
          f"mean citations is shown at field level ({top['mean_citations']})")
    arrows = set(_cells(page, "collab_fields", ".bu-arrow", "data-arrow"))
    check(arrows == set(fields["arrow"]), f"the field arrows are the frame's own ({sorted(arrows)})")

    hrefs = _hrefs(page)
    missing = [u for u in fields["url"] if u not in hrefs]
    check(not missing, f"every field row links its own co-publications ({len(missing)} missing)")
    url = str(top["url"])
    check(f"authorships.institutions.id:{A_ID},authorships.institutions.id:{B_ID}" in url,
          "a field link ANDs both institutions with the repeated filter key")
    check(f"{links.TAXON_FILTER_KEY['field']}:{int(top['field_id'])}" in url,
          "a field link carries the field filter")
    check("+" not in url.split("filter=")[-1], "a field link does NOT use the forbidden `+` form")

    check(copy.COLLAB["FIELDS_CHART_READING"] in text, "the chart's one reading line is visible")
    titles = _titles(page)
    check(copy.COLLAB["FIELDS_CHART_TOOLTIP"].split(".")[0] in titles,
          "the chart's method sits behind a mark, not in a grey wall of text")
    check(copy.FWCI_NOT_AVAILABLE_LINE.split(":")[0] in titles,
          "the impact columns are introduced with the missing-normalised-score line")
    check(copy.COLLAB["COL_TOP10_HELP"].split(".")[0] in titles,
          "the covered-works convention is on the impact column itself")


def _probe_topics(page, text: str, pulse_row: dict) -> None:
    """Section three: the shared-topic table, its chips, arrows, links and the
    slider that cuts it."""
    ctx = _ctx()
    subs = views_collab._subs(TREE, BASIS)
    prof = collab_data.joint_profile(ctx, subs, A_ID, B_ID)
    topics = prof["topics"]
    check(len(topics) == collab_data.PAIR_TOPICS_TOP_N,
          f"the pair ships the full topic cap ({len(topics)})")

    shown = _rows(page, "collab_topics")
    check(shown == views_collab.ROWS_DEFAULT,
          f"the topic table opens on its default depth ({shown} rows)")
    markup = _table_html(page, "collab_topics")
    top = topics.iloc[0]
    check(str(top["topic_name"]) in markup, f"the largest shared topic is listed ({top['topic_name']})")
    check(copy.COLLAB["COL_TOP10_VALUE"].format(
        n_top10=views_collab._count(top["n_top10"]),
        n_covered=views_collab._count(top["n_covered"])) in markup,
        "a topic row carries its own x of y covered pair")
    domains = _cells(page, "collab_topics", ".bu-chip", "data-domain")
    check(len(domains) == 2 * shown, "topic AND subfield names both carry a chip")
    arrows = _cells(page, "collab_topics", ".bu-arrow", "data-arrow")
    check(arrows == list(topics.head(shown)["arrow"]),
          "every topic row carries the frame's own direction arrow")
    check(len(set(arrows)) > 1, "the arrows really vary row to row (not one constant glyph)")

    hrefs = _hrefs(page)
    missing = [u for u in topics.head(shown)["url"] if u not in hrefs]
    check(not missing, f"every shown topic row links its own co-publications ({len(missing)} missing)")
    url = str(top["url"])
    check(f"{links.TAXON_FILTER_KEY['topic']}:{top['topic_id']}" in url,
          "a topic link carries the topic filter")
    check(f"authorships.institutions.id:{A_ID},authorships.institutions.id:{B_ID}" in url,
          "a topic link ANDs both institutions with the repeated filter key")

    vol = float(topics.head(shown)["vol_total"].sum())
    tagged = int(topics.head(shown)["sdg_tagged_n"].sum())
    check(copy.COLLAB["JOINT_SDG_LINE"].format(
        n_tagged=views_collab._count(tagged), n_shown=views_collab._count(vol),
        share=views_collab._pct(tagged / vol)) in text,
        "the goal line counts the topics actually shown")
    erc = prof["erc"]
    line = _plain(copy.COLLAB["JOINT_ERC_LINE"].format(
        panel=views_collab._erc_panel_label(ctx, erc["panel_idx"]),
        n_panel=views_collab._count(erc["panel_n"]),
        n_labelled=views_collab._count(erc["labelled_n"]),
        share=views_collab._pct(erc["panel_n"] / erc["labelled_n"])))
    check(line in text, "the panel line divides by the LABELLED count, not the joint total")
    check(copy.COLLAB["JOINT_ERC_CAPTION"].format(
        pct=views_collab._pct(erc["labelled_n"] / pulse_row["copubs_total"])) in text,
        "the panel caption names the labelled denominator as a share of the pair")


def _probe_slider(page) -> None:
    """The slider is the whole reason a hundred-row cap is usable: it must move
    the TABLE. Driven from the keyboard, which is what the widget's own thumb
    listens to (a drag would be pixel arithmetic against a moving layout)."""
    before = _rows(page, "collab_topics")
    # Streamlit 1.61 draws the slider as a visually hidden `input[type=range]`
    # inside its thumb (react-aria): that input is what holds the value and what
    # the keyboard drives, so it is the handle to press, not the painted knob.
    thumb = page.locator('.st-key-topics_n input[type="range"]').first
    check(thumb.count() > 0, "the topic-depth slider renders")
    check(thumb.get_attribute("max") == str(collab_data.PAIR_TOPICS_TOP_N),
          "the slider's top stop is the shipped topic cap")
    thumb.focus()
    thumb.press("ArrowRight")
    page.wait_for_timeout(4000)
    after = _rows(page, "collab_topics")
    check(after == before + views_collab.ROWS_STEP,
          f"one step right shows one step more topics ({before} -> {after})")
    thumb.focus()
    thumb.press("End")
    page.wait_for_timeout(4000)
    full = _rows(page, "collab_topics")
    check(full == collab_data.PAIR_TOPICS_TOP_N,
          f"the slider reaches the shipped cap ({full} rows)")
    check(copy.COLLAB["TABLE_ROWS_NOTE"].format(
        n_shown=views_collab._count(full),
        n_total=views_collab._count(collab_data.PAIR_TOPICS_TOP_N)) in _text(page),
        "the row note counts what is on screen against what is held")


def _probe_untapped(page, text: str) -> None:
    ctx = _ctx()
    subs = views_collab._subs(TREE, BASIS)
    res = collab_data.untapped(ctx, subs, A_ID, B_ID)
    check(copy.COLLAB["UNTAPPED_READING"] in text, "the untapped section states what it lists")
    check(copy.COLLAB["UNTAPPED_CAPTION"].format(k=views_collab._pct(res["k"])) in _titles(page),
          "the untapped formula and its rate sit behind the mark")
    shown = _rows(page, "collab_untapped")
    check(shown == min(views_collab.ROWS_DEFAULT, len(res["topics"])),
          f"the untapped table opens on its default depth ({shown} rows)")
    hrefs = _hrefs(page)
    missing = [u for u in res["topics"].head(shown)["url"] if u not in hrefs]
    check(not missing, f"every untapped row links its own topic ({len(missing)} missing)")
    check(len(_cells(page, "collab_untapped", ".bu-chip", "data-domain")) == 2 * shown,
          "untapped rows carry the same chips as the topic table")
    check(_rows(page, "collab_siblings") == len(res["siblings"]),
          "the adjacent-topic suggestions are kept")


def _probe_deletions(page, text: str, names: dict) -> None:
    """2B-R2-11(f) and 2B-R2-8: the two directional gap tables are GONE, and
    what the page no longer shows is said in plain words."""
    check(not hasattr(collab_data, "gaps"), "the gap frame is deleted from the data module")
    for gone in ("_render_gaps", "_gaps_frame", "_render_breadth", "_render_shared"):
        check(not hasattr(views_collab, gone), f"`{gone}` is deleted from the page module")
    for iid in (A_ID, B_ID):
        check(copy.COLLAB["GAPS_HEADER"].format(a=names[iid]) not in text,
              f"no gap table is rendered for {names[iid]}")
    check(copy.COLLAB["DOWNLOAD_GAPS"] not in text, "no gap list can be downloaded any more")
    check(copy.SHARED["NOT_OFFERED_HEADER"] in text, "the page says what it does not show")
    for key in ("NOT_OFFERED_GAPS", "NOT_OFFERED_BREADTH", "NOT_OFFERED_SUBFIELDS"):
        check(copy.SHARED["NOT_OFFERED_LINE"].format(
            feature=copy.COLLAB[key], reason=copy.COLLAB[f"{key}_REASON"]) in text,
            f"one plain line for {copy.COLLAB[key].lower()}")
    for banned in ("parquet", "artefact", "pipeline", "BUILD_PLAN", "2B-R"):
        check(banned.lower() not in text.lower(), f"no rendered string says '{banned}'")


def _probe_page(page) -> None:
    _load(page)
    names = _names()
    text = _text(page)
    found = [t for t in TABLES if page.locator(f'[data-table="{t}"]').count() > 0]
    check(found == list(TABLES), f"the four tables render ({found})")
    check(page.locator('[data-testid="stDataFrame"]').count() == 0,
          "no canvas grid is left on the page")
    header = _container_text(page, "collab_header")
    check(names[A_ID] in header, "header strip names institution A")
    check(names[B_ID] in header, "header strip names institution B")

    pulse_row = _probe_pulse(page, text, names)
    _probe_fields(page, text)
    _probe_topics(page, text, pulse_row)
    _probe_untapped(page, text)
    _probe_deletions(page, text, names)

    code = page.evaluate(
        "Array.from(document.querySelectorAll('[data-testid=\"stCode\"]'))"
        ".map(e => e.textContent).join('|')")
    check(f"?pair={A_ID},{B_ID}" in code, "the page prints the pair deep link it was opened with")
    for key in ("pair_a", "pair_b", "pair_swap", "tree", "basis", "topics_n", "untapped_n"):
        check(page.locator(f".st-key-{key}").count() > 0, f"widget `{key}` renders")
    _probe_slider(page)


def _probe_below_floor(page) -> None:
    """A REAL sub-floor pair: topline + the shared honest notice + link-outs,
    and no invented topic detail."""
    _load(page, A_ID, SUB_B_ID)
    text = _text(page)
    p = collab_data.pulse(_ctx(), A_ID, SUB_B_ID)
    check(p is not None and p["copubs_total"] < collab_data.PAIR_TOPICS_FLOOR,
          f"the probe's sub-floor pair really is under the floor of "
          f"{collab_data.PAIR_TOPICS_FLOOR} ({p['copubs_total']} joint works)")
    notice = copy.SHARED["BELOW_FLOOR_NOTICE"].format(
        item=copy.COLLAB["BELOW_FLOOR_ITEM"], n=views_collab._count(p["copubs_total"]),
        floor=collab_data.PAIR_TOPICS_FLOOR)
    check(notice in text, "the below-floor pair renders the shared notice with its own numbers")
    found = [t for t in TABLES if page.locator(f'[data-table="{t}"]').count() > 0]
    check(found == list(TABLES_BELOW_FLOOR),
          f"the field and topic breakdowns are absent below the floor ({found})")
    check(copy.COLLAB["TOPICS_HEADER"] not in text,
          "no topic section is announced for a below-floor pair")
    check(page.locator(".st-key-fig_pulse").count() > 0,
          "the topline pulse still renders below the floor")
    check(views_collab._count(p["copubs_total"]) in text,
          "the joint total is still shown below the floor")
    check(links.copubs_url(A_ID, SUB_B_ID) in _hrefs(page),
          "the co-publication link still works below the floor")


def _probe_downloads(page) -> None:
    """The three CSVs, taken through the page's real download buttons, checked
    against the published frame contracts."""
    for key, cols, label in (("dl_fields", FIELD_BREAKDOWN_COLS, "field breakdown"),
                             ("dl_topics", JOINT_TOPICS_COLS, "shared topics"),
                             ("dl_untapped", UNTAPPED_COLS, "untapped topics")):
        # Reloaded before EACH click: a download button reruns the script, so a
        # handle taken before the previous download is a stale node by now.
        _load(page)
        page.locator(f".st-key-{key} button").first.scroll_into_view_if_needed()
        with page.expect_download(timeout=60_000) as info:
            page.locator(f".st-key-{key} button").first.click()
        rows = list(csv.reader(io.StringIO(Path(info.value.path()).read_text(encoding="utf-8"))))
        check(bool(rows) and rows[0] == list(cols),
              f"{label} CSV header is the published contract ({rows[0][:3] if rows else 'no rows'})")
        check(len(rows) > 1, f"{label} CSV carries data rows ({max(len(rows) - 1, 0)})")


def _probe_widths(browser) -> None:
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    for width in WIDTHS:
        page = browser.new_page(viewport={"width": width,
                                          "height": TALL_SHOT_PX if width >= 1280 else SHOT_HEIGHT_PX})
        _load(page)
        scroll = page.evaluate("document.documentElement.scrollWidth")
        inner = page.evaluate("window.innerWidth")
        check(scroll <= inner + 2,
              f"{width} px: scrollWidth {scroll} <= innerWidth+2 {inner + 2}")
        wide = page.evaluate(
            "(() => { const e = document.querySelector('[data-table=\"collab_topics\"]');"
            " return e ? (e.parentElement.scrollWidth >= e.parentElement.clientWidth) : false; })()")
        check(bool(wide) or width >= 1280,
              f"{width} px: the widest table scrolls inside its own box, not the page")
        path = SHOT_DIR / f"lp_collab_{width}.png"
        page.screenshot(path=str(path), full_page=True)
        print("Saved screenshot:", path)
        check(path.is_file(), f"{width} px: screenshot written")
        page.close()


def _recompute_check() -> None:
    """Server-side, after the browser is gone: the topic-overlap identity the
    untapped reading is built on -- summing the smaller of the two shares over
    every shared topic IS the engine's own L3 lens score for the pair."""
    from lib.engine import rank_all

    ctx = _ctx()
    subs = views_collab._subs(TREE, BASIS)
    page_score = float(collab_data.shared_topics(ctx, subs, A_ID, B_ID)["min_share"].sum())
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
            _probe_downloads(page)
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

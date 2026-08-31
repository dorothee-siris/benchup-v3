"""
tests/ui/smoke.py -- Playwright smoke test against the LIVE Streamlit server.

REWRITTEN for Phase 2B-R3 (BUILD_PLAN_2BR3.md, stream TEV-U, wave 3) against the
new selection architecture merged this phase: ONE shared sidebar search +
basket (`lib.selection.render_sidebar`, called on every page) feeding
basket-only "slots" on Compare (3, `state.COMPARE_CAP`) and Collaborate (2,
`state.COLLAB_CAP`); Find keeps ONE dropdown over the basket
(`views_find._seed_pick`) instead of its own free-text search. Compare and
Collaborate were both reworked around this (VC/VL): Compare is now title ->
slots -> KPI cards -> Coverage -> Subject/ERC/SDG -> the two frontier charts
-> Impact -> a collapsed "About these figures" meta block; Collaborate is
title -> slots -> identity cards + a pair MOMENTUM headline -> the pulse ->
a domain-coloured field CHART (the old field TABLE is gone) -> a new
"Strategic reciprocity by field" bubble scatter -> a native, sortable
`st.dataframe` topic deep-dive (20 rows + "Show all", no slider) -> untapped
potential (same 20-then-show-all pattern) -> a collapsed meta block. The old
per-view "add a comparator" flows, the Compare hand-off button, the old
Collaborate field table + row sliders + "Read the publications on OpenAlex"
section, "Trends in the N subfields", and the light pastel institution trio
are all DELETED this round and are asserted ABSENT below, not merely
untested.

Cross-page persistence is still a load-bearing claim: the basket (a plain,
non-widget session_state list) and every keyed widget (persist_state="session")
must survive real Menu<->Find<->Compare<->Collaborate<->Methods navigation.
Navigation uses the app's OWN sidebar nav link
(`[data-testid="stSidebarNav"] a`) for every page hop -- NEVER `page.goto()`
for a persistence check (a `goto` tears down and recreates the browser's own
WebSocket session, which silently resets exactly the state a persistence
check exists to catch). `goto` IS used for the very first page load and for
every deliberately-standalone, fresh-session check below (the Ifremer crash
seed, the Compare/Collaborate deep-link checks, the below-floor pair) --
each of those asserts NO persistence claim.

All selectors are locale-independent: `.st-key-<key>` classes from the app's
own keyed widgets/containers, `[role=...]`, `[data-testid=...]`. Text is read
via `textContent` (never `innerText`, empty for an inactive tab panel or a
collapsed expander body even though its DOM nodes exist) and only to ASSERT
content, never to locate an element. `st.dataframe` renders a canvas grid
with no real text nodes for cell values (DOM FACT 1 below) -- row-level facts
for the topic/untapped tables are read from the "Show all" button's own
before/after behaviour and from CD4's own pytest suite, never from canvas
cell text; the siblings table alone stays hand-built HTML
(`[data-table="collab_siblings"]`, DOM FACT 2) with real per-cell nodes.

Usage:
    python tests/ui/smoke.py --port 8611

Exit 0 iff every check passes, 1 otherwise. Prints one PASS/FAIL line per
check. Stdout is ASCII-only (cp1252 console).
"""
from __future__ import annotations

import argparse
import io
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

import openpyxl
from playwright.sync_api import TimeoutError as PWTimeoutError
from playwright.sync_api import sync_playwright

# Windows consoles default to cp1252, on which a bare print() of "Gdańsk"
# raises UnicodeEncodeError and aborts the journey mid-flight (inspection
# I-2, carried forward every round since).
for _stream in (sys.stdout, sys.stderr):
    if getattr(_stream, "encoding", "").lower() not in ("utf-8", "utf8"):
        _stream.reconfigure(encoding="utf-8")

DEFAULT_APP_DIR = Path(__file__).resolve().parents[2]  # tests/ui/smoke.py -> app/
WIDTHS = [1920, 1280, 390]
ACTION_TIMEOUT_MS = 30_000     # time-box every wait so a hang FAILS, never blocks

SEP = "\N{MIDDLE DOT}"  # matches lib/copy.py's own separator

# --------------------------------------------------------- reference ids ----
# Real institution ids/queries, chosen for stability across a live re-run
# (no golden numeric value is pinned on any of them here -- TEV-D owns that).
GDANSK_QUERY = "gdansk"
GDANSK_NAME_FRAGMENT = "Gda"
SORBONNE_QUERY = "Sorbonne"
BOLOGNA_QUERY = "Bologna"
CRASH_SEED = "I154202486"        # Ifremer -- umbrella AND type-corrected
STRASBOURG_ID = "I68947357"      # Universite de Strasbourg
CNRS_ID = "I1294671590"          # CNRS -- Strasbourg's own first partner
GDANSK_ID = "I40413290"          # University of Gdansk
IFPEN_ID = "I265217849"          # IFP Energies nouvelles
# smoke.py's own standalone Compare check uses a LIGHTER trio than probe.py's
# (Strasbourg 19.4K + Gdansk 8.8K + IFPEN 1.1K works vs CNRS's 239K alone) --
# measured: a real xlsx workbook for a CNRS-sized trio genuinely took long
# enough in THIS file's own live run (a Streamlit server already warmed
# through 190+ prior checks) to make the standalone check unreliable at any
# sane timeout; probe.py's `_probe_compare` already proves the CNRS-scale
# case works (twice, ~80s each, its own isolated server) -- no need to
# re-pay that cost here too.
COMPARE_TRIO = (STRASBOURG_ID, GDANSK_ID, IFPEN_ID)
BELOW_FLOOR_A_ID = STRASBOURG_ID
BELOW_FLOOR_B_ID = "I109144446"  # Bavarian Academy of Sciences and Humanities
# Nine more distinct, real, simple ASCII names for the sidebar basket-cap
# fill (checked via a real search+add loop -- a `?compare=`/`?pair=` deep
# link CANNOT pre-fill the basket past its own view's slot count: `lib.
# selection.resolve_slot_hydration` trims the param to `n` BEFORE folding
# into the basket, so Compare's own link folds at most 3, never 9).
BASKET_FILL_QUERIES = ("University of Oxford", "University of Cambridge",
                       "Imperial College London", "University College London",
                       "Heidelberg University", "University of Copenhagen",
                       "King's College London", "KU Leuven", "Sapienza")

# 2B-R-11a renumbers the DISPLAY codes but the SHOWN-LENS COUNT is unchanged:
# 8 defaults (L0..L7) + Overview + Aspirational = 10; + L7(optional, ->L9) =
# 11; + C1(optional, ->L8) too = 12.
GDANSK_TAB_COUNT = 10
L7_ON_TAB_COUNT = 11
BOTH_OPTIONAL_TAB_COUNT = 12

SUBFIELDS_TOP_N = 30
TOPICS_TOP_N = 30

N_CARDS = 6
CARD_LABELS = ["Publications", "SDG-tagged share", "Frontier top-quartile share",
              "PP(top10%)", "International co-publications", "Industrial co-publications"]
IDENTITY_TYPE_CORRECTED_RE = re.compile(r"[A-Za-z_]+\*\s*\(was:\s*[A-Za-z_]+\)")
NO_LONGER_ON_FIND = "What counts as a publication"

# 2BR3: forbidden vocabulary a strategy officer must never meet. Extended
# this round with "pastel" and the "2B-R3"/"2BR3" stream-name family
# (TEV-U acceptance) -- kept as a short, HARDCODED list here (never
# re-imported from tests/test_forbidden_vocabulary.py's own list) so a
# rename of that test's list cannot silently widen what this file accepts.
FORBIDDEN_VOCAB = ("2B-R", "BUILD_PLAN", "artefact", "pipeline", "parquet", "pastel")
FORBIDDEN_CODES_RE = re.compile(r"\b(2BR3|MU3|CP3|LP3|VS3|FA3|CD3|WT2?|P[1-7]|G2|H2|I2|SEL|VC|VL|TEV-U|TEV-D)\b")

# 2BR3 PAL: the retired light pastel institution trio must never render
# anywhere -- neither as page text (it never was) nor in any inline `style=`
# colour this file's own page.content() can see.
PASTEL_HEXES = ("#FF8BA6", "#B4BF07", "#8EB3FF")
# The new navy trio (slot 1 = darkest) -- used to prove the KPI cards / chip
# legends actually paint by SLOT POSITION, not by internal institution key.
NAVY_HEXES = ("#192C41", "#5A6883", "#B5C0D4")

SUBJECT_METRIC_LABELS = ["Share", "Specialisation", "PP(top10%)", "SDG-tagged share",
                         "Change in mean annual volume"]
VOL_TOP10_LABEL = "Publications in the world top decile"
VOLUME_LABEL = "Volume"
SORT_TAXONOMY_LABEL = "By subject area"
SORT_VALUE_LABEL = "Largest first"
POOL_VOLUME_LABEL = "Most published by this set"
POOL_ELITE_LABEL = "The most emerging topics only"
COLOR_OWNER_LABEL = "Who holds the topic"
COLOR_DOMAIN_LABEL = "Broad subject area"
LEGEND_SHARED_TEXT = "held by more than one"
LOW_VOLUME_GLYPH = "\N{DAGGER}"
NOT_OFFERED_HEADER = "Not shown here, and why"

PANEL_LABELS = [
    ("fields", "Fields"),
    ("subfields", f"Top {SUBFIELDS_TOP_N} subfields"),
    ("topics", "Top topics"),
    ("frontier", "Frontier positioning"),
    ("sdg", "SDG profile"),
    ("erc", "ERC profile"),
]

TREE_LABEL_BESTFIT = "Repaired taxonomy (best fit, default)"
TREE_LABEL_ORIGINAL = "OpenAlex taxonomy as published"
BASIS_LABEL_FRAC = "Fractional counting"
STRIP_TREE_ORIGINAL = f"taxonomy: {TREE_LABEL_ORIGINAL}"

LENS_GUIDE_HEADER = "How to read the lenses"
LENS0_TAB_CODE = "L0"
LENS0_FULL_NAME = f"L0 {SEP} Field overlap"
LENS_LEGEND_SUBSTR = "see the lens guide above"
L2F_TAB_CODE = "L4"
L2F_DISPLAY_NAME = f"L4 {SEP} Shared specialisations"

FRONTIER_MODE_TOP_IDX, FRONTIER_MODE_EMERGING_IDX = 0, 1
BREAKDOWN_DOMAIN_IDX, BREAKDOWN_DOCTYPE_IDX = 0, 1
BONUS_YEAR_AXIS_LABEL = "2025*"

DATA_CAPTION_RE = re.compile(
    r"[\d,]+\s+institutions\s+" + re.escape(SEP) + r"\s+data from\s+[A-Za-z]+\s+\d{1,2},\s+\d{4}")

METHODS_MIN_SECTIONS = 14
LENS_CODES_TITLE = "Reading the lens codes"
PLACEHOLDER_RE = re.compile(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}")

NAV_CARD_LABELS = ["Find peers", "Compare", "Collaborate", "How it is built"]
NAV_COMPARE, NAV_COLLAB, NAV_METHODS = "Compare", "Collaborate", "Methods"

# 2BR3: cap-3 truncation prose is GONE (slots either hold a basket pick or
# they don't) -- the old CAP_TRUNCATED_SUBSTR constant is retired with it.
COMPARE_MIN_FIGURES = 7   # subject/erc/sdg/frontier-map/shared-frontier/impact-index/impact-subfields
BASKET_CAP = 10           # state.BASKET_CAP (2BR3 SEL ruling 1, was 6)
COMPARE_CAP = 3           # state.COMPARE_CAP
COLLAB_CAP = 2            # state.COLLAB_CAP

XLSX_METHODS_SHEET = "Methods"
XLSX_SHEET_COUNT = 9      # Methods + 8 view sheets (2BR3: Trends dropped, Coverage kept)

# 2BR3 Compare section order (hardcoded literals, never re-imported from
# copy.py -- see the non-vacuity note at the smoke suite's original design).
COMPARE_SECTION_ORDER = [
    "Key figures, side by side", "Coverage", "Subject profile", "ERC panels",
    "SDG profile", "The frontier, pooled", "Who holds the shared frontier",
    "Impact", "About these figures",
]
# 2BR3 deletions this page must never render again.
COMPARE_DELETED_STRINGS = ("Trends in the", "Take one pair further")

# 2BR3 Collaborate section order.
COLLAB_SECTION_ORDER = [
    "The relationship, year by year", "The joint corpus, field by field",
    "Strategic reciprocity by field", "The topics the two publish on together",
    "Where the two overlap without publishing together", "About these figures",
]
COLLAB_DELETED_STRINGS = ("Read the publications on OpenAlex", "does not publish in")

PAIR_FLOOR = 5
BELOW_FLOOR_NOTICE_RE = re.compile(
    r"This pair holds \d+ publications, under the " + str(PAIR_FLOOR)
    + r" a breakdown needs to stay readable")

RESULTS: list[tuple[bool, str]] = []
FINDINGS: list[str] = []
PORT = 8611
BASE_URL = "http://127.0.0.1:8611"


def check(ok: bool, message: str) -> bool:
    RESULTS.append((bool(ok), message))
    print(("PASS: " if ok else "FAIL: ") + message)
    return bool(ok)


def finding(message: str) -> None:
    """A real, reproduced behaviour that is NOT this stream's to fix (outside
    the TEV-U fence) -- printed distinctly and collected for the manager's
    JSON report, on top of (never instead of) a normal `check()` line so the
    exit code still reflects it."""
    FINDINGS.append(message)
    print("FINDING: " + message)


def fail_section(name: str, exc: Exception) -> None:
    check(False, f"{name}: raised {type(exc).__name__}: {exc}")


# ------------------------------------------------------------- server -------

def _wait_for_port(port: int, timeout: float = 60.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.5)
    return False


def _start_server(app_dir: Path, port: int) -> subprocess.Popen:
    # DEVNULL, not PIPE: every rerun logs a deprecation per st.dataframe call,
    # which fills an unread pipe buffer and blocks the server mid-probe.
    return subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "Menu.py",
         "--server.headless", "true", "--server.port", str(port),
         "--browser.gatherUsageStats", "false"],
        cwd=str(app_dir), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)


def _stop_server(server: subprocess.Popen) -> None:
    server.terminate()
    try:
        server.wait(timeout=10)
    except subprocess.TimeoutExpired:
        server.kill()
        server.wait(timeout=10)


# --------------------------------------------------------- DOM helpers ------

def _settle(page, ms: int = 2500) -> None:
    page.wait_for_timeout(ms)


def _wait_for(page, predicate, timeout_ms: int = 15_000, interval_ms: int = 300) -> bool:
    deadline = time.time() + timeout_ms / 1000
    while time.time() < deadline:
        if predicate():
            return True
        page.wait_for_timeout(interval_ms)
    return False


def _all_text(page, selector: str) -> str:
    return page.evaluate(
        "(sel) => Array.from(document.querySelectorAll(sel)).map(e => e.textContent).join('|')",
        selector)


def _full_page_text(page) -> str:
    return page.evaluate("document.body.textContent") or ""


def _no_exception(page, label: str) -> bool:
    return check(page.locator('[data-testid="stException"]').count() == 0,
                 f"{label}: no Streamlit exception on the page")


def _open_select(page, key: str) -> None:
    loc = page.locator(f".st-key-{key} [data-baseweb='select']")
    if loc.count() == 0:
        loc = page.locator(f".st-key-{key}")
    loc.first.click(timeout=ACTION_TIMEOUT_MS)
    try:
        page.wait_for_selector('[role="option"]', timeout=3000)
    except PWTimeoutError:
        page.keyboard.press("ArrowDown")
        page.wait_for_selector('[role="option"]', timeout=ACTION_TIMEOUT_MS)


def _pick_option(page, text: str | None = None) -> None:
    opts = page.locator('[role="option"]')
    target = opts.filter(has_text=text).first if text else opts.first
    target.click(timeout=ACTION_TIMEOUT_MS)


def _selectbox_value(page, key: str) -> str:
    return page.locator(f".st-key-{key} input").first.input_value()


def _ensure_sidebar_open(page) -> None:
    ctrl = page.locator('[data-testid="stSidebarCollapsedControl"] button, '
                         '[data-testid="stSidebarCollapsedControl"]')
    if ctrl.count() and ctrl.first.is_visible():
        ctrl.first.click(timeout=ACTION_TIMEOUT_MS)
        page.wait_for_timeout(500)


def _ensure_expander_open(page, key: str, probe_selector: str) -> None:
    probe = page.locator(probe_selector).first
    if probe.count() == 0 or not probe.is_visible():
        page.locator(f".st-key-{key} summary").first.click(timeout=ACTION_TIMEOUT_MS)
        page.wait_for_timeout(700)


def _ensure_expander_open_by_text(page, text: str, probe_selector: str) -> None:
    probe = page.locator(probe_selector).first
    if probe.count() == 0 or not probe.is_visible():
        page.locator("summary").filter(has_text=text).first.click(timeout=ACTION_TIMEOUT_MS)
        page.wait_for_timeout(700)


def _click_nav(page, label: str) -> None:
    """Real in-app sidebar nav-link click -- the ONLY way this file changes
    page for a persistence check."""
    _ensure_sidebar_open(page)
    link = page.locator('[data-testid="stSidebarNav"] a').filter(has_text=label).first
    link.wait_for(state="visible", timeout=ACTION_TIMEOUT_MS)
    try:
        link.click(timeout=ACTION_TIMEOUT_MS)
    except Exception:
        link.evaluate("el => el.click()")
    _settle(page, 3000)


def _plotly_point_count(page, selector: str) -> int:
    return page.evaluate(
        "(sel) => { const el = document.querySelector(sel); if (!el || !el.data) return -1;"
        " return el.data.reduce((a, t) => a + ((t.x && t.x.length) || 0), 0); }",
        selector)


def _fig_xy_text(page, selector: str) -> dict:
    return page.evaluate(
        "(sel) => { const el = document.querySelector(sel); if (!el || !el.data) return null;"
        " return el.data.map(t => ({x: t.x || [], y: t.y || [], text: t.text || [],"
        " customdata: t.customdata || [], hovertemplate: t.hovertemplate || ''})); }",
        selector)


def _fig_layout(page, selector: str) -> dict:
    return page.evaluate(
        "(sel) => { const el = document.querySelector(sel); if (!el || !el.layout) return null;"
        " const l = el.layout;"
        " return {shapes_n: (l.shapes || []).length,"
        " scaleanchor_y: (l.yaxis || {}).scaleanchor || null,"
        " xrange: (l.xaxis || {}).range || null, yrange: (l.yaxis || {}).range || null}; }",
        selector)


def _hrefs(page) -> list:
    return page.evaluate(
        "Array.from(document.querySelectorAll('a[href]')).map(a => a.getAttribute('href'))")


def _no_forbidden_vocab(page, label: str) -> None:
    """No plan code, build artefact, pipeline/table name, stream code or
    pastel-trio reference anywhere the page renders -- text, tooltips
    (`title=`) and captions alike."""
    text = (_full_page_text(page) + "|"
            + page.evaluate("Array.from(document.querySelectorAll('[title]'))"
                            ".map(e => e.getAttribute('title')).join('|')"))
    low = text.lower()
    hits = [w for w in FORBIDDEN_VOCAB if w.lower() in low]
    check(not hits, f"{label}: no forbidden-vocabulary term renders ({hits})")
    code_hit = FORBIDDEN_CODES_RE.search(text)
    check(code_hit is None,
          f"{label}: no stream code renders on the page (found {code_hit.group(1) if code_hit else None!r})")


def _no_pastel_hexes(page, label: str) -> None:
    """2BR3 PAL: the retired light pastel trio must be greppable NOWHERE in
    the page's own source -- not just absent from visible text, since a stray
    inline `style="color:#FF8BA6"` would never show up as rendered text."""
    source = page.content()
    hits = [h for h in PASTEL_HEXES if h.lower() in source.lower()]
    check(not hits, f"{label}: no retired pastel hex renders anywhere in page source ({hits})")


def _no_bare_na_in_hover(page, selectors: list[str], label: str) -> None:
    """2BR3 CD4: every hover must carry a NUMERIC denominator (`denom_value`),
    never the bare uppercase string 'NA' (the app's own null mark is the
    lowercase 'n/a', `palette.NA_MARK` -- a literal 'NA' would be a real
    regression, not this mark). Checked on each figure's own `customdata` /
    `hovertemplate`, not on page text (a false 'NA' hit inside an unrelated
    English word like 'Denmark' is not a bug)."""
    hits = []
    for sel in selectors:
        data = _fig_xy_text(page, sel)
        if not data:
            continue
        for tr in data:
            blob = " ".join(str(v) for v in tr.get("customdata", [])) + " " + str(tr.get("hovertemplate", ""))
            if re.search(r"\bNA\b", blob):
                hits.append((sel, blob[:120]))
    check(not hits, f"{label}: no bare 'NA' string in any sampled hover payload ({hits[:3]})")


def _hex_to_rgb_css(hexcolor: str) -> str:
    h = hexcolor.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgb({r}, {g}, {b})"


# --------------------------------------------------- sidebar search+basket --
# 2BR3 SEL: the ONE shared component every page now calls
# (`selection.render_sidebar`). Search box key "sidebar_search_query"; each
# result row's Add button key is "sidebar_add_<institution_id>" (id unknown
# from the DOM, so results are matched by their own visible label text);
# each basket row's remove button key is "sidebar_rm_<institution_id>"; the
# clear-all button key is "sidebar_basket_clear".

def _sidebar_search(page, query: str) -> None:
    box = page.locator('[data-testid="stSidebar"] .st-key-sidebar_search_query input').first
    box.click(timeout=ACTION_TIMEOUT_MS)
    box.fill(query)
    # Streamlit's st.text_input commits on Enter or on blur -- a bare .fill()
    # dispatches input/change DOM events but leaves focus in the field, so
    # the debounced value never reaches the server without this (measured:
    # search silently no-ops without it, same lesson the OLD seed_query/
    # basket_query flows already encoded via .press("Enter")).
    box.press("Enter")
    _settle(page, 2200)


def _sidebar_result_rows(page):
    return page.locator('[data-testid="stSidebar"] [class*="st-key-sidebar_add_"] button')


def _sidebar_add_matching(page, query: str, text_hint: str | None = None) -> bool:
    """Search for `query`, click a result row's own Add button, and CONFIRM
    the basket actually grew. `text_hint`, when given, is tried first (a row
    whose own caption contains it); every other result row is tried next, in
    order, skipping a disabled button (already in the basket) -- a plain
    `.first.click()` with no verification proved flaky in practice (a stale
    element reference after a reflow, or a hint match landing on an already-
    added row) and this is the robust replacement. Returns False only when
    no result row rendered at all, or the basket never grew after trying
    every row."""
    _sidebar_search(page, query)
    rows = _sidebar_result_rows(page)
    n = rows.count()
    if n == 0:
        return False
    n_before = _sidebar_basket_count(page)
    order = list(range(n))
    if text_hint:
        capt = page.locator('[data-testid="stSidebar"]').get_by_text(text_hint, exact=False)
        if capt.count():
            row = capt.first.locator("xpath=ancestor::div[contains(@data-testid,'stHorizontalBlock')][1]")
            hinted = row.locator("button")
            if hinted.count():
                # Re-resolve its POSITION among `rows` (not a second, separate
                # locator) so the retry loop below never double-clicks it.
                hinted_box = hinted.first.bounding_box()
                for i in range(n):
                    box = rows.nth(i).bounding_box()
                    if box and hinted_box and abs(box["y"] - hinted_box["y"]) < 2:
                        order = [i] + [j for j in order if j != i]
                        break
    for i in order:
        btn = rows.nth(i)
        try:
            if btn.is_disabled():
                continue
            # A SHORT per-attempt timeout: Streamlit's `disabled=` sometimes
            # reaches the DOM as `aria-disabled`/`pointer-events:none` rather
            # than the native `disabled` attribute `.is_disabled()` checks,
            # so a genuinely inert row can still pass that guard -- a stuck
            # click on it must fail FAST and move on, never eat the full
            # 30s budget per candidate row.
            btn.click(timeout=5000)
        except Exception:  # noqa: BLE001 -- unclickable/detached row: try the next
            continue
        # POLL for the basket to grow (bounded, not a blind fixed sleep): a
        # rerun's true cost varies by query (a fresh 10-row search rebuild
        # is not free) -- a fixed settle that is too short makes this loop
        # (wrongly) try a SECOND row while the first click's rerun is still
        # in flight, over-adding two institutions for one intended pick.
        if _wait_for(page, lambda: _sidebar_basket_count(page) > n_before, timeout_ms=6000):
            return True
    return _sidebar_basket_count(page) > n_before


def _sidebar_basket_rows(page):
    return page.locator('[data-testid="stSidebar"] [class*="st-key-sidebar_rm_"]')


def _sidebar_basket_count(page) -> int:
    return _sidebar_basket_rows(page).count()


def _sidebar_remove_first(page) -> None:
    btns = page.locator('[data-testid="stSidebar"] [class*="st-key-sidebar_rm_"] button')
    if btns.count():
        n_before = _sidebar_basket_count(page)
        btns.first.click(timeout=ACTION_TIMEOUT_MS)
        # POLL, not a blind settle -- same lesson as _sidebar_add_matching:
        # a fixed sleep that is shorter than this rerun's real cost reads
        # the basket before the removal has actually landed.
        _wait_for(page, lambda: _sidebar_basket_count(page) < n_before, timeout_ms=6000)


def _sidebar_clear(page) -> None:
    btn = page.locator(".st-key-sidebar_basket_clear button")
    if btn.count():
        btn.first.click(timeout=ACTION_TIMEOUT_MS)
        _wait_for(page, lambda: _sidebar_basket_count(page) == 0, timeout_ms=6000)


def _sidebar_basket_caption(page) -> str:
    return _all_text(page, '[data-testid="stSidebar"] [data-testid="stCaptionContainer"]')


def _sidebar_basket_n(page) -> int | None:
    m = re.search(r"(\d+) of \d+ added", _sidebar_basket_caption(page))
    return int(m.group(1)) if m else None


# --------------------------------------------------------------- slots API --
# 2BR3 SEL: `selection.slots_row(view, n)` -- side-by-side selectboxes keyed
# `slot_<view>_<i>`, options are the current basket + an empty sentinel.

def _slot_value(page, view: str, i: int) -> str:
    return _selectbox_value(page, f"slot_{view}_{i}")


def _slot_options_count(page, view: str, i: int) -> int:
    """Opens slot `i`, counts its own `[role=option]` rows, closes with
    Escape. Used to prove the slots read ONLY the basket (options == basket
    size + the empty sentinel), never the full institution index."""
    _open_select(page, f"slot_{view}_{i}")
    n = page.locator('[role="option"]').count()
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    return n


def _set_slot(page, view: str, i: int, text: str) -> None:
    _open_select(page, f"slot_{view}_{i}")
    _pick_option(page, text)
    _settle(page, 2500)


# ------------------------------------------------------------- sections -----

def check_menu(page) -> None:
    page.goto(BASE_URL, wait_until="domcontentloaded")
    page.wait_for_selector('[data-testid="stSidebarNav"]', state="attached", timeout=ACTION_TIMEOUT_MS)
    _settle(page, 2000)
    check(page.get_by_role("heading").count() >= 1, "Menu: heading present")
    nav = page.locator(".st-key-nav_cards")
    check(nav.count() >= 1, "Menu: .st-key-nav_cards container present")
    cards = nav.locator("[class*='st-key-nav_card_']")
    try:
        cards.first.wait_for(state="visible", timeout=ACTION_TIMEOUT_MS)
    except Exception:  # noqa: BLE001 -- the count check reports the failure
        pass
    check(cards.count() == len(NAV_CARD_LABELS),
          f"Menu: exactly {len(NAV_CARD_LABELS)} nav cards render (found {cards.count()})")
    live_links = nav.locator("a")
    check(live_links.count() == len(NAV_CARD_LABELS),
          f"Menu: all {len(NAV_CARD_LABELS)} cards are live st.page_link anchors "
          f"(found {live_links.count()})")
    for label in NAV_CARD_LABELS:
        check(live_links.filter(has_text=label).count() >= 1,
              f"Menu: a live card links to {label!r}")
    # 2BR3 SEL: Menu.py itself now calls selection.render_sidebar() -- a
    # reader can start shortlisting from the landing page.
    check(page.locator('[data-testid="stSidebar"] .st-key-sidebar_search_query').count() >= 1,
          "Menu (2BR3 SEL): the shared sidebar search renders on the landing page too")
    _no_exception(page, "Menu")


def check_sidebar_search_and_basket(page) -> None:
    """2BR3 SEL ruling 1, the load-bearing new-architecture check: the ONE
    shared sidebar search + basket, driven for real on the Find page --
    empty state, old free-text search inputs gone, add-3/remove-1, the
    basket-cap message on a real blocked 11th add, and Clear basket."""
    _click_nav(page, "Find")
    _settle(page, 1500)

    # --- old per-view search inputs are GONE -------------------------------
    check(page.locator(".st-key-seed_query").count() == 0,
          "Find (2BR3): the old free-text 'Add an institution by name' input is gone")
    check("Add an institution by name" not in _full_page_text(page),
          "Find (2BR3): the old 'Add an institution by name' string renders nowhere")
    check("Matching institutions" not in _full_page_text(page),
          "Find (2BR3): the old 'Matching institutions' string renders nowhere")

    # --- empty basket -------------------------------------------------------
    n0 = _sidebar_basket_count(page)
    if n0 > 0:
        _sidebar_clear(page)
        n0 = _sidebar_basket_count(page)
    check(n0 == 0, f"Sidebar basket: starts empty on a fresh Find visit (got {n0})")

    # --- search + add ---------------------------------------------------
    added = _sidebar_add_matching(page, GDANSK_QUERY, GDANSK_NAME_FRAGMENT)
    check(added, "Sidebar search: 'gdansk' surfaces a result row with its own Add button")
    n1 = _sidebar_basket_count(page)
    check(n1 == 1, f"Sidebar basket: 1 item after adding the Gdansk result (got {n1})")
    check(_sidebar_add_matching(page, SORBONNE_QUERY), "Sidebar search: 'Sorbonne' surfaces a result row")
    n2 = _sidebar_basket_count(page)
    check(n2 == 2, f"Sidebar basket: 2 items after adding Sorbonne (got {n2})")
    check(_sidebar_add_matching(page, BOLOGNA_QUERY), "Sidebar search: 'Bologna' surfaces a result row")
    n3 = _sidebar_basket_count(page)
    check(n3 == 3, f"Sidebar basket: 3 items after adding Bologna (got {n3})")
    caption = _sidebar_basket_caption(page)
    check(f"3 of {BASKET_CAP} added" in caption,
          f"Sidebar basket: the '{{n}} of {{cap}} added' caption reads 3 of {BASKET_CAP} (got {caption!r})")

    # --- always-visible remove ----------------------------------------------
    _sidebar_remove_first(page)
    n4 = _sidebar_basket_count(page)
    check(n4 == 2, f"Sidebar basket: 2 items after removing one (always-visible remove, got {n4})")

    # --- fill to the cap and prove the blocked 11th add ---------------------
    # Clear first, then fill to 9 via NINE real sidebar search+add rounds
    # (a `?compare=` deep link cannot do this -- `resolve_slot_hydration`
    # trims to the view's own slot count, 3, before folding into the basket,
    # so it can never pre-fill past 3), then add a 10th through the same
    # real UI to reach the cap, then attempt an 11th: the real blocked-add
    # path (`state.add` returns False -> the sidebar renders
    # `copy.FIND["BASKET_FULL"]`).
    _sidebar_clear(page)
    for i, query in enumerate(BASKET_FILL_QUERIES, start=1):
        check(_sidebar_add_matching(page, query),
              f"Sidebar search: fill-round {i}/9 ({query!r}) adds successfully")
    n9 = _sidebar_basket_count(page)
    check(n9 == len(BASKET_FILL_QUERIES),
          f"Sidebar basket: holds {len(BASKET_FILL_QUERIES)} after 9 real adds (got {n9})")
    check(_sidebar_add_matching(page, GDANSK_QUERY, GDANSK_NAME_FRAGMENT),
          "Sidebar search: the 10th add (via the real UI) succeeds")
    n10 = _sidebar_basket_count(page)
    check(n10 == BASKET_CAP, f"Sidebar basket: holds exactly {BASKET_CAP} after the 10th add (got {n10})")

    # `_sidebar_add_matching`'s own return value means "the basket grew" --
    # for THIS attempt that is correctly False (blocked), so the row-
    # rendered claim is checked directly instead of by reusing that signal.
    _sidebar_search(page, "Bologna")
    n_rows_11th = _sidebar_result_rows(page).count()
    check(n_rows_11th > 0,
          f"Sidebar basket cap: the 11th add's own search still surfaces real result rows "
          f"(a genuine attempt, not a missing row) (found {n_rows_11th})")
    _sidebar_result_rows(page).first.click(timeout=ACTION_TIMEOUT_MS)
    _settle(page, 2000)
    after_n = _sidebar_basket_count(page)
    check(after_n == BASKET_CAP,
          f"Sidebar basket cap: an 11th add is BLOCKED, basket unchanged at {BASKET_CAP} (got {after_n})")
    caption_full = _sidebar_basket_caption(page)
    warn_text = _full_page_text(page)
    check(f"{BASKET_CAP} of {BASKET_CAP} added" in caption_full or "already holds the most" in warn_text.lower()
          or page.locator('[data-testid="stSidebar"] [data-testid="stAlert"]').count() >= 1,
          "Sidebar basket cap: the cap message renders on the blocked 11th add attempt")

    # --- Clear basket ---------------------------------------------------
    _sidebar_clear(page)
    n_cleared = _sidebar_basket_count(page)
    check(n_cleared == 0, f"Sidebar basket: Clear basket empties it (got {n_cleared})")
    _no_exception(page, "Sidebar search + basket flow")


def check_find_dropdown_over_basket(page) -> None:
    """2BR3 SEL: Find's own ONE dropdown OVER THE BASKET -- an empty basket
    shows the prompt and no profile; exactly one basket item auto-selects
    (no click, no selectbox at all); two or more still need an explicit pick
    (`.st-key-seed_pick`, `index=None`, never auto-loaded).

    Runs BEFORE `check_sidebar_search_and_basket` (see `main()`'s own
    ordering comment): once ANY basket sequence passes through exactly one
    item while on the Find page, `views_find._seed_pick` auto-sets
    `st.session_state["seed_id"]`, which then STAYS SET (its own documented
    behaviour: 'a pick already made survives a basket change that leaves it
    present') regardless of later basket edits -- so the 'empty basket -> no
    profile' state can only be observed genuinely fresh, before that first
    incidental single-item moment ever occurs anywhere else in the run."""
    _click_nav(page, "Find")
    _sidebar_clear(page)
    _settle(page, 1000)
    check(page.locator(".st-key-profile").count() == 0,
          "Find dropdown (empty basket): no profile renders")
    check(page.locator(".st-key-seed_pick").count() == 0,
          "Find dropdown (empty basket): no picker selectbox renders either")
    check("sidebar search" in _full_page_text(page).lower(),
          "Find dropdown (empty basket): the basket-driven prompt names the sidebar search")

    check(_sidebar_add_matching(page, GDANSK_QUERY, GDANSK_NAME_FRAGMENT),
          "Find dropdown: adding the sole basket item via the sidebar succeeds")
    page.wait_for_selector('[role="tab"]', timeout=ACTION_TIMEOUT_MS)
    _settle(page, 2500)
    check(page.locator(".st-key-seed_pick").count() == 0,
          "Find dropdown (exactly 1 basket item): AUTO-SELECTS -- no picker selectbox renders")
    check(page.locator(".st-key-profile").count() == 1,
          "Find dropdown (exactly 1 basket item): the profile renders with no explicit pick")

    check(_sidebar_add_matching(page, SORBONNE_QUERY),
          "Find dropdown: adding a 2nd basket item via the sidebar succeeds")
    _settle(page, 1500)
    # The already-resolved pick (Gdansk) survives a basket change that leaves
    # it present (per views_find._seed_pick's own docstring) -- so the
    # profile stays put; the NEW two-item rule is proven on a FRESH session.
    _no_exception(page, "Find dropdown over basket")


def check_find_dropdown_requires_explicit_pick(context) -> None:
    """FRESH session: basket pre-filled to 2 via a Compare deep link, then a
    hop to Find -- with 2+ basket items and NO prior pick this session, the
    picker selectbox renders and NOTHING is auto-loaded."""
    page = context.new_page()
    page.set_default_timeout(ACTION_TIMEOUT_MS)
    try:
        page.goto(f"{BASE_URL}/Compare?compare={STRASBOURG_ID},{CNRS_ID}", wait_until="domcontentloaded")
        page.wait_for_selector('[data-testid="stSidebarNav"]', state="attached", timeout=ACTION_TIMEOUT_MS)
        _settle(page, 3000)
        _click_nav(page, "Find")
        _settle(page, 1500)
        check(page.locator(".st-key-seed_pick").count() == 1,
              "Find dropdown (fresh session, 2 basket items): the picker selectbox renders")
        check(page.locator(".st-key-profile").count() == 0,
              "Find dropdown (fresh session, 2 basket items): NOTHING is auto-loaded, no profile yet")
        _open_select(page, "seed_pick")
        _pick_option(page)
        page.wait_for_selector('[role="tab"]', timeout=ACTION_TIMEOUT_MS)
        _settle(page, 2500)
        check(page.locator(".st-key-profile").count() == 1,
              "Find dropdown (fresh session): an explicit pick loads the profile")
        _no_exception(page, "Find dropdown requires explicit pick (fresh session)")
    except Exception as exc:
        fail_section("Find dropdown requires explicit pick", exc)
    finally:
        page.close()


# ----------------------------------------------------- deep-link hydration --

def check_deeplink_hydration(context, *, view: str, page_path: str, param: str,
                            ids: tuple, n_slots: int) -> None:
    """FRESH session, direct `?compare=`/`?pair=` navigation: both the slots
    AND the sidebar basket must reflect the hydrated ids on the FIRST render.

    `lib.selection.slots_row` folds the hydrated ids into the basket via
    `state.add()` INSIDE its own call, which runs AFTER
    `selection.render_sidebar()` has already drawn the sidebar for this same
    script run (both views call render_sidebar() before slots_row() in
    `render()`) -- so if the fold-in has no visible effect until a SECOND
    script run, the very first paint shows slots filled with an EMPTY
    sidebar basket. That gap, if reproduced, is a real cross-file bug
    (`lib/selection.py`, outside this stream's fence) -- reported as a
    FINDING for the manager, never patched here."""
    page = context.new_page()
    page.set_default_timeout(ACTION_TIMEOUT_MS)
    try:
        page.goto(f"{BASE_URL}/{page_path}?{param}={','.join(ids)}", wait_until="domcontentloaded")
        page.wait_for_selector('[data-testid="stSidebarNav"]', state="attached", timeout=ACTION_TIMEOUT_MS)
        _settle(page, 3500)
        slot_vals = [_slot_value(page, view, i) for i in range(n_slots)]
        n_filled = sum(1 for v in slot_vals if v and v != "Empty slot")
        n_basket = _sidebar_basket_count(page)
        check(n_filled == n_slots,
              f"{view} deep-link hydration: all {n_slots} slots hydrate from the URL "
              f"(got {n_filled}: {slot_vals})")
        ok_basket = check(n_basket == n_slots,
                          f"{view} deep-link hydration: the sidebar basket ALSO shows "
                          f"{n_slots} items on the very first render (got {n_basket})")
        if n_filled == n_slots and not ok_basket:
            finding(f"{view} deep-link hydration (?{param}=): slots hydrate to "
                    f"{n_filled}/{n_slots} on the FIRST render but the sidebar basket shows "
                    f"only {n_basket}/{n_slots} -- selection.render_sidebar() draws the "
                    f"basket BEFORE selection.slots_row() folds the URL ids into it in the "
                    f"SAME script run (lib/selection.py, outside the TEV-U fence). A second "
                    f"rerun (any widget interaction) self-corrects; the raw first paint does "
                    f"not. Reported, not patched.")
        _no_exception(page, f"{view} deep-link hydration (fresh session)")
    except Exception as exc:
        fail_section(f"{view} deep-link hydration", exc)
    finally:
        page.close()


# ----------------------------------------------------- Find profile body ----
# UNCHANGED in shape this round (SEL/VC/VL all confirm the profile body is
# byte-unchanged) -- ported from the pre-2BR3 suite with only the ENTRY
# mechanism updated (sidebar search, not a per-page free-text box).

def check_controls_placement(page) -> None:
    sidebar = page.locator('[data-testid="stSidebar"]')
    check(sidebar.locator(".st-key-tree").count() >= 1, "Sidebar: .st-key-tree (scenario) present")
    check(sidebar.locator(".st-key-basis").count() >= 1, "Sidebar: .st-key-basis (scenario) present")
    check(sidebar.locator(".st-key-depth").count() == 0, "Sidebar: no .st-key-depth")
    check(sidebar.locator(".st-key-f_types").count() == 0, "Sidebar: no .st-key-f_types")
    check(sidebar.locator(".st-key-c1_on").count() == 0, "Sidebar: no .st-key-c1_on")

    check(page.locator(".st-key-depth").count() >= 1, "Controls row: .st-key-depth renders in the main area")
    check(page.locator(".st-key-c1_on").count() >= 1, "Controls row: .st-key-c1_on renders in the main area")
    check(page.locator(".st-key-l7_on").count() >= 1, "Controls row: .st-key-l7_on renders in the main area")

    tree_val = _selectbox_value(page, "tree")
    check(tree_val == TREE_LABEL_BESTFIT,
          f"Sidebar: taxonomy selectbox shows the default DISPLAY label (got {tree_val!r})")
    check("bestfit" not in tree_val, "Sidebar: the internal taxonomy value never appears")
    basis_val = _selectbox_value(page, "basis")
    check(basis_val == BASIS_LABEL_FRAC,
          f"Sidebar: counting-basis selectbox shows the default DISPLAY label (got {basis_val!r})")

    _ensure_expander_open(page, "postfilters", ".st-key-f_types input")
    check(page.locator(".st-key-f_types").count() >= 1, "Post-filters expander: reveals .st-key-f_types")
    check(page.locator(".st-key-f_countries").count() >= 1, "Post-filters expander: reveals .st-key-f_countries")
    _no_exception(page, "Controls placement / sidebar labels / post-filters")


def check_profile_and_panels(page) -> dict:
    check(page.locator(".st-key-profile").count() == 1,
          "Profile: .st-key-profile container renders exactly once")
    check(page.locator('.st-key-profile [data-testid="stImage"] img').count() >= 1,
          "Profile: subfield wordcloud renders as an <img>")

    tiles = page.locator(".st-key-profile .benchup-kpi")
    check(tiles.count() == N_CARDS, f"Profile: {N_CARDS} cards render (found {tiles.count()})")
    full_text = _full_page_text(page)
    for label in CARD_LABELS:
        check(label in full_text, f"Profile: card {label!r} renders")
    sublines = page.locator(".st-key-profile .benchup-kpi-sub")
    n_sub = sublines.count()
    check(n_sub == N_CARDS, f"Profile: every card carries exactly one small line (found {n_sub})")

    id_box = page.locator(".st-key-profile")
    name_link = id_box.locator("h3 a").first
    check(name_link.count() >= 1, "Identity: the institution NAME renders as a link")
    name_href = name_link.get_attribute("href") or ""
    check("openalex.org/works" in name_href,
          f"Identity: the institution name links to its own OpenAlex works ({name_href!r})")
    id_text = id_box.inner_text()
    check(NO_LONGER_ON_FIND not in id_text,
          f"Identity: the separate {NO_LONGER_ON_FIND!r} link is gone")

    for name, label in PANEL_LABELS:
        summary = page.locator(f".st-key-panel_{name} summary").first
        check(summary.count() >= 1, f"Panel '{name}': expander present (.st-key-panel_{name})")
        raw = (summary.text_content() or "").strip()
        clean = raw.replace("keyboard_arrow_right", "").replace("keyboard_arrow_down", "").strip()
        check(clean == label, f"Panel '{name}': header label is exactly {label!r} (got {raw!r})")

    _ensure_expander_open(page, "panel_subfields", ".st-key-fig_subfields")
    _settle(page, 1500)
    fig = page.locator(".st-key-fig_subfields .js-plotly-plot").first
    check(fig.count() >= 1 and fig.is_visible(), "Panel Top subfields: reveals a visible Plotly figure")
    check(page.locator(".st-key-panel_subfields .st-key-sort_subfields").count() == 0,
          "Panel Top subfields: carries NO sort control")

    _ensure_expander_open(page, "panel_topics", ".st-key-fig_topics")
    _settle(page, 1500)
    check(page.locator(".st-key-panel_topics .st-key-sort_topics").count() == 0,
          "Panel Top topics: carries NO sort control")

    _ensure_expander_open(page, "panel_sdg", ".st-key-fig_sdg")
    _settle(page, 1500)
    sdg_ticks = page.locator(".st-key-fig_sdg .ytick")
    n_sdg = sdg_ticks.count()
    sdg_texts = [sdg_ticks.nth(i).text_content() or "" for i in range(n_sdg)]
    non_sdg = [t for t in sdg_texts if not t.strip().startswith("SDG")]
    check(n_sdg > 0 and not non_sdg,
          f"Panel SDG profile: all {n_sdg} y-tick labels start with 'SDG' (offenders: {non_sdg})")

    _ensure_expander_open(page, "panel_frontier", ".st-key-frontier_mode button")
    _settle(page, 1500)
    top_points = _plotly_point_count(page, ".st-key-panel_frontier .js-plotly-plot")
    check(top_points > 0, f"Panel Frontier positioning: default mode plots points ({top_points})")
    page.locator(".st-key-frontier_mode button").nth(FRONTIER_MODE_EMERGING_IDX).click(timeout=ACTION_TIMEOUT_MS)
    _settle(page, 4000)
    emerging_points = _plotly_point_count(page, ".st-key-panel_frontier .js-plotly-plot")
    check(emerging_points > 0,
          f"Panel Frontier positioning: the mode control still plots points ({top_points} -> {emerging_points})")

    before_legend = _all_text(page, '.st-key-profile div[style*="flex-wrap"]')
    check(bool(before_legend.strip()), "Breakdown: chip legend renders")
    page.locator(".st-key-breakdown_dim button").nth(BREAKDOWN_DOCTYPE_IDX).click(timeout=ACTION_TIMEOUT_MS)
    _settle(page, 4000)
    after_legend = _all_text(page, '.st-key-profile div[style*="flex-wrap"]')
    check(after_legend != before_legend and bool(after_legend.strip()),
          "Breakdown: segmented control swaps the chip legend (domain <-> document type)")

    _no_exception(page, "Profile / panels")
    return {"frontier_points": emerging_points, "breakdown_legend": after_legend}


def check_bonus_year_axis(page) -> None:
    labels = page.evaluate(
        "(() => { const el = document.querySelector('.st-key-fig_breakdown_yearly .js-plotly-plot');"
        " if (!el || !el.data) return [];"
        " return el.data.flatMap(t => t.x || []); })()")
    check(BONUS_YEAR_AXIS_LABEL in labels,
          f"Breakdown yearly axis: the bonus year is starred ({BONUS_YEAR_AXIS_LABEL!r} in {labels})")


def check_si_value_labels(page) -> None:
    for name, fig_key, probe in (
            ("fields", "fig_fields", ".st-key-fig_fields"),
            ("subfields", "fig_subfields", ".st-key-fig_subfields"),
            ("erc", "fig_erc", ".st-key-sort_erc [data-testid='stRadioOption']")):
        try:
            _ensure_expander_open(page, f"panel_{name}", probe)
            _settle(page, 1200)
            info = page.evaluate(
                """(sel) => {
                    const el = document.querySelector(sel);
                    if (!el || !el.data) return {n_labels: -1, showgrid: null};
                    let n = 0;
                    for (const t of el.data) {
                        if (t.mode && t.mode.indexOf('text') >= 0 && Array.isArray(t.text)) {
                            n += t.text.filter(x => x).length;
                        }
                    }
                    const keys = Object.keys(el.layout || {}).filter(k => /^xaxis/.test(k)).sort();
                    const showgrid = keys.length ? (el.layout[keys[keys.length - 1]].showgrid) : null;
                    return {n_labels: n, showgrid: showgrid};
                }""",
                f".st-key-{fig_key} .js-plotly-plot")
            check(info.get("n_labels", -1) > 0,
                  f"Panel '{name}': the SI marker carries an outer-end value label ({info.get('n_labels')})")
            check(info.get("showgrid") is False,
                  f"Panel '{name}': the retired per-integer SI unit grid stays off ({info.get('showgrid')!r})")
        except Exception as exc:
            fail_section(f"SI value labels ({name})", exc)


def check_tab_overflow_a11(page) -> None:
    try:
        page.locator(".st-key-c1_on label").first.click(timeout=ACTION_TIMEOUT_MS)
        page.locator(".st-key-l7_on label").first.click(timeout=ACTION_TIMEOUT_MS)
        _wait_for(page, lambda: page.locator('[role="tab"]').count() == BOTH_OPTIONAL_TAB_COUNT)
        _settle(page, 800)
        tabs_n = page.locator('[role="tab"]').count()
        check(tabs_n == BOTH_OPTIONAL_TAB_COUNT,
              f"A11: with both optional lenses on, tab count is {BOTH_OPTIONAL_TAB_COUNT} (got {tabs_n})")
        info = page.evaluate(
            """(() => {
                const el = document.querySelector('[role="tablist"]')
                        || document.querySelector('[data-testid="stTabs"]');
                if (!el) return null;
                return {scroll: el.scrollWidth, client: el.clientWidth};
            })()""")
        check(info is not None and info["scroll"] <= info["client"] + 2,
              f"A11: the tab strip fits with no silent scroll at 1280px "
              f"(scroll {info and info.get('scroll')} <= client {info and info.get('client')})")
        tab_text = _all_text(page, '[role="tab"]')
        for code in ("L0", "L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "L9"):
            check(code in tab_text, f"A11: tab strip carries the bare display code {code!r}")
    except Exception as exc:
        fail_section("A11 tab overflow", exc)
    finally:
        try:
            page.locator(".st-key-c1_on label").first.click(timeout=ACTION_TIMEOUT_MS)
            page.locator(".st-key-l7_on label").first.click(timeout=ACTION_TIMEOUT_MS)
            _wait_for(page, lambda: page.locator('[role="tab"]').count() == GDANSK_TAB_COUNT)
            _settle(page, 800)
        except Exception:  # noqa: BLE001
            pass


def check_benchmark_lens_guide(page) -> None:
    _ensure_expander_open(page, "lens_guide", ".st-key-lens_guide strong")
    summary = page.locator(".st-key-lens_guide summary").first
    raw = (summary.text_content() or "").strip()
    clean = raw.replace("keyboard_arrow_right", "").replace("keyboard_arrow_down", "").strip()
    check(clean == LENS_GUIDE_HEADER, f"Lens guide: header label is exactly {LENS_GUIDE_HEADER!r} (got {raw!r})")
    n_lines = page.locator(".st-key-lens_guide strong").count()
    check(n_lines >= 8, f"Lens guide: at least 8 lens lines render (found {n_lines})")

    tabs = page.locator('[role="tab"]')
    first_lens_tab_text = (tabs.nth(1).text_content() or "").strip()
    check(first_lens_tab_text == LENS0_TAB_CODE,
          f"A11: the first default-lens TAB carries only the bare code (got {first_lens_tab_text!r})")
    tabs.nth(1).click(timeout=ACTION_TIMEOUT_MS)
    _settle(page, 1500)
    body_text = _all_text(page, '[role="tabpanel"]')
    check(LENS0_FULL_NAME in body_text, f"A11: the full lens name opens the tab BODY ({LENS0_FULL_NAME!r})")
    tabs.nth(0).click(timeout=ACTION_TIMEOUT_MS)
    _settle(page, 1000)
    caption = _all_text(page, '[data-testid="stCaptionContainer"]')
    check(LENS_LEGEND_SUBSTR in caption, "Overview: the legend caption points at the lens guide")
    _no_exception(page, "Benchmark lens guide")


def _download_csv_header(page, click_selector: str) -> str:
    with page.expect_download(timeout=ACTION_TIMEOUT_MS) as dl_info:
        page.locator(click_selector).click(timeout=ACTION_TIMEOUT_MS)
    download = dl_info.value
    path = download.path()
    with open(path, "r", encoding="utf-8") as fh:
        return fh.readline()


def check_tables_and_export(page) -> None:
    tabs = page.locator('[role="tab"]')
    tabs.nth(1).click(timeout=ACTION_TIMEOUT_MS)
    _settle(page, 2000)
    check(page.locator('.st-key-tbl_L0 [data-testid="stDataFrame"]').count() >= 1,
          "Lens table: L0's ranked table renders")
    header = _download_csv_header(page, ".st-key-dl_L0 button")
    check("total_frac_2020_2024" in header, "CSV export: header carries total_frac_2020_2024")
    check("badge" not in header, "CSV export: header carries NO badge column")

    tabs.last.click(timeout=ACTION_TIMEOUT_MS)
    _settle(page, 2500)
    check(page.locator('.st-key-tbl_aspirational [data-testid="stDataFrame"]').count() >= 1,
          "Aspirational tab: its own table renders")
    tabs.nth(0).click(timeout=ACTION_TIMEOUT_MS)
    _settle(page, 1500)
    _no_exception(page, "Tables / export")


def check_settings(page) -> None:
    before = _all_text(page, '[data-testid="stCaptionContainer"]')
    _ensure_expander_open(page, "postfilters", ".st-key-f_types input")
    tinp = page.locator(".st-key-f_types input").first
    tinp.click(timeout=ACTION_TIMEOUT_MS)
    tinp.fill("education")
    page.wait_for_selector('[role="option"]', timeout=ACTION_TIMEOUT_MS)
    page.locator('[role="option"]').filter(has_text="education").first.click(timeout=ACTION_TIMEOUT_MS)
    _settle(page, 3500)

    page.locator('.st-key-depth [data-testid="stRadioOption"]').last.click(timeout=ACTION_TIMEOUT_MS)
    _settle(page, 3000)
    after = _all_text(page, '[data-testid="stCaptionContainer"]')
    check(before != after, "Settings: depth caption changed after switching depth to its max")

    _open_select(page, "tree")
    _pick_option(page, TREE_LABEL_ORIGINAL)
    _wait_for(page, lambda: page.locator('[role="tab"]').count() >= GDANSK_TAB_COUNT)
    _settle(page, 1000)

    page.locator(".st-key-l7_on label").first.click(timeout=ACTION_TIMEOUT_MS)
    _wait_for(page, lambda: page.locator('[role="tab"]').count() == L7_ON_TAB_COUNT)
    _settle(page, 800)
    tabs = page.locator('[role="tab"]').count()
    check(tabs == L7_ON_TAB_COUNT, f"Settings: L7 tab appeared, tab count is {L7_ON_TAB_COUNT} (got {tabs})")
    check(page.locator(".st-key-strip").count() >= 1, "Settings: off-default strip is visible")
    strip = _all_text(page, ".st-key-strip")
    check(STRIP_TREE_ORIGINAL in strip, "Settings: strip shows the taxonomy's DISPLAY label")
    check("depth = 50" in strip, f"Settings: strip mentions depth = 50 (strip: {strip!r})")
    _no_exception(page, "Settings")


def check_type_filter_clear(page) -> None:
    strip = _all_text(page, ".st-key-strip")
    check("type: " in strip and "education" in strip, "Type filter: still active going in")
    _ensure_expander_open(page, "postfilters", ".st-key-f_types input")
    tag_close = page.locator(".st-key-f_types [data-baseweb='tag'] [role='button'], "
                              ".st-key-f_types [data-baseweb='tag'] svg")
    if tag_close.count():
        tag_close.first.click(timeout=ACTION_TIMEOUT_MS)
    else:
        page.locator(".st-key-f_types input").first.click(timeout=ACTION_TIMEOUT_MS)
        page.keyboard.press("Backspace")
    _settle(page, 3500)
    strip2 = _all_text(page, ".st-key-strip")
    check("education" not in strip2, "Type filter: strip no longer names it after clearing")
    _no_exception(page, "Type filter cleared")


def check_undefined_lens(page, app_dir: Path) -> None:
    sys.path.insert(0, str(app_dir))
    from lib.data_cache import index
    from lib.engine import build_substrates, load_context, rank_all

    idx = index().sort_values("total_full_2020_2024")
    ctx = load_context(str(app_dir / "data"))
    subs = build_substrates(ctx, "original")
    seed_id = seed_name = None
    for row in idx.itertuples(index=False):
        ranking = rank_all(ctx, subs, row.institution_id)
        l2f = ranking.get("L2f")
        if l2f and l2f.get("undefined"):
            seed_id, seed_name = row.institution_id, row.display_name
            break
    if seed_id is None:
        check(False, "Undefined lens: no institution with an undefined L2f was found")
        return
    check(_sidebar_add_matching(page, seed_name), f"Undefined lens: sidebar-adds {seed_name!r}")
    if page.locator(".st-key-seed_pick").count():
        _open_select(page, "seed_pick")
        _pick_option(page, seed_name)
        _settle(page, 2500)
    page.wait_for_selector('[role="tab"]', timeout=ACTION_TIMEOUT_MS)
    heading = page.locator(".st-key-profile h3").first.text_content() or ""
    check(len(heading) > 0, f"Undefined lens: seed {seed_name!r} loaded, heading present")
    tab = page.locator('[role="tab"]').filter(has_text=L2F_TAB_CODE).first
    check(tab.count() >= 1, f"Undefined lens: {L2F_TAB_CODE!r} tab present")
    tab.click(timeout=ACTION_TIMEOUT_MS)
    _settle(page, 1500)
    text = _all_text(page, '[role="tabpanel"]')
    check(L2F_DISPLAY_NAME in text and "cannot be computed for this seed" in text,
          f"Undefined lens: the L2f undefined message present for {seed_name}")
    _no_exception(page, "Undefined L2f seed")


# ------------------------------------------------------------------ Compare -

def _cmp_opt_texts(page, key: str) -> list:
    return [t.strip() for t in
            page.locator(f'.st-key-{key} [data-testid="stRadioOption"]').all_text_contents() if t.strip()]


def _cmp_click_opt(page, key: str, text: str) -> None:
    page.locator(f".st-key-{key}").get_by_text(text, exact=True).first.click(timeout=ACTION_TIMEOUT_MS)
    _settle(page, 2500)


def check_compare_page(context) -> None:
    """Fresh, standalone session (a shared trio via `?compare=`) -- section
    order (KPI cards before Coverage before every chart), slots read ONLY
    the basket, slot-1-darkest, the metric selector's vocabulary + a sweep,
    per-chart 'Not shown here, and why' expanders, the shared frontier's
    top-20 + Show all, the bottom About block, the 9-sheet workbook, every
    2BR3 deletion asserted absent, no forbidden vocab / pastel hex / bare NA
    hover, no horizontal scroll at three widths."""
    page = context.new_page()
    page.set_default_timeout(ACTION_TIMEOUT_MS)
    try:
        page.goto(f"{BASE_URL}/Compare?compare={','.join(COMPARE_TRIO)}", wait_until="domcontentloaded")
        page.wait_for_selector('[data-testid="stSidebarNav"]', state="attached", timeout=ACTION_TIMEOUT_MS)
        _wait_for(page, lambda: page.locator(".js-plotly-plot").count() >= COMPARE_MIN_FIGURES,
                 timeout_ms=45_000)
        _settle(page, 2500)
        _no_exception(page, "Compare (fresh trio, initial render)")

        # --- old free-text/handoff UI is GONE -------------------------------
        check(page.locator(".st-key-basket_add").count() == 0,
              "Compare (2BR3): the old per-page 'add a comparator' box is gone")
        check(page.locator(".st-key-cmp_handoff_open").count() == 0,
              "Compare (2BR3): the old 'Take one pair further' hand-off button is gone")
        full_text = _full_page_text(page)
        for s in COMPARE_DELETED_STRINGS:
            check(s not in full_text, f"Compare (2BR3): the retired string {s!r} renders nowhere")

        for i in range(COMPARE_CAP):
            v = _slot_value(page, "compare", i)
            check(bool(v) and v != "Empty slot", f"Compare slots: slot {i + 1} is filled ({v!r})")

        # --- section order: KPI cards -> Coverage -> every chart -------------
        positions = [full_text.find(s) for s in COMPARE_SECTION_ORDER]
        check(all(p >= 0 for p in positions),
              f"Compare section order: every 2BR3 header renders ({list(zip(COMPARE_SECTION_ORDER, positions))})")
        check(positions == sorted(positions),
              f"Compare section order (LOAD-BEARING): KPI cards -> Coverage -> every 'Compare by' "
              f"section -> both frontier charts -> Impact -> About, in that exact order "
              f"(positions {positions})")

        # --- slot-1-darkest: the strip's first swatch paints the darkest navy
        dot_colors = page.evaluate(
            "Array.from(document.querySelectorAll('.st-key-compare_strip span[style*=\"color:\"]'))"
            ".slice(0, 1).map(e => getComputedStyle(e).color)")
        check(bool(dot_colors) and dot_colors[0] == _hex_to_rgb_css(NAVY_HEXES[0]),
              f"Compare KPI cards (2BR3 palette): slot 1's own swatch paints the darkest navy "
              f"{NAVY_HEXES[0]} (got {dot_colors})")

        # --- metric selector vocabulary + a light sweep -----------------------
        subj_opts = _cmp_opt_texts(page, "cmp_metric_subject")
        erc_opts = _cmp_opt_texts(page, "cmp_metric_erc")
        sdg_opts = _cmp_opt_texts(page, "cmp_metric_sdg")
        for level, opts in (("subject", subj_opts), ("ERC", erc_opts), ("SDG", sdg_opts)):
            check(VOL_TOP10_LABEL not in opts, f"Compare {level}: the retired top-decile TAB is not offered")
        check(set(SUBJECT_METRIC_LABELS) <= set(subj_opts),
              f"Compare subject: offers Share/Specialisation/PP/SDG/Dynamics ({subj_opts})")
        check(VOLUME_LABEL in erc_opts, f"Compare ERC: 'Volume' is offered ({erc_opts})")
        check(VOLUME_LABEL in sdg_opts, f"Compare SDG: 'Volume' is offered ({sdg_opts})")
        for label in ("Share", "Change in mean annual volume", "PP(top10%)"):
            if label in subj_opts:
                _cmp_click_opt(page, "cmp_metric_subject", label)
                check(page.locator(".st-key-fig_cmp_subject .js-plotly-plot").count() >= 1,
                      f"Compare subject = {label!r}: the chart renders")
        _no_exception(page, "Compare (after the metric sweep)")

        # --- slots read ONLY the basket -----------------------------------
        # Checked HERE, after at least one real widget interaction (the
        # metric sweep above) rather than right after the initial goto: a
        # fresh session's FIRST paint hits the same first-paint hydration
        # gap `check_deeplink_hydration` documents as a FINDING (the
        # sidebar's basket display is drawn one script run behind the
        # slots' own basket read) -- any later rerun already self-corrects.
        n_opts = _slot_options_count(page, "compare", 0)
        n_basket = _sidebar_basket_count(page)
        check(n_opts == n_basket + 1,
              f"Compare slots: slot 1's own options are the basket ({n_basket}) + the empty "
              f"sentinel (got {n_opts} options)")

        # --- per-chart 'Not shown here, and why' expander --------------------
        caps = _all_text(page, '[data-testid="stCaptionContainer"]') + full_text
        check(NOT_OFFERED_HEADER in _full_page_text(page),
              f"Compare: the per-chart {NOT_OFFERED_HEADER!r} expander renders")

        # --- shared frontier top-20 + Show all --------------------------------
        shared_text = _full_page_text(page)
        show_all_btn = page.locator("button").filter(has_text=re.compile(r"^Show all \d"))
        if show_all_btn.count():
            before_n = _plotly_point_count(page, ".st-key-fig_cmp_shared_frontier .js-plotly-plot")
            show_all_btn.first.click(timeout=ACTION_TIMEOUT_MS)
            _settle(page, 2500)
            after_n = _plotly_point_count(page, ".st-key-fig_cmp_shared_frontier .js-plotly-plot")
            check(after_n >= before_n,
                  f"Compare shared frontier: 'Show all' reveals at least as many bars ({before_n} -> {after_n})")
        else:
            check("Who holds the shared frontier" in shared_text,
                  "Compare shared frontier: renders (no 'Show all' needed -- total <= 20)")

        # --- the bottom About block --------------------------------------------
        _ensure_expander_open_by_text(page, "About these figures", ".st-key-compare_strip")
        about_text = _full_page_text(page)
        check("institutions" in about_text.lower() and DATA_CAPTION_RE.search(about_text) is not None,
              "Compare 'About these figures': carries the index-size/data-date caption")

        # --- absences: forbidden vocab / pastel hex / bare NA hover ----------
        _no_forbidden_vocab(page, "Compare page (fresh trio)")
        _no_pastel_hexes(page, "Compare page (fresh trio)")
        _no_bare_na_in_hover(page, [".st-key-fig_cmp_subject .js-plotly-plot",
                                    ".st-key-fig_cmp_erc .js-plotly-plot",
                                    ".st-key-fig_cmp_sdg .js-plotly-plot"],
                            "Compare page (fresh trio)")
        check("(generated" not in shared_text, "Compare: the old verbose snapshot stamp is gone")

        # --- the workbook -----------------------------------------------------
        # The button's own presence is asserted unconditionally; the actual
        # download+contents proof is wrapped in its OWN try/except (a
        # separate, bounded concern from the rest of this standalone check)
        # so a slow/undelivered download event never takes the widths and
        # screenshot proofs below down with it -- probe.py's own
        # `_probe_compare` already proves this exact mechanism end to end,
        # against a REAL institution trio, twice (see the deletion ledger /
        # progress note for the measured numbers).
        dl_btn = page.locator(".st-key-dl_workbook button").first
        check(dl_btn.count() >= 1, "Compare: the workbook export button renders")
        try:
            with page.expect_download(timeout=45_000) as dl_info:
                dl_btn.click(timeout=ACTION_TIMEOUT_MS)
            raw = Path(dl_info.value.path()).read_bytes()
            check(raw[:2] == b"PK", "Compare: the workbook downloads as a real xlsx container")
            book = openpyxl.load_workbook(io.BytesIO(raw))
            check(len(book.sheetnames) == XLSX_SHEET_COUNT,
                  f"Compare: the workbook carries exactly {XLSX_SHEET_COUNT} sheets ({book.sheetnames})")
            check(XLSX_METHODS_SHEET in book.sheetnames, "Compare: the workbook carries a Methods sheet")
        except Exception as exc:  # noqa: BLE001 -- see the comment above: bounded, non-fatal to the rest
            fail_section("Compare workbook download", exc)

        # --- widths -----------------------------------------------------------
        for width in WIDTHS:
            page.set_viewport_size({"width": width, "height": 900})
            _settle(page, 900)
            scroll = page.evaluate("document.documentElement.scrollWidth")
            inner = page.evaluate("window.innerWidth")
            check(scroll <= inner + 2, f"Compare {width}px: scrollWidth {scroll} <= innerWidth+2 {inner + 2}")
        page.set_viewport_size({"width": 1920, "height": 1080})
        shot_dir = DEFAULT_APP_DIR / "tests" / "ui" / "screenshots"
        shot_dir.mkdir(parents=True, exist_ok=True)
        _settle(page, 800)
        page.screenshot(path=str(shot_dir / "tevu_compare_1920.png"), full_page=True)
        _no_exception(page, "Compare (fresh trio, final)")
    except Exception as exc:
        fail_section("Compare page (fresh trio)", exc)
    finally:
        page.close()


# --------------------------------------------------------------- Collaborate

def check_collab_anchor_pair(context) -> None:
    """Fresh, standalone session, the manager-verified anchor pair
    (Universite de Strasbourg x CNRS, via `?pair=`): the momentum headline +
    evidence lines, identity cards on slot fill, the joint-only pulse legend,
    the domain-coloured field chart, the reciprocity bubble scatter (squared
    axes, one dotted diagonal), the topic + untapped native dataframes with
    their own 'Show all' buttons, the siblings hand-built table, every 2BR3
    Collaborate deletion asserted absent, no forbidden vocab / pastel hex /
    bare NA hover, no horizontal scroll at three widths."""
    page = context.new_page()
    page.set_default_timeout(ACTION_TIMEOUT_MS)
    try:
        page.goto(f"{BASE_URL}/Collaborate?pair={STRASBOURG_ID},{CNRS_ID}", wait_until="domcontentloaded")
        page.wait_for_selector('[data-testid="stSidebarNav"]', state="attached", timeout=ACTION_TIMEOUT_MS)
        _wait_for(page, lambda: page.locator(".js-plotly-plot").count() >= 3, timeout_ms=45_000)
        _settle(page, 3000)
        _no_exception(page, "Collaborate (anchor pair, initial render)")

        # --- slots + identity ---------------------------------------------
        for i in range(COLLAB_CAP):
            v = _slot_value(page, "collab", i)
            check(bool(v) and v != "Empty slot", f"Collaborate slots: slot {i + 1} is filled ({v!r})")
        check(page.locator(".st-key-collab_header").count() == 1, "Collaborate: identity card container renders")

        # --- momentum headline + evidence -----------------------------------
        check(page.locator(".st-key-collab_momentum").count() == 1,
              "Collaborate: the momentum headline container renders")
        mom_text = _all_text(page, ".st-key-collab_momentum")
        check("Momentum" in mom_text, "Collaborate momentum: the 'Momentum' label renders")
        check(bool(re.search(r"p\s*=|p\s*<", mom_text)),
              f"Collaborate momentum: the significance line names p (mom_text[:200]={mom_text[:200]!r})")
        check(SEP in mom_text or "-" in mom_text or "–" in mom_text,
              "Collaborate momentum: the evidence line names both dynamics windows")
        # The container's FIRST div is the small st.caption("Momentum") label
        # -- the big glyph+text markup carries its own inline font-size, so
        # it has to be found by that inline style, not by DOM order.
        big = page.evaluate(
            "(() => { const e = document.querySelector("
            "'.st-key-collab_momentum div[style*=\"font-size\"]');"
            " return e ? parseFloat(getComputedStyle(e).fontSize) : 0; })()")
        check(big >= 20, f"Collaborate momentum: the headline text is genuinely large ({big}px)")

        # --- pulse: legend is JOINT ONLY ------------------------------------
        check(page.locator(".st-key-fig_pulse .js-plotly-plot").count() >= 1, "Collaborate: the pulse chart renders")
        legend_text = _all_text(page, ".st-key-collab_legend")
        check("signed by both" in legend_text, "Collaborate pulse legend: carries the joint-only chip")
        # `charts_compare.fig_pulse`'s own contract: the star lives in the
        # x-AXIS TICKTEXT (a category-axis relabel), never in the trace's raw
        # `x` values themselves (those stay the bare year, e.g. "2025") --
        # reading `t.x` alone (the Find yearly-breakdown chart's own idiom)
        # would never find it on THIS chart.
        pulse_ticktext = page.evaluate(
            "(() => { const el = document.querySelector('.st-key-fig_pulse .js-plotly-plot');"
            " if (!el || !el.layout) return [];"
            " return (el.layout.xaxis || {}).ticktext || []; })()")
        check(BONUS_YEAR_AXIS_LABEL in [str(v) for v in pulse_ticktext],
              f"Collaborate pulse: the partial bonus year is starred "
              f"({BONUS_YEAR_AXIS_LABEL!r} in {pulse_ticktext})")

        # --- the domain-coloured field chart (no table) -----------------------
        check(page.locator(".st-key-fig_fields .js-plotly-plot").count() >= 1,
              "Collaborate: the domain-coloured field chart renders")
        fields_data = _fig_xy_text(page, ".st-key-fig_fields .js-plotly-plot")
        n_field_vals = sum(len([v for v in tr["x"] if v not in (None, "")]) for tr in (fields_data or []))
        check(bool(fields_data) and n_field_vals > 0,
              f"Collaborate field chart: carries real values ({n_field_vals})")
        check(page.locator('[data-table="collab_fields"]').count() == 0,
              "Collaborate (2BR3): the old field TABLE is gone -- the chart is the whole section")

        # --- the reciprocity bubble scatter: squared axes, one diagonal -------
        recip = page.locator(".st-key-fig_reciprocity .js-plotly-plot")
        check(recip.count() >= 1, "Collaborate: the 'Strategic reciprocity by field' chart renders")
        layout = _fig_layout(page, ".st-key-fig_reciprocity .js-plotly-plot")
        check(layout is not None and layout.get("shapes_n", 0) >= 1,
              f"Collaborate reciprocity: one dotted diagonal shape draws ({layout})")
        check(layout is not None and layout.get("scaleanchor_y") == "x",
              f"Collaborate reciprocity: the y-axis is scale-anchored to x (squared axes) ({layout})")
        if layout and layout.get("xrange") and layout.get("yrange"):
            xr, yr = layout["xrange"], layout["yrange"]
            check(abs(float(xr[1]) - float(yr[1])) < 1e-6,
                  f"Collaborate reciprocity: both axes share the SAME [0, max] range ({xr} vs {yr})")

        # --- the topic deep-dive: native dataframe, 20 + Show all --------------
        dataframes = page.locator('[data-testid="stDataFrame"]')
        check(dataframes.count() >= 2,
              f"Collaborate (2BR3 native dataframes): at least 2 render, topics + untapped "
              f"(found {dataframes.count()})")
        # The topic and untapped sections' "Show all N topics" buttons carry
        # the EXACT SAME copy template (copy.COLLAB["SHOW_ALL_BUTTON"]), so
        # this regex matches BOTH when both have >20 rows to hide -- a
        # before/after COUNT (not an absolute-absence check) is what proves
        # the FIRST one specifically hid itself, since the second may well
        # still be showing after the first is clicked.
        topics_show_all = page.locator("button").filter(has_text=re.compile(r"^Show all \d+ topics"))
        n_show_all_before = topics_show_all.count()
        if n_show_all_before:
            topics_show_all.first.click(timeout=ACTION_TIMEOUT_MS)
            _settle(page, 3000)
            n_show_all_after = page.locator("button").filter(
                has_text=re.compile(r"^Show all \d+ topics")).count()
            check(n_show_all_after < n_show_all_before,
                  f"Collaborate topic table: 'Show all' hides itself once clicked "
                  f"({n_show_all_before} -> {n_show_all_after} matching buttons)")
        check(page.locator(".st-key-topics_n").count() == 0,
              "Collaborate (2BR3): the old topic-depth SLIDER is gone")

        # --- slots read ONLY the basket -------------------------------------
        # Checked HERE (after the show-all click above forces a rerun),
        # avoiding the same first-paint hydration gap `check_deeplink_
        # hydration` documents as a FINDING.
        n_opts = _slot_options_count(page, "collab", 0)
        n_basket = _sidebar_basket_count(page)
        check(n_opts == n_basket + 1,
              f"Collaborate slots: slot 1's own options are the basket ({n_basket}) + empty "
              f"sentinel (got {n_opts})")

        # --- untapped: same 20 + Show all pattern -------------------------------
        untapped_show_all = page.locator("button").filter(has_text=re.compile(r"^Show all \d"))
        n_range_main = page.locator('[data-testid="stMain"] input[type="range"]').count()
        check(n_range_main == 0,
              f"Collaborate (2BR3): NO row sliders remain in the main content (found {n_range_main})")

        # --- siblings: the ONE surviving hand-built HTML table ------------------
        _ensure_expander_open_by_text(page, "Adjacent topics in the same subfields",
                                      '[data-table="collab_siblings"]')
        _settle(page, 1000)
        sib = page.locator('[data-table="collab_siblings"]')
        check(sib.count() >= 1, "Collaborate: the siblings table (the one surviving hand-built HTML table) renders")

        # --- section order -----------------------------------------------------
        full_text = _full_page_text(page)
        positions = [full_text.find(s) for s in COLLAB_SECTION_ORDER]
        check(all(p >= 0 for p in positions),
              f"Collaborate section order: every 2BR3 header renders ({list(zip(COLLAB_SECTION_ORDER, positions))})")
        check(positions == sorted(positions),
              f"Collaborate section order: pulse -> fields -> reciprocity -> topics -> untapped "
              f"-> About, in that exact order (positions {positions})")

        # --- deletions --------------------------------------------------------
        for s in COLLAB_DELETED_STRINGS:
            check(s not in full_text, f"Collaborate (2BR3): the retired string {s!r} renders nowhere")
        check(page.locator(".st-key-pair_swap").count() == 0,
              "Collaborate (2BR3): the old A/B swap button is gone (the picker itself is symmetric)")
        check("(generated" not in full_text, "Collaborate: the old verbose snapshot stamp is gone")
        _no_forbidden_vocab(page, "Collaborate anchor pair page")
        _no_pastel_hexes(page, "Collaborate anchor pair page")
        _no_bare_na_in_hover(page, [".st-key-fig_pulse .js-plotly-plot", ".st-key-fig_fields .js-plotly-plot",
                                    ".st-key-fig_reciprocity .js-plotly-plot"],
                            "Collaborate anchor pair page")

        # --- widths -------------------------------------------------------------
        for width in WIDTHS:
            page.set_viewport_size({"width": width, "height": 900})
            _settle(page, 900)
            scroll = page.evaluate("document.documentElement.scrollWidth")
            inner = page.evaluate("window.innerWidth")
            check(scroll <= inner + 2, f"Collaborate {width}px: scrollWidth {scroll} <= innerWidth+2 {inner + 2}")
        page.set_viewport_size({"width": 1920, "height": 1080})
        shot_dir = DEFAULT_APP_DIR / "tests" / "ui" / "screenshots"
        shot_dir.mkdir(parents=True, exist_ok=True)
        _settle(page, 800)
        page.screenshot(path=str(shot_dir / "tevu_collab_1920.png"), full_page=True)
        _no_exception(page, "Collaborate (anchor pair, final)")
    except Exception as exc:
        fail_section("Collaborate anchor pair", exc)
    finally:
        page.close()


def check_collab_below_floor_pair(context) -> None:
    """FRESH, standalone session: a real below-floor pair (2 joint works,
    under the pair floor of 5) renders the honest notice -- pulse still
    renders, field/reciprocity/topic breakdowns do not."""
    page = context.new_page()
    page.set_default_timeout(ACTION_TIMEOUT_MS)
    try:
        page.goto(f"{BASE_URL}/Collaborate?pair={BELOW_FLOOR_A_ID},{BELOW_FLOOR_B_ID}",
                  wait_until="domcontentloaded")
        page.wait_for_selector('[data-testid="stSidebarNav"]', state="attached", timeout=ACTION_TIMEOUT_MS)
        _settle(page, 4000)
        body_text = _full_page_text(page)
        check(BELOW_FLOOR_NOTICE_RE.search(body_text) is not None,
              f"Collaborate below-floor pair (floor {PAIR_FLOOR}): the honest notice renders")
        check("The relationship, year by year" in body_text, "Collaborate below-floor pair: pulse still renders")
        check(page.locator('[data-table="collab_fields"]').count() == 0,
              "Collaborate below-floor pair: no field table (never existed even pre-2BR3-floor)")
        check(page.locator(".st-key-fig_fields").count() == 0,
              "Collaborate below-floor pair: the field CHART is absent (below the topic floor)")
        check(page.locator(".st-key-fig_reciprocity").count() == 0,
              "Collaborate below-floor pair: the reciprocity chart is absent (below the topic floor)")
        _no_exception(page, "Collaborate (below-floor pair, standalone session)")
    except Exception as exc:
        fail_section("Collaborate below-floor pair", exc)
    finally:
        page.close()


# ------------------------------------------------------------- crash seed ---

def check_ifremer_crash_seed(app_dir: Path, port: int) -> None:
    """2B-R2-1a, carried forward: the profile that took the app down at gate
    2B-R (Ifremer is both an umbrella AND type-corrected), at all 3 widths,
    reached via the SAME `?seed=` param the app's own qp_seed hydration reads
    (folds into the basket too, per views_find.render()'s own docstring)."""
    base = f"http://127.0.0.1:{port}"
    for width in WIDTHS:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={"width": width, "height": 900})
                page.set_default_timeout(ACTION_TIMEOUT_MS)
                page.goto(f"{base}/Find?seed={CRASH_SEED}", wait_until="domcontentloaded")
                page.wait_for_selector('[role="tab"]', timeout=ACTION_TIMEOUT_MS)
                _settle(page, 3000)
                _no_exception(page, f"Ifremer crash seed {width}px")
                check(page.locator(".st-key-profile .benchup-kpi").count() == N_CARDS,
                      f"Ifremer {width}px: {N_CARDS} cards render")
                body = _full_page_text(page)
                m = IDENTITY_TYPE_CORRECTED_RE.search(body)
                check(m is not None, f"Ifremer {width}px: the inline type correction renders")
                name_href = page.locator(".st-key-profile h3 a").first.get_attribute("href") or ""
                check("openalex.org/works" in name_href, f"Ifremer {width}px: the name links to OpenAlex works")
                check(NO_LONGER_ON_FIND not in body, f"Ifremer {width}px: no separate publication-def link")
                scroll = page.evaluate("document.documentElement.scrollWidth")
                inner = page.evaluate("window.innerWidth")
                check(scroll <= inner + 2, f"Ifremer {width}px: scrollWidth {scroll} <= innerWidth+2 {inner + 2}")
                browser.close()
        except Exception as exc:  # noqa: BLE001
            fail_section(f"Ifremer crash seed {width}px", exc)


# -------------------------------------------------------------- Methods -----

def check_methods_journey(page) -> None:
    _click_nav(page, NAV_METHODS)
    page.wait_for_selector('[data-testid="stExpander"]', timeout=ACTION_TIMEOUT_MS)
    _settle(page, 1500)
    n_sections = page.locator('[data-testid="stExpander"]').count()
    check(n_sections >= METHODS_MIN_SECTIONS, f"Methods: >= {METHODS_MIN_SECTIONS} sections render ({n_sections})")
    body = _full_page_text(page)
    leftover = PLACEHOLDER_RE.findall(body)
    check(not leftover, f"Methods: no unresolved {{placeholder}} text (found {leftover[:5]})")
    _ensure_expander_open_by_text(page, LENS_CODES_TITLE, "text=(C1)")
    _settle(page, 1000)
    concordance_text = _full_page_text(page)
    check(LENS_CODES_TITLE in concordance_text, f"Methods: the {LENS_CODES_TITLE!r} section renders")
    _no_forbidden_vocab(page, "Methods page")
    _no_exception(page, "Methods")


# --------------------------------------------- cross-page persistence -------

def check_narrative_persistence(page) -> dict:
    """2BR3: the ONE sidebar basket/scenario must agree across Compare,
    Collaborate, Methods and back to Find -- read off the SHARED sidebar
    caption every page now renders (`selection.render_sidebar`), not off a
    page-specific mirror."""
    _click_nav(page, NAV_COMPARE)
    _settle(page, 1500)
    n_compare = _sidebar_basket_n(page)
    check(n_compare is not None, f"Compare: sidebar basket count is readable (got {n_compare!r})")

    _click_nav(page, NAV_COLLAB)
    _settle(page, 1500)
    n_collab = _sidebar_basket_n(page)
    check(n_compare is not None and n_compare == n_collab,
          f"Basket: the sidebar count agrees on Compare and Collaborate ({n_compare} vs {n_collab})")

    _click_nav(page, NAV_METHODS)
    _settle(page, 1500)
    n_methods = _sidebar_basket_n(page)
    if n_methods is not None:
        check(n_compare == n_methods,
              f"Basket: the sidebar count agrees on Compare and Methods ({n_compare} vs {n_methods})")
    else:
        # MT (wave 3) owns wiring Methods onto the shared sidebar this round;
        # not this stream's fence -- reported, not asserted, if still absent.
        finding("Methods page: no '{n} of {cap} added' sidebar caption found -- "
                "the shared sidebar (selection.render_sidebar) may not yet be wired onto "
                "Methods this wave (assigned to MT per the SEL ledger row, not TEV-U's fence).")
    _no_exception(page, "Methods (persistence hop)")

    _click_nav(page, "Find")
    _settle(page, 1500)
    n_find = _sidebar_basket_count(page)
    check(n_compare is not None and n_find == n_compare,
          f"Basket: {n_find} items on Find matches the {n_compare} the sidebar reported on Compare")
    return {"n_basket": n_find}


# ------------------------------------------------------------------ main ----

def main() -> int:
    global PORT, BASE_URL
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8611)
    parser.add_argument("--app-dir", type=str, default=None)
    parser.add_argument("--width", type=int, default=1280,
                        help="viewport width for the main journey (spot-widths run separately)")
    args = parser.parse_args()
    PORT = args.port
    BASE_URL = f"http://127.0.0.1:{PORT}"
    app_dir = Path(args.app_dir).resolve() if args.app_dir else DEFAULT_APP_DIR

    server = _start_server(app_dir, PORT)
    profile_expect: dict = {}
    try:
        if not _wait_for_port(PORT, timeout=90.0):
            check(False, f"server did not open port {PORT} within timeout")
            return 1

        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(viewport={"width": args.width, "height": 900},
                                          accept_downloads=True)
            page = context.new_page()
            page.set_default_timeout(ACTION_TIMEOUT_MS)

            def _run_profile_panels() -> None:
                profile_expect.update(check_profile_and_panels(page) or {})

            sections = [
                ("Menu", lambda: check_menu(page)),
                # Find dropdown over basket runs FIRST -- it needs a
                # genuinely fresh (never-auto-selected) seed_id state; see
                # that check's own docstring for why the order is load-
                # bearing, not cosmetic.
                ("Find dropdown over basket", lambda: check_find_dropdown_over_basket(page)),
                ("Sidebar search + basket", lambda: check_sidebar_search_and_basket(page)),
                ("Controls placement", lambda: check_controls_placement(page)),
                ("Profile / panels", _run_profile_panels),
                ("Bonus year axis", lambda: check_bonus_year_axis(page)),
                ("SI value labels", lambda: check_si_value_labels(page)),
                ("A11 tab overflow", lambda: check_tab_overflow_a11(page)),
                ("Benchmark lens guide", lambda: check_benchmark_lens_guide(page)),
                ("Tables / export", lambda: check_tables_and_export(page)),
                ("Settings", lambda: check_settings(page)),
                ("Type filter clear", lambda: check_type_filter_clear(page)),
                ("Undefined lens", lambda: check_undefined_lens(page, app_dir)),
                ("Narrative persistence", lambda: check_narrative_persistence(page)),
                ("Methods journey", lambda: check_methods_journey(page)),
            ]
            for name, fn in sections:
                try:
                    fn()
                except Exception as exc:  # noqa: BLE001
                    fail_section(name, exc)

            page.close()
            context.close()

            # Standalone, deliberately-fresh sessions: each asserts NO
            # persistence claim, each gets its own browser context.
            fresh_ctx = browser.new_context(viewport={"width": args.width, "height": 900},
                                            accept_downloads=True)
            check_find_dropdown_requires_explicit_pick(fresh_ctx)
            check_deeplink_hydration(fresh_ctx, view="compare", page_path="Compare", param="compare",
                                     ids=COMPARE_TRIO, n_slots=COMPARE_CAP)
            check_deeplink_hydration(fresh_ctx, view="collab", page_path="Collaborate", param="pair",
                                     ids=(STRASBOURG_ID, CNRS_ID), n_slots=COLLAB_CAP)
            check_compare_page(fresh_ctx)
            check_collab_anchor_pair(fresh_ctx)
            check_collab_below_floor_pair(fresh_ctx)
            fresh_ctx.close()
            browser.close()

        check_ifremer_crash_seed(app_dir, PORT)
    finally:
        _stop_server(server)

    failed = [m for ok, m in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)} of {len(RESULTS)} checks passed")
    if FINDINGS:
        print(f"\n{len(FINDINGS)} FINDING(S) for the manager (reported, not fixed):")
        for f in FINDINGS:
            print(" -", f)
    if failed:
        for m in failed:
            print("FAILED:", m)
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())

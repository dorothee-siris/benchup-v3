# Playwright smoke test (`tests/ui/smoke.py`)

Drives the LIVE Streamlit server (`streamlit run Menu.py`) headlessly with
Playwright. This is the one test in the suite that proves **cross-page
persistence** actually works in a real browser session -- `pytest`'s
`AppTest` harness (Stream G) never leaves a single script run, so it cannot
exercise a Menu&harr;Find hop at all.

## Run it

```
cd app
set PYTHONIOENCODING=utf-8
"<repo>/envs/env-app/Scripts/python.exe" tests/ui/smoke.py --port 8611
```

Exit 0 iff every check passes; one `PASS:`/`FAIL:` line per check, a summary
count, and a list of failed checks at the end. The server is always started
as a foreground-waited subprocess and always terminated in a `finally` block
-- no orphan `streamlit` process is ever left running (`tasklist | findstr
streamlit` is empty once the script returns, in EITHER exit path).

`--app-dir <path>` points the same script at a different `app/` root (a
throwaway copy) instead of the checkout the script itself lives in --
this is how the two non-vacuity proofs below run without ever touching the
real repo.

## What each check proves

| Section | What it proves |
|---|---|
| Menu | The landing page renders: a heading, the `.st-key-nav_cards` container, >=3 cards, the Find card is a live `st.page_link` (not greyed "Phase 2B"), no exception. |
| Find search | A real sidebar nav click (never `page.goto`) reaches Find; typing "gdansk" + Enter populates the results selectbox; picking the first result loads the University of Gdansk seed card (heading contains "Gda"); the default tab count is exactly 10 (Overview + 8 default lenses + Aspirational) -- C1/L7 are OFF by default. |
| Basket | The sidebar "add a comparator" flow (search box -> results selectbox -> Add button) adds Sorbonne then Bologna; the basket panel lists exactly 2 items (counted via the `[class*="st-key-rm_"]` remove buttons, one per item -- never by reading `st.dataframe` text, which is a canvas grid). |
| Settings | Switching the depth radio to its max option changes the depth caption; switching the tree selectbox to "original" and turning the L7 toggle on adds the L7 tab (tab count 11); the "Filtered by..." strip appears and literally names `tree = original` and `depth = 50` (`lib/copy.py`'s `STRIP_TREE`/`STRIP_DEPTH` templates). |
| **Persistence** (load-bearing) | After Menu->Find->Menu->Find (4 real sidebar-nav-link hops from the settings state above): the basket still lists 2 items, the L7 tab is still present (tab count 11), the seed card heading is still "Gda...", and the strip still names `tree = original` and `depth = 50`. The SAME 5 assertions run once after just 2 hops (a second-visit **re-mount** check -- a bug that only appears the second time a page mounts, e.g. a widget id collision, would pass a first-visit-only test and is a real, previously-observed failure mode) and once more after all 4. |
| Type filter | Selecting "education" in the type multiselect makes the strip name `type = ...education...`; clearing it (the tag's own close icon, or a keyboard Backspace fallback) makes the strip stop naming it. |
| Undefined lens | A helper (`_find_undefined_l2f_seed`) scans institutions smallest-`total_full_2020_2024`-first through `lib.engine.rank_all` until it finds one whose L2f ranking is `undefined` (found this run: Transport and Telecommunication Institute, I24568809) -- searched for through the same seed search box, its L2f tab shows `copy.UNDEFINED_LENS_TEMPLATE`'s fixed wording ("... is undefined for this seed: ..."). |
| Screenshots | Menu and Find (Gdansk seed) at 1920/1280/390 px, each asserting `document.documentElement.scrollWidth <= window.innerWidth + 2` (no horizontal overflow) before the screenshot is written to `tests/ui/screenshots/smoke_{menu,find}_<width>.png`. At 390 px the sidebar nav is Streamlit's own collapsed/mobile drawer -- opened via `[data-testid="stSidebarCollapsedControl"]` before any nav click. |

Every selector is locale-independent: `.st-key-<key>` classes from the
page's own keyed widgets/containers (`app/lib/views_find.py`, `Menu.py`),
`[role="tab"]`, `[role="option"]`, `[data-testid="stRadioOption"]`,
`[data-testid="stSidebarNav"]`, `[data-testid="stException"]`. Text is read
via `textContent` (not `innerText`, which is empty inside a Streamlit tab
panel that is not the currently active one -- `st.tabs` runs every tab's
body every rerun, so the content exists in the DOM regardless) and only to
**assert** content, never to locate an element -- and never against
`st.dataframe`, which renders a canvas grid with no real per-cell text
nodes (the basket count, the seed heading and the strip are all read from
plain DOM elements instead).

## DOM facts (Streamlit 1.61.1, measured by Stream E/A, reused here)

- Tabs are `[role="tab"]` inside `[data-testid="stTabs"]` -- there is **no**
  `[data-baseweb="tab"]`.
- A keyed checkbox (`c1_on`, `l7_on`) = the first `label` under
  `.st-key-<key>`.
- Radio options (`depth`) = `[data-testid="stRadioOption"]` scoped under
  `.st-key-depth`; the widget's own label is a separate
  `label[data-testid="stWidgetLabel"]`.
- A multiselect (`f_types`) is opened via `.st-key-f_types input` +
  `.fill(...)`, then a `[role="option"]` is clicked (never a blind Enter
  when a SPECIFIC value is wanted -- Enter alone selects whatever the
  dropdown happens to highlight first). Clearing a selected tag: the tag's
  own `[data-baseweb="tag"]` close icon, falling back to a keyboard
  Backspace with the input focused and empty.
- A selectbox (`tree`, `seed_pick`, `basket_pick`) is opened by clicking
  `.st-key-<key> [data-baseweb='select']` (falling back to the container
  itself); its options are `[role="option"]`, rendered in a **portal** at
  the end of `<body>` -- so once a dropdown is open, a GLOBAL
  `page.locator('[role="option"]')` finds it (only one dropdown is ever
  open at a time).
- Captions are `[data-testid="stCaptionContainer"]`; tab-panel bodies are
  `[role="tabpanel"]` -- both must be read with `textContent`, never
  `innerText` (see above).
- Exceptions render as `[data-testid="stException"]`.
- The sidebar page navigation is `[data-testid="stSidebarNav"]` with one
  `a` per page (`data-testid="stSidebarNavLink"`). **Click that link for
  every Menu<->Find hop -- never `page.goto()` for a persistence check**:
  `goto` tears down and recreates the browser's WebSocket session, silently
  resetting exactly the state a persistence test exists to catch, and
  produces a FALSE FAILURE (Lorraine Phase 2 `tests/ui/smoke.py`; Portfolio
  Mapping `INSPECTION_PLAYBOOK.md` "Known pitfalls"). `goto` is only used
  here for the very first page load of a run (a fresh/standalone load is
  exactly what that is).
- At a narrow (mobile) viewport the sidebar -- and its nav -- collapses
  behind `[data-testid="stSidebarCollapsedControl"]`; open it before
  clicking a nav link. The collapsed drawer can also position its links via
  a CSS transform that puts Playwright's own "is it inside the viewport"
  geometry check off, even once scrolled into view and visibly clickable --
  the fallback is `link.evaluate("el => el.click()")` (a real DOM click on
  the exact element), never a `goto`.
- `st.dataframe` is a canvas grid: no real text nodes for cell values.
  Row-level facts are read from captions/keyed containers/CSV, never from
  the table.
- The server's own stdout MUST be redirected to `DEVNULL` (or a log file),
  never a `PIPE`: every rerun logs a `use_container_width` deprecation per
  `st.dataframe` call, which fills an unread pipe buffer and blocks the
  server mid-probe (looks exactly like a hang).

## The two non-vacuity proofs

Both run against a **throwaway copy** of `app/` (never the real repo),
built once with:

```
robocopy "<repo>/app" "<scratch>/h_copy" /E /XD "tests\ui\screenshots" ".git" "__pycache__" /NFL /NDL /NJH /NJS /NC /NS /NP
```

(90 MB copy warning per BUILD_PLAN's data note is normal and expected --
the copy needs the real parquet data to run at all.)

### Proof (a): remove the basket re-seed -> the basket checks FAIL

The brief's literal target -- the single `state.ensure()` call at the top
of `pages/1_dY"OSJ_Find.py` -- turned out to be **inert on its own**: `Menu.py`
calls `state.ensure()` too (verified: removing only Find's own call still
passed 54/54, since Menu already seeds the key before Find is ever
reached), and `state.add`/`remove`/`items` each call `ensure()` again
defensively before touching the list (also verified: removing BOTH page-top
calls together still passed 54/54). The one genuinely load-bearing line is
`ensure()`'s own body -- so the real mutation neuters that:

```python
# lib/state.py, in the throwaway copy only
def ensure() -> None:
    pass  # MUTATION (proof a): basket re-seed removed
```

(with the two page-top `state.ensure()` calls also removed, matching the
docstring's "call at the top of every page" -- belt-and-braces, though the
`ensure()` body edit alone is sufficient and is the one that actually
matters.)

Command:
```
python tests/ui/smoke.py --port 8624 --app-dir "<scratch>/h_copy"
```

Result: **exit 1**, 25 of 54 checks passed. `st.session_state["basket"]` is
never created anywhere now, so the very first read of it
(`_sidebar_basket` -> `state.items()`, on the first Find render) raises a
`KeyError` and Streamlit shows an exception -- breaking the basket, and
everything downstream of it, immediately (a stronger and even more direct
demonstration that the mechanism is load-bearing than a narrower "lost
after a hop" failure would have been). FAIL lines (excerpt):
```
FAIL: Basket: raised TimeoutError: Locator.click: Timeout 30000ms exceeded.
Call log:
  - waiting for locator(".st-key-basket_add button").first
FAIL: Persistence: raised TimeoutError: Locator.text_content: Timeout 30000ms exceeded.
Call log:
  - waiting for locator(".st-key-seed_card h3").first
FAIL: Settings: L7 tab appeared, tab count is 11 (got 0)
FAIL: Type filter: strip names the type filter (strip: '')
```
All three files reverted afterward (`diff` against the source confirmed
clean before proof (b) started).

### Proof (b): remove `persist_state` from depth/tree -> exactly those checks FAIL

```python
# lib/views_find.py, in the throwaway copy only, _sidebar_scenario()
tree = sb.selectbox(..., key="tree")   # **state.PERSIST removed
depth = sb.radio(..., key="depth")     # **state.PERSIST removed
```

Command:
```
python tests/ui/smoke.py --port 8625 --app-dir "<scratch>/h_copy"
```

Result: **exit 1**, 50 of 54 checks passed -- surgically exactly the 4
persistence checks that read depth/tree fail, nothing else:
```
FAIL: Persistence: 2nd Find visit (re-mount check): depth still at max in the strip
FAIL: Persistence: 2nd Find visit (re-mount check): tree still 'original' in the strip
FAIL: Persistence: 3rd Find visit (after 4 hops): depth still at max in the strip
FAIL: Persistence: 3rd Find visit (after 4 hops): tree still 'original' in the strip
```
The basket (a non-widget key, no `persist_state` involved) and the L7 tab
count and the seed selection all still passed at both visits, exactly as
expected: this mutation only touches the two widgets it was applied to.

### Then: the real app, unmutated

```
python tests/ui/smoke.py --port 8611
```
Result: **exit 0**, 54 of 54 checks passed, 6 screenshots written.

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
| Find search | A real sidebar nav click (never `page.goto`) reaches Find; typing "gdansk" + Enter populates the results selectbox; picking the first result loads the University of Gdansk profile (heading contains "Gda"); the default tab count is exactly 10 (Overview + 8 default lenses + Aspirational) -- C1/L7 are OFF by default. |
| Basket | The sidebar "add a comparator" flow (search box -> results selectbox -> Add button) adds Sorbonne then Bologna; the basket panel lists exactly 2 items (counted via the `[class*="st-key-rm_"]` remove buttons, one per item -- never by reading `st.dataframe` text, which is a canvas grid). |
| **Controls placement (R1)** | The sidebar carries ONLY `.st-key-tree` / `.st-key-basis` (scenario) -- `.st-key-depth`, `.st-key-f_types`, `.st-key-c1_on` are absent from `[data-testid="stSidebar"]`. `.st-key-depth`/`.st-key-c1_on`/`.st-key-l7_on` render in the main-area controls row instead (same widget keys as 2A, just relocated -- L16). Opening the `.st-key-postfilters` expander reveals `.st-key-f_types` and `.st-key-f_countries`; typing "Fra" into the country multiselect surfaces an option containing "France" (country NAMES, not codes -- L22). |
| **Profile / panels (R1)** | `.st-key-profile` renders once (replaces the old seed card, L17); the subfield wordcloud renders as a real `<img>`; the six `.st-key-panel_<name>` expanders carry their exact `copy.FIND["PANEL_*"]` header text (icon-ligature prefix stripped, EXACT match -- see non-vacuity proof (b) below for why substring is not enough); the `breakdown_dim` segmented control swaps the chip legend text and both breakdown figures stay visible after the swap; the bonus-year caption is present; opening the Fields panel reveals a live Plotly figure, and its own `sort_fields` radio changes the FIRST rendered y-axis tick label (read from the SVG, `.st-key-fig_fields .ytick text`). |
| **Tables / export (R1)** | A lens tab's ranked table renders (`.st-key-tbl_L0 [data-testid="stDataFrame"]`); its CSV (captured via Playwright's real download API, never a mocked click) has a header containing `total_frac_2020_2024`, `country` and `evidence`, and NO `badge` column (badges moved to the profile header only, L22); the Aspirational tab renders its own table (`.st-key-tbl_aspirational`). |
| Settings | Opening the post-filters expander and selecting "education" in the type multiselect; switching the depth radio to its max option changes the depth caption; switching the tree selectbox to "original" (waited out with a poll, not a blind sleep -- see DOM facts below) and turning the L7 toggle on adds the L7 tab (tab count 11); the "Filtered by..." strip names `tree = original`, `depth = 50` and `type = ...education...` (`lib/copy.py`'s `STRIP_*` templates) -- all four settings are set here so the persistence check below has something real to lose. |
| **Persistence** (load-bearing) | After Menu->Find->Menu->Find (4 real sidebar-nav-link hops from the settings state above): the basket still lists 2 items, the L7 tab is still present (tab count 11), the profile heading is still "Gda...", and the strip still names `tree = original`, `depth = 50` and the education type filter. The SAME 6 assertions run once at baseline (right after Settings), once after just 2 hops (a second-visit **re-mount** check -- a bug that only appears the second time a page mounts, e.g. a widget id collision, would pass a first-visit-only test and is a real, previously-observed failure mode), and once more after all 4. |
| Type filter clear | The education filter set in Settings is confirmed still active, then cleared (the tag's own close icon, or a keyboard Backspace fallback); the strip stops naming it. |
| Undefined lens | A helper (`_find_undefined_l2f_seed`) scans institutions smallest-`total_full_2020_2024`-first through `lib.engine.rank_all` until it finds one whose L2f ranking is `undefined` (found this run: Transport and Telecommunication Institute, I24568809) -- searched for through the same seed search box, its L2f tab shows `copy.UNDEFINED_LENS_TEMPLATE`'s fixed wording ("... is undefined for this seed: ..."). |
| Screenshots | Menu and Find (Gdansk seed, **one profile panel opened -- R1's own acceptance line**) at 1920/1280/390 px, each asserting `document.documentElement.scrollWidth <= window.innerWidth + 2` (no horizontal overflow) before the screenshot is written to `tests/ui/screenshots/smoke_{menu,find}_<width>.png`. At 390 px the sidebar nav is Streamlit's own collapsed/mobile drawer -- opened via `[data-testid="stSidebarCollapsedControl"]` before any nav click. |

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

### R1 additions (Refinement R1, stream R-H2)

- **`st.segmented_control` (`breakdown_dim`)** renders as a row of real
  `<button>` elements under `.st-key-breakdown_dim` -- click
  `.st-key-breakdown_dim button` by **position** (`nth(0)`/`nth(1)`), never by
  its label text (the two options are "Domain" and "Document type", which are
  `copy.py` strings, not selector material).
- **An `st.expander(..., key=...)` header** is a `<summary>` element whose
  `textContent` is the label PLUS a leading icon-font ligature with no
  separating space or newline -- e.g. `"keyboard_arrow_rightFields"` when
  closed. Comparing a label with a plain substring test (`label in text`) is
  **not enough**: a renamed label that happens to CONTAIN the expected text
  (e.g. `"Fields Overview"` still contains `"Fields"`) silently passes. Strip
  the known ligature strings (`keyboard_arrow_right`, `keyboard_arrow_down`)
  and compare for **equality** instead (see non-vacuity proof (b) below --
  the first version of this exact check was vacuous for exactly this reason,
  caught only by actually running the mutation).
- **A `st.expander`'s body still executes every rerun regardless of its
  visual open/closed state** (documented in `lib/views_find.py`, both for the
  six profile chart panels and for the controls row's `postfilters`
  expander) -- but that visual state resets to the coded `expanded=False`
  default on the very next rerun. A helper (`_ensure_expander_open`) opens a
  keyed expander by checking whether one of its own child widgets
  `.is_visible()` (Playwright's real layout-aware visibility, not DOM
  presence) and clicking the `summary` only if it is not -- called before
  EVERY interaction inside such an expander, never assumed to still be open
  from an earlier click in the same run.
- **A Plotly figure's y-axis tick labels** are plain SVG text nodes:
  `.st-key-fig_<key> .ytick text` (scoped to the `key=` the figure's own
  `st.plotly_chart(..., key=...)` call carries, e.g. `fig_fields`). Reading
  `.first.text_content()` before and after a sort-toggle click is a cheap,
  locale-independent way to prove a chart's *data*, not just its container,
  actually changed.
- **A real file download** (`st.download_button` with a zero-arg callable
  `data=`, per `lib/views_find.py`) is captured with Playwright's own
  download API: wrap the click in `with page.expect_download() as dl_info:`,
  then read `dl_info.value.path()` as a normal local file. This is the CSV's
  own header row, not a mocked click handler -- the honest way to check an
  export's columns per the Assembly Line gotcha list (never assert on a
  `st.dataframe`'s `inner_text`).
- **A scenario switch (`tree` or `basis`) pays a real, one-time cold-build
  cost** the first time THAT (tree, basis) pair is hit in a given server
  process (`build_substrates` measured at ~4.6 s, `progress/R1_E2.md`) --
  every lens tab count and caption change that follows one must be **polled**
  (`_wait_for`, a `page.wait_for_timeout` loop checking the real DOM
  condition) rather than covered by a single fixed `_settle`. A fixed-length
  sleep here is exactly the kind of flake that non-vacuity proof (a) below
  first surfaced as noise before the depth mutation was even applied: it
  reproduced on an UNMUTATED throwaway copy too, purely from cold-start
  timing, and was fixed in `smoke.py` itself (not silenced) before the proof
  was considered clean.
- **The seed identity heading moved**: R1 replaced the old seed card with the
  Profile section (`lib/views_find.py::_render_profile`), so the heading is
  now `.st-key-profile h3` (an `st.subheader`), not `.st-key-seed_card h3`.

## The two non-vacuity proofs (2A originals, Stream H)

Both ran against a **throwaway copy** of `app/` (never the real repo), built
once with `robocopy "<repo>/app" "<scratch>/h_copy" /E /XD "tests\ui\screenshots" ".git" "__pycache__" ...`
(90 MB copy warning per BUILD_PLAN's data note is normal -- the copy needs
the real parquet data to run at all). Result then: basket-removal proof
exit 1 (25/54); `persist_state`-removal-from-depth/tree proof exit 1 (50/54,
exactly the 4 depth+tree persistence checks). Full detail archived in git
history (this section replaced by the R1 proofs below, which exercise the
SAME two mechanisms after R1 moved depth into the main-area controls row and
replaced the seed card with the profile section).

## The two non-vacuity proofs (R1, stream R-H2)

Both run against a **throwaway copy** of `app/` (never the real repo), one
copy per mutation so they cannot interfere with each other:

```
robocopy "<repo>/app" "<scratch>/h2_copy_a" /E /XD "tests\ui\screenshots" ".git" "__pycache__" /NFL /NDL /NJH /NJS /NC /NS /NP
robocopy "<repo>/app" "<scratch>/h2_copy_b" /E /XD "tests\ui\screenshots" ".git" "__pycache__" /NFL /NDL /NJH /NJS /NC /NS /NP
```
(In Git Bash on Windows, `robocopy`'s single-slash switches like `/E` get
mis-parsed by MSYS path translation into a drive letter -- run with
`MSYS_NO_PATHCONV=1` set, and keep the switches single-slash, e.g.
`MSYS_NO_PATHCONV=1 robocopy ... /E /XD ...`.)

### Proof (a): remove `persist_state` from the depth radio ONLY -> exactly the depth persistence checks FAIL

R1 moved `depth` out of the sidebar into the Benchmark section's controls
row (`lib/views_find.py::_controls_row`); `tree`/`basis` stayed in the
sidebar untouched. The mutation targets ONLY the depth radio, so the proof
demonstrates the mechanism is still load-bearing at its new location without
also touching `tree` (unlike the 2A proof, which mutated both together):

```python
# lib/views_find.py, in the throwaway copy only, _controls_row()
depth = st.radio(copy.FIND["DEPTH_LABEL"], DEPTH_OPTIONS, index=0, horizontal=True,
                 help=copy.FIND["DEPTH_HELP"], key="depth")   # **state.PERSIST removed
```

Command:
```
python tests/ui/smoke.py --port 8674 --app-dir "<scratch>/h2_copy_a"
```

Result: **exit 1**, 99 of 101 checks passed -- surgically exactly the 2
depth-reading persistence checks fail, nothing else:
```
FAIL: Persistence: 2nd Find visit (re-mount check): depth still at max in the strip
FAIL: Persistence: 3rd Find visit (after 4 hops): depth still at max in the strip
```
`tree` (untouched), the basket, the L7 tab count and the type filter all
still passed at both visits.

**A genuine flake was found and fixed while proving this, not silenced by
loosening the check.** The first two attempts at this proof also failed
`Settings: L7 tab appeared, tab count is 11 (got 10)` -- reproducible on a
**cold, freshly-copied** `app/` even with NO mutation applied at all (verified
by re-running the same copy again before mutating it). Root cause: switching
`tree` to `"original"` is the first time that (tree, basis) pair is built in
a fresh server process (`build_substrates` costs a measured ~4.6 s cold,
`progress/R1_E2.md`), and the old code followed it with a single fixed
`_settle(page, 3000)` before clicking the L7 checkbox -- too short on a cold
box, so the L7 click could land while the tree-switch rerun was still in
flight. Fixed in `smoke.py` itself: the tree-switch and the L7-toggle are
each now followed by `_wait_for(...)`, a poll on the real tab count, instead
of a blind sleep (see "R1 additions" in the DOM facts above). Re-run against
an unmutated copy confirmed the flake was gone before the proof above was
taken as clean.

### Proof (b): rename one `PANEL_*` label -> exactly the expander-label check FAILS

```python
# lib/copy.py, in the throwaway copy only
"PANEL_FIELDS": "Fields Overview",   # was "Fields"
```

Command:
```
python tests/ui/smoke.py --port 8676 --app-dir "<scratch>/h2_copy_b"
```

Result: **exit 1**, 100 of 101 checks passed -- exactly one check fails:
```
FAIL: Panel 'fields': header label is exactly 'Fields' (got 'keyboard_arrow_rightFields Overview')
```

**This proof caught a vacuous check on its first run and the check was
fixed, not the mutation.** The first version compared with a plain substring
test (`label in text`); since `"Fields"` is a substring of `"Fields
Overview"`, that mutation passed 101/101 -- a vacuous proof. Fixed by
stripping the `st.expander` summary's leading icon-font ligature
(`keyboard_arrow_right`/`keyboard_arrow_down`) and comparing for **exact**
equality instead (see "R1 additions" above); the re-run above is the clean
result under the corrected check.

### Then: the real app, unmutated

```
python tests/ui/smoke.py --port 8678
```
Result: **exit 0**, 101 of 101 checks passed, 6 screenshots written, no
server process left running afterward.

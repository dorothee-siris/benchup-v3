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
| **Controls placement (R1; sidebar labels R2)** | The sidebar carries ONLY `.st-key-tree` / `.st-key-basis` (scenario) -- `.st-key-depth`, `.st-key-f_types`, `.st-key-c1_on` are absent from `[data-testid="stSidebar"]`. `.st-key-depth`/`.st-key-c1_on`/`.st-key-l7_on` render in the main-area controls row instead (same widget keys as 2A, just relocated -- L16). **R2/L29:** the `tree`/`basis` selectboxes show their DISPLAY label ("Repaired taxonomy (best fit, default)" / "Fractional counting"), read off the react-aria ComboBox `input`'s own `value` property, never the internal value ("bestfit"/"frac") anywhere in that string. Opening the `.st-key-postfilters` expander reveals `.st-key-f_types` and `.st-key-f_countries`; typing "Fra" into the country multiselect surfaces an option containing "France" (country NAMES, not codes -- L22). |
| **Profile / panels (R1 layout; R2 tiles/labels/floors/modes)** | `.st-key-profile` renders once; the subfield wordcloud renders as a real `<img>`; **R2/L30-L31:** exactly 8 `.benchup-kpi` tiles, 16 `.benchup-kpi-sub` sublines, and every tile's second subline contains "index median" (the index-baseline reference, `copy.FIND["TILE_BASELINE_SUB"]`); the "Key figures" header renders; the retired coverage line's "ERC-classified share" phrase is nowhere on the page (its items were relocated into panel captions). The six `.st-key-panel_<name>` expanders carry their exact `copy.FIND["PANEL_*"]` header text (icon-ligature prefix stripped, EXACT match -- see non-vacuity proof (b) below for why substring is not enough); **R2/L34:** the Top-subfields panel carries NO `.st-key-sort_subfields` control and its Plotly figure has between 1 and 30 `.ytick` groups; **R2/L36:** every SDG-panel y-tick's `.ytick`-group textContent starts with "SDG"; **R2/L34:** the ERC panel's Plotly figure carries at least one grid tickval on its SI (last `xaxis*`) axis -- the unit grid; **R2/L33:** the frontier panel's `frontier_mode` segmented control (inside the SAME collapsed expander) swaps the scatter's plotted point count, read off the live figure's own `el.data`, never a caption; the `breakdown_dim` segmented control swaps the chip legend text and both breakdown figures stay visible after the swap; the bonus-year caption is present. |
| **Benchmark lens guide (R2/L29)** | The `.st-key-lens_guide` expander's header is exactly "How to read the lenses"; it carries at least 8 `<strong>` lens-name lines (one per shown default lens); the first default-lens tab (`[role="tab"]` index 1, lens `L0`) carries its `copy.LENS_NAMES` text ("L0 · Field overlap"), not a bare code; the Overview's caption points back at the guide ("...see the lens guide above."). |
| **Tables / export (R1)** | A lens tab's ranked table renders (`.st-key-tbl_L0 [data-testid="stDataFrame"]`) -- lens CODES stay the table/CSV key material even though the TAB text now carries the lens's full name; its CSV (captured via Playwright's real download API, never a mocked click) has a header containing `total_frac_2020_2024`, `country` and `evidence`, and NO `badge` column (badges moved to the profile header only, L22); the Aspirational tab renders its own table (`.st-key-tbl_aspirational`). |
| Settings | Opening the post-filters expander and selecting "education" in the type multiselect; switching the depth radio to its max option changes the depth caption; switching the tree selectbox to its **R2 display label** "OpenAlex taxonomy as published" (waited out with a poll, not a blind sleep -- see DOM facts below) and turning the L7 toggle on adds the L7 tab (tab count 11); the "Filtered by..." strip names `taxonomy: OpenAlex taxonomy as published` (R2's `STRIP_TREE` wording, the display label -- never "original"), `depth = 50` and `type: education` (R2's `STRIP_TYPE` wording: a colon, not " = ") -- all set here so the persistence check below has something real to lose. `frontier_mode` and `breakdown_dim` are already off-default from the Profile/panels section above and are deliberately left untouched here (see that section's own docstring). |
| **Persistence** (load-bearing) | After Menu->Find->Menu->Find (4 real sidebar-nav-link hops from the settings state above): the basket still lists 2 items, the L7 tab is still present (tab count 11), the profile heading is still "Gda...", and the strip still names the taxonomy's display label, `depth = 50` and the education type filter. **R2 additions:** the frontier scatter's plotted point count still equals the emerging-mode count captured right after the swap (not the default top-200-by-volume count), and the breakdown pair's chip legend still equals the document-type legend captured right after that swap (not the domain legend) -- both compared against a value this run itself recorded, since neither has a fixed expected literal the way `depth = 50` does. The SAME 8 assertions run once at baseline (right after Settings), once after just 2 hops (a second-visit **re-mount** check -- a bug that only appears the second time a page mounts, e.g. a widget id collision, would pass a first-visit-only test and is a real, previously-observed failure mode), and once more after all 4. |
| Type filter clear | The education filter set in Settings is confirmed still active, then cleared (the tag's own close icon, or a keyboard Backspace fallback); the strip stops naming it. |
| Undefined lens | A helper (`_find_undefined_l2f_seed`) scans institutions smallest-`total_full_2020_2024`-first through `lib.engine.rank_all` until it finds one whose L2f ranking is `undefined` (found this run: Transport and Telecommunication Institute, I24568809) -- searched for through the same seed search box, its L2f tab shows `copy.UNDEFINED_LENS_TEMPLATE`'s **R2 wording** ("L2f cannot be computed for this seed: ..."). |
| Screenshots | Menu and Find (Gdansk seed, **the Top-subfields panel opened**) at 1920/1280/390 px, each asserting `document.documentElement.scrollWidth <= window.innerWidth + 2` (no horizontal overflow) before the screenshot is written to `tests/ui/screenshots/smoke_{menu,find}_<width>.png`. At 390 px the sidebar nav is Streamlit's own collapsed/mobile drawer -- opened via `[data-testid="stSidebarCollapsedControl"]` before any nav click. A viewport-only (non-full-page) `smoke_find_top_1280.png` is captured scrolled to `y=0` right after the seed loads and BEFORE any panel opens (no other screenshot in this suite proves the header/tiles/wordcloud actually render). **R2 (adapted from fix X3's finding I-4):** at 390 px AND 1280 px, `check_subfields_panel_no_overlap` reads the bounding box of every `.st-key-fig_subfields .js-plotly-plot .ytick` GROUP (not `.ytick text` -- see DOM facts below) against the plot's own `.main-svg` box, and FAILS if any tick label starts left of the plot's own left edge or overflows its right edge; a dedicated `smoke_find_subfields_390.png` captures the Top-subfields panel open at the narrowest width. |

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

### R2 additions (Refinement R2, stream R2-H3)

- **A keyed selectbox's CURRENT selection** lives in the react-aria ComboBox
  `input`'s own `value` property, never in the container's `textContent`/
  `inner_text` (measured on this build, same finding `ops/_probe_find.py`
  already recorded: those return the widget LABEL alone). `_selectbox_value`
  reads `.st-key-<key> input`'s `input_value()`. This is what makes the
  negative half of a "the internal value never shows" check meaningful.
- **A Plotly figure mounted inside a COLLAPSED `st.expander` is still fully
  queryable from JS.** `lib/views_find.py`'s own docstring states every panel
  body executes on every rerun regardless of the expander's visual state; this
  file relies on that for the `frontier_mode` control, which now lives inside
  the `panel_frontier` expander: `document.querySelector('.st-key-panel_frontier
  .js-plotly-plot')` finds the scatter and its `.data`/`.layout` are populated
  even while the expander is visually closed (confirmed empirically -- the
  persistence checks read the point count after two real Menu<->Find hops
  with the panel never re-opened, and pass). `_capture_persisted_state` still
  calls `_ensure_expander_open` before reading it, belt-and-suspenders around
  that finding rather than a substitute for it.
- **A wrapped (two-line) y-axis tick label** (`lib/charts.py::wrap_label`,
  R2/L35) renders as separate `<tspan>` children of ONE `<text>` node inside
  its `.ytick` group, not as two sibling `.ytick text` nodes. Reading or
  bounding-box-ing `.ytick text` directly still technically works for a
  single-line label, but the robust, wrap-proof read is the GROUP:
  `.ytick` (not `.ytick text`) for both `.text_content()` (concatenates every
  tspan) and `.bounding_box()` (spans every line). `check_subfields_panel_no_overlap`
  and the SDG-label check both read the group, never the `text` child.
- **The KPI tile grid** (`lib/tiles.py`, R2/L30/L31) is counted via its own
  stable hooks, never a label: `.benchup-kpi` (one per tile, 8 of them) and
  `.benchup-kpi-sub` (two per tile, 16 of them -- the tile's own reference line
  plus the index-baseline line, which always contains the fixed substring
  "index median").
- **Tabs carry a lens NAME, not a bare code** (`copy.LENS_NAMES`, R2/L29):
  `[role="tab"]` index 1 (the first default lens, `L0` per
  `config.yaml`'s `lenses.default` order) reads "L0 · Field overlap" in full.
  Lens-keyed selectors elsewhere on the page (`.st-key-tbl_L0`, `.st-key-dl_L0`,
  `has_text="L2f"` for the undefined-lens tab) are UNCHANGED: the code stays
  the stable identifier for every DOM hook and export column; only the tab's
  own rendered text changed.
- **Two `STRIP_*` wordings changed under R2's copy pass** (easy to miss
  because the OLD text still reads as plausible): `STRIP_TYPE` is now
  `"type: {types}"` (a colon, not `"type = {types}"`), and
  `UNDEFINED_LENS_TEMPLATE` is now `"{lens} cannot be computed for this seed:
  {reason}."` (not "... is undefined for this seed: ..."). Both were caught by
  actually running this file against the real app rather than trusting the R1
  wording forward -- see the first real-app run in "Then: the real app,
  unmutated" below.
- **Panel/tile/lens labels compared for exact text are HARDCODED literals in
  this file** (`PANEL_LABELS`, `TREE_LABEL_*`, `BASIS_LABEL_FRAC`,
  `LENS0_TAB_TEXT`, `LENS_GUIDE_HEADER`), never re-imported from
  `lib/copy.py`: importing the very string a rename would change makes the
  check compare a mutated value against itself and pass vacuously -- the
  reason proof (b) below still works after the R2 rewrite.

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

## The two non-vacuity proofs (R1, stream R-H2; Fix X3 re-gate)

Both ran against **throwaway copies** of `app/` (never the real repo), one
copy per mutation. Proof (a) removed `persist_state` from the depth radio only
(moved by R1 out of the sidebar into the controls row) -> exit 1, 99 of 101
checks passed, surgically exactly the 2 depth-reading persistence checks
failed. Proof (b) renamed `PANEL_FIELDS` to `"Fields Overview"` -> exit 1, 100
of 101, exactly the fields-panel label check failed (its FIRST version used a
substring test and passed vacuously against that same mutation -- fixed to an
exact-equality comparison after stripping the `st.expander` summary's
icon-font ligature, which is what made the proof genuine). The unmutated app
then passed 101/101, and Fix X3's bounding-box + top-of-page additions brought
it to 105/105. Full detail archived in git history (this section condensed by
R2-H3, which re-ran the SAME two mechanisms -- `persist_state` on a
segmented/radio control, and one `PANEL_*` rename -- against the R2 page
below).

## The two non-vacuity proofs (R2, stream R2-H3)

Both ran against **throwaway copies** of `app/` (never the real repo, one copy
per mutation so they cannot interfere with each other), built with:

```
MSYS_NO_PATHCONV=1 robocopy "<repo>/app" "<scratch>/h3_copy_a" /E /XD "tests\ui\screenshots" ".git" "__pycache__" /NFL /NDL /NJH /NJS /NC /NS /NP
MSYS_NO_PATHCONV=1 robocopy "<repo>/app" "<scratch>/h3_copy_b" /E /XD "tests\ui\screenshots" ".git" "__pycache__" /NFL /NDL /NJH /NJS /NC /NS /NP
```
(In Git Bash on Windows, `robocopy`'s single-slash switches like `/E` get
mis-parsed by MSYS path translation into a drive letter -- run with
`MSYS_NO_PATHCONV=1` set. Robocopy's own exit code `1` means "files copied
successfully", not failure.)

### Proof (a): remove `persist_state` from the `frontier_mode` control ONLY -> exactly its persistence checks FAIL

R2/L33 added `frontier_mode`, a `st.segmented_control` INSIDE the (collapsed
by default) `panel_frontier` expander -- a different widget TYPE and a
different DOM location from R1's depth-radio proof, so this demonstrates the
persistence mechanism is load-bearing there too:

```python
# lib/views_find.py, in the throwaway copy only, _panel_frontier()
st.segmented_control(copy.FIND["FRONTIER_MODE_LABEL"], [mode_top, mode_emerging],
                     default=mode_top, required=True, key="frontier_mode")   # **state.PERSIST removed
```

Command:
```
python tests/ui/smoke.py --port 8731 --app-dir "<scratch>/h3_copy_a"
```

Result: **exit 1**, 129 of 131 checks passed -- surgically exactly the 2
frontier-mode-reading persistence checks fail, nothing else:
```
FAIL: Persistence: 2nd Find visit (re-mount check): frontier_mode still shows its off-default (emerging) point count (expected 488, got 168)
FAIL: Persistence: 3rd Find visit (after 4 hops): frontier_mode still shows its off-default (emerging) point count (expected 488, got 168)
```
The baseline capture (taken right after the swap, before any hop) still
reads 488 and passes, as expected -- only a real Menu<->Find hop resets an
un-persisted widget to its coded default. `tree`, `depth`, `L7`, the type
filter, the basket and `breakdown_dim` (untouched by this mutation) all still
passed at both visits.

### Proof (b): rename `PANEL_SUBFIELDS` -> exactly the label check FAILS

```python
# lib/copy.py, in the throwaway copy only
"PANEL_SUBFIELDS": "Top {n} subfields overview",   # was "Top {n} subfields"
```

Command:
```
python tests/ui/smoke.py --port 8732 --app-dir "<scratch>/h3_copy_b"
```

Result: **exit 1**, 130 of 131 checks passed -- exactly one check fails:
```
FAIL: Panel 'subfields': header label is exactly 'Top 30 subfields' (got 'keyboard_arrow_rightTop 30 subfields overview')
```
This confirms the R1 fix (hardcoded literal + exact-equality comparison,
never a re-import of the string under test) still holds after the R2 rewrite:
`SUBFIELDS_TOP_N = 30` is filled into the HARDCODED expected string in
`smoke.py` itself, so the app's own (mutated) `PANEL_SUBFIELDS` template
never gets a chance to grade its own homework.

### Then: the real app, unmutated

```
python tests/ui/smoke.py --port 8722
```
Result: **exit 0**, 131 of 131 checks passed, 8 screenshots written, port
`8722` showed only `TIME_WAIT` rows afterward (no `LISTENING`), no orphan
`python.exe`/`streamlit` process left running.

The first attempt against the real app (port 8721) surfaced two genuine
wording mismatches between this file's inherited-from-R1 expectations and
R2-C's actual copy pass -- `STRIP_TYPE` ("type: ..." not "type = ...") and
`UNDEFINED_LENS_TEMPLATE` ("cannot be computed for this seed" not "is
undefined for this seed") -- both real app-side changes this file had not
caught up with, not flakes: 125 of 131 passed, all 6 failures traced to those
two strings, fixed in `smoke.py` (never in the app), and the clean 131/131
re-run above is the result under the corrected checks.

## Phase 2B additions (BUILD_PLAN_2B.md Stream H): the full four-page journey

After every check above still passes, the same run continues on the SAME
page/session (never a fresh `browser.new_page()`, which would open a new
WebSocket session with an EMPTY basket -- the same false-failure a
`page.goto()` produces, module docstring) through a second, realistic
journey: clear the basket, re-search Gdansk, add the seed's own top-3 L1
(subfield-overlap) peers plus the seed itself (basket = 4), walk that set
through Compare (strip, legend, figures, the frontier Layout control, the
impact floor toggle, the xlsx workbook, the deep link, reorder, remove),
hand off a picked pair to Collaborate with a real button click (an in-session
`st.switch_page` hop since Fix X-2B, not the `link_button` this journey
originally found -- see the DOM-fact bullet below), walk Methods, prove
tree/basis/basket persistence across all FOUR pages with real sidebar-nav
hops (Methods included, since Fix X-2B also gave it the sidebar Compare/
Collaborate already had), and screenshot Compare/Collaborate/Methods at
width. The genuine, real-app total is now **194 of 194** (131 R2 checks + 63
Phase 2B / Fix X-2B checks: the original 58 the journey shipped with, plus 5
Fix X-2B added to prove the hand-off keeps the session and Methods carries
the sidebar).

### New DOM facts (Streamlit 1.61.1)

- **`st.selectbox` is a react-aria `ComboBox`, not a BaseWeb select** --
  `_open_select`'s `[data-baseweb='select']` locator has always missed on
  this build (0 count) and its existing fallback (click the widget's own
  `.st-key-<key>` container) is what actually opens it. That fallback click
  reliably opens the listbox the FIRST time a given widget key is used in a
  script run, but a SECOND, already-focused round on the SAME widget (e.g. a
  second sequential name typed into the sidebar's `basket_query`/
  `basket_pick` pair, immediately after a first successful add) can leave
  `aria-expanded="false"` after an IDENTICAL click -- reproduced in
  isolation (add "Sorbonne", then search "University of Warsaw" in the same
  box: the second click opens nothing; `page.keyboard.press("ArrowDown")`
  recovers it every time, since ArrowDown is react-aria's own
  keyboard-accessible way to open a focused combobox). `_open_select` now
  tries the click, waits a SHORT 3 s for `[role="option"]`, and falls back
  to `ArrowDown` + the full `ACTION_TIMEOUT_MS` wait only if the click alone
  didn't open it -- this was a real, deterministic bug (reproduced twice
  identically, not a flake) that silently truncated the ORIGINAL R2
  "Basket" section too (adding Sorbonne then Bologna) whenever the second
  add landed on an already-focused widget; fixing it here benefits every
  section, old and new.
- **FIXED (Fix X-2B, progress/2B_X.md) -- ORIGINAL FINDING, kept for the
  record: `st.link_button`'s `<a href>` is a REAL browser navigation, not
  Streamlit's own SPA page-link routing.** The Compare-to-Collaborate
  hand-off (2B-8) used to be a `link_button` (`st.page_link` cannot carry a
  query string). Clicking it behaved like `page.goto()` in the one respect
  that matters: it dropped the current WebSocket session, so a brand-new
  Collaborate session started with an EMPTY basket -- the `?pair=` query
  string was the ONLY thing carrying the pair across that hop. Proof (a)
  below (renaming the query key, run against the PRE-FIX codebase) shows the
  failure mode this produced: not "the wrong pair", but NO dataframe at all
  within the timeout, because the fallback candidate list was then also
  empty.

  **The fix**: the hand-off is now a plain `st.button` (`key="cmp_handoff_open"`)
  that stashes the chosen pair in `st.session_state["pair"]` -- a plain,
  non-widget key, the basket's own idiom -- and calls
  `st.switch_page(COLLAB_PAGE)`, the SAME client-routed, session-preserving
  navigation `st.page_link` and the sidebar nav already use (never a new tab:
  no `context.expect_page` is needed any more). `views_collab._pair_picker`
  reads and consumes that key FIRST, ahead of the `?pair=` query and the
  basket order. `check_handoff` below locates the button by its `key`
  (`.st-key-cmp_handoff_open button`), never by an `href` -- there is no
  anchor to read any more -- and reads the pair off the SAME printed
  `?pair=` deep-link text the old code also printed alongside itself (that
  copyable text is unchanged by the fix; only the CLICK's own mechanism is).
  The check now also asserts THE POINT OF THE FIX directly: the sidebar
  basket count and the tree selection read the same on Collaborate as they
  did on Compare a moment before the click -- on the old bug this would have
  found an empty basket and the default tree.
- **The Compare page's per-institution reorder/remove buttons** (`st.button`
  keyed `cmp_up_{iid}` / `cmp_down_{iid}` / `cmp_rm_{iid}`) are found by
  PARTIAL class match on the stable key PREFIX, never the id itself (which
  the test does not otherwise need to know): `[class*="st-key-cmp_down_"]
  button` (`.first` is the FIRST-rendered row, i.e. the reader's own current
  first institution) -- the same idiom `_basket_count` already uses for
  `rm_{iid}`.
- **Two `st.code` deep links can coexist on Compare** (`?compare=...` from
  the selection block, `?pair=...` from the pair hand-off, once >= 2
  institutions are compared) -- read the right one by filtering
  `[data-testid="stCode"]` with `has_text="?compare="` / `has_text="?pair="`,
  never by DOM position or index.
- **Compare's `st.segmented_control`s** (`cmp_frontier_form`: Layout,
  facets/overlay; the existing `frontier_mode`/`breakdown_dim` idiom from R2
  applies unchanged) render as a row of real `<button>` elements under
  `.st-key-<key>`, clicked by POSITION (`nth(0)`/`nth(1)`). Its
  `st.radio(horizontal=True)` sibling (`cmp_impact_floor`) is
  `[data-testid="stRadioOption"]` scoped under `.st-key-cmp_impact_floor`,
  same idiom as R1's `depth` radio.
- **A downloaded `.xlsx` is opened with `openpyxl.load_workbook(io.BytesIO(raw))`**
  after a real `page.expect_download()` click (`.st-key-dl_workbook button`)
  -- `book.sheetnames` is then plain Python, checked the same honest way the
  CSV header is (never a canvas read).
- **Compare's read-only basket mirror carries NO `rm_{iid}` buttons** (only
  Find's OWN editable list does), so `_basket_count` (which counts those
  buttons) cannot see the basket size on Compare/Collaborate. Both pages
  share the exact same `copy.FIND["BASKET_COUNT"]` sidebar caption template
  (`"{n} of {cap} added"`) as Find, so `_sidebar_basket_n` reads it there
  with a regex instead.
- **FIXED (Fix X-2B) -- ORIGINAL FINDING, kept for the record:
  `views_methods.render()` called neither `_sidebar_scenario()` nor
  `_sidebar_basket()`** -- the Methods page's sidebar carried ONLY
  Streamlit's own page nav, no tree/basis selects and no basket count, a
  real gap from an assumption in this stream's own brief ("tree and basis...
  are the sidebar values on Compare, Collaborate AND Methods"). Flagged as
  `needs_change` for stream M/S, not silently worked around, and closed by
  Fix X-2B: `views_methods.render()` now calls both, read-only, exactly as
  Collaborate does. `check_narrative_persistence` verifies tree/basis/basket
  on all THREE downstream pages now, Methods included.
- **The seed's own L1 (subfield-overlap) ranking CSV** (`.st-key-dl_L1
  button`, downloaded the same honest way as the L0 CSV check above) is
  where this journey's 3 "real candidates" come from (`display_name` +
  `institution_id` columns, `lib/exports.py`'s own `_COLUMNS`) -- added to
  the basket through the SAME sidebar `basket_query`/`basket_pick`/
  `basket_add` flow as any other name, never through the ranked table's own
  row-selection checkbox (`st.dataframe(..., selection_mode="multi-row")`),
  which is a canvas grid this file's own rule already forbids clicking into
  by pixel position.

### The two non-vacuity proofs (Phase 2B, Stream H)

Both ran against **throwaway copies** of `app/` (never the real repo, one
copy per mutation), built with the same `MSYS_NO_PATHCONV=1 robocopy ...`
idiom the R2 proofs above use. **Proof (a) below ran against the PRE-FIX
`link_button` codebase and is kept as the historical record of the bug this
stream's finding led to Fix X-2B fixing** -- the same mutation against
today's code would not reproduce this failure mode, because the id-carrier
`_pair_picker` actually reads first is `st.session_state["pair"]`, not the
printed `?pair=` deep-link text `selection.deeplink` builds (renaming that
string's own query key, which is all this mutation does, would now change
only what a shared link outside the session looks like, never what the
in-session button click itself hands to Collaborate). The regression guard
for the CURRENT mechanism is `check_handoff`'s own "THE POINT OF THE FIX"
assertions -- the basket count and the tree selection surviving the hop --
documented in the DOM-facts bullet above, not a fresh mutation proof.

**Proof (a) (historical, pre-fix): rename the `pair` query key `_handoff`
built the hand-off link with (`views_compare.py`, `"pair"` -> `"duo"`) ->
the hand-off checks fail, nothing else.**

```
python tests/ui/smoke.py --port 8645 --app-dir <scratch>/h_copy_a
```
Result: **exit 1**, 183 of 185 checks passed (4 fewer TOTAL checks were even
attempted than the clean 189, because the mutation makes the hand-off
section fail earlier than it otherwise would -- see below):
```
FAILED: Compare: the hand-off link names two distinct ids ('/Collaborate?duo=I34250744,I40413290')
FAILED: Journey: hand-off to Collaborate: raised TimeoutError: Page.wait_for_selector: Timeout 30000ms exceeded.
  - waiting for locator("[data-testid=\"stDataFrame\"]") to be visible
```
Every one of the other 183 checks passed unchanged, including every OTHER
Compare check (strip, legend, figures, Layout control, impact floor,
workbook, deep link, reorder, remove) and Methods/persistence/widths after
it. The failure is more total than "shows the wrong pair": clicking a
`link_button` is a REAL navigation that drops the session (see the DOM fact
above), so Collaborate's fallback candidate list depends ENTIRELY on the
query string; with the key renamed to `duo`, `query["pair"]` is `None` and
the fresh session's basket is empty too, so `_candidates()` returns nothing,
`_pair_picker` never gets past `EMPTY_NO_PAIR`, and no `st.dataframe` ever
mounts -- exactly the load-bearing claim 2B-8/A11 makes about the query
string being the one thing that survives the hop, falsified on purpose and
caught by name.

**Proof (b): drop the workbook's first (Methods) sheet in `exports_xlsx.py`'s
`workbook_bytes` -> exactly the Methods-sheet check fails, nothing else.**

```python
# lib/exports_xlsx.py, in the throwaway copy only
items = list(sheets.items() if hasattr(sheets, "items") else sheets)
items = items[1:]  # MUTATION: drop the workbook's first (Methods) sheet
```
Command:
```
python tests/ui/smoke.py --port 8646 --app-dir <scratch>/h_copy_b
```
Result: **exit 1**, 188 of 189 checks passed -- exactly one failure:
```
FAILED: Compare: the workbook carries a 'Methods' sheet (['Fields', 'Subfields', 'ERC panels', 'SDG profile', 'Frontier positioning', 'Frontier topics', 'Impact overall', 'Impact by subfield', 'Trends', 'Coverage'])
```
Note the `>= 8 sheets` floor check (`XLSX_MIN_SHEETS`) does NOT fail here --
dropping exactly one of 11 sheets still leaves 10, which clears the floor.
The brief's "sheet-count check" is this Methods-sheet-PRESENCE check in
practice: it is the one that actually moves when a sheet goes missing, and
it is the one this proof shows moving, alone.

### Then: the real app, unmutated (Phase 2B, then Fix X-2B)

```
python tests/ui/smoke.py --port 8644
```
Result (Stream H, pre-fix): **exit 0**, 189 of 189 checks passed, all Phase
2B screenshots written (`smoke_compare_{1920,1280,390}.png`,
`smoke_collab_1280.png`, `smoke_methods_1280.png`), port clean afterward, no
orphan `python.exe`/`streamlit` process left running.

Re-run after Fix X-2B (`python tests/ui/smoke.py --port 8678`): **exit 0**,
**194 of 194** checks passed (the 5 new ones are the hand-off's session
checks and the Methods sidebar's persistence checks -- see the DOM-facts
bullets above), same screenshots, port clean.

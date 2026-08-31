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
-- no orphan `streamlit` process is ever left running.

`--app-dir <path>` points the same script at a different `app/` root (a
throwaway copy) instead of the checkout the script itself lives in -- this is
how the non-vacuity proofs below run without ever touching the real repo.

## Phase 2B-R2 re-cut (BUILD_PLAN_2BR2.md Stream H2)

Re-cut for the crash fixes, colour system, Compare rationalisation and
Collaborate rebuild. New/changed this round:

- **Find (2B-R2-1a/6/7/8).** The Ifremer crash seed (umbrella AND
  type-corrected, the profile that took the app down at gate 2B-R) is now its
  own dedicated, standalone check at all three widths -- the inline
  `"<type>* (was: <type>)"` correction with the `*`, and only the `*`, in a
  reddish colour; the retired second badge stays gone. The profile's cards
  column is a SIX-card 2x3 grid (was four): title-first anatomy (name, then a
  bigger bold value, then one small line) proven structurally via computed
  font-size/weight, not by string-matching a label; the Publications card
  carries the fractional-counting NOTE, the other five carry the
  index-baseline line; the institution NAME is the OpenAlex link; the
  separate "What counts as a publication" link is gone. The SI outer-end
  value label is proven fully inside the plot with a real bounding-box check
  (not a DOM-presence check) on Ifremer's own worst-measured panel, at the
  widths the 2B-R2-7 padding fix actually targets (1280/1920 -- 390px keeps a
  pre-existing, documented, unrelated crowding issue).
- **Compare (2B-R2-3/4/5/8/9/10/13).** The metric selector's exact vocabulary
  is asserted per level (Share/Specialisation/PP/SDG-tagged/Dynamics
  everywhere, "Volume" only where a level defines one, the retired
  "Publications in the world top decile" TAB nowhere); every option the
  subject selector offers is actually clicked and redrawn (the 2B-R lesson);
  row order is read off the DRAWN y-axis ticks and proven IDENTICAL between
  two metric tabs (the load-bearing check), then proven to actually re-rank
  under the "Largest first" toggle and restore under "By subject area";
  volume gutters are proven to carry a number on (almost) every row; the
  low-volume dagger glyph is hunted down on the BAR's own value-label text
  (not the y-tick text, which never carries it -- see DOM facts below);
  reference-line shape counts are compared across Share/Dynamics/PP; the
  frontier map's pool selector and domain-colour toggle are proven to change
  the plotted topic-set SIGNATURE and the map's OWN legend (scoped past the
  unrelated "who holds the shared frontier" chart, which carries the same
  "held by more than one" chip in a legend of its own); the plain-language
  "Not shown here, and why" disclosures and a page-wide forbidden-vocabulary
  scan (no "2B-R", "artefact", "pipeline", stream code) run on the journey
  page.
- **Collaborate (2B-R2-11/12/13).** New section order (pulse -> field
  breakdown chart+table -> shared topics -> untapped -> link-outs), driven on
  a manager-verified anchor pair (Universite de Strasbourg x CNRS) as its own
  standalone, deterministic check -- never on the journey's hand-off pair,
  which is built from an arbitrary L1 ranking and could legitimately land
  below the floor. Proves: the field-breakdown chart carries real values and
  is COMPARISON-grey (no institution hue reaches the pair's own chart); every
  field/topic row carries a domain chip and a dynamics arrow that varies row
  to row; every shown row's `.bu-link` carries a live pair+taxon OpenAlex URL
  (both institutions ANDed with a repeated filter key, plus the taxon filter);
  the topic-depth and untapped-depth sliders change their own table's row
  count; the two "X does not publish in" gap tables and their CSV download
  are GONE, disclosed instead through the shared "Not shown here, and why"
  line; the CSV downloads (fields/topics/untapped) match the published column
  contracts. The below-floor pair (Strasbourg x Bavarian Academy of Sciences
  and Humanities, 2 joint works, floor now 5) shows the honest notice and
  renders ONLY the untapped/adjacent tables -- field and topic breakdowns are
  absent, since they are floor-gated and untapped is not.
- Everything else (Menu, Find search-on-validate, basket, controls placement,
  A11 tab overflow, benchmark tables/export, institution-link popup,
  settings, persistence, undefined lens, Methods) is unchanged in shape from
  2B-R and re-verified, not re-designed, this round.

## What each check proves

| Section | What it proves |
|---|---|
| Menu | The landing page renders: a heading, the `.st-key-nav_cards` container, exactly 4 live `st.page_link` cards (Find peers, Compare, Collaborate, How it is built), no exception. |
| Find search (A12) | The data caption reads "`<n>` institutions &middot; data from `<date>`"; typing "gdansk" + Enter opens the results selectbox but renders **no profile and no tabs** until a pick is made; picking the first result loads the University of Gdańsk profile; the default tab count is exactly 10. |
| Basket | The sidebar "add a comparator" flow adds Sorbonne then Bologna; the basket panel lists exactly 2 items. |
| Controls placement | The sidebar carries ONLY `.st-key-tree` / `.st-key-basis`; depth/C1/L7/post-filters render in the main-area controls row; the scenario selectboxes show their DISPLAY label, never the internal value; the country multiselect shows names. |
| Profile / cards (2B-R2-6/7/8) | `.st-key-profile` renders once; the wordcloud renders as a real `<img>`; exactly 6 `.benchup-kpi` cards carrying the ruled labels (title-first, proven via computed font-size/weight of the card's own first two children); 6 `.benchup-kpi-sub` lines, of which exactly 5 read "index median ..." and exactly 1 (Publications) carries the `.benchup-kpi-value2` fractional-counting note; the institution name links to its own OpenAlex works, the separate "What counts as a publication" link is gone; the six chart panels carry their exact labels; Top subfields/topics carry no sort control and are cut at 30; SDG y-ticks all start with "SDG"; the frontier panel's mode control changes the plotted TOPIC SET; the breakdown pair's segmented control swaps the chip legend. |
| Bonus year axis | "2025*" is present in the yearly breakdown figure's own `x` data. |
| SI value labels | The fields/subfields/ERC panels' SI marker carries a non-empty outer-end text label, `showgrid` is `false`. |
| Ifremer crash seed (2B-R2-1a/7, standalone) | At 1920/1280/390px, fresh sessions: no exception; 6 cards; the inline `"<type>* (was: <type>)"` correction renders with the `*` as its own, reddish-coloured span; the name links to OpenAlex works; no separate publication-definition link; a real bounding-box proof that every SI outer-end value label stays inside the plot on Ifremer's own worst-measured panel (1280/1920 only -- see DOM facts); no horizontal scroll. |
| Frontier slider, both modes | The single top-N slider changes the plotted point count in EACH mode independently, and the panel is left in EXACTLY the state handed to the persistence checks. |
| A11 tab overflow | With BOTH optional lenses on (then back off), tab count is 12 and `[role="tablist"]` fits with no silent scroll at 1280px; every tab carries its bare code (`L0`..`L9`). |
| Benchmark lens guide | Header exactly "How to read the lenses"; the first default-lens tab carries only `L0`; clicking it reveals the full name inside the tab body; the Overview caption points back at the guide. |
| Tables / export | A lens's ranked table renders; its CSV carries the R1 columns, no `badge`; the Aspirational tab's table carries no "Interval" column. |
| Institution link (A10) | A REAL click on a canvas-grid Institution cell opens a popup whose URL contains `openalex.org/works`. |
| Settings / Persistence / Type filter clear / Undefined lens | Unchanged mechanics from 2B-R, re-verified. |
| Journey: Compare (2B-R2-3/4/5/8/9/10/13) | Cap-3 truncation notice + deep link; overview cards carry all 6 KPI labels incl. intl/industrial, a best-value dot (painted background span), the name-as-link, no separate Publications button; the selector's exact vocabulary per level (no vol_top10 anywhere, Volume only on ERC/SDG); every subject option is clicked and redrawn; row order IDENTICAL between Share and Dynamics tabs (**load-bearing**), then proven to re-rank under "Largest first" and restore under "By subject area"; the volume gutter carries a number on (almost) every row; a low-volume dagger glyph found in a bar's own value-label text; reference-line shape counts rise on Dynamics/PP vs Share; the frontier map's pool selector and domain-colour toggle change the plotted signature and the map's own (scoped) legend; the plain-language "Not shown here, and why" disclosure renders and a forbidden-vocabulary scan finds nothing; the impact-floor toggle changes the page's markdown reading lines (moved off `st.caption` this round); the workbook carries 11 sheets; removing one shown institution refills the comparison to the cap. |
| Journey: hand-off + Collaborate (persistence) | The in-session `st.switch_page` hand-off keeps the basket and scenario; all 5 current section headers render; the pulse chart carries "2025*"; the two "ranks number" lines read different numbers (no accidental swap); swap flips A/B. |
| Collaborate anchor pair (2B-R2-11, standalone) | Universite de Strasbourg x CNRS, a fresh deterministic session: all 4 tables render as hand-built HTML (no canvas grid); the field-breakdown chart carries real bar values; every field/topic row carries its domain chip(s) and dynamics arrow; every shown row's link ANDs both institutions and carries the right taxon filter; the topic-depth and untapped-depth sliders change their own row counts; the two gap tables and their download are gone, disclosed in plain language; the 3 CSV downloads match the published column contracts. |
| Collaborate below-floor pair (2B-R2-12, standalone) | A REAL sub-floor pair (Strasbourg x Bavarian Academy of Sciences and Humanities, 2 joint works < floor 5), reached via `?pair=` on a fresh session -- the honest notice renders with its own numbers, ONLY the untapped/adjacent tables render (field+topic are floor-gated), pulse/links still render. |
| Journey: Methods | >=14 section expanders, zero unresolved `{placeholder}`s, the lens-concordance table names both optional lenses' internal ids. |
| Journey: cross-page persistence + widths | Tree/basis/basket agree across Compare/Collaborate/Methods and back to Find; no horizontal body scroll at 1920/1280/390 on every page. |

Every selector is locale-independent: `.st-key-<key>` classes, `[role="tab"]`,
`[role="option"]`, `[data-testid="stRadioOption"]`, `[data-table="..."]`,
`[data-testid="stSidebarNav"]`, `[data-testid="stException"]`. Text is read
via `textContent` (never `innerText`) and only to **assert** content, never
to locate an element -- and never against `st.dataframe`'s canvas grid.

## DOM facts (Streamlit 1.61.1)

Carried forward from 2A/R1/R2/2B/2B-R unchanged: tabs are `[role="tab"]`, a
keyed checkbox is the first `label` under `.st-key-<key>`, a
`st.radio(horizontal)` is `[data-testid="stRadioOption"]`, a multiselect
opens via `.st-key-<key> input` + `.fill()`, a selectbox is a react-aria
ComboBox, an `st.expander`'s summary carries an icon-font ligature prefix
requiring exact comparison, an expander's body executes every rerun
regardless of visual state, a `st.segmented_control` is a row of real
`<button>`s clicked by position, a slider's thumb is a visually-hidden real
`<input type="range">` driven by `.press("ArrowLeft"/"ArrowRight")`, and
`st.dataframe` is a canvas grid with no real per-cell text nodes.

### New facts, measured this round (2026-08-31)

- **A low-volume dagger glyph lives INSIDE the bar's own value-label text**
  (a Plotly `text` trace entry, e.g. `"-16.4%†"`), never in the y-axis
  tick text -- the tick carries only the row name and its volume-gutter
  numbers. A check that reads `.ytick text` for the glyph will never find it
  even where a real low-volume row exists; read `el.data[i].text` off the
  live figure instead (`_fig_xy_text` in `smoke.py`).
- **The frontier map's own legend and the "who holds the shared frontier"
  chart's legend both carry the "held by more than one" chip.** A
  page-wide text search for that phrase cannot prove the domain-colour
  toggle did anything (it's always present in the OTHER chart's legend);
  scope the read to the markdown block immediately preceding the map's own
  `.st-key-fig_cmp_frontier_map` container (`previousElementSibling`).
- **2B-R2-8 moved Compare's reading lines out of `st.caption` and into
  markdown `chart_note` blocks.** The impact-floor toggle's own text change
  shows up in `[data-testid="stMarkdownContainer"]`, not
  `[data-testid="stCaptionContainer"]` (measured: captions identical
  before/after, markdown differs).
- **Collaborate's tables are hand-built HTML now, not `st.dataframe`.**
  `[data-table="collab_fields|collab_topics|collab_untapped|collab_siblings"]`
  with `tbody tr[data-row]`, `.bu-chip[data-domain]`,
  `.bu-arrow[data-arrow]`, `.bu-link[href]` -- read rows/cells/links directly
  instead of downloading a CSV to check row-level facts. Waiting for
  `[data-table="collab_untapped"]` (not the old `[data-testid="stDataFrame"]`)
  is what actually signals the page has landed after a hop.
- **The Compare ERC section's own metric vocabulary is
  Share/Specialisation/Volume -- it never offers Dynamics or PP**, and SDG's
  is Share/Dynamics/Volume. A check that assumes every level offers every
  `SELECTOR_METRICS` label will hang forever on `get_by_text(...).click()`
  for a label that section never renders; read the level's own option list
  first and branch on it.
- Carried forward: a Streamlit slider's `role="slider"` is absent (use
  `input[type="range"]`); `[role="tablist"]`, not `[data-testid="stTabs"]`,
  is what actually scrolls; a keyed widget whose key embeds spaces gets them
  turned into hyphens in its `st-key-` class; the frontier panel's ONE
  top-N slider means point COUNT can tie across modes -- read the figure's
  own `x`/`y` arrays (`_frontier_signature`) instead.

## The non-vacuity proofs (2B-R2, stream H2)

Both ran against **throwaway copies** of `app/` (code dirs copied, `data/`
junctioned read-only into each copy via `New-Item -ItemType Junction` --
219 MB of parquet is never duplicated), one copy per mutation.
`tests/ui/smoke.py` itself is always read from the REAL checkout (only
`--app-dir` points at the throwaway copy), so both proofs run under the
exact same test logic as the real run.

### Proof 1: drop the low-volume dagger glyph -> exactly its own check fails

```python
# lib/charts_compare.py, throwaway copy only
LOW_VOLUME_GLYPH = ""   # was "\N{DAGGER}"
```

Result: **exit 1**, 356 of 360 checks passed. The targeted check fails
exactly where the glyph search runs; the other 3 are an unrelated, pre-
existing Methods-download timeout flake (also seen, once, in proof 2's run
below -- not present in the unmutated real-repo run, so it reads as
throwaway-copy cold-cache slowness, not a consequence of this mutation):

```
FAILED: Compare (2B-R2-4): a low-volume marker (dagger glyph) renders on at least one bar's own value label, searched across subject/ERC/SDG on the Dynamics view
```

### Proof 2: drop the star from the type-corrected identity template -> exactly the Ifremer checks fail, at all 3 widths

```python
# lib/copy.py, throwaway copy only
"IDENTITY_TYPE_CORRECTED": "{kind} (was: {was})",   # was "{kind}{star} (was: {was})"
```

Result: **exit 1**, 348 of 354 checks passed -- exactly the 6 Ifremer checks
this template feeds (2 checks x 3 widths), plus the same unrelated download
flake:

```
FAILED: Ifremer 1920px: the inline type correction '<type>* (was: <type>)' renders (body has: None)
FAILED: Ifremer 1920px: the '*' renders as its own span
FAILED: Ifremer 1280px: the inline type correction '<type>* (was: <type>)' renders (body has: None)
FAILED: Ifremer 1280px: the '*' renders as its own span
FAILED: Ifremer 390px: the inline type correction '<type>* (was: <type>)' renders (body has: None)
FAILED: Ifremer 390px: the '*' renders as its own span
```

### Then: the real app, unmutated

```
python tests/ui/smoke.py --port 8641
```
Result: **359 of 359 checks passed, exit 0**. No orphan `python.exe` /
`streamlit` process or LISTENING port left after any run in this stream.

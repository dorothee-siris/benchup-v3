# Playwright UI suite (`tests/ui/smoke.py`, `tests/ui/probe.py`)

REWRITTEN for Phase 2B-R3 (BUILD_PLAN_2BR3.md, stream TEV-U, wave 3) against
the new selection architecture: ONE shared sidebar search + basket
(`lib.selection.render_sidebar`, called on every page) feeding basket-only
"slots" on Compare (3, `state.COMPARE_CAP`) and Collaborate (2,
`state.COLLAB_CAP`); Find keeps ONE dropdown over the basket
(`views_find._seed_pick`). Compare and Collaborate were both reworked around
this (streams VC/VL): Compare is now title -> slots -> KPI cards -> Coverage
-> Subject/ERC/SDG -> the two frontier charts -> Impact -> a collapsed
"About these figures" meta block; Collaborate is title -> slots -> identity
cards + a pair MOMENTUM headline -> the pulse -> a domain-coloured field
CHART (the old field TABLE is gone) -> a NEW "Strategic reciprocity by
field" bubble scatter -> a native, sortable `st.dataframe` topic deep-dive
(20 rows + "Show all", no slider) -> untapped potential (same pattern) -> a
collapsed meta block.

Everything the old per-view "add a comparator" flows, the Compare hand-off
button, the old Collaborate field table + row sliders + "Read the
publications on OpenAlex" section, "Trends in the N subfields", and the
light pastel institution trio used to cover is now either gone (asserted
ABSENT, not merely untested) or replaced by the shapes above.

## Two files, two jobs

- **`smoke.py`** -- the end-to-end proof. Drives the LIVE Streamlit server
  (`streamlit run Menu.py`) headlessly, exercises the shared sidebar
  search+basket for real, the slots API on Compare/Collaborate, the deep-link
  hydration paths, every 2BR3 deletion asserted absent, the full Find profile
  body (unchanged in shape this round), cross-page persistence, and three
  standalone fresh-session checks (Ifremer crash seed, Collaborate below-floor
  pair, the deep-link hydration FINDING below). One `PASS:`/`FAIL:` line per
  check, a summary count, a `FINDING:` block for anything reproduced but
  outside this stream's fence, and a list of failed checks at the end.
- **`probe.py`** -- the acceptance-level recompute proof, ONE file
  parameterised by view (`python tests/ui/probe.py find|compare|collab|all`),
  consolidating what were three separate scripts
  (`ops/_probe_find.py`/`_probe_compare.py`/`_probe_collab.py`, all DELETED
  this wave). Every rendered VALUE is recomputed straight from
  `lib/compare_data.py`/`lib/collab_data.py` (bypassing the page) and looked
  for in the DOM -- the L1 golden recompute, the metric-selector FULL sweep,
  the row-order-identical-across-tabs LOAD-BEARING check, the pulse rank
  DIRECTION anchor, the field-chart values, the reciprocity geometry, the
  FWCI column_config presence.

### Run them

```
cd app
set PYTHONIOENCODING=utf-8
"<repo>/envs/env-app/Scripts/python.exe" tests/ui/smoke.py --port 8611
"<repo>/envs/env-app/Scripts/python.exe" tests/ui/probe.py all --port 8620
```

Exit 0 iff every check passes. The server is always started as a
foreground-waited subprocess and always terminated in a `finally` block --
no orphan `streamlit` process is ever left running. `smoke.py --app-dir
<path>` points the script at a different `app/` root (a throwaway copy)
instead of the checkout it lives in.

## What `smoke.py` proves, section by section

| Section | What it proves |
|---|---|
| Menu | Heading, `.st-key-nav_cards`, 4 live `st.page_link` cards; the shared sidebar search renders here too (`selection.render_sidebar` is called from `Menu.py`). |
| Sidebar search + basket | Old free-text inputs ("Add an institution by name", "Matching institutions") are gone; empty-basket state; three real search+add rounds; always-visible remove; the basket filled to its cap (10) via NINE further real search+add rounds plus one more (never via a deep link -- see the DOM fact below on why); a REAL blocked 11th add renders the cap message; Clear basket. |
| Find dropdown over basket | Zero basket items -> the prompt, no profile, no picker; exactly ONE basket item -> auto-selects, no picker selectbox renders at all; two or more (a FRESH session) -> the picker renders and nothing is auto-loaded until an explicit pick. |
| Deep-link hydration (Compare `?compare=`, Collaborate `?pair=`) | Fresh sessions: the slots hydrate from the URL -- AND the FINDING below. |
| Find profile body | Unchanged in shape this round (SEL/VC/VL all confirm it's byte-unchanged): the 6 KPI cards, the six chart panels, SI value labels, the frontier mode signature change, the breakdown chip-legend swap, A11 tab overflow, the lens guide, table/CSV export, settings, the type-filter clear, an undefined-L2f seed, the Ifremer crash seed (umbrella + type-corrected) at all three widths. |
| Compare (fresh trio, standalone) | Old per-page add/hand-off UI gone; "Trends in the"/"Take one pair further" absent; the slots' own options are the basket + one empty sentinel (checked AFTER a real interaction -- see the hydration-gap DOM fact); section order KPI cards -> Coverage -> Subject/ERC/SDG -> both frontier charts -> Impact -> About (LOAD-BEARING); slot 1's own swatch paints the darkest navy `#192C41`; the metric selector's vocabulary + a sweep; the per-chart "Not shown here, and why" expander; the shared frontier's top-20/Show-all; the About block; no forbidden vocab / pastel hex / bare `NA` hover; the 9-sheet workbook; no horizontal scroll at three widths. |
| Collaborate (Strasbourg x CNRS, standalone) | Momentum headline (a real subheader, big text, glyph; `p =` and both windows folded into its own tooltip since 2C) + a basis chip per CORE-AR section; identity cards; the pulse chart's legend is the JOINT chip ONLY (no institution chips); the bonus year star (in the axis TICKTEXT, not the trace `x` -- see the DOM fact); the domain-coloured field CHART with no table; the reciprocity scatter (squared axes, one dotted diagonal, both axes sharing the same `[0, max]` range); >=2 native dataframes (topic + untapped, each with a name-as-link topic column since 2C), the topic table's own "Show all" hides itself once clicked (a before/after COUNT, not an absolute-absence check -- both sections' buttons share one copy template); no row sliders remain; the retired adjacent-topics expander asserted absent; section order; every 2BR3/2C deletion asserted absent; no forbidden vocab / pastel hex / bare `NA` hover; no horizontal scroll. |
| Collaborate below-floor pair (standalone) | A REAL sub-floor pair (Strasbourg x Bavarian Academy, 2 joint works < floor 5): the honest notice, pulse still renders, the field chart and reciprocity chart are BOTH absent (below the topic floor). |
| Cross-page persistence | The ONE shared sidebar basket count agrees across Compare/Collaborate/Methods/Find (Methods' own wiring is MT's job, not this stream's -- a missing caption there is reported as a FINDING, not failed). |
| Methods | >=14 sections, no unresolved `{placeholder}`, the lens concordance table, no forbidden vocab. |

Every label compared for exact text is a HARDCODED literal (never
re-imported from `lib/copy.py`): importing the very string under test would
make a rename compare against itself and pass vacuously.

## The FINDING (reproduced, not fixed -- outside the TEV-U fence)

`selection.render_sidebar()` draws the sidebar's basket BEFORE
`selection.slots_row()` folds a `?compare=`/`?pair=` URL's ids into the
basket, on the SAME script run (both views call `render_sidebar()` before
`slots_row()` in `render()`). On a FRESH session's very FIRST paint, the
slots already show the hydrated institutions while the sidebar's own basket
list still reads 0 -- a real, reproducible gap in `lib/selection.py` (SEL's
file, outside this stream's fence). ANY later rerun (a widget click, a page
nav) self-corrects, because the basket mutation itself already landed in
session state during that first run; only the raw first paint disagrees.
`smoke.py`'s dedicated `check_deeplink_hydration` proves this on both views
and reports it as a `FINDING:` line, never as a silently-passed check;
every OTHER check that also touches the basket right after a fresh `goto()`
is deliberately sequenced AFTER a real interaction has already forced one
extra rerun, so it reads the corrected state rather than tripping over the
same gap a second time.

## DOM facts (Streamlit 1.61.1, measured 2026-08-31, 2BR3 re-cut)

**New this round:**

- **`st.text_input` (the sidebar search box) commits on Enter or on blur,
  never on a bare Playwright `.fill()` alone.** `.fill()` dispatches
  input/change DOM events but leaves focus in the field, so the debounced
  value never reaches the server without an explicit `.press("Enter")`
  afterwards -- measured: every sidebar search silently no-ops without it.
- **A `?compare=`/`?pair=` deep link can never pre-fill the basket past its
  OWN view's slot count.** `selection.resolve_slot_hydration` trims the
  parsed ids to `n` (3 for Compare, 2 for Collaborate) BEFORE folding them
  into the basket -- a Compare link naming nine ids still only ever baskets
  three. Filling the basket past a view's own cap needs real, repeated
  sidebar search+add rounds (`smoke.py`'s `BASKET_FILL_QUERIES`), not a
  bigger deep link.
- **The first-paint sidebar/slots basket-count gap above** -- read the
  dedicated section; it is a real app behaviour, not a test artefact, and
  every check that is not ITSELF proving the gap needs to be sequenced after
  a real interaction to avoid tripping over it by accident.
- **Collaborate's topic and untapped tables are native `st.dataframe`
  (a canvas grid, DOM FACT below) -- 2C (D8) retires the one hand-built HTML
  table this page still carried ("Adjacent topics in the same subfields"),
  so NO hand-built table remains on this page at all.** Both surviving
  tables' topic column is now name-as-link (the app's one canonical row-link
  idiom) rather than a separate trailing "Open" column. Row-level facts for
  topics/untapped are proved structurally (a "Show all" button's own
  before/after presence, dataframe count) or via `probe.py`'s direct
  recompute against `collab_data`, never by reading canvas cell text.
- **The topic and untapped sections' "Show all N topics" buttons share the
  EXACT SAME copy template** (`copy.COLLAB["SHOW_ALL_BUTTON"]`) -- a text
  search for that pattern matches BOTH when both have >20 rows to hide. A
  check that clicks one and then asserts the pattern is gone entirely will
  false-fail once the OTHER section's identical-text button is still
  present; compare a before/after COUNT of matches instead.
- **The Collaborate pulse chart's bonus-year star lives in the x-AXIS
  TICKTEXT** (`el.layout.xaxis.ticktext`), never in the trace's raw `x`
  values (`charts_compare.fig_pulse` relabels the tick, the `x` stays the
  bare year) -- the OPPOSITE of the Find yearly-breakdown chart, whose own
  `"2025*"` lives directly in `t.x`. Read the right one for the right chart.
- **The momentum headline's big coloured text is found by its OWN inline
  `style*="font-size"`, never by DOM order.** `.st-key-collab_momentum`'s
  FIRST `div` is the small `st.caption("Momentum")` label; the big
  glyph+text markup is a LATER sibling.
- A generating XLSX workbook for a real, LARGE institution (CNRS alone
  carries 238,978 works) can genuinely take longer than a typical reference
  pair's -- the Compare workbook download timeout is 180s, not 120s,
  measured to exceed the shorter one once.

**Carried forward, still true:**

- A Streamlit slider's `role="slider"` is absent; use `input[type="range"]`.
  Collaborate carries NONE any more (retired for the 20-then-Show-all
  pattern); Compare's frontier-map top-N slider is the one survivor.
- `[role="tablist"]`, not `[data-testid="stTabs"]`, is what actually scrolls
  (A11 tab overflow).
- A low-volume dagger glyph lives INSIDE a bar's own value-label text (a
  Plotly `text` trace entry), never in the y-axis tick text.
- An `st.expander`'s BODY executes every rerun regardless of visual state --
  a check for its content never needs the expander actually opened first
  (though opening it first is still the honest thing to do when a real
  human would need to).
- A keyed widget whose key embeds spaces gets them turned into hyphens in
  its `st-key-` class.
- `streamlit run pages/<page>.py` directly (this suite's per-view probe
  entry point) does NOT reliably populate `[data-testid="stSidebarNav"]`
  the way `streamlit run Menu.py` (smoke.py's entry point) does -- wait on a
  PAGE-SPECIFIC element instead (`probe.py`'s own convention, inherited from
  the old per-view probes).

## The non-vacuity proofs

Superseded by direct construction this round: every 2BR3 assertion added to
`smoke.py`/`probe.py` was run once against the LIVE app in its broken,
pre-fix state during this stream's own build (the Enter-less search, the
premature basket-count reads, the wrong momentum-text selector, the `t.x`
pulse-star read) and observed to fail exactly where expected before the fix
landed -- the ledger in `V3/progress/2BR3_TEVU.md` records each one. The
throwaway-copy mutation-testing harness the pre-2BR3 file used
(`--app-dir` pointing at a junctioned copy) still works unchanged for any
future stream that wants to re-run that style of proof.

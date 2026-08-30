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

## Phase 2B-R re-cut (BUILD_PLAN_2BR.md Stream H)

The journey now covers: search-on-validate (A12) with a proof that NOTHING
renders before a pick; the 4-card profile (2B-R-2) with real (non-`n/a`)
international/company facts (2B-R-7); the "2025*" bonus-year mark read off
the live yearly figure's own data, since the old banner/caption is gone; the
"`<n>` institutions &middot; data from `<date>`" caption (2B-R-12, the
verbose snapshot stamp is gone); Top topics cut to 30 with no sort control
(2B-R-13); the SI panels' outer-end value labels with the per-integer grid
retired (`showgrid=False`); the frontier panel's ONE slider driving both
modes; the A11 bare-code tab strip (`L0`..`L9`) fitting at 1280px with both
optional lenses on, and the full lens name opening inside the tab body
instead; the institution-name OpenAlex-works link proven with a real click +
captured popup; Compare's cap-3 truncation (2B-R-4), metric selectors
(2B-R-5/8), two frontier charts (2B-R-9) and 11-sheet workbook; Collaborate's
four sections (2B-R-10) including a REAL below-floor pair; and the Methods
lens-concordance table (2B-R-11).

## What each check proves

| Section | What it proves |
|---|---|
| Menu | The landing page renders: a heading, the `.st-key-nav_cards` container, >=4 live `st.page_link` cards (Find peers, Compare, Collaborate, How it is built), no exception. |
| Find search (2B-R-12/A12) | The data caption reads "`<n>` institutions &middot; data from `<date>`" with the old verbose stamp gone; typing "gdansk" + Enter opens the results selectbox but renders **no profile and no tabs** until a pick is made (A12); picking the first result loads the University of Gdańsk profile; the default tab count is exactly 10. |
| Basket | The sidebar "add a comparator" flow adds Sorbonne then Bologna; the basket panel lists exactly 2 items. |
| Controls placement | The sidebar carries ONLY `.st-key-tree` / `.st-key-basis`; depth/C1/L7/post-filters render in the main-area controls row; the scenario selectboxes show their DISPLAY label, never the internal value; the country multiselect shows names. |
| Profile / panels (2B-R-2/7/13) | `.st-key-profile` renders once; the wordcloud renders as a real `<img>`; exactly 4 `.benchup-kpi` cards, 4 `.benchup-kpi-sub` sublines (one each, all containing "index median"); the identity caption carries REAL international/company percentages (`n/a` is gone now that P2/P4 have deployed); the six panels carry their exact labels; Top subfields AND Top topics both carry no sort control and are cut at 30; SDG y-ticks all start with "SDG"; the frontier panel's mode control changes the plotted TOPIC SET (see "2B-R-13 slider" below); the breakdown pair's segmented control swaps the chip legend. |
| Bonus year axis (2B-R-2) | "2025*" is present in the yearly breakdown figure's own `x` data -- the old caption/banner is gone. |
| SI value labels (2B-R-13) | The fields/subfields/ERC panels' SI marker carries a non-empty outer-end text label, and the axis's `showgrid` is `false` (the old per-integer unit grid is retired). |
| Frontier slider, both modes (2B-R-13) | The single top-N slider changes the plotted point count in EACH mode independently (moved, then restored, in both Top and Emerging), and the panel is left in EXACTLY the state `check_profile_and_panels` handed off (mode=Emerging, slider=default) before the persistence checks run. |
| A11 tab overflow | With BOTH optional lenses switched on (then back off), the tab count is 12 and `[role="tablist"]` (the element BaseWeb actually scrolls -- NOT the outer `[data-testid="stTabs"]` wrapper, which carries a few px of its own chrome) fits with no silent scroll at 1280px; every tab carries its bare code (`L0`..`L9`). |
| Benchmark lens guide (A11) | The guide's header is exactly "How to read the lenses"; the first default-lens TAB carries only the bare code `L0`; clicking it reveals the full name ("L0 &middot; Field overlap") inside the tab BODY; the Overview caption points back at the guide. |
| Tables / export | A lens's ranked table renders; its CSV carries `total_frac_2020_2024`, `country`, `evidence`, no `badge`; the Aspirational tab's table carries no "Interval" column (2B-R-11). |
| Institution link (A10) | A REAL click on the Aspirational table's Institution cell (a canvas grid -- no DOM `<a>` to query) opens a popup whose URL contains `openalex.org/works` -- the URL-fragment display-text trick. |
| Settings | Post-filters, depth-to-max, the tree's non-default DISPLAY label, and L7 all set here, giving the persistence check something real to lose. |
| Persistence (load-bearing) | After 4 real Menu&harr;Find hops: basket, L7 tab, seed heading, strip (taxonomy/depth/type) all survive; the frontier panel's **topic-set SIGNATURE** (not raw point count -- 2B-R-13 made both modes capable of tying on count) still matches the Emerging-mode baseline; the breakdown chip legend still matches. Checked at baseline, after 2 hops (re-mount) and after 4. |
| Type filter clear / Undefined lens | Unchanged mechanics; the undefined-lens tab is now located by its 2B-R-11a display code (`L4`, not the old literal `L2f` substring, which no longer appears anywhere in the rendered page). |
| Screenshots | Menu/Find at 1920/1280/390 with the Top-subfields panel open, scrollWidth checked at each. |
| Journey: Compare (2B-R-4/5/6/7/8/9/12) | A 4-item basket (Gdansk + its top-3 L1 peers) triggers the cap-3 (`COMPARE_CAP=3`) truncation notice and a 3-id deep link; overview cards carry international/company facts; the "Compare by" metric selector switches; the ERC section's option list is checked for the ruled "Volume" option (2B-R-8 -- **currently fails, a real UI gap, see the stream's progress note**); the frontier map's own slider changes its plotted count; the diverging "who holds the shared frontier" chart renders; >=4 legend strips render above their charts; the workbook carries exactly 11 sheets (`Methods` + 10); removing one shown institution refills the comparison to the cap and the truncation notice disappears. |
| Journey: hand-off + Collaborate (2B-R-10) | The in-session `st.switch_page` hand-off keeps the basket and scenario; all four 2B-R-10 section headers render; the pulse chart's data carries "2025*"; the two "ranks number" lines read different numbers (asymmetric, proving no accidental swap); swap flips A/B; the shared-topics table (now inside the untapped section's own expander) and its CSV are unchanged from 2B. |
| Journey: below-floor pair (2B-R-10) | A REAL sub-floor pair (Strasbourg &times; Bavarian Academy of Sciences and Humanities, 2 joint works < floor 3), reached via `?pair=` on a FRESH, standalone session (this asserts no persistence claim, so `page.goto()` is correct here) -- the honest notice renders, the topic table does not, pulse/links still do. |
| Journey: Methods (2B-R-11) | >=14 section expanders (MU shipped 20), zero unresolved `{placeholder}`s, the "Reading the lens codes" concordance table names both optional lenses' internal ids (`C1`, `L7`). |
| Journey: cross-page persistence + widths | Tree/basis/basket agree across Compare/Collaborate/Methods and back to Find; no horizontal body scroll at 1920/1280/390 on EVERY one of the four pages (Compare's own render check already covered all three; Collaborate/Methods are now also checked at 1920/390, not just 1280). |

Every selector is locale-independent: `.st-key-<key>` classes, `[role="tab"]`,
`[role="option"]`, `[data-testid="stRadioOption"]`,
`[data-testid="stSidebarNav"]`, `[data-testid="stException"]`. Text is read
via `textContent` (never `innerText`) and only to **assert** content, never
to locate an element -- and never against `st.dataframe`'s canvas grid.

## DOM facts (Streamlit 1.61.1)

Carried forward from 2A/R1/R2/2B unchanged: tabs are `[role="tab"]`, a keyed
checkbox is the first `label` under `.st-key-<key>`, a `st.radio(horizontal)`
is `[data-testid="stRadioOption"]`, a multiselect opens via
`.st-key-<key> input` + `.fill()`, a selectbox is a react-aria ComboBox
(`.st-key-<key> [data-baseweb='select']`, falling back to the container, with
an `ArrowDown` fallback for a second sequential use of the same widget), a
selectbox's CURRENT value is its `input`'s own `value` property, an
`st.expander`'s summary carries an icon-font ligature prefix requiring exact
(not substring) comparison, an expander's body executes every rerun
regardless of visual state, a `st.segmented_control` is a row of real
`<button>`s clicked by position, and `st.dataframe` is a canvas grid with no
real per-cell text nodes.

### New facts, measured against a standalone debug server (2026-08-31)

- **A Streamlit slider's thumb carries no `role="slider"`** on this pinned
  build -- it is a visually-hidden real `<input type="range">` (react-aria's
  accessible-hide pattern: zero visual size, `clip-path: inset(50%)`).
  `.press("ArrowLeft"/"ArrowRight")` on that locator (which focuses the
  element itself, no separate click) is what actually moves it; a click at
  its own bounding box hits nothing, since the box has zero area.
- **`[data-testid="stTabs"]` (the outer wrapper) is NOT the element that
  scrolls.** It carries a few px of its own padding/border (measured:
  scrollWidth 829 vs clientWidth 820, a false "overflow"), while
  `[role="tablist"]` -- the element BaseWeb's own tab bar renders as, since
  `[data-baseweb="tab-list"]` is absent on this build -- measures exactly
  820==820, matching stream FC's own report. Always measure the tablist, not
  the wrapper.
- **A keyed widget whose key embeds spaces gets them turned into hyphens** in
  its `st-key-` class (`frontier_topn_Top topics by volume` ->
  `st-key-frontier_topn_Top-topics-by-volume`); a `[class*="st-key-<prefix>"]`
  partial match still finds it without needing the exact sanitised string.
- **2B-R-13's frontier panel shares ONE top-N slider between both modes.**
  This means the plotted POINT COUNT can legitimately tie between Top and
  Emerging (both capped at the same `top_n`, e.g. 200==200) even though the
  underlying topic SET is completely different -- a raw count comparison is
  no longer sufficient proof the mode control does anything, and is *not*
  sufficient for the cross-page persistence check either (a mutation that
  silently resets `frontier_mode` to its coded default can still show 200==200
  if both pools have >=200 members). `_frontier_signature` (the live figure's
  `x`/`y` arrays, JSON-stringified) is the only honest signal, used both for
  the mode-switch check and for `_capture_persisted_state`/`_assert_persisted`.
- **2B-R-11a renumbers `L2f`'s display code to `L4`.** The tab carries only
  the bare code, and `UNDEFINED_LENS_TEMPLATE` now formats with
  `copy.LENS_DISPLAY_NAMES["L2f"]` ("L4 &middot; Shared specialisations") --
  the literal substring `"L2f"` no longer appears anywhere in the rendered
  page. Locate the tab by `L4` and check the undefined message against the
  full display name, never the old internal id.
- **`SHARED_EXPANDER` (Collaborate's full-topic-overlap table, inside the
  untapped section) carries no `key=`.** It is opened by its own summary
  TEXT ("The full topic overlap, weighted by publications") -- a navigation
  need, not a content assertion, so this does not reopen the non-vacuity
  question the exact-label checks exist to answer.
- **Compare's reorder buttons (`cmp_up_`/`cmp_down_`) and the frontier
  facets/overlay toggle (`cmp_frontier_form`) are RETIRED in 2B-R.** Do not
  look for them; the frontier section is now two independent charts
  (`fig_cmp_frontier_map`, `fig_cmp_shared_frontier`), and the compared set's
  order is fixed by the identity family's own slot order.

## Real finding surfaced by this run (not a test bug)

**Compare's ERC section offers no "Volume" metric option (2B-R-8).**
`compare_data.py` (`lib/compare_data.py::METRICS`) ships a `vol` metric
(CD's post-commit addendum, verified at the data layer, 84/84), but
`views_compare.py`'s `METRIC_LABELS`/`ERC_METRICS`/`SDG_METRICS` -- written
before that addendum landed -- still enumerate only the original six metrics,
so `vol` never reaches the UI's option list regardless of what
`metric_frame_available` says. This shows up as one reliable FAIL every run:
`Compare ERC (2B-R-8): a 'Volume' metric option is offered among
'Share|Specialisation'`. It is real, reproducible, and out of this stream's
fence (`tests/ui/*` only) -- flagged for CD/CP.

## The non-vacuity proofs (2B-R, stream H)

Both ran against **throwaway copies** of `app/` (never the real repo, one
copy per mutation), built with the established
`MSYS_NO_PATHCONV=1 robocopy ... /E /XD "tests\ui\screenshots" ".git"
"__pycache__" /NFL /NDL /NJH /NJS /NC /NS /NP` idiom (exit code `1` means
"files copied successfully", not failure). `tests/ui/smoke.py` itself is
always read from the REAL checkout (only `--app-dir` points at the throwaway
copy), so both proofs run under the exact same test logic as the real run.

### Proof (a): remove `persist_state` from `frontier_mode` only -> exactly its persistence checks fail

```python
# lib/views_find.py, in the throwaway copy only, _panel_frontier()
st.segmented_control(copy.FIND["FRONTIER_MODE_LABEL"], [mode_top, mode_emerging],
                     default=mode_top, required=True, key="frontier_mode")   # ** PERSIST removed
```

Result: **exit 1**. The frontier signature reads PASS at the baseline capture
(before any hop) and FAIL at both the 2-hop and 4-hop marks -- exactly the 2
checks this mechanism owns:

```
PASS: Persistence: baseline captured before any hop: frontier_mode still shows its off-default (emerging) topic set (signature match: True; ...)
FAIL: Persistence: 2nd Find visit (re-mount check): frontier_mode still shows its off-default (emerging) topic set (signature match: False; ...)
FAIL: Persistence: 3rd Find visit (after 4 hops): frontier_mode still shows its off-default (emerging) topic set (signature match: False; ...)
```

(That same run also hit one unrelated infra timeout on the Compare hand-off's
`cmp_pair_b` selectbox, cutting the journey short -- unrelated to
`frontier_mode`; the mechanism's own before/after signal above is unambiguous
on its own, and the unmutated real app passes that exact section cleanly on
every other run in this stream, including a repeat run right before this
proof.)

### Proof (b): rename `PANEL_TOPICS` -> exactly the label check fails

```python
# lib/copy.py, in the throwaway copy only
"PANEL_TOPICS": "Top topics overview",   # was "Top topics"
```

Result: **exit 1**, 255 of 257 checks passed -- exactly one NEW failure (plus
the pre-existing, unrelated ERC finding above):

```
FAILED: Panel 'topics': header label is exactly 'Top topics' (got 'keyboard_arrow_rightTop topics overview')
FAILED: Compare ERC (2B-R-8): a 'Volume' metric option is offered among 'Share|Specialisation'
```

### Then: the real app, unmutated

```
python tests/ui/smoke.py --port 8622
```
Result: **256 of 257 checks passed** -- the one failure is the real ERC
"Volume" finding above, reproduced identically across three separate runs.
No orphan `python.exe`/`streamlit` process or LISTENING port left after any
run in this stream.

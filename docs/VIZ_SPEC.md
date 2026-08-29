# VIZ SPEC — BenchUp v3 Find tab (Stream D0)

**Produced by:** Stream D0, 2026-08-29, before any page exists (BUILD_PLAN_2A.md §3
Stream D0: "authored BEFORE any page"). Format follows the Lorraine Phase 2 Studio
run (`Client Project\Lorraine\Phase 2\docs\studio\VIZ_SPEC.md`): one app-wide system
section, then one row per view, each with form / encoding / interaction /
empty-state / export / composition and a named rejected alternative.
**Contract, not restated:** `INDICATOR_SPEC_v2.md` (lens statuses, recall figures,
judged reads, closed micro-choices) and `BUILD_PLAN_2A.md` §1 (locked decisions
L1–L15) are binding and only summarised here where a viz decision hangs on them.
**House rules:** light mode only, full width, render-verify at 1920/1280/390 px.
`dataviz` skill loaded; palette validated `--mode light` only (SIRIS override of
the skill's dark pass) — see `design-system/palette_validation.txt`.
**No static string asserts a value** (BUILD_PLAN_2A L10, digit-ban test in Stream
G's scope): every count, percentage and threshold below is written as a
parameter (`{n}`, `{N}`, `{k}`) even where a real number is shown for
illustration — illustrations are marked "e.g." and are never literal UI copy.

---

## 1. App-wide visual system (all Find views inherit)

### 1.1 Colour (computed, not eyeballed — validator runs 1–8, mode light)

Single source: `lib/palette.py`. Full validator log with every command and its
verbatim output: `design-system/palette_validation.txt`.

**The coexistence rule (binding, R1/L19): ONE identity family per chart.** A
chart is coloured by OpenAlex domain, OR by ERC domain, OR by SDG, OR by
document type — never two at once, and never a family plus `FOCAL`. The whole
profile section describes ONE institution, so there is nothing to highlight
against there: painting a bar `FOCAL` inside a domain-coloured panel would
assert a comparison the chart does not make. `FOCAL` therefore appears only in
the ranked/comparison views (seed row, ProgressColumn bars, links). The
yearly-breakdown pair swaps domain ↔ document type through one segmented
control, so exactly one family is on screen at a time and the chip legend is
rebuilt on every swap — which is precisely why the two families' mutual
validator distance is a NON-requirement (§2.14, palette_validation.txt run 6b).

**Family 1 — OpenAlex domains** (`OA_DOMAIN_COLORS`, BenchUp V2 / Lorraine
lineage, FIXED): Life `#0CA750`, Social `#FFCB3A`, Physical `#8190FF`, Health
`#F85C32`. **Fields, subfields and topics have no colour of their own — they
INHERIT their domain's** (`palette.domain_color`, the V2 `get_field_color`
pattern). Because the active TREE decides which subfield, field and domain a
topic rolls up to, colours follow the tree × basis toggles with no extra code.
Unknown / unclassified → `COMPARISON` grey, never a fifth identity.
Validator run 3 is **descriptive**: these hexes are inherited, not chosen, and
its findings are carried as BINDING RELIEF, never as a reason to change a value —
(a) `#FFCB3A` lightness 0.865 is outside the band and (b) `#FFCB3A` 1.52:1 /
`#8190FF` 2.85:1 contrast are below 3:1, both relieved because every bar and
segment carries its category name on the axis and every panel ships the same
numbers through the CSV export; (c) `#F85C32`↔`#0CA750` deutan ΔE 7.6 sits in the
6–8 floor band, legal only with the secondary encoding the axis labels provide,
and the two are non-adjacent in the fixed display order.

**Family 2 — ERC domains** (`ERC_DOMAIN_COLORS`, THREE NEW hues chosen in R1):
PE `#1F4E9C` deep blue, LS `#9B1B6B` deep magenta, SH `#8A5A00` dark ochre.
Validated ALONE (run 4, `--pairs all`): **ALL CHECKS PASS**, worst CVD ΔE 8.8
protan, worst normal-vision ΔE 20.3, every contrast ≥ 3:1. Validated TOGETHER
with the four OA hues (run 5, 7 slots, all pairs): the worst all-pairs
normal-vision distance in the whole set is 20.3, so **every OA↔ERC pair clears
the ΔE ≥ 12 requirement by ~1.7×**, and every ERC-involving CVD pair is ≥ 8.1.
The strategy, stated so a future edit does not undo it: OA lives in the light-to-
mid lightness band (L 0.63–0.87), ERC is deliberately a DARK triad (L 0.45–0.55)
on three hue angles OA does not use. Rejected candidates and their measured
reasons are listed in `lib/palette.py`.

**Family 3 — the UN SDGs** (`SDG_COLORS`, 17 stored, **16 drawn**): the official
UN goal colours, FIXED by the UN. Source: manager-supplied, matching the 2019 UN
guidelines as commonly published; a live check of un.org's communications-material
page (2026-08-29) confirms the governing document — *Sustainable Development
Goals Guidelines for the use of the SDG logo including the colour wheel and 17
icons*, August 2019 edition, revised September 2023 — but that page publishes the
assets, not the hex table. Validator run 7 **FAILS and is descriptive only**; the
findings are real and oblige structural relief, not a hue change. The sharpest:
`#FD9D24` (goal 11) ↔ `#DDA63A` (goal 2) at normal-vision ΔE 5.3 — the UN palette
contains two near-identical ambers, so **no chart may rely on telling SDG colours
apart by hue**. Relief: the SDG panel is a labelled bar chart in fixed goal order,
every bar carrying its goal number and short label on the axis. Goal 17
(`#19486A`) is stored but never drawn — the classifier does not cover it, and the
panel says so from `palette.SDG_UNCOVERED`, never from a typed string.

**Family 4 — document types** (`DOCTYPE_COLORS`): article `#22A2BD`, review
`#A55F8F`, book `#667900`, book-chapter `#7838B6` (Lorraine's validated pass-6
set, taken over unchanged) + **`letter` `#A10A4E`, new for BenchUp** (the hue
Lorraine's own palette carried in that slot; BenchUp's corpus has letters where
Lorraine's had conference papers). The five ALONE (run 6a, all pairs): **ALL
CHECKS PASS**. The new hue clears the OA quartet on its own by min normal-vision
ΔE 24.0 / min CVD ΔE 17.5. The five WITH the four OA hues (run 6b, 9 slots) FAILS
on two PRE-EXISTING pairs that do not involve the new hue (`#667900`↔`#0CA750`
normal 13.1; `#667900`↔`#F85C32` protan 3.3) — disposed of by the coexistence
rule above, recorded rather than suppressed because the swap does put the two
families in sequential memory.

**Focal / comparison / neutral / ink (unchanged):** `FOCAL` `#0072B2` is the seed
institution in the ranked views only — and, mirrored there alone,
`.streamlit/config.toml` `primaryColor`. `COMPARISON` `#8C9196` is candidate rows,
reference marks and every family's unknown/unclassified slot. `NEUTRAL` `#E6E8EB`
is background/zebra/empty-state fill. `INK` `#333333` is text only (the validator
fails it as a series colour by design). `SURFACE` `#FFFFFF` is every figure's
`paper_bgcolor` and `plot_bgcolor`, and is the `--surface` every R1 validator run
was executed against.

**Chrome tokens (R1, text and furniture — excluded from categorical validation by
design, run 8 reproduces the expected FAIL):** `INK_SECONDARY` `#5A5F66` for KPI
sublines, gutter numbers, chip labels and axis ticks (6.43:1 on white, above the
4.5:1 body-text floor — the only check that matters for it); `BORDER` `#E3E6EA`
for tile/panel hairlines; `GRID` `#D9DDE2` for gridlines and zero lines, which
must RECEDE, so their low contrast is the requirement and not the defect.

**Flags are SHAPE, never a new hue.** A catch-all (811) topic keeps its domain
colour at `MUTED_OPACITY` plus a glyph in its label; a top-quartile frontier
topic keeps its domain colour with an `INK` outline of `OUTLINE_WIDTH`. Both are
secondary encodings on top of the family colour. BenchUp v3 still defines no
status palette (no good/bad or momentum read exists in the spec).

**REMOVED in R1: `TYPE_COLORS` / `type_group`.** L22 removes the badge column
from every table (user ruling #8 at gate 2A: the type filter covers the need),
which left the institution-type identity set with no consumer. A grep before
deletion returned only `palette.py`, `tests/test_palette.py` and two prose lines
in `DESIGN_TOKENS.md` — no live code path — so both symbols were deleted rather
than kept as dead colour. Institution type is now plain text in its own table
column plus a post-filter; the seed's own type sits in the profile header.
`tests/test_palette.py::test_type_colors_removed_in_r1` pins the deletion.

### 1.2 Typography

Base 16 px / line-height 1.5 floor on all body and table text; one precision
level per numeric measure; thousands separator; every percentage states its
denominator in the same cell or the line immediately above it (never a bare
"{x}%"). Full scale: `DESIGN_TOKENS.md` §3.

### 1.3 Control placement — sidebar vs the controls row (R1/L16, supersedes the pre-R1 all-in-the-sidebar order)

Gate-2A feedback #1: the sidebar was over-loaded, and controls that act on the
benchmark tables were a page away from the tables they act on. R1 splits them by
SCOPE, not by type — **the sidebar holds what changes the whole app; a control
that changes one section lives at the head of that section.**

**Sidebar (app-wide only):**
1. **Scenario** — tree (`{original, conservative, bestfit}`, default `bestfit`)
   × basis (`{frac, full}`, default `frac`), with the disclosure line "ERC and
   SDG lenses are fractional-only; this toggle does not change them"
   (INDICATOR_SPEC_v2 §5, L5). Scenario is app-wide because it re-derives every
   shape on the page, profile panels included.
2. **Basket** — persistent list, plain session-state key (not a widget key), so
   it survives page navigation.

**Controls row (at the head of the Benchmark section, above the lens tabs):**
depth radio · C1 checkbox · L7 checkbox — each with a `help=` tooltip that
explains the option rather than naming it — then a **"Post-filters" expander**
holding type, country, exclude-own-country, size range, scale guard and family.
C1 and L7 stay two SEPARATE affordances, never bundled, and L7 stays the visibly
more discouraging of the two (INDICATOR_SPEC_v2 §1.8/§1.9, ruling 8).

**Widget keys are UNCHANGED by the move** (`depth`, `c1_on`, `l7_on`, `f_types`,
`f_countries`, `f_excl_own`, `f_size`, `f_guard`, `f_family`) and every one keeps
`persist_state="session"` — so cross-page persistence and the Playwright
`st-key-*` selectors survive relocation. That is the whole reason the move is
cheap; a rename would have cost the smoke suite.

The "Filtered by…" strip (§1.4) still names EVERY off-default dimension,
including tree and basis, wherever their control now lives.

> **Rejected alternative:** move depth and the post-filters into each lens tab,
> so every tab carries its own copy. Rejected because the controls are shared
> state across all ten tabs — per-tab copies would either drift (ten widget keys
> for one value) or lie (one value shown ten times, edited in one place). One row
> above the tab strip states once that these settings govern everything below it.

### 1.4 "Filtered by…" strip (mandatory whenever ANY control is off-default)

Appears directly under the page title, one line, and **names every off-default
dimension by itself** — never a generic "filters active" line (COMPOSITION_AND_CONTROLS.md
Control layer #3; BUILD_PLAN_2A L11). Parametric caption, e.g.:

> Filtered by: tree = original · depth = 50 · type = education, facility · scale guard on

`None` (the strip renders nothing) **iff** tree = bestfit AND basis = frac AND
depth = 30 AND C1 off AND L7 off AND every post-filter is at its default — this
exact predicate is the non-vacuity target for Stream G's toggle × filter matrix
test (`test_matrix.py`).

### 1.5 Badge grammar

Text + glyph, never colour alone (`DESIGN_TOKENS.md` §5). **R1 change:** the
institution-TYPE badge family is GONE together with `TYPE_COLORS` (§1.1) — type
is plain text in its own table column plus a post-filter. Two badge families
remain, both text-only and both seed-level (profile header, §2.10), neither
carrying a colour at all: umbrella/aggregate ("EXPERIMENTAL" text + tooltip
carrying the country×type median compared against) and type-corrected ("type
corrected by SIRIS (was: {type_openalex})"). **Never both an umbrella badge and a type-corrected
badge on the same row** (BUILD_PLAN_2A L7 / WT #14) — this is a hard invariant,
not a styling preference, and Stream F's `badges.py` asserts it in code.

### 1.6 Empty, undefined and thin states

- **Empty (0 rows after post-filters):** name the responsible filter(s) by
  themselves, never a generic "no results" — e.g. "No candidates match `{filter
  A}` ∩ `{filter B}` for this seed at depth {N}. Remove a filter, or increase
  depth to 50." (RULES §8 Empty; BUILD_PLAN_2A L6 "an emptied list names the
  filter(s) responsible").
- **Undefined lens** (e.g. L2f with `n_eligible_subfields_L2f = 0`, or F1 for a
  seed with no frontier-topic mass): an explicit reason line replaces the table
  — never a silently empty table, never a gate on the OTHER lenses (INDICATOR_SPEC_v2
  L8 "lens undefined → explicit reason, never a silent empty list") — e.g. "L2f
  is undefined for this seed: 0 shared-specialisation cells clear the ≥30-paper
  floor."
- **Thin** (few candidates returned, e.g. a small seed whose top-30 has fewer
  than 30 real rows before ties): show the true n and continue — never pad, never
  suppress the mark (RULES §8 Thin; BUILD_PLAN_2A L9 tie rule "never pad").
- **Concordance caption always states both N and n** parametrically — "found in
  the top-{N} of {k} of {n} lenses defined for this seed" — n shrinks when C1/L7
  are off (excluded from n unless enabled) or when a lens is undefined for this
  particular seed; k is never recomputed by post-filters (BUILD_PLAN_2A L3).

### 1.7 Export rules

One "Download full ranking (CSV)" button per lens tab, exporting the FULL
filtered ranking (not just the on-screen depth cut), original competition ranks
preserved (gaps kept, not renumbered), plus constant columns for
`seed_id, lens, tree, basis, snapshot, filters` so a downloaded file is
self-describing outside the app. Filename
`benchup_{seed}_{lens}_{tree}_{basis}[_filtered].csv`. No panel is exported as a
PNG-only artefact (Find has no charts requiring an image export in Phase 2A —
every view here is a table). A whole-page or xlsx-with-method-sheet export is
explicitly deferred to Phase 2B/2C (BUILD_PLAN_2A §7 decisions log).

### 1.8 390 px degradation

Sidebar controls collapse to Streamlit's native top drawer; main content stacks
in argument order — seed search → profile section → controls row → tab strip (Streamlit's native horizontally-scrollable pill
tabs) → ranked table (its own `overflow-x:auto`, never the page body). Legends
and badges wrap to a second line rather than truncating silently (RULES §8
Small screen). Render-verified at 1920/1280/390 px with `scrollWidth ≤
innerWidth+2` is Stream E/H's acceptance gate; this section only fixes the rule
they render against.

**R1 additions, measured rather than assumed** (`design-system/ab/AB_VERDICT.md`,
A/B #3, run at 390x844):

- **The share + SI pair STACKS below the small breakpoint** — share panel above,
  SI panel below, same row order, one shared category axis read twice — because
  side by side at 390 px each panel collapses to a measured 61 px of plot area,
  which is not a chart. Above the breakpoint they stay side by side.
- **The KPI tiles wrap to one per row**, never truncated, sublines intact.
- **The wordcloud + breakdown pair stacks vertically**, cloud first.
- **The six chart panels stay collapsed** and each owns its horizontal scroll;
  the page body still never scrolls sideways.
- **The volume gutter survives at 390 px** (0 clipped annotations measured,
  against 1 clipped for the rejected right-of-bar form) — which is one of the two
  reasons it won A/B #4.

### 1.9 Profile section composition (R1/L17 replaces the seed card of §2.2; R2/L30 re-lays the rows as the Lorraine lab card's grid, not just its chart panels)

Gate-2A feedback #2 (R1): the page was chart-poor. Gate-2A feedback item 3 (R2):
the resulting layout still read as "leftovers" — a coverage line with no clear
audience, a wordcloud oddly paired with a chart it has nothing to do with. R2's
fix is the Lorraine lab card's actual GRID, not just its panels. Fixed order,
top to bottom:

1. **Row 1 — three columns, `[1.0, 2.0, 1.4]`** (§2.10–§2.13): **identity**
   (name, type · city, country NAME, seed-level badges, links) | **KPI tiles**
   (2×4 grid, eight tiles, each positioned against the index baseline) |
   **subfield wordcloud**.
2. **Row 2 — two columns, full width** (§2.14): **global breakdown** |
   **yearly breakdown**, with ONE segmented control and the shared chip legend
   sitting ABOVE both panels — this pair no longer shares its row with the
   wordcloud, so both panels get the full section width instead of half of it.
3. **Six collapsed panels** (§2.15–§2.20), every one `st.expander(expanded=False)`:
   Fields · Top subfields · Top topics · Frontier positioning · SDG profile ·
   ERC profile.

The former "Coverage caption" step is GONE (§2.12, RETIRED): its four items
relocated to the panel/tile/tab each one actually qualifies, so there is no
longer a fourth composition step between the tiles and the breakdown row.

Rules that hold across the whole section, so they are stated once here rather
than repeated in every row below:

- **Everything shape-grain follows tree × basis.** Colours follow too, for free,
  because a topic's domain is decided by the active tree (§1.1, family 1).
- **ERC and SDG are fractional-only artefacts.** When basis = full, those two
  panels say so in their caption instead of silently ignoring the toggle.
- **One identity family per chart** (§1.1) — the profile section never paints a
  bar `FOCAL`.
- **Grouped bars, never stacked.** Lorraine's standing rule: "a bar chart may
  never stack a second categorical dimension." The grouped geometry uses explicit
  `offset`/`width` under `barmode="overlay"` because `offsetgroup` is BROKEN on
  the pinned plotly 5.24.1 (`lib/charts.py::_series_offset_width`, Lorraine
  verbatim).
- **The paired share + SI form and the left volume gutter are A/B verdicts on
  real data**, not preferences — `design-system/ab/AB_VERDICT.md` (R1 section),
  A/B #3 and #4.
- **Every panel that drops rows says how many it dropped**, from the data
  (`is_excluded.sum()`, unscored counts), never from a typed number (L10).
- **No panel is a PNG-only artefact**: every panel's numbers are also in the CSV
  the section exports.

> **Rejected alternative:** render all six panels expanded, as one long scroll
> (BenchUp V2's own layout). Rejected on the measured cost: the six panels are
> ~150 plotly traces and >1,300 marks for a large seed, all built on every rerun,
> against a warm-rerun budget of 1.5 s; and the section's job is to characterise
> the seed in one screen before the reader goes to the benchmark tables, which a
> six-panel scroll defeats. Collapsed-by-default keeps the header + tiles +
> breakdown pair above the fold and makes each panel an explicit choice.

---

## 2. View specs — one row per Find view (9 pre-R1 views; §2 bis adds 13 more)

Status: all **[NEW]** — Phase 2A is the first build of this app.

### 2.1 Seed search

**Decision sentence:** *After typing a few characters, the analyst can find the
one institution they mean, even with an accent, an acronym, or a typo, and move
on to its benchmark.*
**Composition:** hero search box, no default listing — a search-first page
(COMPOSITION_AND_CONTROLS.md harvested pattern "search-first directory": "the
default state is a search prompt... NEVER a full default listing").

| Form id | Form & encoding | Interaction | Empty-state | Export |
|---|---|---|---|---|
| `search-seed` | text input; ≤10 ranked candidates below as a plain list (name · country · type · size), rank = exact name > prefix > substring, fuzzy fallback on token vocabulary | type-ahead on every keystroke (debounced by Streamlit's own rerun cadence); click a candidate to load its seed card | 0 matches: "No institution matches '{query}'. Check the spelling, or try an acronym." — no silent blank | — (not an exportable view) |

**Rejected alternative:** a full alphabetical directory as the page's default
state — rejected on the same COMPOSITION_AND_CONTROLS.md precedent above: a
default listing (alphabetical or otherwise) invites a scan-ranking read the
Find tab never intends, and blows the row budget for no benefit when a search
box resolves the same task in one keystroke sequence.

### 2.2 Seed card

**Decision sentence:** *After reading the card, the analyst can describe the
seed institution's shape, size, and impact position well enough to judge whether
any candidate below is a fair comparison.*
**Composition (argument order, top to bottom):** (1) header — name, `FOCAL`
underline/marker, type + badge, country, ROR link, homepage link; (2) KPI row —
size full **and** fractional (both, each with its own label — never one number
presented as if it were the other), HHI class (a named band, not a bare
number), breadth (n subfields); (3) top-3 fields / top-5 subfields (bestfit,
current scenario) as a short text list, not a chart (RULES form heuristic: a
3–5 item share-of-whole reads faster as text than as a pie); (4) evidence lines
(erc-classified mass share, SDG-tagged share, frontier-top25 share, catch-all
share) — continuous, never a pass/fail gate (INDICATOR_SPEC_v2 L8); (5)
PP(top10%) with its CI, stated as "{pp} [{ci_low}–{ci_high}]" — never the point
estimate alone (RULES honesty rule 6); (6) OpenAlex works deep link
(`authorships.institutions.id:{id},publication_year:2020-2024`), filtered to the
same window used throughout.
**Empty-state:** a seed with `catchall_811_share` undefined (no 811-adjacent
topics at all) shows "n/a" (`palette.NA_MARK`), never 0.
**Export:** none at the card level in 2A (the ranked-table exports below carry
the seed's own row wherever it appears as a candidate for another seed).

| Form id | Form & encoding | Interaction | Empty-state | Export |
|---|---|---|---|---|
| `card-seed` | header + KPI tiles + text lists + evidence lines + CI line + 3 outbound links, as composed above | outbound links open in a new tab; no in-card filtering (one primary interaction per view is spent on the search box that produced this card) | undefined evidence line → `NA_MARK`, never 0 | — |

**Rejected alternative:** a radar/spider chart for the top-3-fields shape —
rejected on the same grounds Lorraine already documented for an analogous
profile card (`VIZ_SPEC.md` §2.6): angle encoding is weak and OpenAlex fields
are not comparable radially; a ranked text list states the same three shares
more precisely in less space.

### 2.3 Concordance overview

**Decision sentence:** *After seeing the overview, the analyst can name the
candidates multiple independent lenses agree on, before opening any single
lens tab.*
**Composition:** displayed prominently as the FIRST tab (INDICATOR_SPEC_v2 §3:
"display prominently as the overview, still never the sole ranking") — a
k-count table: candidate, k of n lenses hit (chip per hit lens, e.g. `L1 L3 F1`),
per-lens rank on hover/expand. Caption states N and n parametrically (§1.6).
Rows removed by post-filters disappear from the table but k is **never**
recomputed (BUILD_PLAN_2A L3 — k/n is computed on the unfiltered ranking).

| Form id | Form & encoding | Interaction | Empty-state | Export |
|---|---|---|---|---|
| `tbl-concordance` | table: candidate · country · type+badge · k (of n) · hit-lens chips · size, sorted by k desc then by the best individual lens rank | row click ↔ jump to that candidate's rank in the first hit lens tab; search box for the tail | 0 candidates hit ≥2 lenses: state it plainly and point at the single-lens tabs, never an empty grid | full concordance table CSV (candidate, k, n, per-lens ranks) |

**Rejected alternative:** as this row's DEFAULT — not eliminated outright: this
exact contrast (k-count table vs. a full rank matrix of candidates × lenses) is
**Cross-cutting A/B #2** in §3 below, resolved on real data by Stream D1. The
k-count table is proposed as the working default because INDICATOR_SPEC_v2 §3
already calls concordance "the cleanest list" (15 sensible / 1 mixed / 0
nonsense, the best judged read of any lens/mode) and a single sortable k number
serves that read more directly than a matrix that needs full lens-column width
to stay legible at 1280 px.

### 2.4 Lens tab (shared form, all 10 lenses)

**Decision sentence:** *After opening any one lens tab, the analyst reads
exactly the same table shape they already learned on the first lens — rank,
who, where, what kind, how big, how strong the read is, and why it might be
noisy — for L0 through L7 and both optional lenses alike.*
**Composition:** gloss (one line, from the table below) + evidence line +
caveat, ALL above the table, never buried in a tooltip only; then the ranked
table; then the depth caption (§2.6) and tail search + export (§2.7) below it.
**Same read, same form** (Lorraine `VIZ_SPEC.md` §3 rule 1): every one of L0,
L1, L3, F1, L2f, L4, L5, L6, C1, L7 renders through the ONE shared form id
below — never a bespoke per-lens layout.

| Form id | Form & encoding | Interaction | Empty-state | Export |
|---|---|---|---|---|
| `tbl-lens-ranked` | table: competition rank · institution (OpenAlex works deep link) · country · type+badge · size (full) · score (form decided by Cross-cutting A/B #1, §3) · evidence (continuous line, lens-specific) · secondary reference "rank under L1/L3" · add-to-basket button | row → add to basket; column sort disabled on score (rank order IS the read — RULES honesty rule 6, no re-sorting past what the ranking already asserts); search scoped to the full ranking (§2.7) | lens undefined for this seed → §1.6 reason line replaces the table entirely | full filtered ranking CSV, §1.7 |

**Per-lens gloss + caveat (source: `INDICATOR_SPEC_v2.md` §1; caveat sits
directly under the gloss, never tooltip-only, per this brief's placement rule):**

| Lens | One-line gloss | Caveat shown with it |
|---|---|---|
| L0 | Field-grain overlap — the coarsest shape, 26 OpenAlex fields | Generic look-alikes for concentrated profiles; moderate outlier crowding among the defaults |
| L1 | Subfield overlap — the anchor lens | Safe to read to rank 50; the most consistently informative lens across seeds |
| L3 | Topic overlap — the workhorse, highest recall of all 10 | Highest same-country clustering of any lens (country post-filter tooltip shown on this tab specifically) |
| F1 | Frontier-topic overlap | Under-represents Social Sciences & Humanities profiles |
| L2f | Shared specialisations (≥30-paper floor per cell) | The failure axis is a diffuse profile, not raw institution size — reads well for concentrated mid-size institutions, poorly for very diffuse or very thin ones |
| L4 | ERC panel overlap | Occasional company/governance leakage into the candidate set |
| L5 | ERC specialisation | The lens with the thinnest external corroboration of the 8 defaults — kept because it still surfaced peers no other lens found; read its candidates with that in mind |
| L6 | SDG profile overlap | Country clustering below L1's — not a peer-finding artefact |
| C1 (optional) | Core-shape — L1 restricted to the seed's own top-20 subfields | A refinement of L1, not a sibling of L7; noise grows faster than L1's past rank 20 |
| L7 (optional, separate toggle) | Experimental SDG-specialisation view | Mostly noise, occasionally unique — the worst judged read of any lens/mode this cycle; kept for the rare peer no other lens surfaces |

L5 and L7's caveats are written to the honest-but-non-alarming standard
(`Portfolio Mapping\units\press\INBOX.md`: neutral, FR-ready vocabulary, no
loaded metaphors) — L5's copy states a fact ("thinnest external corroboration")
rather than a verdict ("weakest"/"unreliable"); L7's copy is the literal
ratified UI string from INDICATOR_SPEC_v2 §1.9 ruling 8 ("mostly noise,
occasionally unique") and is intentionally more discouraging in placement
(§1.3 #3) than in wording — the wording stays factual, the AFFORDANCE carries
the discouragement.

**Rejected alternative:** ten separately laid-out per-lens tables (different
column order/labels per lens) — rejected because a reader would have to relearn
the table on every tab switch, and because Stream F's `ranked.py` exists
specifically to prevent ten divergent implementations of the same row-rendering
logic.

### 2.5 Aspirational tab

**Decision sentence:** *After opening this tab, the analyst sees which
candidates already found by L1 look like they may be punching above the seed's
current impact level — with the uncertainty on that read shown, not hidden.*
**Composition:** the L1 top-50 pool (tie-inclusive) filtered to
`pp_top10_frac > seed` AND `pp_ci_low > seed pp_ci_high`, kept in L1-overlap
order (BUILD_PLAN_2A L4 — this order is what the golden regression pins); a PP
sort is offered as an explicit control, never the default.

| Form id | Form & encoding | Interaction | Empty-state | Export |
|---|---|---|---|---|
| `tbl-aspirational` | `tbl-lens-ranked` base columns, PP(top10%) column replaced by an interval mark: point estimate + CI whiskers rendered per row (RULES form heuristic, Uncertainty/coverage family: "interval dot/caterpillar + n/coverage") | default sort = L1-overlap order; "sort by PP" toggle re-sorts by point estimate, CI still shown; add-to-basket | 0 candidates clear the interval test: "No L1 candidate's impact interval sits fully above {seed}'s at this depth." — never silently blank | full pool CSV incl. `pp_top10_frac, pp_ci_low, pp_ci_high` |

**Rejected alternative:** `st.column_config.ProgressColumn` for the PP value
alone — the shared-form default being evaluated for ordinary lens tabs in
Cross-cutting A/B #1 (§3) — rejected specifically for THIS tab regardless of
that A/B's outcome, because a single progress bar cannot render an interval,
and RULES honesty rule 6 explicitly forbids presenting a ranked value without
its uncertainty ("do not narrate rank 7 vs 8 when intervals overlap"). The
interval mark is not optional here even if it loses the general-purpose A/B.

### 2.6 Depth control

**Decision sentence:** *After choosing 30 or 50, the analyst knows exactly how
many rows they are looking at out of how many computed, and that the rest is
one search or one download away, not gone.*

| Form id | Form & encoding | Interaction | Empty-state | Export |
|---|---|---|---|---|
| `ctl-depth` | two-option segmented control, `{30, 50}`, default 30 (INDICATOR_SPEC_v2 §1/§9 #1); caption under every table: "showing top {N} of {M} ranked — search the tail or download" (RULES §9.9) | one click flips depth app-wide for the current lens tab; `M` and `N` are always read from the live ranking, never typed | — (depth never empties a non-empty ranking) | — (the caption itself is not exportable; the CSV always carries the full ranking regardless of the on-screen depth) |

**Rejected alternative:** a continuous slider over the full ranking length —
rejected per R4.6 simplicity (BUILD_PLAN_2A L2: "ONE global control... not a
per-lens cutoff") and because a freely-draggable depth would need its own
per-value caption logic where a two-option control needs one sentence with two
possible fills; the real per-lens noise-growth-with-depth difference
(INDICATOR_SPEC_v2 §1 table) is handled by disclosure and the post-filter
layer, not by a finer-grained depth control.

### 2.7 Tail search + CSV export

**Decision sentence:** *After the analyst searches for a name they expect but
don't see in the top {N}, they can find it in the full ranking or take the
whole thing away as data.*

| Form id | Form & encoding | Interaction | Empty-state | Export |
|---|---|---|---|---|
| `ctl-tail-search` + `btn-export-csv` | text input scoped to the CURRENT lens's full ranking (not just the on-screen depth cut); one "Download full ranking (CSV)" button beside it | type a name → matching rows appear below the visible table with their true (uncut) rank, even past 50 | 0 matches in the full ranking (not just the depth cut): "'{query}' does not appear anywhere in this lens's ranking for this seed." | CSV per §1.7 |

**Rejected alternative:** pagination or infinite scroll through the tail
instead of search + download — rejected on ponytail grounds (ponytail: "one
line before fifty" — Streamlit has no built-in paginator worth adding a
dependency for) and because the tail is, by construction, a rarely-visited
long list (RULES §9.9's own remedy is "keep the long tail searchable/
downloadable," not "keep it browsable").

### 2.8 Badges (umbrella, type-corrected, catch-all)

**Decision sentence:** *After seeing a badge, the analyst knows in one glance
why a row's numbers might need a second look, without the badge ever implying
the row is wrong or excluded.*
**Composition:** inline in the type/name cell of every ranked table (§2.4);
never a separate panel (RULES §8 "disclose, never demote" — same principle
Lorraine's ARTIFACT-FLAG pattern already applies: a flag discloses, it does not
grey out or hide the row).

| Form id | Form & encoding | Interaction | Empty-state | Export |
|---|---|---|---|---|
| `badge-umbrella` / `badge-type-corrected` / `chip-catchall` | text label + tooltip (median compared against / `was: {type_openalex}` / catch-all share number); institution-type dot from §1.1 where applicable | hover/tap for tooltip detail; badges are never clickable filters (COMPOSITION_AND_CONTROLS.md Control layer #7: "legends filter only when clickable state is obvious" — these aren't legends) | a row with no applicable badge shows none — absence of a badge is not itself a signal requiring an empty-state | badge state is a plain column in the export CSV (not just a visual) |

**Rejected alternative:** a single merged "flag" icon standing in for either
umbrella-or-type-corrected — rejected because it would visually erase the
"never both on one row" mutual-exclusion invariant (BUILD_PLAN_2A L7) that the
two SEPARATE, distinctly-worded badges make legible at a glance; RULES §4's
"never encode two facts as one colour" reasoning generalises to "never encode
two facts as one badge."

### 2.9 Basket affordance + "add a comparator"

**Decision sentence:** *After clicking "add" on a few rows across different
lens tabs, the analyst has a running shortlist that survives switching tabs and
pages, ready for Compare in Phase 2B.*

| Form id | Form & encoding | Interaction | Empty-state | Export |
|---|---|---|---|---|
| `btn-basket-add` + `ctl-basket-freetext` | small button on every ranked-table row ("+ Add"); a persistent sidebar list of added institutions with a remove ("×") control; one free-text box below it, "Add a comparator not found above" | click adds/removes by institution id (ID-based selection payload, COMPOSITION_AND_CONTROLS.md Control layer #4); the free-text box does not validate against OpenAlex in 2A — it is a plain note captured for Compare | empty basket: sidebar shows "No comparators added yet — use '+ Add' on any row." | basket contents are not separately exportable in 2A (they carry into Compare, Phase 2B) |

**Rejected alternative:** a global multi-select dropdown enumerating every
candidate across all tabs as the basket UI — rejected because with up to 50
rows × 10 lens tabs the enumeration would run past LEGIBILITY_BUDGETS' table/
control size guidance for a single control, and because it would duplicate the
row-level "+ Add" affordance that already exists at the exact point the analyst
makes the decision (COMPOSITION_AND_CONTROLS.md Control layer #1: "a control
must change a decision... start from zero controls and add each one against a
named question" — the multiselect answers no question the row button doesn't).


---

## 2 bis. View specs — the R1 profile section and the changed controls/tables

Added by stream R-D2 (refinement R1, 2026-08-29) under BUILD_PLAN_2A.md §9.2
L16–L22. Same row format as §2.1–§2.9: form / encoding / interaction /
empty-state / export, each ending in ONE named rejected alternative. Builders
live in `lib/charts.py` (pure plotly, no Streamlit import); `lib/views_find.py`
composes. Frames are the §9.4 column contracts from `lib/profile_data.py`.

**§2.2 (Seed card) is SUPERSEDED by §2.10–§2.20** and is kept only as the record
of what the pre-R1 page did.

### 2.10 Profile header

**R2 update (L30, user ruling item 3 — "profile space not optimised... Lorraine
lab card as the model"):** the header is now COLUMN 1 of the section's three-column
row 1 (`[1.0, 2.0, 1.4]` — identity | KPI tiles | wordcloud, §2.11–§2.13), not a
full-width block above the tiles. Nothing about the header's own content or rules
changes — only its position and width, which is why this row's prose below is
otherwise the R1 text unaltered.

- **Form.** One block filling column 1: institution name (`text-xl`), then a
  meta line "type · city, country NAME", then the seed-level badges, then a link
  row — ROR · OpenAlex works · homepage. The OpenAlex-works link sits beside the
  `PUBLICATIONS_TOOLTIP` (L29, stream R2-C's copy) that states the corpus
  definition once for the whole section, so every tile and panel beneath it can
  say "publications" without re-explaining doc types, the DOI requirement or the
  bonus year each time.
- **Encoding.** Text only; no chart, no colour. Type is a WORD, not a coloured
  dot (§1.1: `TYPE_COLORS` removed in R1). Country is the English NAME, never the
  two-letter code (L22, `lib/countries.py`, frozen `data/countries_en.csv`).
  Badges keep their pre-R1 rules exactly — umbrella/aggregate (EXPERIMENTAL +
  tooltip carrying the country × type median compared against) and type-corrected
  ("type corrected by SIRIS (was: {type_openalex})") — and the hard invariant
  that **never both on one row** still holds (L7 / WT #14).
- **Interaction.** The OpenAlex link carries the harvest's OWN server-side
  filters (L23: institution, the year window, the five corpus types, `has_doi`),
  percent-encoded; a link that silently returned a different corpus than the app
  counted was gate-2A bug #9. Badges expose their evidence on hover only — the
  visible text stands alone without it (§1.5).
- **Empty state.** A missing ROR, homepage or city drops that item silently
  rather than rendering an empty affordance; a missing TYPE renders `n/a`, never
  a blank or a guess.
- **Export.** Nothing of its own; the identity columns ride in every CSV.

> **Rejected alternative:** keep the institution-type colour dot beside the type
> word, reusing the pre-R1 `TYPE_COLORS`. Rejected because the badge column that
> justified a five-hue identity set is gone (L22) and a lone dot on the header
> would be a fifth colour family competing with the four the profile section
> actually encodes (§1.1) — one entity's own type is not a categorical worth a
> hue when it is stated in words two characters away.

### 2.11 KPI tiles

> **Shipped deviation (R2-E3, manager-accepted 2026-08-29):** the eight tiles render as **4 rows × 2 columns** inside the ruled `[1.0, 2.0, 1.4]` middle column — at 1280 px that column measures ~344 px, so four tiles across would be ~74 px each with every label broken mid-word (`e3_find_top_1280.png`). One constant (`views_find.TILE_GRID_COLS`) flips it back if the column widths are re-ruled.


**R2 rewrite (L30, L31 — user ruling items 3 and 7: "profile space not
optimised... coverage line reads as leftovers" / "every KPI positioned against
the index baseline").** Two changes at once, both forced by the same feedback:
the tile row moves into COLUMN 2 of the section's three-column row 1 as a
**2×4 grid** (was a seven-tile wrapping row spanning full width), and the
now-eighth tile absorbs a metric that used to live in the coverage caption
(§2.12, RETIRED below) rather than growing the row to nine.

- **Form.** EIGHT tiles in a 2×4 grid filling column 2, each **value + label +
  baseline subline** (the Lorraine `_kpi_tile` HTML pattern, copied in —
  `st.metric` has no subline and the subline is the point). Tile chrome:
  `NEUTRAL` fill, `BORDER` hairline, `INK` value, `INK_SECONDARY` subline — all
  from `palette.py`, never inline hex.
- **Encoding.** In fixed order (`lib/baselines.py`'s `KPI_COLUMNS`, L31): size
  full · size fractional · concentration (HHI value, no class word — L32) ·
  breadth (subfields at or above the fractional floor) · SDG-tagged share ·
  frontier top-quartile share · PP(top10%) with its interval · **publications in
  {bonus_year} (bonus year)** — the eighth tile, see the rejected alternative
  below for why this one and not a relocated coverage item. **Every subline now
  positions the value against the INDEX**, not just its own denominator: "index
  median {m} · higher than {pct} of institutions" (`copy.FIND["TILE_BASELINE_SUB"]`,
  L29/L31), the percentile computed over institutions with a non-null value for
  that column; the tooltip on every tile carries the skew caveat — the index is
  itself dominated by HEIs, so "median" is a population fact, not a norm to
  chase. This is what "every KPI pairs value with denominator/coverage" (L11)
  now MEANS for this row: the reference moved from "a raw count's own unit" to
  "where this seed sits in the population."
- **Interaction.** None (a tile is not a control). The interval on PP(top10%)
  renders as a value plus its bounds, never as a bare point estimate (RULES
  §9.6). Concentration (L32) shows the HHI value with its index percentile and
  median and NO class tag — `hhi_class`'s 1,500/2,500 textbook thresholds are
  RETIRED from the UI (they called 86% of the index "generalist," which is not
  a distinction); the coherence check that ratified this is the 16-seed table
  in `progress/2A_P.md`.
- **Empty state.** `n/a` for any tile the data cannot support — never 0, never a
  hidden tile: a missing indicator is information (§1.6, `palette.NA_MARK`). A
  tile whose baseline cannot be computed (e.g. a metric with too few non-null
  index values) shows the value alone and states why the subline is absent,
  never a blank subline.
- **Export.** The same eight numbers are the seed's row in every CSV the page
  writes.

> **Rejected alternative (tile form):** `st.metric` with its delta arrow, one
> call per tile. Rejected twice over: it has no subline, so the baseline
> sentence would have to move into a caption underneath the row and stop being
> attached to its own number; and its delta arrow implies a change-over-time
> read that none of these eight measures has (they are all one snapshot),
> which is exactly the "does the form imply something the data doesn't"
> failure the Studio rules flag.
> **Rejected alternative (eighth tile):** re-promote one of the four items §2.12
> relocates OUT of the coverage line (ERC-classified share, catch-all share,
> SDG-tagged share is already tile #5, L2f-eligible count) back into tile #8.
> Rejected because it would directly contradict the SAME ruling in the SAME
> paragraph that just moved those items OUT for being over-weighted relative to
> the other seven — a coverage share deserves caption weight, not tile weight,
> whichever slot it sits in. Bonus-year publications is not a coverage
> statement at all: it is a genuinely new fact (does this institution have any
> 2025-indexed output yet) that pairs naturally with the two size tiles right
> beside it, and it is exactly the column `lib/baselines.py`'s `KPI_COLUMNS`
> (L31) already commits to — keeping it avoids a cross-stream mismatch between
> what this spec asks for and what the baselines module computes.

### 2.12 Coverage caption — RETIRED (L30)

**R2 (user ruling item 3: "coverage line reads as leftovers").** The former
single caption line under the tiles is REMOVED, not shrunk: its four items each
move to the ONE place they are actually read, so a reader meets each number
next to the panel it qualifies instead of in a pre-emptive list nobody has
context for yet.

| Former coverage item | New home |
|---|---|
| ERC-classified mass share | ERC panel caption (§2.20) |
| Catch-all (811) share | Top-topics panel caption (§2.17) — it already counted the flagged rows from data there |
| L2f-eligible subfield-cell count | The L2f tab's own intro line (Benchmark section, outside the profile — L29's "How to read the lenses" expander) |
| SDG-tagged share | STAYS a KPI tile (§2.11, tile #5) — it was already tile-worthy, not a coverage leftover |

- **Form.** No form of its own any more — this row exists only as the
  relocation record above, kept in this document rather than silently deleting
  the section number (the same "SUPERSEDED, not deleted" convention §2.10 uses
  for the old §2.2 seed card).
- **Encoding / Interaction / Empty state / Export.** N/A — see each item's new
  home for its own rules; nothing about a relocated item's OWN behaviour
  changes, only where on the page it is read.

> **Rejected alternative:** keep the caption line but shorten it to the two
> items that did not find another home. Rejected because a caption with two
> items reads exactly like the four-item version it replaces — the actual
> complaint (item 3) was the caption's POSITION and cognitive weight relative
> to the tiles above it, not its item count, and a shorter version in the same
> place would not have answered it.

### 2.13 Subfield wordcloud

**R2 (L30):** moves from "left half of a wide row shared with the yearly
breakdown" to COLUMN 3 of row 1 (identity | tiles | wordcloud, `[1.0, 2.0, 1.4]`)
— it now sits beside the tiles it illustrates, not beside the breakdown pair,
which has its own row (§2.14) with the global panel it was never paired with
before R2.

- **Form.** A PNG (Lorraine's `WordCloud` → `PIL` → `st.image` pattern, copied
  into `lib/wordcloud_png.py`), filling column 3 of the section's row 1.
- **Encoding.** **Word size = the subfield's works on the CURRENT basis; word
  colour = its domain colour** (`palette.domain_color` through a `color_func`),
  so the cloud re-tints itself when the tree changes and re-weights itself when
  the basis changes. The caption states both encodings — a wordcloud whose size
  channel is unstated is a decoration.
- **Interaction.** None: it is a raster. Every number it hints at is available
  precisely in §2.16 immediately below it, which is what makes an
  interaction-free ornamental form acceptable here rather than a dead end.
- **Empty state.** A seed with no subfield mass renders the empty-state panel
  (`NEUTRAL` fill) and the reason, never a blank white box.
- **Export.** None of its own (§1.7: no PNG-only artefact) — its underlying
  frame is exactly §2.16's CSV.

> **Rejected alternative:** a plotly treemap of subfields, sized by works and
> coloured by domain. It is interactive, exportable and quantitatively honest —
> and it was still rejected: the user asked for the Lorraine cloud by name, and
> the treemap would duplicate §2.16's bar panel in a second, weaker geometry
> (area comparisons across non-adjacent rectangles) two rows above it. The cloud
> earns its place by being the one deliberately impressionistic object on the
> page; a second precise chart would not.

### 2.14 Yearly breakdown pair

**R2 (L30):** this pair's own FORM is unchanged — it was already the global +
yearly pair under one control before R2. What changes is its ROW: it moves out
of sharing a row with the wordcloud (§2.13, R1) into its OWN full-width row 2,
directly under row 1's three columns, so both panels get the section's full
width instead of half of it each.

- **Form.** Row 2 of the section, full width: two figures side by side under
  ONE `st.segmented_control` and ONE shared chip legend, both sitting ABOVE the
  pair. **Left** = global horizontal bars, one per series, sorted by volume
  descending, direct end labels, no legend (`charts.fig_breakdown_global`);
  **right** = per-year GROUPED bars (`charts.fig_breakdown_yearly`). Both
  render `showlegend=False`; `charts.chip_legend_html` is the ONE legend for
  the pair (Lorraine `render_chip_legend`).
- **Encoding.** The segmented control swaps the IDENTITY FAMILY: OpenAlex domain
  (from `profile_data.yearly_by_domain`) ↔ document type (from the R1 artefact
  `doctype_by_year.parquet`). Series order is the family's FIXED order
  (`palette.OA_DOMAIN_ORDER` / `palette.DOCTYPE_ORDER`), never a data-dependent
  sort, and a series that is zero across every year is KEPT so the absence is
  visible. Years are STRINGS (a numeric x-axis autoranges and ticks unlike every
  other chart here). The window covers the analysis years plus 2025 as a labelled
  **bonus year** — partial by construction, said so in the caption, taken from
  CFG rather than typed.
- **Interaction.** One control drives both figures, so they can never disagree.
  Hover gives series, year and volume; the direct end labels on the left panel
  mean the global read needs no hover at all.
- **Empty state.** A year with no output still renders its (empty) group — a
  missing year is data. A seed with no doc-type rows falls back to the domain
  view and discloses the fallback, never silently.
- **Export.** The pair's frame is one CSV (institution × year × series × volume).

> **Rejected alternative:** ONE stacked bar per year, with the segmented control
> choosing what is stacked. It is more compact and gives the year total for free
> — and it is forbidden here: Lorraine's standing rule is that "a bar chart may
> never stack a second categorical dimension", because a stack makes the year
> total the figure and hides each series' own trajectory, which is the only claim
> this pair exists to make. (The same rule is why the grouped geometry uses
> explicit `offset`/`width`: `offsetgroup` is broken on plotly 5.24.1.)

### 2.15 Panel — Fields (share + SI)

- **Form.** `st.expander(expanded=False)`. Inside: `charts.fig_share_si(family="oa")`
  — two aligned panels of one figure sharing the y axis; share bars left with the
  volume in a left text gutter, SI lollipops right against a dashed reference at
  the neutral value (A/B #3 and #4 winners), plus a **unit grid** (R2/L34) — a
  light `GRID`-coloured vertical line at every integer 1, 2, 3 … up to the SI
  axis's own max, tick-labelled at those integers, so a reader can place a dot
  at "about 2.3×" without hovering.
- **Encoding.** One row per field, coloured by the field's DOMAIN (inheritance,
  §1.1). Share is on the current basis; SI has **no floor at field grain** (the
  G6 floor applies to subfields only — the data contract says so on both rows;
  L34 confirms this row explicitly: "Fields: no floor," only the zero-volume
  no-mark rule applies here). A field's mark is FILLED (never hollow) whenever
  it has a defined SI and nonzero volume, since the solid/hollow floor distinction
  is a subfield-grain concept (§2.16) that does not exist at field grain.
- **Interaction.** A sort toggle: **volume** (share descending) | **taxonomy**
  (domain → field id). Colour follows the entity, never the rank, so the toggle
  never repaints anything (`tests/test_charts.py` pins this).
- **Empty state.** A field with zero mass is absent (it is not a fact about the
  seed); a field with mass but undefined SI keeps its bar and gets NO SI mark —
  never a dot at zero, never a dot at the neutral value; a field with mass but
  ZERO volume also gets no mark, whatever any `si_status` might otherwise say
  (R2/L34 — the ERC-bug fix generalised to every panel this builder serves).
- **Export.** CSV of the panel's frame, all columns, full precision.

> **Rejected alternative:** a single chart with SI encoded as bar colour
> intensity over the domain hue. Rejected because it destroys the domain
> inheritance that makes every panel in this section legible as one system (a
> field would no longer be its domain's colour), and because a lightness ramp
> laid over four different hues is not comparable across hues — the reader cannot
> tell a "strong" yellow from a "weak" green.

> **Fix X3 (Refinement R1, inspection finding I-4).** A/B #4's own verdict
> (§5, "left text gutter, numbers right-aligned against the zero baseline")
> held at 1280 px but broke at 390 px: the gutter number was a SEPARATE
> annotation from the y-axis category label, so nothing kept the two apart at
> the narrow breakpoint — they merged into unreadable text ("hemistry,
> Genetics and Molecular Biolog213.7"), truncated from BOTH ends. Verdict kept,
> mechanism made robust: the volume now folds INTO the y tick text as ONE
> right-anchored string per row (`lib/charts.py::_tick_display`), so there is
> nothing separate left to collide with; a label longer than
> `charts.MAX_LABEL_CHARS` is ellipsised from the RIGHT only, never the left,
> with the full label kept in hover/customdata (`_truncate_label`); the left
> margin is reserved from the longest resulting string
> (`_gutter_margin_px`) because `yaxis.automargin` — measured on plotly 5.24.1
> — only stops a label being clipped by the figure's OUTER edge, not by the
> plot's own bars, so it cannot be relied on alone to keep a long label out of
> the data area. **Robustness rule for any future y-axis-label form in this
> app:** a caption or number placed BESIDE a category label must never be laid
> out by a second, independent text system (a separate annotation, a second
> `<text>` element) at a width where the two can run out of room to stay
> apart — fold them into one string, or reserve the margin the wider of the
> two actually needs, never assume. Proof: `tests/test_charts.py`'s
> truncation/margin tests plus `tests/ui/smoke.py`'s bounding-box check at
> 390 px and 1280 px (`progress/R1_X3.md`).
>
> **R2 update (L35, user ruling item 10 — REVERSES the ellipsis half of this
> fix, keeps the folding half).** The one-string-per-row mechanism above is
> UNCHANGED and still the reason there is nothing to collide with; what changed
> is what happens to a string over budget. X3 ellipsised it from the right
> (`_truncate_label`/`MAX_LABEL_CHARS`/`ELLIPSIS`, all now deleted, not left as
> dead code); R2 WRAPS it onto at most two lines at a word boundary instead
> (`charts.wrap_label`), because the user's own read of a shortened field name
> was that losing text is worse than a taller row. Two mechanical consequences
> the next editor should know: (1) `_gutter_margin_px` now measures the
> longest LINE of a (possibly two-line) tick string, not the longest whole
> string — a wrapped row's own margin need can be SMALLER than an unwrapped
> row's, which is correct, not a regression; (2) `charts.row_height` grows a
> row's own budget by `WRAP_ROW_FACTOR` (measured ≈1.7×) for every row whose
> label wrapped, via its new `n_wrapped` argument, so a frame with several long
> names is proportionally taller rather than uniformly cramped. Proof:
> `tests/test_charts.py`'s wrap/row-height/margin tests (§2.15) plus the R2
> render proof PNG (§5).

### 2.16 Panel — Top subfields (share + SI)

**R2 rewrite (L34, user ruling item 8/9 — "top 30, no taxonomy sort" / "SI
charts: unit grid lines; no SI mark at zero volume; harmonised floors").**
Three changes at once, all measured on IFPEN's real profile (top-30 subfields
carry 2 cells ≥30 fractional mass but 17 ≥10 — the old single 30-floor was
throwing away a disclosable signal on 15 of those rows):

- **Form.** As §2.15, `charts.fig_share_si`, on the **top 30 subfields by
  volume** (the caller passes exactly 30 rows — `charts.py` itself types
  neither 20 nor 30 anywhere; the cut is E3's, not the builder's), plus the same
  unit grid described in §2.15.
- **Encoding.** Domain colour inherited through the subfield → field → domain
  chain, so the panel re-tints with the tree. **SI display is now a THREE-WAY
  floor on fractional mass** (`si_status`, harmonised across subfields/ERC/SDG,
  the panel floor — the lens-ranking floor at 30 is untouched, ratified
  separately): mass ≥30 → **solid** (filled) mark; 10 ≤ mass <30 → **hollow**
  mark (white fill, coloured outline) — a below-the-old-floor cell disclosed
  instead of erased; mass <10, or **zero volume regardless of mass**, → no
  mark at all, `n/a` in the row's hover. On real Gdansk data most subfields
  still sit below even the 10 floor, so a mix of solid, hollow and no-mark rows
  in one panel is the common case, not an edge case.
- **Interaction.** **No sort toggle** (reverses the taxonomy | volume toggle
  §2.15 keeps) — always volume order, because "top 30" is itself a
  volume-ordered concept and a taxonomy re-sort of a volume-defined cut reads as
  an arbitrary 30 rows in ID order. The depth of the cut (top 30) is stated
  parametrically in the panel caption, not typed.
- **Empty state.** If NO row in the frame has a mark-eligible SI (mass <10
  throughout, or every row zero-volume), the figure collapses to a single share
  panel and the caption says why, rather than drawing an empty second axis
  (`charts.fig_share_si` does this itself).
- **Export.** CSV of the FULL subfield frame, not just the displayed top-30 cut
  — the §1.7 rule that an export is never the screen's truncation.

> **Rejected alternative:** keep the single 30-floor (solid-or-nothing) and only
> add the unit grid. Rejected on the IFPEN measurement above: a single floor
> would still show a 2-of-30-marked panel that reads as "SI is mostly undefined
> here," when 17 of 30 cells actually carry a usable (if less certain) reading —
> the hollow mark is what lets the chart say "usable, but read it with more
> caution" instead of forcing a binary defined/undefined choice the data does
> not actually make.

### 2.17 Panel — Top topics

- **Form.** `st.expander(expanded=False)` → `charts.fig_topics`: horizontal share
  bars for the top topics by share, volume in the left gutter. Topic names are
  the longest labels in the app, so this panel is the R2 wrap mechanism's
  (§2.15's L35 note, `charts.wrap_label`) hardest real test — a topic name over
  budget now wraps to two lines instead of losing its tail.
- **Encoding.** Colour = the topic's DOMAIN (inherited through the active tree).
  A **catch-all / out-of-scope (811) topic is flagged three ways at once**: a
  glyph prefixed to its axis label, its domain hue at `palette.MUTED_OPACITY`,
  and a hover line naming it — shape and opacity, never a new hue (§1.1).
- **Interaction.** Sort toggle volume | taxonomy (domain → field → subfield →
  topic). Hover gives the topic, its share and its volume.
- **Empty state.** The panel caption **counts the flagged topics from the data**
  (`topics_dim.is_excluded.sum()`), never from a typed number (L10) — a flagged
  topic is shown and counted, never dropped, because its presence is exactly the
  thing a reader needs to discount.
- **Export.** CSV of the full topic frame with `is_excluded` as a column, so the
  flag survives outside the app.

> **Rejected alternative:** exclude the catch-all topics from the panel entirely
> (the pre-R1 811 toggle's behaviour). Rejected because the toggle was REMOVED in
> R2.19/R2.20 precisely so the catch-all mass would be disclosed rather than
> switched off: hiding those rows makes a seed's profile look cleaner than the
> data is, and the share they carry is a caveat on every other number in the
> section.

### 2.18 Panel — Frontier positioning

**R2 rewrite (L33, user ruling item 5 — "frontier panel unreadable/slow: toggle
top-200-by-volume ↔ all global-top-quartile topics").** The panel used to plot
EVERY scored topic at once, which on a large seed is both visually dense and,
per the feedback, slow. It now offers two MODES via a segmented control, each
handing `charts.fig_frontier` a pre-filtered frame — the builder's own API is
unchanged, it never knows which mode produced its input.

- **Form.** `st.expander(expanded=False)` → a segmented control, **"Top {n}
  topics by volume"** (n = `FRONTIER_TOP_N`, a module constant fixed at
  two hundred, `charts` module docs) | **"All topics in the global top quartile
  of emergence"** (`top25pct_frontier == True` — NOT a subset of the top-N mode;
  a topic can be small-volume and still top-quartile emergence, or vice versa),
  default = the volume mode. Below it, `charts.fig_frontier`: a scatter of the
  filtered topic set, **x = Expansion, y = Acceleration**, with the two quadrant
  lines at the origin on both axes (verified against `topics_dim.quadrant`,
  which flips sign exactly there).
- **Encoding.** Bubble area = the topic's mass on the current basis (`sqrt` scale
  between a floor and a ceiling in px, so a big topic cannot swallow the panel);
  colour = domain; **a top-quartile frontier topic carries an `INK` outline** —
  a shape signal on top of the family colour, never a fifth hue (in the
  top-quartile MODE every plotted point therefore carries the outline; in the
  volume mode it marks the subset that also clears the quartile bar).
- **Interaction.** The segmented control swaps which frame `fig_frontier`
  receives; hover names the topic and gives expansion, acceleration and mass in
  either mode. No zoom, no animation (house rule: no motion).
- **Empty state.** Topics with no frontier score are DROPPED from the scatter and
  **counted in the caption**, together with the excluded ones, in WHICHEVER mode
  is active — the caption states the count shown and the count excluded/unscored
  for that mode specifically, never a number left over from the other one. A
  seed with no scored topic renders the reason, not an empty axis, in either mode.
- **Export.** CSV of every topic with its expansion, acceleration, quadrant,
  top-quartile flag, `rank_volume` and mass — scored and unscored alike, ALL
  topics regardless of which mode is on screen, so the export is never a
  function of the toggle.
- **Copy (binding, from DESIGN §4).** The panel says that this measures
  **attention dynamics, not novelty or quality**, and that **low can mean
  foundational**. The sentence is not optional decoration: without it a
  bottom-left quadrant reads as a verdict.

> **Rejected alternative:** a 2×2 quadrant grid of topic COUNTS (a heatmap of
> four cells) instead of the scatter. It is far more compact and needs no
> caveating about position — and it was rejected because it throws away the two
> continuous measures that make the panel worth showing, turning a position into
> a bucket, and because the quadrant boundaries sit at zero on both axes, so a
> topic just either side of a line would be assigned to opposite cells with no
> visible indication of how marginal that assignment is.
> **Rejected alternative (for the R2 toggle specifically):** a single combined
> mode showing the UNION of top-200-by-volume and top-quartile-emergence.
> Rejected because a union hides which criterion put a given topic on the
> chart — the whole point of the user's own two-mode framing was to let the
> reader ask "what does my BIGGEST work look like on this axis" and "what does
> my MOST EMERGENT work look like" as two separate questions, and a union
> answers neither cleanly.

### 2.19 Panel — SDG profile

- **Form.** `st.expander(expanded=False)` → `charts.fig_sdg`, which delegates to
  `charts.fig_share_si` with ESI in the SI slot, so the reader learns ONE form
  and reuses it (Lorraine `same-read-same-form`) — including the R2 unit grid
  (§2.15) and the harmonised solid/hollow/no-mark floor (§2.16), since `fig_sdg`
  reads whatever `si_status` the caller's frame carries with no SDG-specific code.
- **Encoding.** Sixteen bars in **fixed SDG number order** (never sorted by
  value), each in its **official UN colour**; ESI dots against the same dashed
  neutral reference, with the unit grid at every integer. **Axis labels now carry
  the goal number** (L36, user ruling item 11 — "SDG labels carry the number"):
  `sdg_label_numbered` ("SDG {n} · {short label}", number from the resource,
  never typed) when the caller's frame carries that column, falling back to the
  plain `sdg_label` otherwise (`charts._LABEL_COLS` preference order,
  `_first_col`). Every bar still carries its label on the axis, which is the
  structural relief for the UN palette's measured CVD and contrast failures
  (§1.1, family 3): identity is never colour-alone here.
- **Interaction.** Hover gives the goal, its share, its mass and its ESI. Sort is
  FIXED to goal order — the one panel in the section with no sort toggle, because
  the SDG numbers are a canonical sequence a reader navigates by position.
- **Empty state.** **SDG 17 is not covered by the classifier** and is stated as
  such from `palette.SDG_UNCOVERED`, never typed. A goal with zero tagged mass
  renders a zero-length bar in its place, never a gap.
- **Export.** CSV with `sdg_number, share, esi, mass`.
- **Copy (binding).** The caption states the **multi-label denominator**: the
  share is over SDG-TAGGED fractional mass, one work can carry several goals, and
  **these shares therefore do not sum to one**. It also carries the epistemic
  label from DESIGN §5 — this is a policy-vocabulary lens, not a field
  classification.

> **Rejected alternative:** a stacked bar of the SDG mix, one bar per
> institution, so seeds could be compared later in the Compare tab. Rejected as
> arithmetically false for THIS measure: the labelling is multi-label, so the
> segments do not partition anything and a stack would assert a whole that does
> not exist. The same reason forbids a pie.

### 2.20 Panel — ERC profile

**R2 bug fix (user ruling item 4/9 — "concentration KPI wrong" led the review to
the actual finding: "ERC bug", a specialisation dot floating on a panel with NO
classified publications at all).**

- **Form.** `st.expander(expanded=False)` → `charts.fig_erc` (again
  `fig_share_si`): the ERC evaluation panels, share left, SI right, with the R2
  unit grid (§2.15) and the harmonised solid/hollow floor (§2.16) — again no
  ERC-specific code, `fig_erc` reads whatever `si_status` the frame carries.
- **Encoding.** One row per panel, coloured by its **ERC DOMAIN** — three hues,
  `palette.ERC_DOMAIN_COLORS` — and grouped in the fixed PE → LS → SH order under
  `sort="taxonomy"`. No OpenAlex domain hue may appear in this chart
  (`tests/test_charts.py` asserts the two sets do not intersect): it is a
  different taxonomy of the same output, and colouring it like the OA panels
  would invite a false one-to-one reading. **A panel with ZERO classified mass
  NEVER gets an SI mark**, whatever its `si` or `si_status` value happens to
  hold — this is the exact bug the user saw (a dot at a numeric SI value on a
  panel with no publications behind it) and it is now a hard rule in
  `charts.fig_share_si` itself (the zero-volume override, §2.15), not a
  per-caller precaution, so it cannot recur in any panel this builder serves.
- **Interaction.** Sort toggle: taxonomy (ERC domain, then panel code) | volume.
- **Empty state.** A panel with zero classified mass keeps its row at zero rather
  than disappearing (its SHARE bar is a visible zero) — the ERC structure is
  fixed, and a missing panel is a fact about the institution, not about the
  taxonomy; per the fix above, that same zero-mass row draws NO SI mark.
- **Export.** CSV with `panel_code, panel_label, erc_domain, share, si, mass`.
- **Copy (binding, DESIGN §5).** The caption carries the **weak-panel caveat**
  (Biotechnology and Arts are thinly and unevenly populated, so their share and
  SI carry less weight than the others) and, when basis = full, the
  **fractional-only** disclosure.

> **Rejected alternative:** small multiples — three mini-charts, one per ERC
> domain, side by side. Rejected because the panels' shares are all on ONE
> denominator (the institution's classified mass), so three separate x-axes would
> either be three different scales (incomparable) or three copies of the same
> scale (wasteful), and the grouped single chart already carries the domain
> grouping through colour and the taxonomy sort.

### 2.21 Controls row (Benchmark section head)

- **Form.** One horizontal row directly above the lens tab strip: depth radio ·
  C1 checkbox · L7 checkbox · a "Post-filters" expander. See §1.3 for the
  sidebar/section split and the unchanged widget keys.
- **Encoding.** No colour, no chart. Each control carries a `help=` tooltip that
  explains what the option DOES, not what it is called — the gate-2A complaint
  was that the sidebar named options without explaining them.
- **Interaction.** Every widget keeps `persist_state="session"`, so the settings
  survive a Menu ↔ Find round trip; the post-filters stay inside a collapsed
  expander so the default page shows six controls, not fifteen.
- **Empty state.** When a post-filter empties a list, the emptied lens names the
  responsible filter(s) by themselves (§1.6), and the strip above the title names
  every off-default dimension including tree and basis.
- **Export.** The active control state rides in every CSV as constant columns and
  in the filename.

> **Rejected alternative:** a single "Advanced" expander holding depth, C1, L7
> and all six post-filters together. Rejected because depth and the optional
> lenses are ORDINARY controls a reader touches on the first visit, while the
> post-filters are the advanced ones; burying all nine at the same depth would
> hide the two that gate-2A feedback said should be closest to the tables.

### 2.22 Ranked tables — the R1 changes (supersedes §2.4's column list)

- **Form.** Unchanged: the shared `lib/ranked.py` renderer, same form on every
  lens tab, `st.column_config.ProgressColumn` for the score (A/B #1, stream D1).
- **Encoding — what changed (L21, L22).** (a) **Two size columns**, full AND
  fractional, in every table (lens, concordance, aspirational, tail search) and
  in the CSV — a single size column forced the reader to know which counting
  basis was in play. (b) **The badge column is REMOVED** from all tables; the
  seed-level badges live in the profile header (§2.10), and institution type
  stays as plain text plus the type post-filter. (c) **Country NAMES** (English)
  everywhere in the UI — tables, filter labels, the strip, the header — while the
  CSV keeps `country_code` AND adds `country`. (d) **Evidence is lens-specific**:
  the top shared cell for THAT lens (`argmax_j min(seed_j, cand_j)` over the
  lens's own substrate row pair), labelled in the lens's own namespace — field,
  subfield, topic, ERC panel or SDG label — with its contribution share of the
  score. The pre-R1 "Top field" column only ever made sense for L1.
- **Interaction.** Unchanged (sort, tail search, add-to-basket, CSV download).
- **Empty state.** Unchanged (§1.6), except that the emptied-list message now
  names countries by NAME.
- **Export.** CSV gains `country`, `total_frac_2020_2024` and the lens-specific
  `evidence`; original competition ranks are still preserved with their gaps.

> **Rejected alternative:** keep the badge column and simply narrow it to an icon.
> Rejected on the user's own ruling (#8) and on the arithmetic behind it: the
> umbrella badge fired on 158 of 7,557 institutions in calibration, so on a
> typical 30-row table the column is empty on every row and costs width on all of
> them, while the information it carries is available as a filter and on the one
> row that matters — the seed's own header.

---

## 2 ter. View specs — the Compare and Collaborate views (Phase 2B, stream V)

**Produced by:** stream V, 2026-08-29, in wave 1 — before `pages/2_⚖️_Compare.py`
and `pages/3_🤝_Collaborate.py` exist, against the `BUILD_PLAN_2B.md` §4 column
contracts (as amended by the wind tunnel's E16). Same row format as §2 and
§2 bis: form / encoding / interaction / empty state / export, and one NAMED
rejected alternative each. Builders: `lib/charts_compare.py` (pure plotly, no
Streamlit, no hex literal, no digit in any string — the same three scans
`lib/charts.py` passes).

**The one rule every row below obeys (2B-1).** In Compare and Collaborate the
INSTITUTION is the identity: the categorical axis names the field, subfield,
panel, goal, quadrant or grey state, and the COLOUR names the institution
(`palette.INSTITUTION_COLORS`, §1.1). No OA-domain, ERC, SDG or document-type
hue appears in any figure of these two pages. That is not a preference — the six
institution hues and the four OA hues FAIL the validator as one ten-slot set
(`palette_validation.txt` run 10), and the coexistence rule is what carries
them.

**Slot assignment is stable by `inst_key`, never by click order** (A8). Adding a
comparator does not repaint the ones already on screen unless the newcomer's key
falls between two of them, and removing one never repaints the rest. The k ≤ 5
Studio identity budget is exceeded here by design, ONCE, and this stability is
the justification (`palette.py`, FAMILY 5).

**Two things are the caller's, not the builder's, on every row below:** the
caption (which must state the denominator, the basis, the tree and the snapshot)
and the legend placement. `charts_compare.institution_legend_html` is the ONE
legend of a Compare view; every figure ships `showlegend=False`. **The legend is
mandatory, not decorative** — the palette carries a deutan ΔE 7.6 pair and two
sub-3:1 contrasts (run 9), and the legend + the axis labels + the per-mark hover
ARE the secondary encoding that makes those legal.

**Reading order note the captions must carry** (measured need, from the render
proof): in a lane-split mirror the institutions read TOP TO BOTTOM of each row in
the same order the legend reads LEFT TO RIGHT. Without that line the reader has
to infer the mapping from colour alone, which is precisely what the CVD floor
forbids relying on.

### 3.1 Institution strip (the Compare header)

- **Form.** Not a chart: a `st.columns` strip of {k} identical cards, one per
  compared institution, in SLOT order. Each card carries a colour swatch (the
  institution's own `institution_color`), the display name, the type, the
  country and the size on the current basis. Directly under it, the standard
  "Filtered by…" strip (§1.4) whenever any control is off-default.
- **Encoding.** The swatch is the ONLY place the colour↔institution binding is
  stated in full, so it is repeated in the chip legend above every figure. Size
  is a number, not a bar: {k} bars of "total output" would be a chart nobody
  asked for and would compete with the panels below (§1.6, "is it even a chart").
- **Interaction.** A remove control per card and one "add" search box, both
  writing the basket; the cap is `state.BASKET_MAX` and the copy line says so
  from that constant, never from a typed numeral.
- **Empty state.** Fewer than two institutions → the panels are not drawn at
  all and the page shows the add affordance plus the Find link. One institution
  is a PROFILE, and the app already has one.
- **Export.** The strip's own fields are the first sheet of the xlsx workbook
  (2B-13) and the header block of every CSV.

> **Rejected alternative:** a single table with one row per institution instead
> of cards. Rejected because the swatch is doing identity work here, and a
> swatch inside a dataframe cell cannot be styled without the `ProgressColumn`
> hack that R1 already removed from the ranked tables (L22); cards also degrade
> to a stack at 390 px, where a six-column table would scroll sideways — which
> §1.8 forbids outright.

### 3.2 Fields mirror (dot rows)

- **Form.** `charts_compare.fig_mirror_dots(family="oa")` — two aligned panels of
  ONE figure sharing the y axis: one row per field, {k} coloured dots on the
  share axis left, the mass-paired specialisation dots right against the dashed
  neutral reference and the unit grid. **This is A/B #5's winner, measured**
  (§6). It replaces the grouped bars the plan first proposed, which the wind
  tunnel measured at 2.6 px per bar for 26 fields × 6 institutions (A4).
- **Encoding.** Dot = institution. `DOT_PX` diameter with the 2 px SURFACE ring
  the dataviz mark specs require of overlapping marks. Share on the current
  basis; no floor at field grain (§2.15 — the G6 floor is a subfield concept).
  When any row of the frame would put two marks closer than half a dot, EVERY
  row splits into {k} lanes, one per institution, in slot order — all-or-nothing,
  so a lane means the same thing in every row and a reader can scan one
  institution down the panel. An undodged frame is exactly as tall as the
  profile panel it mirrors. Alternate rows carry a `NEUTRAL` zebra band whenever
  lanes are on, which is what keeps {k} lanes reading as one row.
- **Volumes are in the HOVER, not in a gutter.** A/B #4's left gutter is a
  profile form and does not survive {k} institutions: one gutter column cannot
  hold six numbers per row. The hover names the institution in words, gives the
  share, the volume on the current counting basis and the SI; the xlsx and CSV
  carry the same numbers for the reader who wants a column.
- **Interaction.** Sort toggle **volume** (share summed across the compared set,
  descending) | **taxonomy** (domain → field id). Colour follows the entity, so
  the toggle never repaints anything. Tree and basis toggles are the page's, not
  the panel's.
- **Empty state.** A field an institution has no row for gets NO dot for that
  institution — never a dot at zero. A `si_status` of `none`, a NaN SI, or a
  zero volume gets no specialisation mark and `palette.NA_MARK` in the hover; a
  `thin` cell gets a HOLLOW dot (SURFACE fill, institution-coloured outline), so
  a below-the-floor cell is disclosed rather than erased. If NOTHING in the
  frame is eligible for an SI mark, the figure collapses to the share panel
  alone rather than showing an empty half.
- **Export.** CSV of the panel frame, all columns, full precision; one xlsx
  sheet per view (2B-13).

> **Rejected alternative:** small multiples — one mini profile panel per
> institution, 26 field bars each. Measured and rejected in A/B #5 (§6): it is
> compact (900 px against 2,020 px) but it costs 900 px of eye travel to compare
> one field across the set where the dot row costs 74 px, it gives each
> institution a 299 px plot where the dot row gives 496 px, its wrapped category
> labels collided at the shipped pitch, and it has no room for the mass-paired
> SI panel at all — which would break 2B-2 outright.

### 3.3 Subfields mirror (dot rows, top-N shared)

- **Form.** `fig_mirror_dots(family="oa")` on a subfield frame. Identical
  grammar to §3.2 — same read, same form.
- **Encoding.** The N rows are the subfields with the largest share **summed
  across the compared institutions** (A3). This is a ruling, not a default: the
  INTERSECTION of the per-institution top-6 lists is one subfield at k = 6 and
  two at k = 4, measured on real sets, so an intersection rule would render a
  one-row panel and call it a comparison. The caption must state the selection
  rule, because "top subfields" reads as "each institution's top" unless it is
  told otherwise. Subfield SI carries the G6 floor, so `si_status` does real work
  here: solid ≥ 30, hollow 10–30, absent below (L34).
- **Interaction.** Same sort toggle; N is a module constant surfaced in the
  caption as a `{placeholder}`.
- **Empty state.** As §3.2. A subfield that only one institution holds still
  earns its row if its summed share ranks — the other {k}−1 marks are simply
  absent, which IS the finding.
- **Export.** As §3.2.

> **Rejected alternative:** show every subfield the set touches (252 rows).
> Rejected on the same arithmetic that killed the grouped bars: 252 rows at the
> lane-split pitch is over 15,000 px, and a panel nobody can reach the bottom of
> is not a panel. The full frame stays available through the export.

### 3.4 ERC mirror (dot rows)

- **Form.** `fig_mirror_dots(family="erc", sort="taxonomy")`.
- **Encoding.** One row per ERC evaluation panel, in the fixed PE → LS → SH
  domain order. **The ERC domain does NOT colour anything here** — that is the
  coexistence rule biting: in the profile the three ERC hues are the identity,
  in Compare the institution is, and the panel's domain lives in the row label
  and in the taxonomy sort instead. Share denominator is ERC-classified mass;
  the caption states each institution's classified share (2B-6), which is the
  only honest way to read a thin institution's panel.
- **Interaction.** Sort toggle as §3.2; taxonomy is the default here because the
  PE/LS/SH grouping is the reason the panel exists.
- **Empty state.** A panel with zero mass for an institution gets no dot for it.
  The weak-panel caveat is caption text (§2.20), never a mark.
- **Export.** As §3.2.

> **Rejected alternative:** keep the ERC domain hues and encode the institution
> by marker SHAPE (circle / square / triangle …). Rejected because shape is a
> far weaker channel than hue at 12 px, because six shapes exceed what anyone
> can hold, and because it would put two identity families in one figure — the
> exact thing run 10 measured as unsafe.

### 3.5 SDG mirror (dot rows, numbered labels)

- **Form.** `fig_mirror_dots(family="sdg", sort="taxonomy")`.
- **Encoding.** One row per goal in fixed goal order, labelled with
  `sdg_label_numbered` (L36) so the goal NUMBER is on the axis — which matters
  more here than anywhere: the UN palette contains two near-identical ambers
  (run 7) and the app's rule is that no chart may rely on telling SDG colours
  apart. In Compare that rule is free, because the SDG hues are not on screen at
  all; the numbered label is doing the work it was already doing. ESI sits in the
  specialisation slot with its own axis title. Shares do NOT sum to one
  (multi-label) and the caption says so; goal 17 is absent from the classifier
  and the caption states that from `palette.SDG_UNCOVERED`.
- **Interaction / empty state / export.** As §3.2, with `si_status` from SDG
  mass.

> **Rejected alternative:** order the goals by summed share instead of by goal
> number. Rejected because the SDG axis is a *known list* the reader navigates
> by number — re-ordering it makes goal 7 appear in a different place in every
> comparison, and the volume sort is already available on the toggle for the
> reader who wants it.

### 3.6 Frontier — quadrant mix and the topic plane

- **Form (mix).** `fig_quadrant_mix` — **five** dot rows, not four: the four
  quadrants plus "not frontier-scored". A2 measured that the four quadrant
  shares sum to a median of 0.967 and a minimum of 0.128, and that quadrants +
  excluded + unscored = 1 for all 7,557 institutions; a four-part figure would
  silently drop 3 % to 87 % of an institution's mass. The fifth row is computed
  as the residual to one, so it cannot disagree with the four.
- **Form (plane).** `fig_frontier_small_multiples` — one Expansion × Acceleration
  panel per institution, all panels on the SAME axes and the SAME bubble scale.
  **A/B #6's winner, measured** (§6). `fig_frontier_overlay` (all institutions in
  one plane) is kept as an explicitly secondary mode behind the same control that
  swaps the top-200-by-volume and top-quartile point sets (2B-3), with its
  occlusion figure in its caption.
- **Encoding.** Mix: dot = institution, row = quadrant, share of the
  institution's own mass. Plane: bubble = topic, area = mass on the current
  basis on a scale shared by every panel (so a small institution's panel is not
  silently magnified), colour = institution, quadrant lines at the origin on both
  axes, a top-quartile topic outlined in `INK` — a SHAPE flag, never a new hue.
- **Interaction.** A segmented control for the point set (top by volume /
  top-quartile) and one for the form (panels / one plane). Hover names the
  institution, the topic, both scores and the mass.
- **Empty state.** A quadrant an institution does not ship is drawn at zero with
  `palette.NA_MARK` in its hover — one real institution ships three quadrants,
  and an absent row would read as "not measured" rather than "none". Unscored
  topics are dropped from the plane and COUNTED in the caption.
- **Export.** The mix frame and the plotted topic rows, both as CSV, plus their
  own xlsx sheets.

> **Rejected alternative (mix):** one stacked 100 % bar per institution, the four
> quadrants plus not-scored as segments. It is the more obvious picture and it is
> refused for one reason: the segments would need a second identity family
> (quadrant hues) inside a Compare chart, and 2B-1 makes the institution the only
> identity. The coverage strip (§3.9) is the single exemption, and only because
> its segments are grey STATES rather than identities.

> **Rejected alternative (plane):** the overlay as the default. Measured in
> A/B #6: 90.7 % of marks have their centre covered by a mark of a DIFFERENT
> institution at k = 6, 78.0 % at k = 3, 62.6 % at k = 2, and 85.7 % even in the
> sparser top-quartile mode — against 0.0 % faceted. A figure that carries
> identity by colour cannot bury nine marks in ten behind another colour.

### 3.7 Impact — index level and per subfield

- **Form (index).** `fig_impact_intervals` — one dot-interval row per
  institution: the PP(top10%) point estimate with its rendered bootstrap
  interval.
- **Form (subfields).** `fig_impact_subfields` — dot-interval rows over the
  UNION of the subfields any compared institution clears, one lane per
  institution, unconditionally.
- **Encoding.** The interval is the panel's point, not decoration: a PP gap
  smaller than the overlap of two intervals is not a finding, and dots alone
  would invite exactly that read. Per-subfield lanes are always on because an
  interval occupies a stretch of axis rather than a point — a collision test on
  the point estimates alone would not see two intervals lying on top of each
  other.
- **Interaction.** Sort **volume** (estimate descending) | **taxonomy** (stable
  slot order / subfield id). A floor toggle for the per-subfield panel: floor 30
  (fewer cells, tighter intervals) ↔ floor 10 ("more cells, wider intervals"),
  both shipped in `impact_cells` (A1). The bonus year is excluded and the
  caption says so.
- **Empty state.** A missing cell is the NORMAL case, not an error: only 3,342
  of 7,557 institutions have any floor-30 cell, the median is 2, and 40 of 40
  random four-tuples intersect to zero (A1). It is drawn as NO MARK — never a
  dot at zero, which would read as "no top-decile output" when the truth is "too
  few publications to estimate". The caption states how many of the {k}
  institutions each row actually carries.
- **Export.** The union frame with its `in_all_ids` flag, `n/a` where a cell is
  missing (never 0), plus the denominator columns L11 requires beside every rate.

> **Rejected alternative:** render only the subfields ALL compared institutions
> clear, as the plan first said (2B-4). Refuted on data, not on taste: for IFPEN
> plus three L1 peers that intersection is empty, and so is every one of 40
> random four-tuples. A panel that is blank on the gate case is not a panel.

### 3.8 Trends — subfield × year small multiples

- **Form.** `fig_trends_small_multiples` — a grid of small panels, one per
  subfield, one line per institution inside each. Small multiples is right here
  and a dot row is not: the question is "who is growing in this subfield", a
  change-over-time read, and change over time is a line.
- **Encoding.** The N panels are the top-N subfields by share summed across the
  compared set (A3 again, same reason as §3.3). **Every panel shares one y
  scale** — `shared_yaxes` alone links a row of panels, not the grid, so the
  builder matches every axis explicitly; a grid whose second row has its own
  scale is the exact lie small multiples exist to avoid. Because of that shared
  scale the caller passes an institution-NORMALISED measure whenever the compared
  sizes differ by an order of magnitude (a raw count would pin the small
  institutions to the floor), and the caption names which measure it passed.
- **The partial final year is drawn, not hidden.** Its segment is DOTTED and its
  point HOLLOW, so it is visibly not the same kind of observation; the year
  itself is a caller-supplied string, since this module never names a year.
- **Interaction.** Basis toggle (the page's); hover names the institution, the
  panel, the year and the value.
- **Empty state.** An institution with no mass in a panel's subfield has no line
  in that panel — never a line at zero.
- **Export.** The long frame (institution × year × subfield), one xlsx sheet.

> **Rejected alternative:** one panel per INSTITUTION with a line per subfield.
> Rejected because it answers a different question (the institution's internal
> mix over time, which the profile already answers) and because it puts {N}
> subfield lines in one panel with no identity family free to colour them —
> institution is taken.

### 3.9 Coverage strip

- **Form.** `fig_coverage_strip` — one stacked, exhaustive 100 % bar per
  institution. **This is the only stacked bar in the app**, and the exemption is
  earned by arithmetic, not by preference: the six `mass_*` columns sum to
  `total_frac` EXACTLY for all 7,557 institutions (A9), so the segments really
  are the parts of one whole. Everywhere else in Compare the categories are not a
  partition and a stack would assert a total that does not exist.
- **Encoding.** SIX segments, not five (A9 corrects rev 0, which dropped
  `mass_unusable`): classified-eligible, title-only, language-uncertain,
  untranslated, unusable, retracted. The classified-eligible segment takes the
  institution's OWN colour; the five grey states take the ordinal ramp
  `palette.GREY_STATE_COLORS`, light → dark by distance from usable text. That
  split is what keeps the coexistence rule intact — the only identity in the
  figure is still the institution — and it gives the strip the
  highlight-plus-mute reading the Studio colour formula asks for. Segments are
  separated by the 2 px SURFACE gap the dataviz spacers require, never by a
  stroke.
- **Interaction.** Hover per segment: institution, state in words, share of
  `total_frac`.
- **Empty state.** A state with zero mass renders as a zero-width segment and
  keeps its hover — the absence is a fact about the institution, and the six
  always sum to one.
- **Export.** The six shares plus their absolute masses and the denominator.

> **Rejected alternative:** six dot rows (one per state, a dot per institution),
> which is the grammar every other row of this section uses. Rejected precisely
> because it would hide the property that makes this view worth having: the
> reader's question is "how much of this institution's output could the
> classifiers actually read", which is a part-to-whole read, and dots on six
> separate rows never add up to a whole on screen.

### 3.10 Collaborate — header and shared topics

- **Form.** A two-card header (the pair, in slot order, with their swatches) and
  one table of the topics both hold, sorted by `min_share` descending.
- **Encoding.** Columns: topic, subfield (on the SELECTED tree), A's share, B's
  share, the minimum of the two, the topic's keywords as human-readable
  evidence, and the frontier flag. The minimum is the column the sort is on
  because Σ min(share) over shared topics IS the engine's L3 score for the pair —
  the table and the lens agree by construction, and the test pins the identity on
  both bases.
- **`top25pct_frontier` renders as THREE states** — frontier · not frontier ·
  **unscored** — never null coerced to false (E18): 810 of 4,516 topics carry no
  score, and 37 % of the gap rows on a real pair are unscored.
- **Interaction.** A search box over topic names; an off-by-default filter to
  frontier-flagged topics only; keywords truncated in the cell with the full
  string in the export.
- **Empty state.** No shared topic at all → a stated sentence plus the two
  profile links, never an empty table.
- **Export.** CSV + xlsx sheet, keywords un-truncated.

> **Rejected alternative:** a Venn or a set diagram of the two topic sets.
> Rejected because the interesting quantity is not set membership but SHARE
> agreement — two institutions can share 2,376 topics and still be nothing alike
> — and an area-proportional Venn cannot encode a second measure at all.

### 3.11 Gaps tables (A → B and B → A)

- **Form.** Two tables, directional and side by side at wide widths, stacked
  below the small breakpoint.
- **Encoding.** A's gaps = the topics B holds inside A's own top-10 subfields
  that A does not hold, with B's share and the frontier flag; B's gaps
  symmetric. The direction is stated in the table's own title, not left to the
  column order — a directional table read the wrong way round is a wrong answer,
  not a confusing one.
- **Interaction.** Sort by B's share (default) or by subfield; the frontier
  filter is shared with §3.10.
- **Empty state.** No gap rows → a stated sentence naming the pair and the
  subfield scope; the honest reading is "nothing B does inside A's strengths
  that A does not already do", which is a finding.
- **Export.** Both directions, one sheet each.

> **Rejected alternative:** one merged table with a direction column. Rejected
> because the two tables answer two different questions and a merged one invites
> a total that means nothing; the R2 campaign also showed this content is read
> as a partnering shortlist, and a shortlist is read one direction at a time.

### 3.12 Breadth-overlap diagnostic

- **Form.** A single labelled number with its two counts beside it — a stat
  tile, not a chart (§1.6 / the dataviz form heuristic: one value is never a
  one-bar bar chart).
- **Encoding.** The unweighted Jaccard over topics with nonzero share, shown with
  the intersection and union counts that produced it, and a one-line statement
  that it answers a DIFFERENT question from the shared-topics table: breadth
  overlap, not weight agreement. Two institutions can score high here and share
  almost no mass.
- **Interaction.** None. It is a number.
- **Empty state.** Undefined only if both topic sets are empty, which the corpus
  filters make impossible; the tile still renders `palette.NA_MARK` rather than
  zero if it ever happens.
- **Export.** In the Methods sheet of the pair's workbook, with its counts.

> **Rejected alternative:** a share-weighted overlap coefficient instead of the
> unweighted Jaccard. Rejected because the weighted version is what the
> shared-topics Σ min already is — shipping both as one number would give the
> reader two names for one quantity and no diagnostic at all.

### 3.13 Link-outs

- **Form.** A row of external links under the Collaborate tables.
- **Encoding.** The co-publication query on OpenAlex for the pair, built with the
  comma-joined repeated filter `authorships.institutions.id:A,authorships.institutions.id:B`
  plus the corpus filters. The `+` form is FORBIDDEN: it silently returns A's own
  count with HTTP 200 (A7, verified on a real pair), and a test asserts the comma
  form. Each institution's own OpenAlex page is linked from its header card.
- **Interaction.** Links open in a new tab; the co-publication count is NOT shown
  — no co-publication data exists in the artefacts, and a number the app cannot
  reproduce offline does not belong on the page.
- **Empty state.** Nothing to guard: a query with no results is a legitimate
  answer on OpenAlex's own page.
- **Export.** The URLs are written into the Methods sheet so a workbook stays
  self-describing.

> **Rejected alternative:** fetch the co-publication count live and print it in
> the page. Rejected on the standalone principle (`CLAUDE.md`): the app must
> re-run from its own artefacts, and a live figure would be a number in the
> deliverable that no snapshot can reproduce.

---

## 3. Cross-cutting A/Bs to run on real data (D1)

Named here per this stream's brief item 5; **resolved by Stream D1** against
real engine output (`app/lib/engine`, University of Gdańsk `I40413290`, L1
top-30) with Playwright screenshots at 1280 px, appended to this file as a new
"§4 A/B verdict" section (the one exception to D0's exclusive ownership of this
file).

### A/B #1 — score column in every `tbl-lens-ranked` row

| Candidate | Description |
|---|---|
| A | `st.column_config.ProgressColumn` — a horizontal bar per row, confirmed present in Streamlit 1.61.1 |
| B | A Plotly ranked-dot chart, one dot per row at its score, sharing the table's row order |

**Measured criterion:** rows legible above the fold at 1280 px (how many of the
top 30 are visible without scrolling); label-truncation count (institution
names cut off); zero-baseline compliance (RULES honesty rule 1 — does the form
imply a false zero or a false ceiling); an honest read of ties (does the form
visually distinguish two rows tied at the same competition rank, or wrongly
imply one beats the other).
**Real seed to render:** University of Gdańsk (`I40413290`), L1, top-30.
**Downstream consequence already fixed regardless of winner:** the Aspirational
tab (§2.5) never uses Candidate A alone, because A cannot render a confidence
interval (see §2.5's own rejected-alternative note).

### A/B #2 — concordance overview form

| Candidate | Description |
|---|---|
| A | k-count table with hit-lens chips (this document's proposed default, §2.3) |
| B | A full rank matrix: candidates × lenses, cell = rank (or blank) |

**Measured criterion:** rows legible above the fold at 1280 px; label-truncation
count; whether the form still fits full width without the page body scrolling
horizontally (house rule) once all 8 default lens columns are present; an
honest read of ties/undefined cells (does a blank cell in the matrix read as
"not found" or ambiguously as "not computed" — RULES honesty rule 12, "'0' is
not 'not computed'").
**Real seed to render:** University of Gdańsk (`I40413290`), the 8 default
lenses at N=30.

---

## 4. A/B verdict (Stream D1, resolved on real data 2026-08-29)

Full measured criteria, screenshots and the one-paragraph reasoning for each
verdict live in `design-system/ab/AB_VERDICT.md` (the appending stream's own
file, not duplicated here in full). Summary:

**A/B #1 (score column, §3):** Winner **A -- `st.column_config.ProgressColumn`**.
Both candidates were zero-baseline compliant and showed the same row count
above the fold in their table portion at 1280px; the decisive difference was
structural, not a Studio-RULES violation on either side: Candidate B (the
Plotly ranked-dot chart) needs two widgets kept in lockstep (a `st.dataframe`
and a `plotly_chart`) that do not share one scroll region, so past row 10 the
table and the chart drift out of visual sync (the chart, rendered at a fixed
height to show all 30 points, exposes rows the table's own internal scroll
has not reached yet). Candidate A keeps rank, identity and score strength in
one coherent, single-scroll widget, with the percent value printed on the bar
itself. No tied competition rank exists in the L1 top-50 of any of the 19
D19 seeds (checked programmatically), so the honest-tie-rendering criterion
could not be exercised on real data and is scored a tie between candidates.
**Per §2.5, this verdict does not extend to the Aspirational tab**, which
keeps its own interval-mark form regardless (a bare progress bar cannot
render a confidence interval).

**A/B #2 (concordance overview, §3):** Winner **A -- k-count table with
hit-lens chips**. At 1280px both forms fit full width and are equally legible;
the decisive evidence is the 390px render, where Candidate A needs only one
internal horizontal table-scroll to reveal `k of n` and the hit-lens list
(the columns that answer this view's own decision sentence), while Candidate
B's full rank matrix shows only one of its 8 lens columns before its own
scroll is needed, burying the concordance signal behind several swipes.
Both forms keep the page body itself free of horizontal scroll (the house
rule); Candidate B's genuine strength -- column-wise "which candidates does
L6 find" scanning -- answers a different question than the overview's own,
and that question is already answered by each lens's own `tbl-lens-ranked`
tab (§2.4).

**Consequence for `lib/ranked.py` (Stream D1's shared component):**
`render_ranked_table`'s score column is always the winning A/B #1 form; every
ordinary lens tab in §2.4 uses it. `render_concordance_table` is always the
winning A/B #2 form for the view in §2.3. Neither verdict changes any other
row in §2 of this document.

---

## 5. A/B verdicts — refinement R1 (stream R-D2, 2026-08-29)

Two further A/Bs were run on REAL deployed data (Universite de Strasbourg
`I68947357`, resolved by `display_name` in `data/index.parquet`, and University
of Gdansk `I40413290`), rendered through a throwaway Streamlit prototype and
photographed headless by Playwright at 1280 and 390 px. Full tables, measured
criteria, commands and screenshots: `design-system/ab/AB_VERDICT.md` (R1 section).

- **A/B #3 — the share + SI form. WINNER: two aligned panels of one figure
  sharing the y axis**, share bars left, SI lollipops right against a dashed
  reference at the neutral value, no mark where SI is `n/a`. The rival (SI as an
  expected-share tick on the share row itself, the only dual-axis-free form of
  "a secondary marker on the same row") put SI on a per-row scale — equal SIs
  land at different x, so the column cannot be read as a ranking — and stretched
  the share axis by a measured factor of 1.59 on Strasbourg, foreshortening
  every share bar by ~37 %. The winner's own cost is a 390 px collapse to 61 px
  per panel, answered by §1.8's stacking rule, not ignored.
- **A/B #4 — where the volume number goes. WINNER: a left text gutter**, numbers
  right-aligned against the zero baseline. Both variants were given the same
  1.18× horizontal budget, so the test isolated placement: the right-of-bar rival
  clipped one real number at 390 px (0 clipped in the gutter form) and scattered
  the 25 numbers across 850 px (travel std 204 px vs 0). Scope: the verdict
  governs a volume printed BESIDE a bar encoding a different measure; a direct
  label on a bar encoding that very number (the yearly global breakdown) keeps
  its end label.

  **Fix X3 note (Refinement R1 re-gate, inspection finding I-4):** the verdict
  above still stands, but the ORIGINAL implementation of it (a separate
  `add_annotation` per row, independent of the y tick label) collided with the
  category label at 390 px — see §2.15's fix note for the mechanism, the
  measured cause (`yaxis.automargin` does not reserve room away from a plot's
  own bars), and the robustness rule this leaves for the next A/B that places
  a number beside a label.

  **R2 note (user ruling item 10, L35): the gutter placement STAYS, the
  ellipsis rule it was paired with does NOT.** A/B #4's verdict is about WHERE
  the volume number goes (the left gutter, right-aligned) — it says nothing
  about what happens to an over-length CATEGORY label sharing that same tick
  string, which was a separate, later decision (X3's ellipsis, chosen only
  because X3 needed some rule for the label half of the folded string). The
  user's own read at gate 2A was that shortening a field or topic name is a
  worse failure than a taller row, so R2 replaces the ellipsis with a two-line
  WRAP (`charts.wrap_label`, §2.15's R2 update) while leaving A/B #4's own
  finding — gutter over right-of-bar, numbers right-aligned against the zero
  baseline — completely untouched. No re-test of A/B #4 was needed or run: the
  wrap change touches only the LABEL half of the folded tick string, never the
  volume half the A/B actually measured.

Both winners are implemented in `lib/charts.py` and exercised on the real frames
by `tests/test_charts.py`.

---

## 6. A/B verdicts — Phase 2B (stream V, 2026-08-29)

Two A/Bs were run on **real deployed data**, on the six institutions named in
the stream V brief — Iscte `I110026055`, ETH Zurich `I35440088`, Sorbonne
`I39804081`, University of Gdańsk `I40413290`, IMT Atlantique `I4210127572`,
Université de Strasbourg `I68947357` — rendered through a throwaway Streamlit
prototype (`design-system/ab/proto_2b.py`) and photographed headless by
Playwright at 1280 px (`design-system/ab/run_ab_2b.py`). Frames come from the
deployed parquet files through `design-system/ab/_common_2b.py`, which
reproduces the `BUILD_PLAN_2B.md` §4 contracts by hand rather than importing
stream K's modules.

**Everything below is MEASURED off the live DOM, not eyeballed.** The runner
reads every rendered mark's bounding box and computes: `min_mark_px` (the
smallest mark), `max_overlap_frac` (the largest overlap between two marks OF ONE
ROW, as a fraction of a mark's own diameter — rows are resolved from geometry,
`floor((y_centre − plot_top) / (plot_height / n_rows))`, not guessed),
`span_px` (how far the eye must travel to compare every institution on ONE
category) and `cross_occluded_frac` (the share of marks whose centre is covered
by a mark of a DIFFERENT institution). Screenshots: `ab5_a_1280.png`,
`ab5_b_1280.png`, `ab6_a_1280.png`, `ab6_a2_1280.png`, `ab6_a3_1280.png`,
`ab6_aq_1280.png`, `ab6_b_1280.png`.

### A/B #5 — the Compare mirror form. WINNER: dot rows.

Fields mirror, 26 fields × 6 institutions, 1280 px. The grouped-bar form the
plan first proposed was already refuted before this A/B (wind tunnel #16 / A4:
2.6 px per bar at the shipped pitch), so the contest is dot rows against small
multiples.

| measured at 1280 px | **A — dot rows (shipped)** | B — small multiples |
|---|---|---|
| `min_mark_px` (floor 8) | **12.0** ✔ | 10.8 (bar thickness) ✔ |
| `max_overlap_frac` in one row (ceiling 0.5) | **0.000** ✔ | 0.000 (bars cannot overlap) |
| `span_px` — eye travel to compare all six on ONE field | **74** | **900** (12.2×) |
| share-axis plot width per institution | **496 px** | 299 px |
| figure height | 2,020 px | 900 px |
| mass-paired SI panel (2B-2) | **yes**, 12 traces = 6 × 2 panels | **no**, 6 traces, share only |
| category labels | wrapped, no collision | **collide** at the 14.5 px panel pitch |
| horizontal scroll | none | none |

**Verdict.** The dot row wins on the criterion the panel exists for. Comparing
one field across the compared set costs 74 px of eye travel in the dot row and
900 px in the grid — the grid puts the six marks that answer the question in six
different panels, which is the one thing a *mirror* must not do. It also gives
each institution a 496 px share axis against 299 px, and it is the only form
with room for the mass-paired specialisation panel that 2B-2 makes mandatory.
Its cost is real and is accepted: 2,020 px against 900 px, i.e. the Fields
mirror is a scrolling panel at k = 6. The A4 acceptance is met with margin —
every mark 12.0 px against a floor of 8, and zero row-overlap against a ceiling
of half a dot — and it is met **by construction, not by luck**: lanes are
`LANE_PITCH_PX` apart inside a row band whose own height is sized from the lane
count, so no frame can violate it.

Two things the render changed in the shipped builder, both found by looking at
the picture rather than at the numbers:
* the first draft dodged marks GREEDILY, per row, which was more compact (1,204
  px) but put institution 3 second from the top in one row and fourth in the
  next. A vertical position that changes meaning row by row is worse than the
  overlap it fixed, so the split became all-or-nothing with the lane index fixed
  to the SLOT — and the panel grew to 2,020 px, which is the honest price of a
  lane that means something;
* `charts.row_height`'s two-line pitch is not enough for a stacked lane set:
  `compare_row_height` adds the SHORTFALL between the profile pitch and the lane
  stack's own need, per row. Multiplying the whole row budget instead produced a
  2,852 px panel for the same picture.

### A/B #6 — the frontier plane. WINNER: small multiples.

Top-200-by-volume topics per institution, 1,145 rendered bubbles, 1280 px.

| measured at 1280 px | A — overlay | **B — small multiples (shipped)** |
|---|---|---|
| `cross_occluded_frac`, k = 6 | **0.907** | **0.000** |
| `cross_occluded_frac`, k = 3 | 0.780 | 0.000 |
| `cross_occluded_frac`, k = 2 | 0.626 | 0.000 |
| `cross_occluded_frac`, top-quartile mode, k = 6 | 0.857 | 0.000 |
| `min_mark_px` | 9.4 ✔ | 7.5 ✘ in the prototype (the shipped builder raises its own bubble minimum to 8) |
| plot area per institution | 1,039 × 425 shared by six | 329 × 255 each |
| figure height | 520 px | 640 px |

**Verdict.** The overlay loses, and it loses at every k tested and in both point
modes. At k = 6, nine marks in ten have their centre covered by a mark of a
DIFFERENT institution; the last institution drawn blankets the dense core and the
five under it are gone. Opacity does not rescue it — `OVERLAY_OPACITY` was on for
every measurement above. The dataviz series ladder predicted exactly this
("all-pairs forms cap at three"), and the sparser top-quartile mode does not fix
it either (0.857) because top-quartile topics cluster in the same corner of the
plane by definition. Faceting takes the number to 0.000 by construction and keeps
it there at any k, at a cost of 120 px of height and a 3.2× smaller plane per
institution.

`fig_frontier_overlay` is nonetheless KEPT, as an explicitly secondary mode
(§3.6): the single plane answers one question the facets cannot — whose topics
sit furthest out, over everybody — and a bubble stays identifiable on hover. Its
caption carries the occlusion figure, so the reader is told what the picture is
hiding. What is NOT acceptable is the overlay as the default, which is what the
plan assumed.

### Scope of these two verdicts

A/B #5 governs the **mirror** family (§3.2–§3.5): a categorical axis, one value
per institution per category. It says nothing about a part-to-whole read, which
is why the coverage strip (§3.9) is a stacked bar and not dot rows. A/B #6
governs a **topic-cloud** plane; it does not reopen §2.18's single-institution
frontier scatter, which has one series and no occlusion problem.

### Render proof

`design-system/ab/2b_shipped_builders_1280.png` — every shipped builder on the
six real institutions, one page, 1280 × 9,900 px, 11 figures, `scroll_ok: true`.
Read and described in `V3/progress/2B_V.md`.

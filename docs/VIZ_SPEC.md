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

### 1.9 Profile section composition (R1/L17 — replaces the seed card of §2.2)

Gate-2A feedback #2: the page was chart-poor. The seed card becomes a PROFILE
SECTION combining Lorraine Phase 2's "Analyse d'une structure" overview with
BenchUp V2's collapsed chart panels. Fixed order, top to bottom:

1. **Header** (§2.10) — name, type · city, country NAME, seed-level badges,
   links.
2. **KPI tiles** (§2.11) — seven, each value + label + subline.
3. **Coverage caption** (§2.12) — the former evidence lines, one line.
4. **Wordcloud (left) + yearly breakdown pair (right)** (§2.13, §2.14) — the one
   full-width row of the section.
5. **Six collapsed panels** (§2.15–§2.20), every one `st.expander(expanded=False)`:
   Fields · Top subfields · Top topics · Frontier positioning · SDG profile ·
   ERC profile.

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

- **Form.** One block above everything else: institution name (`text-xl`), then a
  meta line "type · city, country NAME", then the seed-level badges, then a link
  row — ROR · OpenAlex works · homepage.
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

- **Form.** Seven tiles in one wrapping row, each **value + label + subline**
  (the Lorraine `_kpi_tile` HTML pattern, copied in — `st.metric` has no subline
  and the subline is the point). Tile chrome: `NEUTRAL` fill, `BORDER` hairline,
  `INK` value, `INK_SECONDARY` subline — all from `palette.py`, never inline hex.
- **Encoding.** In fixed order (L18): size full · size fractional · concentration
  (HHI value + its class tag) · breadth (subfields at or above the fractional
  floor) · SDG-tagged share · frontier top-quartile share · PP(top10%) with its
  interval. **Every subline names the denominator or the reference** — the house
  rule "every KPI pairs value with denominator/coverage" (L11) is what the
  subline is FOR.
- **Interaction.** None (a tile is not a control). The interval on PP(top10%)
  renders as a value plus its bounds, never as a bare point estimate (RULES §9.6).
- **Empty state.** `n/a` for any tile the data cannot support — never 0, never a
  hidden tile: a missing indicator is information (§1.6, `palette.NA_MARK`).
- **Export.** The same seven numbers are the seed's row in every CSV the page
  writes.

> **Rejected alternative:** `st.metric` with its delta arrow, one call per tile.
> Rejected twice over: it has no subline, so the denominator would have to move
> into a caption underneath the row and stop being attached to its own number;
> and its delta arrow implies a change-over-time read that none of these seven
> measures has (they are all one snapshot), which is exactly the "does the form
> imply something the data doesn't" failure the Studio rules flag.

### 2.12 Coverage caption

- **Form.** ONE line under the tiles, `text-xs`, `INK_SECONDARY` — the former
  per-lens evidence lines, promoted to the seed level and merged.
- **Encoding.** Four continuous shares, each a parameter filled from the live
  data: ERC-classified share, SDG-tagged share, catch-all (811) share, and the
  count of L2f-eligible subfield cells. Every one is a coverage statement about
  the SEED, never a gate and never a quality verdict (L8).
- **Interaction.** None; it is a caption. The per-lens evidence line still exists
  inside each lens tab, where it is about that lens.
- **Empty state.** A share that cannot be computed prints `n/a` with the reason
  in the same line; the line never disappears, because "we do not know the
  coverage" is itself the thing the reader needs.
- **Export.** Constant columns on the seed's CSV rows.

> **Rejected alternative:** four more KPI tiles. Rejected because coverage is a
> caveat on the other seven numbers, not a peer of them — giving it the same
> visual weight would invite a reader to compare "SDG-tagged share" against
> "size" as if they were the same kind of fact.

### 2.13 Subfield wordcloud

- **Form.** A PNG (Lorraine's `WordCloud` → `PIL` → `st.image` pattern, copied
  into `lib/wordcloud_png.py`), left half of the section's wide row.
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

- **Form.** Two figures side by side under ONE `st.segmented_control` and ONE
  shared chip legend: **left** = global horizontal bars, one per series, sorted
  by volume descending, direct end labels, no legend
  (`charts.fig_breakdown_global`); **right** = per-year GROUPED bars
  (`charts.fig_breakdown_yearly`). Both render `showlegend=False`;
  `charts.chip_legend_html` is the ONE legend for the pair (Lorraine
  `render_chip_legend`).
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
  the neutral value (A/B #3 and #4 winners).
- **Encoding.** One row per field, coloured by the field's DOMAIN (inheritance,
  §1.1). Share is on the current basis; SI has **no floor at field grain** (the
  G6 floor applies to subfields only — the data contract says so on both rows).
- **Interaction.** A sort toggle: **volume** (share descending) | **taxonomy**
  (domain → field id). Colour follows the entity, never the rank, so the toggle
  never repaints anything (`tests/test_charts.py` pins this).
- **Empty state.** A field with zero mass is absent (it is not a fact about the
  seed); a field with mass but undefined SI keeps its bar and gets NO SI mark —
  never a dot at zero, never a dot at the neutral value.
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

### 2.16 Panel — Top subfields (share + SI)

- **Form.** As §2.15, `charts.fig_share_si`, on the top subfields by volume.
- **Encoding.** Domain colour inherited through the subfield → field → domain
  chain, so the panel re-tints with the tree. **SI is `n/a` below the G6
  fractional floor** and renders as no mark at all, with `n/a` in the row's hover
  — on real Gdansk data most subfields sit below that floor, so this is the
  common case, not an edge case.
- **Interaction.** Same sort toggle as §2.15 (volume | taxonomy: domain → field →
  subfield). The depth of the cut is stated parametrically in the panel caption.
- **Empty state.** If NO row in the frame has a defined SI, the figure collapses
  to a single share panel and the caption says why, rather than drawing an empty
  second axis (`charts.fig_share_si` does this itself).
- **Export.** CSV of the FULL subfield frame, not just the displayed cut — the
  §1.7 rule that an export is never the screen's truncation.

> **Rejected alternative:** show all subfields, with a scroll inside the panel.
> Rejected on the same ground as the depth cut in the ranked tables: a seed can
> carry 200+ subfields, most of them below the floor and therefore SI-less, and a
> 200-row scroll inside a collapsed expander is a worse tail affordance than a
> stated cut plus a complete CSV.

### 2.17 Panel — Top topics

- **Form.** `st.expander(expanded=False)` → `charts.fig_topics`: horizontal share
  bars for the top topics by share, volume in the left gutter.
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

- **Form.** `st.expander(expanded=False)` → `charts.fig_frontier`: a scatter of
  the seed's topics, **x = Expansion, y = Acceleration**, with the two quadrant
  lines at the origin on both axes (verified against `topics_dim.quadrant`, which
  flips sign exactly there).
- **Encoding.** Bubble area = the topic's mass on the current basis (`sqrt` scale
  between a floor and a ceiling in px, so a big topic cannot swallow the panel);
  colour = domain; **a top-quartile frontier topic carries an `INK` outline** —
  a shape signal on top of the family colour, never a fifth hue.
- **Interaction.** Hover names the topic and gives expansion, acceleration and
  mass. No zoom, no animation (house rule: no motion).
- **Empty state.** Topics with no frontier score are DROPPED from the scatter and
  **counted in the caption**, together with the excluded ones — the panel states
  what it could not place rather than letting it vanish. A seed with no scored
  topic renders the reason, not an empty axis.
- **Export.** CSV of every topic with its expansion, acceleration, quadrant,
  top-quartile flag and mass — scored and unscored alike.
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

### 2.19 Panel — SDG profile

- **Form.** `st.expander(expanded=False)` → `charts.fig_sdg`, which delegates to
  `charts.fig_share_si` with ESI in the SI slot, so the reader learns ONE form
  and reuses it (Lorraine `same-read-same-form`).
- **Encoding.** Sixteen bars in **fixed SDG number order** (never sorted by
  value), each in its **official UN colour**; ESI dots against the same dashed
  neutral reference. Every bar carries its goal number and short label on the
  axis, which is the structural relief for the UN palette's measured CVD and
  contrast failures (§1.1, family 3): identity is never colour-alone here.
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

- **Form.** `st.expander(expanded=False)` → `charts.fig_erc` (again
  `fig_share_si`): the ERC evaluation panels, share left, SI right.
- **Encoding.** One row per panel, coloured by its **ERC DOMAIN** — three hues,
  `palette.ERC_DOMAIN_COLORS` — and grouped in the fixed PE → LS → SH order under
  `sort="taxonomy"`. No OpenAlex domain hue may appear in this chart
  (`tests/test_charts.py` asserts the two sets do not intersect): it is a
  different taxonomy of the same output, and colouring it like the OA panels
  would invite a false one-to-one reading.
- **Interaction.** Sort toggle: taxonomy (ERC domain, then panel code) | volume.
- **Empty state.** A panel with zero classified mass keeps its row at zero rather
  than disappearing — the ERC structure is fixed, and a missing panel is a fact
  about the institution, not about the taxonomy.
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

Both winners are implemented in `lib/charts.py` and exercised on the real frames
by `tests/test_charts.py`.

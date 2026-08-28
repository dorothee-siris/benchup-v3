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

### 1.1 Colour (computed, not eyeballed — validator run 2026-08-29, mode light)

Single source: `lib/palette.py`. Full validator log: `design-system/palette_validation.txt`.

- **Focal / comparison / neutral:** the seed institution is the ONLY thing ever
  painted `FOCAL` (`#0072B2`) — highlight-plus-mute (COMPOSITION_AND_CONTROLS.md
  Control layer #6). Every candidate row/mark is `COMPARISON` grey (`#8C9196`)
  unless its institution-type identity is shown (next bullet). `NEUTRAL`
  (`#E6E8EB`) is background/zebra/empty-state fill only.
- **Institution-type identity (k≤5, the app's one stable categorical):**
  `education` carries **no** colour (base-rate, unflagged); `facility` `#D55E00`,
  `healthcare` `#009E73`, `government+funder` `#CC79A7`, `other` `#6A3D9A`
  (company/nonprofit/archive/other collapsed). Validator: **ALL CHECKS PASS**
  (5 slots: FOCAL + the 4 hues). Two WARN advisories are carried as **binding**
  rules, not dismissed: (a) `#CC79A7`↔`#009E73` CVD ΔE 7.6 (deutan, 6–8 floor
  band) → legal only with secondary encoding, satisfied because every type badge
  ships with visible text, never a bare colour dot (§1.5 badge grammar,
  `design-system/DESIGN_TOKENS.md` §5); (b) `#CC79A7` contrast 2.98:1 on white
  ("binding relief") → `government+funder` never renders as a bare fill.
- **Text ink** `#333333` never appears on a mark, bar, dot or badge fill — text
  and table copy only (validator fails it as a series colour by design).
- **Status colours:** BenchUp v3 Phase 2A has no good/bad or momentum read to
  encode (INDICATOR_SPEC_v2 §4 carries no status dimension this phase) — no
  status palette is defined; if one is added later it ships text+glyph, never
  colour alone (RULES §4), and the validator re-runs before ship.
- Full spacing/type-scale tokens and the ui-ux-pro-max reconciliation:
  `design-system/DESIGN_TOKENS.md`.

### 1.2 Typography

Base 16 px / line-height 1.5 floor on all body and table text; one precision
level per numeric measure; thousands separator; every percentage states its
denominator in the same cell or the line immediately above it (never a bare
"{x}%"). Full scale: `DESIGN_TOKENS.md` §3.

### 1.3 Control order (sidebar, top to bottom)

1. **Scenario** — tree (`{original, conservative, bestfit}`, default `bestfit`)
   × basis (`{frac, full}`, default `frac`) — a disclosure line under the basis
   control states "ERC and SDG lenses (L4, L5, L6, L7) are fractional-only; this
   toggle does not change them" (INDICATOR_SPEC_v2 §5, BUILD_PLAN_2A L5).
2. **Depth** — one control, `{30, 50}`, default 30 (§2.6).
3. **Optional lenses** — two SEPARATE affordances, never bundled (INDICATOR_SPEC_v2
   §1.8/§1.9, ruling 8): C1 "restrict to my core subfields" (plain one-click
   toggle) and L7 "Show an experimental SDG-specialisation view — mostly noise,
   occasionally unique" (its own, visibly more discouraging control — smaller,
   greyed-until-hover, or an expander rather than a same-weight checkbox next to
   C1).
4. **Post-filters** (all opt-in, applied AFTER ranking — BUILD_PLAN_2A L6): type,
   country (+ "exclude own country," with an inline tooltip on the L3 tab
   specifically about same-country clustering), size range, scale-guard toggle
   (`max(a,b)/min(a,b) ≤ m`, m = 8 below 20k full works / 4 at ≥20k — the number
   itself is computed live from `total_full_2020_2024`, never hard-coded in
   copy), family filter (opt-in, L0 score ≥ `family_filter_threshold`).
5. **Basket** — persistent list, session-state (not a widget key, BUILD_PLAN_2A
   §2/§7), survives page navigation.

Every widget above is keyed and carries `persist_state="session"` (Stream A) so
none of it resets on a Menu↔Find round trip.

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

Text + glyph/dot, never colour alone (`DESIGN_TOKENS.md` §5). Three badge
families: institution-type (colour dot from §1.1 + type name — `education` gets
no dot), umbrella/aggregate ("EXPERIMENTAL" text + tooltip carrying the
country×type median compared against), type-corrected ("type corrected by SIRIS
(was: {type_openalex})"). **Never both an umbrella badge and a type-corrected
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
in argument order — seed search → seed card (KPI tiles wrap to one per row,
never truncated) → tab strip (Streamlit's native horizontally-scrollable pill
tabs) → ranked table (its own `overflow-x:auto`, never the page body). Legends
and badges wrap to a second line rather than truncating silently (RULES §8
Small screen). Render-verified at 1920/1280/390 px with `scrollWidth ≤
innerWidth+2` is Stream E/H's acceptance gate; this section only fixes the rule
they render against.

---

## 2. View specs — one row per Find view (9 views)

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

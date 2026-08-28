# Design tokens — BenchUp v3 (Stream D0)

Reconciles `design-system/benchup-v3/MASTER.md` (ui-ux-pro-max, one `--design-system`
pass + 3 targeted `--domain ux` queries) against the SIRIS house rules and the Studio
KB (`RULES.md`, `COMPOSITION_AND_CONTROLS.md`, `LEGIBILITY_BUDGETS.md`). Where the two
conflict, **SIRIS wins** (CLAUDE.md: "these instructions OVERRIDE any default
behavior"). Charts and colour are `dataviz` + `lib/palette.py`'s job, never
ui-ux-pro-max's — its material is form inspiration only, queried, not adopted whole.

## 1. Light-only, full-width — the two non-negotiables

- `color-scheme: light` on `:root`; no `@media (prefers-color-scheme: dark)`, no
  `[data-theme="dark"]` block, anywhere in `app/`. `.streamlit/config.toml` pins
  `[theme] base = "light"`.
- No `max-width` character-measure clamp on the page body; `layout="wide"`
  (Streamlit config). Wide tables (ranked lenses, concordance matrix) own their
  scroll — `st.dataframe`'s native horizontal scroll, never a page-level one.
- Render-verify at 1920 / 1280 / 390 px before gate 2A (Stream E/H's job; this
  stream only writes the rule).

## 2. Spacing scale (dense dashboard, 8–32 px)

One scale, multiples of 4, used everywhere a gap/padding/margin is set:

| Token | px | Use |
|---|---:|---|
| `space-1` | 4 | icon-to-label gap inside a badge/chip |
| `space-2` | 8 | table cell padding (dense rows — LEGIBILITY_BUDGETS "table rows... add search at ~50 rows"); gap between a value and its unit |
| `space-3` | 12 | gap between adjacent stat tiles in a KPI row |
| `space-4` | 16 | gap between a control row and the panel it filters; sidebar section gap |
| `space-6` | 24 | gap between the seed card and the tab strip below it |
| `space-8` | 32 | top-of-page padding under the snapshot stamp; gap between major page sections (seed card → overview → tabs) |

No token above 32 px in Phase 2A — this is a working dashboard, not a marketing page
(ui-ux-pro-max's persisted "Enterprise Gateway" hero-section pattern is explicitly
**rejected**, §5).

## 3. Type scale (base 16 px, line-height 1.5)

| Token | px | Weight | Use |
|---|---:|---|---|
| `text-xs` | 12 | 400 | table footnotes, "Filtered by…" strip, evidence-line caveats |
| `text-sm` | 14 | 400 | table body cells, badge text, tab labels |
| `text-base` | 16 | 400 | page body copy, sidebar control labels — **floor, never smaller** (ui-ux-pro-max ux-guidelines.csv "Readable Font Size": "Minimum 16px body text on mobile," Severity High — adopted app-wide, not mobile-only, because the SIRIS density budget already runs dense) |
| `text-lg` | 18 | 600 | tab-panel section headers ("Overview", "L1 — Subfield overlap") |
| `text-xl` | 22 | 600 | seed card institution name |
| `text-2xl` | 28 | 600 | page title ("Find") |

Line-height 1.5 on all body/table text (WCAG 1.4.8 baseline, also the ui-ux-pro-max
"Fira Sans" pairing's own recommendation — see §5). Numeric labels: one precision
level per measure (RULES §5), thousands separator, percentages state their
denominator inline (never a bare "24.7%" without "of 26 subfields" or equivalent
alongside).

## 4. Table density rules

- Row height: compact (`st.dataframe` default density is already close; do not
  add custom CSS padding beyond `space-2`).
- Depth default 30 rows on-screen, one click to 50 (INDICATOR_SPEC_v2 §1/§9 #1,
  BUILD_PLAN_2A L2) — never render the full ranking inline; tail is searchable +
  downloadable (RULES §9.9 "top-N cuts amputating the tail").
- Above ~50 rows visible at once, a search/filter box is mandatory, not optional
  (LEGIBILITY_BUDGETS "Table rows... working rule: add search at ~50 rows").
- Every ranked table's score column, evidence column and type/badge column keep
  identical widths and order across all 10 lens tabs — "a reader learns each form
  once" (Lorraine VIZ_SPEC.md §3 rule 1, `same-read-same-form`).
- Wide tables (concordance rank matrix, 8+ lens columns) scroll horizontally inside
  their own container; the page body never does (SIRIS house rule; ui-ux-pro-max
  ux-guidelines.csv "Table Handling": "Use horizontal scroll... overflow-x-auto
  wrapper," Severity Medium — this is the ONE ui-ux-pro-max UX finding adopted
  verbatim, because it restates the house rule rather than conflicting with it).

## 5. Badge / chip grammar — text + glyph, never colour alone

Every badge in the app (umbrella/aggregate, type-corrected, catch-all-share,
tie-inclusive-rank, undefined-lens) follows one shape:

```
[optional coloured dot from lib.palette.TYPE_COLORS]  short text label  [ⓘ tooltip trigger]
```

- Colour is never the only signal — RULES §4 "status: never encode good/bad as
  red/green alone" generalises here to *any* categorical fact worth flagging.
  Concretely: `type-corrected` renders as the text "type corrected by SIRIS (was:
  {type_openalex})", no colour at all; `umbrella` renders as the text "EXPERIMENTAL"
  + a tooltip, no colour; only the institution-TYPE badge (facility / healthcare /
  government+funder / other) carries a `TYPE_COLORS` dot, and it is always paired
  with the type's own text name in the same cell.
- **Never both an umbrella badge and a type-corrected badge on one row**
  (BUILD_PLAN_2A L7 / WT #14 — the two are mutually exclusive by construction on
  the patched `type` field).
- A badge's tooltip carries the evidence (median compared against, "was:" value,
  catch-all share number) — RULES §6 "tooltips repeat labels and expose
  provenance/detail; they never carry information essential to the static read"
  — so the badge's own visible text must stand alone without the hover.

## 6. Reconciliation vs `design-system/benchup-v3/MASTER.md`

The ui-ux-pro-max pass returned a **B2B-SaaS marketing-adjacent "Enterprise
Gateway" pattern** paired with a **"Data-Dense Dashboard" style** at density 8/10.
The style card is useful form guidance; the pattern card and its own palette are
not this app's shape at all (BenchUp v3's Find tab has one page, no marketing
funnel). Kept vs. rejected, explicitly:

### Kept (form/structure guidance only, no colour adopted)
- **Density profile** ("multiple charts/widgets, data tables, KPI cards, minimal
  padding, grid layout, space-efficient, maximum data visibility") — matches
  BUILD_PLAN_2A's Find-tab journey (seed card → concordance → 10 lens tabs →
  aspirational) and is the basis for the spacing scale in §2.
- **"Fira Code / Fira Sans" typography pairing's mood** ("dashboard, data,
  analytics... precise") as a *directional* cue only — BenchUp v3 does not adopt
  a custom webfont (see rejection below); the mood confirms text-forward, low-
  ornament styling is right for this app.
- **Pre-delivery checklist items that restate house/accessibility rules already
  in force:** no emoji-as-icon, visible focus states, 4.5:1 text contrast,
  `prefers-reduced-motion` respected, responsive breakpoints tested. These are
  kept because they are true regardless of source, not because ui-ux-pro-max is
  the authority on them.
- **ux-guidelines.csv "Table Handling" (overflow-x-auto)** — restates the SIRIS
  house rule verbatim; adopted as confirmation, not as new guidance.
- **ux-guidelines.csv "Readable Font Size" (16px floor)** — adopted app-wide per §3.
- **ux-guidelines.csv "Active State" (current nav/tab visually indicated,
  `border-b-2` underline pattern)** — Streamlit's native `st.tabs` already does
  this; noted so a future custom tab component does not regress it.

### Rejected from ui-ux-pro-max (explicit, per brief)
1. **The entire "Enterprise Gateway" pattern** (hero video/mission, mega menu,
   client-logo carousel, "Contact Sales" CTA, path-selection landing) — this is a
   marketing-site pattern; BenchUp v3's Menu page is a nav-card grid to two
   internal tools, not a conversion funnel. No hero, no video, no CTA button, no
   logo carousel.
2. **The persisted colour palette in full** (`#1E40AF` primary, `#3B82F6`
   secondary, `#D97706` accent, `#DC2626` destructive, etc.) — SIRIS colour comes
   exclusively from `lib/palette.py`, validated by the `dataviz` skill's
   CVD/contrast script, not from a generic B2B palette that was never run through
   that validator. None of these hexes appear anywhere in `app/`.
3. **Dark-mode support** ("Light supported / Dark supported") — SIRIS house rule
   is light-only, always; the dark branch is never built, not even as a stub.
4. **"Fira Code / Fira Sans" as an actual webfont import** — no custom Google
   Fonts import ships in Phase 2A (ponytail: Streamlit's system-font default is
   the "one line before fifty" choice; a font import is scope Stream A/E did not
   ask for and no CDN allowlist entry was requested for it). The *mood* is kept
   (§ above), the font family itself is not.
5. **"Hover tooltips, chart zoom on click, row highlighting on hover, smooth
   filter animations, data loading spinners"** as a bundled "Key Effects" list —
   BenchUp v3 keeps hover tooltips (RULES §6/§7) but explicitly has **no motion**
   (SIRIS house rule: "no motion") — no chart zoom, no smooth animation, no
   spinner choreography beyond Streamlit's own built-in (unstyled) loading state.
6. **`ux-guidelines.csv` "Active States" (`active:scale-95` press feedback)** —
   a scale-transform micro-interaction is motion; rejected under the same
   no-motion house rule, even though the category ("show feedback on
   interaction") is legitimate — Streamlit's native button/widget states already
   provide non-animated feedback (colour/border change only).
7. **`ux-guidelines.csv` "Excessive Motion" card's own remedy** ("Animate 1-2 key
   elements per view maximum") — BenchUp v3's remedy is stricter: zero animated
   elements, not one or two. The finding's diagnostic value (too much motion is
   bad) is kept as directional confirmation of the house rule; its suggested
   *floor* of 1–2 animations is rejected as still too much for this app.

## 7. `<slug>` for the record

`design-system/benchup-v3/MASTER.md` — persisted 2026-08-29, density 8/10,
category "Analytics Dashboard", query "peer benchmarking analytics dashboard
higher education research" (`--design-system` mode) + 3 targeted `--domain ux`
queries ("ranked table dense rows readable", "active filters disclosure strip",
"tab navigation many tabs").

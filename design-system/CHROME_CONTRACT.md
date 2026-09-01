# Chrome contract — BenchUp v3 (Stream CHROME-A, Phase 2C, D10)

Normative, one page. Every value below was measured on the RENDERED app (Chromium,
Playwright, `getComputedStyle`) or read off the source constant it comes from — never
guessed. Screenshots and probe logs: `evals/chrome_audit_2C_shots/`,
`evals/_probe_find.json`, `evals/_probe_all.json`. Companion document:
`evals/chrome_audit_2C.md` (the deviation audit this contract is measured against).

## 0. The best existing chart chrome, and why it is the reference

**Reference: Compare's "Compare by" sections** (`views_compare._view_subject` /
`_view_erc` / `_view_sdg`, built on `charts_compare.fig_metric_bars` +
`views_compare._metric_tip` / `_note`). Not the Find profile panels (`fig_share_si`),
which are close but older (2B-R1) and use a plainer caption; not the Find lens tables,
which pre-date the fold pattern entirely (see audit, VF rows).

Why this one: it is the ONLY chrome unit in the app that resolves every one of the six
things the user's directive names — same formatting, same intro pattern, same
tooltip-carried methodology — in one composed sequence, and it is reused **three
times verbatim** (Subject/ERC/SDG) with zero copy-paste drift because all three call
the same four functions. It is also the newest chrome (2B-R2-8, "the wall of prose
deleted"), so it is the one direction to converge the rest of the app on rather than
the reverse.

**The sequence, in argument order (pin this order for every chart/table in the app):**

1. `st.subheader` — section name (e.g. "Compare by subject").
2. Controls row, if any — drill / metric selector / sort toggle, `st.columns` on one row.
3. `_legend` — the shared chip legend (`charts.chip_legend_html`), ABOVE the chart.
4. The chart itself (`st.plotly_chart`).
5. `_note(reading, tooltip)` — **exactly one** reading line + a "?" glyph carrying the
   methodology (scenario, denominator, gutter, reference, low-volume floor, accent,
   SI floors — whichever apply). Never a stack of `st.caption` lines.
6. `_not_offered_expander` — disclosure of what this frame does NOT show and why
   (collapsed, below the note, never above the chart).
7. `_download` — one "Download the figures behind this view" button.

## 1. Page & section titles

| Element | Selector / call | Measured | Notes |
|---|---|---|---|
| Page title | `st.title` (h1) | **44px / 700**, line-height 52.8px, "Source Sans" | Identical on Find/Compare/Collaborate/Methods — the one title level that IS coherent app-wide. |
| Page promise line | `st.caption` under the title | 14px / 400 | e.g. "Where do these institutions differ, and by how much?" |
| Section header | `st.header` (Find "Profile", "Benchmark") | not separately measured (Streamlit h2, larger than h3) | Two per page in Find, none in Compare/Collaborate (they go straight to `st.subheader`). |
| Subsection header | `st.subheader` ("Key figures, side by side", "The relationship, year by year", "L1 · Subfield overlap" gloss lines are NOT subheaders — see audit) | **28px / 600**, line-height 33.6px | This is a bare Streamlit default (`h3`), not a hand-set token. |

**Binding rule:** page title = `st.title`; every chart/table/section intro = `st.subheader`,
never `st.header` (reserve `st.header` for the two page-level divisions Find already
uses: Profile / Benchmark). No third heading level.

**Known drift, flagged not fixed here (owner PAL):** `design-system/DESIGN_TOKENS.md`
§3 declares a hand-built type scale (`text-xs 12 / text-sm 14 / text-base 16 /
text-lg 18 / text-xl 22 / text-2xl 28`). A grep of `app/lib` for `18px`, `text-lg`,
`text-xl` or any `:root`/`<style>` block returns **zero matches** — the scale is
never implemented as CSS anywhere. Every heading measured above is a bare Streamlit
default (44/28/16), not the documented tokens. The one place the token scale IS real
is `lib/tiles.py`'s `LABEL_PX=15 / VALUE_PX=22 / META_PX=12`, which
`charts_compare._card_html` explicitly imports rather than retyping ("so the two
card families cannot drift apart" — its own docstring) — cite this as the pattern to
generalise, not the header scale.

## 2. Chart chrome — fonts, marks, spacing

All from `lib/charts.py` unless noted; these are the numbers every chart/table
should share.

| Token | Value | Role |
|---|---:|---|
| `FONT_PX` | 12 | figure-wide default font (`layout.font`) |
| `GUTTER_FONT_PX` | 11 | bar text (value+gutter), tick labels, annotations — measured live: Compare's "?" glyph renders at **11px**, colour `rgb(90,95,102)` = `INK_SECONDARY`, matching exactly |
| `HAIRLINE_PX` | 1 | every hairline: bar borders, reference dashes, table hairlines |
| `MARKER_PX` / `LINE_PX` | 10 / 2 | SI dot / stem |
| `BUBBLE_MIN_PX` / `BUBBLE_MAX_PX` | 6 / 34 | frontier scatter bubble range |
| `ROW_PX` / `BASE_PX` / `MIN_HEIGHT` | 18 / 50 / 300 | `row_height(n) = max(300, 18n + 50)` |
| `BAR_GAP` | 0.25 | single-series category charts (`fig_share_si`, frontier) |
| `OUTLINE_WIDTH` | 2 (`palette.py`) | frontier flag outline; hollow/low-vol mark border |

**Known drift, flagged not fixed here (owner CHROME-F, confirm with VC before
changing either):** `DESIGN_TOKENS.md` §8.5 documents `ROW_PX/BASE_PX/MIN_HEIGHT =
22/60/300`; the live constants in `lib/charts.py` are **18/50/300**. The doc is
stale (a 2B-R-13 tightening pass changed the code and not the doc) — treat the code
as the reference for the contract above.

**Bar-group spacing has two DIFFERENT constant pairs for what should be one geometry
idiom:**

| Constant pair | Value | Used by |
|---|---:|---|
| `charts.DEFAULT_GROUP_SPAN` / `DEFAULT_GROUP_FILL` | 0.80 / 0.90 | Fields/Subfields/Topics panels, yearly-breakdown pair (`_series_offset_width`) |
| `charts_compare.BAR_GROUP_SPAN` / `BAR_GROUP_FILL` | 0.82 / 0.86 | `fig_metric_bars` (Compare's Subject/ERC/SDG) |

Both feed the same `_series_offset_width` helper, so the visual effect is close but
not identical — a grouped bar in Compare sits fractionally wider/narrower than the
"same" geometry in Find's profile panels. **Owner CHROME-F to reconcile to one pair**
(see audit row VC/CHROME-F "bar-group span").

## 3. Colour, borders, grid (source: `lib/palette.py`, validated — not restated here)

| Token | Value | Role |
|---|---|---|
| `SURFACE` | `#FFFFFF` | every `paper_bgcolor`/`plot_bgcolor` |
| `INK` / `INK_SECONDARY` | `#333333` / `#5A5F66` | value text / secondary text (ticks, gutter numbers, chip labels, "?" glyphs, captions) |
| `BORDER` | `#E3E6EA` | tile/panel hairlines, "?" glyph border |
| `GRID` | `#D9DDE2` | gridlines, zero line — must recede |
| `FOCAL` / `COMPARISON` | `#0072B2` / `#8C9196` | seed institution (ranked views only) / candidate & reference marks |
| `MUTED_OPACITY` | 0.35 | catch-all-topic fill |

Four identity families (OpenAlex domain / ERC domain / SDG / document type), one per
chart, never mixed with `FOCAL` — unchanged from `VIZ_SPEC.md` §1.1, still correctly
followed everywhere audited.

## 4. Legend

- **Form:** `charts.chip_legend_html` — a row of coloured squares + label, `CHIP_PX=12`
  square, `CHIP_GAP_PX=6`, text at `GUTTER_FONT_PX` (11px).
- **Placement:** ABOVE the chart(s) it labels, never beside or below — confirmed on
  the Find breakdown pair, Compare's Subject/ERC/SDG charts and Collaborate's
  domain-crossing chart and year-by-year chart.
- **Rule:** one legend serves a whole pair/section when both panels share the same
  colour key (`showlegend=False` on every trace; the chip row is the only legend).
  Colour follows the entity, not the sort order or the rank — never repainted on
  toggle.

## 5. Hover template skeleton (`charts_compare._metric_hover`, the reference form)

Fixed line order, `<br>`-joined, each line `label + THIN_SPACE + value`:

```
{institution name}
{taxon / row label}
{metric label, lowercase}␣{value}
works␣{gutter volume}                    ← only if the frame carries a gutter column
index reference␣{ref value}              ← only for REF_METRICS (PP, SDG-tagged share, Dynamics)
denominator␣{denom_value, formatted as a NUMBER, never a note string}
†␣few publications a year on average, read with care   ← only if low-volume
```

**Binding fix already load-bearing (do not regress):** the denominator line renders
the numeric `denom_value` column, never the human-readable `denominator` note
string — the two were once conflated and produced a literal "denominator: n/a" bug
(`_metric_hover` docstring). Any new hover builder (FWCI, 2C) must keep this
separation.

## 6. Method-note / caption convention (`charts_compare.chart_note` / `views_compare._note`)

- **Exactly one reading line**, ≤160 characters (`NOTE_MAX_CHARS`), no line breaks —
  enforced at render time (`ValueError`), not a style guideline.
- Reading line in `INK_SECONDARY`, `FONT_PX` (12px), inline with the "?" glyph.
- "?" glyph: a `1px`-bordered circle, `FONT_PX` (12px) box, `GUTTER_FONT_PX` (11px)
  text, `INK_SECONDARY` colour, `title=` attribute (native tooltip, no script) —
  measured live at **11px / rgb(90,95,102)**, matches spec exactly.
- Everything the reading line does NOT say (scenario, denominator sentence, gutter
  meaning, reference identity, low-volume floor, SI floors, accent-colour meaning,
  fractional-only caveat) goes inside the "?", assembled by `_metric_tip`/`_taxon_tip`
  — never typed twice, never left as a second caption line underneath.
- **This is the pattern every chart AND every table intro should converge on.**
  Tables currently do not use it at all (see audit) — `ranked.py`/`views_find.py`'s
  lens-tab gloss+caveat is full prose above the table with no fold, by original
  design intent (`VIZ_SPEC.md` §2.4: "caveat sits directly under the gloss, never
  tooltip-only"). That intent pre-dates this pattern's own existence (2B-R2-8, one
  refinement cycle later) and now reads as the one deliberate, spec-sanctioned
  exception to this contract — CHROME-A does not overrule it, but flags the
  resulting two-system app as the single largest source of "does this chart/table
  introduce itself the same way" inconsistency a reader will notice.

## 7. D5 — new ratio-chart caption rule (spec for 2C; nothing in the shipped app implements it yet)

Every ratio chart (Share, PP, SDG-tagged share, Dynamics, and the new FWCI tabs) gets
**one line under the title**, above the legend, stating corpus basis · floor ·
N-taxa-unscored, parametrically. Style, to sit consistently beside the existing
`_note` line:

- Normal state: `INK_SECONDARY`, `text-xs` (12px), regular weight (400) — same visual
  weight as a `chart_note` reading line, so the two read as one family of small print.
- **Warning state (taxa unscored > 0, or a floor bites): red, NOT bold, small** — D5's
  own wording. Concretely: colour = PAL's new frontier-red (D7, not yet ratified at
  time of writing — do not hand-pick a hex here), weight stays 400, size stays 12px.
  Never `**bold**` red text, never a `st.warning`/`st.error` banner (those add an
  icon+box chrome this contract does not otherwise use for a one-line caption).
- Composition order: subheader → **D5 caption** → controls row → legend → chart →
  `_note` reading+tooltip. The D5 caption is a NEW line, not a merge into `_note`'s
  single-line cap — it states a fact about the DATA (basis/floor/coverage), `_note`
  states how to READ the chart; keeping them separate avoids blowing `_note`'s
  160-character ceiling.

## 8. Tables

Reference: `lib/ranked.py::render_ranked_table` (the shared lens-table form) +
Collaborate's topic table (`views_collab.py`).

- **Column header:** `st.dataframe` default — measured **16px / 700** (bold), `INK`.
- **Body cell:** measured **16px / 400**, `INK`. (Both are Streamlit's bare
  `st.dataframe` styling — no custom CSS anywhere overrides table typography; this
  is consistent across Find/Collaborate, the one table convention that IS coherent.)
- **Progress-bar columns:** `st.column_config.ProgressColumn` — the shared idiom for
  any 0–1 score (`Score` in lens tables, `In the world top decile` / `Tagged to a
  goal` in Collaborate's topic table). **Binding fix required (D9, see audit):** never
  `format="percent"` (locale-dependent, confirmed rendering **comma decimals**
  live — `76,04 %` — on the very column meant to be scannable); use a printf-style
  spec on a value already scaled 0–100, or `format="%.0f%%"` after pre-multiplying
  the column, so every environment renders the same period-decimal string.
- **Link columns:** the institution NAME is the clickable OpenAlex-works link, via
  `st.column_config.LinkColumn` + the `#<urlencoded name>` fragment trick
  (`NAME_LINK_MODE="fragment"`, `ranked.py`) — this is the CANONICAL link convention.
  ~~Collaborate's topic table instead ships a separate trailing "Open" text-link
  column~~ **RESOLVED (VL, 2026-09-01):** Collaborate's topic and untapped tables
  now use the name-as-link convention; the separate "Open" column and its
  `copy.COLLAB["COL_LINK"]` key are retired. One link idiom app-wide.
- **Long-list pattern — two different, both valid, never mixed on one table:**
  - **Find lens/concordance/aspirational tables:** app-wide depth radio `{30, 50}`
    (`ctl-depth`, sidebar-adjacent controls row) + tail search + full-ranking CSV
    export. Row-count caption: *"Showing the top {N} of {M} ranked institutions
    (depth {N})"*.
  - **Collaborate's topic tables:** per-table `ROWS_DEFAULT = 20` + one **"Show all
    {N}"** button (no slider — sliders were retired, 2BR3 tasks 5/6). Row-count
    caption: *"{n} rows shown of {N}."*
  - These are legitimately different tools for different shapes (one ranking with a
    global depth control that must stay in sync across 10 tabs, vs. one self-
    contained per-table cutoff) — the contract does not ask CHROME-F to unify the
    control, only the **caption phrasing**, which currently differs for no reason
    tied to the mechanism (see audit).

## 9. Number formats (D9, binding, printf-style, period decimal, locale-independent)

- One decimal convention app-wide: printf-style format strings (`"%.1f"`,
  `"%.2f"`), never a locale-sensitive keyword.
- `format="percent"` is BANNED. Two live call sites still use it and must be fixed
  by CHROME-F/VF before 2C closes:
  - `lib/ranked.py:193` (`Score` ProgressColumn) — carries a manager comment
    ("printf spec on a 0-1 score printed '1%'") that describes the workaround
    reason but the workaround itself (`format="percent"`) is exactly what D9 bans.
  - `lib/views_find.py:1476` (Aspirational tab's `L1 overlap` ProgressColumn) —
    same reasoning, same fix needed.
- `views_collab.py`'s `FWCI_FORMAT = "%.2f"` is the compliant pattern to copy.
- Every percentage states its denominator in the same cell or the line directly
  above (unchanged house rule, still correctly followed everywhere audited outside
  the two `format="percent"` cells above).
- Thousands separator on every count ≥ 1,000 (confirmed consistent everywhere
  audited — e.g. "7,557 institutions").

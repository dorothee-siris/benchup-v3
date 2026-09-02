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

## 10. Bar-family contract v2 (Phase 2D, stream CH2, 2026-09-02) — E5/E6/E8/E9

Normative source: `evals/wind_tunnel_2D/WT_2D.md` claims 1–3 (the manager read
every PNG named below personally, E13, before ratifying — BUILD_PLAN_2D.md §7).
Reference builder, unchanged from §0 above: `charts_compare.fig_metric_bars`.
**This is the per-chart-TYPE contract E9's propagation audit runs against for
every horizontal-bar chart** — every ratio chart in Compare (Subject/Subfield/
ERC/SDG/FWCI) already draws through this one function, so "propagate" here
means "do not build a second implementation of any of the four rows below",
not "copy code".

| # | Element | Rule |
|---|---|---|
| 1 | **Gutter column (E6)** | `gutter=True` (default): a phantom `go.Bar` trace per institution, offset into the SAME lane as its real bar, at `x = -GUTTER_NEG_AXIS_FRAC * basis * GUTTER_TIP_FRAC` (a DATA-space negative offset, never a pixel margin), text = the row's `gutter_col` value (`vol_display` by default) formatted by `charts._fmt_vol` — an integer when the value is integral, one decimal otherwise, thin-space thousands. `gutter_header` (new parameter) draws ONE small `INK_SECONDARY` label above the column, at `GUTTER_FONT_PX`, naming the basis — the caller supplies the word (VC4/VF4/VL4's job to wire), this module never invents one. |
| 2 | **Caution channel (E5)** | Every bar is SOLID, in the institution's own colour — `marker.color` and `marker.line.color` are both the SAME hex on EVERY point, `marker.line.width` is `HAIRLINE_PX` on every point, and `marker.pattern` is never set. A row `_is_low_volume` flags (E4 floor unchanged: PP/FWCI on `denom_value < palette.RATIO_HATCH_FLOOR`, every other metric on `vol_full_annual_mean < LOW_VOLUME_FLOOR`) switches BOTH its own bar-end value text AND its gutter-column text (row 1) to `palette.WARNING_CAPTION_COLOR` (`#821D13`), weight 400 (never bold), keeping `LOW_VOLUME_GLYPH` (†). The hover keeps the reason line, unchanged. |
| 3 | **Diamond reference (E8)** | Every metric in `REF_METRICS` (pp / share / sdg_share / dynamics / fwci — `share` added post-audit, stream VC4, per E8's own locked ruling that the pre-2D exclusion did not yet implement) that ships a per-row VARYING `ref_value` draws a `go.Scatter` marker per row, `symbol="diamond-tall"` (`REF_MARKER_SYMBOL`), `size=8` (`REF_MARKER_SIZE`), colour `palette.INK`, `hoverinfo="skip"`, added to the figure BEFORE the institution bar traces (so it sits behind a bar's own outside-text at the one row where the two can coincide). A CONSTANT reference (SI's neutral value, or any single-value case) stays ONE rule across the panel, `palette.INK` at `LINE_PX` (2 px), dashed — heavier and darker than the pre-2D `INK_SECONDARY`/`HAIRLINE_PX` dash, but still a rule, never a repeated marker. |
| 4 | **Fonts** | Unchanged from §2: `FONT_PX` (12) figure-wide, `GUTTER_FONT_PX` (11) for bar text, gutter text, gutter header and tick labels. |
| 5 | **Hover skeleton** | Unchanged from §5, with the gutter-column text change carrying no new hover line — the raw volume was already in the hover's "works" line independent of whether the gutter COLUMN is drawn, and stays there. |
| 6 | **Right-of-bar value** | Unchanged: `textposition="outside"`, `cliponaxis=False`, the value at the bar's own outer end. The pre-2D bar-end PARENTHESISED volume (`"{value} ({volume})"`) is RETIRED — row 1's dedicated column replaces it everywhere; a bar's own text now carries only its value (+ † when cautioned). |
| 7 | **Below ~600 px plot width** | The gutter column (row 1) has nowhere to go — WT_2D measured a wrapped first-row label alone can need the large majority of a 390 px figure's own width. Streamlit cannot read the viewport width server-side (unchanged constraint, §2.15/VIZ_SPEC's `fig_share_si`'s `stacked` argument already lives with this), so `fig_metric_bars` exposes `gutter=False` as the OFF switch and the CALLER (VC4/VF4/VL4) decides when to pass it below that breakpoint. There is never a horizontal scroll either way — the raw volume stays in hover regardless. |

**Binding fix carried in the same round (E11, not a chrome rule but load-
bearing for row 1 above at real density):** `metric_row_height`'s fallback
branch now folds `n_wrapped` into its own per-row `need` estimate — see §12.

## 11. Dot/SI-family contract v2 (Phase 2D, stream CH2, 2026-09-02) — audited, confirmed

`fig_share_si` (Find's profile panels) and `fig_mirror_dots` (Compare's dot-
row mirror, where still called) are a DIFFERENT chart TYPE from row 10's bar
family — a filled/hollow DOT, not a bar — and 2D's brief asked whether any of
row 10's changes should propagate to them. Audited and judged NO on all three
counts, each for a reason specific to the dot family, not by default:

| # | Element | Ruling |
|---|---|---|
| 1 | **Below-floor marker** | STAYS a hollow dot (SURFACE fill, institution-coloured `OUTLINE_WIDTH` outline) — UNCHANGED. A filled-vs-hollow marker swap still reads as an IDENTITY (a ring in the institution's own hue), not a hole or a damaged mark, which is a different visual grammar from the diagonal `marker.pattern` texture row 10 §2 retires from bars — the two were never the same mechanism wearing different names, so retiring one does not obligate retiring the other. Plotly's own pattern fill is a Bar-family feature with no Scatter-marker equivalent in the first place (unchanged reasoning, `fig_metric_bars`'s own pre-2D docstring). |
| 2 | **Gutter mechanism** | STAYS folded into the row's own tick label (`charts._tick_display`) — NOT unified with row 10 §1's phantom-trace column. Different problem shape: one number per row (this chart shows ONE institution) vs up to three. WT_2D's own prior-art note: an EARLIER version of this exact gutter WAS a separate annotation in a negative-x sliver — precisely row 10 §1's refuted candidate A — and was retired because it relied on `automargin` to keep two independently-positioned text systems apart, which collided at 390 px. Re-splitting it back into a column now would reintroduce the bug its own fix already solved, for a chart that never needed the up-to-three-numbers form. |
| 3 | **Reference mark** | STAYS a dashed vertical rule at the neutral/index value, with the existing unit grid — NOT the diamond marker. Row 10 §3's diamond specifically answers "a reference next to a panel already full of solid bars, where a thin dash reads as a stray pixel"; the dot family's reference sits against a MOSTLY EMPTY panel (WT_2D claim 3's own distinction, drawn from `VIZ_SPEC.md` §5.5's original reasoning), where the same dash reads cleanly — a different situation, not an oversight. |

**Fonts, hover skeleton:** unchanged from §§2/5 for both families — the dot
family was never asked to change these, and did not.

## 12. Dynamic-viewport proof-capture rule (Phase 2D, stream CH2, 2026-09-02) — E11

**Binding for every proof script (this round's and future ones) that
screenshots a `.js-plotly-plot` element:** before capturing, read the chart's
own rendered height — `gd.layout.height` via `page.evaluate`, or the
element's `getBoundingClientRect().height` — and set the page's viewport to
AT LEAST that height. **Never a viewport fixed in advance.**

**Why, with evidence:** WT_2D.md claim 2 root-caused 2C's "first row clipped"
symptom (`evals/vc_2C_shots/subject_share_1920.png`) to `render_proof.py`'s
own `viewport={"height": 1400}`, applied to EVERY chart regardless of its own
declared height. The identical live app, identical URL, identical chart,
captured at a viewport TALLER than the chart's own `layout.height` (1700 px
vs. a declared 1513 px) renders the first row perfectly, every wait duration
tested. `gd.layout.height`, the element's `getBoundingClientRect().height`
and the SVG's own `height` attribute were all self-consistently 1513 px
throughout — the chart's internal geometry was correct; only the SCREENSHOT
HARNESS was lying about what the app renders. A 26-row × 3-series share
chart legitimately needs 1513 px (`metric_row_height(26, 3, 0)`); ANY fixed
viewport is a ticking version of the same bug for the next chart that
exceeds it, not a fix for this one instance.

`evals/ch2_2D_shots/`'s own capture script implements this rule (read the
element's bounding box, resize the viewport, THEN screenshot). I5's
inspection battery and any later grouped-bar proof script should adopt the
same pattern rather than a fixed height.

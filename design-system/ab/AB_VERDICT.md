# A/B verdict -- Stream D1

Produced 2026-08-29. Both A/Bs run on real engine output for University of
Gdansk (`I40413290`), the seed named in `BUILD_PLAN_2A.md` Stream D1 and
`VIZ_SPEC.md` §3. All four prototypes ran headless without exception
(`run_ab.py` output below); screenshots read visually per the Streamlit
gotcha list ("glide-data-grid canvas tables defeat text-based assertions --
verify via element screenshots ... never inner_text").

## `run_ab.py` output (headless, all four PASS)

```
Saved .../ab1_a_1280.png
PASS: design-system/ab/proto_ab1_a.py
Saved .../ab1_b_1280.png
PASS: design-system/ab/proto_ab1_b.py
Saved .../ab2_a_1280.png
PASS: design-system/ab/proto_ab2_a.py
Saved .../ab2_b_1280.png
PASS: design-system/ab/proto_ab2_b.py
```
(One real bug found and fixed en route, kept here for the record: `proto_ab2_b.py`
built a mixed None/int column, which pandas upcasts to float64/NaN -- `v is None`
never matched, `int(NaN)` raised `ValueError`. Fixed to `pd.isna(v)`, the exact
"category-dtype `.map()`" gotcha family, generalised to "check `pd.isna`, not
`is None`, on any pandas-touched column." `proto_ab1_b.py`'s Plotly panel also
needed an explicit wait for `.js-plotly-plot .scatterlayer` in `run_ab.py` --
`st.dataframe`'s own paint is not a proxy for a sibling Plotly chart's paint.)

## A/B #1 -- score column in `tbl-lens-ranked`

Seed: University of Gdansk (`I40413290`), lens L1, top-30.

| Criterion | A: ProgressColumn | B: Plotly ranked-dot chart |
|---|---|---|
| Rows visible above the fold, 1280x900 | 10 (one coherent panel: rank+institution+country+type+size+score all in the same scrollable region) | Table panel: 10 (same Streamlit default auto-height as A). Chart panel: ~20, in its OWN scroll region, independent of the table's | 
| Institution-name truncation | 0 (longest name in view, "Adam Mickiewicz University in Poznan", renders in full) | 0 (same names, same column, in fact wider since the score column freed the space) |
| Zero-baseline compliance | Yes -- bar starts at the column's left edge, `min_value=0` | Yes -- `fig.update_xaxes(range=[0, 1], zeroline=True)` |
| Honest tie rendering | No tied competition rank exists in the L1 top-50 of any of the 19 D19 seeds (checked programmatically, see below) -- **none found**, so this criterion could not be exercised on real data for either candidate. By construction: A renders two tied rows as two bars of identical length, in adjacent rows -- unambiguous. B renders two tied scores as two dots at the identical x, distinguished by y (rank/row) -- also unambiguous, since y is row order, not value. **Tie for this criterion on the available data.** |

**Screenshots:** `ab1_a_1280.png`, `ab1_b_1280.png` (also `ab1_a_1920.png`,
`ab1_a_390.png` for the winner).

**Tie check (programmatic, not visual):** `evals/d19` seeds' L1 top-50 scanned
for a repeated competition rank -- `check_ties.py`-style scan over all 19
seeds: `NONE FOUND: no tied competition ranks in the L1 top-50 of any D19 seed`.
The engine's histogram-intersection score is continuous enough that exact
float ties are rare; BUILD_PLAN_2A.md L9's tie rule stays load-bearing for the
depth CUT (several institutions can tie exactly AT the cutoff score, which is
a different event from two ADJACENT ranks both being included -- the cut
mechanism was exercised correctly on every render above, just not with two
rows sharing one visible rank in this specific seed/lens).

**Winner: A (`st.column_config.ProgressColumn`).**

One paragraph why: both candidates satisfy zero-baseline and show the same
row count above the fold in their table portion, and neither could be
discriminated on tie honesty (no tie exists in the rendered data). The
decisive difference is structural: A renders rank, identity, and score
strength in ONE coherent, single-scroll widget, with the percent value printed
directly on the bar (no hover needed to read "how strong the read is," the
card's own decision sentence). B needs TWO widgets kept in sync (a
`st.dataframe` and a `plotly_chart`), and they do **not** share a scroll
region -- past row 10, the table needs its own internal scroll while the
chart (rendered at fixed height to show all 30 points) exposes rows 11-20
before the table does, which means a reader can be looking at the dot for
rank 15 while the table beside it still only shows ranks 1-10: the two panels
drift out of visual sync. That drift is exactly the kind of "does the form
imply something the data doesn't" failure Studio RULES.md §9 flags, even
though it is not a zero-baseline or tie-rendering violation in the technical
sense. A also avoids doubling the per-lens-tab implementation surface for
Stream E (one `st.dataframe` call vs. one table AND one chart, always kept in
lockstep across every lens tab). **Downstream, per VIZ_SPEC.md §2.5, the
Aspirational tab still never uses A alone** -- a bare progress bar cannot
render a confidence interval, so that tab keeps its own interval-mark form
regardless of this verdict.

## A/B #2 -- concordance overview form

Seed: University of Gdansk (`I40413290`), the 8 default lenses (L0 L1 L3 F1
L2f L4 L5 L6), N=30.

| Criterion | A: k-count table + hit-lens chips | B: full rank matrix |
|---|---|---|
| Rows visible above the fold, 1280x900 | 9 | 9 (same Streamlit default auto-height) |
| Label truncation | 0 | 0 |
| Fits full width without PAGE-body horizontal scroll, 1280px | Yes -- 6 columns, table width well inside 1280 | Yes -- institution+country+8 lens columns, table width still inside 1280 |
| Fits full width without PAGE-body horizontal scroll, 390px | Yes (page body). The TABLE's own `overflow-x:auto` is used (house rule allows this) -- institution+country+type visible, `k of n`/`hit_lenses`/`size` need ONE internal table scroll | Yes (page body). Same pattern, but institution+country+L0 visible only -- the other 7 lens columns need internal table scroll |
| Honest read of ties/undefined cells | Hit-lens list only ever names lenses that DID find the candidate -- no ambiguous cell exists in this form by construction | Every non-hit cell renders the literal string `"--"` (never blank, never 0), distinct from `palette.NA_MARK` ("n/a" = lens undefined for the WHOLE seed) -- satisfies Studio RULES.md §9.12 explicitly and visibly |

**Screenshots:** `ab2_a_1280.png`, `ab2_b_1280.png`, plus `ab2_a_390.png` and
`ab2_b_390.png` (390px comparison, decisive below), and `ab2_a_1920.png` for
the winner.

**Winner: A (k-count table with hit-lens chips).**

One paragraph why: at 1280px both forms are equally legible, equally free of
truncation, and both stay inside the page width. The decisive evidence is the
390px render: candidate A's table needs only ONE internal horizontal scroll
to reveal the two columns that actually answer the view's decision sentence
("candidates multiple independent lenses agree on") -- `k of n` and
`hit_lenses`. Candidate B's matrix shows institution + country + exactly ONE
of the 8 lens columns (`L0`) before its own internal scroll is needed, so a
390px reader sees almost none of the actual concordance signal without
scrolling through most of the 8 columns first. Both forms are RULES-compliant
(page body never scrolls sideways in either, per the house rule that wide
tables get `overflow-x:auto` on the table itself), but A reaches its answer
in far less scrolling on the width that matters most for this failure mode.
This also matches VIZ_SPEC.md §2.3's own reasoning for proposing A as the
default: INDICATOR_SPEC_v2 §3 already calls concordance "the cleanest list,"
and a single sortable `k` number serves that read more directly than a matrix
that needs all 8 lens columns to stay legible. B's real strength --
column-wise "who did L6 find" scanning -- is a genuinely different question
than the overview's own decision sentence, and is exactly the question a
`tbl-lens-ranked` tab (L6's own tab) already answers per-lens.

## Downstream consequence for `lib/ranked.py`

- `render_ranked_table`'s `score_form` implements A/B #1's winner: a
  `ProgressColumn` (0-100, `%.0f%%`), never a Plotly chart, for every ordinary
  `tbl-lens-ranked` tab. The Aspirational tab does not call this path (its own
  interval-mark form, per VIZ_SPEC.md §2.5, is untouched by this verdict).
- `format_concordance` / `render_concordance_table` implement A/B #2's
  winner: k-of-n + hit-lens-chip text, never the full rank matrix, for the
  concordance overview tab.

---

# A/B verdict -- Refinement R1, stream R-D2 (2026-08-29)

Two more A/Bs, both run on REAL deployed data through a throwaway Streamlit
prototype photographed by Playwright at 1280x900 and 390x844 (kaleido is not
installed and is not to be added, so every PNG below is a real browser paint).

* prototype: `design-system/ab/proto_r1.py` (one app, `?variant=` selects the form)
* runner:    `design-system/ab/run_ab_r1.py` (launch -> screenshot -> measure -> terminate)
* frames:    `design-system/ab/_common_r1.py` builds the BUILD_PLAN_2A.md section 9.4
  column contracts straight from `data/fields.parquet` / `data/subfields.parquet`
  (`lib/profile_data.py` is stream R-B's and did not exist yet -- deliberately
  not imported)
* seeds:     **Universite de Strasbourg `I68947357`** (resolved by `display_name`
  in `data/index.parquet`; 19,402 full works, 25 fields) and **University of
  Gdansk `I40413290`** (8,786 full works, top-20 subfields), tree `bestfit`,
  basis `frac`

Commands, verbatim:

```
$ python design-system/ab/run_ab_r1.py --port 8631
ab3_a: saved ab3_a_1280.png  {'n_plots': 2, 'plot_w': 1120, 'plot_h': 610, 'plot_area_w': 549, 'y_labels': 25, 'n_bars': 25, 'longest_bar_px': 521, 'scroll_ok': True}
ab3_b: saved ab3_b_1280.png  {'n_plots': 2, 'plot_w': 1120, 'plot_h': 610, 'plot_area_w': 857, 'y_labels': 25, 'n_bars': 25, 'longest_bar_px': 540, 'scroll_ok': True}
ab4_a: saved ab4_a_1280.png  {'n_plots': 1, 'plot_w': 1120, 'plot_h': 610, 'plot_area_w': 857, 'y_labels': 25, 'n_bars': 25, 'n_annotations': 25, 'annotations_clipped': 0, 'longest_bar_px': 726, 'scroll_ok': True}
ab4_b: saved ab4_b_1280.png  {'n_plots': 1, 'plot_w': 1120, 'plot_h': 610, 'plot_area_w': 857, 'y_labels': 25, 'n_bars': 25, 'n_annotations': 25, 'annotations_clipped': 0, 'longest_bar_px': 726, 'scroll_ok': True}
PASS

$ python design-system/ab/run_ab_r1.py --port 8632 --widths 390
ab3_a: saved ab3_a_390.png  {'plot_area_w': 61,  'n_bars': 25, 'scroll_ok': True}
ab3_b: saved ab3_b_390.png  {'plot_area_w': 95,  'n_bars': 25, 'scroll_ok': True}
ab4_a: saved ab4_a_390.png  {'plot_area_w': 95,  'n_annotations': 25, 'annotations_clipped': 0, 'longest_bar_px': 81, 'scroll_ok': True}
ab4_b: saved ab4_b_390.png  {'plot_area_w': 95,  'n_annotations': 25, 'annotations_clipped': 1, 'longest_bar_px': 81, 'scroll_ok': True}
PASS
```

No server was left running (the runner terminates its subprocess in a `finally`).

## A/B #3 -- the share + SI form

**A** -- two aligned panels of ONE figure, sharing the y axis: horizontal share
bars on the left, SI as a lollipop (stem from the neutral reference to the
value, dot at the value) on its own x-axis on the right, with a dashed vertical
reference line at the neutral value; a row whose SI is `n/a` gets no mark.

**B** -- one panel, ONE axis: the share bar, plus a tick on the same row at that
row's EXPECTED share (`share / SI`), so SI is read as the ratio of two lengths.
This is the strongest LEGAL form of the brief's "SI as a secondary marker on the
same row": a second x-scale on the same row would be a dual-axis chart, which
the `dataviz` non-negotiables forbid outright ("the #1 chart mistake"). B is
therefore a real rival, not a strawman.

| Criterion (measured, not eyeballed) | A: aligned panels | B: expected-share tick |
|---|---|---|
| Is SI comparable ACROSS rows? | **Yes** -- one shared x-scale; two rows with the same SI put their dots at the same x, so the panel reads as a ranking | **No** -- the tick's position depends on that row's own share, so equal SIs land at different x. Ranking by SI needs a hover on every row |
| Rows where SI is unreadable without hover (mark within 4 px of its reference or of the bar end) | 1 of 25 (Strasbourg), 1 of 20 (Gdansk) | **2 of 25** (Strasbourg), 1 of 20 (Gdansk) -- and these are the rows whose SI sits *near the neutral value*, the single most consequential read on the panel |
| Effect on the PRIMARY measure (share) | none -- the share axis ends at the largest share | **share axis stretched x1.59** on Strasbourg: the largest share is 21.1 % but Medicine's expected share (0.2114 / 0.6303) is 33.5 %, so every share bar is drawn ~37 % shorter than the panel could draw it. Any row with SI below the neutral value does this |
| Plot-area width at 1280 px | 549 px share + 549 px SI | 857 px share only |
| Category labels drawn | once (shared y) | once |
| `n/a` rendering | literally no mark; the row keeps its share bar and its hover says `n/a` | the tick is simply absent, which is visually identical to "expected share = 0" |
| Plot-area width at 390 px | **61 px per panel** -- the form's real cost | 95 px |

**Winner: A (two aligned panels, shared y, SI lollipop from a dashed reference).**

B loses on the criterion that decides what the panel is FOR. The SI column exists
so a reader can see at a glance which of an institution's fields it is over- and
under-specialised in *relative to each other*; B's encoding makes that comparison
unavailable, because the same SI renders at a different x on every row. Worse, B
degrades the primary measure to do it: on real Strasbourg data the share axis
stretches by a factor of 1.59 to fit a tick belonging to a row whose bar ends at
21 % -- visible in `ab3_b_1280.png`, where the axis runs past 30 % and the bars
are visibly foreshortened.

A pays for its win with width, and with a genuine 390 px problem: at that width
each panel collapses to 61 px, which is not a chart. **Consequence, written into
VIZ_SPEC section 1.8 rather than waved away: below the small breakpoint the two
panels STACK vertically (share above, SI below, same row order) instead of
sitting side by side.** Implemented in `lib/charts.py::fig_share_si`, which also
collapses to a single panel when NO row in the frame has a defined SI --
exercised by `tests/test_charts.py::test_fig_share_si_all_na_si_collapses_to_one_panel`
on Gdansk's real below-floor subfields.

## A/B #4 -- where the volume number goes

**A** -- a LEFT TEXT GUTTER (BenchUp V2 `Streamlit/benchup_topics.py`'s
`left_pad_px = 80` idiom): the x range starts below zero and the volume prints in
that reserved strip, in one aligned column, with a hairline marking the zero
baseline. **B** -- RIGHT-OF-BAR annotations (BenchUp V1 `my_app/lib/viz_helpers.py`;
Lorraine `plot_global_breakdown_h`'s `xanchor="left", xshift=8` with an x1.18
range headroom).

Both variants were given the SAME horizontal budget on purpose (gutter = 0.16 of
the range; right headroom = x1.18 -- both a 1.18x span), so the comparison
isolates PLACEMENT and not space. The measurement confirms the control held:
identical `plot_area_w` (857 px at 1280, 95 px at 390) and identical
`longest_bar_px` (726 / 81) in both variants.

| Criterion | A: left gutter | B: right of the bar |
|---|---|---|
| Annotations clipped at 390 px | **0 of 25** | **1 of 25** -- the top row's number is cut off mid-digit (visible in `ab4_b_390.png`) |
| Annotations clipped at 1280 px | 0 of 25 | 0 of 25 |
| Horizontal travel from a row's category label to its volume number | **constant** (std 0 px) -- one aligned column | 17 px to 865 px, **std 204 px** (Strasbourg); 101-865 px, std 183 px (Gdansk) |
| Can volumes be compared down the column? | yes -- one column, a vertical scan | no -- a zig-zag; the eye finds each number at a different x |
| Does the number sit next to the thing it describes? | yes -- immediately right of the category name | no -- at the far end of a variable-length bar |
| Zero baseline | clean; nothing attached to the bar's end | clean, but every bar carries a trailing label that reads as extra bar length at a glance |
| Plot area / longest bar at 1280 px | 857 px / 726 px | 857 px / 726 px (identical by construction) |

**Winner: A (left text gutter), with the numbers RIGHT-ALIGNED against the
baseline.** Right alignment is the one change made between the prototype (which
left-aligned them) and the shipped `lib/charts.py`: aligning the digits is the
whole point of putting the numbers in a column.

The decisive evidence is the 390 px clip -- B loses a digit off a real number at
a width this app is required to render at, and it does so on the largest, most
important row. The travel measurement is the second reason and the one that holds
at every width: B scatters 25 numbers across 850 px of chart, so "which field has
the most works" becomes a search rather than a scan.

**Scope of this verdict, stated so it is not over-applied:** it governs a volume
number sitting BESIDE a bar that encodes a DIFFERENT measure (a share). It does
NOT govern a direct label on a bar that encodes that very number -- the
yearly-breakdown global panel, where the bar IS the count. There the number stays
at the bar's end (`lib/charts.py::fig_breakdown_global`, Lorraine
`plot_global_breakdown_h`), which is the textbook direct-label case from the
`dataviz` mark specs.

## Screenshots

`ab3_a_1280.png` `ab3_b_1280.png` `ab4_a_1280.png` `ab4_b_1280.png`
`ab3_a_390.png` `ab3_b_390.png` `ab4_a_390.png` `ab4_b_390.png`
(all in `design-system/ab/`)

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

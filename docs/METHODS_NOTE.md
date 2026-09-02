# BenchUp v3 methods note (source text)

**This file is not rendered by the app.** The Methods page renders `lib/copy.py`'s `METHODS` dict,
whose numbers are `{placeholders}` filled at run time from the config, the manifest and the index
(`BUILD_PLAN_2B.md` §0 A5). This file carries the same sections with the numbers written out and a
citation per claim, so a reviewer can check what the page says without reading the data. Keep the
two in step: `tests/test_methods_note.py` fails when a `METHODS` section has no `## ` heading here,
or when a template grows a placeholder `METHODS_SOURCES` does not document.

Snapshot described here: **august_2026** (`app/data/MANIFEST.json` `snapshot`), index of **7,557**
institutions (`MANIFEST.json` `files["index.parquet"].n_rows`).

---

## What counts as a publication

A publication is an OpenAlex record of type article, review, book, book chapter or letter, carrying
a DOI and published between 2020 and 2024 (`app/config.yaml` `corpus_types`, `openalex_filters`,
`window`; harvest filter in `pipeline/01b_harvest_eu27_aug.py` lines 10 to 14). 2025 is harvested as
a bonus year and reported for volumes only (`app/config.yaml` `bonus_year`; `DESIGN.md` §2.2, D1).

Every institution in the index sits in one of the 31 perimeter countries: the European Union, the
United Kingdom, Switzerland, Norway and Iceland (`app/config.yaml` `perimeter_countries`;
`DESIGN.md` §2.1, D10). Retracted records are counted in the totals and left out of the subject
classification, so the subfield, topic, ERC and SDG panels rest on a slightly smaller set than the
size figures (`pipeline/agg/enriched_corpus.py::classify_grey_state`).

The page reuses the Find tab's own tooltip for this section (`copy.FIND["PUBLICATIONS_TOOLTIP"]`),
so the two can never diverge.

## Attribution, and the two counting bases

An institution is credited with a publication when the record names that institution directly.
OpenAlex's lineage graph is never used: for a French institution sharing a joint unit with a
partner it grafts the partner's whole portfolio onto the parent, inflating the count by up to
eight times (`DESIGN.md` §2.2, D5; SIRIS `CLAUDE.md`, OpenAlex gotchas).

Full counting credits the whole publication to every institution named on it. Fractional counting
gives each author 1/n of the publication and splits that part across the institutions the author
declares (`DESIGN.md` §2.2, D5). ERC, SDG and impact figures are fractional whatever the counting
setting says (`app/docs/data_contract.yaml`, `erc.share` and `sdg.share` entries;
`copy.FIND["BASIS_NOT_APPLIED_TOOLTIP"]`).

OpenAlex list endpoints truncate `authorships` at 100 entries without saying so, so any work
returning exactly 100 authorships is re-fetched singly (about 9,325 EU27 works, the
mega-collaborations); `DESIGN.md` §2.2, R1.1.

## Which figures follow the counting-basis setting

One setting, full or fractional counting, reaches every volume figure in the tool: the chart
value, the gutter beside it and the number a hover names as the denominator all move together
(`app/docs/data_contract.yaml`, "metric_frame v4", `denom_value` note; `progress/2BR3_CD4.md`).

Three figures sit outside that setting on purpose. The tool's two impact figures, FWCI_EU and
PP10_WD, are always read on full counting: a publication counts once toward every institution it
names (`pipeline/19_impact_taxa.py`, `impact_work.parquet`, weight columns dropped;
`pipeline/17_fwci.py`, the same convention, decisions log 2026-09-01). PP10_WD changed basis this
round: an earlier release read it on fractional counting instead (`index.parquet`
`pp_top10_frac`), and the golden cross-check institution x field cell used to reconcile the two
reads 16.8% on full counting against 10.9% on the old fractional one, a gap of full attribution
basis rather than any change in the underlying publications (`progress/2D_P9.md`, three-way
golden, decisions log 2026-09-02). The per-goal SDG share (`sdg.parquet`) is likewise always
fractional, over its own six-year window. The SDG tagging crossed with a field or with a year
(`sdg_fields.parquet`/`sdg_year.parquet`, v2, 2026-08-31) no longer belongs on that list: both now
ship a fractional and a full column (`mass_any_frac`/`mass_any_full`, `mass_frac`/`mass_full`) on
the same window the field and year figures around them use, so the setting reaches them like
everything else.

## Two baselines, and why the tool keeps them apart

FWCI_EU and PP10_WD are never averaged into one score: they read two different reference
populations. FWCI_EU is a typical-level reading, each publication against the average publication
of the same subfield, year and document type across the tool's European baseline, the 31-country
population named above (`pipeline/17_fwci.py`, `fwci_taxa.parquet`). PP10_WD is an excellence-tail
reading, the share of an institution's output landing in the world top decile of citations for its
own subfield, year and document type, computed against the whole world instead
(`pipeline/19_impact_taxa.py`, `impact_taxa.parquet`, the August 2026 `world_thresholds.parquet`
vintage). The two differ on two axes, not one: what each measures (typical level versus excellence
tail) and whom each is measured against (the European baseline versus the world) -- an institution
can sit close to the European typical level on FWCI_EU while still standing out, or not, on the
world's own top decile.

## The European average behind a reference line

The Sustainable Development Goals and the ERC panels each carry two different "average
institution" constructions, computed on purpose in two different ways. Find's own specialisation
index (`sdg.esi`) is a ratio of sums: it adds every institution's numerator and every
institution's denominator separately across the whole population first, then divides the two
totals, so it reads as though the population were one large, pooled institution
(`docs/data_contract.yaml`, `sdg.parquet.esi` entry, `pipeline/agg/erc_sdg_long.py::build_sdg_long`
`europe_avg` line). Compare's own reference line (`share_refs.parquet`, `eu_mean_share`) is instead
an unweighted mean of ratios: the average, across institutions with a nonzero share in that cell,
of each institution's own share, so a small institution counts exactly as much as a large one
(`docs/data_contract.yaml`, `share_refs.parquet` entry; ratified for the SDG grain
2026-09-02, `evals/wind_tunnel_2D`, claim 5, to match the same convention `fields.si` and
`subfields.si` already use). Neither is more correct; each page names which one it shows.

## How co-publication is counted

A co-publication is a work naming both institutions directly, counted in full: a single
heavily co-authored paper still adds one to the pair's total (`app/docs/data_contract.yaml`,
`collab_pairs.parquet`). Every pair of indexed institutions sharing at least one work, any
document type, over the whole run window, is counted at all, over the exact corpus union the
rest of the tool uses, `openalex_eu27_aug` UNION `openalex_supplement` per year, eu27_aug
canonical on id overlap (`pipeline/agg/enriched_corpus.py::load_year_corpus`;
`progress/2BR_P2.md`). That widest population is also what the year-by-year relationship chart
draws, 2020 to 2025, the 2025 bar drawn hollow as a partial year.

Every other Collaborate number reads a narrower, matched population instead, ruling 3 of the
2026-08-31 refinement round: articles and reviews only, 2020 to 2024, still full counting (the
CORE-AR basis, `app/docs/data_contract.yaml`, `window_conventions.core_ar_window`). That
population is what `collab_pairs.parquet`'s `core_total`/`c1`/`c2`, the topic and field
breakdown, the goal-tagged count, the median citation-impact figure and the momentum reading are
all built on, and it is the exact filter (`type:article|review,publication_year:2020-2024`)
carried on every OpenAlex link at pair and topic grain, so the number on the page and the count
the link opens on agree there. Ranks are computed in both directions on this same narrower
population, before any floor is applied: `rank_in_a` and `rank_in_b` are two different dense
ranks over the same pair, RECOMPUTED on `core_total` rather than the old `copubs_total`
(`app/docs/data_contract.yaml`, `collab_pairs.parquet` v2).

`collab_pairs.parquet` itself still carries no floor on the wide, all-document-type population:
all 3,581,332 a<b pairs with at least one shared work ship (WT A1, unchanged at v2). The
topic-level breakdown in `collab_pair_topics.parquet` needs a floor to stay meaningful, now
measured on the narrower CORE-AR population: pairs with at least 5 shared articles and reviews
get up to the top 100 shared topics by joint volume, read off each work's primary topic only,
never every topic it touches, so one paper is never counted into more than one row
(`lib.views_methods._collab_pair_topic_facts`, measured live off the shipped v2 tables,
2026-08-31). 913,512 pairs clear the floor on the shipped snapshot (`progress/2BR3_P7.md`); a
pair below it keeps its total and a link to every shared publication, and loses the topic, SDG
and ERC breakdown (`copy.COLLAB["TOPIC_BELOW_FLOOR_NOTICE"]`).

## Reading a pair's shared subjects

The 2B-R2 regeneration of the pair tables ships a floor of 5 shared works (raised from the 2B-R
floor of 3) and up to the top 100 shared topics per pair by joint volume (raised from 20),
measured live off the shipped `collab_pair_topics.parquet` at 5 and 100 respectively
(`lib.views_methods._collab_pair_topic_facts`, `progress/2BR2_P6.md`). The same shared works are
also rolled up to field level, uncapped: every field a pair has any joint work in ships, since a
pair spans a mean of about 4 distinct fields, far fewer than its topic diversity
(`app/docs/data_contract.yaml`, `collab_pair_fields.parquet` grain, WT #13).

Two impact-adjacent figures ship per topic or field row: `n_covered` and `n_top10`. Covered means
the row's joint publications published 2020 to 2024, article or review only, non-retracted, that
fall in a (subfield, year, document type) cell the world citation-threshold table actually covers;
the threshold table is null on a meaningful share of cells, so a joint publication in an uncovered
cell counts in the row's total but in neither of these two figures
(`app/docs/data_contract.yaml`, `collab_pair_topics.parquet.n_covered`; WT claim #7). `n_top10` is,
of the covered works, how many reach the world subfield x year x type top-decile citation cutoff,
using the exact same `>=` convention as `agg/impact.py::join_thresholds`'s `pp_hit`. Volume-weighted
coverage across the shipped snapshot is 98.4% on topics and 98.3% on fields, well above the raw
76% cell-coverage rate, because joint works cluster in the larger, denser cells that are most
likely to carry a threshold (`progress/2BR2_P6.md`). The subfield behind every covered cell is
read under the best-fit taxonomy only: no tree-neutral subfield column exists on the topic
dictionary, and shipping all three trees on this table would triple its size for a secondary fact
(WT claim #8).

A field-weighted citation index (FWCI) ships as of the 2026-08-31 refinement round: each
publication's own citation count, set against the average a publication of the same best-fit
subfield, the same publication year and the same document type collects across the tool's own
European reference corpus, articles and reviews, 2020 to 2024, the same 31-country population
the rest of the tool draws on (`pipeline/17_fwci.py`; `app/docs/data_contract.yaml`,
`fwci_ref.parquet`). A (subfield, year, type) stratum with fewer than 50 works falls back to
(field, year, type), and if that is still under 50, to (year, type) alone; 709 of 2,327 strata
(30.5%) needed a fallback on the shipped build (`progress/2BR3_P7.md`). Every topic and field row
carries the median FWCI across its own CORE-AR joint works with a value, left null under 3 such
works (`app/docs/data_contract.yaml`, `collab_pair_topics.fwci_median`/`collab_pair_fields.
fwci_median`). The reference is Europe, not the world: the citation-weighted mean FWCI is
verified equal to 1 (max deviation 5.960e-08) on every non-fallback stratum, by construction, but
that is a Europe-only 1, not the ≈1.22 world-mean convention SIRIS `CLAUDE.md`'s OpenAlex
gotchas describes for a world-referenced FWCI, and the two are never comparable
(`progress/2BR3_P7.md`, invariant suite). The mean-citations column this table once carried
(`collab_pair_fields.parquet` v1) is dropped; FWCI supersedes it, and the field table no longer
needs the size trade-off that column once forced (`app/docs/data_contract.yaml`,
`collab_pair_fields.parquet` v2, `dropped_column` note).

One caveat applies at field grain only, never at pair or topic grain: the taxonomy repair this
tool reads field membership through can place a publication in a different field from the one
OpenAlex's own record names as primary. Golden-sample checks against live OpenAlex found
pair-grain CORE-AR counts within 0.03% of the live count (Strasbourg × CNRS: 10,587 here, 10,584
live), while 5 of 6 field-grain checks differed by 5.2% to 20.5%, entirely explained by that
taxonomy difference rather than a counting error (`progress/2BR3_P7.md`, golden JSON; the same
approximation `lib/links.py::copubs_taxon_url`'s own docstring already names for every other
field-grain link in the tool). A field row's OpenAlex link can therefore open a nearby but not
always identical count to the figure beside it; a topic-level link, and the pair's own overall
link, both open the exact count shown.

Every topic row, every field row and the pair as a whole carries a link to OpenAlex, filtered live
to exactly the joint publications behind that row. There is no offline browsing mode for this
detail: the deep dive is always the live OpenAlex list, and it can drift a little from the
snapshot the way every OpenAlex link in the tool does (`copy.FIND["LINK_OPENALEX_HELP"]`).

## Reading momentum

Momentum reads whether a pair's CORE-AR output is speeding up or slowing down, on the same two
windows Dynamics reads elsewhere, 2020-2022 against 2023-2024
(`app/docs/data_contract.yaml`, `window_conventions.dynamics_window_1`/`_2`). The raw ratio
`r = (c2/d2) / (c1/d1)` (the pair's later-window co-publication share of the two institutions'
combined output, over the same share in the earlier window) is recentred against `MED`, the
median of that same ratio over every eligible pair (`c1 > 0`, `c2 > 0`, `c1 + c2 ≥ 10`), so
corpus-wide growth over the same years does not read as partnership-specific growth; `MED` is
verified to sit inside a sane [0.8, 1.3] band on the shipped build, at 1.0431
(`app/data/collab_facts.json`; `progress/2BR3_P7.md`, invariant suite). The recentred ratio `rr =
r / MED` classifies up at `rr ≥ 1.25`, down at `rr ≤ 0.80`, else stable; an up or down verdict is
demoted to not significant when a pooled two-proportion z-test on `c1`/`c2` returns `p ≥ 0.05`
(`app/docs/data_contract.yaml`, `collab_pairs.parquet` v2, `mom_class`/`mom_rr`/`mom_p`;
`app/data/collab_facts.json`, `band`/`alpha`). Four further states need no ratio at all: `new`
(`c1 == 0`, `c2 ≥ 5`), `dormant` (`c2 == 0`, `c1 ≥ 5`), `weak` (`0 < c1 < 5`, "weak base", no
percentage shown), and pairs below even that floor carry no momentum reading. On the shipped
build the class distribution is dominated by `weak` and `ns` (1,807,729 and 1,450,358 of
3,581,332 pairs), `stable` a further 185,538, with `up`/`down`/`dormant`/`new` in the tens of
thousands each (`progress/2BR3_P7.md`, invariant suite). Field and topic rows share the pair's
own `d1`/`d2`/`MED` (one drift correction per run) and carry the class label only, no percentage,
shown only where the cell's own `c1 + c2 ≥ 10`. Colour never carries the reading alone: text and
a glyph (↗/↘/→) accompany every state (`lib/palette.py`, `MOMENTUM_COLORS`/`MOMENTUM_GLYPHS`;
WT_2BR3.md task 2.8).

## Strategic reciprocity, read

Ported from `Client Project/Lorraine/Phase 2/Streamlit/pages/9_🔍_Zoom_partenaire.py`, in the
honest both-sides form: for every field the pair has any joint CORE-AR volume in, one axis is
that field's share of one institution's own portfolio and the other axis is the same field's
share of the other institution's own portfolio, both read from `fields.parquet` on the current
tree and basis, never from the joint corpus itself; bubble area is the pair's own joint volume in
that field, from `collab_pair_fields.parquet`'s `vol` (`lib/collab_data.py::reciprocity_frame`).
The chart is symmetric by construction: swapping which institution is "A" swaps the two axes and
leaves every bubble's area unchanged. A bubble on the dotted 45° diagonal marks a field weighted
about equally by both institutions' own portfolios; one off the diagonal marks a field central to
one side and marginal to the other, separating a structural partnership (both sides already
invest in the shared ground) from a volume partnership (joint output is large mainly because one
side is large).

## How colour is used

One colour system runs through every page. An institution keeps one colour for as long as it
stays in a comparison or a pair: three colours from one monochrome navy family (`#192C41`,
`#5A6883`, `#B5C0D4`, darkest first), each with a same-family twin used for value labels and
legend text, kept distinct from the OpenAlex-domain, SDG and ERC palettes and from the
shared-frontier red used for pooled Collaborate charts (`evals/wind_tunnel_2BR3/WT_2BR3.md` task
2; `palette.INSTITUTION_COLORS`, `SHARED_FRONTIER_COLOR`, 2026-08-31). A bar below its own
citation-impact floor is drawn hatched rather than solid or hollow, the same rule across every
chart that carries the floor.

A taxonomy carries its own official colour too: the OpenAlex domain, the ERC panel (mapped to
PE/LS/SH's own vermillion, green and violet) or the Sustainable Development Goal, none of them
chosen by this tool. That colour never fills a bar or a mark that also carries an institution's
colour; it appears on a label or a chip beside a name instead, on the field-breakdown chart's own
field names and the topic tables' subject chips alike, so the two colour systems are always
readable apart (`evals/wind_tunnel_2BR2.md` A1 and A6, coexistence exception).

## International and company co-publication shares

The international share is the part of an institution's eligible works, 2020 to 2024 (the core
window), naming at least one other direct co-authoring institution based in a different country.
The company share is the part naming at least one direct co-authoring institution, the institution
itself included, typed `company`. Both are full counting, denominator = the institution's own
`total_full_2020_2024` (`app/docs/data_contract.yaml`, `index.intl_share`/`index.company_share`,
verified equal to that column exactly on 6 of 6 spot-checked institutions including three
GB/CH/NO/IS journey seeds).

Type, for an institution not already carried by the index or the enriched master, comes from a
direct OpenAlex pull: 74,899 identifiers, resolving 99.81% of them (coverage 99.83% of the
authorship instances that needed one); the source is `index.type` (post gate-rev-6 corrections)
for indexed institutions and OpenAlex's own raw type for the rest, pulled after the type
corrections were applied so the two never disagree on an indexed id (`BUILD_PLAN_2BR.md` §0 A4/A5,
§7 P1 row). The 1 to 2% of identifiers OpenAlex itself could not resolve are recorded as
resolved-unknown and counted as such, never folded into either share as if they were zero (WT A4).

## Reading a change over time

Dynamics compares two multi-year averages rather than one year against another: the mean annual
figure over 2020-2022 against the mean annual figure over 2023-2024, shown as a percentage change
from the first to the second, 2025 excluded from both windows (`app/docs/data_contract.yaml`,
`window_conventions.dynamics_window_1`/`dynamics_window_2`; 2B-R-6). Averaging across each window
absorbs the noise a single year carries and still leaves two periods short enough to read as
before and after. Where the earlier window is empty for an institution, no percentage is shown,
because a change measured against zero has no reading.

A dynamics figure carries a low-volume marker whenever the earlier window's mean annual output, on
the full count, sits under 10 publications a year (`lib.charts_compare.LOW_VOLUME_FLOOR`; 2B-R2-4,
brainstorm Q3): a change read off a handful of publications swings on very little evidence, and the
marker is drawn in the chart and stated in the gutter alike.

## The subject taxonomy and its three versions

Three trees ship: the original OpenAlex taxonomy, a conservative repair (955 corrections, about one
in twenty arguable) and a best-fit repair (1,673 differences, about one in seven arguable, winning
86% of blind A/B tests where the two differ). Release v1.3, copied into
`V3/reference/taxonomy_repair_v1.3/`; `METHODS_FAISCEAU.md` §6.1 and §6.6.

Every topic keeps a subfield under all three trees, so subfield volumes sum to the institution's
total under each (`METHODS_FAISCEAU.md` §6.1). Golden-set accuracy of the repair is 0.975 to 1.000
per domain, and `fit_quality` flags 859 forced or no-fit topics, 15.2% of world mass and 5.2% of
the median institution's mass (`METHODS_FAISCEAU.md` §6.6).

Impact is decided against the world threshold of a work's **original** subfield, so a top-decile
flag is tree-independent and only the roll-up moves with the selected tree (`METHODS_FAISCEAU.md`
§6.4).

## The lenses, one by one

Eight lenses display by default (L0, L1, L3, F1, L2f, L4, L5, L6) and two are one click away (C1,
L7): `app/config.yaml` `lenses`; `INDICATOR_SPEC_v2.md` §1, rulings M5.1 and M5.2.

The Methods page builds this section from `copy.LENS_NAMES`, `copy.LENS_INTRO` and
`copy.LENS_CAVEAT`, the same three dicts the Find tab's lens guide renders, so the wording cannot
drift between the two pages. The per-lens definitions, recall figures and caveats behind those
sentences are in `INDICATOR_SPEC_v2.md` §1.0 to §1.9; the grain-by-method rationale is in
`METHODS_FAISCEAU.md` §3.

Two figures worth carrying into a review of this section: the default-set union recovers 61.9% of
independently graded external peers at depth 20 and 77.9% at depth 50 (`INDICATOR_SPEC_v2.md` §7),
and noise grows with depth at very different rates per lens, from 19.4% non-education rows in
L1's ranks 31 to 50 up to 51.0% for L7 (`INDICATOR_SPEC_v2.md` §1). The depth control stays one
global setting, and that difference is disclosed rather than encoded (§9 ruling 10).

## Reading the lens codes

Refinement 2B-R renumbers the tab a reader sees, left to right in tab order, without touching the
internal identifier the evidence column, the CSV export and the rest of this note still use
(2B-R-11a; `copy.LENS_DISPLAY_CODE`/`copy.LENS_DISPLAY_NAMES`, `progress/2BR_FC.md`).

| Tab code | Name | Internal id |
|---|---|---|
| L0 | Field overlap | L0 |
| L1 | Subfield overlap | L1 |
| L2 | Topic overlap | L3 |
| L3 | Frontier-topic overlap | F1 |
| L4 | Shared specialisations | L2f |
| L5 | ERC panel overlap | L4 |
| L6 | ERC specialisation overlap | L5 |
| L7 | SDG profile overlap | L6 |
| L8 | Core-shape overlap (optional) | C1 |
| L9 | SDG specialisation, experimental (optional) | L7 |

The ★ Aspirational tab, last in the row, carries no code of its own and sits outside this table:
it is not a similarity lens, and does not ask which institutions resemble this one. Its own
question and its two modes are in "The aspirational view" below.

## Concordance

Concordance counts how many lenses place a candidate inside their own top-30
(`app/config.yaml` `concordance_N`; `INDICATOR_SPEC_v2.md` §3, ruling M5.5). Both numbers, the
depth and the count of lenses defined for the seed, are stated on every render
(`app/docs/data_contract.yaml` `concordance_denominator_disclosure`).

It adds nothing the lenses miss: zero unique candidates against the default set at every depth and
population tested, which is why it is displayed as an aid and never as the ranking
(`INDICATOR_SPEC_v2.md` §3, H7). Judged read: 15 sensible, 1 mixed, 0 nonsense over the 16 seeds of
panel v2.

## The aspirational view

The shipped rule keeps L1 candidates whose PP(top10%) interval sits entirely above the seed's, in
L1 order (`evals/aspirational_R2/REPORT.md` §1, variant V0; ruling A in §4, applied as the
default-if-silent at `GATE_2A_MEMO.md` §4.1).

Six definitions were generated for eight seeds and graded 0 to 3 by two fresh-context judges whose
expectations were pre-registered and read only after grading. V0 scored 2.62, tied first with
A-combined; A-frontier 2.50, A-size and A-impact+size 2.38, A-complement 1.50
(`evals/aspirational_R2/REPORT.md` §2). Non-university crowding on V0 is 3%.

V0's two weak spots are structural: it empties for a seed at the top of its pool (ETH Zurich,
Sorbonne on size) and thins to four rows for a narrow small seed (Burgos)
(`evals/aspirational_R2/REPORT.md` §3.1).

2B-R-3 ships the fix: mode B. When V0 is empty for a seed, the view falls back automatically to
A-frontier, the same subfield-lens candidate pool reordered by shared presence in the topics the
world is currently expanding into (ties keeping V0's own order), labelled "ordered by frontier
alignment" rather than left blank (`BUILD_PLAN_2BR.md` §1 2B-R-3; `progress/2BR_FC.md`, wired as
`engine.aspirational_frontier`, verified on the ETH Zurich seed). The tab itself is marked apart
from the similarity lenses with its own star and no lens code (see "Reading the lens codes"
above): it does not ask which institutions resemble this one, it asks which of the subfield
lens's own candidates this institution could plausibly grow into.

## Specialisation, and the floors it is displayed at

The specialisation index is an institution's share of a cell divided by the mean share across the
institutions active in that cell, so a value of 1 is what an average active institution holds
(`app/docs/data_contract.yaml`, `subfields.si`).

Display floors, in fractional publications: solid at 30 or more, hollow between 10 and 30, no mark
below 10 (`lib/profile_data.py` `SI_FLOOR_SOLID` = 30.0, `SI_FLOOR_THIN` = 10.0; ruling L34 in
`GATE_2A_MEMO.md` §2 item 8). The lens floor is separate and unchanged: L2f counts only cells where
both institutions hold at least 30 papers (`app/config.yaml` `l2f_floor`, basis `paper_count`;
`INDICATOR_SPEC_v2.md` §1.4).

Measured effect of the display floor on a small institution: IFPEN's top 30 subfields show two
marks under 30 fractional publications and seventeen under 10 (`GATE_2A_MEMO.md` §2 item 8), which
is why the hollow state exists rather than a single cut.

## Impact: PP10_WD

PP10_WD is the share of an institution's articles and reviews from 2020 to 2024 landing in the
world top decile of citations for their own subfield, year and document type (`DESIGN.md` §4, D6;
`app/docs/data_contract.yaml`, `impact_taxa.parquet`). Thresholds are computed on the world, not on
the European baseline or on the index.

The denominator is the institution's own full count of articles and reviews with a matching world
threshold: each publication counts once toward every institution it names, on full counting only
(`impact_taxa.parquet`, `n_covered_pp`; `pipeline/19_impact_taxa.py`). An earlier release of this
tool read the same figure on fractional counting instead (`index.parquet` `pp_top10_frac`); see
"Which figures follow the counting-basis setting" above for the reconciled cross-check. 2025 is
excluded (`app/config.yaml` `bonus_year`).

Intervals are a 95% bootstrap interval from 1,000 resamples (`app/data/source_manifest.json`
`bootstrap_reps`; `app/config.yaml` `methods_facts.impact_ci_coverage_pct`, read off
`pipeline/agg/impact.py::poisson_bootstrap_ci_vectorized`'s own default two-sided alpha of 0.05,
never overridden at any call site) and are always rendered with the point estimate;
`pp_ci_low <= pp_top10_frac <= pp_ci_high` holds for all 7,557 index rows and all 328,978 impact
cells (verified 2026-08-29, `app/docs/data_contract.yaml`). This paragraph's own coverage
sentence is the copy key `copy.IMPACT_CI_CAPTION`, kept as one template so the Compare page can
show the same wording beside every interval from its own build wave onward, rather than a second
hand-typed caption (2B-R-12).

The earlier two-floor design (30 default, 10 alternate, `impact_cells.floor`) is retired this
round: its floor-30 intersection across several institutions was usually empty (only 3,342 of
7,557 institutions had any floor-30 cell, median 2, and 40 of 40 random four-institution tuples
shared none, `evals/wind_tunnel_2B.md`, absorbed as `BUILD_PLAN_2B.md` §0 A1), which is why a cell
used to read `n/a` below the chosen floor rather than as a low value. `impact_taxa.parquet` now
ships every taxon an institution holds at least one world-benchmarked publication in, at every one
of the four grains (field, subfield, SDG, ERC); a cell resting on very few publications is shown,
not hidden, and marked as a caution instead of excluded (`pipeline/19_impact_taxa.py`, floor
n_covered_pp >= 1).

Two normalised-impact traps are deliberately avoided: `fwci` (a mean of ratios whose world mean is
not 1) and `cited_by_percentile_year` (normalised by year, not by field); SIRIS `CLAUDE.md`,
OpenAlex gotchas, and `DESIGN.md` §4.

## Frontier scores

Frontier scores are the ACCORD artefact, per topic: expansion, acceleration and a composite, with
the quadrant of expansion against acceleration as the primary visual (`DESIGN.md` §4, D2). They
measure attention dynamics rather than novelty or quality, and a low score can mark a foundational
area (same source, UI copy rule).

811 topics carry no score by construction: they are the catch-all topics outside the subject scope
of the taxonomy, and the exclusion list is versioned with a reason code per topic
(`METHODS_FAISCEAU.md` §6.2; verified 2026-08-29 against `app/data/topics_dim.parquet`,
`is_excluded` sums to 811). Their mass is shown, never dropped.

`index.frontier_quadrant_mix` sums to 1 only once the excluded and unscored shares are added
(median 0.967, minimum 0.128; one institution holds three quadrants), which is why the Compare
quadrant bar carries a fifth segment (`BUILD_PLAN_2B.md` §0 A2).

The Compare page's pooled frontier map (2B-R2-10) offers two pool modes. `"volume"`, the default,
keeps every topic flagged `top25pct_frontier` (the global top quartile of `frontier_score_latest`)
that at least one compared institution publishes in, ranked by their combined volume. `"elite"`
keeps only topics in the global top decile of `frontier_score_latest`, cut over all 3,706 scored
topics rather than over the compared institutions' own footprint, so the pool never moves when the
comparison changes (`lib.compare_data.ELITE_FRONTIER_PERCENTILE` = 0.90; WT 2BR2 claim #22). The
elite set is a subset of the volume set by construction, a stricter percentile cut on the same
score.

## The ERC classifier

`SIRIS-Lab/erc-classifiers`, a SPECTER-base multilabel model with a sigmoid head, over the 28 ERC
evaluation panels (`DESIGN.md` §5, D13; 28 panels verified against `app/data/erc.parquet`,
`panel_idx` distinct count). Global threshold tau = 0.5 (`app/config.yaml` `erc_tau`;
`app/data/source_manifest.json` `erc_tau`). No panel above tau leaves the work `erc_unclassified`;
a work clearing several panels is split 1/n across them (`DESIGN.md` §5).

Biotechnology and Arts have recall of about 0.26 in the model's published evaluation and carry an
inline caveat wherever ERC panels are drawn (`DESIGN.md` §5; `copy.FIND["CAPTION_ERC"]`).

The denominator of `erc.share` is the institution's own `erc_classified_mass_frac`, verified exact
(`app/docs/data_contract.yaml`, `erc.share`). Coverage varies widely between institutions:
Université de Strasbourg reads 92.1% of `total_frac`, the remainder being grey mass.

## The SDG classifier

VocTagger route B, 16 independent per-SDG passes on the parse-once engine, VocTagger defaults, any
keyword hit yielding 0 to N goals per document (`DESIGN.md` §5, D8/F1; 16 goals verified against
`app/data/sdg.parquet`, `sdg_idx` distinct count).

**SDG 17 is not covered** and is left out rather than drawn as an empty row (`DESIGN.md` §5). The
denominator of `sdg.share` is the institution's SDG-tagged mass, not its classified or eligible
mass, verified exact (`app/docs/data_contract.yaml`, `sdg.share`); per-institution shares can sum
above 1 (observed maximum 3.52) because a work can carry several goals.

Epistemic label, kept verbatim in the UI: matches reflect the SIRIS classifier's reading of the
SDGs, and different classifiers disagree substantially. Comparison with another provider's SDG
numbers is never invited (`DESIGN.md` §5, hard rule). SDG classification requires an abstract;
title-only works go to grey (`DESIGN.md` §2.3, D12).

SDG mass is measured on a different window from every volume figure elsewhere in the tool: the
six-year snapshot, 2020 to 2025, including the bonus year, rather than the 2020 to 2024 core
window (`app/docs/data_contract.yaml`, `window_conventions.sdg_mass_window`). Summing
`sdg_year.parquet` down to 2020-2024 only recovers a median 84.96% of `sdg.parquet`'s own mass on
the same cells, not all of it (verified 2026-08-30, `app/docs/data_contract.yaml`,
`sdg_year.parquet`); the two windows are named on both sides of every SDG share and are never
meant to be summed together.

The comparison page's field cross reads a different, narrower population again, distinct-tagged
rather than per-goal and matched to the field figures beside it: see "The SDG-tagged share, by
field" below.

## The SDG-tagged share, by field

The comparison page's SDG-share metric reads `sdg_fields.parquet` v2, DISTINCT-tagged at
institution × field × tree grain: a work counts at most once toward a field regardless of how
many Sustainable Development Goals it carries (`app/docs/data_contract.yaml`,
`sdg_fields.parquet`, 2026-08-31 rebuild). Numerator (`mass_any_frac`/`mass_any_full`) and
denominator (`fields.parquet`'s own `vol_frac`/`vol_full`) are read over the identical
population, all document types, 2020 to 2024 (the core window, not the six-year SDG-mass window
above), on the same counting basis the page's toggle selects, so the share is asserted no greater
than 1 plus a float32 tolerance at build time (`lib/compare_data.py::_sdg_share_field_frame`,
`SDG_SHARE_EPS`), verified with 0 violations over 22,668 sampled institution × tree cells
(`progress/2BR3_P7.md`, invariant suite).

## Grey accounting: what happened to every publication

Six exclusive states, whose `mass_*` columns sum to `total_frac` exactly for all 7,557 institutions:
`mass_classified_eligible`, `mass_title_only`, `mass_lang_uncertain`, `mass_untranslated_grey`,
`mass_retracted_excluded`, `mass_unusable` (`app/docs/data_contract.yaml`, index `mass_*` entries;
sum verified in `evals/wind_tunnel_2B.md`, absorbed as `BUILD_PLAN_2B.md` §0 A9). Europe-wide
totals are in `app/data/source_manifest.json` `grey_totals_frac_mass` (classified eligible:
4,618,728.8 fractional publications).

The country by field breakdown planned in `DESIGN.md` §4 was descoped to institution level by user
ruling at gate 2A (`BUILD_PLAN_2A.md` L25). SDG-untagged mass is reported as unknown, never as zero
(`DESIGN.md` §4).

## Corrected institution types

41 type corrections ship (`app/data/overrides/type_overrides.csv`, read live), and none is left
unresolved. 16 come from the gate rev 6 review, including the Netherlands Defence Academy, the
General Jonas Žemaitis Military Academy of Lithuania, Fundación Universitaria Iberoamericana and
Institut Mines-Télécom, four cases a single source could not settle on first pass and which gate
rev 6 itself resolved on 2026-08-28 (`INDICATOR_SPEC_v2.md` §5, ruling M5.8/H13). 18 more come
from the R2 scan (IFPEN, Ifremer, six Inria centres, ONERA, INERIS, CSTB, IRSN, Météo-France,
Santé publique France to `government`; Ikerbasque, DLR e.V., SINTEF to `nonprofit`; IT Carlow to
`education`), listed in `evals/type_scan_R2/TYPE_SCAN.md` and `GATE_2A_MEMO.md` §2 item 1. The
remaining 7 were applied this round by user ruling (2B-R-3, brainstorm Q3, 2026-08-30): CNR Italy,
TNO and VTT to `government`, DZHK, DZNE, DZL and DZIF to `nonprofit`
(`data/overrides/type_overrides.csv`, rows dated 2026-08-30).

Two files describe cases that were once gated and record them as such today: `data/overrides/
type_overrides_GATE.md` still reads "none applied" for the four gate-rev-6 cases above, and
`data/overrides/type_overrides_GATE_R2.md` still reads "none applied" for the seven applied this
round. Both lines predate the ruling that resolved them and are stale; `type_overrides.csv` and
this note are the one source of truth for which institution carries a patched type
(`app/docs/data_contract.yaml`, `type_overrides.stale_reference_note`). 391 university hospitals
matching the HEI name pattern were left as `healthcare` as a category rather than reviewed one by
one (`evals/type_scan_R2/TYPE_SCAN.md`, method section).

An override changes the label and the type post-filter, never a rank and never inclusion;
`type_openalex` is kept for audit and shown on the badge (`INDICATOR_SPEC_v2.md` §5). The regex
rule's own recall is unknown, and the file is a living list the operator extends
(`INDICATOR_SPEC_v2.md` §5, E7 fix-cycle disclosure).

## Which institutions are in the index

7,557 institutions, with the population rule: at least 200 publications over the window and at
least 20 in each of 2023 and 2024 (`app/docs/data_contract.yaml`, index `grain`).

The population is dominated by small specialised institutes and hospitals: median 572 full
publications and median breadth of 1 subfield at the G6 floor, with roughly 21% universities
(`app/docs/data_contract.yaml` `percentile_definition`; `GATE_2A_MEMO.md` §2 item 7). Every tile
positioned against the index carries that caveat (`copy.FIND["BASELINE_HELP"]`), because a median
computed on this population describes the population and is not a level to reach.

## Snapshot and vintage

Snapshot august_2026 (`app/config.yaml` `snapshot`; `app/data/MANIFEST.json` `snapshot`), source
manifest generated 2026-08-27, deployed 2026-08-29 (`MANIFEST.json`). The EU27 harvest is April
2026 vintage with an August 2026 attribution and citation patch, so impact inputs share the August
vintage with the world thresholds; the skew is accepted and stamped (`DESIGN.md` §2.2, D20 and
R1.3).

OpenAlex is a living database, and about 21% of works change their title or abstract text per year
between snapshots (SIRIS `CLAUDE.md`, vintage churn). A deterministic re-run means the same code
against the same archived snapshot, not the same live counts. Link-outs carry the snapshot's own
filters and still drift a little (`copy.FIND["LINK_OPENALEX_HELP"]`).

## What the tool cannot find, and how it was checked

26 external peers of the 16 panel v2 seeds, 8 of them GOLD, are found by no lens at depth 50
despite being the same type and a compatible size: Bologna to Barcelona, Burgos to León, Télécom
Paris to École Polytechnique, Iscte to Sciences Po and CEU, and 21 others
(`INDICATOR_SPEC_v2.md` §8, ruling M5.10; full list in `evals/campaign_v2/recall_v2.md` §10).
National-system and mission peers are not recoverable from output shape alone, which is why every
page keeps a free-text "add a comparator" affordance.

The validation base has a known weakness. Only 46.0% of the earlier round's LLM-pre-registered
peers were confirmed by independent evidence, and only 24.3% of the confirmed external peers had
been pre-registered at all, so the earlier recall figures were measured against a weaker
denominator than the current ones (`INDICATOR_SPEC_v2.md` §8, H12 disclosure, ruling M5.9). The
figures in this note come from the external evidence base. Judged reads are LLM-produced, not
domain-expert-produced, with a second judge only on L0, L5 and L7 (`INDICATOR_SPEC_v2.md` §8).

Candidates for review, not a verdict.

"""
app/lib/copy.py -- every user-facing string in the Find tab (Sprint 2 Phase
2A, Stream F; re-read end to end for a first-time external reader by Stream
R2-C, refinement R2 / L29).

RULE (BUILD_PLAN_2A.md Stream F build step 5 / L10 "no static string asserts
a value"): no digit character appears anywhere in a string constant below
except inside a lens code (L0, L1, L2f, L3, L4, L5, L6, L7, F1, C1) or the
literal "top10" / "PP(top10%)". Every other number a caption needs (a count,
a threshold, a share, a median) is a `{named}` format placeholder the CALLER
fills from CFG or the live data -- never typed here. `scan_for_digit_violations`
at the bottom is the self-check; `tests/test_badges.py` runs it.

VOICE (R2-C, `siris-voice-en`): no em dash and no "--" standing in for one
inside a user-facing string; a comma, a colon or parentheses instead. Plain
words over jargon, because the reader is a strategy officer meeting OpenAlex
for the first time: "histogram intersection", "excess-SI vector" and "HHI"
do not appear in UI copy. Every figure is followed by its reading.
"""
from __future__ import annotations

import re

# ------------------------------------------------- scenario display labels --
# R2 / L29: the sidebar shows a label, the app keeps the internal value. E3
# passes these dicts to `format_func`; the KEYS are the contract and never
# change.

TREE_LABELS = {
    "bestfit": "Repaired taxonomy (best fit, default)",
    "conservative": "Repaired taxonomy (conservative)",
    "original": "OpenAlex taxonomy as published",
}

BASIS_LABELS = {
    "frac": "Fractional counting",
    "full": "Full counting",
}

# ---------------------------------------------------------- lens naming -----
# R2 / L29: the code stays the identifier (Overview chips, evidence column,
# CSV export), the name says what the lens looks at. Tabs carry these labels.

LENS_NAMES = {
    "L0": "L0 · Field overlap",
    "L1": "L1 · Subfield overlap",
    "L3": "L3 · Topic overlap",
    "F1": "F1 · Frontier-topic overlap",
    "L2f": "L2f · Shared specialisations",
    "L4": "L4 · ERC panel overlap",
    "L5": "L5 · ERC specialisation overlap",
    "L6": "L6 · SDG profile overlap",
    "C1": "C1 · Core-shape overlap",
    "L7": "L7 · SDG specialisation (experimental)",
}

# One plain sentence per lens: what "similar" means here, and what the lens
# reads well or badly. Source: INDICATOR_SPEC_v2.md S1. No placeholder, on
# purpose, so the caller renders the sentence as it stands.
LENS_INTRO = {
    "L0": "Similar means the two institutions divide their publications across the broad fields in "
          "much the same proportions; it finds look-alikes quickly, and returns generic matches when "
          "a profile is narrow.",
    "L1": "Similar means the same subfields in the same proportions, one level finer than fields; "
          "this is the reference view of the set, and it stays readable deep into the ranking.",
    "L3": "Similar means the same topics, the finest grain the index carries; it recovers more known "
          "peers than the coarser views, and candidates from the seed's own country come up often.",
    "F1": "Similar means shared presence in the topics the world is currently expanding into, so the "
          "list leans towards where attention is moving; Social Sciences and Humanities profiles are "
          "under-represented.",
    "L2f": "Similar means specialised in the same subfields relative to the average institution, "
           "counting only subfields where both publish enough to judge; it reads well for concentrated "
           "mid-size institutions, and poorly for very diffuse or very thin ones.",
    "L4": "Similar means the same distribution across the ERC evaluation panels, the categories the "
          "European Research Council uses to sort proposals; companies and government bodies "
          "occasionally appear in the list.",
    "L5": "Similar means specialised in the same ERC panels relative to the average; it surfaces peers "
          "the other views miss, with thinner outside corroboration than they have.",
    "L6": "Similar means the same profile of SDG-tagged output across the goals; its candidates come "
          "from other countries readily, so the list is not a country artefact.",
    "C1": "Similar means the same subfields as L1, with the comparison narrowed to the seed's own "
          "strongest subfields, so it reads the core rather than the whole profile; noise grows "
          "quickly past the first ranks.",
    "L7": "Similar means over-represented in the same SDGs relative to the average; the view is "
          "experimental and most of what it returns is noise, with the occasional peer nothing else "
          "finds.",
}

# R2 / L29 (stream R2-E3): the reader-facing reason a lens has nothing to show
# for this seed. `lib/engine/lenses.py` produces its own diagnostic string
# ("seed's excess-SI vector is empty under candidate (f), papers>=30
# (n_eligible_cells=0)") which is a debugging artefact, not copy: it names
# internal structures and types digits this file bans everywhere else. The
# engine keeps it for its own log; the page renders the sentence below.
LENS_UNDEFINED_REASON = {
    "L0": "none of the seed's publications could be placed in a field, so there is no field profile "
          "to compare",
    "L1": "none of the seed's publications could be placed in a subfield, so there is no subfield "
          "profile to compare",
    "L3": "none of the seed's publications could be placed in a topic, so there is no topic profile "
          "to compare",
    "F1": "the seed holds no publications in the topics the world is currently expanding into",
    "L2f": "the seed has no subfield where it publishes enough for a specialisation to be measured",
    "L4": "none of the seed's publications could be placed in an ERC evaluation panel",
    "L5": "the seed has no ERC panel where it publishes enough for a specialisation to be measured",
    "L6": "none of the seed's publications carries an SDG tag, so there is no goal profile to compare",
    "C1": "the seed has no strongest subfields to narrow the comparison to",
    "L7": "the seed has no goal where it publishes enough for a specialisation to be measured",
}

# --------------------------------------------------------- lens glosses -----
# Source: VIZ_SPEC.md S2.4 / INDICATOR_SPEC_v2.md S1, every digit replaced by
# a named placeholder the caller fills from CFG/data. The placeholders these
# two dicts may use are exactly the six keys `_gloss_values()` builds in
# views_find.py: n_fields, n_named_lenses, n_default_lenses, floor_papers,
# core_top_n, depth_max.

LENS_GLOSS = {
    "L0": "Overlap of the publication shares held across the {n_fields} OpenAlex fields, the coarsest "
          "view of a profile",
    "L1": "Overlap of the publication shares held across subfields, the anchor view",
    "L3": "Overlap of the publication shares held across topics, the finest grain the index carries",
    "F1": "Topic overlap restricted to the topics the world is currently expanding into",
    "L2f": "Overlap of specialisations across subfields, counting only cells that hold at least "
           "{floor_papers} papers",
    "L4": "Overlap of the publication shares held across the ERC evaluation panels",
    "L5": "Overlap of specialisations across the ERC evaluation panels",
    "L6": "Overlap of the shares of SDG-tagged output across the goals",
    "C1": "L1 again, with the comparison restricted to the seed's own top-{core_top_n} subfields",
    "L7": "Overlap of specialisations across the SDGs, an experimental view",
}

LENS_CAVEAT = {
    "L0": "Reads as a generic look-alike list when the seed has a narrow profile, and brings in more "
          "non-university rows than the finer views.",
    "L1": "Steady to read down to rank {depth_max}.",
    "L3": "Candidates cluster in the seed's own country more than on the other default views, so the "
          "country filter is worth a look here in particular.",
    "F1": "Under-represents Social Sciences and Humanities profiles.",
    "L2f": "The failure axis is a diffuse profile rather than institution size: it reads well for "
           "concentrated mid-size institutions, poorly for very diffuse or very thin ones.",
    "L4": "Companies and government bodies occasionally leak into the candidate set.",
    "L5": "Kept because it surfaced peers no other view found, with less outside corroboration than "
          "the other defaults; read its candidates with that in mind.",
    "L6": "Country clustering is modest here, so the list is not a country artefact.",
    "C1": "A refinement of L1 rather than a view of its own; noise grows faster than L1's past rank "
          "{core_top_n}.",
    "L7": "Mostly noise, with the occasional peer no other view surfaces.",
}

# ------------------------------------------------------------ toggles -------

L7_TOGGLE_LABEL = ("Show the experimental SDG-specialisation view (mostly noise, with the occasional "
                   "peer no other lens finds)")
C1_TOGGLE_LABEL = "Restrict to my core subfields"
VERDICT_LINE = "Candidates for review, not a verdict."

# ------------------------------------------------------------ tooltips ------

BASIS_NOT_APPLIED_TOOLTIP = ("The ERC and SDG lenses (L4, L5, L6, L7) are built on fractional counting "
                             "alone, so this setting leaves them unchanged.")
L3_COUNTRY_TOOLTIP = ("Of this lens's top candidates, {share} share the seed's country, the highest "
                      "figure among the default lenses; the country filter is worth a look here in "
                      "particular.")
UMBRELLA_BADGE_LABEL = "umbrella / aggregate (EXPERIMENTAL)"
UMBRELLA_TOOLTIP = ("EXPERIMENTAL: this institution publishes far more than the {median} median for "
                    "its country and type, which usually means the record covers a group of "
                    "institutions rather than one. The list of known umbrellas is not exhaustive.")
CATCHALL_TOOLTIP = ("Catch-all topics sit outside the subject scope of the taxonomy. Share of this "
                    "institution's publications that sit in them: {share}.")

# --------------------------------------------------------------- strip ------

STRIP_PREFIX = "Filtered by: "
STRIP_JOIN = " · "  # middle dot, VIZ_SPEC S1.4's own separator
STRIP_TREE = "taxonomy: {tree}"
STRIP_BASIS_FULL = "full counting (the ERC and SDG lenses stay fractional)"
STRIP_DEPTH = "depth = {depth} rows shown per lens"
STRIP_C1_ON = "core-shape restriction on (L1 limited to the seed's own core subfields)"
STRIP_L7_ON = "experimental SDG-specialisation view on"
STRIP_TYPE = "type: {types}"
STRIP_COUNTRY = "country: {countries}"
STRIP_EXCLUDE_OWN_COUNTRY = "the seed's own country excluded"
STRIP_SIZE_RANGE = "size between {lo}-{hi} publications"
STRIP_SCALE_GUARD = "scale guard on"
STRIP_FAMILY = "family filter on (L0 field overlap at or above {threshold})"

# --------------------------------------------------------- empty states -----

SEARCH_EMPTY_TEMPLATE = "No institution matches '{query}'. Check the spelling, or try an acronym."
EMPTY_STATE_JOIN = " and "
NO_ACTIVE_FILTER_LABEL = "the active filters"
EMPTY_STATE_TEMPLATE = ("No candidate matches {filters} for {seed}. Remove a filter, or show more rows "
                        "per lens.")
UNDEFINED_LENS_TEMPLATE = "{lens} cannot be computed for this seed: {reason}."
CONCORDANCE_CAPTION = "Placed in the top-{N} by {k} of the {n} lenses defined for this seed."

# ----------------------------------------------------------- depth/export ---

DEPTH_CAPTION_TEMPLATE = ("showing the top {n} of {m} ranked candidates; search the tail below, or "
                          "download the full ranking")
EXPORT_BUTTON_LABEL = "Download full ranking (CSV)"
TAIL_SEARCH_EMPTY_TEMPLATE = "'{query}' does not appear anywhere in this lens's ranking for this seed."
ADD_COMPARATOR_HELP = "Add a comparator by name"

# ---- Find page (moved from lib/views_find.py EXTRA_COPY, Stream X1 2026-08-29) ----

FIND = {
    # ---- sidebar: counting and taxonomy (R2 / L29) -----------------------
    "SCENARIO_HEADER": "Counting & taxonomy",
    "TREE_LABEL": "Subject taxonomy",
    "TREE_HELP": ("OpenAlex files every publication under a topic, and every topic under a subfield "
                  "and a field; a measurable share of those subfield placements is wrong, and the two "
                  "repaired versions of the taxonomy correct them, the best-fit one more thoroughly "
                  "than the conservative one. Changing this setting moves publications between "
                  "subfields and fields, so the profile charts and the subfield lenses (L0, L1, L2f, "
                  "C1) shift with it, while the topic, ERC and SDG views stay as they are."),
    "BASIS_LABEL": "Counting basis",
    "BASIS_HELP": ("Fractional counting credits an institution the author share it holds on a "
                   "publication, so a paper written with many partners counts for a fraction; full "
                   "counting credits the whole publication to every institution named on it, which "
                   "raises the totals of institutions that co-publish widely. The ERC and SDG lenses "
                   "(L4, L5, L6, L7) are fractional-only and do not change with this setting."),
    "DEPTH_HEADER": "Depth",
    "DEPTH_LABEL": "Rows shown per lens",
    "OPTIONAL_HEADER": "Optional lenses",
    "L7_HEADER": "Experimental view",
    "FILTERS_HEADER": "Post-filters",
    "FILTERS_HELP": "Applied after ranking: they remove rows, they never change a rank.",
    "TYPE_LABEL": "Institution type",
    "COUNTRY_LABEL": "Country",
    "EXCLUDE_OWN_LABEL": "Exclude the seed's own country",
    "SIZE_LABEL": "Size range (full counting)",
    "SCALE_GUARD_LABEL": "Scale guard (comparable size band)",
    "SCALE_GUARD_HELP": ("Keeps candidates within a size ratio of the seed; the ratio is banded "
                         "by the seed's own size."),
    "FAMILY_LABEL": "Family filter (field overlap)",
    "FAMILY_HELP": "Keeps candidates whose L0 field overlap with the seed is at or above {threshold}.",
    "BASKET_HEADER": "Basket",
    "BASKET_EMPTY": "No comparator added yet. Use the add button under any table.",
    "BASKET_CLEAR": "Clear basket",
    "BASKET_REMOVE": "Remove",
    "ADD_COMPARATOR_LABEL": "Add a comparator not found above",
    "ADD_COMPARATOR_PICK": "Matching institutions",
    "ADD_COMPARATOR_BUTTON": "Add to basket",
    "PAGE_TITLE": "Find",
    "PAGE_INTRO": "Search for an institution, then read who resembles it across independent lenses.",
    "SNAPSHOT_CAPTION": ("Snapshot: {snapshot} (generated {generated_at}) {sep} {n_institutions} "
                         "institutions in the index."),
    "SEED_SEARCH_LABEL": "Institution name, acronym or alternative name",
    "SEED_PICK_LABEL": "Matching institutions",
    "SEED_PROMPT": "Type an institution name above to load its benchmark.",

    # ---- what a publication is (R2 / L29; every clause verified against
    # pipeline/01b_harvest_eu27_aug.py l.10-14, app/config.yaml l.42-43,
    # pipeline/agg/attribution.py l.1-16 and pipeline/agg/enriched_corpus.py
    # `classify_grey_state` l.792-798 -- citations in progress/R2_C.md).
    "PUBLICATIONS_LINK_LABEL": "What counts as a publication",
    "PUBLICATIONS_TOOLTIP": (
        "A publication here is an OpenAlex record of type article, review, book, book chapter or "
        "letter, carrying a DOI and published between {y0} and {y1}. {bonus_year} is harvested as a "
        "bonus year and reported for volumes only, never in the impact indicators. A record counts "
        "for an institution when that institution is named on the record itself: full counting "
        "credits the whole publication to each institution named, fractional counting credits the "
        "author share it holds. Retracted records are counted in the totals and left out of the "
        "subject classification, so the subfield, topic, ERC and SDG panels rest on a slightly "
        "smaller set than the size tiles."),

    # ---- legacy seed card, superseded by the profile tiles below ---------
    "CARD_SIZE_FULL": "Size (full counting)",
    "CARD_SIZE_FRAC": "Size (fractional counting)",
    "CARD_HHI": "Concentration",
    "CARD_BREADTH": "Breadth (subfields)",
    "CARD_DENOM_CAPTION": ("Publications from {y0} to {y1}. Full counting credits a whole publication "
                           "to the institution; fractional counting credits its author share. "
                           "Concentration is the subfield concentration index ({hhi_value}); breadth "
                           "is the number of subfields present."),
    "CARD_TOP_FIELDS": "Top fields",
    "CARD_TOP_SUBFIELDS": "Top subfields",
    "CARD_EVIDENCE": "Coverage evidence for this seed",
    "EV_L2F": ("L2f compares specialisations only in subfields where both institutions publish enough "
               "to judge: {value} of this institution's subfields qualify."),
    "EV_SDG": "SDG-tagged share of publications: {value}",
    "EV_ERC": "ERC-classified share of fractional publications: {value}",
    "EV_FRONTIER": "Frontier top-quartile share: {value}",
    "EV_CATCHALL": "Share of publications in catch-all topics, outside the subject scope: {value}",
    "CARD_PP": "PP(top10%): {pp} [{lo}{dash}{hi}]",
    "CARD_PP_CAPTION": ("Share of the institution's fractional output in the world top decile of its "
                        "own citation distribution, with its bootstrap interval, never the point "
                        "estimate alone."),
    "LINK_OPENALEX": "OpenAlex publications",
    "LINK_ROR": "ROR",
    "LINK_HOMEPAGE": "Homepage",
    "TAB_OVERVIEW": "Overview",
    "TAB_ASPIRATIONAL": "Aspirational",
    "OVERVIEW_INTRO": ("Candidates that several independent lenses agree on. Order here is agreement, "
                       "not a score."),
    "CONCORDANCE_EMPTY": ("No candidate is found by more than one of the lenses defined for this seed. "
                          "Open the single-lens tabs instead."),
    "BASIS_DISCLOSURE": "This lens is fractional-only: the counting-basis setting does not change it.",
    "EVIDENCE_LABEL": "Evidence for this seed {sep} {text}",
    "EV_NONE": "No lens-specific evidence line for this seed.",
    "ADD_SELECTED": "Add selected rows to basket",
    "ADD_SELECTED_NONE": "Select rows in the table above, then use this button.",
    "TAIL_SEARCH_LABEL": "Search the full ranking (beyond the rows shown)",
    "TAIL_CAPTION": "Matches anywhere in this lens's ranking, with their original rank.",
    "POP_CAPTION": "Ranked against {n_pop} institutions in the index, the seed excluded.",
    "ASP_INTRO": ("Candidates already found by L1 whose impact interval sits entirely above the "
                  "seed's. Kept in L1-overlap order."),
    "ASP_SORT_LABEL": "Sort by PP(top10%) instead of L1 overlap",
    "ASP_EMPTY": "No L1 candidate's impact interval sits fully above {seed}'s in the pool.",
    "ASP_UNDEFINED": ("The aspirational view needs a defined L1 ranking and a PP(top10%) value with an "
                      "interval for the seed; one of them is missing here."),
    "ASP_CAPTION": ("{n_rows} candidates clear the interval test, out of {n_pool} in the L1 pool "
                    "considered."),
    "COL_RANK": "Rank",
    "COL_INSTITUTION": "Institution",
    "COL_WORKS": "OpenAlex publications",
    "COL_COUNTRY": "Country",
    "COL_TYPE": "Type",
    "COL_SIZE": "Size (full)",
    "COL_PP": "PP(top10%)",
    "COL_CI": "Interval",
    "COL_L1": "L1 overlap",

    # ---- Refinement R1 (gate-2A feedback, BUILD_PLAN_2A.md S9.2) ----------

    # L22: shared table columns -- both size bases, and the lens-specific
    # evidence cell (replaces the old "Top field" line: L22/#7, "top field"
    # only ever fit L1). Names are the contract stream R-E2 looks up.
    "COL_SIZE_FULL": "Size (full)",
    "COL_SIZE_FRAC": "Size (fractional)",
    "COL_EVIDENCE": "Evidence",

    # L16: the controls row (depth / C1 / L7 / post-filters), moved out of
    # the sidebar to sit with the benchmark tables it controls (feedback #1).
    "CONTROLS_HEADER": "Benchmark controls",
    "DEPTH_HELP": ("Sets how many rows are shown per lens. A display cutoff only: the full ranking is "
                   "always computed, and can be downloaded whatever this is set to."),
    "C1_HELP": ("Restricts the anchor lens (L1) to the seed's own top-{core_top_n} subfields, "
                "for a tighter reading of its core specialisation."),
    "L7_HELP": ("An experimental view, off by default: most of what it surfaces is noise, "
                "with an occasional peer no other lens finds."),
    "POSTFILTERS_EXPANDER": "Post-filters (applied after ranking)",

    # ---- the lens guide (R2 / L29) ---------------------------------------
    "LENS_INTRO_HEADER": "How to read the lenses",
    "LENS_INTRO_LEAD": ("Each lens compares two institutions in a different way, so a candidate can "
                        "rank high on one and be absent from another; the codes are stable "
                        "identifiers, reused in the Overview, in the evidence column and in the "
                        "downloads. Concordance counts the lenses that agree on a candidate, a "
                        "measure of agreement rather than a score."),
    "LENS_LEGEND_CAPTION": ("Codes name the lenses that place a candidate in their top-{N}; see the "
                            "lens guide above."),

    # L17/L18: the profile section that replaces the old seed card.
    "PROFILE_HEADER": "Profile",
    "TILES_HEADER": "Key figures",
    "TILE_SIZE_FULL": "Size (full)",
    "TILE_SIZE_FULL_SUB": "publications {y0}{dash}{y1}, whole publication credited",
    "TILE_SIZE_FRAC": "Size (fractional)",
    "TILE_SIZE_FRAC_SUB": "author-share credited",
    "TILE_HHI": "Concentration",
    "TILE_HHI_SUB": "subfield concentration index; higher means more concentrated",
    "TILE_BREADTH": "Breadth",
    "TILE_BREADTH_SUB": "subfields with at least {floor} fractional publications",
    "TILE_SDG": "SDG-tagged share",
    "TILE_SDG_SUB": "of SDG-eligible publications, any keyword hit",
    "TILE_FRONTIER": "Frontier top-quartile share",
    "TILE_FRONTIER_SUB": "of frontier-scorable output",
    "TILE_PP": "PP(top10%)",
    "TILE_PP_SUB": "[{lo}{dash}{hi}] bootstrap interval, articles and reviews",
    "TILE_BONUS_YEAR": "Publications in {year} (bonus year)",
    "TILE_BONUS_YEAR_SUB": "volume only, left out of the impact indicators",

    # ---- R2 / L31: every tile positioned against the index ---------------
    "TILE_BASELINE_SUB": "index median {median} {sep} higher than {pct} of institutions",
    "BASELINE_HELP": ("The reference is the whole index, which is made up mostly of universities, so "
                      "the median describes what that population does rather than a level to reach. "
                      "A value under it places the institution within the population, and says "
                      "nothing on its own about how well it performs."),

    "COVERAGE_LINE": ("ERC-classified share {erc} {sep} SDG-tagged share {sdg} {sep} "
                      "catch-all share {catchall} {sep} L2f-eligible subfields {l2f}"),
    "WORDCLOUD_CAPTION": ("Subfields {sep} size = publications on the current counting basis, "
                          "colour = domain"),

    # Yearly breakdown pair (L17 block 4): one segmented control swaps the
    # global + per-year charts between a domain view and a document-type view.
    "BREAKDOWN_CONTROL_LABEL": "Break down by",
    "BREAKDOWN_DOMAIN": "Domain",
    "BREAKDOWN_DOCTYPE": "Document type",
    "BREAKDOWN_GLOBAL_TITLE": "Overall breakdown",
    "BREAKDOWN_YEARLY_TITLE": "Yearly breakdown",
    "BONUS_YEAR_CAPTION": "{year} is a bonus year: volume only, left out of the impact indicators",

    # L17 block 5: the six collapsed chart panels.
    "PANEL_FIELDS": "Fields",
    "PANEL_SUBFIELDS": "Top {n} subfields",
    "PANEL_TOPICS": "Top topics",
    "PANEL_FRONTIER": "Frontier positioning",
    "PANEL_SDG": "SDG profile",
    "PANEL_ERC": "ERC profile",

    # L20: the shared sort toggle every bar-chart panel carries.
    "SORT_LABEL": "Sort by",
    "SORT_VOLUME": "Volume / share",
    "SORT_TAXONOMY": "Taxonomy order",

    # ---- R2 / L33: the frontier panel's two modes ------------------------
    "FRONTIER_MODE_LABEL": "Topics shown",
    "FRONTIER_MODE_TOP": "Top {n} topics by volume",
    "FRONTIER_MODE_EMERGING": "All topics in the global top quartile of emergence",

    # L20 panel captions.
    "CAPTION_SI": ("SI = the institution's share of a cell divided by the mean share across the "
                   "institutions active in it, so the dashed line marks what an average institution "
                   "holds"),
    "CAPTION_SI_FLOOR": ("Solid marks: at least {floor_solid} fractional publications in the cell. "
                         "Hollow marks: between {floor_thin} and {floor_solid}. Below {floor_thin}, "
                         "no mark at all. The similarity lenses keep their own {floor_solid} rule."),
    "CAPTION_TOPICS_CATCHALL": ("{n} of the topics shown are catch-all topics, outside the subject "
                                "scope, flagged {glyph}; catch-all topics hold {catchall} of this "
                                "institution's publications."),
    "CAPTION_FRONTIER": ("{n_shown} topics are placed here, and {n_excluded} are excluded or carry no "
                         "frontier score. Frontier scores measure attention dynamics rather than "
                         "novelty or quality: a low score can mark a foundational area."),
    "CAPTION_SDG": ("Shares of SDG-tagged output; a publication can carry several SDGs, so the shares "
                    "need not sum to one. SDG {n_missing} is not covered. Matches reflect the "
                    "SIRIS classifier's reading of the SDGs, and different classifiers disagree "
                    "substantially."),
    "CAPTION_ERC": ("Shares of ERC-classified output over {n_panels} panels, covering {erc_share} of "
                    "this institution's publications; the Biotechnology and Arts panels have low "
                    "recall, so read those two with care."),
    "FRACTIONAL_ONLY_PANEL": ("This panel is fractional-only: the counting-basis setting does not "
                              "change it"),

    # ---- Refinement R1, added by stream R-E2 (the page that composes the
    # above). Additive only: every key below is a string R-F2's set did not
    # carry and the composed page needs (BUILD_PLAN_2A.md S9.3 R-E2 fence).

    # The benchmark half of the page -- the section the controls row heads.
    "BENCHMARK_HEADER": "Benchmark",
    "BENCHMARK_INTRO": ("Candidate peers, ranked by each lens independently. The controls "
                        "below govern every tab."),

    # L23 / gate-2A bug #9: the publications link carries the harvest's own
    # server-side filters, so it counts the same corpus the app does, give or
    # take the drift between a live query and a frozen snapshot.
    "LINK_OPENALEX_HELP": ("Live OpenAlex count with the same filters as the snapshot; "
                           "expect a small difference"),

    # The yearly breakdown's residual series: publications the topic table
    # cannot place in a domain (they carry no primary topic). Shown, never
    # hidden, so the domain and document-type views sum to the same total.
    "UNCLASSIFIED_LABEL": "Unclassified",
    "BREAKDOWN_DOCTYPE_MISSING": ("No document-type rows for this institution in the "
                                  "snapshot; showing the domain breakdown instead."),

    # Empty states for the profile section's own blocks (VIZ_SPEC S1.6: an
    # explicit reason, never a blank panel and never a silent gap).
    "WORDCLOUD_EMPTY": "No subfield mass for this institution under the current settings.",
    "PANEL_EMPTY": "No data for this panel under the current settings.",
    "FRONTIER_EMPTY": ("No topic of this institution carries a frontier score, so there is "
                       "nothing to place on the two axes."),

    # The displayed cut of the two "top N" panels, stated parametrically
    # (VIZ_SPEC S2.16: "the depth of the cut is stated in the panel caption").
    "CAPTION_TOP_N_VOLUME": ("Showing the top {n} subfields by publications on the current counting "
                             "basis; the CSV export carries every subfield."),
    "CAPTION_TOP_N_SHARE": ("Showing the top {n} topics by share of output; the CSV export "
                            "carries every topic."),
}

# ----------------------------------------------------- digit-ban self-check -

_ALLOWLIST_RE = re.compile(
    r"\bL0\b|\bL1\b|\bL2f\b|\bL3\b|\bL4\b|\bL5\b|\bL6\b|\bL7\b|\bF1\b|\bC1\b|top10|PP\(top10%\)"
)
# A `{named}` format placeholder is never rendered literally -- the RULE at
# the top of this file exempts it explicitly -- so a digit inside the
# placeholder's own name (e.g. the FIND section's "{y0}"/"{y1}") is not a
# digit-ban violation. Stripped before the scan below, same as this file's
# independent reimplementation in tests/test_narrative.py's
# `has_digit_violation` (kept in sync with that stripping behaviour, not with
# its literal regex source).
_PLACEHOLDER_RE = re.compile(r"\{[^{}]*\}")


def scan_for_digit_violations() -> list[tuple[str, str]]:
    """Every string constant above (dict values included), digits allowed only
    inside the allowlisted lens codes / top10 / PP(top10%) / a `{placeholder}`.
    Returns (constant_name, offending_value) pairs; empty list = PASS."""
    violations = []
    for name, value in globals().items():
        if name.startswith("_") or not name.isupper():
            continue
        candidates = value.values() if isinstance(value, dict) else [value]
        for v in candidates:
            if not isinstance(v, str):
                continue
            cleaned = _PLACEHOLDER_RE.sub("", _ALLOWLIST_RE.sub("", v))
            if re.search(r"\d", cleaned):
                violations.append((name, v))
    return violations


if __name__ == "__main__":
    import sys

    bad = scan_for_digit_violations()
    if bad:
        print("DIGIT-BAN FAILURES:")
        for name, v in bad:
            print(f"  {name}: {v!r}")
        sys.exit(1)
    print("copy.py digit scan: PASS")

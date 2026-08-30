"""
app/lib/copy.py -- every user-facing string in the Find tab (Sprint 2 Phase
2A, Stream F; re-read end to end for a first-time external reader by Stream
R2-C, refinement R2 / L29).

RULE (BUILD_PLAN_2A.md Stream F build step 5 / L10 "no static string asserts
a value"): no digit character appears anywhere in a string constant below
except inside a lens code (L0, L1, L2, L2f, L3, L4, L5, L6, L7, L8, L9, F1,
C1 -- L2/L8/L9 are the 2B-R-11a DISPLAY codes the renumbered defaults and the
two optional lenses need, added to the allowlist alongside the pre-existing
ten) or the literal "top10" / "PP(top10%)". Every other number a caption needs
(a count,
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
    "BASKET_COUNT": "{n} of {cap} added",
    "BASKET_FULL": ("The basket already holds the most institutions Compare can show at "
                     "once ({cap}). Remove one before adding another."),
    "BASKET_CLEAR": "Clear basket",
    "BASKET_REMOVE": "Remove",
    "ADD_COMPARATOR_LABEL": "Add a comparator not found above",
    "ADD_COMPARATOR_PICK": "Matching institutions",
    "ADD_COMPARATOR_BUTTON": "Add to basket",
    "PAGE_TITLE": "Find",
    "PAGE_INTRO": "Search for an institution, then read who resembles it across independent lenses.",
    # 2B-R-12 / A14: the verbose "Snapshot: <label> (generated <timestamp>)"
    # stamp is GONE from every page. The key and its four call-site keywords
    # (`snapshot`, `generated_at`, `n_institutions`, `sep`) are kept exactly as
    # they were -- `str.format` ignores the keywords a template stops using --
    # so the four callers (Find, Compare, Collaborate, Methods) drop the string
    # without any of their files being edited. Find and Menu use the richer
    # DATA_CAPTION below; the Methods page keeps its factual provenance in its
    # own METHODS["snapshot"] section, which is where a vintage belongs.
    "SNAPSHOT_CAPTION": "{n_institutions} institutions in the index.",
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
    "EV_ERC": "Share of the seed's fractional publications that carry an ERC panel: {value}",  # manager reword 2026-08-29: must not share the retired coverage line's prefix (probe/test check)
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

    # ======================================================================
    # Sprint 2 Phase 2B-R, stream FA (2B-R-1 / 2B-R-2 / 2B-R-12). ADDITIVE
    # ONLY: every key below is new. The eight-tile keys above are left in
    # place -- lib/views_compare.py still reads BONUS_YEAR_CAPTION, and a
    # deleted key is a crash in another stream's file, not a cleanup.
    # ======================================================================

    # 2B-R-12: the results list no longer auto-loads its best match. The
    # placeholder is what the reader sees until they pick deliberately.
    "SEED_PICK_PLACEHOLDER": "Choose one of these institutions",

    # 2B-R-2: FOUR cards replace the eight tiles. Each shows one big value,
    # the index-baseline line (TILE_BASELINE_SUB above), and carries ALL of
    # its methodology in its own `?` tooltip -- the sublines that used to
    # print a definition under every tile are gone from the page surface.
    "KPI_PUBS_LABEL": "Publications",
    "KPI_PUBS_FRAC_LABEL": "on fractional counting",
    "KPI_PUBS_HELP": (
        "Publications from {y0} to {y1}. The large figure is full counting, which credits the "
        "whole publication to every institution named on it; the second figure is fractional "
        "counting, which credits only the author share the institution holds. {bonus_year} is "
        "harvested as a bonus year, reported for volumes only and left out of every impact "
        "indicator. The index position under the card is computed on full counting."),
    "KPI_SDG_LABEL": "SDG-tagged share",
    "KPI_SDG_HELP": (
        "Share of the institution's SDG-eligible fractional mass that carries at least one hit "
        "from the SDG keyword vocabulary. Eligibility excludes records the classifier cannot "
        "read (no usable text, or an untranslated language); the SDG panel below names the goals "
        "the vocabulary does not cover, which are missing from every institution alike."),
    "KPI_FRONTIER_LABEL": "Frontier top-quartile share",
    "KPI_FRONTIER_HELP": (
        "Share of the institution's frontier-scorable output sitting in topics that fall in the "
        "global top quartile of emergence. A topic that carries no frontier score is left out of "
        "both the numerator and the denominator, so this is a share of what can be scored, never "
        "a share of everything published."),
    "KPI_PP_LABEL": "PP(top10%)",
    "KPI_PP_VALUE_CI": "[{lo}{dash}{hi}]",
    "KPI_PP_CI_LABEL": "bootstrap interval",
    "KPI_PP_HELP": (
        "Share of the institution's fractional output that sits in the world top decile of its "
        "own citation distribution. The bootstrap interval is shown with the value and never "
        "dropped for the point estimate alone: two institutions whose intervals overlap are not "
        "separated by this measure. Articles and reviews only; the bonus year is excluded."),

    # 2B-R-7: two identity-column facts. The columns land on index.parquet
    # later this phase (stream P2); until they do, both read n/a -- never 0.
    "IDENTITY_INTL_LABEL": "International co-publications",
    "IDENTITY_COMPANY_LABEL": "with a company",
    "IDENTITY_FACTS_HELP": (
        "Share of the institution's publications from {y0} to {y1}, full counting, carrying at "
        "least one other institution named directly on the record: based in another country for "
        "the first figure, typed as a company for the second. Both read n/a until the "
        "co-publication tables ship."),

    # 2B-R-1 / A15: what the cloud encodes, and the one thing a reader has to
    # know before comparing two renders of it.
    "WORDCLOUD_HELP": (
        "Word size is the subfield's publications on the current counting basis and word colour "
        "is its OpenAlex domain. Fractional counting up-weights few-author subfields, social "
        "sciences and humanities in particular, so the two bases render at different scales: "
        "compare positions within one basis, never sizes across the two."),

    # 2B-R-2: the breakdown pair gets a section title carrying the bonus-year
    # footnote in its tooltip; the standalone banner under the pair is gone and
    # the control's own "Break down by" label is collapsed.
    "BREAKDOWN_SECTION_TITLE": "Publication breakdown",
    "BREAKDOWN_SECTION_HELP": (
        "Both figures read the counting basis chosen in the sidebar and split the same total: "
        "one shows it over the whole window, the other year by year. {year}{star} is a bonus "
        "year, marked with a star on the year axis: it is reported for volumes only and left out "
        "of every impact indicator."),

    # 2B-R-12: what replaces the snapshot stamp on Find and on the menu.
    "DATA_CAPTION": "{n_institutions} institutions {sep} data from {date}",

    # ======================================================================
    # Sprint 2 Phase 2B-R, stream FC (2B-R-3 / 2B-R-11 / 2B-R-13 handoff).
    # ADDITIVE ONLY, save the three narrow in-place edits the deliverable
    # itself requires and that no other stream reads (noted at each one):
    # TAB_ASPIRATIONAL gains its star, FRONTIER_MODE_TOP drops the {n} the
    # slider below replaces, CAPTION_FRONTIER's wording follows suit (catch-
    # all topics are no longer pre-excluded from the cut it describes).
    # ======================================================================

    # 2B-R-3 mode B: the aspirational tab's own framing line, ahead of
    # ASP_INTRO, and the one-line notice a V0-empty seed's fallback carries.
    "ASP_FRAME_INTRO": ("A different exercise from the lenses above: identifying institutions worth "
                        "aspiring to, not institutions that merely resemble this one."),
    "ASP_FRONTIER_FALLBACK": ("No candidate in this institution's look-alike pool clears its impact "
                              "interval, so the list below is ordered by frontier alignment instead: "
                              "shared presence in the topics the world is currently expanding into."),
    "COL_F1": "Frontier alignment",

    # 2B-R-13 handoff (FB): the frontier panel's new top-N slider and the
    # coverage caption templated from `charts.frontier_coverage`'s numbers.
    "FRONTIER_TOPN_LABEL": "Maximum topics plotted",
    "CAPTION_FRONTIER_COVERAGE": (
        "Catch-all topics are counted in this cut like any other topic: {n_catchall} of the topics "
        "shown are catch-all, flagged {glyph}. This cut leaves out {pct_not_shown} of the placeable "
        "mass; the smallest topic shown holds {min_mass} publications on the current counting basis."),

    # 2B-R-11a: DISPLAY lens codes, renumbered L0..L7 in TAB ORDER (the eight
    # defaults) plus L8 (C1) and L9 (L7, the experimental/noise lens) for the
    # two optional tabs -- the codes a reader actually sees on a tab, in the
    # guide, in the concordance chips and in the cross-lens "rank under"
    # reference. Internal engine ids (`lib.engine.ALL_LENSES` and everything
    # keyed on them: CSV exports, `evidence_text`, `rank_under_other_lenses`,
    # ctx dict keys) are UNCHANGED -- LENS_DISPLAY_CODE is the ONE table that
    # translates one into the other, keyed by the internal id it is looked up
    # with. `docs/METHODS_NOTE.md`'s own concordance table (stream MU, next
    # wave) reads this same dict rather than a second copy of the mapping.
    #
    # LENS_DISPLAY_NAMES is LENS_NAMES' sentence, with the NEW code substituted
    # for the old one -- the full name + one-line intro a tab body now opens
    # on (A11: the tab itself carries only the bare code). The OLD LENS_NAMES/
    # LENS_INTRO/LENS_CAVEAT dicts above are untouched: the Methods page still
    # reads them as they stand until stream MU's own wave retires the old
    # numbering there too (BUILD_PLAN_2BR.md S3 FC row).
    "LENS_DISPLAY_CODE": {
        "L0": "L0", "L1": "L1", "L3": "L2", "F1": "L3", "L2f": "L4",
        "L4": "L5", "L5": "L6", "L6": "L7", "C1": "L8", "L7": "L9",
    },
    "LENS_DISPLAY_NAMES": {
        "L0": "L0 · Field overlap",
        "L1": "L1 · Subfield overlap",
        "L3": "L2 · Topic overlap",
        "F1": "L3 · Frontier-topic overlap",
        "L2f": "L4 · Shared specialisations",
        "L4": "L5 · ERC panel overlap",
        "L5": "L6 · ERC specialisation overlap",
        "L6": "L7 · SDG profile overlap",
        "C1": "L8 · Core-shape overlap",
        "L7": "L9 · SDG specialisation (experimental)",
    },
}

# 2B-R-11a: the two dicts above, hoisted to module level so `lib/ranked.py`
# (which has no reason to import the whole FIND dict) and any other caller can
# read `copy.LENS_DISPLAY_CODE` directly, exactly like the pre-existing
# `copy.LENS_NAMES` at module level above.
LENS_DISPLAY_CODE = FIND["LENS_DISPLAY_CODE"]
LENS_DISPLAY_NAMES = FIND["LENS_DISPLAY_NAMES"]

# In-place edits the 2B-R-13/2B-R-3/A11 wiring requires (narrow, noted above):
FIND["TAB_ASPIRATIONAL"] = "★ " + FIND["TAB_ASPIRATIONAL"]           # "★ Aspirational"
FIND["FRONTIER_MODE_TOP"] = "Top topics by volume"                        # the slider now states n
FIND["CAPTION_FRONTIER"] = (
    "{n_shown} topics are placed here; {n_excluded} carry no frontier score and cannot be placed. "
    "Frontier scores measure attention dynamics rather than novelty or quality: a low score can mark "
    "a foundational area.")

# ==========================================================================
# Sprint 2 Phase 2B, Stream N: the narrative wrapper (NAV), the Compare page
# (COMPARE), the Collaborate page (COLLAB) and the Methods page (METHODS +
# METHODS_SOURCES). Same RULE and same VOICE as everything above: no digit
# outside an allowlisted token or a `{placeholder}`, no em dash and no "--"
# standing in for one, and no engine vocabulary (the words an engineer uses
# for the machinery, in place of the words a strategy officer uses for the
# question). Sources are cited section by section in `docs/METHODS_NOTE.md`,
# which carries the same text with the numbers written out; the app never
# renders that file (BUILD_PLAN_2B.md A5).
# ==========================================================================

# ------------------------------------------------------- nav + Menu cards --
# 2B-10: four pages, in the order a reader walks them. The label is what the
# sidebar shows, the blurb is what the Menu card says, the lead is the one
# sentence the page opens on (the question it answers).

NAV = {
    "MENU_HEADER": "BenchUp",
    "MENU_INTRO": ("Four pages, in the order most readings take: find institutions that resemble "
                   "yours, put a handful of them side by side, look at one pair in detail, and read "
                   "how every figure on the way was built."),

    "FIND_LABEL": "Find peers",
    "FIND_BLURB": ("Start from one institution and see who resembles it, lens by lens, with the "
                   "agreement between lenses shown rather than averaged away."),
    "FIND_LEAD": "Which institutions have a research profile close to this one?",

    "COMPARE_LABEL": "Compare",
    "COMPARE_BLURB": ("Put the shortlist side by side: subject profile, specialisations, ERC and SDG "
                      "mirrors, frontier positioning, impact intervals, trends and coverage."),
    "COMPARE_LEAD": "Where do these institutions differ, and by how much?",

    "COLLAB_LABEL": "Collaborate",
    "COLLAB_BLURB": ("Take one pair and read what the two already share, what each one publishes in "
                     "that the other does not, and where their publications meet on OpenAlex."),
    "COLLAB_LEAD": "What would these two bring to each other?",

    "METHODS_LABEL": "How it is built",
    "METHODS_BLURB": ("Every definition, threshold and known weakness behind the figures, one "
                      "section per question a reader is entitled to ask."),
    "METHODS_LEAD": "Where does each number come from, and what does it leave out?",
}

# --------------------------------------------------------- Compare page ----
# 2B-1 to 2B-6, 2B-13, 2B-14. Stream C renders these keys. Each view carries
# a caption naming its denominator and its counting basis, because a share
# read without its denominator is unreadable at a glance.

COMPARE = {
    "PAGE_TITLE": "Compare",
    "PAGE_INTRO": ("Institutions side by side on the same measures. Each institution keeps one "
                   "colour across every chart on the page, so a colour names an institution and the "
                   "axis names the subject."),

    # ---- selection ------------------------------------------------------
    "SELECTION_HEADER": "Institutions compared",
    "SELECTION_HELP": ("The comparison starts from the basket built on the Find page, and can be "
                       "edited here."),
    "ADD_LABEL": "Add an institution by name",
    "ADD_PICK": "Matching institutions",
    "ADD_BUTTON": "Add to the comparison",
    "REMOVE_BUTTON": "Remove",
    "CLEAR_BUTTON": "Clear the comparison",
    "CAP_REACHED": ("The comparison holds {cap} institutions at a time, which is what keeps the "
                    "charts readable. Remove one before adding another."),
    "CAP_HELP": "Two institutions at least, {cap} at most.",

    # ---- the institution strip ------------------------------------------
    "STRIP_HEADER": "Who is in the comparison",
    "STRIP_COLOUR_NOTE": "Colours are assigned once and hold across every chart below.",
    "STRIP_COUNTRY": "Country",
    "STRIP_TYPE": "Type",
    "STRIP_SIZE_FULL": "Size (full)",
    "STRIP_SIZE_FRAC": "Size (fractional)",
    "STRIP_PP": "PP(top10%)",
    "STRIP_BREADTH": "Breadth",

    # ---- the nine views: section headers ---------------------------------
    "VIEW_FIELDS": "Fields",
    "VIEW_SUBFIELDS": "Subfields",
    "VIEW_ERC": "ERC panels",
    "VIEW_SDG": "SDG profile",
    "VIEW_FRONTIER_MIX": "Frontier positioning",
    "VIEW_FRONTIER_POINTS": "Frontier topics",
    "VIEW_IMPACT": "Impact",
    "VIEW_TRENDS": "Trends",
    "VIEW_COVERAGE": "Coverage",

    # ---- captions: denominator and basis, one per view -------------------
    "CAPTION_FIELDS": ("Share of each institution's publications held in each field, on the {basis} "
                       "basis and the {tree} taxonomy; the shares sum to one per institution. The "
                       "mark beside each bar is the specialisation, read against that same mass."),
    "CAPTION_SUBFIELDS": ("Share of each institution's publications held in each subfield, on the "
                          "{basis} basis and the {tree} taxonomy; the shares sum to one per "
                          "institution. Subfields are ordered by the mass the compared set holds in "
                          "them, so every institution is represented."),
    "CAPTION_ERC": ("Share of each institution's ERC-classified publications held in each panel. The "
                    "denominator is the institution's own classified mass, which differs from one "
                    "institution to the next: the coverage view gives each one. Fractional basis "
                    "only."),
    "CAPTION_SDG": ("Share of each institution's SDG-tagged publications held under each goal. A "
                    "publication can carry several goals, so these shares need not sum to one, and "
                    "the denominator is the institution's own tagged mass. Fractional basis only."),
    "CAPTION_FRONTIER_MIX": ("Share of each institution's whole output in each quadrant of the "
                             "frontier map. Frontier scores measure attention dynamics rather than "
                             "novelty or quality: a low score can mark a foundational area."),
    "CAPTION_FRONTIER_POINTS": ("One mark per topic, placed on the two frontier axes and coloured by "
                                "institution; the size of a mark is the publications that "
                                "institution holds in the topic, on the {basis} basis."),
    "CAPTION_IMPACT": ("Share of each institution's articles and reviews from {y0} to {y1} that land "
                       "in the world top decile of citations for their own subfield, year and "
                       "document type, with the interval around each figure. Fractional basis "
                       "throughout."),
    "CAPTION_COVERAGE": ("Share of each institution's whole fractional output in each state. The six "
                         "states are exclusive and sum to that total, so the classified share is "
                         "what the subject, ERC and SDG views above rest on."),

    # ---- frontier quadrant: the fifth segment (A2) ------------------------
    "QUADRANT_UNSCORED_LABEL": "Not frontier-scored",
    "QUADRANT_UNSCORED_HELP": ("Publications in topics on the excluded list, plus publications in "
                               "topics that carry no frontier score for another reason. Showing them "
                               "is what makes the quadrant shares add up to the whole output."),
    "QUADRANT_MISSING_HELP": ("A quadrant an institution holds nothing in reads as zero by "
                              "construction, not as a missing measurement."),
    "CAPTION_QUADRANT_COUNTS": ("{n_scored} of this set's publications sit in topics carrying a "
                                "frontier score; {n_unscored} sit in excluded or unscored topics."),

    # ---- impact: the union frame, the missing cells, the floor toggle -----
    "IMPACT_INDEX_HEADER": "Across the whole output",
    "IMPACT_SUBFIELD_HEADER": "By subfield",
    "IMPACT_FLOOR_LABEL": "Minimum publications behind a cell",
    "IMPACT_FLOOR_OPTION": "at least {floor} fractional publications",
    "IMPACT_FLOOR_HELP": ("Lowering the floor brings more subfields into the view and widens the "
                          "intervals around them, because fewer publications sit behind each "
                          "figure."),
    "IMPACT_NA_LABEL": "n/a",
    "IMPACT_UNION_CAPTION": ("Every subfield at least one of the compared institutions clears at this "
                             "floor is shown. Where an institution does not clear it, the cell reads "
                             "n/a: it publishes too little there for the figure to be measured, "
                             "which is a different thing from a low value."),
    "IMPACT_BONUS_NOTE": ("{bonus_year} is a bonus year and stays out of every impact figure on this "
                          "page."),

    # ---- trends ----------------------------------------------------------
    "TRENDS_HEADER": "Trends in the {n} subfields this set publishes most in",
    "TRENDS_SELECTION_HELP": ("The subfields are chosen by the publication mass the whole compared "
                              "set holds in them, so a subfield that matters to one institution "
                              "alone can still appear."),

    # ---- coverage: the six states plus the total -------------------------
    "STATE_CLASSIFIED": "Classified",
    "STATE_CLASSIFIED_HELP": ("Publications that cleared every exclusion and were read by the subject "
                              "and topic classifiers."),
    "STATE_TITLE_ONLY": "Title only",
    "STATE_TITLE_ONLY_HELP": ("No abstract in the record, so the subject reading rests on the title "
                              "alone and the SDG classifier is not run on it."),
    "STATE_LANG_UNCERTAIN": "Language uncertain",
    "STATE_LANG_UNCERTAIN_HELP": ("The language of the text could not be established with enough "
                                  "confidence to route the record to a classifier."),
    "STATE_UNTRANSLATED": "Untranslated",
    "STATE_UNTRANSLATED_HELP": ("Written in a language outside the translation set, so the text was "
                                "never read in English."),
    "STATE_RETRACTED": "Retracted",
    "STATE_RETRACTED_HELP": ("Counted in the size figures and left out of the subject "
                             "classification."),
    "STATE_UNUSABLE": "Unusable",
    "STATE_UNUSABLE_HELP": ("Neither a usable title nor a usable abstract, so nothing could be read "
                            "from the record."),
    "STATE_TOTAL": "All publications",
    "STATE_TOTAL_HELP": ("The institution's whole fractional output over the window, which is the "
                         "denominator of the six states."),

    # ---- the scenario flip (A10) -----------------------------------------
    "SPINNER_SCENARIO": ("Rebuilding the profiles for this taxonomy and counting basis. This happens "
                         "once per setting, then the page answers straight away."),

    # ---- export (2B-13) ---------------------------------------------------
    "EXPORT_XLSX_BUTTON": "Download this comparison (Excel)",
    "EXPORT_XLSX_HELP": ("One sheet per view, plus a Methods sheet naming the snapshot, the settings "
                         "and the denominator of every other sheet."),
    "XLSX_SHEET_METHODS": "Methods",
    "XLSX_COL_ITEM": "What",
    "XLSX_COL_VALUE": "Value",
    "XLSX_COL_SOURCE": "Where it comes from",
    "XLSX_ROW_SNAPSHOT": "Snapshot",
    "XLSX_ROW_WINDOW": "Publication window",
    "XLSX_ROW_TREE": "Subject taxonomy",
    "XLSX_ROW_BASIS": "Counting basis",
    "XLSX_ROW_INSTITUTIONS": "Institutions compared",
    "XLSX_ROW_DENOMINATORS": "Denominator, sheet by sheet",
    "XLSX_ROW_FILTERS": "Filters in force",
    "XLSX_ROW_READING": "Reading",

    # ---- empty states -----------------------------------------------------
    "EMPTY_TOO_FEW": ("Comparing needs at least two institutions. Add one from the search above, or "
                      "build a basket on the Find page."),
    "EMPTY_NO_ERC": ("{institution} has no ERC-classified publications in this snapshot, so it holds "
                     "no bar in this view."),
    "EMPTY_NO_SDG": ("{institution} has no SDG-tagged publications in this snapshot, so it holds no "
                     "bar in this view."),
    "EMPTY_IMPACT_FLOOR": ("No subfield is cleared by any of the compared institutions at this floor. "
                           "Lower the floor, or read the figure for the whole output above."),
    "EMPTY_TRENDS": ("None of the compared institutions carries a per-year subfield breakdown in this "
                     "snapshot."),
    "EMPTY_FRONTIER_POINTS": ("None of the compared institutions holds publications in topics that "
                              "carry a frontier score."),

    # ---- added by Stream C (page composition): controls, reading keys and ---
    # ---- the strings the shipped chart forms turned out to need ------------
    "DEEPLINK_LABEL": "Share this comparison, exactly as it stands, with this link.",
    "MOVE_UP": "Up",
    "MOVE_DOWN": "Down",
    "MOVE_HELP": ("The order sets how the institutions are listed and what the shared link "
                  "carries. Colours do not move with it."),
    "READING_ORDER": ("Inside every row, the institutions read from top to bottom in the order the "
                      "legend lists them from left to right."),
    "CAPTION_SUBFIELDS_TOP": ("Showing the {n} subfields the compared set holds the most "
                              "publications in."),
    "FRONTIER_FORM_LABEL": "Layout",
    "FRONTIER_FORM_FACETS": "One panel per institution",
    "FRONTIER_FORM_OVERLAY": "Every institution in one plane",
    "CAPTION_FRONTIER_OVERLAY": ("In this layout nearly every mark is covered by a mark of another "
                                 "institution, measured on a full comparison at this width. Read it "
                                 "for which topics sit furthest out over the whole set, and read the "
                                 "panels for the shape of one institution's cloud."),
    "CAPTION_FRONTIER_FACETS": ("Every panel shares the same axes and the same mark scale, so the "
                                "clouds can be compared as shapes."),
    "CAPTION_IMPACT_SHOWN": ("Showing the {n} of the {n_union} subfields in the union that this set "
                             "holds the most publications in."),
    "CAPTION_TRENDS_SHARE": ("Each line is the share of that institution's own publications of the "
                             "year that sits in the subfield of its panel, on the {basis} basis and "
                             "the {tree} taxonomy. Every panel shares one vertical scale, so a line "
                             "can be read against any other line on the grid."),
    "CAPTION_CLASSIFIED_SHARES": ("Share of each institution's output behind these bars, in the "
                                  "order of the legend: {shares}."),
    "DOWNLOAD_VIEW": "Download the figures behind this view",
    "STRIP_LINK_PUBS": "Publications",
    "HANDOFF_HEADER": "Take one pair further",
    "HANDOFF_HELP": ("Two institutions at a time can be read as a possible collaboration: what they "
                     "already share, and what each one publishes in that the other does not."),
    "HANDOFF_A_LABEL": "First institution",
    "HANDOFF_B_LABEL": "Second institution",
    "HANDOFF_LINK": "Open this pair",
    "XLSX_SHEET_IMPACT_INDEX": "Impact overall",
    "XLSX_SHEET_IMPACT_SUBFIELDS": "Impact by subfield",
    "XLSX_ROW_FLOORS": "Floors in force",
    "XLSX_ROW_SHEETS": "Sheets, and what each one counts",
    "XLSX_SOURCE_PAGE": "The Compare page, as it stood when this file was written.",
}

# ----------------------------------------------------- Collaborate page ----
# 2B-7 / 2B-8: exactly two institutions, read in one direction at a time.

COLLAB = {
    "PAGE_TITLE": "Collaborate",
    "PAGE_INTRO": ("Two institutions read against each other: the topics both already publish in, "
                   "and the topics each one is absent from inside its own strongest subfields."),

    # ---- the pair picker --------------------------------------------------
    "PAIR_HEADER": "The pair",
    "PAIR_A_LABEL": "Institution A",
    "PAIR_B_LABEL": "Institution B",
    "PAIR_SWAP_BUTTON": "Swap A and B",
    "PAIR_SWAP_HELP": ("The gap tables read in one direction, so swapping changes which institution "
                       "the gaps are listed for."),
    "PAIR_PROMPT": ("Pick two institutions, from the basket or by name, to read what they share and "
                    "what each one lacks."),
    "PAIR_PICK": "Matching institutions",

    # ---- shared topics ----------------------------------------------------
    "SHARED_HEADER": "What both already work on",
    "SHARED_COL_TOPIC": "Topic",
    "SHARED_COL_SUBFIELD": "Subfield",
    "SHARED_COL_SHARE_A": "Share held by A",
    "SHARED_COL_SHARE_B": "Share held by B",
    "SHARED_COL_MIN": "Shared share",
    "SHARED_COL_KEYWORDS": "Keywords",
    "SHARED_COL_FRONTIER": "Frontier",
    "SHARED_CAPTION": ("Topics both institutions publish in, ordered by the smaller of the two "
                       "shares, which is the part of the portfolio the two hold in common on that "
                       "topic. Summed over every shared topic, those smaller shares come to "
                       "{score}, the topic-overlap score the Find page ranks on."),
    "SHARED_KEYWORDS_HELP": ("The keywords OpenAlex attaches to the topic, kept as readable evidence "
                             "of what the topic covers."),

    # ---- the two gap tables -----------------------------------------------
    "GAPS_HEADER": "What {a} does not publish in",
    "GAPS_CAPTION": ("Topics {b} publishes in inside {a}'s strongest subfields, where {a} has no "
                     "publications; frontier-flagged where the topic is in the global top quartile."),
    "GAPS_COL_TOPIC": "Topic",
    "GAPS_COL_SUBFIELD": "Subfield",
    "GAPS_COL_SHARE": "Share held by the other institution",
    "GAPS_COL_FRONTIER": "Frontier",
    "GAPS_FRONTIER_HELP": ("The topic sits in the global top quartile of emergence, so attention to "
                           "it is rising faster than the world average."),

    # ---- breadth overlap --------------------------------------------------
    "BREADTH_HEADER": "Breadth overlap",
    "BREADTH_LINE": ("{jaccard} of the topics either institution touches are touched by both: "
                     "{n_shared} shared, out of {n_a} for A and {n_b} for B. This counts a topic once "
                     "whatever mass sits on it, so it answers a different question from the shared "
                     "table above, which weighs every topic by the publications behind it."),

    # ---- link-outs --------------------------------------------------------
    "LINKS_HEADER": "Read the publications on OpenAlex",
    "LINK_PUBS": "{name}: publications",
    "LINK_COPUBS": "Publications the two have signed together",

    # ---- empty states -----------------------------------------------------
    "EMPTY_NO_PAIR": ("Two institutions are needed here. Pick them above, or open this page from a "
                      "pair in the comparison."),
    "EMPTY_SAME": "The two selections are the same institution. Pick a second one.",
    "EMPTY_SHARED": ("{a} and {b} publish in no topic in common in this snapshot, which is itself a "
                     "finding: their portfolios do not meet at topic grain."),
    "EMPTY_GAPS": ("{b} publishes in no topic inside {a}'s strongest subfields that {a} is absent "
                   "from."),
    "EMPTY_BREADTH": "Neither institution carries topic-level publications in this snapshot.",

    # ---- Stream L additions (Collaborate page, 2B-7): the row count the
    # shared caption does not carry, the breadth floor the page passes to
    # `collab_data.breadth_jaccard`, the two CSV buttons, and the label above
    # the shareable pair link.
    "SHARED_ROWS": "{n} topics are held by both institutions under the current settings.",
    "BREADTH_FLOOR": ("A topic counts for an institution once at least {min_pubs} of its "
                      "full-counted publications sit there, so a single co-authored paper does "
                      "not by itself put a topic in a portfolio."),
    "DOWNLOAD_SHARED": "Download the shared topics (CSV)",
    "DOWNLOAD_GAPS": "Download this gap list (CSV)",
    "DEEPLINK_LABEL": "Link to this pair",
}

# --------------------------------------------------------- Methods page ----
# 2B-9 / A5: one section per objection, ordered as a reader meets them. The
# app renders these templates and fills every `{placeholder}` at run time
# from CFG, the manifest or the index (the mapping is METHODS_SOURCES below,
# and `docs/METHODS_NOTE.md` carries the same sections with the numbers
# written out and a citation per section). Sources: INDICATOR_SPEC_v2.md S1
# to S3 and S8, DESIGN.md S2.2/S4/S5/S7, METHODS_FAISCEAU.md S1/S2/S6,
# app/docs/data_contract.yaml, evals/aspirational_R2/REPORT.md,
# evals/type_scan_R2/TYPE_SCAN.md.


def _lens_paragraphs() -> str:
    """One paragraph per lens, built from the two dicts the Find page already
    renders (`LENS_NAMES` + `LENS_INTRO` + `LENS_CAVEAT`) rather than from a
    second copy of the same sentences: the Methods page and the lens guide
    can never drift, and the placeholders stay the ones the Find page already
    fills."""
    order = ["L0", "L1", "L3", "F1", "L2f", "L4", "L5", "L6", "C1", "L7"]
    return "\n\n".join(f"{LENS_NAMES[k]}. {LENS_INTRO[k]} {LENS_CAVEAT[k]}" for k in order)


METHODS = {
    "publications": {
        "title": "What counts as a publication",
        "body": FIND["PUBLICATIONS_TOOLTIP"] + (
            " Every institution in the index is based in one of the {n_countries} countries of the "
            "perimeter: the European Union, the United Kingdom, Switzerland, Norway and Iceland. "
            "Publications signed with partners outside that perimeter are counted in full, and the "
            "partners themselves are not in the index."),
    },
    "attribution": {
        "title": "Attribution, and the two counting bases",
        "body": (
            "An institution is credited with a publication when the publication's own record names "
            "it. The chain of parent and child organisations OpenAlex maintains is deliberately not "
            "followed: for an institution that shares a laboratory with a partner, following it "
            "grafts the partner's whole portfolio onto the parent and inflates the count several "
            "times over.\n\n"
            "Two counting bases are offered. Full counting credits the whole publication to every "
            "institution named on it, which raises the totals of institutions that co-publish "
            "widely. Fractional counting gives each author an equal part of the publication and "
            "splits that part across the institutions the author declares, so a paper written with "
            "many partners counts for a fraction. Neither is more correct; they answer different "
            "questions, and the setting that governs them is stated on every page that uses it.\n\n"
            "The ERC, SDG and impact figures are fractional whatever that setting says, and the "
            "views that carry them say so on the view itself. Records whose author list is "
            "truncated by the OpenAlex list endpoint are re-fetched one at a time, so that large "
            "collaborations keep their full author list and their fractional weights stay right."),
    },
    "taxonomy": {
        "title": "The subject taxonomy and its three versions",
        "body": (
            "OpenAlex files every publication under a topic, every topic under a subfield, and every "
            "subfield under a field. A measurable share of those subfield placements is wrong, so "
            "the tool ships {n_trees} versions of the taxonomy: the original as OpenAlex publishes "
            "it, a conservative repair that moves only the clear cases, and a best-fit repair that "
            "moves more. Every topic keeps a subfield under all three, so subfield volumes always "
            "sum to the institution's total.\n\n"
            "Changing the version moves publications between subfields and fields, which shifts the "
            "profile charts and the subfield lenses; the topic, ERC and SDG views are untouched by "
            "it. The repair is a judgement in the arguable cases, and a share of the assignments in "
            "each version is arguable, which is why the original tree stays selectable for "
            "comparison. Impact is the one exception: a publication's top-decile flag is decided "
            "against the world threshold of its original subfield, so the flag does not move when "
            "the version does."),
    },
    "lenses": {
        "title": "The lenses, one by one",
        "body": (
            "A lens is one way of asking whether two institutions resemble each other. Each reads a "
            "different classification at a different grain, so a candidate can rank high on one and "
            "be absent from another; that disagreement is information, and the tool shows it rather "
            "than averaging it into a single score. The codes are stable identifiers, reused in the "
            "overview, the evidence column and the downloads. {n_lenses} lenses are shown by "
            "default and two more are one click away.\n\n" + _lens_paragraphs()),
    },
    "concordance": {
        "title": "Concordance",
        "body": (
            "Concordance counts how many lenses place a candidate inside their own "
            "top-{concordance_n}. It measures agreement between lenses, and it is not a score: a "
            "candidate found by several lenses is a candidate several independent readings support, "
            "not a candidate that resembles the seed several times over. Both numbers are always "
            "shown, the depth and the count of lenses defined for that seed, so the fraction can be "
            "read.\n\n"
            "Concordance was tested for whether it surfaces anything the lenses themselves miss. At "
            "every depth checked it returned no candidate absent from the union of the individual "
            "lenses, which is why it opens the page as the cleanest list to read and never stands "
            "as the only list."),
    },
    "aspirational": {
        "title": "The aspirational view",
        "body": (
            "The aspirational view keeps the candidates the subfield lens already found whose impact "
            "interval sits entirely above the seed's, in the order the subfield lens produced. It "
            "empties for an institution already at the top of its own pool, and thins to a handful "
            "of rows for a narrow small one; both are readable results rather than failures.\n\n"
            "{n_definitions} definitions of the word were generated for {n_seeds} institutions and "
            "graded by two independent judges reading the lists without knowing what was expected of "
            "them. The definition shipped here scored highest, with the cleanest lists. A second "
            "mode, ranking the same pool by shared presence in emerging topics, scored as well and "
            "returned a full list for the institutions where this one empties: it is a candidate for "
            "a later release, and it is not what the tool does today."),
    },
    "specialisation": {
        "title": "Specialisation, and the floors it is displayed at",
        "body": (
            "A specialisation index compares the share an institution holds in a subject with the "
            "share held by the average institution active in that subject. A value of one is what "
            "that average institution holds, which is why the charts draw the line at one rather "
            "than at zero.\n\n"
            "A specialisation is never shown without the publications behind it, because a share of "
            "a very small mass moves for reasons that have nothing to do with strategy. Three "
            "display states follow from the mass in the cell: a solid mark at {floor_solid} "
            "fractional publications or more, a hollow mark between {floor_thin} and {floor_solid}, "
            "and no mark at all below {floor_thin}. The similarity lenses that compare "
            "specialisations use their own floor of {floor_papers} papers, applied to both "
            "institutions, so a cell counts only where both publish enough for the comparison to "
            "mean something."),
    },
    "impact": {
        "title": "Impact: PP(top10%)",
        "body": (
            "The impact figure is PP(top10%): the share of an institution's articles and reviews "
            "that land in the world top decile of citations for their own subfield, year and "
            "document type. The thresholds are computed on the world rather than on Europe or on "
            "the index, so an institution is read against the field it publishes in and not against "
            "its neighbours.\n\n"
            "The denominator is the institution's own fractional mass of articles and reviews "
            "between {y0} and {y1}. {bonus_year} is harvested and reported for volumes, and left "
            "out of every impact figure, because a recent year has not had time to accumulate the "
            "citations the threshold is built on. Every figure carries an interval from "
            "{n_bootstrap} resamples and is rendered with it, never as a point estimate alone: for "
            "a small institution that interval is wide enough to change the reading, and two "
            "institutions whose intervals overlap are not separated by the data.\n\n"
            "Per-subfield cells need a minimum mass before an interval means anything. A cell below "
            "the floor in force is shown as unavailable rather than as a low value, and lowering "
            "the floor brings more cells in at the cost of wider intervals on all of them."),
    },
    "frontier": {
        "title": "Frontier scores",
        "body": (
            "Frontier scores measure attention dynamics: how fast a topic is expanding, and whether "
            "that expansion is accelerating. They say nothing about novelty or quality, and a low "
            "score can mark a foundational area a whole discipline rests on. Each topic is placed on "
            "the two axes, which gives four quadrants, and an institution's position is the share of "
            "its publications sitting in each.\n\n"
            "{n_excluded} topics carry no frontier score by construction: they are catch-all topics "
            "outside the subject scope of the taxonomy, and the exclusion list is versioned with a "
            "reason recorded per topic. Their mass is shown as a segment of its own rather than "
            "dropped, so the quadrant shares add up to the institution's whole output and a large "
            "unscored share is visible instead of hidden."),
    },
    "erc": {
        "title": "The ERC classifier",
        "body": (
            "The ERC classifier assigns publications to the {n_panels} evaluation panels the "
            "European Research Council uses to sort proposals, which is what makes the view "
            "readable by anyone who has written a proposal. It reads the title and the abstract, "
            "and assigns a panel when its confidence passes {tau}. A publication no panel reaches "
            "that level on is left unclassified rather than forced into the nearest one; a "
            "publication reaching it on several panels is split equally between them.\n\n"
            "Two panels, Biotechnology and Arts, have low recall in the model's own published "
            "evaluation, so an institution active in either will read lower there than it is, and "
            "the panel views say so where they are drawn. The denominator of every ERC share is the "
            "institution's own classified mass, which the coverage view gives per institution, and "
            "every ERC figure is fractional whatever the counting setting says."),
    },
    "sdg": {
        "title": "The SDG classifier",
        "body": (
            "The SDG classifier reads the title and the abstract against a vocabulary held per goal "
            "and records every goal it finds a keyword for, so a publication can carry several goals "
            "or none at all. {n_sdgs} goals are covered; goal {missing} is not, and it is left out "
            "rather than drawn as an empty row.\n\n"
            "The denominator of an SDG share is the institution's own tagged mass, so the shares of "
            "one institution need not sum to one. Matches reflect this classifier's reading of the "
            "goals, and different classifiers disagree substantially on the same corpus: the "
            "figures here support a comparison made inside the tool, and they should not be set "
            "against another provider's SDG numbers. Publications with no abstract are not run "
            "through the classifier at all, which the coverage view makes visible per institution."),
    },
    "grey": {
        "title": "Grey accounting: what happened to every publication",
        "body": (
            "Nothing is dropped silently. Every publication sits in one of six states, and the six "
            "sum to the institution's whole fractional output: classified, title only, language "
            "uncertain, untranslated, retracted, and unusable.\n\n"
            "Retracted publications are counted in the size figures and kept out of the subject "
            "classification, so the subject, topic, ERC and SDG panels rest on a slightly smaller "
            "set than the size figures do. Where a classifier found nothing, the result is recorded "
            "as unknown and never as zero. The coverage view on the Compare page shows the six "
            "states per institution, which is what makes an ERC or SDG share comparable: an "
            "institution with a large title-only share has a smaller base behind its classified "
            "figures than a neighbour showing the same headline number."),
    },
    "types": {
        "title": "Corrected institution types",
        "body": (
            "OpenAlex assigns each institution a type, and some assignments do not match what the "
            "institution is: a public research organisation filed as a facility, a business school "
            "filed as a company. {n_overrides} corrections have been reviewed one by one against "
            "the institution's own record and applied. {n_gated} further cases were examined and "
            "left as they are, because the institution genuinely sits between two categories, a "
            "hospital and a university department among them.\n\n"
            "A correction changes the label and what the type filter does, never a rank and never "
            "whether an institution is in the index; the original type is kept and shown on the "
            "badge. The list is one an operator is expected to keep extending, and its coverage of "
            "the cases nobody has examined yet is unknown, so an institution carrying no correction "
            "has not necessarily been checked."),
    },
    "index": {
        "title": "Which institutions are in the index",
        "body": (
            "The index holds {n_institutions} institutions. An institution enters it when its "
            "record carries at least {floor_total} publications over the window and at least "
            "{floor_recent} in each of the two most recent full years, which keeps out records too "
            "thin to profile and records of activity that has stopped.\n\n"
            "The population that results is not a peer group. It is dominated by small specialised "
            "institutes and hospitals rather than by universities, so a median computed on it "
            "describes that population and is not a level to reach. Every figure positioned against "
            "the index says so, and a value under the median places an institution within the "
            "population without saying anything on its own about how well it performs."),
    },
    "snapshot": {
        "title": "Snapshot and vintage",
        "body": (
            "Every figure in the tool comes from one snapshot, {snapshot}, and that stamp is shown "
            "on the Find page. OpenAlex is a living database: records are added, abstracts are "
            "edited and citation counts move, so a query run against the live source today will not "
            "return exactly what the tool shows.\n\n"
            "The links out to OpenAlex carry the same filters as the snapshot and will still differ "
            "by a small amount for that reason, which the links say. Reproducing a figure means "
            "running the same code against the same archived snapshot; running it again against the "
            "live source is a different measurement, not a check."),
    },
    "ceiling": {
        "title": "What the tool cannot find, and how it was checked",
        "body": (
            "The lenses were checked against a set of peers assembled outside OpenAlex and graded by "
            "hand. {n_unfound} of those peers are found by no lens at all at depth {depth_max}, "
            "although they are the same type as their seed and a comparable size: peers that come "
            "from a shared national system or a shared mission do not show up in the shape of an "
            "output. The free-text search on every page exists for exactly that case, and a peer no "
            "list contains is not thereby a wrong peer.\n\n"
            "The checking itself has a known weakness. An earlier round of validation measured the "
            "lenses against a list of expected peers written by a language model; when that list "
            "was set against evidence assembled independently, much of it went unconfirmed and much "
            "of the independent evidence had been missed. The figures quoted in this note come from "
            "the independent evidence, and the judged readings that support them were produced by "
            "language models rather than by domain experts.\n\n" + VERDICT_LINE),
    },
}

# Where the app gets each `{placeholder}` above. Stream M fills them; this
# dict is the contract, and `tests/test_methods_note.py` fails if a template
# grows a placeholder that is not documented here. Descriptions name the key
# or the column, never the value, so this dict carries no digit either.
METHODS_SOURCES = {
    "n_countries": "number of entries in CFG perimeter_countries",
    "y0": "first entry of CFG window",
    "y1": "second entry of CFG window",
    "bonus_year": "CFG bonus_year",
    "n_trees": "number of entries in CFG scenario.toggles.tree",
    "n_lenses": "number of entries in CFG lenses.default",
    "concordance_n": "CFG concordance_N",
    "depth_max": "CFG depth.max",
    "core_top_n": "lib.views_find.CORE_TOP_N, the same value the C1 help text uses",
    "n_definitions": "count of aspirational variants tested, from the aspirational campaign report in evals",
    "n_seeds": "count of seeds in the aspirational campaign results file in evals",
    "floor_solid": "lib.profile_data.SI_FLOOR_SOLID, the same value the profile caption uses",
    "floor_thin": "lib.profile_data.SI_FLOOR_THIN, the same value the profile caption uses",
    "floor_papers": "CFG lens floor value for shared specialisations, counted in papers",
    "n_bootstrap": "source_manifest.json bootstrap_reps",
    "n_excluded": "count of topics_dim.parquet rows with is_excluded true",
    "n_panels": "count of distinct panel_idx in erc.parquet",
    "tau": "CFG erc_tau",
    "n_sdgs": "count of distinct sdg_idx in sdg.parquet",
    "missing": "the one goal the SDG vocabulary does not cover (DESIGN.md section five)",
    "n_overrides": "MANIFEST.json type_overrides.n_rows",
    "n_gated": "count of gated rows in the type-override gate file under data/overrides",
    "n_institutions": "MANIFEST.json files, index.parquet, n_rows",
    "floor_total": "index population rule, total publications floor (docs/data_contract.yaml, index grain)",
    "floor_recent": "index population rule, per-recent-year floor (docs/data_contract.yaml, index grain)",
    "snapshot": "MANIFEST.json snapshot, falling back to CFG snapshot",
    "n_unfound": "count of external peers reached by no lens, indicator spec section eight, recall ceiling",
}

# ------------------------------------------------ Methods page chrome (2B, manager) --
METHODS_UI = {
    "DOWNLOAD_LABEL": "Download the source note (Markdown)",
    "DOWNLOAD_CAPTION": ("This page and the file above come from the same templates: the numbers here are "
                         "filled at run time from the snapshot loaded, the file states them in full with a "
                         "citation per section."),
}

# ----------------------------------------------------- digit-ban self-check -

_ALLOWLIST_RE = re.compile(
    r"\bL0\b|\bL1\b|\bL2f\b|\bL2\b|\bL3\b|\bL4\b|\bL5\b|\bL6\b|\bL7\b|\bL8\b|\bL9\b|\bF1\b|\bC1\b|"
    r"top10|PP\(top10%\)"
)
# 2B-R-11a adds L2/L8/L9 -- L2 is the renumbered topic lens's own DISPLAY
# code (L2f, a DIFFERENT lens, must stay in the alternation and BEFORE L2 so
# the longer token matches first), L8/L9 are the two optional lenses' codes --
# to the allowlist above; `tests/test_narrative.py::has_digit_violation`
# carries its own copy of this same stripping behaviour and is updated
# alongside it.
# A `{named}` format placeholder is never rendered literally -- the RULE at
# the top of this file exempts it explicitly -- so a digit inside the
# placeholder's own name (e.g. the FIND section's "{y0}"/"{y1}") is not a
# digit-ban violation. Stripped before the scan below, same as this file's
# independent reimplementation in tests/test_narrative.py's
# `has_digit_violation` (kept in sync with that stripping behaviour, not with
# its literal regex source).
_PLACEHOLDER_RE = re.compile(r"\{[^{}]*\}")


def _iter_strings(value):
    """Every string inside a constant, however deeply nested. Phase 2B's
    `METHODS` is a dict of {"title", "body"} sub-dicts, so a one-level walk
    (the pre-2B behaviour) would have skipped every Methods-page sentence:
    the scan must recurse or it goes vacuous exactly where the longest new
    copy lives. `tests/test_narrative.py` carries the same widening."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _iter_strings(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            yield from _iter_strings(v)


def scan_for_digit_violations() -> list[tuple[str, str]]:
    """Every string constant above (dict values included), digits allowed only
    inside the allowlisted lens codes / top10 / PP(top10%) / a `{placeholder}`.
    Returns (constant_name, offending_value) pairs; empty list = PASS."""
    violations = []
    for name, value in globals().items():
        if name.startswith("_") or not name.isupper():
            continue
        for v in _iter_strings(value):
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

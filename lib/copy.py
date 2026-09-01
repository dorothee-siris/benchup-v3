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
          "from other countries readily, so the list is not simply an effect of shared country.",
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
    "L6": "Country clustering is modest here, so the list does not simply reflect a shared country.",
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
# ADD_COMPARATOR_HELP DELETED 2BR3 (TEV-U wave 3 deletion ledger, SEL's own
# flag): the old per-page "add a comparator by name" flow this help text
# belonged to is gone (superseded by `selection.render_sidebar`'s shared
# search); confirmed zero usage by grep across lib/ and tests/.

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
    "BASKET_EMPTY": "No institution added yet. Search above and add one.",
    "BASKET_COUNT": "{n} of {cap} added",
    "BASKET_FULL": ("The basket already holds the most institutions it can hold at "
                     "once ({cap}). Remove one before adding another."),
    "BASKET_CLEAR": "Clear basket",
    "BASKET_REMOVE": "✕",
    # ---- 2BR3 SEL, ruling 1: the ONE shared sidebar search + basket, live on
    # every page through lib/selection.render_sidebar -- replaces the old
    # per-view "add a comparator" flow (ADD_COMPARATOR_LABEL/PICK/BUTTON,
    # retired; see WT_2BR3.md §5.7 views_find.py:370-398). One-click add per
    # result row, never a pick-then-click second step.
    "SIDEBAR_SEARCH_HEADER": "Search institutions",
    # "＋" not "Add": the 1/5 sidebar column is too narrow for a word — "Add"
    # wraps to one letter per line at 1920px (manager merge fix, SEL proof
    # screenshot). The help tooltip carries the words.
    "SIDEBAR_ADD_BUTTON": "＋",
    "SIDEBAR_ADD_HELP": "Add to basket",
    # ---- 2BR3 SEL: the slots API (lib/selection.slots_row), Compare/
    # Collaborate's own basket-only slot pickers.
    "SLOT_EMPTY_LABEL": "Empty slot",
    "SLOT_LABEL": "Slot {n}",
    "SLOT_NEED_COMPARE": ("Add at least two institutions to your basket, using the "
                          "sidebar search, to compare them."),
    "SLOT_NEED_COLLAB": ("Collaborate reads exactly two institutions. Pick two in the "
                        "slots above, adding more to your basket first if you need to."),
    "PAGE_TITLE": "Find",
    "PAGE_INTRO": "Add institutions in the sidebar, then read who resembles the one you profile, across independent lenses.",
    # 2B-R-12 / A14: the verbose "Snapshot: <label> (generated <timestamp>)"
    # stamp is GONE from every page. The key and its four call-site keywords
    # (`snapshot`, `generated_at`, `n_institutions`, `sep`) are kept exactly as
    # they were -- `str.format` ignores the keywords a template stops using --
    # so the four callers (Find, Compare, Collaborate, Methods) drop the string
    # without any of their files being edited. Find and Menu use the richer
    # DATA_CAPTION below; the Methods page keeps its factual provenance in its
    # own METHODS["snapshot"] section, which is where a vintage belongs.
    "SNAPSHOT_CAPTION": "{n_institutions} institutions in the index.",
    # 2BR3 SEL: SEED_SEARCH_LABEL now labels the ONE shared sidebar search box
    # (lib/selection.render_sidebar), not a Find-only field -- the wording
    # already named what it searches by, not where it lives, so it carries
    # over unchanged. SEED_PICK_LABEL/PLACEHOLDER/PROMPT are Find's own
    # dropdown OVER THE BASKET that replaced the free-text seed search.
    "SEED_SEARCH_LABEL": "Institution name, acronym or alternative name",
    "SEED_PICK_LABEL": "Institution to profile",
    "SEED_PROMPT": "Add an institution using the sidebar search to see its benchmark.",

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
    "SEED_PICK_PLACEHOLDER": "Choose which one to profile",

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

    # ======================================================================
    # Sprint 2 Phase 2B-R2, stream FA3 (2B-R2-1a / 2B-R2-6 / 2B-R2-8, Find
    # scope). ADDITIVE ONLY -- every key below is new, and the keys the cards
    # stop using (KPI_PUBS_HELP, KPI_PP_HELP, IDENTITY_FACTS_HELP,
    # PUBLICATIONS_LINK_LABEL) are left exactly as they stand for stream MU3's
    # own plain-language sweep to dispose of. Deleting one here would be a
    # crash in another stream's file, never a cleanup.
    # ======================================================================

    # 2B-R2-1a: the type correction is no longer a badge. It renders INLINE in
    # the identity line -- "government* (was: facility) · Brest, France" -- with
    # the star, and only the star, in red, and the whole line's tooltip saying
    # what the star means. Ten institutions carry it (Ifremer, TNO, CNR,
    # SINTEF, DLR, Ikerbasque and the four German centres); every one of them
    # crashed the profile while the correction and the umbrella badge were
    # asserted mutually exclusive.
    "IDENTITY_TYPE_CORRECTED": "{kind}{star} (was: {was})",
    "IDENTITY_TYPE_HELP": (
        "The type marked with a star is a SIRIS correction: OpenAlex records this institution "
        "under the type in brackets, which misdescribes what it is and would place it against the "
        "wrong comparison group. The corrected type is what every filter, median and comparison on "
        "this page uses."),

    # 2B-R2-6: the institution NAME is the link to its publications in
    # OpenAlex, so the row of links carries only the two links that point
    # somewhere else. What a publication IS moved into the publications card's
    # own tooltip, where the figure it qualifies is.
    "IDENTITY_NAME_HELP": (
        "The institution name opens its publications in OpenAlex, filtered exactly as this "
        "analysis filters them. The live count differs slightly from the figure shown here: "
        "OpenAlex keeps changing, this analysis reads a fixed extract."),

    # 2B-R2-6: SIX cards, name first. The publications card carries the
    # fractional count as its small line instead of an index position; the
    # other five carry the index baseline.
    "KPI_PUBS_FRAC_NOTE": "({n} in fractional counting)",
    "KPI_PUBS_HELP_FULL": (
        "The large figure counts every publication the institution is named on. The figure under "
        "it credits only the author share it holds, which is the fairer basis for comparing "
        "institutions of different sizes and the basis most of this page uses."),
    "KPI_PP_HELP_R2": (
        "Share of the institution's fractional output that sits in the world top decile of its "
        "own citation distribution. Articles and reviews only; the bonus year is excluded. The "
        "figure rests on the publications the world reference covers, so two institutions whose "
        "positions are close are not separated by this measure."),
    "KPI_INTL_LABEL": "International co-publications",
    "KPI_COMPANY_LABEL": "Industrial co-publications",
    "KPI_INTL_HELP": (
        "Share of the institution's publications from {y0} to {y1}, full counting, carrying at "
        "least one other institution named on the record and based in another country. "
        "Institutions OpenAlex cannot place in a country are counted in the denominator and never "
        "treated as domestic."),
    "KPI_COMPANY_HELP": (
        "Share of the institution's publications from {y0} to {y1}, full counting, carrying at "
        "least one company named on the record. The type is the one OpenAlex records for the "
        "partner, so an institute a company owns but OpenAlex types otherwise is not counted."),

    # 2B-R2-8 (Find scope) needs NO new string: what stays visible under a
    # chart is ONE reading line, and the second and third grey lines move --
    # verbatim, same keys -- into that line's own `?` tooltip. A relocation is
    # not a rewrite; rewriting these sentences is stream MU3's pass.

    # Phase 2C, stream VF (D5/D4, CHROME_CONTRACT.md S7): the SDG and ERC
    # profile panels read `sdg.parquet`/`erc.parquet`, both denominated on the
    # WHOLE-RUN window (window_conventions.sdg_mass_window, data_contract.yaml
    # -- six years, the bonus year included), never the five-year corpus
    # window this page states everywhere else. Disclosure only: the basis
    # itself is unchanged, this just says it in words where the ratio it
    # qualifies is on screen.
    "RATIO_WHOLE_RUN_BASIS": ("This panel's shares are computed on the {window} window (the whole "
                              "run, including the bonus year), not the {corpus} window used "
                              "elsewhere on this page."),
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

# ==========================================================================
# Sprint 2 Phase 2B-R2, stream MU3 (2B-R2-8/13): two plain-language templates
# a reader meets on more than one page, hoisted here so CP3 (Compare) and
# LP3 (Collaborate) read one shared wording rather than each writing its own
# for the same two situations: a measure this page does not show, and a row
# too thin to break down further. Neither names a plan code, a stream, or a
# table or file name: tests/test_forbidden_vocabulary.py scans this dict
# like every other constant in this file. Additive: COMPARE's own
# METRIC_HIDDEN_HEADER/METRIC_HIDDEN_LINE and COLLAB's own
# TOPIC_BELOW_FLOOR_NOTICE stay exactly where they are and say the same
# thing in the same voice; a page may read either its own key or this one.
# ==========================================================================

SHARED = {
    "NOT_OFFERED_HEADER": "Not shown here, and why",
    "NOT_OFFERED_LINE": "{feature}: {reason}",
    "BELOW_FLOOR_NOTICE": (
        "{item} holds {n} publications, under the {floor} a breakdown needs to stay readable. "
        "The total above is shown; the breakdown itself is not."),
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

    # ---- selection ---------------------------------------------------------
    # 2BR3 VC (plan SS1 items 1/8): the add-by-name flow, the basket-vs-
    # comparison cap message and the inline share link are GONE from here --
    # the sidebar owns search now (`selection.render_sidebar`) and the three
    # slots (`selection.slots_row("compare", 3)`) own the pick; the share
    # link moved to the bottom meta block (`links.share_link_block`).

    # ---- the nine views: section headers ---------------------------------
    "VIEW_FIELDS": "Fields",
    "VIEW_SUBFIELDS": "Subfields",
    "VIEW_ERC": "ERC panels",
    "VIEW_SDG": "SDG profile",
    "VIEW_FRONTIER_MIX": "Frontier positioning",
    "VIEW_FRONTIER_POINTS": "Frontier topics",
    "VIEW_IMPACT": "Impact",
    "VIEW_COVERAGE": "Coverage",

    # ---- captions: denominator and basis, one per view -------------------
    # CAPTION_FIELDS/CAPTION_SUBFIELDS/CAPTION_ERC/CAPTION_SDG (the pre-metric-
    # selector, one-caption-per-view shape) DELETED 2BR3 (TEV-U wave 3
    # deletion ledger): confirmed dead by grep (zero usages in lib/ or tests/)
    # BEFORE this stream too -- superseded by 2B-R2-8's `_metric_tip`/
    # `_taxon_tip` tooltip captions, long before 2BR3 (flagged by VC's own
    # progress note, not this round's regression).
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

    # QUADRANT_UNSCORED_LABEL/QUADRANT_UNSCORED_HELP/QUADRANT_MISSING_HELP/
    # CAPTION_QUADRANT_COUNTS (the retired four-quadrant frontier-mix chart)
    # DELETED 2BR3 (TEV-U wave 3 deletion ledger): confirmed dead by grep --
    # pre-existing (superseded by 2B-R-9's pooled map + shared-frontier
    # chart), not a 2BR3 regression.

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
    "EMPTY_NO_ERC": ("{institution} has no ERC-classified publications in this snapshot, so it holds "
                     "no bar in this view."),
    "EMPTY_NO_SDG": ("{institution} has no SDG-tagged publications in this snapshot, so it holds no "
                     "bar in this view."),
    "EMPTY_IMPACT_FLOOR": ("No subfield is cleared by any of the compared institutions at this floor. "
                           "Lower the floor, or read the figure for the whole output above."),
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
    # CAPTION_SUBFIELDS_TOP / FRONTIER_FORM_LABEL / FRONTIER_FORM_FACETS /
    # FRONTIER_FORM_OVERLAY DELETED 2BR3 (TEV-U wave 3 deletion ledger):
    # confirmed dead by grep -- the retired facets-vs-overlay frontier layout
    # toggle, pre-existing (superseded by 2B-R-9), not a 2BR3 regression.
    "CAPTION_FRONTIER_OVERLAY": ("In this layout nearly every mark is covered by a mark of another "
                                 "institution, measured on a full comparison at this width. Read it "
                                 "for which topics sit furthest out over the whole set, and read the "
                                 "panels for the shape of one institution's cloud."),
    "CAPTION_FRONTIER_FACETS": ("Every panel shares the same axes and the same mark scale, so the "
                                "clouds can be compared as shapes."),
    "CAPTION_IMPACT_SHOWN": ("Showing the {n} of the {n_union} subfields in the union that this set "
                             "holds the most publications in."),
    "CAPTION_CLASSIFIED_SHARES": ("Share of each institution's output behind these bars, in the "
                                  "order of the legend: {shares}."),
    "DOWNLOAD_VIEW": "Download the figures behind this view",
    "STRIP_LINK_PUBS": "Publications",
    "XLSX_SHEET_IMPACT_INDEX": "Impact overall",
    "XLSX_SHEET_IMPACT_SUBFIELDS": "Impact by subfield",
    "XLSX_ROW_FLOORS": "Floors in force",
    "XLSX_ROW_SHEETS": "Sheets, and what each one counts",
    "XLSX_SOURCE_PAGE": "The Compare page, as it stood when this file was written.",

    # ======================================================================
    # Sprint 2 Phase 2B-R, stream CP (2B-R-4/5/6/7/8/9/12). ADDITIVE ONLY:
    # every key below is new. The Phase 2B keys above stay in place -- the
    # rebuilt page still reads most of them (the captions, the impact floor,
    # the empty states, the workbook chrome), and a deleted key is a crash in
    # another stream's file rather than a cleanup.
    # ======================================================================

    # 2B-R-12: the chip the shared-frontier colour carries in every legend.
    "LEGEND_SHARED": "held by more than one",

    # 2B-R-7 / VIZ_SPEC 4.1: the overview cards replace the institution strip.
    "OVERVIEW_HEADER": "Key figures, side by side",
    "OVERVIEW_HELP": ("One card per institution, in the order every chart below draws them. The "
                      "swatch is the colour that institution keeps on this whole page."),
    "OVERVIEW_WINDOW": ("Publications, international co-publications and company co-publications "
                        "are counted over the {y0} to {y1} window, full counting. The other three "
                        "figures name their own denominator in their tooltip."),

    # 2B-R-5 / 2B-R-8: the one metric selector, and what it hides.
    "METRIC_LABEL": "Compare by",
    "METRIC_HELP": ("One measure at a time, so the bars in a row can be read against each other "
                    "without a second axis. The rows never re-sort under a control: the order is "
                    "the ranking the caption names."),
    "METRIC_SHARE": "Share",
    "METRIC_VOL_TOP10": "Publications in the world top decile",
    "METRIC_PP": "PP(top10%)",
    "METRIC_SDG_SHARE": "SDG-tagged share",
    "METRIC_DYNAMICS": "Change in mean annual volume",
    "METRIC_SI": "Specialisation",
    "METRIC_VOL": "Volume",
    # 2C (Stream VC, D2): FWCI joins the Subject/ERC/SDG "Compare by" selector.
    "METRIC_FWCI": "FWCI (median)",
    "METRIC_HIDDEN_HEADER": "Measures not offered here, and why",
    "METRIC_HIDDEN_LINE": "{metric}: {reason}",

    # 2B-R-5: the subject section (fields, with a drill into one field).
    "VIEW_SUBJECT": "Subject profile",
    "DRILL_LABEL": "Level of detail",
    "DRILL_ALL": "All fields",
    "CAPTION_SUBJECT": ("Read on the {basis} basis and the {tree} taxonomy. Each bar is one "
                        "institution and the value is written at its outer end, so a row can be "
                        "read without hovering."),
    "CAPTION_DRILL": "Showing the subfields of {field}.",
    "CAPTION_RANKED": ("Rows are ranked by the value the compared set holds between them, not by "
                       "any one institution's own ranking; colours never move with the order."),
    "EMPTY_METRIC": ("No institution carries a value for this measure at this level of detail "
                     "under the current settings."),

    # 2B-R-8: what the coloured glyph beside a row label means, and the one
    # rule it obeys.
    "CAPTION_ACCENT_ERC": ("The mark beside each panel name is the official colour of its ERC "
                           "domain. Colour on a bar is always the institution; a taxonomy's own "
                           "colour appears on labels only."),
    "CAPTION_ACCENT_SDG": ("The mark beside each goal is the official colour of that goal, and the "
                           "goal number stays in the label: two of the goal colours are hard to "
                           "tell apart, so the number is the encoding and the colour is "
                           "recognition on top of it."),

    # 2B-R-9: the two frontier charts that replace the panels and the overlay.
    "VIEW_FRONTIER_MAP": "The frontier, pooled",
    "FRONTIER_TOPN_LABEL": "Topics plotted",
    "FRONTIER_TOPN_HELP": ("The largest topics by the publications the compared set puts into "
                           "them. Raising it adds smaller topics and crowds the plane; the same "
                           "setting cuts the list below."),
    "CAPTION_FRONTIER_MAP": ("One bubble per topic, over the topics in the global top quartile of "
                             "emergence that these institutions publish in. Bubble area is the "
                             "publications the compared set holds in the topic on the {basis} "
                             "basis; colour names the institution that holds it alone."),
    "CAPTION_FRONTIER_SHARED_COUNT": ("{n_shared} of the {n_shown} topics plotted are held by more "
                                      "than one of the compared institutions: at the head of the "
                                      "volume ranking the colour split says very little, and what "
                                      "the plane shows is position and size."),
    "CAPTION_FRONTIER_AXES": ("The bold black lines are the two zero axes: right of the vertical "
                              "one attention to the topic is expanding, above the horizontal one "
                              "that expansion is itself speeding up."),
    "VIEW_SHARED_FRONTIER": "Who holds the shared frontier",
    # 2BR3 VC item 4: top twenty by combined volume by default, a button
    # (never a slider) swaps in the rest -- independent of the pooled map's
    # own "topics plotted" control just above it.
    "SHARED_FRONTIER_SHOW_ALL": "Show all {n}",
    "SHARED_FRONTIER_SHOW_TOP": "Show the top {n} only",
    "CAPTION_SHARED_FRONTIER": ("The topics more than one of them holds, ranked by the publications "
                                "they hold between them on the {basis} basis, with each "
                                "institution's own volume drawn. At two institutions the bars "
                                "diverge from a common zero, so the imbalance is the shape of the "
                                "row; the axis carries absolute counts on both sides."),
    "CAPTION_SHARED_TOTAL": "{n} topics are held by more than one of the compared institutions.",
    "EMPTY_SHARED_FRONTIER": ("No frontier topic in this cut is held by more than one of the "
                              "compared institutions, which is itself a finding: their frontier "
                              "portfolios do not meet."),

    # 2B-R re-cut of the workbook: no snapshot row, the data date instead, both
    # dynamics windows, the cap, the slider and the interval coverage.
    "XLSX_ROW_DATA": "Data from",
    "XLSX_ROW_DYNAMICS": "Dynamics windows",
    "XLSX_ROW_CAP": "Institutions compared at once, at most",
    "XLSX_ROW_TOPN": "Frontier topics plotted",
    "XLSX_ROW_CI": "Interval coverage",
    "XLSX_SHEET_OVERVIEW": "Overview",
    "XLSX_SHEET_SUBJECT_FIELD": "Fields",
    "XLSX_SHEET_SUBJECT_SUBFIELD": "Subfields",
    "XLSX_CAPTION_METRIC": ("{metric}, on the {basis} basis and the {tree} taxonomy. Every row "
                            "carries its own denominator in the last column."),

    # ======================================================================
    # Sprint 2 Phase 2B-R2, stream CP3 (2B-R2-3/4/5/8/9/10). ADDITIVE ONLY,
    # inside this dict and nowhere else in the file.
    #
    # The presentation rule every key below obeys (2B-R2-8): a `NOTE_*` key
    # is ONE short reading line -- what the chart SAYS -- and is rendered
    # through `charts_compare.chart_note`, which REFUSES a line over its own
    # character cap. A `TIP_*` key is the methodology that used to sit under
    # the chart as a grey paragraph, and is rendered inside that line's `?`.
    # The pairing is what removed the walls of prose: nothing was deleted,
    # everything moved one hover away.
    # ======================================================================

    # 2B-R2-9: the cards. The window sentence that used to sit under the whole
    # strip is now per card, inside the card's own `?`, beside the figure it
    # actually qualifies; the bootstrap-interval line is gone from the cards
    # (it stays on the impact panel, where the intervals are the subject).
    "CARD_WINDOW_TIP": "Counted over the {y0} to {y1} window.",
    "CARD_PUBS_FRAC": "On fractional counting the figure is {n}.",
    "OVERVIEW_NOTE": "One card per institution; the dot marks the highest figure on that measure.",
    "OVERVIEW_NOTE_TIP": ("Each figure names its own denominator and window in its own tooltip. A "
                          "measure an institution holds too little to support reads n/a, never "
                          "zero. Where two institutions are exactly level no dot is drawn. Each "
                          "institution name opens its own publications in OpenAlex."),

    # 2B-R2-5: the row order, and the one control that moves it.
    "SORT_LABEL": "Row order",
    "SORT_TAXONOMY": "By subject area",
    "SORT_VALUE": "Largest first",
    "SORT_HELP": ("By subject area keeps every row in the same place when the measure changes, so "
                  "two measures can be read against one another; a heavier line marks where one "
                  "subject area ends. Largest first ranks the rows by what the compared "
                  "institutions hold between them."),

    # 2B-R2-3/4: the reading line and the method behind each metric chart.
    "NOTE_SUBJECT": "One bar per institution, with its own publication count beside the row name.",
    "NOTE_ERC": "One bar per institution in each ERC research panel.",
    "NOTE_SDG": "One bar per institution under each Sustainable Development Goal.",
    "TIP_SCENARIO": "Read on the {basis} basis and the {tree} taxonomy.",
    "TIP_GUTTER": ("The figures beside each row name are that institution's own publications in "
                   "that row, each written in its own colour."),
    "TIP_REFERENCE": ("The dashed mark on a row is the average across every institution in this "
                      "index that publishes there. The world top decile behind PP(top10%) is a "
                      "different reference: it is set on world publications, per topic and year, "
                      "not on the institutions compared here."),
    # 2C (Stream VC, D2/D3): FWCI's own reference wording -- never "average"
    # (WT_2C.md claim 1: the corpus mean sits near one by construction and
    # would misread as a neutral baseline beside a median bar).
    "TIP_REFERENCE_FWCI": ("The dashed mark on a row is {ref_label}: the same statistic, a median, "
                          "over the same works as the bar, never the corpus mean, which sits near "
                          "one by construction and would misread as neutral beside a median bar."),
    # 2C AMENDMENT (D6): ONE sentence for every hatched bar app-wide, hatched
    # rather than hollow (2B-R3), and stated as a WINDOW TOTAL rather than a
    # per-year average -- PP and FWCI hatch on a window total already, and
    # the old per-year framing read as a second, different number next to it.
    "TIP_LOW_VOLUME": ("A hatched bar with a dagger rests on fewer than {floor} works over {y0} to "
                       "{y1}: the figure is real, but too thin to race against its neighbour."),
    "TIP_ACCENT": ("The mark beside each row name is that taxonomy's own colour. Colour on a bar "
                   "is always the institution."),

    # 2C (Stream VC, D5/D4): the one-line basis/floor/coverage caption every
    # ratio chart gets directly under its section title (CHROME_CONTRACT.md
    # §7). PP and FWCI state a FIXED basis (D4: pinned, never the page's
    # full/frac toggle); share/sdg_share/dynamics state the CURRENT toggle.
    # `{n}`/`{floor}` are always a real, computed value -- never hand-typed.
    "CAPTION_BASIS_PP": ("Articles and reviews, {y0} to {y1}, fixed regardless of the "
                        "counting-basis toggle; fields with at least {floor} works are scored."),
    "CAPTION_BASIS_PP_UNSCORED": ("Articles and reviews, {y0} to {y1}, fixed regardless of the "
                                 "counting-basis toggle; fields with at least {floor} works are "
                                 "scored -- {n} more fields fall below that floor and are not "
                                 "shown."),
    "CAPTION_BASIS_FWCI": ("Best-fit taxonomy, covered articles and reviews, {y0} to {y1}, full "
                          "counting, fixed regardless of the counting-basis toggle."),
    "CAPTION_BASIS_FWCI_UNSCORED": ("Best-fit taxonomy, covered articles and reviews, {y0} to {y1}, "
                                   "full counting, fixed regardless of the counting-basis toggle -- "
                                   "{n} {grain}s hold too few covered works to be scored."),
    "CAPTION_BASIS_FWCI_ERC_GAP": (" Coverage on this grain is incomplete for a measured share of "
                                  "works; the exact gap is in the icon below."),
    "CAPTION_BASIS_SHARE": "{basis} counting, {y0} to {y1}.",
    "CAPTION_BASIS_DYNAMICS": "{w1} against {w2}, {basis} counting.",

    # 2B-R2-10: the frontier map's two controls, and the pool rule in words.
    "FRONTIER_POOL_LABEL": "Topics shown",
    "FRONTIER_POOL_VOLUME": "Most published by this set",
    "FRONTIER_POOL_ELITE": "The most emerging topics only",
    "FRONTIER_POOL_HELP": ("The first pool answers where these institutions put their work; the "
                           "second answers what the fastest-moving topics are, whatever the volume "
                           "behind them. Both pools are cut on all topics in the world, so neither "
                           "moves when an institution is added or removed."),
    "FRONTIER_POOL_RULE_VOLUME": ("the pool is every topic in the global top quarter of emergence "
                                  "these institutions publish in, ranked by what they put into "
                                  "it."),
    "FRONTIER_POOL_RULE_ELITE": ("the pool is narrowed to topics in the global top tenth of "
                                 "emergence, ranked by what these institutions put into them."),
    "FRONTIER_COLOR_LABEL": "Colour by",
    "FRONTIER_COLOR_OWNER": "Who holds the topic",
    "FRONTIER_COLOR_DOMAIN": "Broad subject area",
    "FRONTIER_COLOR_HELP": ("Who holds the topic colours a bubble by the institution publishing "
                            "there alone, and greys the ones more than one of them holds. Broad "
                            "subject area colours the same bubbles by the kind of science instead, "
                            "which answers what is expanding rather than whose it is."),
    "NOTE_FRONTIER_MAP": "{n_shared} of the {n_shown} topics plotted are held by more than one of them.",
    "TIP_FRONTIER_MAP": ("One bubble per topic: {pool_rule} Bubble area is the publications the "
                         "compared set holds in it on the {basis} basis. The bold lines are the "
                         "two zero axes -- right of the vertical one attention to the topic is "
                         "expanding, above the horizontal one that expansion is itself speeding "
                         "up. At the head of the ranking almost every topic is shared, so the "
                         "colour split says little and what the plane shows is position and size."),
    "NOTE_SHARED_FRONTIER": "The topics more than one of them holds, largest first: {n} in all.",
    "TIP_SHARED_FRONTIER": ("Each institution's own publications in the topic are drawn from a "
                            "common zero on the {basis} basis, so the imbalance is the shape of "
                            "the row and the axis carries counts on both sides."),

    # 2B-R2-8: the impact, trends and coverage panels lose their grey stacks.
    "NOTE_IMPACT": "Share of each institution's articles and reviews in the world top decile of citations.",
    "TIP_IMPACT": ("Counted over the {y0} to {y1} window, against the world distribution for the "
                   "publication's own subject, year and document type; fractional counting "
                   "throughout, and {bonus_year} is left out. {ci}"),
    # 2BR3 VC item 3: the selection rule stated in plain words, not "showing
    # {n} of {n_union}" alone -- the rule is `compare_data.impact_subfields`'s
    # own floor-clearing union, read out here rather than left implicit.
    "NOTE_IMPACT_SUBFIELDS": ("Showing the {n} of {n_union} subfields where at least one institution "
                              "holds {floor} or more fractional publications."),
    "TIP_IMPACT_SUBFIELDS": ("Every subfield at least one of the compared institutions clears at "
                             "the chosen floor is in the frame. Where an institution does not "
                             "clear it the cell reads n/a: it publishes too little there to "
                             "measure, which is a different thing from a low figure. Lowering the "
                             "floor brings in more subfields and widens every interval. {ci}"),
    "NOTE_COVERAGE": "Share of each institution's whole output in each state; the states cover everything.",
    "TIP_COVERAGE": ("The states are exclusive and sum to the institution's whole fractional "
                     "output, so the classified share is what the subject, ERC and SDG views above "
                     "rest on."),

    # 2B-R2-10/5: the workbook records the controls the reader was actually on.
    "XLSX_ROW_POOL": "Frontier topics shown",
    "XLSX_ROW_COLOUR": "Frontier colours",
    "XLSX_ROW_SORT": "Row order",

    # ======================================================================
    # 2BR3 VC (plan SS1 item 1 / SS3 "VC"). The bottom meta block: the page's
    # own method sentence and the index-size/data-date line move here from
    # the header, inside one collapsible, so the first chart is visible
    # without scrolling past prose (plan SS1.5). ADDITIVE ONLY.
    # ======================================================================
    "ABOUT_HEADER": "About these figures",
}

# ----------------------------------------------------- Collaborate page ----
# 2B-7 / 2B-8: exactly two institutions, read in one direction at a time.

COLLAB = {
    "PAGE_TITLE": "Collaborate",
    "PAGE_INTRO": ("Two institutions read against each other: the topics both already publish in, "
                   "and the topics each one is absent from inside its own strongest subfields."),

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

    # ---- empty states -----------------------------------------------------
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
    # DOWNLOAD_SHARED / DOWNLOAD_GAPS DELETED 2BR3 (TEV-U wave 3 deletion
    # ledger, VL's own flag): DOWNLOAD_SHARED went dead THIS round (the
    # manual CSV button VL's rework dropped in favour of the native
    # `st.dataframe` export toolbar); DOWNLOAD_GAPS predates 2BR3 entirely
    # (the old "does not publish in" gap tables, retired 2B-R2-11f). Both
    # confirmed zero usage by grep across lib/ and tests/.
    "DEEPLINK_LABEL": "Link to this pair",

    # 2B-R-10/MU: the below-floor honest notice, additive here for stream LP's
    # own wave (BUILD_PLAN_2BR.md S3 LP row: "below-floor pair renders "
    # topline + honest notice") to reuse rather than hand-type; methods.copub
    # states the SAME floor rule in general terms, this is the per-pair
    # render. {floor} and {n_copubs} are filled by the caller from the pair's
    # own row, never typed in here.
    "TOPIC_BELOW_FLOOR_NOTICE": (
        "This pair shares {n_copubs} publications, under the floor of {floor} the topic-by-topic "
        "breakdown needs to stay readable. The total and a link to every shared publication on "
        "OpenAlex are shown below; the breakdown by topic, SDG and ERC panel is not."),

    # ======================================================================
    # 2B-R-10 / stream LP: the four-section Collaborate page. ADDITIVE only --
    # every key above stays where it is, because the shared-topics table, the
    # two gap tables and the breadth line are all still rendered, now inside
    # the third section. Every placeholder is filled by lib/views_collab.py
    # from the pair's own frames, CFG or a module constant: no number and no
    # window is typed into a string here.
    # ======================================================================
    "PAGE_INTRO_PAIR": (
        "Two institutions read as a partnership: how much they publish together and how that has "
        "moved, what the joint corpus is about, where the two portfolios meet without the joint "
        "publications having followed, and where to read every one of them."),

    # ---- section one: the relationship pulse ------------------------------
    "PULSE_HEADER": "The relationship, year by year",
    "PULSE_AXIS": "Joint publications",
    "LEGEND_JOINT": "signed by both",
    "PULSE_CHART_CAPTION": (
        "Publications signed by both institutions, counted in full, one bar per year. "
        "{bonus_year}{star} is a partial year: the snapshot was taken inside it, so its bar is drawn "
        "hollow and is not read against the full years beside it."),
    "PULSE_TOTAL_LABEL": "Joint publications",
    "PULSE_SHARE_LABEL": "Share of {name}",
    "PULSE_SHARE_DENOM": (
        "Each share divides the joint total by that institution's own full-counted output over the "
        "same window, {window}: {name_a} published {vol_a} over it and {name_b} {vol_b}. A large "
        "institution and a small one therefore read very differently on the same partnership."),
    "PULSE_RANK_LINE": (
        "**{name_b}** ranks number **{rank_of_b}** among {name_a}'s partners by joint volume; "
        "**{name_a}** ranks number **{rank_of_a}** among {name_b}'s. The two ranks answer different "
        "questions and are kept side by side rather than averaged."),
    "PULSE_TREND_UP": "Joint output ran {pct} higher per year in {w2} than in {w1}.",
    "PULSE_TREND_FLAT": "Joint output ran at much the same annual rate in {w2} as in {w1}.",
    "PULSE_TREND_DOWN": "Joint output ran {pct} lower per year in {w2} than in {w1}.",
    "PULSE_TREND_NA": "There is no joint output in {w1} to read the later years against.",
    "PULSE_TREND_NOTE": (
        "Mean annual joint publications over {w1} against {w2}, the same two windows the comparison "
        "page reads dynamics on. The partial year {bonus_year}{star} is excluded from both, and a "
        "difference smaller than {band} is reported as the same annual rate rather than as a "
        "direction."),
    "EMPTY_PULSE": (
        "{a} and {b} have signed no publication together in this snapshot. The sections below still "
        "read the two portfolios against each other."),

    # ---- section two: the joint corpus ------------------------------------
    "JOINT_HEADER": "What the two publish on together",
    "JOINT_INTRO": (
        "The joint corpus, read through the topic each shared work is primarily about, so a paper is "
        "never counted into more than one row. Only the pair's {cap} most-published shared topics are "
        "shipped, and only for pairs with at least {floor} shared works: the field and subfield "
        "rollups below sum those topics alone and are lower bounds on the whole joint corpus."),
    "JOINT_FIELDS_HEADER": "Fields of the joint corpus",
    "JOINT_SUBFIELDS_HEADER": "The same corpus by subfield",
    "JOINT_TOPICS_HEADER": "The most-published shared topics",
    "JOINT_COL_SUBFIELD": "Subfield",
    "JOINT_COL_TOPIC": "Topic",
    "JOINT_COL_VOL": "Joint publications",
    "JOINT_COL_W1": "{w1}",
    "JOINT_COL_W2": "{w2}",
    "JOINT_COL_BONUS": "{bonus_year}{star}",
    "JOINT_COL_SDG": "Tagged to a goal",
    "JOINT_WINDOW_NOTE": (
        "The two window columns are {w1} and {w2}, the windows dynamics is read on everywhere else in "
        "the tool; the starred column is the partial year and is not comparable with either."),
    "JOINT_SDG_LINE": (
        "{n_tagged} of the {n_shown} joint publications on the topics shown, {share}, carry at least "
        "one sustainable development goal."),
    "JOINT_ERC_LINE": (
        "**{panel}** is the panel most of the pair's labelled joint work lands on: {n_panel} of "
        "{n_labelled} labelled joint publications, {share}."),
    "JOINT_ERC_CAPTION": (
        "Panel shares are read of the {pct} of joint publications that carry an ERC label at all, "
        "never of the joint total, and the panel is the one most often the highest-scoring for a "
        "work rather than a funded grant."),
    "EMPTY_JOINT_ERC": "No joint publication of this pair carries an ERC label.",

    # ---- section three: untapped potential --------------------------------
    "UNTAPPED_HEADER": "Where the two overlap without publishing together",
    "UNTAPPED_CAPTION": (
        "For every topic both institutions publish in, the expected joint volume is the pair's own "
        "overall joint rate, {k}, applied to the smaller of the two institutions' volumes on that "
        "topic; the gap is that expectation minus what the pair actually published there. Only "
        "topics with a gap left over are listed, largest first."),
    "UNTAPPED_RATE_NOTE": (
        "The joint rate is the pair's joint total divided by the smaller institution's own output "
        "over {window}, so it reads as: if the two collaborated on this topic at the rate they "
        "collaborate overall, this is what would be there."),
    "UNTAPPED_COL_TOPIC": "Topic",
    "UNTAPPED_COL_SUBFIELD": "Subfield",
    "UNTAPPED_COL_VOL_SIDE": "Held by {name}",
    "UNTAPPED_COL_OBSERVED": "Published together",
    "UNTAPPED_COL_EXPECTED": "Expected together",
    "UNTAPPED_COL_GAP": "Gap",
    "EMPTY_UNTAPPED": (
        "Every topic the two share already carries as much joint output as the pair's overall rate "
        "would predict."),
    # The four keys for the "Adjacent topics in the same subfields" expander
    # (its own header, caption, and two column labels) are DELETED 2C (D8,
    # grill ruling): that expander is retired end to end -- its data-layer
    # frame, its render helper and these keys. Confirmed zero usage across
    # lib/ and tests/ by grep.

    # ======================================================================
    # 2B-R2-11 / stream LP3: the re-cut Collaborate page (field breakdown as
    # a chart, top shared topics with a slider, untapped potential with a
    # slider, and the two directional "what X does not publish in" tables
    # removed). ADDITIVE: every key above stays where it is, and the keys
    # this section does not replace are still read by the page. Every
    # placeholder is filled by lib/views_collab.py from a frame, from CFG or
    # from a module constant: no number, no window and no floor is typed
    # into a string here, and nothing here names a build code, a table or a
    # file (tests/test_forbidden_vocabulary.py scans this dict).
    # ======================================================================

    # ---- section one: the pulse, its prose folded into the chart tooltip --
    "PULSE_CHART_READING": (
        "Publications signed by both institutions, counted in full, one bar per year."),
    # D4/D5 (2C, chrome-audit fix L7): the pulse is the ONE section on this
    # page that does NOT read the articles-and-reviews window every other
    # section is pinned to -- this basis chip says so explicitly, in its own
    # caption, rather than leaving a reader to assume every chart shares one
    # basis.
    "PULSE_BASIS_CAPTION": (
        "All publication types, {w1}, full counting. Every other section on this page reads "
        "articles and reviews only, {y0} to {y1}."),
    # D4 (2C): the shared basis chip every CORE-AR section on this page
    # carries -- the field chart, the reciprocity chart, and both the topic
    # and untapped tables, all pinned to the SAME basis.
    "BASIS_CAPTION_CORE_AR": "Articles and reviews, {y0} to {y1}, full counting.",

    # ---- the pair momentum headline (2BR3 task 1) --------------------------
    # Windows, shares, counts and the significance threshold all come from
    # `collab_data.pair_momentum` / `collab_facts.json` at render time -- no
    # window and no number is typed into any of these three.
    "MOMENTUM_LABEL": "Momentum",
    # 2C chrome-audit fix (L5): the one reading line that stays visible --
    # the three evidence lines below (share, per-year rate, significance)
    # fold into this line's own tooltip instead of stacking as separate
    # captions.
    "MOMENTUM_READING": (
        "Whether the pair's co-publication rate is rising, falling or holding steady, tested for "
        "significance between two windows."),
    "MOMENTUM_EVIDENCE_SHARE": (
        "{w1}: co-publications made up {share1} of the pair's combined output {sep} {w2}: {share2}"),
    # Annual means, not raw window totals: the two windows are unequal (three
    # years vs two), so raw counts always read as a drop (manager merge fix
    # after the first live render did exactly that).
    "MOMENTUM_EVIDENCE_COPUBS": "Co-publications per year: {c1} {arrow} {c2}",
    "MOMENTUM_EVIDENCE_SIGNIFICANCE": "Significance: p = {p} (threshold {alpha})",

    # ---- section two: the joint corpus, field by field --------------------
    "FIELDS_HEADER": "The joint corpus, field by field",
    "FIELDS_CHART_READING": (
        "Publications signed by both institutions, by field, grouped under the four broad domains."),
    "FIELDS_CHART_TOOLTIP": (
        "Each joint publication is counted once, under the field its main subject belongs to, and "
        "counted in full for both sides. Every bar is coloured by its OpenAlex domain. Field mix "
        "reads the repaired subject taxonomy and does not follow the taxonomy choice in the sidebar, "
        "so it stays the same as that choice moves; the topic table below does follow it."),

    # ---- "Strategic reciprocity by field" (2BR3 task 4, Lorraine port) -----
    "RECIPROCITY_HEADER": "Strategic reciprocity by field",
    # 2C chrome-audit fix (L6): the one reading line that stays visible --
    # RECIPROCITY_HOW_TO_READ and RECIPROCITY_WHY below fold into this
    # line's own tooltip instead of standing as two separate always-visible
    # paragraphs either side of the chart.
    "RECIPROCITY_READING": (
        "Each bubble is a shared field; its position shows how central that field is to each side, "
        "its size the joint volume there."),
    "RECIPROCITY_HOW_TO_READ": (
        "How to read: each bubble is a field the pair has published in together. Its horizontal "
        "position is that field's share of {name_b}'s own portfolio; its vertical position is the "
        "same field's share of {name_a}'s own portfolio. A bubble close to the dotted line carries a "
        "similar weight on both sides; one further from it matters more to one side than the other. "
        "Bubble area is the pair's own joint publications in that field."),
    "RECIPROCITY_WHY": (
        "Why this figure: a field can be central to one partner's portfolio and only marginal to the "
        "other's. Crossing the two shares this way separates a structural partnership, where both "
        "sides already invest heavily, from a volume partnership, where the joint output is large "
        "mainly because one side is large."),
    "RECIPROCITY_AXIS_X": "Share of {name}'s own portfolio",
    "RECIPROCITY_AXIS_Y": "Share of {name}'s own portfolio",
    "RECIPROCITY_HOVER_X": "share of {name}'s portfolio",
    "RECIPROCITY_HOVER_Y": "share of {name}'s portfolio",
    "RECIPROCITY_HOVER_JOINT": "joint publications",

    # ---- section three (2BR3): the topic deep dive -------------------------
    "TOPICS_HEADER": "The topics the two publish on together",
    "TOPICS_READING": "The shared topics carrying the most joint publications, largest first.",
    "TOPICS_TOOLTIP": (
        "Each joint publication counts once, under the topic it is mainly about, so a publication is "
        "never spread over several rows. Only the pair's most-published shared topics are held, up to "
        "{cap} of them, and only for pairs with at least {floor} joint publications; the counts by "
        "goal and by panel below therefore describe the topics shown rather than the whole joint "
        "corpus. Topics roll up to the subfield the taxonomy choice in the sidebar gives them."),
    # ---- section four: the untapped reading, its formula behind the mark --
    "UNTAPPED_READING": (
        "Shared topics where the two publish less together than their own overall rate predicts."),

    "SHOW_ALL_BUTTON": "Show all {n} topics",

    # ---- the table columns shared by the topic and untapped tables --------
    "COL_TOP10": "In the world top decile",
    "COL_TOP10_DF_HELP": (
        "Share of this topic's joint publications that sit among the most-cited tenth of the world's "
        "publications on the same subject, in the same year and of the same kind. Only publications "
        "with enough citation data can be placed in that world comparison at all, so this share reads "
        "against every joint publication in the topic, not only the ones a world comparison exists "
        "for."),
    "COL_SDG_DF_HELP": (
        "Share of this topic's joint publications tagged to at least one Sustainable Development "
        "Goal."),
    "DF_COL_DOMAIN": "Domain",
    "DF_COL_FWCI": "Median FWCI",
    "COL_FWCI_HELP": (
        "Citations a joint publication in this topic has collected, relative to a European reference "
        "of the same subfield, year and document type; a value above the reference reads as more "
        "cited than that European average, one below as less. The figure shown is the median across "
        "the topic's joint publications with enough citation data. See Methods for the reference "
        "corpus and its known limits."),
    "JOINT_COL_SDG_RAW": "Tagged, count",
    "DF_COL_MOMENTUM": "Momentum",
    "DF_COL_MOMENTUM_HELP": (
        "Whether joint output in this topic is growing, shrinking or steady between the two windows "
        "the tool reads momentum on, at class grain only. See the pair's own momentum figure above "
        "for the full reading, with its percentage and its significance test."),
    # COL_LINK ("Read") / COL_LINK_DISPLAY ("Open") DELETED 2C (chrome-audit
    # fix, D10): the topic name itself is now the row's clickable link (the
    # app's one canonical name-as-link convention), not a separate trailing
    # column, so neither a link LABEL nor a fixed display string is needed
    # any more. COL_LINK_HELP survives, unchanged, as that link's own help
    # text.
    "COL_LINK_HELP": (
        "Opens the publications the two institutions signed together on this row's subject, live on "
        "OpenAlex, with the same filters this page counts on."),
    "TABLE_ROWS_NOTE": "{n_shown} rows shown of {n_total}.",

    # ---- the below-floor branch, and what this page does not show ---------
    "BELOW_FLOOR_ITEM": "This pair",
    "NOT_OFFERED_GAPS": "What each one publishes in that the other does not",
    "NOT_OFFERED_GAPS_REASON": (
        "answered better by the reading above, which starts from the ground the two already share "
        "and asks where the joint publications have not followed"),
    "NOT_OFFERED_BREADTH": "How many topics both institutions touch",
    "NOT_OFFERED_BREADTH_REASON": (
        "a single overlap figure counts a topic the same whether it carries one publication or a "
        "thousand, so the topic by topic reading above replaces it here"),
    "NOT_OFFERED_SUBFIELDS": "The joint corpus by subfield",
    "NOT_OFFERED_SUBFIELDS_REASON": (
        "the field breakdown and the topic table sit either side of it and are both complete on "
        "their own terms"),

    # ---- bottom meta, collapsed by default (2BR3 layout ruling) -----------
    "META_EXPANDER": "About these figures",
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


def _lens_concordance_table() -> str:
    """2B-R-11a/2B-R-MU: one line per lens, the DISPLAY code a reader sees on
    a tab, the lens's name, and the internal identifier the evidence column,
    the CSV export and the rest of this note still use. Built from
    `LENS_DISPLAY_CODE`/`LENS_DISPLAY_NAMES` (stream FC's own concordance key,
    `progress/2BR_FC.md`) rather than a second hand-typed list, so the two
    numberings cannot drift apart. Order follows tab order (defaults L0..L7,
    then the two optional tabs C1->L8, L7->L9). A markdown TABLE (`|---|`)
    would read fine but types a literal "--" into a copy.py string constant,
    which the VOICE rule bans outright; a bold-code list reads just as
    clearly in a rendered `st.markdown` expander and keeps the scan clean."""
    order = ["L0", "L1", "L3", "F1", "L2f", "L4", "L5", "L6", "C1", "L7"]
    lines = []
    for internal in order:
        name = LENS_DISPLAY_NAMES[internal].split(" · ", 1)[1]
        lines.append(f"**{LENS_DISPLAY_CODE[internal]}** ({internal}): {name}")
    return "\n\n".join(lines)


# 2B-R-12 / stream MU: the impact-interval coverage sentence, hoisted to
# module level so the Compare page can reuse the SAME wording next wave
# rather than a second hand-typed caption (BUILD_PLAN_2BR.md S3 CP row,
# "impact intervals with stated coverage"). `ci_coverage` and `n_bootstrap`
# are plain facts (config.yaml methods_facts / source_manifest.json), never
# typed in here; `tests/test_pages_methods.py` pins the coverage number
# against the pipeline function it is actually read off.
IMPACT_CI_CAPTION = (
    "A {ci_coverage}% bootstrap interval, from {n_bootstrap} resamples of the cell's own "
    "fractional citation mass, is shown beside every impact figure and never in place of it.")

# FWCI_NOT_AVAILABLE_LINE (2B-R2-11(c) / MU3) DELETED 2BR3 (TEV-U wave 3, MT
# sweep casualty #4): FWCI is a real, always-attempted column now (ruling 4,
# `fwci_ref.parquet` + `collab_pairs`/`collab_pair_topics`/`collab_pair_
# fields`'s own `fwci_median`), never a "not available" descope line -- the
# ONE caller (`ops/_probe_collab.py`, itself deleted this wave, superseded by
# `tests/ui/probe.py`) is gone with it. Zero other usage confirmed
# (`grep -rn "FWCI_NOT_AVAILABLE_LINE"` across lib/tests/ops).

# 2B-R2-2 / stream MU3: the colour-system rule stated once, in plain terms, so
# a future chart caption on any page can quote it rather than re-explaining
# the same convention. The rule itself: institution colour fills a mark, a
# taxonomy's own colour never does (COMPARE's CAPTION_ACCENT_ERC/_SDG already
# say the narrower, per-chart version of this same sentence).
COLOUR_SYSTEM_NOTE = (
    "One colour system runs through every page. An institution keeps one colour for as long as "
    "it stays in a comparison or a pair, drawn from a small set of light, deliberately "
    "understated hues chosen so a mark reads first as data and only second as decoration.\n\n"
    "A taxonomy, an OpenAlex domain, an ERC panel or a Sustainable Development Goal, carries its "
    "own official colour too, fixed by the body that owns it rather than chosen by this tool. "
    "That colour never fills a bar or a mark that also carries an institution's colour: it "
    "appears on a label or a small chip beside a name instead, so the two colour systems are "
    "always readable apart and never asked to share one mark.")

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
            "A share or a specialisation index built from the ERC classifier or the Sustainable "
            "Development Goals stays fractional whatever that setting says, because a share can "
            "only mean one thing at a time; a raw count from either classifier follows the setting "
            "like any other volume, named beside the figure it produced. The counting-basis section "
            "below carries the full list of figures that sit outside the setting entirely, the "
            "impact figure among them. Records whose author list is truncated by the OpenAlex list "
            "endpoint are re-fetched one at a time, so that large collaborations keep their full "
            "author list and their fractional weights stay right."),
    },
    "counting_bases": {
        "title": "Which figures follow the counting-basis setting",
        "body": (
            "One setting, full or fractional counting, reaches every volume the tool displays, on "
            "every page: the number in a chart, the number in its gutter and the number a hover "
            "names as the denominator all move together when that setting changes, so a reader is "
            "never shown two figures computed on two different bases side by side. A change over "
            "time follows the same rule: the value and the raw counts behind it are read on "
            "whichever basis is in force, never a mix of the two.\n\n"
            "A handful of figures sit outside that setting by design, and each says so where it "
            "appears. The impact figure, PP(top10%), is always read on the institution's fractional "
            "mass of articles and reviews: the citation-threshold work behind it is built on that "
            "basis and has no full-counted equivalent. The goal-tagged share this tool reports for "
            "each Sustainable Development Goal on its own, one row per goal, is likewise always "
            "fractional, over its own six-year window. The same tagging crossed with a field or a "
            "year, by contrast, now offers full counting as well as fractional, on the same window "
            "the field and year figures around it use, so the setting reaches those readings too."),
    },
    "copub": {
        "title": "How co-publication is counted",
        "body": (
            "A co-publication between two institutions is a work naming both of them directly, "
            "counted in full: a single heavily co-authored paper still adds one to the pair's "
            "total, the same way it adds one to each institution's own output under full "
            "counting. Every pair of indexed institutions with at least one shared work anywhere "
            "in the run enters the tool at all, over the same combined set of harvested records "
            "every other figure draws on; that widest count is what decides whether a pair "
            "appears, and it is also what the year-by-year relationship chart draws, one bar per "
            "year, {bonus_year} included and marked as a partial year because the snapshot was "
            "taken inside it.\n\n"
            "Every other number a partnership carries reads a narrower, matched population "
            "instead: articles and reviews only, {y0} to {y1}, still full counting. That "
            "population sits behind the joint total on a pair's own page, the topic and field "
            "breakdown, the goal-tagged share, the citation-impact figure and the momentum "
            "reading alike, and it is also the population every 'read on OpenAlex' link is "
            "filtered to, so the number on the page and the count the link opens on agree, at "
            "the level of the pair and at the level of a single topic. Each institution's rank "
            "among the other's collaborators, and the other's rank among its own, are two "
            "different numbers on this same narrower population, kept side by side rather than "
            "averaged into one.\n\n"
            "Below a pair's topic-level detail sits a floor: a breakdown by topic only means "
            "something once a pair has enough shared output, on that narrower population, to "
            "support it. Pairs with at least {collab_topic_floor} shared articles and reviews "
            "get up to {collab_topic_cap} of their most-published shared topics, ranked by joint "
            "volume and read off the work's own primary topic rather than every topic it "
            "touches, so a single paper is never counted into more than one row. A pair below "
            "that floor still shows its total and a link to every shared publication; the "
            "topic-level breakdown is left out rather than served too thin to read."),
    },
    "collab_detail": {
        "title": "Reading a pair's shared subjects",
        "body": (
            "Below the joint total, a pair's shared topics are broken down one row per topic, "
            "capped at the {collab_topic_cap} most-published ones by joint volume; a pair with a "
            "longer tail of shared subjects than that is summarised rather than shown in full. "
            "The same breakdown is rolled up to field level too, with every field the pair has "
            "any joint work in shown, however small.\n\n"
            "Two figures sit beside a topic or a field row. Covered counts the row's joint "
            "publications published between {y0} and {y1}, articles and reviews only, that fall "
            "in a subfield, year and document-type cell the world holds a citation threshold "
            "for. Of that covered count, the second figure is how many reach the world top "
            "decile of citations for their own cell. A joint publication outside a covered cell "
            "still counts in the row's own total, so the top-decile figure should always be read "
            "against covered, never against the total. The subfield behind a covered cell is "
            "always read under the best-fit taxonomy, whatever the taxonomy setting elsewhere on "
            "the page shows.\n\n"
            "A citation-impact figure sits beside them too, the field-weighted citation index "
            "(FWCI): each publication's own citation count, set against the average a "
            "publication of the same subfield, the same year and the same document type "
            "collects across the tool's own European reference corpus, the same "
            "{n_countries}-country {y0}-to-{y1} population, articles and reviews only, "
            "everywhere else in the tool draws on. A stratum too thin to support its own average "
            "falls back to the wider field, and if that is still too thin, to the year and "
            "document type alone, so every publication still receives a reading. Every topic or "
            "field row shows the median across its own covered joint publications with a valid "
            "figure, left blank under three such publications. The reference is Europe, not the "
            "world: a figure here does not compare with one built against a worldwide reference, "
            "and the usual rule that a world-referenced score averages to one does not hold for a "
            "Europe-only one. The mean-citation column this table once carried is gone; the "
            "figure above replaces it.\n\n"
            "One caveat applies at field grain only, never at topic grain. The taxonomy repair "
            "this tool reads field membership through can place a publication in a different "
            "field from the one OpenAlex's own record names as primary, so a field row's "
            "OpenAlex link can open a nearby but not always identical count to the figure beside "
            "it; a topic-level link, and the pair's own overall link, both open the exact count "
            "shown.\n\n"
            "Every topic row, every field row and the pair as a whole carries a link to "
            "OpenAlex, live, filtered to exactly the joint publications behind that row; there "
            "is no offline browsing mode for them, and the live count can drift a little from "
            "the snapshot's own, the same gap every OpenAlex link in the tool carries."),
    },
    "momentum": {
        "title": "Reading momentum",
        "body": (
            "Momentum reads whether a partnership's output is speeding up or slowing down, on "
            "the same two windows Dynamics uses elsewhere in the tool, {dynamics_window_1} "
            "against {dynamics_window_2}: the pair's own co-published output, as a share of the "
            "two institutions' combined output in each window, compared across the two.\n\n"
            "A raw comparison of those two shares would read as growth for almost every "
            "partnership, because the whole corpus is itself growing over the same years; "
            "before anything is classified, every eligible pair's ratio of the two windows is "
            "corrected against the middle of that same ratio across every other eligible "
            "partnership, so what is left over is the partnership's own change relative to the "
            "pace collaboration is moving at generally, not the corpus's own drift dressed up as "
            "a partnership finding. A partnership whose corrected ratio still moves by at least "
            "{momentum_band} either way reads as up or down; anything closer to flat than that "
            "reads as stable. An up or a down reading is checked once more, with a statistical "
            "test at the {momentum_alpha} level: a move that could plausibly be noise on that "
            "pair's own volume is relabelled not significant rather than shown as a trend.\n\n"
            "Four further states cover the partnerships a ratio cannot classify honestly: new, "
            "for a partnership with nothing in the earlier window and enough in the later one to "
            "read as a start; dormant, the same shape run backwards; weak base, for a "
            "partnership with too little in the earlier window for a ratio to mean anything; and "
            "not applicable, below the volume a comparison needs at all. None of these four "
            "carries a percentage, only the label, because none of them is a rate that can be "
            "read against the band."),
    },
    "reciprocity": {
        "title": "Strategic reciprocity, read",
        "body": (
            "Strategic reciprocity plots a pair's shared fields against how central that field "
            "is to each institution's own portfolio, not to the partnership. For each field the "
            "two publish in together, one position is that field's share of one institution's "
            "own output and the other position is the same field's share of the other's, each "
            "read against everything that institution publishes on its own, never against the "
            "joint corpus; the size of the mark is how much the two have actually published "
            "together in that field.\n\n"
            "A field sitting on the diagonal matters about as much to both sides; one far off it "
            "is central to one partner's own portfolio and marginal to the other's. The reading "
            "separates two different kinds of partnership that a joint total alone cannot tell "
            "apart: one where both sides already invest heavily in the shared ground, and one "
            "where the joint output is large mainly because one side is large."),
    },
    "colour": {
        "title": "How colour is used",
        "body": COLOUR_SYSTEM_NOTE,
    },
    "intl_company": {
        "title": "International and company co-publication shares",
        "body": (
            "Two shares sit next to the size figures on every profile and comparison. The "
            "international share is the part of an institution's output naming at least one "
            "other direct co-authoring institution based in a different country. The company "
            "share is the part naming at least one direct co-authoring institution, this one "
            "included, typed as a company. Both are full counting shares of the institution's own "
            "eligible works between {y0} and {y1}, the same window and the same denominator the "
            "size figures use.\n\n"
            "Country and type for an institution the index does not already carry come from a "
            "direct pull against OpenAlex, covering {intl_company_n_ids} identifiers and "
            "resolving {intl_company_pct_resolved} of them. An identifier OpenAlex itself cannot "
            "resolve is recorded as unknown rather than guessed foreign or domestic, company or "
            "not, and is counted as unknown rather than folded into either share as if it were "
            "zero."),
    },
    "dynamics": {
        "title": "Reading a change over time",
        "body": (
            "Dynamics compares two multi-year averages rather than one year against another: the "
            "mean annual figure over {dynamics_window_1}, against the mean annual figure over "
            "{dynamics_window_2}, shown as a percentage change from the first to the second. "
            "Averaging across each window absorbs the noise a single year would carry, and still "
            "leaves two periods short enough to read as before and after.\n\n"
            "{bonus_year} sits outside both windows and plays no part in the comparison, for the "
            "same reason it is left out of every impact figure: a year this recent has not "
            "settled into a stable count yet. Where the earlier window is empty for an "
            "institution, no percentage is shown, because a change measured against zero has no "
            "reading.\n\n"
            "A dynamics figure carries a low-volume marker whenever the earlier window's mean "
            "annual output, on the full count, sits under {low_volume_floor} publications a "
            "year: a change read off a handful of publications swings on very little evidence, "
            "and the marker says so wherever the figure is drawn, in the chart and in the gutter "
            "alike."),
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
    "lens_codes": {
        "title": "Reading the lens codes",
        "body": (
            "Every lens above is shown under a short code on its own tab, chosen to read left to "
            "right in the order the tabs appear rather than the order the lenses were built in. "
            "The table below gives each code, the lens it stands for, and the internal identifier "
            "still used in the evidence column, the CSV export and the rest of this note.\n\n"
            + _lens_concordance_table() +
            "\n\nThe ★ Aspirational tab, last in the row, sits outside this table: it carries no "
            "code of its own, because it is not a similarity lens and does not ask which "
            "institutions resemble this one. Its own question and its two modes are set out in "
            "the aspirational view section below."),
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
            "them. The definition shipped here scored highest, with the cleanest lists, and is shown "
            "first whenever it has anything to show. When it is empty, the view falls back "
            "automatically to the second-best definition, the same candidate pool ordered instead by "
            "shared presence in the topics the world is currently expanding into, and says so on the "
            "page rather than leaving the tab blank.\n\n"
            "The tab sits apart from the similarity lenses above it, marked with its own star: it "
            "does not ask which institutions resemble this one, it asks which of the subfield lens's "
            "own candidates this institution could plausibly grow into, a different question "
            "answered from thinner evidence."),
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
            "citations the threshold is built on. " + IMPACT_CI_CAPTION + " For a small "
            "institution that interval is wide enough to change the reading, and two institutions "
            "whose intervals overlap are not separated by the data.\n\n"
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
            "unscored share is visible instead of hidden.\n\n"
            "On the Compare page, the topics pooled across several institutions can be widened "
            "or narrowed by one setting. The wider pool, and the default, keeps every topic in "
            "the top quartile of frontier emergence that at least one compared institution "
            "publishes in, ranked by their combined volume. The narrower pool keeps only topics "
            "in the global top decile of frontier emergence, a fixed cut over every topic the "
            "score covers rather than over the compared institutions' own footprint, so the pool "
            "does not move when the comparison changes; it sits inside the wider pool by "
            "construction, a stricter cut on the same score."),
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
            "through the classifier at all, which the coverage view makes visible per institution.\n\n"
            "SDG mass and the size figures use different windows: the six-year snapshot from {y0} "
            "to {bonus_year} for SDG, the {y0} to {y1} window everywhere else in the tool that "
            "counts volumes. Adding up the SDG figures over the shorter window recovers only part "
            "of the six-year total, not all of it, so the two are never meant to be summed "
            "together.\n\n"
            "The comparison page crosses this same tagging with a field instead of showing it on "
            "its own, and reads a different, narrower population again: see 'The SDG-tagged "
            "share, by field' below."),
    },
    "sdg_field_share": {
        "title": "The SDG-tagged share, by field",
        "body": (
            "Beside the field and subfield figures on the comparison page sits a further "
            "reading: the share of each field's own output that carries at least one "
            "Sustainable Development Goal. A publication counts once toward that share no "
            "matter how many goals it carries, so, unlike the per-goal shares above, this one "
            "cannot run past the whole. Numerator and denominator are read over the exact same "
            "population, the {y0}-to-{y1} window, every document type, and whichever counting "
            "basis is set on the page, so the share is provably no more than the field's own "
            "total.\n\n"
            "This is a different reading from the per-goal shares above: those are read over the "
            "wider six-year snapshot and can add up past the whole because a work with several "
            "goals counts toward each of them; this one is read at field grain, over the "
            "narrower window shared with the rest of the comparison page, and counts a work "
            "once."),
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
            "the institution's own record and applied; {n_gated} cases sit unresolved at the "
            "moment this page was built, held back where a single source could not settle the "
            "call rather than corrected on a guess.\n\n"
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
    "collab_topic_floor": "measured live: smallest copubs_total among pairs shipped in collab_pair_topics.parquet",
    "collab_topic_cap": "measured live: largest number of topic rows shipped for any one pair in collab_pair_topics.parquet",
    "intl_company_n_ids": "config.yaml methods_facts.intl_company_n_ids (the institution-metadata pipeline pull, outside the app repo)",
    "intl_company_pct_resolved": "config.yaml methods_facts.intl_company_pct_resolved, formatted as a percent",
    "dynamics_window_1": "docs/data_contract.yaml window_conventions block, the earlier dynamics window, verbatim",
    "dynamics_window_2": "docs/data_contract.yaml window_conventions block, the later dynamics window, verbatim",
    "ci_coverage": "config.yaml methods_facts.impact_ci_coverage_pct (the pipeline bootstrap alpha, outside the app repo)",
    "low_volume_floor": "lib.charts_compare.LOW_VOLUME_FLOOR, the same value the Compare dynamics low-volume marker uses",
    "momentum_band": "measured live: data/collab_facts.json band value, formatted as a percent",
    "momentum_alpha": "measured live: data/collab_facts.json alpha value, formatted as a percent",
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

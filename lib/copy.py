"""
app/lib/copy.py -- every user-facing string in the Find tab (Sprint 2 Phase
2A, Stream F). Constants only: no classes, no Streamlit import, no rendering.

RULE (BUILD_PLAN_2A.md Stream F build step 5 / L10 "no static string asserts
a value"): no digit character appears anywhere in a string constant below
except inside a lens code (L0, L1, L2f, L3, L4, L5, L6, L7, F1, C1) or the
literal "top10" / "PP(top10%)". Every other number a caption needs (a count,
a threshold, a share, a median) is a `{named}` format placeholder the CALLER
fills from CFG or the live data -- never typed here. `scan_for_digit_violations`
at the bottom is the self-check; `tests/test_badges.py` runs it.
"""
from __future__ import annotations

import re

# --------------------------------------------------------- lens glosses -----
# Source: VIZ_SPEC.md S2.4 / INDICATOR_SPEC_v2.md S1, verbatim except every
# digit replaced by a named placeholder (the caller fills it from CFG/data).

LENS_GLOSS = {
    "L0": "Field-grain overlap -- the coarsest shape, {n_fields} OpenAlex fields",
    "L1": "Subfield overlap -- the anchor lens",
    "L3": "Topic overlap -- the workhorse lens for broad recall",
    "F1": "Frontier-topic overlap",
    "L2f": "Shared specialisations (a floor of {floor_papers} papers per cell)",
    "L4": "ERC panel overlap",
    "L5": "ERC specialisation",
    "L6": "SDG profile overlap",
    "C1": "Core-shape -- L1 restricted to the seed's own top-{core_top_n} subfields",
    "L7": "Experimental SDG-specialisation view",
}

LENS_CAVEAT = {
    "L0": "Generic look-alikes for concentrated profiles; moderate outlier crowding among the defaults",
    "L1": "Safe to read to rank {depth_max}",
    "L3": "Same-country clustering is noticeably higher on this lens (hence the country post-filter tooltip on this tab)",
    "F1": "Under-represents Social Sciences & Humanities profiles",
    "L2f": "The failure axis is a diffuse profile, not raw institution size -- reads well for concentrated "
           "mid-size institutions, poorly for very diffuse or very thin ones",
    "L4": "Occasional company/governance leakage into the candidate set",
    "L5": "Kept because it surfaced peers no other lens found, with less external corroboration than the "
          "other defaults; read its candidates with that in mind",
    "L6": "Country clustering is modest on this lens -- not a peer-finding artefact",
    "C1": "A refinement of L1, not a sibling of L7; noise grows faster than L1's past rank {core_top_n}",
    "L7": "Mostly noise, occasionally unique -- kept for the rare peer no other lens surfaces",
}

# ------------------------------------------------------------ toggles -------

L7_TOGGLE_LABEL = "Show an experimental SDG-specialisation view -- mostly noise, occasionally unique"
C1_TOGGLE_LABEL = "Restrict to my core subfields"
VERDICT_LINE = "Candidates for review, not a verdict."

# ------------------------------------------------------------ tooltips ------

BASIS_NOT_APPLIED_TOOLTIP = ("ERC and SDG lenses (L4, L5, L6, L7) are fractional-only; "
                              "this toggle does not change them.")
L3_COUNTRY_TOOLTIP = ("This lens has the highest same-country clustering of the default lenses "
                       "({share} of its top candidates share the seed's country); "
                       "the country filter is worth a look here specifically.")
UMBRELLA_BADGE_LABEL = "umbrella / aggregate (EXPERIMENTAL)"
UMBRELLA_TOOLTIP = ("EXPERIMENTAL: this row's size is far above the {median} country-and-type median it is "
                     "compared against. Known umbrellas, not an exhaustive list.")
CATCHALL_TOOLTIP = "Share of this institution's mass sitting in catch-all (out-of-scope) topics: {share}."

# --------------------------------------------------------------- strip ------

STRIP_PREFIX = "Filtered by: "
STRIP_JOIN = " · "  # middle dot, VIZ_SPEC S1.4's own separator
STRIP_TREE = "tree = {tree}"
STRIP_BASIS_FULL = "basis = full (not applied to the ERC/SDG lenses)"
STRIP_DEPTH = "depth = {depth}"
STRIP_C1_ON = "core-shape restriction on"
STRIP_L7_ON = "experimental SDG-specialisation view on"
STRIP_TYPE = "type = {types}"
STRIP_COUNTRY = "country = {countries}"
STRIP_EXCLUDE_OWN_COUNTRY = "excluding the seed's own country"
STRIP_SIZE_RANGE = "size range {lo}-{hi} works"
STRIP_SCALE_GUARD = "scale guard on"
STRIP_FAMILY = "family filter on (L0 score at or above {threshold})"

# --------------------------------------------------------- empty states -----

SEARCH_EMPTY_TEMPLATE = "No institution matches '{query}'. Check the spelling, or try an acronym."
EMPTY_STATE_JOIN = " and "
NO_ACTIVE_FILTER_LABEL = "the active filters"
EMPTY_STATE_TEMPLATE = ("No candidates match {filters} for {seed}. "
                         "Remove a filter, or increase depth to see more.")
UNDEFINED_LENS_TEMPLATE = "{lens} is undefined for this seed: {reason}."
CONCORDANCE_CAPTION = "Found in the top-{N} of {k} of {n} lenses defined for this seed."

# ----------------------------------------------------------- depth/export ---

DEPTH_CAPTION_TEMPLATE = "showing top {n} of {m} ranked -- search the tail or download"
EXPORT_BUTTON_LABEL = "Download full ranking (CSV)"
TAIL_SEARCH_EMPTY_TEMPLATE = "'{query}' does not appear anywhere in this lens's ranking for this seed."
ADD_COMPARATOR_HELP = "Add a comparator by name"

# ---- Find page (moved from lib/views_find.py EXTRA_COPY, Stream X1 2026-08-29) ----

FIND = {
    "SCENARIO_HEADER": "Scenario",
    "TREE_LABEL": "Subfield tree",
    "BASIS_LABEL": "Counting basis",
    "DEPTH_HEADER": "Depth",
    "DEPTH_LABEL": "Rows shown per lens",
    "OPTIONAL_HEADER": "Optional lenses",
    "L7_HEADER": "Experimental view",
    "FILTERS_HEADER": "Post-filters",
    "FILTERS_HELP": "Applied after ranking: they remove rows, they never change a rank.",
    "TYPE_LABEL": "Institution type",
    "COUNTRY_LABEL": "Country",
    "EXCLUDE_OWN_LABEL": "Exclude the seed's own country",
    "SIZE_LABEL": "Size range (full works)",
    "SCALE_GUARD_LABEL": "Scale guard (comparable size band)",
    "SCALE_GUARD_HELP": ("Keeps candidates within a size ratio of the seed; the ratio is banded "
                          "by the seed's own size."),
    "FAMILY_LABEL": "Family filter (field-grain overlap)",
    "FAMILY_HELP": "Keeps candidates whose L0 field-grain overlap with the seed is at or above {threshold}.",
    "BASKET_HEADER": "Basket",
    "BASKET_EMPTY": "No comparators added yet -- use the add button under any table.",
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
    "CARD_SIZE_FULL": "Size (full counting)",
    "CARD_SIZE_FRAC": "Size (fractional counting)",
    "CARD_HHI": "Concentration",
    "CARD_BREADTH": "Breadth (subfields)",
    "CARD_DENOM_CAPTION": ("Works published {y0}{dash}{y1}. Full counting credits a whole work to the "
                            "institution; fractional counting credits its author share. Concentration "
                            "is the subfield HHI ({hhi_value}); breadth is the number of subfields present."),
    "CARD_TOP_FIELDS": "Top fields",
    "CARD_TOP_SUBFIELDS": "Top subfields",
    "CARD_EVIDENCE": "Coverage evidence for this seed",
    "EV_L2F": "Eligible subfield cells for L2f: {value}",
    "EV_SDG": "SDG-tagged share of works: {value}",
    "EV_ERC": "ERC-classified share of fractional mass: {value}",
    "EV_FRONTIER": "Frontier top-quartile share: {value}",
    "EV_CATCHALL": "Catch-all (out-of-scope) topic share: {value}",
    "CARD_PP": "PP(top10%): {pp} [{lo}{dash}{hi}]",
    "CARD_PP_CAPTION": ("Share of the institution's fractional output in the world top decile of its own "
                         "citation distribution, with its bootstrap interval -- never the point estimate alone."),
    "LINK_OPENALEX": "OpenAlex works",
    "LINK_ROR": "ROR",
    "LINK_HOMEPAGE": "Homepage",
    "TAB_OVERVIEW": "Overview",
    "TAB_ASPIRATIONAL": "Aspirational",
    "OVERVIEW_INTRO": ("Candidates that several independent lenses agree on. Order here is agreement, "
                        "not a score."),
    "CONCORDANCE_EMPTY": ("No candidate is found by more than one of the lenses defined for this seed. "
                           "Open the single-lens tabs instead."),
    "BASIS_DISCLOSURE": "This lens is fractional-only: the counting-basis toggle does not change it.",
    "EVIDENCE_LABEL": "Evidence for this seed {sep} {text}",
    "EV_NONE": "No lens-specific evidence line for this seed.",
    "ADD_SELECTED": "Add selected rows to basket",
    "ADD_SELECTED_NONE": "Select rows in the table above, then use this button.",
    "TAIL_SEARCH_LABEL": "Search the full ranking (beyond the rows shown)",
    "TAIL_CAPTION": "Matches anywhere in this lens's ranking, with their original rank.",
    "POP_CAPTION": "Ranked against {n_pop} institutions in the index, the seed excluded.",
    "ASP_INTRO": ("Candidates already found by L1 whose impact interval sits entirely above the seed's. "
                   "Kept in L1-overlap order."),
    "ASP_SORT_LABEL": "Sort by PP(top10%) instead of L1 overlap",
    "ASP_EMPTY": "No L1 candidate's impact interval sits fully above {seed}'s in the pool.",
    "ASP_UNDEFINED": ("The aspirational view needs a defined L1 ranking and a PP(top10%) value with an "
                       "interval for the seed; one of them is missing here."),
    "ASP_CAPTION": "{n_rows} candidates clear the interval test, out of {n_pool} in the L1 pool considered.",
    "COL_RANK": "Rank",
    "COL_INSTITUTION": "Institution",
    "COL_WORKS": "OpenAlex works",
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
    "DEPTH_HELP": ("Sets how many rows are shown per lens. A display cutoff only -- "
                   "the full ranking is always computed and can be downloaded regardless "
                   "of this setting."),
    "C1_HELP": ("Restricts the anchor lens (L1) to the seed's own top-{core_top_n} subfields, "
                "for a tighter reading of its core specialisation."),
    "L7_HELP": ("An experimental view, off by default: most of what it surfaces is noise, "
                "with an occasional peer no other lens finds."),
    "POSTFILTERS_EXPANDER": "Post-filters (applied after ranking)",

    # L17/L18: the profile section that replaces the old seed card.
    "PROFILE_HEADER": "Profile",
    "TILE_SIZE_FULL": "Size (full)",
    "TILE_SIZE_FULL_SUB": "works {y0}{dash}{y1}, whole work credited",
    "TILE_SIZE_FRAC": "Size (fractional)",
    "TILE_SIZE_FRAC_SUB": "author-share credited",
    "TILE_HHI": "Concentration",
    "TILE_HHI_SUB": "{hhi_class} {sep} subfield HHI, higher means more concentrated",  # manager edit 2026-08-29: the value slot already shows the HHI number (E2 needs_change #2)
    "TILE_BREADTH": "Breadth",
    "TILE_BREADTH_SUB": "subfields with at least {floor} fractional works",
    "TILE_SDG": "SDG-tagged share",
    "TILE_SDG_SUB": "of SDG-eligible works, any keyword hit",
    "TILE_FRONTIER": "Frontier top-quartile share",
    "TILE_FRONTIER_SUB": "of frontier-scorable output",
    "TILE_PP": "PP(top10%)",
    "TILE_PP_SUB": "[{lo}{dash}{hi}] bootstrap interval, articles and reviews",
    "COVERAGE_LINE": ("ERC-classified share {erc} {sep} SDG-tagged share {sdg} {sep} "
                       "catch-all share {catchall} {sep} L2f-eligible subfields {l2f}"),
    "WORDCLOUD_CAPTION": "Subfields {sep} size = works on the current counting basis, colour = domain",

    # Yearly breakdown pair (L17 block 4): one segmented control swaps the
    # global + per-year charts between a domain view and a document-type view.
    "BREAKDOWN_CONTROL_LABEL": "Break down by",
    "BREAKDOWN_DOMAIN": "Domain",
    "BREAKDOWN_DOCTYPE": "Document type",
    "BREAKDOWN_GLOBAL_TITLE": "Overall breakdown",
    "BREAKDOWN_YEARLY_TITLE": "Yearly breakdown",
    "BONUS_YEAR_CAPTION": "{year} is a bonus year: volume only, excluded from impact indicators",

    # L17 block 5: the six collapsed chart panels.
    "PANEL_FIELDS": "Fields",
    "PANEL_SUBFIELDS": "Top subfields",
    "PANEL_TOPICS": "Top topics",
    "PANEL_FRONTIER": "Frontier positioning",
    "PANEL_SDG": "SDG profile",
    "PANEL_ERC": "ERC profile",

    # L20: the shared sort toggle every bar-chart panel carries.
    "SORT_LABEL": "Sort by",
    "SORT_VOLUME": "Volume / share",
    "SORT_TAXONOMY": "Taxonomy order",

    # L20 panel captions.
    "CAPTION_SI": ("SI = share divided by the mean share across institutions active in "
                   "that cell; dashed line = parity"),
    "CAPTION_SI_FLOOR": "SI shown only for cells with at least {floor} fractional works",
    "CAPTION_TOPICS_CATCHALL": "{n} of the topics shown are catch-all (out-of-scope) topics, flagged {glyph}",
    "CAPTION_FRONTIER": ("Frontier scores measure attention dynamics, not novelty or quality; "
                          "low can mean foundational. {n_excluded} topics are excluded or "
                          "unscored and do not appear."),
    "CAPTION_SDG": ("Shares of SDG-tagged output; a work can carry several SDGs, so shares "
                    "need not sum to one. SDG {n_missing} is not covered. Matches reflect the "
                    "SIRIS classifier's reading of the SDGs; different classifiers disagree "
                    "substantially."),
    "CAPTION_ERC": ("Shares of ERC-classified output over {n_panels} panels; the Biotechnology "
                     "and Arts panels have low recall, read them with care"),
    "FRACTIONAL_ONLY_PANEL": "This panel is fractional-only: the counting-basis toggle does not change it",

    # ---- Refinement R1, added by stream R-E2 (the page that composes the
    # above). Additive only: every key below is a string R-F2's set did not
    # carry and the composed page needs (BUILD_PLAN_2A.md S9.3 R-E2 fence).

    # The benchmark half of the page -- the section the controls row heads.
    "BENCHMARK_HEADER": "Benchmark",
    "BENCHMARK_INTRO": ("Candidate peers, ranked by each lens independently. The controls "
                        "below govern every tab."),

    # L23 / gate-2A bug #9: the works link carries the harvest's own
    # server-side filters, so it counts the same corpus the app does -- give
    # or take the drift between a live query and a frozen snapshot.
    "LINK_OPENALEX_HELP": ("Live OpenAlex count with the same filters as the snapshot; "
                           "expect a small difference"),

    # The yearly breakdown's residual series: works the topic table cannot
    # place in a domain (they carry no primary topic). Shown, never hidden,
    # so the domain and document-type views sum to the same yearly total.
    "UNCLASSIFIED_LABEL": "Unclassified",
    "BREAKDOWN_DOCTYPE_MISSING": ("No document-type rows for this institution in the "
                                  "snapshot; showing the domain breakdown instead."),

    # Empty states for the profile section's own blocks (VIZ_SPEC S1.6: an
    # explicit reason, never a blank panel and never a silent gap).
    "WORDCLOUD_EMPTY": "No subfield mass for this institution under the current scenario.",
    "PANEL_EMPTY": "No data for this panel under the current scenario.",
    "FRONTIER_EMPTY": ("No topic of this institution carries a frontier score, so there is "
                       "nothing to place on the two axes."),

    # The displayed cut of the two "top N" panels, stated parametrically
    # (VIZ_SPEC S2.16: "the depth of the cut is stated in the panel caption").
    "CAPTION_TOP_N_VOLUME": ("Showing the top {n} subfields by works on the current counting "
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

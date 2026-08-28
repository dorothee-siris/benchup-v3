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
    "L3": "Topic overlap -- the workhorse, highest recall of all {n_named_lenses} lenses",
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
    "L1": "Safe to read to rank {depth_max}; the most consistently informative lens across seeds",
    "L3": "Highest same-country clustering of any lens (country post-filter tooltip shown on this tab specifically)",
    "F1": "Under-represents Social Sciences & Humanities profiles",
    "L2f": "The failure axis is a diffuse profile, not raw institution size -- reads well for concentrated "
           "mid-size institutions, poorly for very diffuse or very thin ones",
    "L4": "Occasional company/governance leakage into the candidate set",
    "L5": "The lens with the thinnest external corroboration of the {n_default_lenses} defaults -- kept "
          "because it still surfaced peers no other lens found; read its candidates with that in mind",
    "L6": "Country clustering below L1's -- not a peer-finding artefact",
    "C1": "A refinement of L1, not a sibling of L7; noise grows faster than L1's past rank {core_top_n}",
    "L7": "Mostly noise, occasionally unique -- the worst judged read of any lens/mode this cycle; kept "
          "for the rare peer no other lens surfaces",
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

# ----------------------------------------------------- digit-ban self-check -

_ALLOWLIST_RE = re.compile(
    r"\bL0\b|\bL1\b|\bL2f\b|\bL3\b|\bL4\b|\bL5\b|\bL6\b|\bL7\b|\bF1\b|\bC1\b|top10|PP\(top10%\)"
)


def scan_for_digit_violations() -> list[tuple[str, str]]:
    """Every string constant above (dict values included), digits allowed only
    inside the allowlisted lens codes / top10 / PP(top10%). Returns
    (constant_name, offending_value) pairs; empty list = PASS."""
    violations = []
    for name, value in globals().items():
        if name.startswith("_") or not name.isupper():
            continue
        candidates = value.values() if isinstance(value, dict) else [value]
        for v in candidates:
            if not isinstance(v, str):
                continue
            if re.search(r"\d", _ALLOWLIST_RE.sub("", v)):
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

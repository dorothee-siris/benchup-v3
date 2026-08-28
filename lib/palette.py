"""BenchUp v3 - the ONE legal source of colour for the app.

Every hex below is validated (design-system/palette_validation.txt) and carries
a provenance comment. No other file under app/lib/ (this one excepted),
app/pages/ or app/Menu.py may contain a "#RRGGBB" literal -- app/tests/test_palette.py
scans for that and fails the build if one appears.

SIRIS house rule (CLAUDE.md): light mode only, full width. This file ships no
dark-mode variants and no [data-theme] branches -- there is exactly one palette.

Design lineage: Studio RULES.md §4 colour formula (Okabe-Ito derived identity
set, k<=5) + COMPOSITION_AND_CONTROLS.md's "highlight-plus-mute beats more
colours" + Lorraine Phase 2 Streamlit/lib/helpers.py palette-section convention
(DOMAIN_COLORS / NEUTRAL_GREY / NA_MARK naming and comment style).
"""

# ---------------------------------------------------------------------------
# Validator provenance (full log: design-system/palette_validation.txt)
# ---------------------------------------------------------------------------
# Run 1 (2026-08-29, dataviz skill scripts/validate_palette.js, --mode light
# ONLY per house rule): FOCAL + the 4 non-education type-identity hues below,
# 5 slots -> ALL CHECKS PASS (lightness band, chroma floor, normal-vision
# floor all PASS; two WARN advisories -- CVD #CC79A7<->#009E73 dE 7.6 deutan,
# and #CC79A7 contrast 2.98:1 -- both carried as BINDING requirements: every
# type badge in this app ships with a visible text label, never a bare colour
# fill, which is exactly the "secondary encoding" / "binding relief" the
# validator asks for).
#
# Run 2 (same date) confirms, by design, that COMPARISON/NEUTRAL/INK do NOT
# belong in the categorical set: run together they FAIL the lightness and
# chroma floors (they read as achromatic grey/near-white/near-black, which is
# exactly their job -- neutral fill and text ink, never an identity). This is
# the same finding class RULES.md §4 already documents for #333333 ("fails the
# palette validator as a series colour -- TEXT ONLY"), reproduced here for
# BenchUp v3's own hexes before locking them in below.

# ---------------------------------------------------------------------------
# Focal / comparison / neutral / ink
# (RULES §4 colour formula: "1 focal + 1 comparison + 1 neutral + k identities")
# ---------------------------------------------------------------------------

FOCAL = "#0072B2"
# The seed institution ONLY -- highlight-plus-mute pattern (COMPOSITION_AND_CONTROLS.md
# Control layer #6: "selection and search paint the focal entity in the focal colour and
# grey the rest"). Reserved exclusively for the seed row/mark in every view: it is NEVER
# reused as a type-identity colour (see TYPE_COLORS below) precisely because an
# education-type seed would otherwise share its own highlight colour with every other
# education-type candidate row in the same ranked table, destroying the "which row is
# the seed" read. Validator: PASS, run 1, 2026-08-29, light.

COMPARISON = "#8C9196"
# Grey: candidate rows, reference bars, "rest of the ranking" -- a NEUTRAL, not an
# identity. Same hex as Lorraine Streamlit/lib/helpers.py's NEUTRAL_GREY (helpers.py:108)
# and RULES.md's "comparison/reference" grey. Deliberately excluded from the categorical
# validator (fails the chroma floor by design, chroma 0.009 -- reads as achromatic); its
# WCAG check is against actual usage (fills/bars with a text label alongside, never body
# text) -- see palette_validation.txt run 2 disposition.

NEUTRAL = "#E6E8EB"
# Background / unclassified fill (RULES §4: "Background/unclassified is #E6E8EB, not the
# low end of the scale"). Table zebra striping, empty-state panels, disabled controls.
# Never a categorical identity; never the low end of a sequential ramp (BenchUp v3 ships
# no sequential/quantitative colour scale in Phase 2A -- no heatmap/choropleth view).

INK = "#333333"
# TEXT ONLY. Validator FAILS it as a series colour (chroma 0, outside the lightness/
# chroma band) -- the exact amendment RULES.md §4 carries from Lorraine's chain pass 3
# ("#333333 is TEXT INK, never a series colour"). NEVER assign INK to a mark, bar, dot,
# or badge fill; it is body text, table copy, labels, captions. Contrast on white:
# 12.6:1 (floor is 4.5:1) -- see palette_validation.txt run 2 disposition.

# ---------------------------------------------------------------------------
# Institution-type identity set -- the ONE stable app-wide categorical, k<=5
# ---------------------------------------------------------------------------
# Okabe-Ito derived set per RULES §4: #0072B2 #D55E00 #009E73 #CC79A7 #6A3D9A.
# Validator: PASS, run 1, 2026-08-29, light (FOCAL + the 4 hues below, 5 slots
# together -- they appear in the same ranked table, so they must be validated
# as one set, not two).
#
# DECISION -- does `education` share FOCAL blue, or get its own colour? NEITHER.
# `education` carries NO identity colour at all (plain text in the type column,
# no dot/chip fill). One-line justification: education is the base-rate expected
# type for a peer-benchmarking candidate list (evals/campaign_v2/lists/*.md shows
# the overwhelming majority of rows on every lens are `education` -- e.g. 47/50
# of Gdansk's L1 top-50, 0/13 companies+facilities excepted on IFPEN's more
# heterogeneous L0/L1); the identity set exists to flag the candidates worth a
# second look -- a facility, a healthcare provider, a government body or funder,
# or the "other" catch-all -- per COMPOSITION_AND_CONTROLS.md Control layer #6
# ("highlight-plus-mute beats more colours") and the brief's own framing
# ("candidates are neutral unless a type identity is shown in a badge/column").
# This also removes the FOCAL-collision risk described in the FOCAL comment above.
#
# Assignment order below keeps #009E73 and #CC79A7 NON-adjacent, per RULES §4's
# explicit instruction ("keep #009E73 and #CC79A7 non-adjacent in assignment
# order (deutan dE 7.6 when adjacent)").

TYPE_COLORS = {
    "education": None,               # no identity colour -- base rate, unflagged (see decision above)
    "facility": "#D55E00",           # vermillion -- specialised research institutes, national labs
    "healthcare": "#009E73",         # bluish green
    "other": "#6A3D9A",              # dark violet -- collapsed: company, nonprofit, archive, other
    "government+funder": "#CC79A7",  # reddish purple -- BINDING RELIEF (2.98:1 on white, validator
                                      # WARN): NEVER render as a bare fill/dot without its text label.
}

NA_MARK = "n/a"
# D53 / L8 convention (Lorraine Streamlit/lib/helpers.py:111 NA_MARK): a missing
# indicator is "n/a", never 0 and never a blank string. See INDICATOR_SPEC_v2.md
# §5/§8 and BUILD_PLAN_2A.md L11 ("n/a never 0").

# ---------------------------------------------------------------------------
# Status colours
# ---------------------------------------------------------------------------
# RULES §4: "never encode good/bad as red/green alone." BenchUp v3 Phase 2A ships
# no good/bad or momentum/trend read (that is a Lorraine-specific indicator,
# explicitly out of scope here -- INDICATOR_SPEC_v2.md §4 carries no status
# dimension). No constant is defined here deliberately (ponytail: no unused
# colour). If a future phase adds one, define it here with text+glyph, never
# colour alone, and re-run the validator before shipping.


def type_group(type_str: str) -> str:
    """Map a raw (or type-patched) OpenAlex `type` string to one of the 5
    app-wide identity groups keying TYPE_COLORS.

    Callers MUST cast the source column with `.astype(str)` before mapping
    (BUILD_PLAN_2A.md global dispatch rule, WT #36: categorical columns are
    compared/mapped as str, never as a pandas Categorical dtype directly).
    """
    t = str(type_str).strip().lower()
    if t == "education":
        return "education"
    if t == "facility":
        return "facility"
    if t == "healthcare":
        return "healthcare"
    if t in ("government", "funder"):
        return "government+funder"
    return "other"  # company, nonprofit, archive, other, and anything unrecognised

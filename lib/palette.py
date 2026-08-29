"""BenchUp v3 - the ONE legal source of colour for the app.

Every hex below is validated (design-system/palette_validation.txt) and carries
a provenance comment. No other file under app/lib/ (this one excepted),
app/pages/ or app/Menu.py may contain a "#RRGGBB" literal -- app/tests/test_palette.py
scans for that and fails the build if one appears.

SIRIS house rule (CLAUDE.md): light mode only, full width. This file ships no
dark-mode variants and no [data-theme] branches -- there is exactly one palette.

Design lineage: Studio RULES.md section 4 colour formula + COMPOSITION_AND_CONTROLS.md's
"highlight-plus-mute beats more colours" + Lorraine Phase 2 Streamlit/lib/helpers.py
palette-section convention (DOMAIN_COLORS / NEUTRAL_GREY / NA_MARK naming and
comment style) + BenchUp V2 `domain_color` inheritance pattern.

--- THE FOUR IDENTITY FAMILIES (BUILD_PLAN_2A.md L19, refinement R1) --------
    OA_DOMAIN_COLORS   4 OpenAlex domains; fields, subfields and topics INHERIT
                       their domain's colour (the tree decides the ancestry, so
                       the colours follow the tree/basis toggles for free).
    ERC_DOMAIN_COLORS  3 ERC domains (PE / LS / SH) -- the ERC panel view.
    SDG_COLORS         the 17 official UN goal colours (16 used; 17 unused).
    DOCTYPE_COLORS     5 document types = the harvest's corpus types.

COEXISTENCE RULE (binding; VIZ_SPEC.md section 1.1): **one identity family per
chart**. A chart is coloured by OA domain, OR by ERC domain, OR by SDG, OR by
document type -- never two families at once, and never a family plus FOCAL.
`FOCAL` is the seed-institution highlight in the ranked/comparison views only;
it NEVER appears in a domain-, SDG-, ERC- or doctype-coloured chart (the whole
profile section describes ONE institution, so there is nothing to highlight
against -- painting one bar FOCAL there would assert a comparison that the
chart does not make). The yearly-breakdown pair swaps domain <-> document type
through a segmented control: exactly one family is on screen at a time and the
chip legend is rebuilt on every swap, which is what makes the two families'
mutual validator distance a NON-requirement (see palette_validation.txt run 6).
"""

# ---------------------------------------------------------------------------
# Validator provenance (full log with every command + verbatim output:
# design-system/palette_validation.txt). All runs: dataviz skill
# scripts/validate_palette.js, `--mode light` ONLY per the SIRIS house rule.
# ---------------------------------------------------------------------------
# Run 1 (2026-08-29, stream D0): FOCAL + the 4 institution-type hues -> ALL
#   CHECKS PASS. The type-identity set was DELETED in R1 (see the removal note
#   at the bottom of this file); the run is kept in the log because FOCAL's own
#   PASS line comes from it.
# Run 2 (2026-08-29, stream D0): COMPARISON/NEUTRAL/INK together -> expected
#   FAIL, documenting that they are chrome, never identities.
# Run 3 (2026-08-29, R1/R-D2): the 4 OA domain hues alone -> FAIL on the fixed
#   hue #FFCB3A (lightness 0.865, above the 0.43-0.77 band) + contrast WARN.
#   These hexes are FIXED by lineage (BenchUp V2 / Lorraine DOMAIN_COLORS) and
#   by the R1 brief; the run is DESCRIPTIVE and the two findings are carried as
#   binding relief rules, never as a reason to change a hex.
# Run 4 (2026-08-29, R1/R-D2): the 3 ERC hues alone, `--pairs all` -> ALL CHECKS
#   PASS (worst CVD 8.8 protan, worst normal-vision 20.3, all contrasts >= 3:1).
# Run 5 (2026-08-29, R1/R-D2): OA(4) + ERC(3) together, `--pairs all`, the
#   co-occurrence the R1 brief asks for -> every ERC hue clears every check and
#   the worst ALL-PAIRS normal-vision distance in the 7-slot set is 20.3
#   (i.e. every OA<->ERC pair is >= 20.3, far above the >= 12 requirement) and
#   every ERC-involving CVD pair is >= 8.1. The only FAIL/WARN lines are the
#   three pre-existing fixed-OA findings from run 3 plus the fixed OA pair
#   #F85C32<->#0CA750 (deutan 7.6).
# Run 6 (2026-08-29, R1/R-D2): DOCTYPE(5, i.e. Lorraine's 4 + the new `letter`
#   hue) alone, `--pairs all` -> ALL CHECKS PASS. Then DOCTYPE(5) + OA(4)
#   together -> FAIL, entirely on two PRE-EXISTING fixed pairs that do not
#   involve the new hue (#667900 book <-> #0CA750 Life, normal 13.1; #667900
#   <-> #F85C32 Health, protan 3.3). Disposition: the coexistence rule above --
#   the two families are never on screen together. The NEW hue #A10A4E clears
#   OA by minimum normal-vision 24.0 / minimum CVD 17.5 on its own.
# Run 7 (2026-08-29, R1/R-D2): the 17 UN SDG hexes, `--pairs all` -> FAIL,
#   DESCRIPTIVE ONLY. The UN fixes these colours; a validator finding is never a
#   reason to change one. Relief is structural instead (see SDG_COLORS).
# Run 8 (2026-08-29, R1/R-D2): the chrome tokens INK_SECONDARY/BORDER/GRID ->
#   expected FAIL, same class as run 2: chrome, never an identity.

# ---------------------------------------------------------------------------
# Focal / comparison / neutral / ink
# (RULES section 4 colour formula: "1 focal + 1 comparison + 1 neutral + k identities")
# ---------------------------------------------------------------------------

FOCAL = "#0072B2"
# The seed institution ONLY, and ONLY in the ranked/comparison views --
# highlight-plus-mute (COMPOSITION_AND_CONTROLS.md Control layer #6). Never
# appears in a chart coloured by one of the four identity families above
# (coexistence rule, module docstring). Also mirrored, and ONLY there, by
# `.streamlit/config.toml` theme.primaryColor, which Streamlit uses to paint
# ProgressColumn bars, links and buttons -- tests/test_palette.py pins the two
# together. Validator: PASS, run 1, 2026-08-29, light.

COMPARISON = "#8C9196"
# Grey: candidate rows, reference bars, "rest of the ranking", and the
# UNCLASSIFIED / unknown slot of every identity family (`domain_color` returns
# it for an unknown domain id) -- a NEUTRAL, not an identity. Same hex as
# Lorraine Streamlit/lib/helpers.py NEUTRAL_GREY (helpers.py:108). Deliberately
# excluded from the categorical validator (fails the chroma floor BY DESIGN,
# chroma 0.009 -- it reads as achromatic, which is the job); its WCAG check is
# against actual usage (fills/bars that always carry a text label alongside,
# never body text) -- palette_validation.txt run 2 disposition.

NEUTRAL = "#E6E8EB"
# Background / unclassified fill (RULES section 4: "Background/unclassified is
# #E6E8EB, not the low end of the scale"). Table zebra striping, empty-state
# panels, disabled controls, KPI tile background. Never a categorical identity;
# never the low end of a sequential ramp (BenchUp v3 ships no sequential colour
# scale -- no heatmap, no choropleth).

INK = "#333333"
# TEXT ONLY. Validator FAILS it as a series colour (chroma 0, outside the
# lightness band) -- the exact amendment RULES.md section 4 carries from
# Lorraine's chain pass 3. NEVER assign INK to a mark, bar, dot or badge fill.
# Contrast on white: 12.6:1 (floor 4.5:1) -- palette_validation.txt run 2.

SURFACE = "#FFFFFF"
# The chart surface: every figure's `paper_bgcolor` and `plot_bgcolor`. It is
# also the `--surface` argument every R1 validator run was executed against
# (runs 3-8), so the contrast column of those runs describes the surface the
# app actually paints, not the skill's off-white default #fcfcfb.

# ---------------------------------------------------------------------------
# Chrome tokens -- text and furniture, EXCLUDED from categorical validation
# by design (same class as COMPARISON / NEUTRAL / INK; palette_validation.txt
# run 8 reproduces the expected FAIL for these three exact hexes before they
# are locked in here).
# ---------------------------------------------------------------------------

INK_SECONDARY = "#5A5F66"
# Secondary text: KPI-tile sublines, chart annotations (the volume gutter), chip
# legend labels, axis tick labels, table footnotes. Lorraine Phase 2's own
# secondary ink. Contrast on SURFACE: 6.43:1 (measured, run 8) -- above the 4.5:1 body-text floor,
# so it is legal for small text, which is exactly what it is for. NEVER a mark.

BORDER = "#E3E6EA"
# 1 px hairline: KPI tile border, expander and panel edges, table rules. A
# furniture line, never a data mark and never text.

GRID = "#D9DDE2"
# Plot gridlines and the zero line (Lorraine plot_global_breakdown_h's
# gridcolor). Recessive by construction -- RULES section 3 "recessive grid/axes";
# it must never compete with a bar it sits behind.

NA_MARK = "n/a"
# D53 / L8 convention (Lorraine Streamlit/lib/helpers.py:111 NA_MARK): a missing
# indicator is "n/a", never 0 and never a blank string. See INDICATOR_SPEC_v2.md
# section 5/section 8 and BUILD_PLAN_2A.md L11 ("n/a never 0"). In a chart, a
# missing SI/ESI value is rendered as NO MARK AT ALL plus this text in the row's
# hover -- never a dot at zero, never a dot at one.

# ---------------------------------------------------------------------------
# FAMILY 1 -- OpenAlex domains (and, by inheritance, every field, subfield and
# topic). Provenance: BenchUp V2 `DOMAIN_COLORS` / Lorraine Phase 2
# Streamlit/lib/helpers.py:45-53, hue-for-hue. FIXED by the R1 brief.
# ---------------------------------------------------------------------------
# Validator run 3 (the four alone) and run 5 (with ERC), `--mode light
# --surface #FFFFFF --pairs all`. Run 3 is DESCRIPTIVE -- these hexes are
# inherited, not chosen, and two findings are carried as BINDING relief rules
# rather than fixed:
#   (a) [FAIL] lightness band: #FFCB3A sits at L 0.865, above the 0.43-0.77
#       band. Relief: Social Sciences is never a bare fill on white -- every
#       bar/segment carries the category name on the axis beside it and a
#       1 px SURFACE gap ring (VIZ_SPEC section 1.1), and the wordcloud draws
#       its Social Sciences words on a white ground at >= 9 pt weight, never as
#       a thin hairline.
#   (b) [WARN] contrast vs surface: #FFCB3A 1.52:1 and #8190FF 2.85:1, both
#       below 3:1 -- "relief required (visible labels or table view)". Satisfied
#       identically: every chart in the profile section is a labelled chart
#       (axis category names) and every panel ships the same numbers as a table
#       through the CSV export. Not dismissable, hence written here.
#   (c) [WARN] CVD: #F85C32 <-> #0CA750 deutan 7.6 (the 6-8 floor band). Legal
#       ONLY with secondary encoding, which the axis labels provide; the two are
#       also non-adjacent in the fixed display order below (Life, Social,
#       Physical, Health -> green, yellow, periwinkle, orange).

OA_DOMAIN_COLORS = {
    1: "#0CA750",   # Life Sciences -- green
    2: "#FFCB3A",   # Social Sciences -- yellow (lightness-band FAIL, relief (a)+(b) above)
    3: "#8190FF",   # Physical Sciences -- periwinkle (contrast WARN, relief (b) above)
    4: "#F85C32",   # Health Sciences -- orange-red
}

OA_DOMAIN_ORDER = (1, 2, 3, 4)
# The fixed taxonomy order (never a data-dependent sort) used by the "taxonomy"
# sort mode, by the chip legend, and by the yearly breakdown's series order.


def domain_color(domain_id) -> str:
    """Colour for an OpenAlex domain id -- the ONE inheritance point.

    Fields, subfields and topics have no colour of their own: they take their
    domain's (BenchUp V2 `get_field_color` pattern). Because the ACTIVE TREE
    decides which subfield -- and therefore which field and domain -- a topic
    rolls up to, colours follow the tree x basis toggles with no extra code.

    Unknown, missing or unclassified (domain_id 0 / None / NaN) -> COMPARISON
    grey: an unclassified item is a neutral, never a fifth identity.
    """
    try:
        key = int(domain_id)
    except (TypeError, ValueError):
        return COMPARISON
    return OA_DOMAIN_COLORS.get(key, COMPARISON)


# ---------------------------------------------------------------------------
# FAMILY 2 -- ERC domains (PE / LS / SH). THREE NEW hues, chosen here.
# ---------------------------------------------------------------------------
# Requirement (R1 brief): normal-vision Delta E >= 12 from EVERY OA hue,
# CVD-safe within the set, contrast adequate for a filled bar carrying a text
# label. Method: candidates screened pairwise against the four OA hues with the
# dataviz validator's own `validate()` (design-system/ab/screen_erc.mjs, output
# in palette_validation.txt run 4a), then the surviving triad validated ALONE
# (run 4) and TOGETHER WITH THE FOUR OA HUES (run 5), `--pairs all`.
#
# RESULT for the triad below: alone -> ALL CHECKS PASS (worst all-pairs CVD 8.8
# protan, above the 8.0 target; worst all-pairs normal-vision 20.3; all three
# contrasts >= 3:1, the lowest being #8A5A00 at 5.93:1). With the four OA hues
# (7 slots, all pairs) -> the worst all-pairs normal-vision distance in the
# WHOLE set is 20.3, so EVERY OA<->ERC pair clears the >= 12 requirement by a
# factor of ~1.7; every ERC-involving CVD pair is >= 8.1. The 7-slot run's only
# FAIL/WARN lines are the fixed-OA findings (a)/(b)/(c) above.
#
# The strategy that made it work, stated so a future edit does not undo it: the
# OA quartet lives in the LIGHT-to-mid band (L 0.63-0.87); the ERC triad is
# deliberately a DARK triad (L 0.45-0.55) on three hue angles OA does not use
# (deep blue, deep magenta, dark ochre). Lightness carries most of the
# separation, which is the one axis that survives every kind of CVD.
#
# REJECTED CANDIDATES (all measured, none eyeballed -- run 4a table):
#   #B07A00 mid-gold      -- CVD 2.4 vs #F85C32 (Health): collapses under protan.
#   #C24E00 burnt orange  -- normal-vision 11.4 vs #F85C32: below the >= 12 bar.
#   #00706B dark teal     -- chroma 0.085, below the 0.1 floor (reads grey), and
#                            normal-vision 14.6 vs #1F4E9C inside the triad.
#   #00566E dark teal-blue-- chroma 0.08 FAIL + CVD 5.8 vs the magenta slot.
#   #5E5C00 dark olive    -- chroma 0.1 exactly at the floor -> FAIL.
#   #B5197C bright magenta-- CVD 5.5 vs #1F4E9C inside the triad (protan).
#   #A31A6E magenta       -- passes, but CVD 8.1 vs #1F4E9C: a thinner margin
#                            than the chosen #9B1B6B's 8.8, so it loses on the
#                            only criterion that separated them.
#   #4B2E83 deep violet   -- the best single hue measured (normal 31.2 / CVD
#                            29.8 vs OA) but REJECTED for a different reason: it
#                            is one hue family away from #7838B6 (doctype
#                            book-chapter) and from #8190FF (OA Physical), and
#                            the ERC panel sits two expanders below the doctype
#                            breakdown -- a sequential-memory collision the
#                            validator cannot measure. #1F4E9C keeps the blue
#                            slot far from both.

ERC_DOMAIN_COLORS = {
    "PE": "#1F4E9C",   # Physical Sciences & Engineering -- deep blue.  vs OA: min normal 25.8, min CVD 24.5, contrast 7.99:1
    "LS": "#9B1B6B",   # Life Sciences -- deep magenta.                 vs OA: min normal 25.7, min CVD 19.1, contrast 7.60:1
    "SH": "#8A5A00",   # Social Sciences & Humanities -- dark ochre.    vs OA: min normal 21.2, min CVD 10.0, contrast 5.93:1
}

ERC_DOMAIN_ORDER = ("PE", "LS", "SH")
# Fixed ERC display order (the panel codes run PE1-11, LS1-9, SH1-8).

ERC_DOMAIN_LABELS = {
    "PE": "Physical Sciences and Engineering",
    "LS": "Life Sciences",
    "SH": "Social Sciences and Humanities",
}


def erc_color(erc_domain) -> str:
    """Colour for an ERC domain code. Unknown -> COMPARISON grey."""
    return ERC_DOMAIN_COLORS.get(str(erc_domain).strip().upper(), COMPARISON)


# ---------------------------------------------------------------------------
# FAMILY 3 -- the UN Sustainable Development Goals.
# ---------------------------------------------------------------------------
# SOURCE: the official UN goal colours as supplied by the R1 brief. A live
# cross-check against un.org's communications-material page (2026-08-29) CONFIRMS
# the governing document -- "Sustainable Development Goals Guidelines for the use
# of the SDG logo including the colour wheel and 17 icons", the August 2019
# edition (SDG_Guidelines_AUG_2019_Final.pdf), since revised September 2023 --
# but that page publishes the downloadable assets, not the hex table, so the
# values below are recorded as: **manager-supplied, matching the 2019 UN
# guidelines as commonly published**. They are FIXED by the UN and are not the
# app's to choose.
#
# Validator run 7 (all 17, `--pairs all`) FAILS, and that is DESCRIPTIVE ONLY --
# never a reason to change a hex. Findings, recorded because they are real and
# because the relief they oblige is structural:
#   * [FAIL] lightness band: #FCC30B (goal 7) L 0.845, #FD9D24 (11) L 0.777,
#     #19486A (17) L 0.387.
#   * [FAIL] chroma floor: #19486A 0.077 (goal 17 -- STORED BUT UNUSED here).
#   * [FAIL] CVD + normal-vision: worst pair #FD9D24 (11) <-> #DDA63A (2),
#     normal Delta E 5.3, protan 1.3. The UN palette simply contains two very
#     similar ambers, plus a third (#BF8B2E, goal 12) 11.8 from #FD9D24.
#   * [WARN] contrast: six hues below 3:1 (#DDA63A, #26BDE2, #FCC30B, #FD6925,
#     #FD9D24, #56C02B).
# RELIEF (binding, VIZ_SPEC section 2.11): the SDG panel is a labelled bar chart
# in FIXED goal order -- every bar carries its goal number and short label on
# the axis, so colour is brand recognition and never the encoding; identity is
# never colour-alone. That is exactly the secondary encoding the CVD floor asks
# for, and it holds for the amber trio as well as for everything else.

SDG_COLORS = {
    1: "#E5243B",   # No Poverty
    2: "#DDA63A",   # Zero Hunger
    3: "#4C9F38",   # Good Health and Well-being
    4: "#C5192D",   # Quality Education
    5: "#FF3A21",   # Gender Equality
    6: "#26BDE2",   # Clean Water and Sanitation
    7: "#FCC30B",   # Affordable and Clean Energy
    8: "#A21942",   # Decent Work and Economic Growth
    9: "#FD6925",   # Industry, Innovation and Infrastructure
    10: "#DD1367",  # Reduced Inequalities
    11: "#FD9D24",  # Sustainable Cities and Communities
    12: "#BF8B2E",  # Responsible Consumption and Production
    13: "#3F7E44",  # Climate Action
    14: "#0A97D9",  # Life Below Water
    15: "#56C02B",  # Life on Land
    16: "#00689D",  # Peace, Justice and Strong Institutions
    17: "#19486A",  # Partnerships for the Goals -- STORED BUT UNUSED: the SDG
                    # classifier does not cover goal 17, so the panel renders
                    # goals 1-16 only and says so (never a silent absence).
}

SDG_UNCOVERED = (17,)
# The goal(s) the classifier does not cover. Read by the SDG panel's caption so
# the exclusion is stated from data, not typed into a string.


def sdg_color(sdg_number) -> str:
    """Colour for an SDG goal NUMBER (one-based). Unknown -> COMPARISON grey."""
    try:
        key = int(sdg_number)
    except (TypeError, ValueError):
        return COMPARISON
    return SDG_COLORS.get(key, COMPARISON)


# ---------------------------------------------------------------------------
# FAMILY 4 -- document types (the harvest's five corpus types).
# ---------------------------------------------------------------------------
# Provenance: Lorraine Phase 2's pass-6 DOCTYPE palette (Streamlit/lib/helpers.py
# :92-99), which was itself validated all-pairs light against Lorraine's copy of
# the same OA domain hues -- four of the five hexes are taken over unchanged.
# The fifth, `letter`, is NEW for BenchUp (Lorraine's corpus had conference
# papers where BenchUp's has letters); it reuses Lorraine's `#A10A4E`, the hue
# that slot's own validated palette already carried, rather than inventing one.
#
# Validator run 6a (the five alone, `--pairs all`) -> ALL CHECKS PASS: worst CVD
# 8.2 deutan (#A55F8F <-> #22A2BD, both pre-existing), worst normal-vision 15.0
# (#A10A4E <-> #A55F8F), every contrast >= 3:1. The new hue on its own clears
# the OA quartet by min normal-vision 24.0 / min CVD 17.5.
#
# Run 6b (the five WITH the four OA hues, 9 slots) FAILS -- on two pre-existing
# pairs that do NOT involve the new hue: #667900 (book) <-> #0CA750 (Life),
# normal 13.1; #667900 <-> #F85C32 (Health), protan 3.3. Disposition: the
# COEXISTENCE RULE in the module docstring. The yearly-breakdown pair shows
# EITHER the domain series OR the document-type series, chosen by one segmented
# control, with the chip legend rebuilt on each swap -- the two families are
# never simultaneously on screen, never in one legend, and never in one figure,
# so a 9-slot simultaneous-discrimination result is not the test this palette
# has to pass. It is recorded rather than suppressed because the swap does put
# them in sequential memory, and a future editor must not "fix" it by giving
# the doctype family a second, chart-dependent set of hues.
# REJECTED for `letter`: #C24E00 burnt orange (CVD 4.0 vs #667900 book);
# #1F4E9C (CVD 4.3 / normal 14.0 vs #7838B6 book-chapter -- and it is the ERC PE
# hue, which the coexistence rule would rather keep unambiguous); #8A5A00 (CVD
# 3.0 / normal 10.1 vs #667900 -- two ochres in one legend).

DOCTYPE_COLORS = {
    "article": "#22A2BD",        # teal-blue  (Lorraine pass-6 "Articles")
    "review": "#A55F8F",         # mauve      (Lorraine pass-6 "Reviews")
    "book": "#667900",           # olive      (Lorraine pass-6 "Books")
    "book-chapter": "#7838B6",   # violet     (Lorraine pass-6 "Book chapters")
    "letter": "#A10A4E",         # deep crimson -- NEW for BenchUp (run 6a)
}

DOCTYPE_ORDER = ("article", "review", "book", "book-chapter", "letter")
# Fixed corpus order (never a data-dependent sort) -- the series order of the
# yearly breakdown and of the chip legend when the doc-type family is selected.

DOCTYPE_LABELS = {
    "article": "Articles",
    "review": "Reviews",
    "book": "Books",
    "book-chapter": "Book chapters",
    "letter": "Letters",
}


def doctype_color(doc_type) -> str:
    """Colour for a document type. Unknown -> COMPARISON grey."""
    return DOCTYPE_COLORS.get(str(doc_type).strip().lower(), COMPARISON)


# ---------------------------------------------------------------------------
# Status colours
# ---------------------------------------------------------------------------
# RULES section 4: "never encode good/bad as red/green alone." BenchUp v3 ships
# no good/bad or momentum read (INDICATOR_SPEC_v2.md section 4 carries no status
# dimension), so no status constant is defined here deliberately (ponytail: no
# unused colour). The nearest thing the app has -- a catch-all (811) topic and a
# top-quartile frontier topic -- is flagged by SHAPE, not by hue: the catch-all
# topic keeps its own domain colour at reduced opacity plus a glyph in its
# label, and a top-quartile frontier topic keeps its domain colour with a
# SURFACE-coloured outline. Both are secondary encodings on top of the family
# colour, never a new colour.

MUTED_OPACITY = 0.35
# Fill opacity for a flagged-but-included item (the catch-all topics). It is a
# transparency, not a hex, so it composites over SURFACE and stays inside the
# one-family rule.

OUTLINE_WIDTH = 2
# Marker outline width for a top-quartile frontier topic (drawn in SURFACE, the
# "2px surface ring on overlapping marks" spacer from the dataviz mark specs).


# ---------------------------------------------------------------------------
# REMOVED in R1 (2026-08-29): TYPE_COLORS and type_group()
# ---------------------------------------------------------------------------
# BUILD_PLAN_2A.md L22 removes the badge column from every table (user ruling
# #8 at gate 2A: "badge column not relevant, the type filter exists"), which
# left the institution-type identity set with no consumer. A grep over the whole
# app before deletion --
#     grep -rn "TYPE_COLORS|type_group" --include=*.py --include=*.md app/
# -- returned ONLY lib/palette.py itself, tests/test_palette.py, and two prose
# lines in design-system/DESIGN_TOKENS.md. No live code path referenced either
# symbol, so both were deleted rather than kept as dead colour (ponytail: no
# unused colour). Institution type is now carried in the tables as plain text in
# its own column and as a post-filter; the seed's own type sits in the profile
# header beside its badges. The five hexes (#D55E00, #009E73, #CC79A7, #6A3D9A
# and the deliberate `education: None`) are recorded in palette_validation.txt
# run 1 and in this comment, so restoring them needs no new validator run --
# only a new consumer and a line in the R1 progress file.

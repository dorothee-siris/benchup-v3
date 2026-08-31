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

--- THE FIVE IDENTITY FAMILIES (BUILD_PLAN_2A.md L19 + 2B-1) ----------------
    OA_DOMAIN_COLORS   4 OpenAlex domains; fields, subfields and topics INHERIT
                       their domain's colour (the tree decides the ancestry, so
                       the colours follow the tree/basis toggles for free).
    ERC_DOMAIN_COLORS  3 ERC domains (PE / LS / SH) -- the ERC panel view.
    SDG_COLORS         the 17 official UN goal colours (16 used; 17 unused).
    DOCTYPE_COLORS     5 document types = the harvest's corpus types.
    INSTITUTION_COLORS 3 institution identity slots -- COMPARE AND COLLABORATE
                       ONLY (Phase 2B / 2B-1, shrunk to three by 2B-R2-2). The
                       one family whose meaning is per-page rather than app-wide:
                       a slot names "the second institution in this basket",
                       never a fixed entity. It ships a SECOND array,
                       `INSTITUTION_COLORS_DARK`, which is not a second family:
                       each entry is the SAME HUE as its fill, dark enough to be
                       read as TEXT (value labels, legend text, the KPI dot's
                       caption) -- the relief the fills' contrast WARN obliges.

Plus ONE ordered ramp, which is NOT an identity family:
    GREY_STATE_COLORS  5 sequential neutral steps for the grey-accounting
                       states of the coverage strip (an ORDINAL severity, so it
                       takes a one-hue ramp, not categorical hues).

COEXISTENCE RULE (binding; VIZ_SPEC.md section 1.1 and section 2 ter): **one
identity family per chart**. A chart is coloured by OA domain, OR by ERC
domain, OR by SDG, OR by document type, OR by institution -- never two families
at once, and never a family plus FOCAL.
`FOCAL` is the seed-institution highlight in the ranked/comparison views only;
it NEVER appears in a domain-, SDG-, ERC- or doctype-coloured chart (the whole
profile section describes ONE institution, so there is nothing to highlight
against -- painting one bar FOCAL there would assert a comparison that the
chart does not make). In COMPARE and COLLABORATE the rule bites the other way
round (2B-1): the institution IS the identity, so the categorical axis names
the field / panel / goal / quadrant and the colour names the institution --
never a domain-, ERC-, SDG- or doctype-coloured mark in the same figure. The
yearly-breakdown pair swaps domain <-> document type
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
# Run 9 (2026-08-29, 2B/V): INSTITUTION_COLORS, the six in SHIPPED SLOT ORDER,
#   `--pairs all` -> ALL CHECKS PASS (worst all-pairs normal-vision 15.6, worst
#   all-pairs CVD 7.6 deutan). Two WARNs carried as binding relief, never as a
#   reason to change a hex: (i) #CC79A7 <-> #009E73 deutan 7.6 sits in the 6-8
#   floor band -> legal ONLY with secondary encoding, which every Compare view
#   supplies three times over (the row label on the axis, the institution chip
#   legend, the per-mark hover naming the institution); (ii) #56B4E9 2.31:1 and
#   #E69F00 2.25:1 contrast vs SURFACE are below 3:1 -> "relief required
#   (visible labels or table view)", satisfied by the same labels plus the CSV
#   and xlsx exports of every panel.
# Run 9b (2026-08-29, 2B/V): the k = 2, 3, 4, 5 PREFIXES -- the sets actually
#   drawn when the basket is smaller than six. k=2 and k=3 -> ALL CHECKS PASS
#   with NO warning at all (worst CVD 11.0, worst normal 25.8, every contrast
#   >= 3:1); k=4 and k=5 -> ALL CHECKS PASS with the deutan 7.6 WARN only; the
#   contrast WARN appears only at k >= 5. The slot ORDER below was chosen to
#   make that true (see the ordering note in the family section).
# Run 10 (2026-08-29, 2B/V): the six WITH the four OA domain hues (10 slots),
#   `--pairs all` -> expected FAIL: #F85C32 <-> #D55E00 protan 3.5 and #0CA750
#   <-> #009E73 normal 6.0. DISPOSITION: the COEXISTENCE RULE -- a Compare or
#   Collaborate chart is coloured by institution and by nothing else, so the two
#   families are never in one figure and never in one legend. Recorded rather
#   than suppressed, because the Compare page does scroll past domain-coloured
#   panels in Find, i.e. the two families share SEQUENTIAL memory.
# Run 11 (2026-08-29, 2B/V): the six WITH the chrome pair FOCAL + COMPARISON
#   (8 slots) -> FAIL, entirely on COMPARISON #8C9196 (chroma 0.009; #8C9196
#   <-> #CC79A7 normal 12.2 / deutan 3.0), which is the run-2 exclusion class
#   restated, not a new finding. FOCAL contributes NO failing pair: its nearest
#   institution hue is #6A3D9A at normal 15.6 / CVD 6.9 (screening matrix,
#   design-system/ab/screen_inst.mjs), above the normal-vision floor and inside
#   the 6-8 CVD band -- legal here because FOCAL is never a MARK on a Compare
#   page (it paints Streamlit chrome: buttons, links, ProgressColumn bars) and
#   is never in the same figure as an institution dot.
# Run 12 (2026-08-29, 2B/V): GREY_STATE_COLORS. The CATEGORICAL run FAILS by
#   design (five neutrals: chroma floor, and adjacent normal-vision 7.8) --
#   exactly what the validator's own scope line says to expect, "for a sequential
#   ramp, lightness monotonicity". The ORDINAL validator (`validateOrdinal`, the
#   same module) is the applicable one and returns OK on all four of its checks:
#   lightness monotone light->dark, every adjacent dL >= 0.06, light-end contrast
#   2.14:1 (floor 2:1), single hue (spread 4 degrees).
# Run 13 (2026-08-30, 2B-R/VS): the k = 3 COMPARE prefix alone (#D55E00,
#   #009E73, #6A3D9A), `--pairs all` -> ALL CHECKS PASS with no warning at all
#   (worst CVD 11.0 deutan, worst normal 25.8, every contrast >= 3:1). 2B-R-4
#   caps Compare at three institutions, so this -- not the k = 6 run 9 -- is the
#   set the new Compare figures actually draw.
# Run 14 (2026-08-30, 2B-R/VS): the SHARED-FRONTIER candidate screen. Every
#   candidate was validated as {k = 3 institutions} + FOCAL + candidate,
#   `--pairs all`, so any FAIL involving the candidate is the candidate's
#   (FOCAL's own pre-existing deutan 6.9 vs #6A3D9A is the run-11 finding
#   restated). REJECTED, all measured:
#     #2E75B6 -> passes the 4-slot set but is FOCAL's twin: normal DeltaE 2.3 /
#               protan 1.3 vs #0072B2. FOCAL paints Streamlit's own buttons and
#               links ON THE COMPARE PAGE, so this is a same-screen collision,
#               not a sequential one. The strongest candidate, rejected anyway.
#     #0E7C9E -> normal 14.0 vs #009E73 (below the 15 floor).
#     #386CB0 -> normal 13.0 / deutan 6.7 vs #6A3D9A.
#     #A6761D -> protan 2.4 / normal 9.4 vs #D55E00.
#     #005F73, #00796B, #0B7285, #00838F, #2C6E49 -> chroma 0.081-0.095, below
#               the 0.1 floor (they read grey), and #0B7285/#00838F also collide
#               with FOCAL (normal 7.3 / 8.5).
#     #8A5A00 -> normal 14.3 vs #D55E00 (and it is the ERC SH hue).
#     #1F4E9C -> protan 1.7 / normal 10.8 vs #6A3D9A (and it is the ERC PE hue).
#     #7A7A7A -> chroma 0, plus deutan 4.6 vs #009E73: a grey "shared" mark
#               would also read as the COMPARISON unknown slot.
#     #6B8E00 -> deutan 3.6 vs #D55E00, normal 10.1 vs #009E73.
#     #B5197C -> protan 5.7 vs #6A3D9A.
#     #B03060, #AD1457 -> both PASS the 8-slot run, and both lose to #C2185B on
#               the one criterion that separated them: distance to the crimson
#               NEIGHBOURHOOD this app already owns (see run 16).
# Run 15 (2026-08-30, 2B-R/VS): the WINNER #C2185B with the six institution
#   slots + FOCAL (8 slots), `--pairs all` -> ALL CHECKS PASS. The only WARN
#   lines are the two pre-existing ones from run 9 (#CC79A7 <-> #009E73 deutan
#   7.6; #56B4E9 2.31:1 and #E69F00 2.25:1 contrast). #C2185B itself is in no
#   failing or warning pair: its nearest institution hue is #CC79A7 at normal
#   17.8 / deutan 14.9, and #6A3D9A at normal 19.9 / protan 11.7.
# Run 16 (2026-08-30, 2B-R/VS): #C2185B against the CRIMSON NEIGHBOURHOOD, the
#   run that decided the winner. Pairwise, `--pairs all`:
#       vs #CC79A7 (institution slot 4)  normal 17.8 / deutan 14.9  PASS
#       vs #6A3D9A (institution slot 3)  normal 19.9 / protan 11.7  PASS
#       vs #9B1B6B (ERC LS)              normal  8.8 / protan  6.1  FAIL
#       vs #A10A4E (doctype letter)      normal  7.4 / protan  6.0  FAIL
#   The two FAILs are DISPOSED OF by the coexistence rule, exactly as runs 6b
#   and 10 are, and the disposition is checkable rather than asserted: the
#   doctype family renders ONLY in the Find yearly breakdown, and the ERC hues
#   render ONLY as LABEL ACCENTS (see the label-accent section below), never as
#   a mark and never in the frontier map, which is the one figure `SHARED_FRONTIER`
#   paints. The two families and this hue are never in one figure or one legend.
#   #C2185B was preferred over #B03060 (normal 5.8 / 6.5 to the same two) and
#   #AD1457 (3.0 / 5.1) because it maximises that minimum distance -- the
#   sequential-memory margin is the only thing that separated three hues which
#   all passed every check.
# Run 17 (2026-08-30, 2B-R/VS): the k = 3 institution slots + the 3 ERC accent
#   hues (6 slots), the co-occurrence `fig_metric_bars(level="erc")` creates ->
#   FAIL (#1F4E9C <-> #6A3D9A protan 1.7 / normal 10.8). DESCRIPTIVE, and the
#   reason the label-accent rule below is written as narrowly as it is: the ERC
#   hue is never a MARK in that figure, only a glyph in the row LABEL, so the
#   two are never two marks a reader has to tell apart. Recorded rather than
#   suppressed because they ARE on screen together. **SUPERSEDED by run 25** --
#   the 2B-R2 palette moves BOTH families and the same co-occurrence now PASSES.
#
# --- PHASE 2B-R2 (2026-08-31, stream VS3). Runs 18-25 were the ONE colour
#     rework of that phase: a light pastel institution trio (L = 0.77, the top
#     of the lightness band) replacing the original six-hue Okabe-Ito set, plus
#     the ERC family's move to #6A3D9A/#009E73/#D55E00. Full numbers for that
#     trio (now RETIRED, 2B-R3 -- see the "PHASE 2B-R3" block below the family
#     section) are in git history and `design-system/palette_validation.txt`;
#     the ERC-family result (runs 23-24, still current) is: ERC trio ALONE ->
#     ALL CHECKS PASS (worst CVD 11.0 deutan, worst normal 25.8); ERC trio +
#     SHARED_FRONTIER (4 slots) -> ALL CHECKS PASS, one WARN (SHARED_FRONTIER
#     <-> ERC-LS deutan in the 6-8 band, relief unchanged: ERC hues are row
#     LABEL glyphs only, SHARED_FRONTIER is a different figure's mark, both
#     name themselves in words). Run 25 (pastel institution trio + ERC trio,
#     6 slots) turned run 17's same-screen protan FAIL into a PASS -- the
#     historical reason the two families' 2B-R2 rework shipped together; that
#     specific pastel-vs-ERC number no longer applies to the 2B-R3 navy trio
#     and is superseded by the 2B-R3 runs below.

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

# ---------------------------------------------------------------------------
# 2B-R2-2 REPLACES THE THREE HEXES ABOVE (2026-08-31, stream VS3).
# ---------------------------------------------------------------------------
# The dark triad #1F4E9C / #9B1B6B / #8A5A00 was chosen (above) to be far from
# the OA quartet, and it was -- but it collided with the INSTITUTION family it
# has to share a screen with (run 17: #1F4E9C <-> #6A3D9A protan 1.7 / normal
# 10.8, "descriptive"), and it was a fourth dark saturated triad in an app that
# already had three. 2B-R2-2 hands ERC the Okabe-Ito trio the institution family
# vacates: #D55E00 / #009E73 / #6A3D9A. Legality was never in question (run 23 =
# run 13: ALL CHECKS PASS, no warning), and the same-screen collision is GONE
# (run 25: the two families together now PASS, worst normal 18.7).
#
# WHICH DOMAIN GETS WHICH -- the A/B 2B-R2-2 asks for, measured, not eyeballed
# (`design-system/ab/screen_erc_2br2.mjs`; renders
# `design-system/ab/2br2_erc_{a,b}_1280.png`). The only thing that can make an
# assignment WRONG is what a reader carries over from the OA-coloured Find page,
# so each of the six permutations was scored as
#     sum over PE/LS/SH of [ mean normal-vision distance to the OA domains that
#     mean something ELSE  -  distance to the OA domain that means the SAME ]
# i.e. a hue should sit CLOSE to its semantic twin in the OA palette and FAR
# from the domains it could be mistaken for. The winner wins by a chasm:
#     PE violet / LS green / SH vermillion   score  32.8   <- SHIPPED
#     PE violet / LS vermillion / SH green   score  -0.0
#     PE vermillion / LS green / SH violet   score  -7.1   <- the plan's listing order
#     PE green / LS violet / SH vermillion   score  -7.8
#     PE vermillion / LS violet / SH green   score -21.0
#     PE green / LS vermillion / SH violet   score -26.7
# Read: LS green is 6.0 from OA Life Sciences green and 28.7 from everything
# else -- the same meaning wearing nearly the same colour in both taxonomies,
# which is recognition rather than confusion; PE violet is 24.4 from OA Physical
# periwinkle (the same blue-violet neighbourhood) and 39.6 from the rest. SH is
# the weak leg in EVERY permutation (twin 26.9 vs others 21.7 for vermillion)
# because OA Social Sciences is yellow and none of the three hues is: no
# assignment can fix that, and the row label naming the panel in full is what
# carries SH, exactly as the label-accent rule below requires.
# NOTE the plan's listing order (PE/LS/SH = #D55E00/#009E73/#6A3D9A) is the
# THIRD-ranked permutation; 2B-R2-2 says the mapping is "fixed by a quick A/B",
# and the A/B overturned the listing. That is what the A/B was for.

ERC_DOMAIN_COLORS = {
    "PE": "#6A3D9A",   # Physical Sciences & Engineering -- violet.  twin (OA Physical) 24.4, others 39.6, contrast 7.64:1
    "LS": "#009E73",   # Life Sciences -- bluish green.              twin (OA Life)      6.0, others 28.7, contrast 3.42:1
    "SH": "#D55E00",   # Social Sciences & Humanities -- vermillion. twin (OA Social)   26.9, others 21.7, contrast 3.87:1
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
# FAMILY 5 -- INSTITUTION IDENTITY. **COMPARE AND COLLABORATE ONLY** (2B-1).
# ---------------------------------------------------------------------------
# What a slot means: "the n-th institution of the current basket", not a fixed
# entity. Every other family in this file names a thing that keeps its colour
# app-wide; this one names a POSITION, which is why the assignment rule below
# (ascending `inst_key`) matters more here than anywhere else -- it is the only
# thing that makes the colour stable between the Compare page, the Collaborate
# page, a rerun, a deep link and an export.
#
# k = 3 IS THE WHOLE FAMILY. 2B-R-4 caps Compare at three institutions and
# Collaborate is a PAIR, so slots 4-6 had no consumer. `state.BASKET_CAP` is
# still 6 -- a reader may hold six institutions in the basket -- but a basket
# chip is not painted with `institution_color` anywhere (the only callers are
# `charts_compare.py`, `views_compare.py` and `views_collab.py`, all behind
# `charts_compare._series_ids`' hard cap of COMPARE_MAX_SERIES = 3), so no
# fourth slot can reach the screen. If a future view ever needs one it gets
# COMPARISON grey, never a generated hue and never a cycle.
#
# --- PHASE 2B-R3 (2026-08-31, stream PAL, user ruling 5) -----------------
# REPLACES THE LIGHT PASTEL TRIO (2B-R2) with a DARK NAVY TRIO -- three shades
# of the same ink-navy hue, darkest first. Full wind-tunnel measurement:
# `evals/wind_tunnel_2BR3/WT_2BR3.md` task 2. The pastel trio is RETIRED and no
# longer appears anywhere in `lib/` (grepped clean 2026-08-31); its own numbers
# now live only in git history.
#
# NAMED VALIDATOR EXCEPTION: institution-monochrome-family. A monochrome
# identity ramp fails the categorical validator's lightness band AND its chroma
# floor BY DEFINITION -- that IS the design (a single ink-navy hue at three
# lightness steps, not three distinct hues), so those two checks are WAIVED for
# `INSTITUTION_COLORS` alone, and INTERNAL PAIRWISE SEPARATION is asserted
# instead of them:
#     L / C            #192C41 L=0.288 C=0.046  ·  #5A6883 L=0.516 C=0.046  ·
#                       #B5C0D4 L=0.806 C=0.031  (all three fail band+floor,
#                       BY DESIGN -- see the exception name above)
#     in-trio CVD       worst 22.6 (protan)  -- far above the 8.0 target
#     in-trio normal    worst 22.9           -- far above the 15 floor
# (WT_2BR3.md task 2.1/2.3, re-measurable with `evals/wind_tunnel_2BR3/
# wt_task2_colour.mjs` sections 1/1-alone.)
#
# COEXISTENCE EXCEPTION (the pre-existing rule this file has always carried,
# extended here with the navy trio's own numbers -- WT_2BR3.md task 2.4-2.6):
#     vs OA        min normal 17.5   (slot 3 <-> OA Physical periwinkle)  PASS
#     vs SDG       min normal 12.5   (slot 3 <-> SDG-6 Clean Water cyan)  FAIL,
#                  same coexistence disposition as every other cross-family
#                  pair in this file: an institution fill and an SDG fill never
#                  share a MARK (SDG reaches a Compare figure only as a row-
#                  label glyph, LABEL ACCENTS below).
#     vs ERC       min normal 12.9   (slot 2 <-> ERC-PE violet)  FAIL, same
#                  disposition -- ERC reaches a Compare mark only via the label
#                  accent, never a fill sharing a figure with an institution bar.
# Both FAILs are legal for the same reason runs 6b/10/20/21 already established
# in this file: the two colliding families are never two MARKS in one figure.
#
# WHY DARKEST FIRST. Slot 1 (`#192C41`) is the darkest and needs no label twin
# at all (contrast 14.21:1 on white, already text-legible); slot 2 (`#5A6883`,
# 5.61:1) likewise self-twins; only slot 3 (`#B5C0D4`, 1.83:1, the light end)
# needs an actually-computed darker twin (`INSTITUTION_COLORS_DARK[2]`) --
# an ADJUSTED finding vs the plan's plural "twins": only one new hex, not three
# (WT_2BR3.md task 2.2).

INSTITUTION_COLORS = [
    "#192C41",   # slot 1 -- darkest navy   (L 0.288, contrast 14.21:1 -- self-twin)
    "#5A6883",   # slot 2 -- mid navy       (L 0.516, contrast  5.61:1 -- self-twin)
    "#B5C0D4",   # slot 3 -- pale navy      (L 0.806, contrast  1.83:1 -- needs a twin)
]

INSTITUTION_COLORS_DARK = [
    "#192C41",   # slot 1 self-twin (== the fill: already clears 4.5:1 body text)
    "#5A6883",   # slot 2 self-twin (== the fill: already clears 4.5:1 body text)
    "#687284",   # slot 3 twin -- same hue, L 0.55, contrast 4.85:1 (first clean
                 # pass above the 4.5:1 floor; measured by walking OKLCH L down
                 # at constant hue/chroma, `wt_task2_colour.mjs` section 9).
                 # Readability note, not a validator FAIL (fill-vs-text is not a
                 # checked pair): this twin sits only ~3.7 normal-vision units
                 # from slot 2's own FILL, i.e. institution-3's label text reads
                 # visually close to institution-2's bar on the same screen.
]
# NOT a second identity family and NEVER a fill: one entry per slot, the SAME
# hue as the fill it belongs to, dark enough to be read as small text on
# SURFACE -- the value label on a bar, the institution's name in the chip
# legend, the KPI card's best-value dot caption. Only slot 3 required a NEW
# hex (see the ADJUSTED note above); slots 1-2 are their own fill, which is
# legal here because they already clear 4.5:1 unmodified.

INSTITUTION_SLOT_MAX = len(INSTITUTION_COLORS)
# The hard ceiling. A fourth institution is NEVER a generated hue (dataviz
# non-negotiable) -- `charts_compare.COMPARE_MAX_SERIES` refuses the figure and
# `institution_color` hands back COMPARISON grey rather than cycling.


SHARED_FRONTIER = "#7A1600"
# **NOT a fourth institution slot** -- deliberately kept OUT of
# `INSTITUTION_COLORS` so `institution_color` can never hand it to an
# institution and `INSTITUTION_SLOT_MAX` keeps meaning what it says.
#
# WHAT IT MEANS (2B-R-9, unchanged by 2B-R3): in the pooled Compare frontier
# map a topic is painted in an institution's own hue when ONLY that institution
# holds it, and in this hue when EVERY compared institution holds it --
# "shared" is the intersection, so it takes a hue no entity owns. It paints the
# pooled frontier map and the "who holds the shared frontier" bar chart ONLY;
# the Collaborate pulse chart moved to `JOINT_COLOR` below (2B-R3), so this hue
# and the vermillion ERC-SH/momentum-down hue are no longer both reachable from
# the same Collaborate page.
#
# 2B-R3 RE-MEASUREMENT (user ruling 5 / WT_2BR3.md §0): the previous
# `SHARED_FRONTIER` failed outright against ERC-SH/momentum-down vermillion
# `#D55E00` -- normal-vision 7.6, deutan 2.4, both below their hard floors, not
# a "needs care" WARN. PAL re-measured the ratification's two darker-red
# candidates against `#D55E00` with `evals/wind_tunnel_2BR3/
# wt_task2_pal_remeasure.mjs` (both normal AND deutan required >= 15):
#     candidate 1  L=0.501  normal ΔE 13.05  deutan ΔE 12.10   FAIL (both < 15)
#     candidate 2  L=0.377  normal ΔE 24.93  deutan ΔE 25.20   PASS  <- SHIPPED
# The winner clears every other cross-family floor too (isolated pairwise,
# normal-vision): vs OA min 30.4, vs SDG min 11.2 (FAIL -- same coexistence
# disposition as the rest of this file: SHARED_FRONTIER is a MARK in its own
# two figures, never alongside an SDG fill), vs ERC min 21.8, vs FOCAL 30.2,
# vs COMPARISON 31.3. Contrast on white: 10.81:1.
#
# RELIEF the SDG-coexistence and "colour never alone" rules oblige: the
# frontier map's chip legend carries a "shared" chip beside the institution
# chips (`charts_compare.legend_strip`), every bubble's hover names its owner
# in words, and the map's own export column carries the owner as text.

JOINT_COLOR = "#2F3B52"
# The Collaborate relationship-pulse bars and other JOINT-corpus accents (2B-R3,
# user ruling 5 / WT_2BR3.md §0). Dark ink-navy, deliberately NOT a red: the
# pulse chart's only mark is the PAIR's joint corpus, and the ERC-SH/momentum-
# down vermillion `#D55E00` renders on the SAME Collaborate page (the topic
# table's Momentum column), so painting the pulse in any red risked exactly the
# collision `SHARED_FRONTIER` was just re-measured out of (contrast on white
# 11.24:1). Never chip-adjacent to an institution chip: the pulse is the one
# figure on the Collaborate page whose colour carries no institution identity
# at all (`charts_compare.fig_pulse`'s own docstring), so a chip strip that
# would otherwise show a JOINT chip beside institution chips drops the joint
# chip instead rather than asking a reader to tell JOINT_COLOR apart from the
# darkest institution navy.


# ---------------------------------------------------------------------------
# MOMENTUM -- Collaborate's up/down/stable read (2B-R3, ruling 6, Lorraine
# port; class thresholds and windows live in `collab_facts.json`, not here).
# ---------------------------------------------------------------------------
# TEXT + GLYPH ONLY, NEVER A FILL (§2.3) -- the mandatory reason this is legal
# at all: `up`'s own hue is ERC-LS green and `down`'s is ERC-SH/momentum-down
# vermillion (the app's one hard colour-alone failure, WT_2BR3.md task 2.8:
# ΔE 7.6 normal / 2.4 deutan against the old SHARED_FRONTIER, still the
# distinguishability floor a bare fill would fail). A momentum chip is always
# colour + glyph + the class word together, never colour alone.
#
# `stable` moved off the shipped `INK_SECONDARY` twin `#5A5F66` (WT_2BR3.md
# task 2.7, a NEW finding not in the plan: `#5A5F66` sits only ΔE 4.7 from
# navy slot 2 `#5A6883`, near-indistinguishable even to normal vision) to
# `#727272` -- re-measured against navy slot 2 with `wt_task2_pal_remeasure.mjs`
# section F at ΔE 5.86, still short of the 15 mark. That residual is the same
# disposition class as the slot-3 twin's ΔE 3.7 to slot 2's fill above: a
# TEXT-vs-FILL pairing the categorical validator does not check (chrome tokens
# are excluded from it by this file's own convention, see INK_SECONDARY /
# COMPARISON / INK above), carried here as a readability note rather than a
# blocking fail. `#727272` clears 4.5:1 body-text contrast (4.81:1).

MOMENTUM_COLORS = {
    "up": "#009E73",
    "down": "#D55E00",
    "stable": "#727272",
    "ns": "#8C9196",       # up/down demoted by the significance test
    "new": "#8C9196",
    "dormant": "#8C9196",
    "weak": "#8C9196",     # weak base -- glyph + "weak base" text, no percent
}

MOMENTUM_GLYPHS = {
    "up": "\N{NORTH EAST ARROW}",
    "down": "\N{SOUTH EAST ARROW}",
    "stable": "\N{RIGHTWARDS ARROW}",
    # the four "can't classify with confidence" states share ONE neutral dash
    # (never the stable arrow -- "n.s." must not read as "stable"): manager
    # merge 2BR3, aligning to collab_data's documented ladder + the Lorraine
    # source convention.
    "ns": "\N{EN DASH}",
    "new": "\N{EN DASH}",
    "dormant": "\N{EN DASH}",
    "weak": "\N{EN DASH}",
}


def momentum_color(mom_class) -> str:
    """Colour for a `mom_class` value. Unknown -> COMPARISON grey, the family
    convention -- never a fill, see the section note above."""
    return MOMENTUM_COLORS.get(str(mom_class).strip().lower(), COMPARISON)


def momentum_glyph(mom_class) -> str:
    """Glyph for a `mom_class` value. Unknown -> the neutral en dash, never
    blank -- a momentum chip is never colour or text alone."""
    return MOMENTUM_GLYPHS.get(str(mom_class).strip().lower(), MOMENTUM_GLYPHS["ns"])


def institution_color(slot) -> str:
    """Colour for an institution SLOT (zero-based, as returned by
    `institution_slots`). Out of range / unknown -> COMPARISON grey, the same
    unknown-slot convention every other family helper uses. It never wraps
    around: a cycled categorical palette is the one thing the dataviz
    non-negotiables forbid outright."""
    try:
        key = int(slot)
    except (TypeError, ValueError):
        return COMPARISON
    if 0 <= key < len(INSTITUTION_COLORS):
        return INSTITUTION_COLORS[key]
    return COMPARISON


def institution_ink(slot) -> str:
    """The TEXT colour for an institution slot -- its fill's darker same-hue
    twin (2B-R2-2).

    The counterpart of `institution_color`, and the reason it exists: the fills
    sit at L 0.77 and contrast about 2:1 on white, so a value label, a legend
    name or a KPI dot's caption drawn IN THE FILL COLOUR would be unreadable.
    The twin keeps the hue -- the label and its bar are visibly the same
    institution -- and clears the 4.5:1 body-text floor.

    Out of range / unknown -> `INK_SECONDARY`, which is the app's ordinary
    secondary text colour: an unassignable slot loses its identity accent
    rather than being written in grey-that-looks-like-a-colour. (The mark-side
    twin of this rule returns COMPARISON; text and marks have different
    neutrals, which is why the two helpers do not share one.)"""
    try:
        key = int(slot)
    except (TypeError, ValueError):
        return INK_SECONDARY
    if 0 <= key < len(INSTITUTION_COLORS_DARK):
        return INSTITUTION_COLORS_DARK[key]
    return INK_SECONDARY


def institution_slots(inst_keys) -> dict:
    """Assign colour slots to the compared institutions -- the ONE place this
    happens, so a slot cannot drift between two views of the same basket.

    RULE (2B-1 / wind-tunnel finding #15): slots go by **ASCENDING `inst_key`**,
    never by click order and never by the order the caller happens to hold the
    ids in. Click order would repaint the whole chart when the reader removes
    the institution they added first -- "colour follows the entity, never its
    rank" applied to selection order rather than to a sort.

    Two accepted input shapes, because the caller has two natural ones:
      * a SEQUENCE of `inst_key`s            -> ``{inst_key: slot}``
      * a MAPPING ``{identifier: inst_key}`` -> ``{identifier: slot}``, which is
        what a page holds (the frames are keyed by `institution_id` while the
        stable ordering key is `inst_key`).
    Duplicates collapse; anything past `INSTITUTION_SLOT_MAX` still gets a slot
    number, and `institution_color` turns it into COMPARISON grey rather than
    cycling -- an over-long basket degrades visibly instead of lying.
    """
    if hasattr(inst_keys, "items"):
        pairs = list(inst_keys.items())
    else:
        pairs = [(k, k) for k in inst_keys]
    seen: dict = {}
    for ident, key in pairs:
        if ident not in seen:
            seen[ident] = key

    def _order(item):
        key = item[1]
        try:
            return (0, float(key), "")
        except (TypeError, ValueError):
            return (1, 0.0, str(key))

    return {ident: i for i, (ident, _k) in enumerate(sorted(seen.items(), key=_order))}


# ---------------------------------------------------------------------------
# LABEL ACCENTS -- the ONE documented narrowing of the coexistence rule (2B-R-8)
# ---------------------------------------------------------------------------
# The coexistence rule in the module docstring says one identity family per
# chart, and in Compare that family is the institution. 2B-R-8 keeps that rule
# for MARKS and narrows it for one piece of AXIS FURNITURE: in the Compare
# ERC and SDG views the row label may carry a small coloured glyph in its own
# taxonomy's OFFICIAL colour -- the three ERC domain hues, the sixteen UN goal
# hues -- so a reader can see the PE / LS / SH grouping, or recognise a goal by
# its UN colour, without the panel losing the institution as its identity.
#
# THE RULE, in three parts, and all three are load-bearing:
#   1. A taxonomy colour may appear ONLY in a y-axis tick label, never in a bar,
#      dot, bubble, line, interval or legend chip. The reader is never asked to
#      tell two MARKS apart by two different families' hues -- which is the
#      thing validator run 17 measures as unsafe (ERC PE #1F4E9C vs institution
#      slot 3 #6A3D9A, protan 1.7).
#   2. The accent is never the only carrier of the taxon: the label TEXT beside
#      it names the panel or the numbered goal in full, so the accent is
#      recognition, never encoding. That is the same relief the SDG panel has
#      carried since run 7 (the UN palette's two near-identical ambers), applied
#      one level up.
#   3. INSTITUTION IDENTITY NEVER APPEARS ON A LABEL ACCENT. The direction is
#      fixed and one-way: colour on a MARK means the institution, colour on a
#      LABEL means the taxonomy. If both could go either way, neither would
#      mean anything.
# 2B-R3 (user ruling 5, plan section 1.5) ADDS "oa" to the accent families.
# The 2B-R-8 note above ("OA fields, subfields, topics take NO accent") is
# RETIRED: every field/subfield row `fig_metric_bars` draws now carries its
# OA-domain chip too, the same idiom the ERC/SDG rows already used -- an
# institution-coloured bar chart otherwise gives no visual cue AT ALL for
# which domain a field belongs to, which the OA-coloured Find panels the
# reader came from do supply. The three-part rule above is unchanged and
# binds "oa" identically: chip on the LABEL only, institution colour never
# reaches a label accent, and the label text still names the field in full.

LABEL_ACCENT_FAMILIES = ("erc", "sdg", "oa")


def label_accent_color(family, key) -> str:
    """Colour for a ROW-LABEL accent glyph, by taxonomy family.

    The ONE entry point for part 1 of the rule above -- a chart module asks for
    an accent by family and never reaches into `ERC_DOMAIN_COLORS`,
    `SDG_COLORS` or `OA_DOMAIN_COLORS` itself, so the "labels only, marks
    never" split has a single place it can be audited. An unsupported family
    (`doctype`, anything else) returns COMPARISON grey, the family convention:
    no accent rather than a borrowed one."""
    fam = str(family).strip().lower()
    if fam == "erc":
        return erc_color(key)
    if fam == "sdg":
        return sdg_color(key)
    if fam == "oa":
        return domain_color(key)
    return COMPARISON


# ---------------------------------------------------------------------------
# THE ORDINAL RAMP -- grey-accounting states (coverage strip, 2B-6 / A9)
# ---------------------------------------------------------------------------
# NOT an identity family: these five states are ORDERED by distance from usable
# text, so they take a one-hue sequential ramp (dataviz: "Sequential = one hue,
# light->dark"), and the sixth segment of the strip -- the classified-eligible
# mass -- is painted in the compared institution's OWN identity colour. That
# keeps the coexistence rule intact (the only identity in the figure is still
# the institution) and gives the strip the highlight-plus-mute reading the
# Studio colour formula asks for: one coloured segment that is the answer, a
# muted ramp behind it that accounts for the rest.
#
# The five sum with `mass_classified_eligible` to `total_frac` EXACTLY for all
# 7,557 institutions (wind-tunnel claim #14, A9) -- which is what makes the
# stacked 100 % strip a true statement and the one stacked bar this app draws.
#
# VALIDATOR run 12: the categorical checks FAIL by design (five neutrals below
# the chroma floor; adjacent normal-vision 7.8) -- the validator's own scope
# line says a sequential ramp is checked for lightness monotonicity instead.
# `validateOrdinal` returns OK on all four applicable checks: monotone
# light->dark, every adjacent dL >= 0.06, light-end contrast 2.14:1 (floor 2:1),
# single hue (spread 4 degrees). Contrasts vs SURFACE, lightest to darkest:
# 2.14 / 2.84 / 3.89 / 5.39 / 7.77.

GREY_STATE_COLORS = {
    "title_only": "#ACB2B9",
    "lang_uncertain": "#939AA2",
    "untranslated_grey": "#7B828A",
    "unusable": "#646B73",
    "retracted_excluded": "#4D535B",
}

GREY_STATE_ORDER = ("classified_eligible", "title_only", "lang_uncertain",
                    "untranslated_grey", "unusable", "retracted_excluded")
# Fixed segment order of the coverage strip, left to right: the usable mass
# first (the institution's own hue), then the ramp light -> dark. The order is
# the ramp's meaning -- re-sorting it by size would turn an ordinal scale into a
# categorical one and make the lightness gradient a lie.

CLASSIFIED_ELIGIBLE_STATE = "classified_eligible"
# The one segment of the strip that is NOT grey: it takes the institution's own
# `institution_color`. Named here rather than typed into the chart module so the
# "which segment is the highlight" decision lives with the colours.


def grey_state_color(state) -> str:
    """Colour for a grey-accounting state. The classified-eligible state has no
    grey of its own (the caller paints it with `institution_color`); an unknown
    state -> COMPARISON, the family convention."""
    return GREY_STATE_COLORS.get(str(state).strip().lower(), COMPARISON)


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

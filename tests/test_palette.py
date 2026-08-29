"""Stream D0 tests: palette.py is the ONE legal colour source, and VIZ_SPEC.md
carries a rejected alternative for every §2 view row.

Run from cwd `app/`:  python -m pytest tests/test_palette.py -q
"""
from __future__ import annotations

import re
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
HEX_RE = re.compile(r"#[0-9A-Fa-f]{6}\b")

# Files allowed to contain a "#RRGGBB" literal. Everything else under
# lib/, pages/, and Menu.py must route colour through lib/palette.py.
ALLOWLIST = {APP_DIR / "lib" / "palette.py"}

# Directories scanned for stray hex literals (scanned lazily -- the test must
# keep working as Stream E/F files appear during the rest of Phase 2A).
SCAN_DIRS = [APP_DIR / "lib", APP_DIR / "pages"]
SCAN_FILES = [APP_DIR / "Menu.py"]


def _hexes_in(text: str) -> set[str]:
    return {m.group(0).upper() for m in HEX_RE.finditer(text)}


def _palette_module_source() -> str:
    path = APP_DIR / "lib" / "palette.py"
    assert path.exists(), f"lib/palette.py not found at {path}"
    return path.read_text(encoding="utf-8")


def test_every_palette_hex_is_validated():
    """Every #RRGGBB literal in lib/palette.py appears (case-insensitively)
    somewhere in design-system/palette_validation.txt -- i.e. every colour
    the app can render was actually run through the validator, not eyeballed.
    """
    validation_path = APP_DIR / "design-system" / "palette_validation.txt"
    assert validation_path.exists(), f"missing {validation_path}"
    validation_text = validation_path.read_text(encoding="utf-8").upper()

    palette_hexes = _hexes_in(_palette_module_source())
    assert palette_hexes, "lib/palette.py defines no #RRGGBB constants -- unexpected"

    missing = sorted(h for h in palette_hexes if h not in validation_text)
    assert not missing, (
        f"hex(es) in lib/palette.py never appear in palette_validation.txt: {missing}"
    )


def test_no_stray_hex_literals_outside_palette():
    """No #RRGGBB literal exists in any .py under app/lib/ (other than
    palette.py), app/pages/, or app/Menu.py. Scans whatever exists right now
    -- files that land later in Phase 2A (Streams E/F) are covered
    automatically, no allowlist edit needed unless they legitimately need a
    literal (they should import from lib.palette instead).
    """
    offenders: dict[str, set[str]] = {}

    py_files: list[Path] = []
    for d in SCAN_DIRS:
        if d.exists():
            py_files.extend(sorted(d.rglob("*.py")))
    py_files.extend(f for f in SCAN_FILES if f.exists())

    for f in py_files:
        if f in ALLOWLIST:
            continue
        # Never descend into __pycache__ or test/golden fixtures accidentally
        # swept in by a broad rglob under lib/ (there are none today, but the
        # guard costs nothing and keeps this test honest as files appear).
        if "__pycache__" in f.parts:
            continue
        found = _hexes_in(f.read_text(encoding="utf-8", errors="ignore"))
        if found:
            offenders[str(f.relative_to(APP_DIR))] = found

    assert not offenders, (
        "stray #RRGGBB literal(s) found outside lib/palette.py -- route colour "
        f"through lib.palette instead: {offenders}"
    )


def test_viz_spec_has_rejected_alternative_per_view_row():
    """docs/VIZ_SPEC.md contains the literal token 'Rejected alternative:' at
    least once per §2 view row (one row = one '### 2.N' heading inside §2).
    """
    spec_path = APP_DIR / "docs" / "VIZ_SPEC.md"
    assert spec_path.exists(), f"missing {spec_path}"
    text = spec_path.read_text(encoding="utf-8")

    view_row_count = len(re.findall(r"^### 2\.\d+", text, flags=re.MULTILINE))
    assert view_row_count > 0, "no '### 2.N' view rows found in VIZ_SPEC.md §2"

    rejected_count = text.count("Rejected alternative:")
    assert rejected_count >= view_row_count, (
        f"VIZ_SPEC.md has {view_row_count} §2 view rows but only "
        f"{rejected_count} 'Rejected alternative:' tokens -- every view row "
        "needs at least one"
    )


def _palette():
    import sys
    sys.path.insert(0, str(APP_DIR))
    from lib import palette  # noqa: E402
    return palette


def test_type_colors_removed_in_r1():
    """R1 (BUILD_PLAN_2A.md L22, user ruling #8 at gate 2A) removed the badge
    column from every table, which left the institution-type identity set with
    no consumer. `TYPE_COLORS` and `type_group` were DELETED (grep before
    deletion returned only palette.py, this test file and two prose lines in
    DESIGN_TOKENS.md -- no live code path). This test pins the deletion so the
    symbols cannot creep back as dead colour: restoring them needs a real
    consumer and a ledger line, not an import."""
    palette = _palette()
    assert not hasattr(palette, "TYPE_COLORS")
    assert not hasattr(palette, "type_group")
    assert palette.NA_MARK == "n/a"


# ---------------------------------------------------------------------------
# R1 -- the four identity families (BUILD_PLAN_2A.md L19)
# ---------------------------------------------------------------------------
HEX6 = re.compile(r"^#[0-9A-Fa-f]{6}$")

EXPECTED_KEYS = {
    "OA_DOMAIN_COLORS": {1, 2, 3, 4},
    "ERC_DOMAIN_COLORS": {"PE", "LS", "SH"},
    "SDG_COLORS": set(range(1, 18)),
    "DOCTYPE_COLORS": {"article", "review", "book", "book-chapter", "letter"},
}


def test_identity_families_have_the_exact_key_sets():
    palette = _palette()
    for name, keys in EXPECTED_KEYS.items():
        fam = getattr(palette, name)
        assert set(fam) == keys, f"{name} keys: {sorted(map(str, set(fam)))}"
    assert len(palette.SDG_COLORS) == 17
    assert len(palette.OA_DOMAIN_COLORS) == 4
    assert len(palette.ERC_DOMAIN_COLORS) == 3
    assert len(palette.DOCTYPE_COLORS) == 5


def test_every_family_value_is_a_six_digit_hex():
    palette = _palette()
    for name in EXPECTED_KEYS:
        for key, value in getattr(palette, name).items():
            assert isinstance(value, str) and HEX6.match(value), f"{name}[{key!r}] = {value!r}"
    for token in ("FOCAL", "COMPARISON", "NEUTRAL", "INK", "SURFACE",
                  "INK_SECONDARY", "BORDER", "GRID"):
        assert HEX6.match(getattr(palette, token)), token


def test_no_duplicate_hue_across_oa_erc_and_doctype():
    """The three families that can appear in adjacent panels of the same page
    must not share a hex: an identical colour in two families would read as one
    identity across a scroll or a segmented-control swap."""
    palette = _palette()
    used = ([v.upper() for v in palette.OA_DOMAIN_COLORS.values()]
            + [v.upper() for v in palette.ERC_DOMAIN_COLORS.values()]
            + [v.upper() for v in palette.DOCTYPE_COLORS.values()])
    dupes = {h for h in used if used.count(h) > 1}
    assert not dupes, f"hue(s) reused across OA / ERC / DOCTYPE: {sorted(dupes)}"
    assert palette.FOCAL.upper() not in used, (
        "FOCAL is the seed highlight and never an identity hue (coexistence rule)")


def test_sdg_seventeen_is_stored_but_declared_uncovered():
    palette = _palette()
    assert palette.SDG_UNCOVERED == (17,)
    assert 17 in palette.SDG_COLORS
    assert palette.SDG_COLORS[17] == "#19486A"


def test_domain_and_family_helpers_fall_back_to_comparison_grey():
    palette = _palette()
    assert palette.domain_color(1) == palette.OA_DOMAIN_COLORS[1]
    assert palette.domain_color("3") == palette.OA_DOMAIN_COLORS[3]
    for unknown in (0, 9, None, float("nan"), "", "unclassified"):
        assert palette.domain_color(unknown) == palette.COMPARISON
    assert palette.erc_color("pe") == palette.ERC_DOMAIN_COLORS["PE"]
    assert palette.erc_color("XX") == palette.COMPARISON
    assert palette.sdg_color(1) == palette.SDG_COLORS[1]
    assert palette.sdg_color(99) == palette.COMPARISON
    assert palette.doctype_color("Article") == palette.DOCTYPE_COLORS["article"]
    assert palette.doctype_color("preprint") == palette.COMPARISON


def test_fixed_display_orders_cover_their_families():
    palette = _palette()
    assert set(palette.OA_DOMAIN_ORDER) == set(palette.OA_DOMAIN_COLORS)
    assert set(palette.ERC_DOMAIN_ORDER) == set(palette.ERC_DOMAIN_COLORS)
    assert set(palette.DOCTYPE_ORDER) == set(palette.DOCTYPE_COLORS)
    assert set(palette.DOCTYPE_LABELS) == set(palette.DOCTYPE_COLORS)
    assert set(palette.ERC_DOMAIN_LABELS) == set(palette.ERC_DOMAIN_COLORS)


def test_theme_primary_is_focal():
    """BUILD_PLAN_2A.md Decisions log 2026-08-29 ("`.streamlit/config.toml`
    `primaryColor = #0072B2` (= palette.FOCAL) is the ONE hex outside
    palette.py"): Streamlit paints ProgressColumn bars, links and buttons
    with the theme's primaryColor, so it must track lib.palette.FOCAL rather
    than drift to Streamlit's off-palette default red. Stream G extension
    named explicitly in that decisions-log row.
    """
    import sys

    if sys.version_info >= (3, 11):
        import tomllib
    else:  # pragma: no cover -- this app's pinned interpreter is 3.12
        import tomli as tomllib  # type: ignore[import-not-found]

    sys.path.insert(0, str(APP_DIR))
    from lib import palette  # noqa: E402

    config_path = APP_DIR / ".streamlit" / "config.toml"
    assert config_path.exists(), f"missing {config_path}"
    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    primary_color = config.get("theme", {}).get("primaryColor")
    assert primary_color, f"[theme] primaryColor not set in {config_path}"
    assert primary_color.upper() == palette.FOCAL.upper(), (
        f"config.toml theme.primaryColor={primary_color!r} != palette.FOCAL={palette.FOCAL!r}")


def test_hex_scan_actually_covers_the_new_charts_module():
    """Non-vacuity guard for `test_no_stray_hex_literals_outside_palette`: that
    test walks whatever exists under lib/, so it would pass trivially if
    lib/charts.py ever disappeared from the walk. Pin the file into the scan."""
    charts = APP_DIR / "lib" / "charts.py"
    assert charts.exists(), "lib/charts.py missing -- the hex scan would be vacuous"
    scanned: list[Path] = []
    for d in SCAN_DIRS:
        if d.exists():
            scanned.extend(sorted(d.rglob("*.py")))
    assert charts in scanned
    assert charts not in ALLOWLIST, "charts.py must NOT be allowed a hex literal"
    assert not _hexes_in(charts.read_text(encoding="utf-8"))

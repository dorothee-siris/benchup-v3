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


def test_type_colors_shape():
    """lib.palette.TYPE_COLORS covers exactly the 5 collapsed identity groups,
    education is deliberately uncoloured, and no colour repeats FOCAL.
    """
    import sys

    sys.path.insert(0, str(APP_DIR))
    from lib import palette  # noqa: E402

    assert set(palette.TYPE_COLORS) == {
        "education",
        "facility",
        "healthcare",
        "government+funder",
        "other",
    }
    assert palette.TYPE_COLORS["education"] is None
    used = [v for v in palette.TYPE_COLORS.values() if v is not None]
    assert len(used) == len(set(used)), "TYPE_COLORS hues must be distinct"
    assert palette.FOCAL not in used, "FOCAL must never double as a type-identity colour"
    assert palette.NA_MARK == "n/a"


def test_type_group_mapping():
    import sys

    sys.path.insert(0, str(APP_DIR))
    from lib import palette  # noqa: E402

    assert palette.type_group("education") == "education"
    assert palette.type_group("Education") == "education"
    assert palette.type_group("facility") == "facility"
    assert palette.type_group("healthcare") == "healthcare"
    assert palette.type_group("government") == "government+funder"
    assert palette.type_group("funder") == "government+funder"
    for other_type in ("company", "nonprofit", "archive", "other", "nonsense-value"):
        assert palette.type_group(other_type) == "other"


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

"""tests/test_forbidden_vocabulary.py -- stream MU3 (2B-R2-8/13 plain-language
sweep). RULE: no string a reader actually sees names a plan code, a build
artefact, a pipeline, a stream, or a table/file name. A strategy officer
reading this tool for the first time must never meet "2B-R", "BUILD_PLAN",
"artefact", "pipeline", "parquet" or a stream name (MU3, CP3, LP3, WT2, P6,
G2, H2, I2, VS3, FA3, CD3, ...).

SCOPE -- every RENDERED string, two sources:
  (a) `lib/copy.py`'s own uppercase module constants, reusing
      `tests/test_narrative.py`'s `collect_copy_module_strings` collector
      (the same recursive walk the digit-ban already trusts), MINUS
      `METHODS_SOURCES`: that dict is the Methods page's own provenance
      map, read only by this test suite and by `docs/METHODS_NOTE.md`'s own
      cross-check (`tests/test_methods_note.py`), never passed to a
      Streamlit call or rendered on any page (`views_methods.render()` only
      ever reads `copy.METHODS`, `copy.NAV`, `copy.VERDICT_LINE` and
      `copy.METHODS_UI`) -- this is the ONE allowlisted section the brief
      anticipates ("an allowlist ONLY for the Methods provenance section if
      it genuinely needs it"), and it earns the exemption on "never
      rendered" grounds rather than on a word-by-word carve-out: every
      OTHER string in copy.py, METHODS's own {title, body} templates
      included, is scanned in full.
  (b) `lib/compare_data.py`'s `UNAVAILABLE_REASON` values (2B-R2-13 A4:
      "CD3 rewrites them" -- read live via import here so a future edit to
      that dict is caught the same day, not just at CD3's own build time).
      `lib/collab_data.py` carries no equivalent reason dict today (grepped
      2026-08-31: no module-level string constant holding a `reason:` value
      or a `REASON` name) -- `_reason_frame_strings()` below still imports
      the module and reads any dict whose name ends in `REASON` generically,
      so a reason dict LP3 adds next wave is picked up with no edit here.

FALSE-POSITIVE GUARD: "artefact" is also an ordinary English word (an
unintended effect, as in "a country artefact" / "a statistical artefact"),
not only internal build vocabulary. Two pre-existing LENS_INTRO/LENS_CAVEAT
sentences used it that way; MU3 rephrased both ("not simply an effect of
shared country" / "does not simply reflect a shared country") rather than
carving a word-sense exception into this test, per the brief's own
"prefer rephrasing" instruction -- so the banned-term list below is applied
literally, with no per-string exemption.

Run from cwd `app/`:  python -m pytest tests/test_forbidden_vocabulary.py -q
"""
from __future__ import annotations

import re

import pytest

from tests.test_narrative import collect_copy_module_strings

# Case-insensitive except the bare stream-code tokens (MU3, CP3, ... read as
# uppercase identifiers; a lowercase "cp3" is not a stream code, and "P6" as
# a bare token would false-positive on ordinary prose, so every stream code
# is matched with a word boundary and its exact case).
FORBIDDEN_CI = [
    "2B-R", "2b-r", "BUILD_PLAN", "artefact", "pipeline", "parquet",
    "wind tunnel", "wind-tunnel",
    # 2BR3 TEV-U (wave 3 acceptance): "pastel" (the retired institution
    # trio's own family name -- never a word a reader needs, even in the
    # abstract) and the "2B-R3"/"2BR3" stream-round family, alongside every
    # earlier round's "2B-R" this list already banned.
    "pastel", "2b-r3", "2br3",
]
FORBIDDEN_CODES = re.compile(
    r"\b(MU3|CP3|LP3|VS3|FA3|CD3|WT2?|P[1-6]|G2|H2|I2)\b"
)

# METHODS_SOURCES: the one non-rendered exemption (see module docstring).
# Every other name in lib.copy is in scope, including copy.METHODS itself.
NON_RENDERED_NAMES = {"METHODS_SOURCES"}


def _violations(strings: list[tuple[str, str]]) -> list[tuple[str, str, str]]:
    out = []
    for loc, s in strings:
        low = s.lower()
        for term in FORBIDDEN_CI:
            if term.lower() in low:
                out.append((loc, term, s))
        m = FORBIDDEN_CODES.search(s)
        if m:
            out.append((loc, m.group(1), s))
    return out


def _copy_rendered_strings() -> list[tuple[str, str]]:
    from lib import copy as copy_mod

    return [(loc, s) for loc, s in collect_copy_module_strings(copy_mod)
            if not any(f"::{name}[" in loc for name in NON_RENDERED_NAMES)]


def _reason_frame_strings() -> list[tuple[str, str]]:
    """Every string value in a `*REASON*`-named dict of `lib.compare_data`
    or `lib.collab_data` -- the 'frame reason strings' the brief names:
    `compare_data.metric_frame`'s empty-frame `.attrs["reason"]` is filled
    from exactly this kind of dict (`UNAVAILABLE_REASON`, per that module's
    own docstring), so scanning the dict scans every reason the page can
    ever render without needing to drive every (metric, level) pair through
    the UI here."""
    out = []
    for mod_name in ("lib.compare_data", "lib.collab_data"):
        mod = __import__(mod_name, fromlist=["_"])
        for name, value in vars(mod).items():
            if not name.isupper() or "REASON" not in name:
                continue
            if isinstance(value, dict):
                for k, v in value.items():
                    if isinstance(v, str):
                        out.append((f"{mod_name}.{name}[{k!r}]", v))
    return out


def all_rendered_strings() -> list[tuple[str, str]]:
    return _copy_rendered_strings() + _reason_frame_strings()


# ------------------------------------------------------------------ tests --

def test_scan_is_not_vacuous():
    """Guards the collectors themselves: if this drops near zero, an import
    broke (lib.compare_data/lib.collab_data are CD3's concurrent files) or
    collect_copy_module_strings stopped walking -- not that the app has no
    copy left to scan."""
    total = len(all_rendered_strings())
    assert total >= 50, f"only {total} rendered strings collected -- collector likely broken"


def test_unavailable_reason_dict_is_reachable():
    """Non-vacuity of the (b) source specifically: compare_data.UNAVAILABLE_
    REASON must exist and carry at least one string, or the reason-frame
    scan above is silently empty."""
    from lib.compare_data import UNAVAILABLE_REASON

    assert len(UNAVAILABLE_REASON) >= 1
    assert all(isinstance(v, str) for v in UNAVAILABLE_REASON.values())


def test_methods_sources_itself_would_fail_without_the_exemption():
    """Proves the METHODS_SOURCES exemption is doing real work (and is not
    hiding a violation that also lives somewhere rendered): several of its
    values name a real table file on purpose (it is the provenance map),
    so this documents WHY it is excluded rather than leaving that claim
    unverified. If this ever passes, METHODS_SOURCES stopped naming files
    and the exemption in NON_RENDERED_NAMES can be dropped."""
    from lib import copy as copy_mod

    raw = [(f"copy::METHODS_SOURCES[{k}]", v) for k, v in copy_mod.METHODS_SOURCES.items()]
    assert _violations(raw), "expected METHODS_SOURCES to still name a table/pipeline term"


def test_no_forbidden_vocabulary_in_rendered_strings():
    """The regression itself. A hit here is copy a reader can actually see
    naming a plan code, a build artefact, a pipeline, a table file or a
    stream -- see the module docstring for scope and the one exemption."""
    violations = _violations(all_rendered_strings())
    if violations:
        detail = "\n".join(f"  {loc} -- matched {term!r} in {s!r}" for loc, term, s in violations)
        pytest.fail(f"{len(violations)} forbidden-vocabulary violation(s):\n{detail}")

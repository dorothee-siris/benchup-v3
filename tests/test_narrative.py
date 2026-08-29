"""
tests/test_narrative.py -- Stream G: the digit-ban regression (BUILD_PLAN_2A.md
L10 / Stream F build step 5 / Stream G build step 2).

RULE: no digit character appears in a Find-page user-facing string except
inside an allowlisted token (tests/digit_allowlist.txt) or a `{placeholder}`
a caller fills at render time from CFG or the live data. Two scopes:

  (a) every string constant in lib/copy.py (dict values included), which
      since Stream X1 (2026-08-29) also carries the Find-page strings
      formerly in lib/views_find.py's EXTRA_COPY dict, folded into
      lib/copy.py's own `FIND` dict -- one collector, no separate
      views_find.py import needed for this scope any more.

  (b) string literals passed to a Streamlit UI call, or to that call's
      label=/help=/caption=/placeholder= kwarg, in pages/*.py, Menu.py,
      lib/views_find.py, lib/ranked.py, lib/filters.py, lib/badges.py.

      DEVIATION FROM THE LITERAL BRIEF WORDING ("ast walk: Call nodes whose
      func is st.<name> or st.column_config.<name>"): lib/views_find.py
      aliases st.sidebar to `sb`, st.columns(...) to `cols`, individual
      columns to `col_a`/`col_b`/`cols[0]`, etc. (this is ordinary Streamlit
      style, not an obfuscation) -- a matcher that only recognises a literal
      `st.xxx` / `st.column_config.xxx` attribute chain would silently miss
      almost every real call in that file (sb.header, sb.selectbox,
      cols[0].metric, col_a.write, ...), making the test vacuous for the
      file with the most UI copy. Instead a Call is treated as an in-scope
      UI call when its final attribute name is a real, callable member of
      the INSTALLED `streamlit` module or `streamlit.column_config` (built
      from `dir(st)` / `dir(st.column_config)` at test-collection time) --
      grounded in the actual Streamlit API surface, alias-proof, and needs
      no maintenance as new aliases or files appear (test_palette.py uses
      the same "scan whatever exists" philosophy for its own directory
      walk).

EXCLUDED (scope fence, one reason each -- BUILD_PLAN_2A.md Stream G):
  lib/palette.py     -- hex colour constants only, no UI copy.
  lib/data_cache.py  -- parquet/JSON column names and file paths, not UI copy.
  lib/app_config.py  -- loads config.yaml verbatim into CFG, defines no strings.
  lib/exports.py     -- CSV filename template, not rendered UI copy.
  lib/engine/**      -- no Streamlit import anywhere in the engine package.

NON-VACUITY PROOF: run standalone (not part of this suite -- see
V3/progress/2A_G.md for the transcript):
    python - <<'PY'
    import shutil, sys
    sys.path.insert(0, ".")
    shutil.copy("lib/copy.py", "lib/_scratch_copy.py")
    with open("lib/_scratch_copy.py", "a", encoding="utf-8") as f:
        f.write('\nINJECTED = "showing 30 rows"\n')
    from tests.test_narrative import collect_copy_module_strings, has_digit_violation, load_allowlist
    import importlib
    scratch = importlib.import_module("lib._scratch_copy")
    tokens = load_allowlist()
    bad = [s for _, s in collect_copy_module_strings(scratch) if has_digit_violation(s, tokens)]
    print("scratch violations:", bad)   # -> ['showing 30 rows'] (FAIL as expected)
    PY
    rm lib/_scratch_copy.py

Run from cwd `app/`:  python -m pytest tests/test_narrative.py -q
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
import streamlit as st

APP_DIR = Path(__file__).resolve().parents[1]
ALLOWLIST_PATH = Path(__file__).resolve().parent / "digit_allowlist.txt"

# label=/help=/caption=/placeholder= only -- BUILD_PLAN_2A.md Stream G scope,
# not every kwarg a Streamlit call accepts (e.g. `format=`, `page_title=` are
# deliberately not scanned: out of the brief's named kwarg set).
KW_NAMES = {"label", "help", "caption", "placeholder"}

# Grounded in the real installed Streamlit API (see module docstring) --
# alias-proof and future-proof, unlike a hand-maintained name list.
ST_CALL_NAMES = ({n for n in dir(st) if not n.startswith("_") and callable(getattr(st, n, None))}
                  | {n for n in dir(st.column_config) if not n.startswith("_")})

SCOPE_B_FILES = [
    APP_DIR / "Menu.py",
    APP_DIR / "lib" / "views_find.py",
    APP_DIR / "lib" / "ranked.py",
    APP_DIR / "lib" / "filters.py",
    APP_DIR / "lib" / "badges.py",
    *sorted((APP_DIR / "pages").glob("*.py")),
]

PLACEHOLDER_RE = re.compile(r"\{[^{}]*\}")


def load_allowlist(path: Path = ALLOWLIST_PATH) -> list[str]:
    tokens = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        tokens.append(line)
    return tokens


def _allow_re(tokens: list[str]) -> re.Pattern:
    if not tokens:
        return re.compile(r"(?!)")  # matches nothing
    ordered = sorted(tokens, key=len, reverse=True)  # longest first: "PP(top10%)" before "top10"
    return re.compile("|".join(re.escape(t) for t in ordered))


def has_digit_violation(s: str, tokens: list[str]) -> bool:
    """A string violates the digit-ban if, after stripping every allowlisted
    token and every `{...}` placeholder, a digit character remains."""
    cleaned = _allow_re(tokens).sub("", s)
    cleaned = PLACEHOLDER_RE.sub("", cleaned)
    return bool(re.search(r"\d", cleaned))


def collect_copy_module_strings(copy_module) -> list[tuple[str, str]]:
    """Every uppercase module-level str / dict-of-str constant -- copy.py's
    own convention (mirrors its `scan_for_digit_violations`), reimplemented
    independently against the SHARED allowlist file rather than copy.py's
    own hard-coded `_ALLOWLIST_RE`, so the two can never silently drift
    apart unnoticed. Takes a module OBJECT (not an import path) so the
    non-vacuity proof can point it at a scratch module without touching
    sys.modules["lib.copy"]."""
    out = []
    mod_name = getattr(copy_module, "__name__", "copy")
    for name, value in vars(copy_module).items():
        if name.startswith("_") or not name.isupper():
            continue
        if isinstance(value, dict):
            for k, v in value.items():
                if isinstance(v, str):
                    out.append((f"{mod_name}::{name}[{k}]", v))
        elif isinstance(value, str):
            out.append((f"{mod_name}::{name}", value))
    return out


def _literal_parts(node: ast.AST) -> list[str]:
    """The literal text of a plain string Constant, or of a JoinedStr's own
    literal segments -- deliberately excludes a FormattedValue's
    `format_spec` (e.g. ',.0f', '.1%'): those are printf-style specs, not
    user-facing constant strings, and are structurally separate from
    JoinedStr.values so they are never visited here."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.JoinedStr):
        return [v.value for v in node.values
                if isinstance(v, ast.Constant) and isinstance(v.value, str)]
    return []


def collect_ui_call_strings(path: Path) -> list[tuple[str, str]]:
    """Every literal string passed positionally to a recognised Streamlit UI
    call, or via its label=/help=/caption=/placeholder= kwarg, in one file."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr in ST_CALL_NAMES):
            continue
        loc = f"{path.relative_to(APP_DIR)}:{node.lineno}"
        for arg in node.args:
            for s in _literal_parts(arg):
                out.append((loc, s))
        for kw in node.keywords:
            if kw.arg in KW_NAMES:
                for s in _literal_parts(kw.value):
                    out.append((loc, s))
    return out


def all_scoped_strings() -> list[tuple[str, str]]:
    from lib import copy as copy_mod

    # copy.FIND (Find-page strings, folded in from views_find.py's former
    # EXTRA_COPY dict by Stream X1) is scanned here too: it is an uppercase
    # module-level dict-of-str constant in lib/copy.py, exactly what
    # collect_copy_module_strings already walks -- no separate collector
    # needed, and scope (a) no longer needs a views_find.py import.
    out = collect_copy_module_strings(copy_mod)
    for f in SCOPE_B_FILES:
        out += collect_ui_call_strings(f)
    return out


# ------------------------------------------------------------------ tests --

def test_allowlist_has_required_tokens_and_stays_small():
    tokens = load_allowlist()
    required = {"L0", "L1", "L2f", "L3", "L4", "L5", "L6", "L7", "F1", "C1",
                "top10", "PP(top10%)"}
    missing = required - set(tokens)
    assert not missing, f"digit_allowlist.txt is missing required token(s): {sorted(missing)}"
    assert len(tokens) <= 15, (
        f"digit_allowlist.txt has {len(tokens)} non-comment lines (cap 15) -- "
        "a growing allowlist is the historical failure mode (BUILD_PLAN_2A.md Stream G)")


def test_scope_b_matcher_is_not_vacuous():
    """Guards the AST matcher itself: if this drops to ~0, ST_CALL_NAMES (or
    a file path) broke -- e.g. a Streamlit rename -- not that the app has no
    UI copy left to scan. 33 is the count measured against this build; the
    floor is set well below it."""
    total = sum(len(collect_ui_call_strings(f)) for f in SCOPE_B_FILES)
    assert total >= 20, f"only {total} UI-call strings found across scope (b) -- matcher likely broken"


def test_copy_and_extra_copy_scan_is_not_vacuous():
    from lib import copy as copy_mod
    n = len(collect_copy_module_strings(copy_mod))
    assert n >= 50, f"only {n} strings collected from copy.py (incl. copy.FIND) -- collector likely broken"


def test_no_digit_ban_violations():
    """The regression itself. A real violation here is an APPLICATION defect
    (a static string in pages/Menu.py/lib/{views_find,ranked,filters,badges}.py
    or lib/copy.py that types a digit the digit-ban forbids) -- Stream G owns
    the test, not the fix (BUILD_PLAN_2A.md dispatch contract); see
    progress/2A_G.md for what this run found."""
    tokens = load_allowlist()
    violations = [(loc, s) for loc, s in all_scoped_strings() if has_digit_violation(s, tokens)]
    if violations:
        detail = "\n".join(f"  {loc} -- {s!r}" for loc, s in violations)
        pytest.fail(f"{len(violations)} digit-ban violation(s) found (see progress/2A_G.md):\n{detail}")

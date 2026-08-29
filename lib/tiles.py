"""
app/lib/tiles.py -- the KPI tile (BUILD_PLAN_2A.md S9.2 L18, VIZ_SPEC.md
S2.11), copied in from Lorraine Phase 2 `Streamlit/pages/2_(factory)_
Laboratoires.py::_kpi_tile` (lines 1151-1178) and reduced to what BenchUp
needs: value + label + subline + an optional second subline (R2/L31, the
index baseline), no per-tile download button.

WHY HTML AND NOT `st.metric`: `st.metric` has no subline, and the subline is
the whole point -- the house rule "every KPI pairs its value with the
denominator or reference it is computed against" (BUILD_PLAN_2A.md L11) is
what the third line carries. `st.metric`'s delta arrow would also imply a
change-over-time reading that none of these eight one-snapshot measures has
(VIZ_SPEC.md S2.11, the named rejected alternative).

Two house rules this module obeys mechanically:
  * every colour comes from `lib.palette` (`tests/test_palette.py` fails the
    build on a `#RRGGBB` anywhere under `lib/` except `palette.py`);
  * every number inside the rendered markup is composed from a named int
    constant, never typed into the string -- the same discipline
    `lib/charts.py` follows, so this file stays clean if the digit-ban scope
    (`tests/test_narrative.py`) ever widens to it.

The caller passes ALREADY-FORMATTED strings: this module formats no number and
reads no data, so `n/a` (`palette.NA_MARK`) versus a value is the caller's
decision, taken once, in `lib/views_find.py`.
"""
from __future__ import annotations

import streamlit as st

from lib import palette as P

# Type scale (design-system/DESIGN_TOKENS.md S3, Lorraine's own tile sizes).
VALUE_PX = 22
META_PX = 12
VALUE_WEIGHT = 700
VALUE_LINE_HEIGHT = 1.25
META_LINE_HEIGHT = 1.4

# A stable hook so a test or the Playwright probe can count rendered tiles
# without matching a user-facing label (which would break with any copy edit).
TILE_CLASS = "benchup-kpi"
# R2/L31: a tile now carries TWO sublines -- its own denominator/reference line
# and the index-baseline line -- so the sublines get their own hook as well, and
# "every tile states where the seed sits in the population" becomes countable
# (`html.count(SUBLINE_CLASS) == 2`) rather than a claim about prose.
SUBLINE_CLASS = "benchup-kpi-sub"


def _esc(value) -> str:
    """Minimal HTML escape: these strings are institution-derived data, and
    they are injected with `unsafe_allow_html=True`."""
    return (str(value).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _subline_html(text: str) -> str:
    return (f'<div class="{SUBLINE_CLASS}" style="font-size:{META_PX}px;'
            f'line-height:{META_LINE_HEIGHT};color:{P.INK_SECONDARY};">{_esc(text)}</div>')


def tile_html(label: str, value: str, subline: str, subline2: str | None = None) -> str:
    """The tile's markup on its own (no Streamlit call) -- pure, so a test can
    assert on it without a running app.

    `subline2` (R2/L31) is the index-baseline line: "index median {m} . higher
    than {pct} of institutions". It is OPTIONAL rather than required so the tile
    stays usable where no baseline exists for a measure; where one does, the
    caller passes it and the tile renders four lines instead of three."""
    parts = [
        f'<div class="{TILE_CLASS}">',
        f'<div style="font-size:{VALUE_PX}px;font-weight:{VALUE_WEIGHT};'
        f'line-height:{VALUE_LINE_HEIGHT};color:{P.INK};">{_esc(value)}</div>',
        f'<div style="font-size:{META_PX}px;line-height:{META_LINE_HEIGHT};'
        f'color:{P.INK_SECONDARY};">{_esc(label)}</div>',
        _subline_html(subline),
    ]
    if subline2 is not None:
        parts.append(_subline_html(subline2))
    parts.append('</div>')
    return "".join(parts)


def kpi_tile(col, label: str, value: str, subline: str, subline2: str | None = None) -> None:
    """Render one tile into `col` (a `st.columns(...)` slot): a bordered
    container whose chrome is Streamlit's own `border=True` hairline, holding
    the three- or four-line block above."""
    with col:
        with st.container(border=True):
            st.markdown(tile_html(label, value, subline, subline2), unsafe_allow_html=True)

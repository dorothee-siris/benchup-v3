"""
app/lib/views_methods.py -- Stream M (Sprint 2 Phase 2B): the Methods page
(2B-9 / BUILD_PLAN_2B.md S0 A5).

`copy.METHODS` is a dict of `{title, body}` templates whose every number is a
`{placeholder}` filled at RUN TIME, never typed as a literal (the digit-ban
RULE at the top of lib/copy.py). `methods_values()` below is the one place
that fills them, from CFG (lib/app_config.py), the deploy/source manifest
(lib/data_cache.manifest()), the index (lib/data_cache.index()), two shipped
resource files (data/overrides/type_overrides.csv,
lib/engine/resources/sdg_labels.csv) and docs/data_contract.yaml's own prose
-- exactly the sources `progress/2B_N.md` S2 names for each placeholder.
`docs/METHODS_NOTE.md` is the human-readable twin of the same sections (never
rendered by the app; offered as a download at the foot of the page).

FOUR placeholders have no source reachable from inside the deployed `app/`
git repo and render `palette.NA_MARK` ("n/a") rather than a typed-in number
(the RULE's own escape hatch, never guessed):

  - `n_seeds`, `n_definitions` -- `V3/evals/aspirational_R2/**` sits outside
    the `app/` repo entirely (V3/app is its own git repo; `evals/` is a
    sibling of `app/`, not a subtree of it).
  - `n_unfound` -- `V3/INDICATOR_SPEC_v2.md` S8, same reason.
  - `n_gated` -- `V3/data/overrides/type_overrides_GATE_R2.md` is likewise
    outside `app/` (compare `app/data/overrides/`, which ships only
    `type_overrides.csv` and `umbrella_supplement.csv`), and no CFG key
    carries the count either. NOTE for the manager: `docs/data_contract.yaml`
    DOES carry a "0 gated rows remain" sentence for `overrides/type_overrides
    .csv`, but that sentence answers a different question (whether the
    shipped 34 rows are provisional) from the one `METHODS["types"]["body"]`
    asks (how many examined cases were left uncorrected) -- it is NOT used
    here as a stand-in; see V3/progress/2B_M.md S3 for the full note.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

from lib import copy
from lib.app_config import CFG
from lib.data_cache import DATA_DIR, erc, index, manifest, sdg, topics_dim
from lib.palette import NA_MARK
from lib.profile_data import SI_FLOOR_SOLID, SI_FLOOR_THIN
from lib.views_find import CORE_TOP_N

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"
CONTRACT_PATH = DOCS_DIR / "data_contract.yaml"
NOTE_PATH = DOCS_DIR / "METHODS_NOTE.md"
SDG_LABELS_PATH = Path(__file__).resolve().parent / "engine" / "resources" / "sdg_labels.csv"
OVERRIDES_PATH = DATA_DIR / "overrides" / "type_overrides.csv"
SOURCE_MANIFEST_PATH = DATA_DIR / "source_manifest.json"

# "one row per index institution (7,557 rows, population_rule: total>=200
# works, >=20 in EACH of 2023/2024)" -- docs/data_contract.yaml,
# files["index.parquet"]["grain"]. Two numbers, read off that ONE sentence
# rather than typed, so a contract edit that changes the population rule
# changes this page too.
_INDEX_GRAIN_RE = re.compile(r"total\s*>=\s*([\d,]+)\s*works.*?>=\s*([\d,]+)\s*in EACH", re.S)


def _index_floors() -> tuple[object, object]:
    """(floor_total, floor_recent) parsed from data_contract.yaml's own
    index.parquet grain string (BUILD_PLAN_2B.md S3 row M's own example).
    NA_MARK, NA_MARK if the contract prose the regex depends on ever
    reshapes -- never a stale literal."""
    try:
        contract = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
        grain = contract["files"]["index.parquet"]["grain"]
        m = _INDEX_GRAIN_RE.search(grain)
        if m:
            return int(m.group(1).replace(",", "")), int(m.group(2).replace(",", ""))
    except Exception:
        pass
    return NA_MARK, NA_MARK


def _bootstrap_reps() -> object:
    """source_manifest.json's own `bootstrap_reps`. NOT read through
    `manifest()`: that function prefers the deploy-time MANIFEST.json once
    ops/deploy.py has run, and MANIFEST.json does not carry this key (only
    source_manifest.json, the pre-staged pipeline manifest, does) -- so this
    reads the pre-staged file directly, the one place its own key survives."""
    if not SOURCE_MANIFEST_PATH.is_file():
        return NA_MARK
    try:
        data = json.loads(SOURCE_MANIFEST_PATH.read_text(encoding="utf-8"))
        return data["bootstrap_reps"]
    except Exception:
        return NA_MARK


def _sdg_numbers() -> tuple[int, object]:
    """(n_sdgs, missing): n_sdgs = distinct sdg_idx actually shipped in
    sdg.parquet; missing = the one SDG number (1..17) absent from
    sdg_labels.csv's own vocabulary, computed by set difference rather than
    typed in."""
    n = int(sdg()["sdg_idx"].nunique())
    try:
        labels = pd.read_csv(SDG_LABELS_PATH)
        covered = {int(x) for x in labels["sdg_number"]}
        gap = set(range(1, 18)) - covered
        missing: object = gap.pop() if len(gap) == 1 else NA_MARK
    except Exception:
        missing = NA_MARK
    return n, missing


def _n_overrides() -> object:
    """Row count of the shipped override list, read from the CSV itself
    (BUILD_PLAN_2B.md S3 row M's own instruction) rather than through a
    manifest field: `source_manifest.json`'s own `type_overrides.n_rows` is
    STALE on this snapshot (16, a pre-R2-T-scan count) while the file on
    disk carries 34 rows -- probed 2026-08-29, see V3/progress/2B_M.md."""
    try:
        return len(pd.read_csv(OVERRIDES_PATH))
    except Exception:
        return NA_MARK


def methods_values() -> dict:
    """Every `{placeholder}` copy.METHODS uses, filled from CFG / manifest()
    / index() / the resource files above. Keys match copy.METHODS_SOURCES
    exactly (tests/test_pages_methods.py cross-checks the two dicts don't
    drift)."""
    mf = manifest()
    idx = index()
    floor_total, floor_recent = _index_floors()
    n_sdgs, missing = _sdg_numbers()
    n_from_manifest = mf.get("files", {}).get("index.parquet", {}).get("n_rows")

    return {
        "n_countries": len(CFG["perimeter_countries"]),
        "y0": CFG["window"][0],
        "y1": CFG["window"][1],
        "bonus_year": CFG["bonus_year"],
        "n_trees": len(CFG["scenario"]["toggles"]["tree"]),
        "n_lenses": len(CFG["lenses"]["default"]),
        "concordance_n": CFG["concordance_N"],
        "depth_max": CFG["depth"]["max"],
        "core_top_n": CORE_TOP_N,
        "floor_solid": int(SI_FLOOR_SOLID),
        "floor_thin": int(SI_FLOOR_THIN),
        "floor_papers": CFG["l2f_floor"]["value"],
        "n_bootstrap": _bootstrap_reps(),
        "tau": CFG["erc_tau"],
        "n_panels": int(erc()["panel_idx"].nunique()),
        "n_sdgs": n_sdgs,
        "missing": missing,
        "n_excluded": int(topics_dim()["is_excluded"].fillna(False).sum()),
        "n_overrides": _n_overrides(),
        "n_gated": _fact("n_gated"),
        "n_institutions": n_from_manifest if n_from_manifest else len(idx),
        "floor_total": floor_total,
        "floor_recent": floor_recent,
        "snapshot": mf.get("snapshot") or CFG.get("snapshot", NA_MARK),
        "n_seeds": _fact("aspirational_seeds"),
        "n_definitions": _fact("aspirational_definitions"),
        "n_unfound": _fact("external_peers_unfound"),
    }


def _fact(key: str):
    """Manager addition 2026-08-29: facts whose source lives outside the app repo
    (gated type rows, the aspirational campaign, the recall ceiling) come from
    `config.yaml: methods_facts` with a provenance comment per value -- never
    typed in a string, never n/a for a known fact."""
    return CFG.get("methods_facts", {}).get(key, NA_MARK)


def _note_bytes() -> bytes:
    return NOTE_PATH.read_bytes()


def render() -> None:
    """The Methods page: title/lead from copy.NAV, the verdict line, one
    expander per copy.METHODS section in dict order, and a footer offering
    docs/METHODS_NOTE.md as a download alongside the snapshot stamp.

    NOTE for the manager (needs_change, V3/progress/2B_M.md S4): the two
    short strings the download button and its caption use are plain
    literals, not a copy.NAV/copy.METHODS key -- no such key exists yet and
    lib/copy.py is outside this stream's fence. Both are digit-free and
    carry no unresolved figure, so they satisfy the digit-ban as written."""
    values = methods_values()

    st.title(copy.NAV["METHODS_LABEL"])
    st.caption(copy.NAV["METHODS_LEAD"])
    st.markdown(f"**{copy.VERDICT_LINE}**")
    st.markdown("---")

    for section in copy.METHODS.values():
        title = section["title"].format(**values)
        with st.expander(title, expanded=False):
            st.markdown(section["body"].format(**values))

    st.markdown("---")
    mf = manifest()
    generated_at = (mf.get("source_manifest_generated_at") or mf.get("generated_at")
                    or mf.get("deployed_at") or NA_MARK)
    st.caption(copy.FIND["SNAPSHOT_CAPTION"].format(
        snapshot=values["snapshot"], generated_at=generated_at, sep=copy.STRIP_JOIN,
        n_institutions=f"{len(index()):,}"))
    st.download_button(
        copy.METHODS_UI["DOWNLOAD_LABEL"],
        _note_bytes,
        file_name="METHODS_NOTE.md",
        mime="text/markdown",
        key="dl_methods_note",
    )
    st.caption(
        copy.METHODS_UI["DOWNLOAD_CAPTION"]
    )

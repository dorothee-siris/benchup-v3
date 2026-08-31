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

SEVEN placeholders have no source reachable from inside the deployed `app/`
git repo and render `palette.NA_MARK` ("n/a") rather than a typed-in number
(the RULE's own escape hatch, never guessed) -- all seven come from
`config.yaml: methods_facts`, via `_fact()` below, each with its own
provenance comment in that file:

  - `n_seeds`, `n_definitions` -- `V3/evals/aspirational_R2/**` sits outside
    the `app/` repo entirely (V3/app is its own git repo; `evals/` is a
    sibling of `app/`, not a subtree of it).
  - `n_unfound` -- `V3/INDICATOR_SPEC_v2.md` S8, same reason.
  - `n_gated` -- 2BR/MU: value is 0 (`docs/data_contract.yaml`'s own
    `type_overrides.n_ids` grain note: "0 gated rows remain from any
    round"). BOTH gate files are stale: `type_overrides_GATE_R2.md`'s seven
    rows (CNR, TNO, VTT, DZHK, DZNE, DZL, DZIF) were applied this round
    (2B-R-3), and `type_overrides_GATE.md`'s four rows (NLDA, MAL, IMT,
    FUNIBER) were ALREADY applied at gate rev 6, predating 2B-R entirely --
    verified live against `type_overrides.csv` (`tests/test_pages_methods
    .py::test_n_gated_is_zero_every_previously_gated_case_is_now_applied`).
    A manager self-correction: a first pass here misread WT A5's "the R1
    gate's four still-gated ids STAY gated" as "remain unapplied"; it means
    their gate-rev-6 resolution stands unchanged, not that they are open.
    Kept in `config.yaml: methods_facts` anyway (rather than folded into
    `_n_overrides()`'s own live CSV read) because a future gate round WILL
    reopen a real case here, and `_fact()` is where that number belongs.
  - `intl_company_n_ids`, `intl_company_pct_resolved` -- P1
    (`V3/pipeline/14_fetch_inst_meta.py`) writes only
    `V3/data/interim/inst_meta_all.parquet`, interim and not shipped
    (2B-R-15); the id count and resolved share are the manager's own
    read-back of that pipeline run (`BUILD_PLAN_2BR.md` S7 P1 row).
  - `ci_coverage` -- the bootstrap alpha lives in
    `V3/pipeline/agg/impact.py::poisson_bootstrap_ci_vectorized`'s own
    default (0.05, never overridden at any call site), a pipeline constant
    with no CFG key; `tests/test_pages_methods.py` re-derives it from that
    file directly rather than trusting the config copy alone.

`collab_topic_floor` and `collab_topic_cap` are the one case that needed
NEITHER route: `collab_pairs.parquet`/`collab_pair_topics.parquet` ARE
shipped to `app/data/` (2B-R-15), so `_collab_pair_topic_facts()` below
measures them live off the actual tables instead of a hand-typed fact.
`dynamics_window_1`/`dynamics_window_2` likewise need no fact: PC's own
`window_conventions` block in `docs/data_contract.yaml` already carries the
exact label, read verbatim by `_window_conventions()` below (the same
read-the-contract-prose pattern `_index_floors()` above already uses).
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
from lib.charts_compare import LOW_VOLUME_FLOOR
from lib.data_cache import DATA_DIR, collab_pair_topics, collab_pairs, erc, index, manifest, sdg, topics_dim
from lib.palette import NA_MARK
from lib.profile_data import SI_FLOOR_SOLID, SI_FLOOR_THIN
from lib.views_collab import _sidebar_basket
from lib.views_find import CORE_TOP_N, _bundle, _sidebar_scenario

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


COLLAB_PAIRS_PATH = DATA_DIR / "collab_pairs.parquet"
COLLAB_PAIR_TOPICS_PATH = DATA_DIR / "collab_pair_topics.parquet"


@st.cache_resource(show_spinner=False)
def _collab_pair_topic_facts() -> dict:
    """2BR stream MU: the co-publication floor and topic cap the copub
    Methods section states are MEASURED off the shipped tables, not typed in
    -- P2 (`V3/pipeline/15_collab_pass.py`) sits outside the app repo, so
    unlike a CFG key these numbers have no config home of their own. The
    floor is the smallest `copubs_total` among pairs that made it into
    `collab_pair_topics.parquet`; the cap is the largest number of topic rows
    shipped for any one pair.

    Reads through `lib.data_cache.collab_pairs()`/`collab_pair_topics()`
    (stream CD's own `@st.cache_resource` loaders) rather than a second
    `pd.read_parquet` of the same 26/58 MB files: those two frames are
    already resident once any other page touches them, so this only ever
    pays a groupby/merge, never a duplicate load. `st.cache_resource` here
    (not `cache_data`, per the rest of this module's process-wide pattern)
    still caches the RESULT of that groupby, so this pays it at most once."""
    if not COLLAB_PAIRS_PATH.is_file() or not COLLAB_PAIR_TOPICS_PATH.is_file():
        return {"collab_topic_floor": NA_MARK, "collab_topic_cap": NA_MARK}
    try:
        pairs = collab_pairs()[["a", "b", "copubs_total"]]
        topics = collab_pair_topics()[["a", "b"]]
        n_topics = topics.groupby(["a", "b"], observed=True).size().reset_index(name="n_topics")
        merged = pairs.merge(n_topics, on=["a", "b"], how="inner")
        if merged.empty:
            return {"collab_topic_floor": NA_MARK, "collab_topic_cap": NA_MARK}
        return {
            "collab_topic_floor": int(merged["copubs_total"].min()),
            "collab_topic_cap": int(merged["n_topics"].max()),
        }
    except Exception:
        return {"collab_topic_floor": NA_MARK, "collab_topic_cap": NA_MARK}


def _window_conventions() -> dict:
    """The two Dynamics-window labels, read VERBATIM off
    docs/data_contract.yaml's own `window_conventions` block (PC's own
    additive entry, 2B-R-6/A7) rather than retyped here -- same pattern as
    `_index_floors()` above, one sentence in the contract, never a stale
    literal. NA_MARK for both if the block or either key is ever missing."""
    try:
        contract = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
        wc = contract["window_conventions"]
        return {
            "dynamics_window_1": wc["dynamics_window_1"],
            "dynamics_window_2": wc["dynamics_window_2"],
        }
    except Exception:
        return {"dynamics_window_1": NA_MARK, "dynamics_window_2": NA_MARK}


def _fmt_pct_fact(key: str) -> object:
    """A methods_facts value stored as a plain percentage number (e.g.
    99.81, not a 0-1 fraction) formatted to one decimal with a percent sign.
    NA_MARK passes through unchanged."""
    v = _fact(key)
    if v == NA_MARK or v is None:
        return NA_MARK
    return f"{float(v):.1f}%"


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
    collab_facts = _collab_pair_topic_facts()
    window_facts = _window_conventions()

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
        "collab_topic_floor": collab_facts["collab_topic_floor"],
        "collab_topic_cap": collab_facts["collab_topic_cap"],
        "intl_company_n_ids": _fact("intl_company_n_ids"),
        "intl_company_pct_resolved": _fmt_pct_fact("intl_company_pct_resolved"),
        "dynamics_window_1": window_facts["dynamics_window_1"],
        "dynamics_window_2": window_facts["dynamics_window_2"],
        "ci_coverage": _fact("impact_ci_coverage_pct"),
        "low_volume_floor": int(LOW_VOLUME_FLOOR),
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
    """The Methods page: the SAME sidebar as Compare/Collaborate (the scenario
    picker plus the read-only basket, Fix X-2B / BUILD_PLAN_2B.md
    progress/2B_H.md's second finding: this page had neither, the one gap in
    "all three downstream pages carry them" left over from Stream M), then
    title/lead from copy.NAV, the verdict line, one expander per
    copy.METHODS section in dict order, and a footer offering
    docs/METHODS_NOTE.md as a download alongside the snapshot stamp.

    The sidebar is READ-ONLY here exactly as on Collaborate, and costs no
    extra data load: `_bundle()` is the SAME process-wide `st.cache_resource`
    every other page already pays for once (views_find.py's own docstring),
    and `_sidebar_scenario()` only renders the tree/basis selectboxes -- this
    page never calls `_subs()`, so a tree/basis flip here never pays
    `build_substrates` (this page's numbers do not depend on either toggle).

    NOTE for the manager (needs_change, V3/progress/2B_M.md S4): the two
    short strings the download button and its caption use are plain
    literals, not a copy.NAV/copy.METHODS key -- no such key exists yet and
    lib/copy.py is outside this stream's fence. Both are digit-free and
    carry no unresolved figure, so they satisfy the digit-ban as written."""
    bundle = _bundle()
    _sidebar_scenario()
    _sidebar_basket(bundle)
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

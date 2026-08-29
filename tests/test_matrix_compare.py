"""
tests/test_matrix_compare.py -- Stream G: Compare/Collaborate toggle x filter
matrix (BUILD_PLAN_2B.md Stream G deliverable 2, brief item 2).

AppTest over the Compare page for the FULL cross product basket size
{2, 4, 6} x tree {bestfit, original} x basis {frac, full} -- 12 cells, run in
ONE module so `st.cache_resource` (the engine context, each (tree, basis)
substrate) stays warm across cells the same way tests/test_pages_compare.py's
own docstring describes: the first cell pays the cold engine load, every
later cell -- including the Collaborate cells at the end of this same file --
finds the substrate for its (tree, basis) already built. Only FOUR distinct
substrates exist across all 16 cells in this file (2 trees x 2 bases), so at
most four `build_substrates` calls ever run, not sixteen.

Per Compare cell:
  * the page renders with no exception;
  * the fields-mirror frame (the page's own cached wrapper, not a fresh
    compare_data call) sums to 1 per institution;
  * `frontier_mix` sums to 1 per institution (tree/basis-independent by
    contract -- re-checked per cell anyway, since it is the page's cache key
    that changes, not the frame's own maths);
  * the legend the page renders carries exactly one swatch per compared
    institution (basket size);
  * under basis="full" the ERC and SDG panel captions carry
    `copy.FIND["FRACTIONAL_ONLY_PANEL"]`, and never do under basis="frac";
  * the impact floor toggle 30 -> 10 never REDUCES the union frame's row
    count (a lower floor can only ADD subfields to the union, A1);
  * the `?compare=` deep link the page prints round-trips through
    `selection.parse_query` back to the same id list.

Then the Collaborate page x {bestfit, original} x {frac, full} for one pair
(4 cells): renders with no exception, and the shared-topics table's
Sigma(min_share) equals the engine's own L3 lens score for the pair under
that SAME scenario -- the identity tests/test_pages_collab.py already pins
at the default scenario, generalised here across all four.

Run from cwd `app/`:  python -m pytest tests/test_matrix_compare.py -q
"""
from __future__ import annotations

import itertools
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from lib import charts_compare, copy, selection, views_compare, views_collab
from lib.data_cache import DATA_DIR
from lib.engine import load_context, rank_all
from lib.views_find import _subs

APP_DIR = Path(__file__).resolve().parents[1]
COMPARE_PAGE = str(APP_DIR / "pages" / "2_⚖️_Compare.py")     # scales
COLLAB_PAGE = str(APP_DIR / "pages" / "3_\U0001F91D_Collaborate.py")    # handshake

STRASBOURG = "I68947357"    # Universite de Strasbourg -- the R1 reference seed
GDANSK = "I40413290"        # University of Gdansk -- panel_v2 D19 seed
IFPEN = "I265217849"        # IFP Energies nouvelles -- the RTO case
ISCTE = "I110026055"        # Iscte, Lisbon -- the SSH-heavy case
SORBONNE = "I39804081"
ETH = "I35440088"

TWO = [STRASBOURG, GDANSK]
FOUR = [STRASBOURG, GDANSK, IFPEN, ISCTE]
SIX = FOUR + [SORBONNE, ETH]
SIZE_TO_IDS = {2: TWO, 4: FOUR, 6: SIX}

TREES = ["bestfit", "original"]      # BUILD_PLAN_2B.md brief item 2's own pair
                                     # (config.yaml also ships "conservative",
                                     # out of scope for this matrix by name)
BASES = ["frac", "full"]

COMPARE_MATRIX = list(itertools.product([2, 4, 6], TREES, BASES))   # 12 cells
COLLAB_MATRIX = list(itertools.product(TREES, BASES))               # 4 cells


@pytest.fixture(scope="module")
def ctx():
    return load_context(str(DATA_DIR))


def _compare_app(ids, tree, basis) -> AppTest:
    at = AppTest.from_file(COMPARE_PAGE, default_timeout=600)
    at.session_state["basket"] = list(ids)
    at.session_state["tree"] = tree
    at.session_state["basis"] = basis
    return at.run()


def _collab_app(pair, tree, basis) -> AppTest:
    at = AppTest.from_file(COLLAB_PAGE, default_timeout=300)
    at.session_state["basket"] = list(pair)
    at.session_state["tree"] = tree
    at.session_state["basis"] = basis
    return at.run()


# --------------------------------------------------------- Compare matrix --

@pytest.mark.parametrize(
    "size,tree,basis", COMPARE_MATRIX,
    ids=[f"k{size}_{tree}_{basis}" for size, tree, basis in COMPARE_MATRIX])
def test_compare_matrix_cell(size, tree, basis, ctx):
    ids = SIZE_TO_IDS[size]
    at = _compare_app(ids, tree, basis)
    assert not at.exception, (size, tree, basis, [str(e) for e in at.exception])

    # -- fields-mirror frame: Sigma(share) == 1 per institution, off the
    # page's own cached wrapper (BUILD_PLAN_2B.md 2B-1's own contract).
    fields = views_compare._fields(tuple(ids), tree, basis)
    sums = fields.groupby("institution_id")["share"].sum()
    assert len(sums) == len(ids), (size, tree, basis, sums.to_dict())
    for iid, total in sums.items():
        assert total == pytest.approx(1.0, abs=1e-6), (size, tree, basis, iid, total)

    # -- frontier_mix: Sigma(share) == 1 per institution (A2's fifth segment).
    fmix = views_compare._frontier_mix(tuple(ids))
    fmix_sums = fmix.groupby("institution_id")["share"].sum()
    assert len(fmix_sums) == len(ids)
    for iid, total in fmix_sums.items():
        assert total == pytest.approx(1.0, abs=1e-5), (size, tree, basis, iid, total)

    # -- legend swatch count == basket size. institution_legend_html draws
    # one chip per (label, colour) pair it is handed; count the swatches by
    # counting the inline-style "background:" occurrences the builder emits
    # one of per chip (lib/charts.py::chip_legend_html), and cross-check the
    # exact markup appears verbatim on the rendered page (test_pages_compare.py's
    # own idiom), so this is not just checking the builder's input length.
    names = views_compare._names(ctx, ids)
    slots = views_compare._slots(ctx, ids)
    legend_html = charts_compare.institution_legend_html(names, slots)
    assert legend_html.count("background:") == len(ids), (
        size, tree, basis, legend_html)
    rendered = [m.value for m in at.markdown]
    assert legend_html in rendered, (size, tree, basis, "legend markup missing from the page")

    # -- basis == "full": the ERC and SDG captions carry FRACTIONAL_ONLY_PANEL;
    # basis == "frac": neither does.
    captions = [c.value for c in at.caption]
    if basis == "full":
        assert copy.FIND["FRACTIONAL_ONLY_PANEL"] in captions, (size, tree, basis, captions)
    else:
        assert copy.FIND["FRACTIONAL_ONLY_PANEL"] not in captions, (size, tree, basis, captions)

    # -- impact floor toggle 30 -> 10 never REDUCES the union row count (A1: a
    # lower floor only ADDS subfields to the union, never removes one).
    high, low = views_compare.IMPACT_FLOORS
    assert high > low
    union_high = views_compare._impact_subfields(tuple(ids), tree, high)
    union_low = views_compare._impact_subfields(tuple(ids), tree, low)
    assert len(union_low) >= len(union_high), (
        size, tree, basis, len(union_low), len(union_high))
    assert union_low["subfield_id"].nunique() >= union_high["subfield_id"].nunique()

    # -- the deep link the page prints round-trips through selection.parse_query.
    codes = [c.value for c in at.get("code")]
    link = selection.deeplink("compare", ids)
    assert link in codes, (size, tree, basis, codes)
    parsed = selection.parse_query({"compare": link.split("=", 1)[1]}, ids)
    assert parsed["compare"] == list(ids), (size, tree, basis, parsed)


def test_compare_matrix_covers_the_full_cross_product():
    """Non-vacuity of the matrix itself: 3 sizes x 2 trees x 2 bases, no
    accidental collapse (e.g. a broken itertools.product call producing far
    fewer cells than the brief's 12)."""
    assert len(COMPARE_MATRIX) == 12
    assert len({(s, t, b) for s, t, b in COMPARE_MATRIX}) == 12


# ------------------------------------------------------- Collaborate matrix --

@pytest.mark.parametrize(
    "tree,basis", COLLAB_MATRIX, ids=[f"{t}_{b}" for t, b in COLLAB_MATRIX])
def test_collab_matrix_cell_shared_topics_matches_engine_l3(tree, basis, ctx):
    a, b = STRASBOURG, GDANSK
    at = _collab_app((a, b), tree, basis)
    assert not at.exception, (tree, basis, [str(e) for e in at.exception])

    df = views_collab._shared_frame(a, b, tree, basis)
    page_score = float(df["min_share"].sum())

    subs = _subs(tree, basis)
    l3 = rank_all(ctx, subs, a)["L3"]
    engine_score = float(l3["scores"][ctx["id_pos"][b]])

    # tests/test_collab_data.py's OWN tolerance convention: atol=1e-6 (its
    # tighter check) on the frac/bestfit default, rtol=1e-5 wherever basis
    # or tree departs from that default (test_shared_topics_tree_invariant,
    # test_shared_topics_basis_full) -- basis="full" resums float32 vol_full-
    # normalised shares in a different order than the frac path, which moves
    # the last ULPs (same class of drift as the numpy-float32-sum-memory-
    # order lesson: bit-identical inputs, different accumulation order, ~1e-6
    # noise). A fixed abs=1e-6 is exactly what trips on that noise at full
    # basis while staying valid at frac -- so match K's own two-tier rule
    # instead of tightening past what the float32 path can deliver.
    tol = dict(rel=0, abs=1e-6) if (tree, basis) == ("bestfit", "frac") else dict(rel=1e-5, abs=1e-6)
    assert page_score == pytest.approx(engine_score, **tol), (
        tree, basis, page_score, engine_score)

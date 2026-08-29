"""
Stream R-B -- lib/links.py acceptance tests (BUILD_PLAN_2A.md S9.2 L23).
Run: python -m pytest tests/test_links.py -q
"""
from __future__ import annotations

from urllib.parse import unquote

from lib.links import copubs_url, ror_url, works_url


def test_works_url_contains_all_four_filters_and_no_raw_pipe():
    url = works_url("I40413290")
    assert "|" not in url, "raw pipe leaked into the URL unencoded"
    decoded = unquote(url)
    assert "authorships.institutions.id:I40413290" in decoded
    assert "publication_year:2020-2024" in decoded
    assert "type:article|review|book|book-chapter|letter" in decoded
    assert "has_doi:true" in decoded


def test_works_url_overrides():
    url = works_url("I1", years=(2015, 2019), types=["article"], has_doi=False)
    decoded = unquote(url)
    assert "publication_year:2015-2019" in decoded
    assert "type:article" in decoded
    assert "has_doi:false" in decoded


def test_ror_url_bare_and_full():
    assert ror_url("03xyz1234") == "https://ror.org/03xyz1234"
    assert ror_url("https://ror.org/03xyz1234") == "https://ror.org/03xyz1234"


def test_copubs_url_comma_form_and_no_plus():
    """A7 / WT-2B #13-14: the co-publications filter repeats the SAME key
    (`authorships.institutions.id`) once per institution, comma-joined --
    OpenAlex ANDs repeated filters on one key. The `+` intersection form is
    FORBIDDEN (it silently returns the first id's own count, HTTP 200, no
    error) -- assert it never appears in the built URL."""
    url = copubs_url("I68947357", "I21491767")
    assert "+" not in url, "the `+` intersection form leaked into the URL -- it is silently wrong"
    decoded = unquote(url)
    assert "authorships.institutions.id:I68947357" in decoded
    assert "authorships.institutions.id:I21491767" in decoded
    assert decoded.count("authorships.institutions.id:") == 2
    assert "publication_year:2020-2024" in decoded
    assert "type:article|review|book|book-chapter|letter" in decoded
    assert "has_doi:true" in decoded


def test_copubs_url_overrides():
    url = copubs_url("I1", "I2", years=(2023, 2023), types=["article"], has_doi=False)
    decoded = unquote(url)
    assert "publication_year:2023-2023" in decoded
    assert "type:article" in decoded
    assert "has_doi:false" in decoded
    assert "+" not in url

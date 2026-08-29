"""
Stream R-B -- lib/links.py acceptance tests (BUILD_PLAN_2A.md S9.2 L23).
Run: python -m pytest tests/test_links.py -q
"""
from __future__ import annotations

from urllib.parse import unquote

from lib.links import ror_url, works_url


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

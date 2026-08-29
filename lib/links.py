"""
app/lib/links.py -- outbound OpenAlex/ROR deep links (BUILD_PLAN_2A.md S9.2
L23): the works link now carries the SAME server-side filters the harvest
itself used (`pipeline/01b_harvest_eu27_aug.py` lines 10-14), not just the
publication-year window the pre-R1 card link had.
"""
from __future__ import annotations

from urllib.parse import quote

from lib.app_config import CFG

WORKS_BASE = "https://openalex.org/works"


def works_url(institution_id: str, *, years: tuple[int, int] | None = None,
             types: list[str] | None = None, has_doi: bool | None = None) -> str:
    """`https://openalex.org/works?filter=authorships.institutions.id:{id},
    publication_year:{y0}-{y1},type:t1|t2|...,has_doi:true` -- defaults from
    CFG (`window`, `corpus_types`, `openalex_filters.has_doi`); `|` is
    percent-encoded (`quote(filter_str, safe=":,-")`, Lorraine pattern) so the
    link survives copy/paste and markdown rendering unbroken."""
    y0, y1 = years if years is not None else CFG["window"]
    type_list = types if types is not None else CFG["corpus_types"]
    doi = CFG["openalex_filters"]["has_doi"] if has_doi is None else has_doi
    filt = (f"authorships.institutions.id:{institution_id},"
           f"publication_year:{y0}-{y1},"
           f"type:{'|'.join(type_list)},"
           f"has_doi:{'true' if doi else 'false'}")
    return f"{WORKS_BASE}?filter={quote(filt, safe=':,-')}"


def ror_url(ror_id: str) -> str:
    """Accepts a bare ROR id (e.g. `03xyz1234`) or an already-full
    `https://ror.org/...` URL (index.parquet ships the full URL -- this stays
    a no-op passthrough for that shape, and builds the URL for a bare id)."""
    ror_id = ror_id.strip()
    return ror_id if ror_id.startswith("http") else f"https://ror.org/{ror_id}"

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


def copubs_url(institution_a: str, institution_b: str, *, years: tuple[int, int] | None = None,
               types: list[str] | None = None, has_doi: bool | None = None) -> str:
    """Co-publications between two institutions on OpenAlex (BUILD_PLAN_2B.md
    §4, A7): the SAME `authorships.institutions.id` key repeated once per
    institution, comma-joined -- OpenAlex ANDs repeated filters on one key
    (Wind Tunnel 2B #13, VERIFIED with live `filter=` calls, $0.0008: A alone
    5,211 / B alone 8,827 / both keys repeated 174, Universite de Strasbourg x
    Aix-Marseille Universite, 2023). The `+` intersection form is FORBIDDEN --
    `id:A+B` silently returns A's own count with HTTP 200, no error (#14) --
    never build the filter that way here."""
    y0, y1 = years if years is not None else CFG["window"]
    type_list = types if types is not None else CFG["corpus_types"]
    doi = CFG["openalex_filters"]["has_doi"] if has_doi is None else has_doi
    filt = (f"authorships.institutions.id:{institution_a},"
           f"authorships.institutions.id:{institution_b},"
           f"publication_year:{y0}-{y1},"
           f"type:{'|'.join(type_list)},"
           f"has_doi:{'true' if doi else 'false'}")
    return f"{WORKS_BASE}?filter={quote(filt, safe=':,-')}"


TAXON_FILTER_KEY = {
    "topic": "primary_topic.id",
    "subfield": "primary_topic.subfield.id",
    "field": "primary_topic.field.id",
}
TAXON_LEVELS = tuple(TAXON_FILTER_KEY)


def copubs_taxon_url(institution_a: str, institution_b: str, level: str, taxon_id,
                     *, years: tuple[int, int] | None = None, types: list[str] | None = None,
                     has_doi: bool | None = None) -> str:
    """CD3 2B-R2-11(e): a pair's co-publications RESTRICTED to one taxon (a
    topic, subfield or field row of a Collaborate table) -- the same repeated-
    key AND convention `copubs_url` already verified live (Wind Tunnel 2B #13:
    OpenAlex ANDs two `authorships.institutions.id:` filters, never a `+`
    union, #14), with ONE more repeated key added: `primary_topic.id:`,
    `primary_topic.subfield.id:` or `primary_topic.field.id:` depending on
    `level` -- OpenAlex's own taxonomy nesting on the work's PRIMARY topic,
    matching the pair tables' own `topic_id`/`field_id` grain (never the
    tree-specific `{tree}_subfield_id` BenchUp repairs internally: OpenAlex
    has no concept of BenchUp's repaired trees, so a SUBFIELD-level link uses
    the topic's OpenAlex-native subfield, a documented approximation on the
    conservative/original trees' repaired cells).

    Construct-only (WT 2B-R2 claim #23/24-adjacent 2BR2 A4): no live call is
    made here or required before shipping -- the shape is verified against
    `copubs_url`'s own already-live-verified convention, not by a fresh probe."""
    if level not in TAXON_LEVELS:
        raise ValueError(f"level must be one of {TAXON_LEVELS}, got {level!r}")
    y0, y1 = years if years is not None else CFG["window"]
    type_list = types if types is not None else CFG["corpus_types"]
    doi = CFG["openalex_filters"]["has_doi"] if has_doi is None else has_doi
    filt = (f"authorships.institutions.id:{institution_a},"
           f"authorships.institutions.id:{institution_b},"
           f"{TAXON_FILTER_KEY[level]}:{taxon_id},"
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

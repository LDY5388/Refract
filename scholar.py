"""
Refract - Semantic Scholar API Client v2
Works with ParsedReference dataclass from parser.py
"""

import time
import requests
from dataclasses import dataclass

BASE_URL = "https://api.semanticscholar.org/graph/v1"

PAPER_FIELDS = ",".join([
    "title", "abstract", "authors", "year",
    "citationCount", "referenceCount",
    "fieldsOfStudy", "url", "externalIds", "tldr",
])


@dataclass
class ScholarData:
    title: str | None = None
    abstract: str | None = None
    authors: list[str] | None = None
    year: int | None = None
    citation_count: int | None = None
    fields: list[str] | None = None
    url: str | None = None
    tldr: str | None = None
    doi: str | None = None


def search_paper(query: str, limit: int = 3) -> list[dict]:
    url = f"{BASE_URL}/paper/search"
    params = {"query": query, "limit": limit, "fields": PAPER_FIELDS}
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json().get("data", [])
    except requests.RequestException as e:
        return [{"error": str(e)}]


def enrich_references(parsed_refs: dict, delay: float = 0.5) -> dict:
    """
    For each ParsedReference, search Semantic Scholar.
    Returns dict with same keys, values are dicts with:
      - all original ParsedReference fields
      - scholar_data: ScholarData or None
      - match_status: "found" or "not_found"
    """
    enriched = {}

    for key, ref in parsed_refs.items():
        query = ref.search_query or ref.extracted_title or ref.raw_text[:120]
        query = query.strip()[:200]

        results = search_paper(query, limit=1)

        if results and "error" not in results[0]:
            best = results[0]
            sd = ScholarData(
                title=best.get("title"),
                abstract=best.get("abstract"),
                authors=[a.get("name", "") for a in best.get("authors", [])],
                year=best.get("year"),
                citation_count=best.get("citationCount"),
                fields=best.get("fieldsOfStudy"),
                url=best.get("url"),
                tldr=best.get("tldr", {}).get("text") if best.get("tldr") else None,
                doi=best.get("externalIds", {}).get("DOI"),
            )
            enriched[key] = {
                "key": key,
                "raw": ref.raw_text,
                "extracted_title": ref.extracted_title,
                "authors": ref.authors,
                "year": ref.year,
                "citation_contexts": ref.citation_contexts,
                "scholar_data": {
                    "title": sd.title,
                    "abstract": sd.abstract,
                    "authors": sd.authors,
                    "year": sd.year,
                    "citation_count": sd.citation_count,
                    "fields": sd.fields,
                    "url": sd.url,
                    "tldr": sd.tldr,
                    "doi": sd.doi,
                },
                "match_status": "found",
            }
        else:
            enriched[key] = {
                "key": key,
                "raw": ref.raw_text,
                "extracted_title": ref.extracted_title,
                "authors": ref.authors,
                "year": ref.year,
                "citation_contexts": ref.citation_contexts,
                "scholar_data": None,
                "match_status": "not_found",
            }

        time.sleep(delay)

    return enriched


def format_authors(authors: list[str], max_show: int = 3) -> str:
    if not authors:
        return "Unknown"
    if len(authors) <= max_show:
        return ", ".join(authors)
    return ", ".join(authors[:max_show]) + f" et al. (+{len(authors) - max_show})"

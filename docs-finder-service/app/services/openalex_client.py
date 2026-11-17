import logging
import time
from typing import Any, Optional

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "DocsFinderService/1.0 (academic paper discovery)",
    "Accept": "application/json",
})


def _request_json(params: dict) -> Optional[dict]:
    request_params = dict(params)
    if settings.OPENALEX_MAILTO:
        request_params["mailto"] = settings.OPENALEX_MAILTO

    for attempt in range(settings.OPENALEX_RETRIES + 1):
        try:
            response = SESSION.get(
                settings.OPENALEX_BASE_URL,
                params=request_params,
                timeout=settings.OPENALEX_TIMEOUT,
            )
            if response.status_code == 429 and attempt < settings.OPENALEX_RETRIES:
                time.sleep(min(2 ** attempt, 5))
                continue
            if response.status_code in (500, 502, 503, 504) and attempt < settings.OPENALEX_RETRIES:
                time.sleep(1 + attempt)
                continue
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            if attempt >= settings.OPENALEX_RETRIES:
                logger.warning("OpenAlex request failed: %s", exc)
                return None
            time.sleep(1 + attempt)
    return None


def restore_abstract(inverted_index: Optional[dict]) -> str:
    """OpenAlex stores abstracts as word-position maps; restore normal text."""
    if not inverted_index:
        return ""
    positioned_words = []
    for word, positions in inverted_index.items():
        for position in positions:
            positioned_words.append((position, word))
    positioned_words.sort(key=lambda item: item[0])
    return " ".join(word for _, word in positioned_words)


def search_works(query: str, limit: int) -> list[dict[str, Any]]:
    params = {
        "search": query,
        "per-page": min(max(limit, 1), 100),
        "select": (
            "id,doi,title,publication_year,authorships,primary_location,"
            "abstract_inverted_index,type"
        ),
    }
    payload = _request_json(params)
    if not payload:
        return []

    works = []
    for item in payload.get("results", []):
        authors = []
        for authorship in (item.get("authorships") or [])[:5]:
            author = (authorship.get("author") or {}).get("display_name")
            if author:
                authors.append(author)

        location = item.get("primary_location") or {}
        source = location.get("source") or {}
        doi = item.get("doi")
        openalex_id = item.get("id") or ""
        works.append({
            "title": item.get("title") or "Untitled",
            "authors": ", ".join(authors) or "Authors not specified",
            "year": item.get("publication_year"),
            "venue": source.get("display_name") or item.get("type"),
            "abstract": restore_abstract(item.get("abstract_inverted_index")),
            "doi": doi,
            "url": doi or openalex_id,
            "openalex_id": openalex_id,
        })
    return works

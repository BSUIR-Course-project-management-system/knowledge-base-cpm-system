import logging
import re
from typing import Any

import numpy as np

from app.core.config import settings
from app.services.embedding_service import encode_texts
from app.services.openalex_client import search_works

logger = logging.getLogger(__name__)


def translate_query(query: str) -> str:
    """Best-effort Russian-to-English translation for OpenAlex retrieval.

    BGE-M3 itself is multilingual. Translation is only an additional retrieval
    route because OpenAlex search may return better coverage for English terms.
    If translation is unavailable, the original query still works.
    """
    if not re.search(r"[А-Яа-яЁё]", query):
        return query
    try:
        from deep_translator import GoogleTranslator
        translated = GoogleTranslator(source="auto", target="en").translate(query)
        return translated.strip() if translated and translated.strip() else query
    except Exception as exc:
        logger.info("Query translation skipped: %s", exc)
        return query


def _dedup_key(paper: dict[str, Any]) -> str:
    doi = (paper.get("doi") or "").lower().strip()
    if doi:
        return doi
    title = re.sub(r"[^a-z0-9а-яё]+", "", (paper.get("title") or "").lower())
    return title or paper.get("openalex_id", "")


def _text_for_embedding(paper: dict[str, Any]) -> str:
    title = (paper.get("title") or "").strip()
    abstract = (paper.get("abstract") or "").strip()
    # Повтор названия немного увеличивает его вклад в общий текст.
    return f"{title}. {title}. {abstract}" if abstract else title


def search_papers(query: str, limit: int = 10) -> list[dict[str, Any]]:
    query = query.strip()
    if not query:
        return []

    translated = translate_query(query)
    query_variants = list(dict.fromkeys(
        value for value in (query, translated) if value
    ))

    candidate_limit = min(max(settings.CANDIDATE_LIMIT, limit), 100)
    candidates = []
    for variant in query_variants:
        candidates.extend(search_works(variant, candidate_limit))

    unique = {}
    for paper in candidates:
        key = _dedup_key(paper)
        if key and (
            key not in unique
            or len(paper.get("abstract", "")) > len(unique[key].get("abstract", ""))
        ):
            unique[key] = paper

    papers = list(unique.values())
    if not papers:
        return []

    query_vectors = encode_texts(query_variants)
    paper_texts = [_text_for_embedding(paper) for paper in papers]
    paper_vectors = encode_texts(paper_texts)

    # Векторы нормализованы, поэтому dot product равен cosine similarity.
    similarities = np.matmul(paper_vectors, query_vectors.T)
    scores = similarities.max(axis=1)

    for paper, score in zip(papers, scores):
        # Это относительная семантическая близость, не вероятность качества.
        paper["relevance"] = round(float(score), 4)

    papers.sort(key=lambda item: item["relevance"], reverse=True)
    return papers[:limit]

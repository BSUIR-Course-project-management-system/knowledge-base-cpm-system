from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional, Set

import requests

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "AcademicSourceFinder/1.1 (educational research tool)",
    "Accept": "application/json",
})

OPENALEX_URL = "https://api.openalex.org/works"

STOP_WORDS = {
    "the", "and", "for", "with", "from", "into", "using", "use", "based",
    "about", "study", "research", "of", "in", "on", "to", "a", "an",
    "и", "в", "во", "на", "для", "по", "с", "со", "из", "от", "о", "об",
    "как", "при", "над", "под", "исследование", "исследования", "изучение",
}

ALIASES = {
    "robot": {"robot", "robots", "robotic", "robotics", "робот", "роботы",
              "робота", "роботов", "робототехника", "роботизированный"},
    "computer": {"computer", "computers", "компьютер", "компьютерное",
                 "компьютерный", "вычислительный"},
    "vision": {"vision", "visual", "визуальный", "зрение", "машинное"},
    "learning": {"learning", "learn", "обучение", "обучения"},
    "medical": {"medical", "medicine", "clinical", "медицина", "медицинский",
                "клинический"},
}


def translate_to_english(text: str) -> str:
    """Переводит запрос, но не ломает поиск при недоступности переводчика."""
    if not re.search(r"[А-Яа-яЁё]", text):
        return text
    try:
        from deep_translator import GoogleTranslator
        result = GoogleTranslator(source="auto", target="en").translate(text)
        return result.strip() if result and result.strip() else text
    except Exception:
        return text


def _request_json(url: str, params: dict, retries: int = 2) -> Optional[dict]:
    """GET JSON с таймаутом и ограниченным числом повторов."""
    for attempt in range(retries + 1):
        try:
            response = SESSION.get(url, params=params, timeout=20)
            if response.status_code == 429:
                if attempt < retries:
                    retry_after = response.headers.get("Retry-After", "")
                    try:
                        delay = min(max(int(retry_after), 1), 5)
                    except (TypeError, ValueError):
                        delay = min(2 ** attempt, 5)
                    time.sleep(delay)
                    continue
                return None

            if response.status_code in (500, 502, 503, 504) and attempt < retries:
                time.sleep(1 + attempt)
                continue

            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError):
            if attempt < retries:
                time.sleep(1 + attempt)
            else:
                return None
    return None


def _clean_abstract(value: Optional[str], limit: int = 1200) -> str:
    if not value:
        return ""
    value = re.sub(r"\s+", " ", str(value)).strip()
    return value if len(value) <= limit else value[:limit].rsplit(" ", 1)[0] + "..."


def _openalex_abstract(inverted_index: Optional[dict]) -> str:
    """Восстанавливает аннотацию из inverted index OpenAlex."""
    if not inverted_index:
        return ""
    words = []
    for word, positions in inverted_index.items():
        for position in positions:
            words.append((position, word))
    words.sort(key=lambda pair: pair[0])
    return " ".join(word for _, word in words)


def _search_openalex(query: str, limit: int) -> List[Dict[str, Any]]:
    params = {
        "search": query,
        "per-page": min(max(limit, 1), 100),
        "select": (
            "id,doi,title,publication_year,authorships,primary_location,"
            "abstract_inverted_index,relevance_score,type"
        ),
    }
    payload = _request_json(OPENALEX_URL, params)
    if not payload:
        return []

    papers = []
    for item in payload.get("results", []):
        authors = []
        for authorship in (item.get("authorships") or [])[:5]:
            name = (authorship.get("author") or {}).get("display_name")
            if name:
                authors.append(name)

        location = item.get("primary_location") or {}
        source = location.get("source") or {}
        doi = item.get("doi")
        papers.append({
            "title": item.get("title") or "Без названия",
            "authors": ", ".join(authors) or "Авторы не указаны",
            "date": str(item.get("publication_year") or "Год не указан"),
            "url": doi or item.get("id") or "",
            "abstract": _clean_abstract(
                _openalex_abstract(item.get("abstract_inverted_index"))
            ),
            "categories": " | ".join(filter(None, [
                item.get("type"), source.get("display_name"), "OpenAlex"
            ])),
            "doi": doi,
            "source": "OpenAlex",
        })
    return papers


def _canonical_word(word: str) -> str:
    for canonical, variants in ALIASES.items():
        if word in variants:
            return canonical
    return word


def _tokens(text: str) -> Set[str]:
    words = re.findall(r"[a-zа-яё0-9]+", (text or "").lower())
    return {
        _canonical_word(w)
        for w in words
        if len(w) > 2 and w not in STOP_WORDS
    }


def _term_is_present(term: str, document_tokens: Set[str]) -> bool:
    return _canonical_word(term) in document_tokens


def _query_terms(query: str) -> List[str]:
    """Получает содержательные слова запроса без служебных слов."""
    return sorted(_tokens(query))


def _relevance_score(paper: Dict[str, Any], query_variants: List[str]) -> float:
    """Единая оценка: название важнее аннотации, учитывается покрытие запроса."""
    title_tokens = _tokens(paper.get("title", ""))
    abstract_tokens = _tokens(paper.get("abstract", ""))
    full_tokens = title_tokens | abstract_tokens

    best_score = 0.0
    for query in query_variants:
        terms = _query_terms(query)
        if not terms:
            continue

        matched_title = sum(_term_is_present(t, title_tokens) for t in terms)
        matched_all = sum(_term_is_present(t, full_tokens) for t in terms)
        title_coverage = matched_title / len(terms)
        total_coverage = matched_all / len(terms)

        # Сильный бонус за слова в заголовке; небольшая прибавка за аннотацию.
        score = (title_coverage * 70) + (total_coverage * 30)

        # Совпадение всей короткой темы особенно важно.
        if len(terms) <= 4 and matched_all == len(terms):
            score += 15

        best_score = max(best_score, score)

    return min(best_score, 100.0)


def _dedup_key(paper: Dict[str, Any]) -> str:
    doi = (paper.get("doi") or "").lower().strip()
    if doi:
        return doi
    return re.sub(r"[^a-z0-9а-яё]+", "", paper.get("title", "").lower())


def search_openalex(
    query: str,
    max_results: int = 5,
    *,
    include_sources: bool = False,
) -> List[Dict[str, Any]]:
    query = (query or "").strip()
    if not query:
        return []

    try:
        max_results = min(max(int(max_results), 1), 30)
    except (TypeError, ValueError):
        max_results = 5

    english_query = translate_to_english(query)
    query_variants = list(dict.fromkeys(
        q.strip() for q in (english_query, query) if q and q.strip()
    ))

    collected: List[Dict[str, Any]] = []

    for search_query in query_variants:
        collected.extend(_search_openalex(search_query, max_results * 5))

    # Удаляем дубликаты, сохраняя запись с наиболее полной аннотацией.
    unique: Dict[str, Dict[str, Any]] = {}
    for paper in collected:
        key = _dedup_key(paper)
        if not key:
            continue
        previous = unique.get(key)
        if previous is None or len(paper.get("abstract", "")) > len(previous.get("abstract", "")):
            unique[key] = paper

    ranked = []
    for paper in unique.values():
        score = _relevance_score(paper, query_variants)
        paper["relevance"] = round(score, 1)
        ranked.append(paper)

    best_terms = max((_query_terms(q) for q in query_variants), key=len, default=[])
    threshold = 55 if len(best_terms) <= 4 else 40
    ranked = [paper for paper in ranked if paper["relevance"] >= threshold]

    ranked.sort(key=lambda paper: paper["relevance"], reverse=True)

    if not include_sources:
        for paper in ranked:
            paper.pop("source", None)

    return ranked[:max_results]


def search_semantic_scholar(
    query: str,
    max_results: int = 5,
    *,
    include_sources: bool = False,
) -> List[Dict[str, Any]]:
    """Совместимость со старым main.py; фактически ищет только в OpenAlex."""
    return search_openalex(
        query,
        max_results=max_results,
        include_sources=include_sources,
    )

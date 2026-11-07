from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

OPENALEX_URL = "https://api.openalex.org/works"

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "AcademicSourceFinder/2.0 (educational research tool)",
    "Accept": "application/json",
})

# docs_finder_module и search_module находятся рядом в корне проекта.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = PROJECT_ROOT / "search_module" / "models" / "all-MiniLM-L6-v2"

_MODEL = None


def _get_model():
    """Загружает локальную модель один раз за запуск программы."""
    global _MODEL
    if _MODEL is None:
        if not MODEL_PATH.is_dir():
            raise FileNotFoundError(
                "Не найдена локальная модель all-MiniLM-L6-v2. "
                f"Ожидаемый путь: {MODEL_PATH}"
            )

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "Для семантического поиска установите sentence-transformers: "
                "pip install sentence-transformers"
            ) from exc

        # Выбор устройства аналогичен ThemeFinder в search_module.
        try:
            import torch
            if torch.backends.mps.is_available():
                device = "mps"
            elif torch.cuda.is_available():
                device = "cuda"
            else:
                device = "cpu"
        except ImportError:
            device = "cpu"

        _MODEL = SentenceTransformer(str(MODEL_PATH), device=device)

    return _MODEL


def translate_to_english(text: str) -> str:
    """Переводит русский запрос для OpenAlex; при сбое оставляет оригинал."""
    if not re.search(r"[А-Яа-яЁё]", text):
        return text

    try:
        from deep_translator import GoogleTranslator
        translated = GoogleTranslator(source="auto", target="en").translate(text)
        return translated.strip() if translated and translated.strip() else text
    except Exception:
        return text


def _request_json(url: str, params: dict, retries: int = 2) -> Optional[dict]:
    """GET JSON с таймаутом и ограниченным числом повторов."""
    for attempt in range(retries + 1):
        try:
            response = SESSION.get(url, params=params, timeout=25)

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


def _clean_abstract(value: Optional[str], limit: int = 4000) -> str:
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
            author = (authorship.get("author") or {}).get("display_name")
            if author:
                authors.append(author)

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


def _dedup_key(paper: Dict[str, Any]) -> str:
    doi = (paper.get("doi") or "").lower().strip()
    if doi:
        return doi
    return re.sub(r"[^a-z0-9а-яё]+", "", paper.get("title", "").lower())


def _paper_text(paper: Dict[str, Any]) -> str:
    """Собирает текст для сравнения; заголовок повторяется для его усиления."""
    title = (paper.get("title") or "").strip()
    abstract = (paper.get("abstract") or "").strip()

    if abstract:
        return f"{title}. {title}. {abstract}"
    return title


def _semantic_rerank(
    papers: List[Dict[str, Any]],
    query_variants: List[str],
) -> List[Dict[str, Any]]:
    """Ранжирует статьи по cosine similarity модели all-MiniLM-L6-v2."""
    if not papers:
        return []

    model = _get_model()
    documents = [_paper_text(paper) for paper in papers]

    # Нормализованные embeddings позволяют считать cosine similarity
    # обычным скалярным произведением.
    document_vectors = model.encode(
        documents,
        batch_size=32,
        show_progress_bar=False,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )

    query_vectors = model.encode(
        query_variants,
        show_progress_bar=False,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )

    # Сравниваем каждый документ с вариантами запроса (перевод и оригинал)
    # и берём максимальную близость.
    similarities = document_vectors @ query_vectors.T
    scores = similarities.max(axis=1)

    ranked = []
    for paper, score in zip(papers, scores):
        # Процент — удобная шкала отображения cosine similarity,
        # это не вероятность и не научная оценка качества статьи.
        paper["relevance"] = round(float(score) * 100, 1)
        ranked.append(paper)

    ranked.sort(key=lambda paper: paper["relevance"], reverse=True)
    return ranked


def search_openalex(
    query: str,
    max_results: int = 5,
    *,
    include_sources: bool = False,
) -> List[Dict[str, Any]]:
    """Ищет публикации в OpenAlex и сортирует их по семантической близости."""
    query = (query or "").strip()
    if not query:
        return []

    try:
        max_results = min(max(int(max_results), 1), 30)
    except (TypeError, ValueError):
        max_results = 5

    translated_query = translate_to_english(query)
    query_variants = list(dict.fromkeys(
        value.strip()
        for value in (translated_query, query)
        if value and value.strip()
    ))

    # Запрашиваем расширенную выборку, потому что после семантической
    # сортировки порядок OpenAlex уже не является окончательным.
    fetch_limit = min(max(max_results * 10, 50), 100)
    collected: List[Dict[str, Any]] = []

    for search_query in query_variants:
        collected.extend(_search_openalex(search_query, fetch_limit))

    unique: Dict[str, Dict[str, Any]] = {}
    for paper in collected:
        key = _dedup_key(paper)
        if not key:
            continue

        previous = unique.get(key)
        if previous is None or len(paper.get("abstract", "")) > len(previous.get("abstract", "")):
            unique[key] = paper

    ranked = _semantic_rerank(list(unique.values()), query_variants)

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
    """Старое имя функции сохранено для совместимости с main.py."""
    return search_openalex(
        query,
        max_results=max_results,
        include_sources=include_sources,
    )

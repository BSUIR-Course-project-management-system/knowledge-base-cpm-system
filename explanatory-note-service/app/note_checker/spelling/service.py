"""Оркестрация орфографии: фрагменты -> чанки -> спеллер -> замечания."""

from __future__ import annotations

import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor

from ..checkers.common import make_finding
from ..extraction.common import BIBLIOGRAPHY_TITLES, normalize_title
from ..model import DocumentModel, Finding, FragmentKind
from ..rules.schema import Rule
from .base import SpellError, SpellingChecker
from .chunker import build_chunks, entry_at
from .dictionary import DEFAULT_DICTIONARY_PATH, is_excluded, load_dictionary
from .yandex import SpellerUnavailable, create_checker_from_env

logger = logging.getLogger(__name__)

_SPELL_KINDS = {
    FragmentKind.paragraph,
    FragmentKind.heading,
    FragmentKind.caption,
    FragmentKind.list_item,
}
_CITATION_RE = re.compile(r"^\s*\[\d+\]")
_URL_RE = re.compile(r"https?://|www\.", re.IGNORECASE)

_checker: SpellingChecker | None = None
_checker_ready = False


def get_checker() -> SpellingChecker | None:
    global _checker, _checker_ready
    if not _checker_ready:
        _checker = create_checker_from_env()
        _checker_ready = True
    return _checker


def reset_checker() -> None:
    """Сбрасывает клиент; используется в тестах."""
    global _checker, _checker_ready
    close = getattr(_checker, "close", None)
    if callable(close):
        close()
    _checker = None
    _checker_ready = False


def check_spelling(document: DocumentModel, rule: Rule) -> list[Finding]:
    checker = get_checker()
    if checker is None:
        return []

    try:
        dictionary = load_dictionary(
            os.getenv("SPELLING_DICTIONARY_PATH", str(DEFAULT_DICTIONARY_PATH))
        )
    except OSError as exc:
        logger.warning("Словарь исключений не загружен: %s", exc)
        dictionary = frozenset()
    chunk_chars = int(os.getenv("SPELLER_CHUNK_CHARS", "9500"))
    max_workers = max(1, int(os.getenv("SPELLER_PARALLEL_REQUESTS", "2")))
    fragments = _spellable_fragments(document)
    chunks = build_chunks(fragments, chunk_chars)
    if not chunks:
        return []

    texts = [chunk.text for chunk in chunks]
    try:
        if max_workers > 1 and len(texts) > 1:
            with ThreadPoolExecutor(max_workers=min(max_workers, len(texts))) as pool:
                responses = list(pool.map(checker.check, texts))
        else:
            responses = [checker.check(text) for text in texts]
    except SpellerUnavailable as exc:
        logger.warning("Проверка орфографии пропущена: %s", exc)
        return []

    findings: list[Finding] = []
    seen: set[tuple[int, str]] = set()
    for chunk, errors in zip(chunks, responses):
        for error in errors:
            entry = entry_at(chunk, error.pos)
            if entry is None:
                continue
            word = error.word or chunk.text[error.pos : error.pos + error.length]
            if not word or is_excluded(word, dictionary):
                continue
            location = entry.fragment.location.model_copy(deep=True)
            local_offset = max(error.pos - entry.start, 0)
            location.order = location.order * 1000 + min(local_offset, 999)
            key = (location.order, word.casefold())
            if key in seen:
                continue
            seen.add(key)
            findings.append(_finding(rule, location, word, error))
    return findings


def _spellable_fragments(document: DocumentModel) -> list:
    bibliography_order = _bibliography_order(document)
    result = []
    for fragment in document.fragments:
        if fragment.kind not in _SPELL_KINDS:
            continue
        text = fragment.text.strip()
        if not text or not re.search(r"[А-Яа-яЁё]{2,}", text):
            continue
        if (
            bibliography_order is not None
            and fragment.location.order > bibliography_order
        ):
            continue
        if _CITATION_RE.match(text) or _URL_RE.search(text):
            continue
        if _looks_like_formula(text):
            continue
        result.append(fragment)
    return result


def _bibliography_order(document: DocumentModel) -> int | None:
    heading = next(
        (
            item
            for item in reversed(document.headings)
            if normalize_title(item.title) in BIBLIOGRAPHY_TITLES
        ),
        None,
    )
    return heading.location.order if heading is not None else None


def _looks_like_formula(text: str) -> bool:
    if len(text) > 200:
        return False
    symbols = sum(1 for char in text if char in "=+−±×÷*/^_≤≥∑∫√")
    letters = sum(1 for char in text if char.isalpha())
    return symbols >= 3 and letters < len(text) * 0.5


def _finding(rule: Rule, location, word: str, error: SpellError) -> Finding:
    if error.code == 2:
        message = f"Повтор слова: «{word}»"
    else:
        message = f"Возможная орфографическая ошибка: «{word}»"
    if error.suggestions:
        suggestion = "Возможные варианты: " + ", ".join(error.suggestions[:3])
    else:
        suggestion = "Проверьте написание слова"
    return make_finding(rule, location, message, suggestion, manual=True)

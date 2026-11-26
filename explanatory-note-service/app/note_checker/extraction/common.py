"""Общие регулярные выражения и нормализация для извлечения текста."""

from __future__ import annotations

import re

_WHITESPACE_RE = re.compile(r"\s+")

# Латинские двойники кириллицы, которые встречаются в PDF-шрифтах.
_LOOKALIKES = str.maketrans(
    {
        "A": "А",
        "B": "В",
        "C": "С",
        "E": "Е",
        "H": "Н",
        "K": "К",
        "M": "М",
        "O": "О",
        "P": "Р",
        "T": "Т",
        "X": "Х",
        "Y": "У",
    }
)

HEADING_NUMBER_RE = re.compile(r"^\s*(\d+(?:\.\d+)*)(\.?)\s+(.+)$")
CAPTION_NUMBER = r"([0-9]+(?:\.[0-9]+)*|[А-ЯA-Z]\.\d+)"
TABLE_CAPTION_RE = re.compile(
    rf"^\s*Таблица\s+{CAPTION_NUMBER}\s*[–—-]?\s*(.*)$", re.IGNORECASE
)
FIGURE_CAPTION_RE = re.compile(
    rf"^\s*Рисунок\s+{CAPTION_NUMBER}\s*[–—-]?\s*(.*)$", re.IGNORECASE
)
BIBLIOGRAPHY_TITLES = {
    "СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ",
    "СПИСОК ИСПОЛЬЗОВАННОЙ ЛИТЕРАТУРЫ",
    "СПИСОК ЛИТЕРАТУРЫ",
}


def normalize_text(text: str) -> str:
    """Схлопывает пробелы и переводы строк; текст уходит спеллеру как есть."""
    return _WHITESPACE_RE.sub(" ", text).strip()


def fix_mixed_homoglyphs(text: str) -> str:
    """Заменяет латинские двойники кириллицы в смешанных словах.

    Например, в PDF заголовок может извлечься как ``CПИСОК`` (латинская C),
    хотя визуально и по смыслу это кириллица.
    """
    result: list[str] = []
    for word in re.split(r"(\s+)", text):
        if re.search(r"[А-Яа-яЁё]", word) and re.search(r"[A-Za-z]", word):
            word = word.translate(_LOOKALIKES)
        result.append(word)
    return "".join(result)


def split_heading_number(raw: str) -> tuple[str | None, str]:
    """«2.1 Анализ» -> («2.1», «Анализ»); без номера — (None, исходный текст)."""
    match = HEADING_NUMBER_RE.match(raw)
    if not match:
        return None, raw.strip()
    return match.group(1), match.group(3).strip()


def parse_caption(text: str, kind: str) -> tuple[str | None, str]:
    """Возвращает номер и заголовок подписи таблицы или рисунка."""
    pattern = TABLE_CAPTION_RE if kind == "table" else FIGURE_CAPTION_RE
    match = pattern.match(text.strip())
    if not match:
        return None, text.strip()
    return match.group(1), (match.group(2) or "").strip()


def normalize_title(title: str) -> str:
    """Нормализация заголовка для сравнения с эталоном."""
    cleaned = re.sub(r"[^\w\sА-Яа-яЁё]", " ", title.upper())
    cleaned = cleaned.translate(_LOOKALIKES)
    return normalize_text(cleaned)

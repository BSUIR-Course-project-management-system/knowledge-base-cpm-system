"""Диагностика и восстановление кодировки текста PDF.

Некоторые PDF (например, собранные pdfLaTeX со шрифтами без ToUnicode)
извлекаются как «кракозябры»: кириллица в cp1251 интерпретируется как
Latin-1. Такой текст можно восстановить обратным перекодированием, не
подменяя результат мусором.
"""

from __future__ import annotations

import logging
import re

from ...core.exceptions import DocumentExtractionError
from ..model import DocumentModel

logger = logging.getLogger(__name__)

CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
MIN_CYRILLIC_LETTER_SHARE = 0.2
MIN_REPAIRED_SHARE = 0.3
ENCODINGS = ("cp1251", "cp866", "koi8-r")
# Частые буквы русского текста. Нужны, чтобы отличить правильную кодировку
# от «тоже кириллической», но нечитаемой (частый случай: cp1251 и koi8-r
# дают одинаковую долю кириллицы).
COMMON_RUSSIAN_LETTERS = frozenset("оеаинтсрвл")
COMMON_RUSSIAN_BIGRAMS = (
    "ст",
    "но",
    "на",
    "по",
    "то",
    "пр",
    "ко",
    "ро",
    "ни",
    "ен",
    "ов",
    "ан",
    "ер",
    "ал",
    "ли",
    "ре",
    "ор",
    "те",
)


def cyrillic_letter_share(text: str) -> float:
    """Доля кириллицы среди букв (цифры, код и пунктуация не мешают)."""
    letters = sum(1 for char in text if char.isalpha())
    if not letters:
        return 0.0
    return len(CYRILLIC_RE.findall(text)) / letters


def _russian_text_score(text: str) -> float:
    """Насколько текст похож на осмысленный русский, а не на «кириллицу»."""
    letters = [char for char in text.lower() if char.isalpha()]
    if not letters:
        return 0.0
    common = sum(char in COMMON_RUSSIAN_LETTERS for char in letters) / len(letters)
    lowered = text.lower()
    bigrams = sum(lowered.count(bigram) for bigram in COMMON_RUSSIAN_BIGRAMS)
    bigram_share = min(1.0, bigrams / max(len(letters) / 2, 1))
    return common * 0.7 + bigram_share * 0.3


def transcode(text: str, encoding: str) -> str:
    """Перекодирует байты Latin-1 обратно в указанную кодировку."""
    pieces: list[str] = []
    for char in text:
        code = ord(char)
        if code < 256:
            pieces.append(bytes([code]).decode(encoding, errors="ignore"))
        else:
            pieces.append(char)
    return "".join(pieces)


def detect_mojibake(text: str) -> str | None:
    """Возвращает кодировку, если текст похож на перекодированную кириллицу."""
    current = cyrillic_letter_share(text)
    if current >= MIN_CYRILLIC_LETTER_SHARE:
        return None

    best: tuple[str, float, float] | None = None
    for encoding in ENCODINGS:
        repaired = transcode(text, encoding)
        share = cyrillic_letter_share(repaired)
        if share < MIN_REPAIRED_SHARE:
            continue
        if share <= current:
            continue
        score = share * 0.4 + _russian_text_score(repaired) * 0.6
        if best is None or score > best[1]:
            best = (encoding, score, share)
    if best is None:
        return None
    logger.warning(
        "PDF: обнаружена перекодировка текста, применяю %s (доля кириллицы %.0f%% -> %.0f%%)",
        best[0],
        current * 100,
        best[2] * 100,
    )
    return best[0]


def validate_document_text(document: DocumentModel, filename: str) -> None:
    """Проверяет, что из PDF извлечён осмысленный русский текст."""
    text = document.full_text()
    if not text.strip() and document.pages:
        # Документ может состоять только из фронтальной части (титульный
        # лист и задание): фрагменты таких страниц намеренно не создаются,
        # но текст для проверки полей извлечён.
        text = " ".join(page.text for page in document.pages)
    pages = document.page_count
    if not text.strip():
        raise DocumentExtractionError(
            f"В PDF «{filename}» не найден текстовый слой "
            f"(страниц: {pages or 0}). Пришлите .tex-файлы разделов."
        )

    share = cyrillic_letter_share(text)
    if share < MIN_CYRILLIC_LETTER_SHARE:
        logger.warning(
            "PDF %s: доля кириллицы %.1f%%, символов %d, начало текста: %r",
            filename,
            share * 100,
            len(text),
            text[:200],
        )
        raise DocumentExtractionError(
            f"Не удалось корректно извлечь текст из PDF «{filename}»: "
            f"кириллица составляет {share:.0%} букв "
            f"(символов: {len(text)}, страниц: {pages or 0}). "
            "Похоже, шрифт не содержит Unicode-таблиц. "
            "Пришлите .tex-файлы разделов."
        )

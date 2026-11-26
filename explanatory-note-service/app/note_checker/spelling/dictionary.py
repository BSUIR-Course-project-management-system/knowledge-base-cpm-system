"""Словарь исключений для проверки орфографии."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

_WORD_TRIM_RE = re.compile(r"^[^\wА-Яа-яЁё]+|[^\wА-Яа-яЁё]+$", re.UNICODE)
DEFAULT_DICTIONARY_PATH = Path(__file__).parent / "data" / "spelling_dictionary.txt"


@lru_cache(maxsize=4)
def load_dictionary(path: str | Path = DEFAULT_DICTIONARY_PATH) -> frozenset[str]:
    """Читает по одному слову в строке; строки с # — комментарии."""
    path = Path(path)
    words: set[str] = set()
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            for token in line.split():
                words.add(_normalize(token))
    return frozenset(word for word in words if word)


def _normalize(word: str) -> str:
    return _WORD_TRIM_RE.sub("", word).casefold()


def is_excluded(word: str, dictionary: frozenset[str]) -> bool:
    return _normalize(word) in dictionary

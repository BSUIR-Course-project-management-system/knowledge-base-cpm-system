"""Интерфейс средства проверки орфографии."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SpellError:
    """Ошибка, найденная внешним средством в отправленной строке."""

    pos: int
    length: int
    word: str
    suggestions: tuple[str, ...] = ()
    code: int | None = None


class SpellingChecker(Protocol):
    """Любая реализация: Яндекс Спеллер, LanguageTool или заглушка в тестах."""

    def check(self, text: str) -> list[SpellError]:
        """Возвращает ошибки с позициями относительно переданной строки."""

    def close(self) -> None:
        """Освобождает сетевые ресурсы, если они есть."""

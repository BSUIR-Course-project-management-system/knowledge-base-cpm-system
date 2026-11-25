"""Проверка орфографии вынесена в отдельный необязательный модуль.

Чтобы полностью убрать проверку, достаточно удалить каталог
``app/note_checker/spelling``. Реестры правил и чекеров подключают его
опционально, а файл ``rules.json`` внутри каталога добавляет правило в набор.
"""

from __future__ import annotations

from pathlib import Path

from .service import check_spelling

CHECKERS = {"spelling_external": check_spelling}
CHECK_TYPES = {
    "spelling_external": "Орфография проверяется внешним средством (Яндекс Спеллер)",
}
RULES_PATH = Path(__file__).parent / "rules.json"

__all__ = ["CHECKERS", "CHECK_TYPES", "RULES_PATH", "check_spelling"]

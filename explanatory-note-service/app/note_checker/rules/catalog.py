"""Реестр типов проверок.

Правило из ``rules.json`` может ссылаться только на тип из ``CHECK_TYPES``.
Если тип ещё не реализован, правило не отбрасывается молча, а получает
статус ``unimplemented``
"""

from __future__ import annotations

# Тип проверки -> краткое описание контракта.
CHECK_TYPES: dict[str, str] = {
    # front matter / structure
    "assignment_pages": "Лист задания занимает две страницы",
    "assignment_questions": "В перечне вопросов задания есть «Введение» и «Заключение»",
    "toc_pages": "Лист содержания занимает одну страницу",
    "toc_max_level": "В содержании только разделы и подразделы (не глубже 2 уровня)",
    "abbreviations_not_empty": "Лист сокращений не пуст, если присутствует",
    "abbreviations_page": "Перечень условных обозначений расположен на 4-й странице",
    # bibliography
    "bibliography_min_items": "Список источников содержит не менее 10 наименований",
    "bibliography_gost_fields": "Библиографическое описание соответствует ГОСТ 7.1–2003",
    # Модуль spelling можно удалить; правило тогда тоже удаляется вместе с ним.
    "spelling_external": "Орфография проверяется внешним средством",
}

# Типы, для которых уже есть реализация чекера (компактный профиль).
IMPLEMENTED_CHECK_TYPES: frozenset[str] = frozenset(
    {
        "assignment_pages",
        "assignment_questions",
        "toc_pages",
        "toc_max_level",
        "abbreviations_not_empty",
        "abbreviations_page",
        "bibliography_min_items",
        "bibliography_gost_fields",
        "spelling_external",
    }
)

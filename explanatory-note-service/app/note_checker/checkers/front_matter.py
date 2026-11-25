"""Проверки начальной части записки: задание, содержание, сокращения."""

from __future__ import annotations

import re

from ..model import DocumentModel, Finding, PageRole, PageText
from ..rules.schema import Rule
from .common import document_location, make_finding

ALNUM_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9]")
TOC_ENTRY_RE = re.compile(r"(?<!\d)(\d+(?:\.\d+)+)(?!\d)")


def _pages(document: DocumentModel, role: PageRole) -> list[PageText]:
    return [page for page in document.pages if page.role is role]


def _location_for(page: PageText):
    from ..model import Location

    return Location(page=page.printed_number or page.number)


def check_assignment_pages(document: DocumentModel, rule: Rule) -> list[Finding]:
    pages = _pages(document, PageRole.assignment)
    if not pages:
        return []
    expected_pages = int(rule.check.params.get("pages", 2))
    if len(pages) == expected_pages:
        return []
    return [
        make_finding(
            rule,
            _location_for(pages[0]),
            f"Лист задания занимает {len(pages)} страниц(ы), ожидается {expected_pages}",
            "Проверьте разбиение листа задания на страницы",
        )
    ]


def check_assignment_questions(document: DocumentModel, rule: Rule) -> list[Finding]:
    pages = _pages(document, PageRole.assignment)
    if not pages:
        return []
    text = " ".join(page.text for page in pages).lower()
    required = [
        str(word)
        for word in rule.check.params.get("must_include", ["Введение", "Заключение"])
    ]
    missing = [word for word in required if word.lower() not in text]
    if not missing:
        return []
    return [
        make_finding(
            rule,
            _location_for(pages[0]),
            "В перечне вопросов листа задания отсутствуют: "
            + ", ".join(f"«{word}»" for word in missing),
            "Добавьте в содержание пояснительной записи «Введение» и «Заключение»",
        )
    ]


def check_toc_pages(document: DocumentModel, rule: Rule) -> list[Finding]:
    pages = _pages(document, PageRole.toc)
    if not document.pages:
        return []
    has_front_matter = bool(
        _pages(document, PageRole.title) or _pages(document, PageRole.assignment)
    )
    if not pages and not has_front_matter:
        return []
    expected = int(rule.check.params.get("pages", 1))
    if not pages:
        return [
            make_finding(
                rule,
                document_location(document),
                "Лист содержания не найден",
                "Добавьте содержание после листа задания",
            )
        ]
    if len(pages) != expected:
        return [
            make_finding(
                rule,
                _location_for(pages[0]),
                f"Содержание занимает {len(pages)} страниц(ы), ожидается {expected}",
                "Сократите содержание до одной страницы",
            )
        ]
    return []


def check_toc_max_level(document: DocumentModel, rule: Rule) -> list[Finding]:
    pages = _pages(document, PageRole.toc)
    if not pages:
        return []
    max_level = int(rule.check.params.get("max_level", 2))
    numbers: list[str] = []
    for page in pages:
        numbers.extend(TOC_ENTRY_RE.findall(page.text))
    too_deep = sorted(
        {number for number in numbers if len(number.split(".")) > max_level}
    )
    if not too_deep:
        return []
    return [
        make_finding(
            rule,
            _location_for(pages[0]),
            "В содержании есть заголовки глубже "
            f"{max_level}-го уровня: {', '.join(too_deep[:5])}",
            "Оставьте в содержании только разделы и подразделы (например, 1.1)",
        )
    ]


def check_abbreviations(document: DocumentModel, rule: Rule) -> list[Finding]:
    pages = _pages(document, PageRole.abbreviations)
    if not pages:
        return []
    text = " ".join(page.text for page in pages)
    for heading in ("ПЕРЕЧЕНЬ УСЛОВНЫХ ОБОЗНАЧЕНИЙ", "СПИСОК СОКРАЩЕНИЙ"):
        index = text.upper().find(heading)
        if index >= 0:
            text = text[index + len(heading) :]
            break
    if len(ALNUM_RE.findall(text)) < 5:
        return [
            make_finding(
                rule,
                _location_for(pages[0]),
                "Лист сокращений пуст",
                "Заполните список сокращений или удалите пустой лист",
            )
        ]
    return []


def check_abbreviations_page(document: DocumentModel, rule: Rule) -> list[Finding]:
    """Перечень обозначений либо отсутствует, либо начинается с заданной страницы."""
    pages = _pages(document, PageRole.abbreviations)
    if not pages:
        return []
    expected = int(rule.check.params.get("page", 4))
    actual = pages[0].printed_number or pages[0].number
    if actual == expected:
        return []
    return [
        make_finding(
            rule,
            _location_for(pages[0]),
            f"Перечень условных обозначений расположен на странице {actual}, "
            f"ожидается {expected}",
            "Разместите перечень сразу после листа задания и содержания",
        )
    ]


__all__ = [
    "check_assignment_pages",
    "check_assignment_questions",
    "check_toc_pages",
    "check_toc_max_level",
    "check_abbreviations",
    "check_abbreviations_page",
]

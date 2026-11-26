"""Проверки списка использованных источников."""

from __future__ import annotations

import re

from ..extraction.common import BIBLIOGRAPHY_TITLES, normalize_title
from ..model import DocumentModel, Finding
from ..rules.schema import Rule
from .common import document_location, make_finding

_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")


def bibliography_heading(document: DocumentModel):
    """Последний заголовок списка источников.

    В содержании тоже есть строка «Список использованных источников», поэтому
    первый найденный заголовок может указывать на страницу оглавления.
    Реальный раздел расположен в конце записки — берём последний.
    """
    return next(
        (
            heading
            for heading in reversed(document.headings)
            if normalize_title(heading.title) in BIBLIOGRAPHY_TITLES
        ),
        None,
    )


def check_min_items(document: DocumentModel, rule: Rule) -> list[Finding]:
    minimum = int(rule.check.params.get("min_items", 10))
    if len(document.bibliography) >= minimum:
        return []
    if document.bibliography:
        location = document.bibliography[0].location
    else:
        heading = bibliography_heading(document)
        location = heading.location if heading else document_location(document)
    return [
        make_finding(
            rule,
            location,
            f"В списке источников {len(document.bibliography)} позиций, требуется не менее {minimum}",
            "Дополните список использованных источников",
        )
    ]


def check_gost_fields(document: DocumentModel, rule: Rule) -> list[Finding]:
    findings: list[Finding] = []
    for entry in document.bibliography:
        text = entry.text.strip()
        if len(text) < 20 or not _YEAR_RE.search(text):
            findings.append(
                make_finding(
                    rule,
                    entry.location,
                    "Библиографическое описание неполное: не найден год издания",
                    "Оформите описание по ГОСТ 7.1–2003: автор, название, место, издательство, год",
                    manual=True,
                )
            )
    return findings


def _is_book_or_article(entry_text: str) -> bool:
    text = entry_text.lower()
    without_urls = re.sub(r"https?://\S+", " ", text)
    if "//" in without_urls:
        return True
    electronic_markers = (
        "http://",
        "https://",
        "url:",
        "режим доступа",
        "электронный ресурс",
        "[электронный ресурс]",
    )
    return not any(marker in text for marker in electronic_markers)


def bibliography_statistics(document: DocumentModel) -> dict[str, object]:
    total = len(document.bibliography)
    books = sum(1 for entry in document.bibliography if _is_book_or_article(entry.text))
    return {
        "total": total,
        "books_articles": books,
        "books_articles_share": round(books / total, 3) if total else 0.0,
    }

"""Единая модель документа, с которой работают все проверки.

PDF и TeX приводятся к одному ``DocumentModel``: проверки не знают, из
какого формата пришёл документ, и не зависят от FastAPI.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from .rules.schema import Category, Severity


class SourceType(str, Enum):
    pdf = "pdf"
    tex = "tex"


class PageRole(str, Enum):
    title = "title"
    assignment = "assignment"
    toc = "toc"
    abbreviations = "abbreviations"
    body = "body"


class PageText(BaseModel):
    # Физический номер страницы в PDF (1-based).
    number: int
    text: str
    role: PageRole = PageRole.body
    # Номер, напечатанный в колонтитуле. Может отличаться от физического
    # (например, титульный лист не пронумерован) и использоваться в отчёте.
    printed_number: int | None = None


class FragmentKind(str, Enum):
    paragraph = "paragraph"
    heading = "heading"
    caption = "caption"
    list_item = "list_item"
    table_cell = "table_cell"
    bibliography_entry = "bibliography_entry"


class Location(BaseModel):
    """Место элемента: страница для PDF либо файл и строка для TeX."""

    page: int | None = None
    section: str | None = None
    element: str | None = None
    file: str | None = None
    line: int | None = None
    # Внутренний порядок в документе для детерминированной сортировки
    # замечаний; в ответ API не попадает.
    order: int = Field(default=0, exclude=True)


class TextFragment(BaseModel):
    """Единица текста для проверок."""

    text: str
    location: Location
    kind: FragmentKind = FragmentKind.paragraph


class Heading(BaseModel):
    raw: str
    title: str
    number: str | None = None
    level: int = 1
    location: Location


class TableElement(BaseModel):
    number: str | None = None
    caption: str | None = None
    location: Location
    caption_position: Literal["above", "below"] | None = None
    # None означает, что структуру таблицы извлечь не удалось.
    cells: list[list[str]] | None = None


class FigureElement(BaseModel):
    number: str | None = None
    caption: str | None = None
    location: Location
    caption_position: Literal["above", "below"] | None = None


class ListItem(BaseModel):
    marker: str | None = None
    text: str
    location: Location


class ListBlock(BaseModel):
    kind: Literal["dash", "numbered", "lettered", "unknown"] = "unknown"
    items: list[ListItem] = Field(default_factory=list)
    intro: str | None = None
    level: int = 1
    location: Location


class BibliographyEntry(BaseModel):
    number: int | None = None
    label: str | None = None
    text: str
    location: Location


class DocumentModel(BaseModel):
    source_type: SourceType
    # Число страниц документа: по напечатанной нумерации, если она
    # распознана и не противоречит физическому числу страниц; иначе —
    # число непустых физических страниц.
    page_count: int | None = None
    # Сколько страниц физически лежит в PDF.
    physical_page_count: int | None = None
    pages: list[PageText] = Field(default_factory=list)
    fragments: list[TextFragment] = Field(default_factory=list)
    headings: list[Heading] = Field(default_factory=list)
    tables: list[TableElement] = Field(default_factory=list)
    figures: list[FigureElement] = Field(default_factory=list)
    lists: list[ListBlock] = Field(default_factory=list)
    bibliography: list[BibliographyEntry] = Field(default_factory=list)

    def full_text(self) -> str:
        return "\n".join(fragment.text for fragment in self.fragments)


class Finding(BaseModel):
    """Замечание в едином формате ответа."""

    rule_id: str
    category: Category
    severity: Severity
    location: Location
    requirement_ref: str
    message: str
    suggestion: str = ""
    needs_manual_review: bool = False
    rule_set_version: str = ""

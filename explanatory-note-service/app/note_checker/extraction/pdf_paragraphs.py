"""Извлечение абзацев, заголовков и элементов из PDF (PyMuPDF).

Для орфографии достаточно последовательности абзацев с номером страницы.
Структурные элементы (таблицы, рисунки, списки, библиография) извлекаются
эвристически; если свойство недоступно (например, положение подписи при
отсутствии изображения), оно остаётся ``None``, и правило помечает случай
как требующий ручной проверки, а не выдаёт ложное срабатывание.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

import fitz

from ...core.exceptions import DocumentExtractionError
from ..model import (
    BibliographyEntry,
    DocumentModel,
    FigureElement,
    FragmentKind,
    Heading,
    ListBlock,
    ListItem,
    Location,
    PageRole,
    PageText,
    SourceType,
    TableElement,
    TextFragment,
)
from .common import (
    BIBLIOGRAPHY_TITLES,
    FIGURE_CAPTION_RE,
    TABLE_CAPTION_RE,
    fix_mixed_homoglyphs,
    normalize_text,
    normalize_title,
    parse_caption,
    split_heading_number,
)
from .pdf_fonts import PdfFontDecoder, apply_mapping, combined_mapping
from .text_encoding import (
    cyrillic_letter_share,
    detect_mojibake,
    transcode,
    validate_document_text,
)

_PAGE_NUMBER_LINE_RE = re.compile(
    r"^\s*(?:стр(?:аница)?\.?\s*)?[-–—]?\s*(\d{1,4})\s*[-–—]?\s*$",
    re.IGNORECASE,
)
_MAX_PAGE_NUMBER_DELTA = 20
_LIST_MARKER_RE = re.compile(r"^\s*(?P<marker>[–—-]|\d+[.)]|[а-я]\))\s+(?P<text>.+)$")
_TABLE_CONTINUATION_RE = re.compile(r"^\s*Продолжение\s+таблицы", re.IGNORECASE)
_TOC_DOTS_RE = re.compile(r"(?:\.{3,}|…{2,}|·{3,}|_{3,})")
_TOC_PAGE_NUMBER_RE = re.compile(r"^(?P<title>.{2,120}?)\s+(?P<page>\d{1,4})$")
_ASSIGNMENT_MARKERS = (
    "СПЕЦИАЛЬНОСТЬ",
    "ТЕМАРАБОТЫ",
    "ТЕМАПРОЕКТА",
    "СРОКСДАЧИ",
    "СОДЕРЖАНИЕПОЯСНИТЕЛЬНОЙ",
    "ДАТАВЫДАЧИ",
    "КУРАТОР",
    "ЗАДАНИЕПРИНЯЛ",
    "КАЛЕНДАРНЫЙПЛАН",
)
_ASSIGNMENT_CONTINUATION_MARKERS = (
    "КАЛЕНДАРНЫЙПЛАН",
    "СРОКСДАЧИ",
    "ДАТАВЫДАЧИ",
    "ЗАДАНИЕПРИНЯЛ",
    "КУРАТОР",
)
_TITLE_STRONG_MARKERS = (
    "ПОЯСНИТЕЛЬНАЯЗАПИСКА",
    "ТИТУЛЬНЫЙЛИСТ",
)
_TITLE_CONTEXT_MARKERS = (
    "НАТЕМУ",
    "МИНИСТЕРСТВО",
    "УЧРЕЖДЕНИЕОБРАЗОВАНИЯ",
    "БГУИР",
)
_ABBREVIATION_MARKERS = (
    "ПЕРЕЧЕНЬУСЛОВНЫХОБОЗНАЧЕНИЙ",
    "СПИСОКСОКРАЩЕНИЙ",
    "ПЕРЕЧЕНЬСОКРАЩЕНИЙ",
    "СПИСОКУСЛОВНЫХОБОЗНАЧЕНИЙ",
)
_BODY_MARKERS = (
    "ВВЕДЕНИЕ",
    "ЗАКЛЮЧЕНИЕ",
    "СПИСОКИСПОЛЬЗОВАННЫХИСТОЧНИКОВ",
    "СПИСОКЛИТЕРАТУРЫ",
)


@dataclass
class _Line:
    text: str
    bbox: tuple[float, float, float, float]
    page: int
    bold: bool
    size: float


@dataclass
class _Block:
    lines: list[_Line]
    page: int
    y0: float


@dataclass
class _Caption:
    text: str
    bbox: tuple[float, float, float, float]
    page: int
    kind: str
    consumed: bool = False


class PdfTextExtractor:
    def __init__(self, source: str | Path | bytes, filename: str):
        self.source = source
        self.filename = filename
        self._tick = 0
        self._heading_positions: list[tuple[int, float, str]] = []
        self._current_section: str | None = None
        self._captions: list[_Caption] = []
        self._page_heights: dict[int, float] = {}
        self._tables: dict[int, list[tuple[tuple, list[list[str]]]]] = {}
        self._encoding: str | None = None
        self._font_decoder: PdfFontDecoder | None = None
        self._page_font_maps: dict[int, dict[str, dict[str, str]]] = {}
        self._page_usage_maps: dict[int, dict[str, dict[str, str]]] = {}
        self._page_texts: dict[int, str] = {}
        self._page_lines: dict[int, list[_Line]] = {}
        self._detected_page_numbers: dict[int, int] = {}
        self._printed_pages: dict[int, int] = {}
        self._content_page_count: int | None = None
        self._page_roles: dict[int, PageRole] = {}
        self._toc_pages: set[int] = set()
        self._toc_heading_added = False

    # ------------------------------------------------------------------ API
    def extract(self) -> DocumentModel:
        document = self._open()
        try:
            self._font_decoder = PdfFontDecoder(document)
            blocks = self._collect_blocks(document)
            pages = document.page_count
            blocks, plain_text = self._drop_headers_and_footers(blocks, pages)
            self._repair_page_encodings(blocks)
            plain_text = " ".join(line.text for block in blocks for line in block.lines)
            self._encoding = detect_mojibake(plain_text)
            if self._encoding:
                for block in blocks:
                    for line in block.lines:
                        line.text = transcode(line.text, self._encoding)
                for caption in self._captions:
                    caption.text = transcode(caption.text, self._encoding)

            self._rebuild_page_texts(blocks)
            self._resolve_page_numbering(pages)

            result = DocumentModel(
                source_type=SourceType.pdf,
                page_count=self._content_page_count,
                physical_page_count=pages,
            )
            self._blocks = blocks
            self._result = result
            self._toc_pages = self._detect_toc_pages()
            result.pages = self._classify_pages()
            self._page_roles = {page.number: page.role for page in result.pages}
            self._tables = self._collect_tables(document)
            caption_texts = {normalize_text(caption.text) for caption in self._captions}
            self._build_paragraphs(result, blocks, caption_texts)
            self._build_tables(result)
            self._build_table_captions(result)
            self._build_figures(result, document)
            self._build_lists(result)
            self._build_bibliography(result)
            validate_document_text(result, self.filename)
            return result
        finally:
            document.close()

    def _open(self):
        try:
            if isinstance(self.source, bytes):
                document = fitz.open(stream=self.source, filetype="pdf")
            else:
                document = fitz.open(self.source)
        except Exception as exc:  # noqa: BLE001 - любая ошибка чтения PDF
            raise DocumentExtractionError(
                f"Не удалось открыть PDF «{self.filename}»: файл повреждён или не является PDF"
            ) from exc
        if document.needs_pass:
            document.close()
            raise DocumentExtractionError(
                f"PDF {self.filename} защищён паролем: извлечь текст невозможно"
            )
        if document.page_count == 0:
            document.close()
            raise DocumentExtractionError(f"PDF {self.filename} не содержит страниц")
        return document

    # ----------------------------------------------------------- сбор строк
    def _collect_blocks(self, document) -> list[_Block]:
        blocks: list[_Block] = []
        for page_number, page in enumerate(document, start=1):
            self._page_heights[page_number] = page.rect.height
            font_maps = (
                self._font_decoder.for_page(page, page_number)
                if self._font_decoder
                else {}
            )
            usage_maps = (
                self._font_decoder.usage_maps_for_page(page, page_number)
                if self._font_decoder
                else {}
            )
            self._page_font_maps[page_number] = font_maps
            self._page_usage_maps[page_number] = usage_maps
            try:
                trace_spans = page.get_texttrace()
            except Exception:  # noqa: BLE001
                trace_spans = []
            data = page.get_text("dict")
            page_start = len(blocks)
            for raw_block in data.get("blocks", []):
                if raw_block.get("type", 0) != 0:
                    continue
                lines: list[_Line] = []
                for raw_line in raw_block.get("lines", []):
                    spans = raw_line.get("spans", [])
                    text = self._decode_raw_line(
                        raw_line,
                        trace_spans,
                        usage_maps,
                        font_maps,
                        page,
                        page_number,
                    )
                    if not text.strip():
                        continue
                    bold = _is_bold(spans)
                    size = max((span.get("size", 0) for span in spans), default=0)
                    lines.append(
                        _Line(
                            text=text,
                            bbox=tuple(raw_line.get("bbox", (0, 0, 0, 0))),
                            page=page_number,
                            bold=bold,
                            size=size,
                        )
                    )
                if lines:
                    blocks.append(
                        _Block(
                            lines=lines,
                            page=page_number,
                            y0=min(line.bbox[1] for line in lines),
                        )
                    )
            page_lines = [line for block in blocks[page_start:] for line in block.lines]
            self._page_lines[page_number] = page_lines
            detected = _detect_margin_page_number(page_lines, page.rect.height)
            if detected is not None:
                self._detected_page_numbers[page_number] = detected
            self._captions.extend(
                self._page_captions(
                    page_number, page, usage_maps, font_maps, trace_spans
                )
            )
        return blocks

    def _decode_raw_line(
        self,
        raw_line,
        trace_spans,
        usage_maps,
        font_maps,
        page,
        page_number: int,
    ) -> str:
        bbox = tuple(raw_line.get("bbox", (0, 0, 0, 0)))
        candidates = [span for span in trace_spans if _trace_span_in_line(span, bbox)]
        parts: list[tuple[str, tuple]] = []
        decoded_all = True
        if candidates and self._font_decoder is not None:
            candidates.sort(key=lambda span: span.get("bbox", (0, 0, 0, 0))[0])
            for span in candidates:
                text = self._font_decoder.decode_span(page, page_number, span)
                if text is None:
                    decoded_all = False
                    break
                parts.append((text, tuple(span.get("bbox", (0, 0, 0, 0)))))
        else:
            decoded_all = False

        if not decoded_all:
            # Сырые спаны PyMuPDF уже содержат позиционные пробелы.
            # Посимвольная сборка из get_texttrace() их теряет, поэтому
            # используем её только когда глифы удалось декодировать целиком.
            parts = []
            for span in raw_line.get("spans", []):
                font_name = span.get("font", "")
                text = apply_mapping(
                    usage_maps.get(font_name) or font_maps.get(font_name),
                    span.get("text", ""),
                )
                parts.append((text, tuple(span.get("bbox", (0, 0, 0, 0)))))
        return _join_parts(parts)

    def _page_captions(
        self,
        page_number: int,
        page,
        usage_maps: dict[str, dict[str, str]],
        font_maps: dict[str, dict[str, str]],
        trace_spans,
    ) -> list[_Caption]:
        captions: list[_Caption] = []
        data = page.get_text("dict")
        for raw_block in data.get("blocks", []):
            if raw_block.get("type", 0) != 0:
                continue
            for raw_line in raw_block.get("lines", []):
                text = normalize_text(
                    self._decode_raw_line(
                        raw_line,
                        trace_spans,
                        usage_maps,
                        font_maps,
                        page,
                        page_number,
                    )
                )
                if not text:
                    continue
                for kind, pattern in (
                    ("table", TABLE_CAPTION_RE),
                    ("figure", FIGURE_CAPTION_RE),
                ):
                    if pattern.match(text):
                        if kind == "table" and _TABLE_CONTINUATION_RE.match(text):
                            break
                        captions.append(
                            _Caption(
                                text=text,
                                bbox=tuple(raw_line.get("bbox", (0, 0, 0, 0))),
                                page=page_number,
                                kind=kind,
                            )
                        )
                        break
        return captions

    # --------------------------------------------------- колонтитулы и мусор
    def _drop_headers_and_footers(
        self, blocks: list[_Block], pages: int
    ) -> tuple[list[_Block], str]:
        counts: dict[str, int] = {}
        for block in blocks:
            for line in block.lines:
                if self._in_margin(line, self._page_heights.get(line.page, 1.0)):
                    key = re.sub(r"\d+", "#", normalize_text(line.text)).lower()
                    if len(key) > 3:
                        counts[key] = counts.get(key, 0) + 1

        threshold = max(2, math.ceil(pages * 0.4)) if pages > 1 else 10**9
        cleaned: list[_Block] = []
        texts: list[str] = []
        for block in blocks:
            kept: list[_Line] = []
            for line in block.lines:
                if (
                    self._in_margin(line, self._page_heights.get(line.page, 1.0))
                    and _PAGE_NUMBER_LINE_RE.match(normalize_text(line.text))
                    and not line.bold
                    and line.size <= 14
                ):
                    continue
                key = re.sub(r"\d+", "#", normalize_text(line.text)).lower()
                if (
                    self._in_margin(line, self._page_heights.get(line.page, 1.0))
                    and counts.get(key, 0) >= threshold
                ):
                    continue
                kept.append(line)
            if kept:
                cleaned.append(
                    _Block(lines=kept, page=block.page, y0=min(l.bbox[1] for l in kept))
                )
                texts.extend(line.text for line in kept)
        return cleaned, " ".join(texts)

    @staticmethod
    def _in_margin(line: _Line, page_height: float) -> bool:
        y0, y1 = line.bbox[1], line.bbox[3]
        return y0 < page_height * 0.08 or y1 > page_height * 0.92

    # -------------------------------------------------- нумерация страниц
    def _repair_page_encodings(self, blocks: list[_Block]) -> None:
        """Чинит отдельные страницы, закодированные не так, как остальной PDF.

        Титульный лист и лист задания нередко вставляются в PDF из другого
        источника. Глобальная проверка «доля кириллицы по всему документу»
        такие страницы пропускает, и дальше они выглядят как незаполненные.
        """
        lines_by_page: dict[int, list[_Line]] = {}
        for block in blocks:
            lines_by_page.setdefault(block.page, []).extend(block.lines)

        for page_number, lines in lines_by_page.items():
            text = " ".join(line.text for line in lines)
            if not _looks_like_latin1_mojibake(text):
                continue
            encoding = detect_mojibake(text)
            if not encoding:
                continue
            repaired = transcode(text, encoding)
            if cyrillic_letter_share(repaired) < 0.5:
                continue
            for line in lines:
                line.text = transcode(line.text, encoding)
            for caption in self._captions:
                if caption.page == page_number:
                    caption.text = transcode(caption.text, encoding)

    def _rebuild_page_texts(self, blocks: list[_Block]) -> None:
        """Собирает текст страницы построчно, а не поблочно.

        PyMuPDF нередко отдаёт таблицу (лист задания, титульный лист) двумя
        блоками: сначала все подписи, затем все значения. Поблочная склейка
        превращает «Специальность … Тема работы …» в список подписей без
        значений. Построчная сборка (сортировка по вертикали, затем по
        горизонтали) сохраняет пары «подпись — значение».
        """
        lines_by_page: dict[int, list[_Line]] = {}
        for block in blocks:
            lines_by_page.setdefault(block.page, []).extend(block.lines)
        for page_number in range(1, (max(lines_by_page) if lines_by_page else 0) + 1):
            lines = lines_by_page.get(page_number, [])
            self._page_lines[page_number] = lines
            self._page_texts[page_number] = _page_text_from_lines(lines)

    def _resolve_page_numbering(self, physical_count: int) -> None:
        """Определяет печатный номер страницы и реальное число страниц.

        Верхняя граница — физические страницы; нижняя — напечатанные номера.
        Если титульный лист не пронумерован, физических страниц на одну
        больше, чем напечатанных, и отчёт не должен показывать лишнюю.
        """
        candidates = {
            page: number
            for page, number in self._detected_page_numbers.items()
            if 1 <= number <= physical_count + _MAX_PAGE_NUMBER_DELTA
        }
        mapping: dict[int, int] | None = None
        if len(candidates) >= max(2, math.ceil(physical_count * 0.5)):
            offsets = {page - number for page, number in candidates.items()}
            offset = max(
                offsets,
                key=lambda value: sum(
                    1 for page, number in candidates.items() if page - number == value
                ),
            )
            agreed = sum(
                1 for page, number in candidates.items() if page - number == offset
            )
            if agreed >= max(2, math.ceil(len(candidates) * 0.6)):
                proposed = {
                    page: max(1, page - offset) for page in range(1, physical_count + 1)
                }
                for page, number in candidates.items():
                    if page - number == offset:
                        proposed[page] = number
                numbers = list(proposed.values())
                if all(
                    1 <= number <= physical_count + _MAX_PAGE_NUMBER_DELTA
                    for number in numbers
                ) and all(
                    first <= second for first, second in zip(numbers, numbers[1:])
                ):
                    mapping = proposed

        self._printed_pages = mapping or {
            page: page for page in range(1, physical_count + 1)
        }

        content_pages = [
            page
            for page in range(1, physical_count + 1)
            if self._page_texts.get(page, "").strip() or page in candidates
        ]
        last_content = max(content_pages) if content_pages else physical_count
        last_printed = max(
            self._printed_pages.get(page, page) for page in range(1, last_content + 1)
        )
        if 0 <= last_content - last_printed <= 2:
            self._content_page_count = last_printed
        else:
            self._content_page_count = last_content

    # -------------------------------------------------- роли страниц
    def _classify_pages(self) -> list[PageText]:
        texts = self._page_texts
        compact = {page: _compact_text(text) for page, text in texts.items()}
        className_by_page = self._role_sets(compact)
        title, assignment, abbreviations = className_by_page
        toc = set(self._toc_pages)
        pages: list[PageText] = []
        for page_number in sorted(texts):
            if page_number in title:
                role = PageRole.title
            elif page_number in assignment:
                role = PageRole.assignment
            elif page_number in toc:
                role = PageRole.toc
            elif page_number in abbreviations:
                role = PageRole.abbreviations
            else:
                role = PageRole.body
            pages.append(
                PageText(
                    number=page_number,
                    text=texts[page_number],
                    role=role,
                    printed_number=self._printed_pages.get(page_number),
                )
            )
        return pages

    def _role_sets(
        self, compact: dict[int, str]
    ) -> tuple[set[int], set[int], set[int]]:
        toc = set(self._toc_pages)
        assignment = self._detect_assignment_pages(compact, toc)

        title: set[int] = set()
        front = assignment | toc
        if front:
            cutoff = min(front)
            title = {
                page
                for page, text in self._page_texts.items()
                if page < cutoff
                and page not in front
                and text.strip()
                and _has_title_marker(compact.get(page, ""))
            }
            # Титульный лист мог не содержать явных маркеров (например,
            # извлечён с потерей шрифта) — тогда это всё, что стоит до
            # листа задания/содержания.
            if not title:
                title = {
                    page
                    for page, text in self._page_texts.items()
                    if page < cutoff and page not in front and text.strip()
                }
        else:
            title = {
                page
                for page, text in self._page_texts.items()
                if text.strip()
                and _has_title_marker(compact.get(page, ""))
                and page <= 3
            }

        abbreviations = {
            page
            for page, text in compact.items()
            if page not in title | assignment | toc
            and any(marker in text for marker in _ABBREVIATION_MARKERS)
        }
        return title, assignment, abbreviations

    def _detect_assignment_pages(
        self, compact: dict[int, str], toc: set[int]
    ) -> set[int]:
        if toc:
            limit = min(toc) - 1
        else:
            limit = min(len(compact), 10)
        candidates: set[int] = set()
        for page in sorted(compact):
            if page > limit:
                break
            if page in toc:
                continue
            text = compact[page]
            if "КАЛЕНДАРНЫЙПЛАН" in text:
                candidates.add(page)
                continue
            if "ЗАДАНИЕ" not in text:
                continue
            markers = sum(1 for marker in _ASSIGNMENT_MARKERS if marker in text)
            heading_near_start = text.find("ЗАДАНИЕ") <= 80
            if markers >= 2 and (heading_near_start or markers >= 3):
                candidates.add(page)

        for page in sorted(candidates):
            following = page + 1
            while (
                following <= limit
                and following not in toc
                and following not in candidates
                and following in compact
            ):
                text = compact[following]
                if any(
                    marker in text for marker in _ASSIGNMENT_CONTINUATION_MARKERS
                ) and not any(marker in text for marker in _BODY_MARKERS):
                    candidates.add(following)
                    following += 1
                else:
                    break
        return candidates

    def _detect_toc_pages(self) -> set[int]:
        start: int | None = None
        for page_number in sorted(self._page_texts):
            compact = _compact_text(self._page_texts[page_number])
            # «СОДЕРЖАНИЕ» должно быть заголовком страницы, а не словом в
            # тексте листа задания («4. Содержание пояснительной записки»).
            if compact.find("СОДЕРЖАНИЕ") > 100:
                continue
            if "ЗАДАНИЕ" in compact and not self._looks_like_toc_page(page_number):
                continue
            if self._looks_like_toc_page(page_number):
                start = page_number
                break
        if start is None:
            return set()
        result = {start}
        for page_number in sorted(self._page_texts):
            if page_number <= start:
                continue
            if self._has_section_heading(page_number, _ABBREVIATION_MARKERS):
                break
            if self._has_section_heading(page_number, _BODY_MARKERS):
                break
            if self._looks_like_toc_page(page_number):
                result.add(page_number)
            else:
                break
        return result

    def _has_section_heading(self, page_number: int, markers: tuple[str, ...]) -> bool:
        """Страница начинается с настоящего заголовка раздела, а не с пункта оглавления."""
        for row in _page_row_groups(self._page_lines.get(page_number, [])):
            text = normalize_text(" ".join(line.text for line in row))
            if not text:
                continue
            if _TOC_DOTS_RE.search(text) or _TOC_PAGE_NUMBER_RE.match(text):
                continue
            compact = _compact_text(text)
            if any(
                compact.startswith(marker) and len(compact) <= len(marker) + 20
                for marker in markers
            ):
                return True
        return False

    def _looks_like_toc_page(self, page_number: int) -> bool:
        lines = self._page_lines.get(page_number, [])
        rows = _page_row_groups(lines)
        dot_rows = sum(
            1 for row in rows if any(_TOC_DOTS_RE.search(line.text) for line in row)
        )
        if dot_rows >= 2:
            return True
        numbered = 0
        for row in rows:
            text = normalize_text(" ".join(line.text for line in row))
            match = _TOC_PAGE_NUMBER_RE.match(text)
            if not match:
                continue
            title = match.group("title").strip()
            if len(title) >= 3 and re.search(r"[А-Яа-яA-Za-z]", title):
                numbered += 1
        return numbered >= 3

    def _build_paragraphs(
        self, result: DocumentModel, blocks: list[_Block], caption_texts: set[str]
    ) -> None:
        pending_number: str | None = None
        for block in blocks:
            if block.page in self._toc_pages:
                if not self._toc_heading_added:
                    location = self._location(block.page, block.y0)
                    result.headings.append(
                        Heading(
                            raw="СОДЕРЖАНИЕ",
                            title="СОДЕРЖАНИЕ",
                            number=None,
                            level=1,
                            location=location,
                        )
                    )
                    result.fragments.append(
                        TextFragment(
                            text="СОДЕРЖАНИЕ",
                            location=self._location(block.page, block.y0),
                            kind=FragmentKind.heading,
                        )
                    )
                    self._heading_positions.append((block.page, block.y0, "СОДЕРЖАНИЕ"))
                    self._toc_heading_added = True
                continue
            if self._page_roles.get(block.page) in (
                PageRole.title,
                PageRole.assignment,
                PageRole.abbreviations,
            ):
                continue
            for group in self._split_block(block, caption_texts):
                text = _join_lines(group)
                if not text:
                    continue
                if (
                    re.fullmatch(r"\d+(?:\.\d+)*\.?", text.strip())
                    and len(text.strip()) <= 12
                ):
                    pending_number = text.strip().rstrip(".")
                    continue
                if self._is_heading(group, text):
                    if pending_number and not re.match(r"^\d", text):
                        text = f"{pending_number} {text}"
                    pending_number = None
                    number, title = split_heading_number(text)
                    label = number or title
                    self._current_section = label
                    location = self._location(block.page, group[0].bbox[1])
                    result.headings.append(
                        Heading(
                            raw=text,
                            title=title,
                            number=number,
                            level=2 if number and "." in number else 1,
                            location=location,
                        )
                    )
                    self._heading_positions.append(
                        (block.page, group[0].bbox[1], label)
                    )
                    result.fragments.append(
                        TextFragment(
                            text=text,
                            location=self._location(block.page, group[0].bbox[1]),
                            kind=FragmentKind.heading,
                        )
                    )
                else:
                    pending_number = None
                    result.fragments.append(
                        TextFragment(
                            text=text,
                            location=self._location(block.page, group[0].bbox[1]),
                            kind=FragmentKind.paragraph,
                        )
                    )

    def _split_block(self, block: _Block, caption_texts: set[str]) -> list[list[_Line]]:
        groups: list[list[_Line]] = []
        current: list[_Line] = []
        for line in block.lines:
            text = normalize_text(line.text)
            if not text or text in caption_texts:
                if current:
                    groups.append(current)
                    current = []
                continue
            if self._in_table(line):
                if current:
                    groups.append(current)
                    current = []
                continue
            if current:
                previous = current[-1]
                gap = line.bbox[1] - previous.bbox[3]
                strong = _strong_heading_line(line)
                group_strong = all(_strong_heading_line(item) for item in current)
                if (
                    gap > 7
                    or (strong and not group_strong)
                    or (group_strong and not strong)
                ):
                    groups.append(current)
                    current = []
            current.append(line)
        if current:
            groups.append(current)
        return groups

    def _collect_tables(
        self, document
    ) -> dict[int, list[tuple[tuple, list[list[str]]]]]:
        tables: dict[int, list[tuple[tuple, list[list[str]]]]] = {}
        for page_number, page in enumerate(document, start=1):
            try:
                finder = page.find_tables()
            except Exception:  # noqa: BLE001
                continue
            items = []
            for table in getattr(finder, "tables", []):
                rows = _extract_rows(table)
                font_mapping = combined_mapping(
                    self._page_usage_maps.get(page_number)
                    or self._page_font_maps.get(page_number, {})
                )
                if font_mapping:
                    rows = [
                        [apply_mapping(font_mapping, cell) for cell in row]
                        for row in rows
                    ]
                if self._encoding:
                    rows = [
                        [transcode(cell, self._encoding) for cell in row]
                        for row in rows
                    ]
                items.append((tuple(table.bbox), rows))
            tables[page_number] = items
        return tables

    def _is_front_page(self, page_number: int) -> bool:
        return self._page_roles.get(page_number) in (
            PageRole.title,
            PageRole.assignment,
            PageRole.toc,
            PageRole.abbreviations,
        )

    def _in_table(self, line: _Line) -> bool:
        x = (line.bbox[0] + line.bbox[2]) / 2
        y = (line.bbox[1] + line.bbox[3]) / 2
        for x0, y0, x1, y1 in (bbox for bbox, _ in self._tables.get(line.page, [])):
            if x0 - 2 <= x <= x1 + 2 and y0 - 2 <= y <= y1 + 2:
                return True
        return False

    @staticmethod
    def _is_heading(block: list[_Line], text: str) -> bool:
        if len(text) > 160 or text.endswith((".", ";", ",", ":")):
            return False
        stripped = text.strip()
        bold = sum(1 for line in block if line.bold) * 2 >= max(len(block), 1)
        if re.match(r"^\d+(?:\.\d+)*\s+\S", stripped):
            return bold
        return stripped.isupper() and len(stripped) <= 120

    # ---------------------------------------------------------- таблицы
    def _build_tables(self, result: DocumentModel) -> None:
        for page_number, items in self._tables.items():
            if self._is_front_page(page_number):
                continue
            for bbox, rows in items:
                caption = self._nearest_caption(page_number, bbox, "table")
                number = None
                position = None
                if caption is not None:
                    number, _ = parse_caption(caption.text, "table")
                    position = "above" if caption.bbox[3] <= bbox[1] + 2 else "below"
                    caption.consumed = True
                label = f"Таблица {number}" if number else "Таблица"
                location = self._location(
                    page_number,
                    bbox[1],
                    section=self._section_at(page_number, bbox[1]),
                    element=label,
                )
                result.tables.append(
                    TableElement(
                        number=number,
                        caption=caption.text if caption else None,
                        location=location,
                        caption_position=position,
                        cells=rows,
                    )
                )
                for row in rows:
                    for cell in row:
                        if cell:
                            result.fragments.append(
                                TextFragment(
                                    text=cell,
                                    location=self._location(
                                        page_number,
                                        bbox[1],
                                        section=self._section_at(page_number, bbox[1]),
                                        element=label,
                                    ),
                                    kind=FragmentKind.table_cell,
                                )
                            )

    def _nearest_caption(
        self, page: int, bbox: tuple[float, float, float, float], kind: str
    ) -> _Caption | None:
        candidates = [
            caption
            for caption in self._captions
            if caption.page == page and caption.kind == kind and not caption.consumed
        ]
        above = [c for c in candidates if c.bbox[3] <= bbox[1] + 2]
        below = [c for c in candidates if c.bbox[1] >= bbox[3] - 2]
        pool = above or below
        if not pool:
            return None
        return min(
            pool,
            key=lambda c: min(abs(c.bbox[3] - bbox[1]), abs(c.bbox[1] - bbox[3])),
        )

    def _build_table_captions(self, result: DocumentModel) -> None:
        """Подписи, для которых структура таблицы не распознана, не теряются."""
        for caption in self._captions:
            if caption.kind != "table" or caption.consumed:
                continue
            if self._is_front_page(caption.page):
                continue
            number, _ = parse_caption(caption.text, "table")
            label = f"Таблица {number}" if number else "Таблица"
            section = self._section_at(caption.page, caption.bbox[1])
            caption.consumed = True
            result.tables.append(
                TableElement(
                    number=number,
                    caption=caption.text,
                    location=self._location(
                        caption.page, caption.bbox[1], section=section, element=label
                    ),
                    caption_position=None,
                    cells=None,
                )
            )
            result.fragments.append(
                TextFragment(
                    text=caption.text,
                    location=self._location(
                        caption.page, caption.bbox[1], section=section, element=label
                    ),
                    kind=FragmentKind.caption,
                )
            )

    # ---------------------------------------------------------- рисунки
    def _build_figures(self, result: DocumentModel, document) -> None:
        images: dict[int, list[tuple[float, float, float, float]]] = {}
        for page_number, page in enumerate(document, start=1):
            try:
                infos = page.get_image_info()
            except Exception:  # noqa: BLE001
                infos = []
            images[page_number] = [
                tuple(info["bbox"]) for info in infos if info.get("bbox")
            ]

        for caption in self._captions:
            if caption.kind != "figure" or caption.consumed:
                continue
            if self._is_front_page(caption.page):
                continue
            number, title = parse_caption(caption.text, "figure")
            position = self._caption_side(caption, images.get(caption.page, []))
            label = f"Рисунок {number}" if number else "Рисунок"
            section = self._section_at(caption.page, caption.bbox[1])
            caption.consumed = True
            result.figures.append(
                FigureElement(
                    number=number,
                    caption=caption.text,
                    location=self._location(
                        caption.page, caption.bbox[1], section=section, element=label
                    ),
                    caption_position=position,
                )
            )
            result.fragments.append(
                TextFragment(
                    text=caption.text,
                    location=self._location(
                        caption.page, caption.bbox[1], section=section, element=label
                    ),
                    kind=FragmentKind.caption,
                )
            )

    @staticmethod
    def _caption_side(
        caption: _Caption, image_boxes: list[tuple[float, float, float, float]]
    ) -> str | None:
        if not image_boxes:
            return None
        below = [box for box in image_boxes if caption.bbox[1] >= box[3] - 5]
        above = [box for box in image_boxes if caption.bbox[3] <= box[1] + 5]
        if below:
            return "below"
        if above:
            return "above"
        return None

    # ------------------------------------------------------------ списки
    def _build_lists(self, result: DocumentModel) -> None:
        bibliography_heading = self._bibliography_heading(result)
        bibliography_section = (
            (bibliography_heading.number or bibliography_heading.title)
            if bibliography_heading
            else None
        )
        lines: list[_Line] = []
        for block in self._blocks:
            for line in block.lines:
                if self._is_front_page(block.page):
                    continue
                if self._in_table(line):
                    continue
                section = self._section_at(line.page, line.bbox[1])
                if bibliography_section and section == bibliography_section:
                    continue
                lines.append(line)
        lines.sort(key=lambda line: (line.page, line.bbox[1], line.bbox[0]))

        groups_with_intro: list[tuple[list[_Line], str | None]] = []
        current: list[_Line] = []
        current_intro: str | None = None
        current_marker_x: float | None = None
        previous_marker: str | None = None
        last_text: str | None = None
        for line in lines:
            match = _LIST_MARKER_RE.match(line.text)
            if match:
                marker = match.group("marker")
                same_list = bool(
                    current
                    and previous_marker is not None
                    and _marker_kind(marker) == _marker_kind(previous_marker)
                    and line.page == current[-1].page
                    and line.bbox[1] - current[-1].bbox[3] <= 14
                )
                if current and not same_list:
                    groups_with_intro.append((current, current_intro))
                    current = []
                if not current:
                    current_intro = last_text
                    current_marker_x = line.bbox[0]
                current.append(line)
                previous_marker = marker
            elif (
                current
                and line.page == current[-1].page
                and line.bbox[1] - current[-1].bbox[3] <= 14
                and (
                    (
                        current_marker_x is not None
                        and line.bbox[0] > current_marker_x + 4
                    )
                    or not current[-1].text.rstrip().endswith((";", ".", ":"))
                )
            ):
                current.append(line)
            else:
                if current:
                    groups_with_intro.append((current, current_intro))
                    current = []
                    previous_marker = None
                    current_marker_x = None
                last_text = line.text
        if current:
            groups_with_intro.append((current, current_intro))

        for group, intro in groups_with_intro:
            lines_in_item: list[list[_Line]] = []
            for line in group:
                if _LIST_MARKER_RE.match(line.text) or not lines_in_item:
                    lines_in_item.append([line])
                else:
                    lines_in_item[-1].append(line)
            items: list[ListItem] = []
            kind = "unknown"
            for item_lines in lines_in_item:
                text = _join_lines(item_lines)
                match = _LIST_MARKER_RE.match(item_lines[0].text)
                marker = match.group("marker") if match else None
                if marker in {"–", "-", "—"}:
                    kind = "dash"
                elif marker and marker[0].isdigit():
                    kind = "numbered"
                elif marker:
                    kind = "lettered"
                location = self._location(
                    item_lines[0].page,
                    item_lines[0].bbox[1],
                    section=self._section_at(item_lines[0].page, item_lines[0].bbox[1]),
                )
                items.append(ListItem(marker=marker, text=text, location=location))
            if not items:
                continue
            if kind == "dash" and len(items) < 2:
                continue
            location = items[0].location
            result.lists.append(
                ListBlock(kind=kind, items=items, intro=intro, location=location)
            )

    # ------------------------------------------------------ библиография
    @staticmethod
    def _bibliography_heading(result: DocumentModel):
        """Последний заголовок списка источников: первый может быть в содержании."""
        return next(
            (
                item
                for item in reversed(result.headings)
                if normalize_title(item.title) in BIBLIOGRAPHY_TITLES
            ),
            None,
        )

    def _build_bibliography(self, result: DocumentModel) -> None:
        heading = self._bibliography_heading(result)
        heading_entries: list[BibliographyEntry] = []
        if heading is not None:
            section_label = heading.number or heading.title
            heading_entries = self._entries_from_fragments(
                fragment
                for fragment in result.fragments
                if fragment.location.order > heading.location.order
                and fragment.location.section == section_label
            )

        tail_entries = self._bibliography_entries_from_tail(result)
        if tail_entries and (
            not heading_entries
            or tail_entries[0].location.order > heading_entries[0].location.order
        ):
            result.bibliography = tail_entries
        else:
            result.bibliography = heading_entries

    @staticmethod
    def _entries_from_fragments(fragments) -> list[BibliographyEntry]:
        entries: list[BibliographyEntry] = []
        for fragment in fragments:
            if fragment.kind not in (FragmentKind.paragraph, FragmentKind.list_item):
                continue
            chunks = [
                chunk.strip()
                for chunk in re.split(r"(?=\[\d+\])", fragment.text)
                if chunk.strip()
            ]
            for chunk in chunks:
                match = re.match(r"^\[?(\d+)\]?[.)]?\s+(.*)$", chunk)
                if match:
                    entries.append(
                        BibliographyEntry(
                            number=int(match.group(1)),
                            text=normalize_text(match.group(2)),
                            location=fragment.location,
                        )
                    )
                elif entries:
                    entries[-1].text = normalize_text(f"{entries[-1].text} {chunk}")
                else:
                    entries.append(
                        BibliographyEntry(
                            number=1,
                            text=normalize_text(chunk),
                            location=fragment.location,
                        )
                    )
        return entries

    @staticmethod
    def _bibliography_entries_from_tail(
        result: DocumentModel,
    ) -> list[BibliographyEntry]:
        candidates = [
            fragment
            for fragment in result.fragments
            if fragment.location.page is not None
            and fragment.kind in (FragmentKind.paragraph, FragmentKind.list_item)
            and re.match(r"^\s*\[\d+\]", fragment.text)
        ]
        if not candidates:
            return []
        by_page: dict[int, list] = {}
        for fragment in candidates:
            by_page.setdefault(fragment.location.page, []).append(fragment)
        runs: list[list[int]] = []
        for page in sorted(by_page):
            if runs and page - runs[-1][-1] <= 1:
                runs[-1].append(page)
            else:
                runs.append([page])
        start_page = runs[-1][0]
        start_order = min(fragment.location.order for fragment in by_page[start_page])
        tail = [
            fragment
            for fragment in result.fragments
            if fragment.location.order >= start_order
        ]
        return PdfTextExtractor._entries_from_fragments(tail)

    # --------------------------------------------------------- служебное
    def _section_at(self, page: int, y: float) -> str | None:
        best: tuple[int, float, str] | None = None
        for position in self._heading_positions:
            if position[0] < page or (position[0] == page and position[1] <= y + 2):
                best = position
        return best[2] if best else None

    def _location(
        self,
        page: int,
        y: float,
        section: str | None = None,
        element: str | None = None,
    ) -> Location:
        self._tick = (self._tick + 1) % 10
        order = page * 10_000_000 + int(max(y, 0) * 100) * 10 + self._tick
        return Location(
            page=self._printed_pages.get(page, page),
            section=section if section is not None else self._current_section,
            element=element,
            order=order,
        )


def _detect_margin_page_number(lines: list[_Line], page_height: float) -> int | None:
    bottom: list[tuple[float, int]] = []
    top: list[tuple[float, int]] = []
    centers = [((line.bbox[1] + line.bbox[3]) / 2, line) for line in lines]
    for line in lines:
        if line.bold:
            continue
        text = normalize_text(line.text)
        match = _PAGE_NUMBER_LINE_RE.match(text)
        if not match:
            continue
        # Номер страницы — отдельная короткая строка. Если рядом на той же
        # строке стоит пункт содержания с отточиями, это не колонтитул, а
        # последний номер страницы в оглавлении.
        center = (line.bbox[1] + line.bbox[3]) / 2
        if any(
            other is not line
            and abs(other_center - center) <= 3
            and (
                _TOC_DOTS_RE.search(other.text) or len(normalize_text(other.text)) > 40
            )
            for other_center, other in centers
        ):
            continue
        number = int(match.group(1))
        if line.bbox[1] >= page_height * 0.88:
            bottom.append((line.bbox[3], number))
        elif line.bbox[3] <= page_height * 0.12:
            top.append((line.bbox[1], number))
    if bottom:
        return max(bottom, key=lambda item: item[0])[1]
    if top:
        return min(top, key=lambda item: item[0])[1]
    return None


def _page_text_from_lines(lines: list[_Line]) -> str:
    """Склеивает строки страницы построчно: сверху вниз, внутри строки — слева направо."""
    parts = [
        " ".join(item.text.strip() for item in row if item.text.strip())
        for row in _page_row_groups(lines)
    ]
    text = normalize_text(" ".join(part for part in parts if part))
    # Перенос по дефису: «Специаль-\nность» -> «Специальность».
    return re.sub(r"([А-Яа-яЁёA-Za-z])-\s+([а-яёa-z])", r"\1\2", text)


def _page_row_groups(lines: list[_Line]) -> list[list[_Line]]:
    rows: list[tuple[float, list[_Line]]] = []
    for line in sorted(lines, key=lambda item: (item.bbox[1], item.bbox[0])):
        center = (line.bbox[1] + line.bbox[3]) / 2
        if rows:
            row_center, row_lines = rows[-1]
            height = max(
                1.0,
                min(
                    line.bbox[3] - line.bbox[1],
                    row_lines[0].bbox[3] - row_lines[0].bbox[1],
                ),
            )
            if abs(center - row_center) <= max(2.5, height * 0.4):
                row_lines.append(line)
                rows[-1] = (
                    (row_center * (len(row_lines) - 1) + center) / len(row_lines),
                    row_lines,
                )
                continue
        rows.append((center, [line]))
    groups: list[list[_Line]] = []
    for _, row_lines in rows:
        row_lines.sort(key=lambda item: item.bbox[0])
        groups.append(row_lines)
    return groups


def _compact_text(text: str) -> str:
    """Текст без пробелов и пунктуации — для устойчивого поиска заголовков."""
    return re.sub(r"[^0-9A-ZА-ЯЁ]", "", fix_mixed_homoglyphs(text.upper()))


def _has_title_marker(compact: str) -> bool:
    return any(marker in compact for marker in _TITLE_STRONG_MARKERS) and any(
        marker in compact for marker in _TITLE_CONTEXT_MARKERS
    )


def _looks_like_latin1_mojibake(text: str) -> bool:
    letters = [char for char in text if char.isalpha()]
    if not letters:
        return False
    high = sum(1 for char in letters if 0xC0 <= ord(char) <= 0xFF)
    return high / len(letters) >= 0.3


def _is_bold(spans: list[dict]) -> bool:
    bold_chars = 0
    total_chars = 0
    for span in spans:
        text = span.get("text", "")
        total_chars += len(text)
        flags = span.get("flags", 0)
        font = (span.get("font") or "").lower()
        if flags & 16 or "bold" in font or "black" in font:
            bold_chars += len(text)
    return bold_chars * 2 >= max(total_chars, 1)


def _join_lines(lines: list[_Line]) -> str:
    parts: list[str] = []
    for line in lines:
        text = line.text.strip()
        if not text:
            continue
        if parts and parts[-1].endswith("-") and text[:1].islower():
            parts[-1] = parts[-1][:-1] + text
        else:
            parts.append(text)
    return normalize_text(" ".join(parts))


def _strong_heading_line(line: _Line) -> bool:
    text = line.text.strip()
    if not text or len(text) > 160:
        return False
    if text.isupper() and re.search(r"[А-ЯЁ]{3,}", text):
        return True
    return bool(re.match(r"^\d+(?:\.\d+)*\s+\S", text)) and line.bold


def _marker_kind(marker: str) -> str:
    if marker in {"–", "-", "—"}:
        return "dash"
    if marker[0].isdigit():
        return "numbered"
    return "lettered"


def _trace_span_in_line(span, line_bbox: tuple[float, float, float, float]) -> bool:
    bbox = span.get("bbox") or (0, 0, 0, 0)
    line_height = max(line_bbox[3] - line_bbox[1], 1.0)
    span_height = bbox[3] - bbox[1]
    # Один trace-спан может покрывать всю колонку/страницу. Такой спан
    # нельзя привязывать к строке: текст продублируется.
    if span_height > line_height * 1.6:
        return False
    center_y = (bbox[1] + bbox[3]) / 2
    if not (line_bbox[1] - 3 <= center_y <= line_bbox[3] + 3):
        return False
    overlap = min(bbox[2], line_bbox[2]) - max(bbox[0], line_bbox[0])
    span_width = max(bbox[2] - bbox[0], 1.0)
    line_width = max(line_bbox[2] - line_bbox[0], 1.0)
    return overlap >= min(span_width, line_width) * 0.5


def _join_parts(parts: list[tuple[str, tuple]]) -> str:
    output = ""
    previous_x1: float | None = None
    for text, bbox in parts:
        if not text:
            continue
        if (
            previous_x1 is not None
            and bbox[0] - previous_x1 > 1.5
            and output
            and not output.endswith(" ")
        ):
            output += " "
        output += text
        previous_x1 = bbox[2]
    return normalize_text(fix_mixed_homoglyphs(output))


def _extract_rows(table) -> list[list[str]]:
    try:
        raw_rows = table.extract()
    except Exception:  # noqa: BLE001
        return []
    rows: list[list[str]] = []
    for raw_row in raw_rows or []:
        row = [normalize_text(cell) if cell else "" for cell in raw_row]
        if any(row):
            rows.append(row)
    return rows


def extract_pdf(source: str | Path | bytes, filename: str) -> DocumentModel:
    return PdfTextExtractor(source, filename).extract()

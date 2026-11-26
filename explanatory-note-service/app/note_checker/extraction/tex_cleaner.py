"""Извлечение структуры и чистого текста из LaTeX-файла раздела.

Модуль не рендерит документ: он вырезает разметку, формулы, листинги и
адреса, оставляя текстовые фрагменты с привязкой ``file``/``line``.
Каждый ``.tex`` раздела обрабатывается отдельно; склейка файлов не нужна.
"""

from __future__ import annotations

import bisect
import re
from dataclasses import dataclass, field

from pylatexenc.latexwalker import (
    LatexCharsNode,
    LatexCommentNode,
    LatexEnvironmentNode,
    LatexGroupNode,
    LatexMacroNode,
    LatexMathNode,
    LatexSpecialsNode,
    LatexWalker,
    LatexWalkerParseError,
)

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
    SourceType,
    TableElement,
    TextFragment,
)
from .common import (
    BIBLIOGRAPHY_TITLES,
    normalize_text,
    parse_caption,
    split_heading_number,
)

SKIP_ENVIRONMENTS = {
    "equation",
    "equation*",
    "align",
    "align*",
    "gather",
    "gather*",
    "multline",
    "multline*",
    "displaymath",
    "math",
    "verbatim",
    "verbatim*",
    "lstlisting",
    "minted",
    "tikzpicture",
}
LIST_ENVIRONMENTS = {"itemize", "enumerate", "description"}
FLOAT_ENVIRONMENTS = {"table", "table*", "figure", "figure*"}
TABLE_ENVIRONMENTS = {"tabular", "tabular*", "tabularx", "longtable"}
INLINE_TEXT_MACROS = {
    "textbf",
    "textit",
    "emph",
    "underline",
    "texttt",
    "textrm",
    "textsc",
    "textsl",
    "textup",
    "text",
    "mbox",
    "footnote",
}
SKIP_MACROS = {
    "label",
    "index",
    "ref",
    "eqref",
    "pageref",
    "url",
    "href",
    "includegraphics",
    "hspace",
    "vspace",
    "hfill",
    "vfill",
    "newline",
    "linebreak",
    "clearpage",
    "newpage",
    "pagebreak",
    "tableofcontents",
    "hline",
    "cline",
    "toprule",
    "midrule",
    "bottomrule",
    "centering",
    "raggedright",
    "raggedleft",
    "small",
    "footnotesize",
    "normalsize",
    "large",
    "Large",
    "LARGE",
    "singlespacing",
    "onehalfspacing",
    "setlength",
    "setcounter",
    "addcontentsline",
    "phantom",
}
HEADING_MACROS = {"section": 1, "subsection": 2, "subsubsection": 3}


@dataclass
class _FloatState:
    kind: str
    start_pos: int
    caption: str | None = None
    caption_pos: int | None = None
    cells: list[list[str]] | None = None
    body_pos: int | None = None
    image_pos: int | None = None


@dataclass
class _ListState:
    kind: str
    level: int
    intro: str | None
    start_pos: int
    items: list[ListItem] = field(default_factory=list)
    marker_index: int = 0
    current_marker: str | None = None
    current_pos: int | None = None
    current_parts: list[str] = field(default_factory=list)


@dataclass
class _BibState:
    label: str | None
    pos: int
    parts: list[str] = field(default_factory=list)


class TexTextExtractor:
    def __init__(self, source: str, filename: str):
        self.source = source
        self.filename = filename
        self.line_starts = [0]
        for index, char in enumerate(source):
            if char == "\n":
                self.line_starts.append(index + 1)
        self.document = DocumentModel(source_type=SourceType.tex)
        self._order = 0
        self._current_section: str | None = None
        self._para_parts: list[str] = []
        self._para_pos: int | None = None
        self._last_paragraph: str | None = None
        self._floats: list[_FloatState] = []
        self._lists: list[_ListState] = []
        self._bib_state: _BibState | None = None
        self._pending_caption = False

    # API
    def extract(self) -> DocumentModel:
        if not self.source.strip():
            raise DocumentExtractionError(f"Файл {self.filename} пуст")
        try:
            walker = LatexWalker(self.source, tolerant_parsing=True)
            nodes, _, _ = walker.get_latex_nodes(pos=0)
        except LatexWalkerParseError as exc:
            raise DocumentExtractionError(
                f"Не удалось разобрать TeX-файл {self.filename}: {exc}"
            ) from exc

        self._walk(nodes)
        self._flush_paragraph()
        self._postprocess()
        return self.document

    # обход AST
    def _walk(self, nodes) -> None:
        for node in nodes:
            if self._pending_caption and isinstance(node, LatexGroupNode):
                self._set_caption(self._plain_text(node.nodelist), node.pos)
                self._pending_caption = False
                continue

            if isinstance(node, LatexCharsNode):
                self._append_text(node.chars, node.pos)
            elif isinstance(node, LatexCommentNode):
                continue
            elif isinstance(node, LatexMathNode):
                self._append_text(" ", node.pos)
            elif isinstance(node, LatexSpecialsNode):
                self._append_text(_specials_to_text(node.specials_chars), node.pos)
            elif isinstance(node, LatexMacroNode):
                self._handle_macro(node)
            elif isinstance(node, LatexEnvironmentNode):
                self._handle_environment(node)
            elif isinstance(node, LatexGroupNode):
                self._walk(node.nodelist)

    def _handle_macro(self, node: LatexMacroNode) -> None:
        name = node.macroname

        if name in HEADING_MACROS:
            self._handle_heading(node, HEADING_MACROS[name])
            return
        if name == "caption":
            groups = _group_args(node)
            if groups:
                self._set_caption(self._plain_text(groups[-1].nodelist), node.pos)
            else:
                self._pending_caption = True
            return
        if name == "item":
            self._start_item(node)
            return
        if name == "bibitem":
            self._start_bibitem(node)
            return
        if name == "par":
            self._flush_paragraph()
            return
        if name == "includegraphics":
            if self._floats and self._floats[-1].kind == "figure":
                self._floats[-1].image_pos = node.pos
            return
        if name in INLINE_TEXT_MACROS:
            for group in _group_args(node):
                self._append_text(self._plain_text(group.nodelist), node.pos)
            return
        if name == "\\":
            self._append_text(" ", node.pos)
            return
        if name in SKIP_MACROS:
            return
        # Неизвестные макросы не разворачиваем: их аргументы могут быть
        # служебными, а не текстом записки.

    def _handle_heading(self, node: LatexMacroNode, level: int) -> None:
        groups = _group_args(node)
        raw = self._plain_text(groups[-1].nodelist) if groups else ""
        raw = normalize_text(raw)
        if not raw:
            return

        self._flush_paragraph()
        is_starred = bool(
            re.match(r"\\[a-zA-Z]+\*", self.source[node.pos : node.pos + 40])
        )
        number, title = (None, raw) if is_starred else split_heading_number(raw)
        location = self._location(node.pos)
        heading = Heading(
            raw=raw, title=title, number=number, level=level, location=location
        )
        self.document.headings.append(heading)
        self._current_section = number or title
        self.document.fragments.append(
            TextFragment(
                text=raw,
                location=self._location(node.pos),
                kind=FragmentKind.heading,
            )
        )

    # окружения
    def _handle_environment(self, node: LatexEnvironmentNode) -> None:
        env = node.environmentname

        if env in SKIP_ENVIRONMENTS:
            self._flush_paragraph()
            return
        if env in FLOAT_ENVIRONMENTS:
            self._handle_float(node, "table" if env.startswith("table") else "figure")
            return
        if env in TABLE_ENVIRONMENTS:
            self._handle_tabular(node)
            return
        if env in LIST_ENVIRONMENTS:
            self._handle_list(node)
            return
        if env.startswith("thebibliography"):
            self._handle_bibliography(node)
            return
        # Прочие окружения (quote, center, minipage и т. п.) — обычный текст.
        self._walk(node.nodelist)

    def _handle_float(self, node: LatexEnvironmentNode, kind: str) -> None:
        self._flush_paragraph()
        state = _FloatState(kind=kind, start_pos=node.pos)
        self._floats.append(state)
        self._walk(node.nodelist)
        self._floats.pop()
        self._finish_float(state)

    def _handle_tabular(self, node: LatexEnvironmentNode) -> None:
        cells = self._parse_tabular(node)
        if self._floats and self._floats[-1].kind == "table":
            self._floats[-1].cells = cells
            self._floats[-1].body_pos = node.pos

    def _set_caption(self, text: str, pos: int) -> None:
        text = normalize_text(text)
        if not text or not self._floats:
            return
        self._floats[-1].caption = text
        self._floats[-1].caption_pos = pos

    def _finish_float(self, state: _FloatState) -> None:
        number, title = parse_caption(state.caption or "", state.kind)
        label = ("Таблица" if state.kind == "table" else "Рисунок") + (
            f" {number}" if number else ""
        )
        caption_pos = (
            state.caption_pos if state.caption_pos is not None else state.start_pos
        )
        location = self._location(caption_pos, element=label)

        if state.kind == "table":
            position = None
            if state.caption_pos is not None and state.body_pos is not None:
                position = "above" if state.caption_pos < state.body_pos else "below"
            self.document.tables.append(
                TableElement(
                    number=number,
                    caption=state.caption,
                    location=location,
                    caption_position=position,
                    cells=state.cells,
                )
            )
            for row in state.cells or []:
                for cell in row:
                    if cell.strip():
                        self.document.fragments.append(
                            TextFragment(
                                text=cell,
                                location=self._location(caption_pos, element=label),
                                kind=FragmentKind.table_cell,
                            )
                        )
        else:
            position = None
            if state.caption_pos is not None and state.image_pos is not None:
                position = "below" if state.caption_pos > state.image_pos else "above"
            self.document.figures.append(
                FigureElement(
                    number=number,
                    caption=state.caption,
                    location=location,
                    caption_position=position,
                )
            )

        if state.caption:
            self.document.fragments.append(
                TextFragment(
                    text=state.caption,
                    location=self._location(caption_pos, element=label),
                    kind=FragmentKind.caption,
                )
            )

    def _handle_list(self, node: LatexEnvironmentNode) -> None:
        self._flush_paragraph()
        env = node.environmentname
        if env == "itemize":
            kind = "dash"
        elif env == "enumerate":
            kind = "numbered"
        else:
            kind = "unknown"
        if self._lists:
            self._finish_item()
        state = _ListState(
            kind=kind,
            level=len(self._lists) + 1,
            intro=self._last_paragraph,
            start_pos=node.pos,
        )
        self._lists.append(state)
        self._walk(node.nodelist)
        self._finish_item()
        self._lists.pop()

        if state.items:
            self.document.lists.append(
                ListBlock(
                    kind=kind,
                    items=state.items,
                    intro=state.intro,
                    level=state.level,
                    location=self._location(state.start_pos),
                )
            )

    def _start_item(self, node: LatexMacroNode) -> None:
        if not self._lists:
            return
        self._finish_item()
        state = self._lists[-1]
        groups = _group_args(node)
        if groups:
            marker = normalize_text(self._plain_text(groups[-1].nodelist))
        elif state.kind == "dash":
            marker = "–"
        elif state.kind == "numbered":
            marker = str(state.marker_index + 1)
        elif state.kind == "lettered":
            marker = _russian_letter(state.marker_index) + ")"
        else:
            marker = None
        state.marker_index += 1
        state.current_marker = marker
        state.current_pos = node.pos
        state.current_parts = []

    def _finish_item(self) -> None:
        if not self._lists:
            return
        state = self._lists[-1]
        text = normalize_text("".join(state.current_parts))
        if text:
            location = self._location(state.current_pos or state.start_pos)
            state.items.append(
                ListItem(marker=state.current_marker, text=text, location=location)
            )
            self.document.fragments.append(
                TextFragment(
                    text=text,
                    location=self._location(state.current_pos or state.start_pos),
                    kind=FragmentKind.list_item,
                )
            )
        state.current_marker = None
        state.current_parts = []
        state.current_pos = None

    def _handle_bibliography(self, node: LatexEnvironmentNode) -> None:
        self._flush_paragraph()
        self._bib_state = None
        expect_label = False
        for child in node.nodelist:
            if isinstance(child, LatexMacroNode) and child.macroname == "bibitem":
                self._finish_bib_entry()
                self._bib_state = _BibState(label=None, pos=child.pos)
                expect_label = True
                continue
            if self._bib_state is None:
                # Аргумент \begin{thebibliography}{...} и прочий служебный
                # текст до первого \bibitem в позиции списка не входят.
                continue
            if expect_label and isinstance(child, LatexGroupNode):
                self._bib_state.label = normalize_text(self._plain_text(child.nodelist))
                expect_label = False
                continue
            if isinstance(child, LatexMacroNode) and (
                child.macroname in SKIP_MACROS or child.macroname in CITE_MACROS
            ):
                continue
            self._bib_state.parts.append(self._plain_text([child]))
        self._finish_bib_entry()

    def _start_bibitem(self, node: LatexMacroNode) -> None:
        self._finish_bib_entry()
        groups = _group_args(node)
        label = (
            normalize_text(self._plain_text(groups[-1].nodelist)) if groups else None
        )
        self._bib_state = _BibState(label=label, pos=node.pos)

    def _finish_bib_entry(self) -> None:
        if self._bib_state is None:
            return
        text = normalize_text("".join(self._bib_state.parts))
        if text:
            number = len(self.document.bibliography) + 1
            self.document.bibliography.append(
                BibliographyEntry(
                    number=number,
                    label=self._bib_state.label,
                    text=text,
                    location=self._location(self._bib_state.pos),
                )
            )
            self.document.fragments.append(
                TextFragment(
                    text=text,
                    location=self._location(self._bib_state.pos),
                    kind=FragmentKind.bibliography_entry,
                )
            )
        self._bib_state = None

    def _append_text(self, text: str, pos: int) -> None:
        if not text:
            return
        if self._bib_state is not None:
            self._bib_state.parts.append(text)
            return
        if self._lists and self._lists[-1].current_marker is not None:
            self._lists[-1].current_parts.append(text)
            return
        if self._para_pos is None:
            self._para_pos = pos
        parts = re.split(r"\n[ \t]*\n", text)
        for index, part in enumerate(parts):
            if index:
                self._flush_paragraph()
                self._para_pos = pos
            if part:
                self._para_parts.append(part)

    def _flush_paragraph(self) -> None:
        text = normalize_text("".join(self._para_parts))
        self._para_parts = []
        if not text:
            self._para_pos = None
            return
        self._last_paragraph = text
        self.document.fragments.append(
            TextFragment(
                text=text,
                location=self._location(self._para_pos or 0),
                kind=FragmentKind.paragraph,
            )
        )
        self._para_pos = None

    def _plain_text(self, nodes) -> str:
        parts: list[str] = []
        for node in nodes:
            if isinstance(node, LatexCharsNode):
                parts.append(node.chars)
            elif isinstance(node, LatexCommentNode):
                continue
            elif isinstance(node, LatexMathNode):
                parts.append(" ")
            elif isinstance(node, LatexSpecialsNode):
                parts.append(_specials_to_text(node.specials_chars))
            elif isinstance(node, LatexGroupNode):
                parts.append(self._plain_text(node.nodelist))
            elif isinstance(node, LatexMacroNode):
                name = node.macroname
                if name in INLINE_TEXT_MACROS:
                    for group in _group_args(node):
                        parts.append(self._plain_text(group.nodelist))
                elif name == "\\":
                    parts.append(" ")
            elif isinstance(node, LatexEnvironmentNode):
                if node.environmentname not in SKIP_ENVIRONMENTS:
                    parts.append(self._plain_text(node.nodelist))
        return normalize_text("".join(parts))

    def _parse_tabular(self, node: LatexEnvironmentNode) -> list[list[str]]:
        raw = self.source[node.pos : node.pos + node.len]
        body = _tabular_body(raw)
        rows: list[list[str]] = []
        for row in re.split(r"\\\\", body):
            row = re.sub(
                r"\\(?:hline|toprule|midrule|bottomrule|cline\{[^}]*\})", " ", row
            )
            row = row.strip()
            if not row:
                continue
            cells = [_clean_cell(cell) for cell in re.split(r"(?<!\\)&", row)]
            if any(cells):
                rows.append(cells)
        return rows

    # служебное
    def _location(self, pos: int, element: str | None = None) -> Location:
        self._order += 1
        return Location(
            file=self.filename,
            line=self._line(pos),
            section=self._current_section,
            element=element,
            order=self._order,
        )

    def _line(self, pos: int) -> int:
        return bisect.bisect_right(self.line_starts, pos)

    def _postprocess(self) -> None:
        self._bibliography_from_section()

    def _bibliography_from_section(self) -> None:
        if self.document.bibliography:
            return
        target = next(
            (
                heading
                for heading in self.document.headings
                if normalize_text(heading.title).upper() in BIBLIOGRAPHY_TITLES
            ),
            None,
        )
        if target is None:
            return
        section_label = target.number or target.title
        entries: list[BibliographyEntry] = []
        for fragment in self.document.fragments:
            if fragment.location.section != section_label:
                continue
            if fragment.kind is not FragmentKind.paragraph:
                continue
            # В TeX позиции списка могут идти подряд без пустых строк;
            # делим текст по маркерам [n], чтобы не склеить весь список.
            chunks = [
                chunk.strip()
                for chunk in re.split(r"(?=\[\d+\])", fragment.text)
                if chunk.strip()
            ]
            for chunk in chunks:
                match = re.match(r"^\[?(\d+)\]?[.)]?\s+(.*)$", chunk)
                number = int(match.group(1)) if match else len(entries) + 1
                body = match.group(2) if match else chunk
                entries.append(
                    BibliographyEntry(
                        number=number,
                        label=None,
                        text=normalize_text(body),
                        location=fragment.location,
                    )
                )
        self.document.bibliography = entries


# helpers
def extract_tex(source: str, filename: str) -> DocumentModel:
    return TexTextExtractor(source, filename).extract()


def merge_tex_documents(documents: list[DocumentModel]) -> DocumentModel:
    """Объединяет разделы в один документ, сохраняя порядок файлов."""
    result = DocumentModel(source_type=SourceType.tex)
    offset = 0
    for document in documents:
        if document.source_type is not SourceType.tex:
            raise DocumentExtractionError("Объединять можно только TeX-документы")
        maximum = offset
        for collection in (
            document.fragments,
            document.headings,
            document.tables,
            document.figures,
            document.lists,
            document.bibliography,
        ):
            for item in collection:
                item.location.order += offset
                maximum = max(maximum, item.location.order)
        result.fragments.extend(document.fragments)
        result.headings.extend(document.headings)
        result.tables.extend(document.tables)
        result.figures.extend(document.figures)
        result.lists.extend(document.lists)
        result.bibliography.extend(document.bibliography)
        offset = maximum + 1
    return result


def _group_args(node: LatexMacroNode) -> list[LatexGroupNode]:
    if not node.nodeargd or not node.nodeargd.argnlist:
        return []
    return [arg for arg in node.nodeargd.argnlist if isinstance(arg, LatexGroupNode)]


def _specials_to_text(specials: str) -> str:
    return {
        "~": " ",
        "--": "–",
        "---": "—",
        "&": " ",
    }.get(specials, " ")


def _russian_letter(index: int) -> str:
    alphabet = "абвгдежзиклмнопрстуфхцчшщэюя"
    return alphabet[index] if index < len(alphabet) else str(index + 1)


def _tabular_body(raw: str) -> str:
    start = re.search(r"\\begin\{(?:tabular\*?|tabularx|longtable)\}", raw)
    if not start:
        return ""
    body_start = start.end()
    # Пропускаем необязательные аргументы и описание колонок.
    while body_start < len(raw) and raw[body_start] in " \t\n":
        body_start += 1
    if body_start < len(raw) and raw[body_start] == "[":
        close = raw.find("]", body_start)
        body_start = close + 1 if close != -1 else body_start
    if body_start < len(raw) and raw[body_start] == "{":
        depth = 0
        index = body_start
        while index < len(raw):
            if raw[index] == "{":
                depth += 1
            elif raw[index] == "}":
                depth -= 1
                if depth == 0:
                    body_start = index + 1
                    break
            index += 1
    end = raw.rfind("\\end{")
    return raw[body_start:end] if end != -1 else raw[body_start:]


def _clean_cell(cell: str) -> str:
    cell = re.sub(r"\$[^$]*\$", " ", cell)
    cell = re.sub(r"\\\([^)]*\\\)", " ", cell)
    cell = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?", " ", cell)
    cell = cell.replace("\\&", "&").replace("\\%", "%").replace("\\_", "_")
    cell = cell.replace("{", "").replace("}", "")
    cell = cell.replace("--", "–").replace("~", " ")
    return normalize_text(cell)

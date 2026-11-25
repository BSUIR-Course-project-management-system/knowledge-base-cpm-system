"""Восстановление текста PDF по шрифтовым `/Differences`.

Некоторые PDF (например, macOS Quartz PDFContext) содержат корректный
``/Encoding /Differences`` с именами глифов, но некорректный ``/ToUnicode``:
PyMuPDF доверяет ToUnicode и извлекает ``!`` вместо ``С``. Здесь мы строим
обратное соответствие «неверный символ -> настоящий» по Differences и AGL.
"""

from __future__ import annotations

import io
import os
import re
import tempfile

from fontTools import agl
from fontTools.t1Lib import T1Font
from fontTools.ttLib import TTFont

_DIFFERENCES_RE = re.compile(r"/Differences\s*\[(.*?)\]", re.DOTALL)
_GLYPH_OR_NUMBER_RE = re.compile(r"/([^\s/\[\]]+)|(\d+)")
_CUSTOM_GLYPHS = {
    "guillemotleft": "«",
    "guillemotright": "»",
    "emdash": "—",
    "endash": "–",
    "quotedblleft": "“",
    "quotedblright": "”",
    "quotesingle": "'",
}


class PdfFontDecoder:
    """Кэширует карты перекодирования для шрифтов документа."""

    def __init__(self, document):
        self.document = document
        self._by_xref: dict[int, dict[str, str]] = {}
        self._by_page: dict[int, dict[str, dict[str, str]]] = {}
        self._glyphs_by_xref: dict[int, list[str]] = {}
        self._usage_by_page: dict[int, dict[str, dict[str, str]]] = {}
        self._xrefs_by_page: dict[int, dict[str, int]] = {}

    def decode_span(self, page, page_number: int, span) -> str | None:
        """Декодирует span по фактическим глифам; None — если шрифт не разобран."""
        names = self._glyph_names(
            self.font_xrefs(page, page_number).get(span.get("font", ""))
        )
        if not names:
            return None
        result: list[str] = []
        previous_x1: float | None = None
        for item in span.get("chars", ()):
            wrong_code, glyph_id = item[0], item[1]
            wrong = chr(wrong_code) if isinstance(wrong_code, int) else str(wrong_code)
            right = names[glyph_id] if 0 <= glyph_id < len(names) else ""
            char = right or wrong
            char_bbox = item[3] if len(item) > 3 else None
            if (
                result
                and previous_x1 is not None
                and char_bbox is not None
                and char_bbox[0] - previous_x1 > 1.2
                and not result[-1].endswith(" ")
                and char not in ".,;:!?)]}…"
                and result[-1] not in "([«"
            ):
                result.append(" ")
            result.append(char)
            if char_bbox is not None:
                previous_x1 = char_bbox[2]
        return "".join(result)

    def font_xrefs(self, page, page_number: int) -> dict[str, int]:
        if page_number in self._xrefs_by_page:
            return self._xrefs_by_page[page_number]
        result: dict[str, int] = {}
        try:
            for font in page.get_fonts(full=True):
                result[(font[3] or "").split("+", 1)[-1]] = font[0]
        except Exception:  # noqa: BLE001
            pass
        self._xrefs_by_page[page_number] = result
        return result

    def usage_maps_for_page(self, page, page_number: int) -> dict[str, dict[str, str]]:
        """Карты «неверный символ -> настоящий» по фактическим глифам страницы."""
        if page_number in self._usage_by_page:
            return self._usage_by_page[page_number]
        name_to_xref: dict[str, int] = {}
        try:
            for font in page.get_fonts(full=True):
                name_to_xref[(font[3] or "").split("+", 1)[-1]] = font[0]
        except Exception:  # noqa: BLE001
            pass
        maps: dict[str, dict[str, str]] = {}
        try:
            trace = page.get_texttrace()
        except Exception:  # noqa: BLE001
            trace = []
        for span in trace:
            font_name = span.get("font", "")
            names = self._glyph_names(name_to_xref.get(font_name))
            if not names:
                continue
            mapping = maps.setdefault(font_name, {})
            for item in span.get("chars", ()):
                wrong_code, glyph_id = item[0], item[1]
                wrong = (
                    chr(wrong_code) if isinstance(wrong_code, int) else str(wrong_code)
                )
                right = names[glyph_id] if 0 <= glyph_id < len(names) else ""
                if len(wrong) != 1 or len(right) != 1 or wrong == right:
                    continue
                if wrong in mapping and mapping[wrong] != right:
                    mapping.pop(wrong, None)
                else:
                    mapping[wrong] = right
        maps = {font: mapping for font, mapping in maps.items() if mapping}
        self._usage_by_page[page_number] = maps
        return maps

    def _glyph_names(self, xref: int | None) -> list[str]:
        if xref is None:
            return []
        if xref in self._glyphs_by_xref:
            return self._glyphs_by_xref[xref]
        names: list[str] = []
        try:
            _, extension, _, content = self.document.extract_font(xref)
        except Exception:  # noqa: BLE001
            self._glyphs_by_xref[xref] = names
            return names

        extension = (extension or "").lower()
        try:
            if extension in {"pfa", "pfb", "cff"}:
                handle, path = tempfile.mkstemp(suffix=f".{extension}")
                try:
                    with os.fdopen(handle, "wb") as stream:
                        stream.write(content)
                    names = [
                        glyph_to_unicode(name)
                        for name in T1Font(path).getGlyphSet().keys()
                    ]
                finally:
                    try:
                        os.unlink(path)
                    except OSError:
                        pass
            elif extension in {"ttf", "otf", "ttc"}:
                font = TTFont(io.BytesIO(content))
                names = [glyph_to_unicode(name) for name in font.getGlyphOrder()]
        except Exception:  # noqa: BLE001
            names = []
        self._glyphs_by_xref[xref] = names
        return names

    def for_page(self, page, page_number: int) -> dict[str, dict[str, str]]:
        if page_number in self._by_page:
            return self._by_page[page_number]
        maps: dict[str, dict[str, str]] = {}
        try:
            fonts = page.get_fonts(full=True)
        except Exception:  # noqa: BLE001
            fonts = []
        for font in fonts:
            xref = font[0]
            basefont = font[3] or ""
            name = basefont.split("+", 1)[-1]
            mapping = self._mapping_for_xref(xref)
            if mapping:
                maps[name] = mapping
        self._by_page[page_number] = maps
        return maps

    def _mapping_for_xref(self, xref: int) -> dict[str, str]:
        if xref in self._by_xref:
            return self._by_xref[xref]
        mapping: dict[str, str] = {}
        try:
            encoding = self.document.xref_get_key(xref, "Encoding")
        except Exception:  # noqa: BLE001
            encoding = ("", "")
        if encoding[0] != "dict":
            self._by_xref[xref] = mapping
            return mapping

        differences = _parse_differences(encoding[1])
        if not differences:
            self._by_xref[xref] = mapping
            return mapping

        tounicode = _parse_tounicode(self.document, xref)
        for code, glyph_name in differences.items():
            right = glyph_to_unicode(glyph_name)
            wrong = tounicode.get(code)
            if not right or not wrong or len(wrong) != 1 or wrong == right:
                continue
            mapping.setdefault(wrong, right)
        self._by_xref[xref] = mapping
        return mapping


def apply_mapping(mapping: dict[str, str] | None, text: str) -> str:
    if not mapping:
        return text
    return "".join(mapping.get(char, char) for char in text)


def combined_mapping(maps: dict[str, dict[str, str]]) -> dict[str, str]:
    """Общая карта страницы (для текста, извлечённого без привязки к шрифту)."""
    merged: dict[str, str] = {}
    conflicted: set[str] = set()
    for mapping in maps.values():
        for wrong, right in mapping.items():
            if wrong in merged and merged[wrong] != right:
                conflicted.add(wrong)
            else:
                merged[wrong] = right
    for wrong in conflicted:
        merged.pop(wrong, None)
    return merged


def glyph_to_unicode(glyph_name: str) -> str:
    value = agl.toUnicode(glyph_name)
    if len(value) == 1:
        return value
    base = glyph_name.split(".", 1)[0]
    value = agl.toUnicode(base)
    if len(value) == 1:
        return value
    return _CUSTOM_GLYPHS.get(base, "")


def _parse_differences(body: str) -> dict[int, str]:
    match = _DIFFERENCES_RE.search(body)
    if not match:
        return {}
    result: dict[int, str] = {}
    code: int | None = None
    for name, number in _GLYPH_OR_NUMBER_RE.findall(match.group(1)):
        if number:
            code = int(number)
        elif name and code is not None:
            result[code] = name
            code += 1
    return result


def _parse_tounicode(document, xref: int) -> dict[int, str]:
    try:
        key = document.xref_get_key(xref, "ToUnicode")
        if key[0] != "xref":
            return {}
        stream_xref = int(key[1].split()[0])
        raw = document.xref_stream(stream_xref)
    except Exception:  # noqa: BLE001
        return {}
    stream = raw.decode("latin-1", errors="replace")
    result: dict[int, str] = {}

    for block in re.findall(r"beginbfchar(.*?)endbfchar", stream, re.DOTALL):
        for source, destination in re.findall(
            r"<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]+)>", block
        ):
            result[int(source, 16)] = _hex_to_text(destination)

    for block in re.findall(r"beginbfrange(.*?)endbfrange", stream, re.DOTALL):
        for source, end, destination in re.findall(
            r"<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]+)>", block
        ):
            start_code, end_code = int(source, 16), int(end, 16)
            start_unicode = int(destination, 16)
            for offset in range(end_code - start_code + 1):
                result[start_code + offset] = chr(start_unicode + offset)
    return result


def _hex_to_text(value: str) -> str:
    return "".join(
        chr(int(value[index : index + 4], 16)) for index in range(0, len(value), 4)
    )

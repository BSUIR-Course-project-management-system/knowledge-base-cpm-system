"""Извлечение единой модели документа из PDF и TeX."""

from .pdf_paragraphs import PdfTextExtractor, extract_pdf
from .tex_cleaner import TexTextExtractor, extract_tex, merge_tex_documents

__all__ = [
    "PdfTextExtractor",
    "TexTextExtractor",
    "extract_pdf",
    "extract_tex",
    "merge_tex_documents",
]

"""Реестр реализованных проверок: ``check.type`` -> функция чекера."""

from __future__ import annotations

from . import bibliography, front_matter

CHECKERS = {
    "assignment_pages": front_matter.check_assignment_pages,
    "assignment_questions": front_matter.check_assignment_questions,
    "toc_pages": front_matter.check_toc_pages,
    "toc_max_level": front_matter.check_toc_max_level,
    "abbreviations_not_empty": front_matter.check_abbreviations,
    "abbreviations_page": front_matter.check_abbreviations_page,
    "bibliography_min_items": bibliography.check_min_items,
    "bibliography_gost_fields": bibliography.check_gost_fields,
}

# Необязательный модуль орфографии: удаление каталога spelling убирает и
# проверку, и её правило.
try:
    from ..spelling import CHECKERS as SPELLING_CHECKERS
except ImportError:  # pragma: no cover - модуль вырезан
    pass
else:
    CHECKERS.update(SPELLING_CHECKERS)

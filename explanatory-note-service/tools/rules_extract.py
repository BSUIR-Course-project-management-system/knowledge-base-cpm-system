#!/usr/bin/env python3
"""Офлайн-извлечение текста исходных документов для разметки правил.

Утилита не входит в рантайм сервиса: она запускается разработчиком на
машине, где доступны исходные PDF (СТП 01-2024 и методическое руководство),
и помогает вручную составить ``app/note_checker/rules/data/rules.json``.

Пример:

    python tools/rules_extract.py ../documents/*.pdf --out-dir /tmp/rules-text

Результат — по одному ``.txt`` на документ с маркерами страниц. Файлы
исходников и извлечённый текст в git не коммитятся.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")


def _import_fitz():
    try:
        import fitz  # PyMuPDF
    except ImportError:  # pragma: no cover - зависит от окружения разработчика
        sys.exit(
            "Не установлен PyMuPDF. Установите зависимости: "
            "pip install -r requirements.txt"
        )
    return fitz


def extract_pdf(path: Path, out_dir: Path) -> Path:
    """Пишет текст PDF постранично и возвращает путь к результату."""
    fitz = _import_fitz()
    try:
        document = fitz.open(path)
    except Exception as exc:  # noqa: BLE001 - сообщение важнее типа ошибки
        sys.exit(f"Не удалось открыть {path}: {exc}")

    chunks: list[str] = []
    total_chars = 0
    total_cyrillic = 0
    with document:
        for page_number, page in enumerate(document, start=1):
            text = page.get_text() or ""
            total_chars += len(text)
            total_cyrillic += len(CYRILLIC_RE.findall(text))
            chunks.append(f"\n<<< page {page_number} >>>\n{text}")

    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{path.stem}.txt"
    target.write_text("".join(chunks), encoding="utf-8")

    share = total_cyrillic / total_chars if total_chars else 0.0
    print(
        f"{path.name}: страниц {page_number}, символов {total_chars}, "
        f"доля кириллицы {share:.1%} -> {target}"
    )
    if share < 0.2:
        print(
            "  ВНИМАНИЕ: похоже, в PDF нет текстового слоя (скан). "
            "Для разметки потребуется OCR.",
            file=sys.stderr,
        )
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path, help="исходные PDF")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("build/rules-text"),
        help="каталог для извлечённого текста (по умолчанию build/rules-text)",
    )
    args = parser.parse_args(argv)

    missing = [path for path in args.inputs if not path.is_file()]
    if missing:
        parser.error("файлы не найдены: " + ", ".join(str(path) for path in missing))

    for path in args.inputs:
        extract_pdf(path, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Чтение и валидация файлов для проверки пояснительной записки."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

from fastapi import UploadFile

from ..config import Settings
from ..core.exceptions import NoteInputError
from ..note_checker.extraction import extract_pdf, extract_tex, merge_tex_documents
from ..note_checker.model import DocumentModel

SUPPORTED_SUFFIXES = {".pdf", ".tex", ".zip"}


async def read_uploads(
    files: list[UploadFile], settings: Settings
) -> list[tuple[str, bytes]]:
    if not files:
        raise NoteInputError(
            "Приложите файл записки: один PDF, набор .tex-файлов разделов или ZIP"
        )
    if len(files) > settings.max_note_files:
        raise NoteInputError(
            f"Слишком много файлов: {len(files)}, максимум {settings.max_note_files}",
            status_code=413,
        )

    payloads: list[tuple[str, bytes]] = []
    total = 0
    for upload in files:
        name = Path(upload.filename or "").name
        if not name:
            raise NoteInputError("У загруженного файла отсутствует имя")
        suffix = Path(name).suffix.lower()
        if suffix not in SUPPORTED_SUFFIXES:
            raise NoteInputError(
                f"Неподдерживаемый формат файла «{name}». "
                "Приложите PDF, .tex-файлы или ZIP-архив",
                status_code=415,
            )
        data = await upload.read()
        if suffix == ".tex" and len(data) > settings.max_tex_file_bytes:
            raise NoteInputError(
                f"Файл «{name}» больше допустимого размера "
                f"({settings.max_tex_file_bytes} байт)",
                status_code=413,
            )
        total += len(data)
        if total > settings.max_note_bytes:
            raise NoteInputError(
                f"Суммарный размер файлов превышает {settings.max_note_bytes} байт",
                status_code=413,
            )
        payloads.append((name, data))
    return payloads


def build_document(
    payloads: list[tuple[str, bytes]], settings: Settings
) -> tuple[DocumentModel, list[str]]:
    pdfs = [item for item in payloads if Path(item[0]).suffix.lower() == ".pdf"]
    texs = [item for item in payloads if Path(item[0]).suffix.lower() == ".tex"]
    zips = [item for item in payloads if Path(item[0]).suffix.lower() == ".zip"]

    if pdfs:
        if len(pdfs) > 1 or texs or zips:
            raise NoteInputError(
                "Приложите либо один PDF, либо .tex-файлы (можно ZIP), не смешивая форматы"
            )
        name, data = pdfs[0]
        return extract_pdf(data, name), [name]

    if zips:
        if len(zips) > 1 or texs:
            raise NoteInputError(
                "ZIP-архив нельзя сочетать с отдельными .tex-файлами или другим ZIP"
            )
        name, data = zips[0]
        entries = _unpack_zip(name, data, settings)
    else:
        entries = texs

    if not entries:
        raise NoteInputError("Не найдено ни одного .tex-файла для проверки")

    documents: list[DocumentModel] = []
    names: list[str] = []
    for name, data in entries:
        documents.append(extract_tex(_decode_tex(name, data), name))
        names.append(name)
    return merge_tex_documents(documents), names


def _unpack_zip(
    archive_name: str, data: bytes, settings: Settings
) -> list[tuple[str, bytes]]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise NoteInputError(
            f"Файл «{archive_name}» не является корректным ZIP-архивом",
            status_code=400,
        ) from exc

    entries: list[tuple[str, bytes]] = []
    total = 0
    with archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            member = Path(info.filename)
            if member.is_absolute() or ".." in member.parts:
                raise NoteInputError(
                    f"В архиве недопустимый путь «{info.filename}»",
                    status_code=400,
                )
            if member.suffix.lower() != ".tex":
                continue
            if info.file_size > settings.max_tex_file_bytes:
                raise NoteInputError(
                    f"Файл «{member.name}» в архиве больше допустимого размера",
                    status_code=413,
                )
            total += info.file_size
            if total > settings.max_note_bytes:
                raise NoteInputError(
                    "Суммарный размер файлов в архиве превышает допустимый",
                    status_code=413,
                )
            try:
                content = archive.read(info)
            except (RuntimeError, zipfile.BadZipFile) as exc:
                raise NoteInputError(
                    f"Не удалось прочитать «{member.name}» из архива",
                    status_code=400,
                ) from exc
            if len(content) > settings.max_tex_file_bytes:
                raise NoteInputError(
                    f"Файл «{member.name}» в архиве больше допустимого размера",
                    status_code=413,
                )
            entries.append((member.as_posix(), content))

    if not entries:
        raise NoteInputError("В ZIP-архиве нет .tex-файлов")
    entries.sort(key=lambda item: item[0])
    return entries


def _decode_tex(name: str, data: bytes) -> str:
    if b"\x00" in data[:1024]:
        raise NoteInputError(
            f"Файл «{name}» не является текстовым TeX-файлом",
            status_code=422,
        )
    for encoding in ("utf-8-sig", "cp1251"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise NoteInputError(
        f"Файл «{name}» не удалось прочитать как текст (ожидается UTF-8 или Windows-1251)",
        status_code=422,
    )

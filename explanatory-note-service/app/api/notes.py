"""Проверка пояснительной записки: приём PDF/TeX/ZIP и перечень замечаний."""

from __future__ import annotations

from fastapi import APIRouter, File, UploadFile
from starlette.concurrency import run_in_threadpool

from ..schemas import CheckedDocument, CheckResponse
from .deps import NoteCheckerDep, SettingsDep
from .notes_input import build_document, read_uploads

router = APIRouter(prefix="/notes", tags=["notes"])


@router.post("/notes:check", response_model=CheckResponse)
async def check_note(
    checker: NoteCheckerDep,
    settings: SettingsDep,
    file: UploadFile | None = File(
        default=None,
        description="Один файл: PDF, .tex или ZIP с .tex",
    ),
    files: list[UploadFile] | None = File(
        default=None,
        description="Набор .tex-файлов разделов (можно несколько)",
    ),
) -> CheckResponse:
    """Проверяет один PDF, набор .tex-файлов разделов или ZIP с .tex."""
    uploads = ([file] if file is not None else []) + list(files or [])
    payloads = await read_uploads(uploads, settings)
    document, names = await run_in_threadpool(build_document, payloads, settings)
    result = await run_in_threadpool(checker.check, document)
    return CheckResponse(
        findings=result.findings,
        rule_set_version=checker.rule_set_version,
        stats=result.stats,
        document=CheckedDocument(
            source_type=document.source_type,
            files=names,
            pages=document.page_count,
            physical_pages=document.physical_page_count,
        ),
    )


@router.post("/notes:check-file", response_model=CheckResponse)
async def check_note_file(
    checker: NoteCheckerDep,
    settings: SettingsDep,
    file: UploadFile = File(..., description="Один файл: PDF, .tex или ZIP с .tex"),
) -> CheckResponse:
    """Удобная для Swagger обёртка: ровно один файл через file input."""
    return await check_note(
        file=file,
        files=None,
        checker=checker,
        settings=settings,
    )

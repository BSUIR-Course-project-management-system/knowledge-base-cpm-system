"""Список и скачивание сгенерированных .tex-файлов."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ...schemas import FilesResponse
from ..deps import TaskSheetServiceDep

router = APIRouter(tags=["assignment-sheets / files"])


@router.get("/files", response_model=FilesResponse)
def list_files(service: TaskSheetServiceDep):
    return FilesResponse(files=service.list_files())


@router.get("/files/{name}", response_class=FileResponse)
def download_file(name: str, service: TaskSheetServiceDep):
    path = service.get_file(name)
    if path is None:
        raise HTTPException(status_code=404, detail="Файл не найден")
    return FileResponse(path, filename=name, media_type="application/x-tex")

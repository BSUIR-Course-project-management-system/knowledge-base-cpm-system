"""Генерация файлов листа задания."""

from __future__ import annotations

from fastapi import APIRouter

from ...schemas import GenerateResponse, StudentPayload
from ..deps import TaskSheetServiceDep

router = APIRouter(tags=["assignment-sheets / generation"])


@router.post("/generate", response_model=GenerateResponse)
def generate(payload: StudentPayload, service: TaskSheetServiceDep):
    """Сгенерировать два .tex по полям студента и записать их в OUTPUT_DIR."""
    result = service.generate(payload.model_dump())
    return GenerateResponse(
        files=result.files,
        system_revision=result.system_revision,
        system_updated_at=result.system_updated_at,
    )

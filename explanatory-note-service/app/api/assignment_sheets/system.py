"""Системные данные генерации листа задания."""

from __future__ import annotations

from fastapi import APIRouter

from ...schemas import SystemResponse, SystemValues
from ..deps import TaskSheetServiceDep

router = APIRouter(tags=["assignment-sheets / system"])


def _system_response(service, values, revision, updated_at) -> SystemResponse:
    return SystemResponse(values=values, revision=revision, updated_at=updated_at)


@router.get("/system", response_model=SystemResponse)
def get_system(service: TaskSheetServiceDep):
    """Текущие системные данные (задаются отдельно и меняются редко)."""
    return _system_response(service, *service.system_snapshot())


@router.put("/system", response_model=SystemResponse)
def put_system(payload: SystemValues, service: TaskSheetServiceDep):
    """Полная замена системных данных."""
    return _system_response(service, *service.replace_system(payload.model_dump()))


@router.patch("/system", response_model=SystemResponse)
def patch_system(payload: SystemValues, service: TaskSheetServiceDep):
    """Частичное обновление системных данных (например, только год)."""
    return _system_response(service, *service.patch_system(payload.model_dump()))

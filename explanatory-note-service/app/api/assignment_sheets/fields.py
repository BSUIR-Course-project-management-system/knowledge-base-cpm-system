"""Схема полей формы листа задания."""

from __future__ import annotations

from fastapi import APIRouter

from ...schemas import FieldsResponse
from ..deps import TaskSheetServiceDep

router = APIRouter(tags=["assignment-sheets / fields"])


@router.get("/fields", response_model=FieldsResponse)
def get_fields(service: TaskSheetServiceDep):
    """Схема полей для GUI: системные поля, поля студента и их лимиты."""
    return service.fields_response()

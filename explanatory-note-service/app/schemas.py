from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .config import DEFAULT_SYSTEM
from .note_checker.model import Finding, SourceType

STUDENT_EXAMPLE: dict[str, Any] = {
    "project_system_name": "Решатель задач",
    "student_full_name_long": "Иванов Иван Иванович",
    "student_fio_short": "И. И. Иванов",
    "student_group_code": "111111",
    "student_code": "123",
    "curator_fio_short": "П. П. Петров",
    "examiner_fio_short": "С. С. Сидоров",
    "source_data_for_project": [""],
    "note_sections": [
        "интеллектуальной системы",
        "интеллектуальной системы",
        "интеллектуальной системы",
    ],
    "graphic_material": [""],
}


class FieldSpec(BaseModel):
    """Описание одного поля из fields.json (для динамической формы GUI)."""

    model_config = ConfigDict(extra="allow")

    type: str
    role: str | None = None
    source: str | None = None
    required: bool | None = None
    min_rows: int | None = None
    max_rows: int | None = None
    max_chars: int | None = None
    default_rows: list[str] = Field(default_factory=list)
    format: str | None = None
    prefix_from: str | None = None


class FieldsResponse(BaseModel):
    system: dict[str, FieldSpec]
    student: dict[str, FieldSpec]


class SystemValues(BaseModel):
    """Тело PUT/PATCH /system: плоский объект системных полей."""

    model_config = ConfigDict(
        extra="allow", json_schema_extra={"example": DEFAULT_SYSTEM}
    )


class SystemResponse(BaseModel):
    values: dict[str, Any]
    revision: int
    updated_at: datetime


class StudentPayload(BaseModel):
    """Тело POST /generate: только поля студента, system берётся с сервера."""

    model_config = ConfigDict(
        extra="allow", json_schema_extra={"example": STUDENT_EXAMPLE}
    )


class FileInfo(BaseModel):
    name: str
    path: str
    url: str
    size: int


class GenerateResponse(BaseModel):
    files: list[FileInfo]
    system_revision: int
    system_updated_at: datetime


class FilesResponse(BaseModel):
    files: list[FileInfo]


class CheckedDocument(BaseModel):
    source_type: SourceType
    files: list[str]
    # Число страниц документа по напечатанной нумерации.
    pages: int | None = None
    # Сколько страниц физически содержится в PDF (для PDF).
    physical_pages: int | None = None


class CheckResponse(BaseModel):
    """Результат проверки записки; версия правил фиксируется для воспроизводимости."""

    findings: list[Finding]
    rule_set_version: str
    stats: dict[str, Any] = Field(default_factory=dict)
    document: CheckedDocument

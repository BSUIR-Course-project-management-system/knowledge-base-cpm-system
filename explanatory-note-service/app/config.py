from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .core.exceptions import ConfigurationError

APP_DIR = Path(__file__).resolve().parent

DEFAULT_FIELDS_PATH = APP_DIR / "task_sheet_filler" / "config" / "fields.json"
DEFAULT_TEMPLATES_DIR = APP_DIR / "task_sheet_filler" / "templates"
DEFAULT_RULES_PATH = APP_DIR / "note_checker" / "rules" / "data" / "rules.json"
DEFAULT_OUTPUT_DIR = APP_DIR / "out"

# Значения config/system.json. Файла в образе нет: они задают стартовое
# состояние серверных настроек и могут быть переопределены через SYSTEM_JSON.
DEFAULT_SYSTEM: dict[str, Any] = {
    "year": "2026",
    "specialty_code": "1-11-1111-01",
    "topic_prefix": "Решатель задач",
    "submission_date": "05.12.2026",
    "date_task_assign": "12.09.2026",
    "semester_numb": "5",
    "course_project_subject": "Проектирование баз знаний",
    "department_head": "И. О. Фамилия",
    "note_section_prefixes": ["Анализ", "Проектирование", "Разработка"],
    "note_blank_rows": 7,
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    output_dir: Path = Field(default=DEFAULT_OUTPUT_DIR)
    fields_path: Path = Field(default=DEFAULT_FIELDS_PATH)
    templates_dir: Path = Field(default=DEFAULT_TEMPLATES_DIR)
    rules_path: Path = Field(default=DEFAULT_RULES_PATH)
    system_json: str | None = Field(default=None)

    max_note_bytes: int = 52_428_800
    max_tex_file_bytes: int = 2_097_152
    max_note_files: int = 200


def get_settings() -> Settings:
    return Settings()


def load_initial_system(settings: Settings) -> dict[str, Any]:
    """Берём system из SYSTEM_JSON, иначе из встроенных значений по умолчанию."""
    if not settings.system_json:
        return dict(DEFAULT_SYSTEM)
    try:
        values = json.loads(settings.system_json)
    except json.JSONDecodeError as exc:
        raise ConfigurationError(
            f"SYSTEM_JSON не является корректным JSON: {exc}"
        ) from exc
    if not isinstance(values, dict):
        raise ConfigurationError("SYSTEM_JSON должен содержать объект")
    return values

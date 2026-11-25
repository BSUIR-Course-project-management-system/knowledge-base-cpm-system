from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

from ..config import ConfigurationError, Settings, load_initial_system
from ..schemas import FileInfo
from ..system_store import SystemStore
from .filler import TaskTemplateFiller, TemplateFillError


def load_fields(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text("utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigurationError(
            f"Не удалось загрузить fields.json ({path}): {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise ConfigurationError("fields.json должен содержать объект")
    return data


def _atomic_write(path: Path, content: str) -> None:
    """Пишет во временный файл рядом и подменяет его, чтобы не было частичного .tex."""
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.chmod(tmp_name, 0o644)
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


@dataclass
class GenerateResult:
    files: list[FileInfo]
    system_revision: int
    system_updated_at: datetime


class TaskSheetService:
    """Связывает API, серверные system-настройки, валидацию и запись .tex."""

    def __init__(self, settings: Settings):
        self.output_dir = Path(settings.output_dir)
        self.fields = load_fields(settings.fields_path)
        self.filler = TaskTemplateFiller(settings.templates_dir, self.fields, {})
        self.filler.preflight()
        self.system_store = SystemStore(
            load_initial_system(settings), self.filler.validate_system
        )
        self.allowed_names = {
            name.removesuffix(".j2") for name in self.filler.templates
        }

    def fields_response(self) -> dict[str, dict]:
        system: dict[str, Any] = {}
        student: dict[str, Any] = {}
        for key, spec in self.fields.items():
            target = system if spec["type"].startswith("sys") else student
            target[key] = spec
        return {"system": system, "student": student}

    def system_snapshot(self) -> tuple[dict[str, Any], int, datetime]:
        return self.system_store.get()

    def replace_system(
        self, values: dict[str, Any]
    ) -> tuple[dict[str, Any], int, datetime]:
        return self.system_store.replace(values)

    def patch_system(
        self, values: dict[str, Any]
    ) -> tuple[dict[str, Any], int, datetime]:
        return self.system_store.patch(values)

    def generate(self, student: dict[str, Any]) -> GenerateResult:
        if not isinstance(student, dict):
            raise TemplateFillError(["тело запроса должно быть объектом"])

        system, revision, updated_at = self.system_snapshot()
        ctx = self.filler.build_context(student, system=system)

        # Сначала рендерим всё в память: при ошибке второго шаблона не будет
        # частично перезаписан результат первого.
        rendered = [
            (name, self.filler.render(name, ctx)) for name in self.filler.templates
        ]

        self.output_dir.mkdir(parents=True, exist_ok=True)
        files = []
        for template_name, content in rendered:
            name = template_name.removesuffix(".j2")
            target = self.output_dir / name
            _atomic_write(target, content)
            files.append(self._file_info(name))
        return GenerateResult(
            files=files, system_revision=revision, system_updated_at=updated_at
        )

    def _file_info(self, name: str) -> FileInfo:
        path = self.output_dir / name
        return FileInfo(
            name=name,
            path=str(path),
            url=f"/api/v1/files/{quote(name)}",
            size=path.stat().st_size,
        )

    def list_files(self) -> list[FileInfo]:
        result = []
        for name in sorted(self.allowed_names):
            if (self.output_dir / name).is_file():
                result.append(self._file_info(name))
        return result

    def get_file(self, name: str) -> Path | None:
        """Только whitelist имён: Path.traversal через URL невозможен."""
        if name not in self.allowed_names:
            return None
        path = self.output_dir / name
        return path if path.is_file() else None

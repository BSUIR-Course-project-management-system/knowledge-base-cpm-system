from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, meta

from .tex_utils import escape_tex, fio


class TemplateFillError(ValueError):
    """Ошибка заполнения: хранит список всех найденных проблем."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("\n".join(errors))


class TaskTemplateFiller:
    """Заполняет .tex-шаблоны (Jinja2) данными студента и системными данными.

    Типы полей в fields.json:
      sys / sys_list / sys_int - значение из system, студент его не задаёт;
      req / opt               - одиночное значение, одна строка, лимит max_chars;
      mltrow                  - список записей, каждая переносится по max_chars,
                                суммарно не больше max_rows физических строк.

    ``system`` можно передать как при создании объекта, так и в ``build_context``
    (нужно для сервиса, где системные данные живут на сервере и меняются
    независимо от запроса).
    """

    TEMPLATES = ("course_task.tex.j2", "course_title.tex.j2")
    ALLOWED_TYPES = {"sys", "sys_list", "sys_int", "req", "opt", "mltrow"}

    def __init__(
        self,
        templates_dir: Path,
        fields: dict | Path,
        system: dict | Path | None = None,
        templates: tuple[str, ...] | None = None,
    ):
        self.templates_dir = Path(templates_dir)
        self.fields = self._load(fields)
        self.system = self._load(system) if system is not None else {}
        self.templates = templates or self.TEMPLATES
        self._check_fields_spec()
        self.env = self._make_env()

    @staticmethod
    def _load(src) -> dict:
        if isinstance(src, dict):
            return src
        return json.loads(Path(src).read_text("utf-8"))

    def _check_fields_spec(self) -> None:
        """Проверяет структуру fields.json на этапе создания объекта."""
        errs: list[str] = []
        if not isinstance(self.fields, dict):
            raise TemplateFillError(["fields.json должен содержать объект"])
        for key, spec in self.fields.items():
            if not isinstance(spec, dict):
                errs.append(f"fields.json: '{key}': описание поля должно быть объектом")
                continue
            ftype = spec.get("type")
            if ftype not in self.ALLOWED_TYPES:
                errs.append(f"fields.json: '{key}': неизвестный тип '{ftype}'")
            if ftype == "mltrow":
                max_rows = spec.get("max_rows")
                if (
                    isinstance(max_rows, bool)
                    or not isinstance(max_rows, int)
                    or max_rows < 1
                ):
                    errs.append(
                        f"fields.json: '{key}': max_rows должно быть целым >= 1"
                    )
                max_chars = spec.get("max_chars")
                if max_chars is not None and (
                    isinstance(max_chars, bool)
                    or not isinstance(max_chars, int)
                    or max_chars < 1
                ):
                    errs.append(
                        f"fields.json: '{key}': max_chars должно быть целым >= 1"
                    )
        if errs:
            raise TemplateFillError(errs)

    def preflight(self) -> None:
        """Проверяет шаблоны один раз при старте сервиса."""
        errs = self.check_templates()
        if errs:
            raise TemplateFillError(errs)

    def check_templates(self) -> list[str]:
        """Находит в шаблонах переменные, которых нет в fields.json."""
        errs = []
        for name in self.templates:
            src = self.env.loader.get_source(self.env, name)[0]
            used = meta.find_undeclared_variables(self.env.parse(src))
            for v in sorted(used - set(self.fields) - {"range", "loop"}):
                errs.append(f"{name}: переменная '{v}' не описана в fields.json")
        return errs

    def _make_env(self) -> Environment:
        env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            block_start_string=r"\BLOCK{",
            block_end_string="}",
            variable_start_string=r"\VAR{",
            variable_end_string="}",
            comment_start_string=r"\#{",
            comment_end_string="}",
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
            undefined=StrictUndefined,
            autoescape=False,
        )
        env.filters["tex"] = escape_tex
        env.filters["fio"] = fio
        return env

    def system_fields(self) -> dict[str, dict]:
        return {k: v for k, v in self.fields.items() if v["type"].startswith("sys")}

    def validate_system(self, system: dict) -> dict:
        """Проверяет и нормализует системные данные (приходят извне API)."""
        if not isinstance(system, dict):
            raise TemplateFillError(["system должен быть объектом"])

        errs: list[str] = []
        spec_by_key = self.system_fields()
        known = set(self.fields)

        for key in system:
            if key not in known:
                errs.append(f"'{key}': неизвестное поле (нет в fields.json)")
            elif key not in spec_by_key:
                errs.append(f"'{key}': поле студента, нельзя задавать в system")

        cleaned: dict = {}
        for key, spec in spec_by_key.items():
            if key not in system:
                errs.append(f"'{key}': не задано в system")
                continue
            value = system[key]
            ftype = spec["type"]
            if ftype == "sys_int":
                if isinstance(value, bool) or not isinstance(value, (int, str)):
                    errs.append(f"'{key}': ожидается целое число")
                else:
                    try:
                        cleaned[key] = int(value)
                    except (TypeError, ValueError):
                        errs.append(f"'{key}': ожидается целое число")
            elif ftype == "sys_list":
                if not isinstance(value, list) or not all(
                    isinstance(x, str) for x in value
                ):
                    errs.append(f"'{key}': ожидается список строк")
                else:
                    cleaned[key] = list(value)
            else:  # sys
                if isinstance(value, bool) or not isinstance(value, (str, int, float)):
                    errs.append(f"'{key}': ожидается скалярное значение")
                else:
                    cleaned[key] = str(value)

        # Шаблон перебирает префиксы и индексирует строки студента по ним,
        # поэтому префиксов не может быть больше, чем максимум строк поля.
        for key, spec in self.fields.items():
            if spec["type"] == "mltrow" and spec.get("prefix_from"):
                prefix_key = spec["prefix_from"]
                prefixes = cleaned.get(prefix_key, [])
                if len(prefixes) > spec["max_rows"]:
                    errs.append(
                        f"'{prefix_key}': {len(prefixes)} префиксов, но максимум строк "
                        f"{spec['max_rows']} (поле '{key}')"
                    )

        if errs:
            raise TemplateFillError(errs)
        return cleaned

    def _rows_mltrow(self, key, spec, student, errors):
        raw = student.get(key, [])
        if not isinstance(raw, list):
            errors.append(f"'{key}': ожидается список строк")
            return []
        rows = list(spec.get("default_rows", [])) + [str(r).strip() for r in raw]
        if spec.get("required") and len([r for r in raw if str(r).strip()]) < spec.get(
            "min_rows", 1
        ):
            errors.append(
                f"'{key}': нужно минимум {spec.get('min_rows', 1)} непустых записей"
            )
        if len(rows) > spec["max_rows"]:
            errors.append(f"'{key}': {len(rows)} строк, максимум {spec['max_rows']}")
        for i, r in enumerate(rows, 1):
            if len(r) > spec.get("max_chars", 10**9):
                errors.append(
                    f"'{key}'[{i}]: {len(r)} симв., рекомендуемый максимум {spec['max_chars']}"
                )
        return rows

    def build_context(self, student: dict, system: dict | None = None) -> dict:
        """Проверяет данные и собирает контекст; при ошибках бросает TemplateFillError."""
        if not isinstance(student, dict):
            raise TemplateFillError(["student должен быть объектом"])
        sys_data = self.validate_system(self.system if system is None else system)

        errors: list[str] = []
        ctx: dict = {}
        sys_ids = set(self.system_fields())

        for key in student:
            if key in sys_ids:
                errors.append(f"'{key}': системное поле, студент не может его задавать")
            elif key not in self.fields:
                errors.append(f"'{key}': неизвестное поле (нет в fields.json)")

        for key, spec in self.fields.items():
            ftype = spec["type"]
            if ftype.startswith("sys"):
                ctx[key] = sys_data[key]
            elif ftype in ("req", "opt"):
                val = str(student.get(key, "")).strip()
                if ftype == "req" and not val:
                    errors.append(f"'{key}': обязательное поле не заполнено")
                if len(val) > spec.get("max_chars", 10**9):
                    errors.append(
                        f"'{key}': {len(val)} симв., максимум {spec['max_chars']}"
                    )
                ctx[key] = val
            elif ftype == "mltrow":
                lines = self._rows_mltrow(key, spec, student, errors)
                lines += [""] * max(0, spec["max_rows"] - len(lines))
                ctx[key] = lines

        if errors:
            raise TemplateFillError(errors)
        return ctx

    def render(self, template: str, ctx: dict) -> str:
        return self.env.get_template(template).render(**ctx)

    def fill(
        self, student: dict | Path, out_dir: Path, system: dict | None = None
    ) -> list[Path]:
        """Рендерит все шаблоны и записывает .tex в out_dir (для локального использования)."""
        student = self._load(student)
        ctx = self.build_context(student, system=system)
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        written = []
        for name in self.templates:
            target = out_dir / name.removesuffix(".j2")
            target.write_text(self.render(name, ctx), encoding="utf-8")
            written.append(target)
        return written

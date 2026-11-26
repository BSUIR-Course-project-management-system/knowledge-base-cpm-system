from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from .api.router import api_router
from .config import ConfigurationError, get_settings
from .core.exceptions import (
    DocumentExtractionError,
    NoteInputError,
    RulesLoadError,
)
from .note_checker.rules.engine import RuleIndex, load_rule_set
from .note_checker.service import NoteChecker
from .task_sheet_filler.filler import TemplateFillError
from .task_sheet_filler.service import TaskSheetService


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    app.state.service = TaskSheetService(settings)
    # Набор правил проверяется при старте: сервис не должен работать с
    # повреждённым rules.json и выдавать искажённый результат.
    app.state.rules = RuleIndex(load_rule_set(settings.rules_path))
    app.state.checker = NoteChecker(app.state.rules)
    yield


app = FastAPI(
    title="Explanatory note service",
    description="Генерация .tex-задания и титульного листа по шаблонам и проверка пояснительной записки курсового проекта.",
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(api_router)


@app.exception_handler(TemplateFillError)
async def template_fill_error_handler(request: Request, exc: TemplateFillError):
    """Ошибки валидации полей с теми же формулировками, что были в CLI."""
    return JSONResponse(status_code=422, content={"detail": {"errors": exc.errors}})


@app.exception_handler(RulesLoadError)
async def rules_load_error_handler(request: Request, exc: RulesLoadError):
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.exception_handler(NoteInputError)
async def note_input_error_handler(request: Request, exc: NoteInputError):
    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})


@app.exception_handler(DocumentExtractionError)
async def document_extraction_error_handler(
    request: Request, exc: DocumentExtractionError
):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(ConfigurationError)
async def configuration_error_handler(request: Request, exc: ConfigurationError):
    return JSONResponse(status_code=500, content={"detail": str(exc)})


def _custom_openapi():
    """Помечает файловые поля как binary, чтобы Swagger показывал file input."""
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    for component in schema.get("components", {}).get("schemas", {}).values():
        properties = component.get("properties") or {}
        for prop in properties.values():
            variants = prop.get("anyOf") or [prop]
            for variant in variants:
                if (
                    variant.get("type") == "string"
                    and variant.get("contentMediaType") == "application/octet-stream"
                ):
                    variant["format"] = "binary"
                if variant.get("type") != "array":
                    continue
                items = variant.get("items") or {}
                if items.get("contentMediaType") == "application/octet-stream":
                    items["format"] = "binary"
    app.openapi_schema = schema
    return schema


app.openapi = _custom_openapi

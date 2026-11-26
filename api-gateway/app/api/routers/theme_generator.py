from fastapi import Request, Depends
from fastapi.routing import APIRouter
from app.api_client import request_service
from app.dependencies import require_roles
from app.schemas import (
    CurrentUserOutSchema,
    GenerateIdeasRequest,
    GenerateIdeasResponse,
)
from app.utils import get_proxy_headers
from app.config import settings

router = APIRouter(prefix="/theme-generation", tags=["Theme generation"])


@router.get("/ready")
async def ready(
    request: Request, _: CurrentUserOutSchema = Depends(require_roles("admin"))
):
    return request_service(
        "GET",
        f"{settings.THEME_GENERATOR_SERVICE}/ready",
        headers=get_proxy_headers(request),
    )


@router.post("/generate", response_model=GenerateIdeasResponse)
async def generate_ideas(
    request: Request,
    schema: GenerateIdeasRequest,
    _: CurrentUserOutSchema = Depends(require_roles("admin", "student")),
):
    return await request_service(
        "POST",
        f"{settings.THEME_GENERATOR_SERVICE}/generate",
        body=schema.model_dump(),
        headers=get_proxy_headers(request),
        timeout=300,
    )

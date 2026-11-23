from fastapi import APIRouter, Request, Depends
from app.schemas import (
    TopicSearchRequest,
    InterestsSearchRequest,
    SearchResponse,
    UpdateDataResponse,
    CurrentUserOutSchema,
    PaperSearchRequest,
    PaperSearchResponse,
    PaperResult,
)
from app.dependencies import require_roles
from app.api_client import request_service
from app.utils import get_proxy_headers
from app.config import settings

router = APIRouter(prefix="/search", tags=["Search"])


@router.post("/topic", response_model=SearchResponse)
async def search_by_topic(
    payload: TopicSearchRequest,
    request: Request,
    _: CurrentUserOutSchema = Depends(require_roles("*")),
):
    return await request_service(
        "POST",
        f"{settings.SEARCH_SERVICE_URL}/search/topic",
        body=payload.model_dump(),
        headers=get_proxy_headers(request),
    )


@router.post("/documents", response_model=PaperSearchResponse)
async def search_documents(
    request: Request,
    schema: PaperSearchRequest,
    _: CurrentUserOutSchema = Depends(require_roles("student", "admin")),
):
    return await request_service(
        "POST",
        f"{settings.SEARCH_SERVICE_URL}/search/documents",
        body=schema.model_dump(),
        headers=get_proxy_headers(request),
        timeout=180,
    )


@router.post("/interests", response_model=SearchResponse)
async def search_by_interests(
    request: Request,
    payload: InterestsSearchRequest,
    _: CurrentUserOutSchema = Depends(require_roles("student")),
):
    profile = await request_service(
        "GET",
        f"{settings.USER_SERVICE_URL}/me",
        headers=get_proxy_headers(request),
    )

    technologies = profile.get("technologies", [])

    search_payload = InterestsSearchRequest(
        n_results=payload.n_results,
        max_distance=payload.max_distance,
        sort_by=payload.sort_by,
    ).model_dump()
    search_payload["interests"] = technologies

    return await request_service(
        "POST",
        f"{settings.SEARCH_SERVICE_URL}/search/interests",
        body=search_payload,
        headers=get_proxy_headers(request),
    )


@router.post("/update-data", response_model=UpdateDataResponse)
async def update_data(
    request: Request, _: CurrentUserOutSchema = Depends(require_roles("admin"))
):
    return await request_service(
        "POST",
        f"{settings.SEARCH_SERVICE_URL}/update-data",
        headers=get_proxy_headers(request),
    )

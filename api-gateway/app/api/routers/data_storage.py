from typing import Annotated
from fastapi import status, Request, Depends, Query
from fastapi.routing import APIRouter

from app.dependencies import require_roles
from app.schemas import (
    RefreshResponse,
    CurrentUserOutSchema,
    GroupOut,
    TopicOut,
    TopicsPage,
    TopicRequest,
)
from app.api_client import request_service
from app.utils import get_proxy_headers
from app.config import settings

router = APIRouter(prefix="/storage", tags=["Data Storage"])


@router.post(
    "/refresh",
    response_model=RefreshResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def storage_refresh(
    request: Request,
    _: CurrentUserOutSchema = Depends(require_roles("admin")),
):
    return await request_service(
        "POST",
        f"{settings.DATA_STORAGE_SERVICE}/refresh",
        headers=get_proxy_headers(request),
    )


@router.get("/status", response_model=RefreshResponse)
async def storage_status(
    request: Request,
    _: CurrentUserOutSchema = Depends(require_roles("admin")),
):
    return await request_service(
        "GET",
        f"{settings.DATA_STORAGE_SERVICE}/status",
        headers=get_proxy_headers(request),
    )


@router.get("/groups", response_model=list[GroupOut])
async def list_groups(
    request: Request,
    _: CurrentUserOutSchema = Depends(require_roles("admin")),
):
    return await request_service(
        "GET",
        f"{settings.DATA_STORAGE_SERVICE}/groups",
        headers=get_proxy_headers(request),
    )


@router.get("/groups/{group_id}", response_model=GroupOut)
async def get_group(
    group_id: str,
    request: Request,
    _: CurrentUserOutSchema = Depends(require_roles("admin")),
):
    return await request_service(
        "GET",
        f"{settings.DATA_STORAGE_SERVICE}/groups/{group_id}",
        headers=get_proxy_headers(request),
    )


@router.get("/topics", response_model=TopicsPage)
async def list_topics(
    request: Request,
    params: Annotated[TopicRequest, Query()],
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _: CurrentUserOutSchema = Depends(require_roles("admin")),
):
    return await request_service(
        "GET",
        f"{settings.DATA_STORAGE_SERVICE}/topics",
        params={
            **params.model_dump(exclude_none=True),
            "limit": limit,
            "offset": offset,
        },
        headers=get_proxy_headers(request),
    )

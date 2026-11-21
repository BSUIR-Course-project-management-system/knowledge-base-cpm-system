from fastapi import Request, Depends
from fastapi.routing import APIRouter
from app.schemas import (
    ScheduleGenerateSchema,
    ScheduleResponseSchema,
    CurrentUserOutSchema,
)
from app.dependencies import require_roles
from app.api_client import request_service
from app.utils import get_proxy_headers
from app.config import settings

router = APIRouter(prefix="/schedule", tags=["Schedule"])


@router.post("/milestones", response_model=ScheduleResponseSchema)
async def generate_schedule(
    request: Request,
    schema: ScheduleGenerateSchema,
    _: CurrentUserOutSchema = Depends(require_roles("teacher")),
):
    return await request_service(
        "POST",
        f"{settings.SCHEDULE_SERVICE}/milestone-schedule",
        body=schema.model_dump(),
        headers=get_proxy_headers(request),
    )

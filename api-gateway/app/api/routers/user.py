import uuid
from fastapi import APIRouter, Query, Request, status, Depends
from fastapi.responses import JSONResponse
from app.schemas import (
    AdminUserUpdateSchema,
    LoginSchema,
    RequestRefreshSchema,
    StudentRegistrationSchema,
    TeacherRegistrationSchema,
    TokenResponseSchema,
    UserOutSchema,
    StudentProfileOut,
    StudentUpdateSchema,
    TeacherProfileOut,
    CurrentUserOutSchema,
)
from app.dependencies import require_roles
from app.api_client import request_service
from app.config import settings
from app.utils import get_proxy_headers

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/register/students", response_model=TokenResponseSchema)
async def register_student(schema: StudentRegistrationSchema) -> TokenResponseSchema:
    return await request_service(
        "POST",
        f"{settings.USER_SERVICE_URL}/auth/register/student",
        body=schema.model_dump(),
    )


@router.post("/register/teacher", response_model=TokenResponseSchema)
async def register_teacher(schema: TeacherRegistrationSchema) -> TokenResponseSchema:
    return await request_service(
        "POST",
        f"{settings.USER_SERVICE_URL}/auth/register/teacher",
        body=schema.model_dump(),
    )


@router.post("/auth/login", response_model=TokenResponseSchema)
async def login(data: LoginSchema) -> TokenResponseSchema:
    return await request_service(
        "POST",
        f"{settings.USER_SERVICE_URL}/auth/login",
        body=data.model_dump(),
    )


@router.post("/auth/logout", response_class=JSONResponse)
async def logout(_: CurrentUserOutSchema = Depends(require_roles("*"))):
    return await request_service(
        "POST",
        f"{settings.USER_SERVICE_URL}/auth/logout",
    )


@router.post("/auth/refresh", response_model=TokenResponseSchema)
async def refresh(
    data: RequestRefreshSchema, _: CurrentUserOutSchema = Depends(require_roles("*"))
) -> TokenResponseSchema:
    return await request_service(
        "POST",
        f"{settings.USER_SERVICE_URL}/auth/refresh",
        body=data.model_dump(),
    )


@router.get("/admin/users", response_model=list[UserOutSchema])
async def list_users(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: CurrentUserOutSchema = Depends(require_roles("admin")),
):
    return await request_service(
        "GET",
        f"{settings.USER_SERVICE_URL}/admin/users",
        params={"limit": limit, "offset": offset},
    )


@router.get("/admin/users/{user_id}", response_model=UserOutSchema)
async def get_user(
    user_id: uuid.UUID, _: CurrentUserOutSchema = Depends(require_roles("admin"))
):
    return await request_service(
        "GET",
        f"{settings.USER_SERVICE_URL}/admin/users/{user_id}",
    )


@router.patch("/admin/users/{user_id}", response_model=UserOutSchema)
async def update_user(
    user_id: uuid.UUID,
    body: AdminUserUpdateSchema,
    _: CurrentUserOutSchema = Depends(require_roles("admin")),
):
    return await request_service(
        "PATCH",
        f"{settings.USER_SERVICE_URL}/admin/users/{user_id}",
        body=body.model_dump(exclude_unset=True),
    )


@router.delete("/admin/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID, _: CurrentUserOutSchema = Depends(require_roles("admin"))
):
    return await request_service(
        "DELETE",
        f"{settings.USER_SERVICE_URL}/admin/users/{user_id}",
    )


@router.post("/admin/users/{user_id}/revoke-sessions")
async def revoke_user_sessions(
    user_id: uuid.UUID, _: CurrentUserOutSchema = Depends(require_roles("admin"))
):
    return await request_service(
        "POST",
        f"{settings.USER_SERVICE_URL}/admin/users/{user_id}/revoke-sessions",
    )


@router.patch("/me", response_model=StudentProfileOut | TeacherProfileOut)
async def update_profile(
    request: Request,
    schema: StudentUpdateSchema,
    _: CurrentUserOutSchema = Depends(require_roles("*")),
):
    return await request_service(
        "PATCH",
        f"{settings.USER_SERVICE_URL}/me",
        body=schema.model_dump(exclude_unset=True),
        headers=get_proxy_headers(request),
    )


@router.get("/me", response_model=StudentProfileOut | TeacherProfileOut)
async def get_profile(
    request: Request, _: CurrentUserOutSchema = Depends(require_roles("*"))
):
    return await request_service(
        "GET", f"{settings.USER_SERVICE_URL}/me", headers=get_proxy_headers(request)
    )

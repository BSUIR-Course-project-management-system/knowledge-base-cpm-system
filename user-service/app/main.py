import uuid
from fastapi import Depends, FastAPI, Query, status
from app.dependencies import get_service
from app.schemas import (
    AdminUserUpdateSchema,
    LoginSchema,
    RequestRefreshSchema,
    StudentRegistrationSchema,
    TeacherRegistrationSchema,
    TokenResponseSchema,
    UserOutSchema,
)
from .service import UserService
import uvicorn

app = FastAPI(title="Auth Service")


@app.post(
    "/auth/register/student",
    response_model=TokenResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def register_student(
    data: StudentRegistrationSchema,
    service: UserService = Depends(get_service),
) -> TokenResponseSchema:
    return await service.register(data)


@app.post(
    "/auth/register/teacher",
    response_model=TokenResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def register_teacher(
    data: TeacherRegistrationSchema,
    service: UserService = Depends(get_service),
) -> TokenResponseSchema:
    return await service.register(data)


@app.post("/auth/login", response_model=TokenResponseSchema)
async def login(
    data: LoginSchema,
    service: UserService = Depends(get_service),
) -> TokenResponseSchema:
    return await service.login(data)


@app.post("/auth/refresh", response_model=TokenResponseSchema)
async def refresh(
    data: RequestRefreshSchema,
    service: UserService = Depends(get_service),
) -> TokenResponseSchema:
    return await service.refresh(data)


@app.get("/admin/users", response_model=list[UserOutSchema])
async def list_users(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: UserService = Depends(get_service),
) -> list[UserOutSchema]:
    users = await service.list_users(limit=limit, offset=offset)
    return [UserOutSchema.model_validate(u) for u in users]


@app.get("/admin/users/{user_id}", response_model=UserOutSchema)
async def get_user(
    user_id: uuid.UUID,
    service: UserService = Depends(get_service),
) -> UserOutSchema:
    user = await service.get_user(user_id)
    return UserOutSchema.model_validate(user)


@app.patch("/admin/users/{user_id}", response_model=UserOutSchema)
async def update_user(
    user_id: uuid.UUID,
    body: AdminUserUpdateSchema,
    service: UserService = Depends(get_service),
) -> UserOutSchema:
    user = await service.update_user(user_id, **body.model_dump(exclude_unset=True))
    return UserOutSchema.model_validate(user)


@app.delete(
    "/admin/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_user(
    user_id: uuid.UUID,
    service: UserService = Depends(get_service),
) -> None:
    await service.delete_user(user_id)


@app.post("/admin/users/{user_id}/revoke-sessions")
async def revoke_user_sessions(
    user_id: uuid.UUID,
    service: UserService = Depends(get_service),
) -> dict[str, int]:
    count = await service.revoke_user_sessions(user_id)
    return {"revoked": count}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)

from fastapi import APIRouter, Request, Depends, File, UploadFile
from fastapi.responses import Response

from app.dependencies import require_roles
from app.schemas import (
    CurrentUserOutSchema,
    FieldsResponse,
    SystemResponse,
    SystemValues,
    StudentPayload,
    GenerateResponse,
    FilesResponse,
    CheckResponse,
)
from app.api_client import request_service
from app.utils import get_proxy_headers
from app.config import settings

router = APIRouter(prefix="/notes", tags=["Assignment Sheets"])


@router.get("/fields", response_model=FieldsResponse)
async def get_fields(
    request: Request,
    _: CurrentUserOutSchema = Depends(require_roles("student", "admin")),
):
    return await request_service(
        "GET",
        f"{settings.EXPLANATORY_NOTE_SERVICE_URL}/fields",
        headers=get_proxy_headers(request),
    )


@router.get("/system", response_model=SystemResponse)
async def get_system(
    request: Request,
    _: CurrentUserOutSchema = Depends(require_roles("admin")),
):
    return await request_service(
        "GET",
        f"{settings.EXPLANATORY_NOTE_SERVICE_URL}/system",
        headers=get_proxy_headers(request),
    )


@router.put("/system", response_model=SystemResponse)
async def put_system(
    payload: SystemValues,
    request: Request,
    _: CurrentUserOutSchema = Depends(require_roles("admin")),
):
    return await request_service(
        "PUT",
        f"{settings.EXPLANATORY_NOTE_SERVICE_URL}/system",
        body=payload.model_dump(),
        headers=get_proxy_headers(request),
    )


@router.patch("/system", response_model=SystemResponse)
async def patch_system(
    payload: SystemValues,
    request: Request,
    _: CurrentUserOutSchema = Depends(require_roles("admin")),
):
    return await request_service(
        "PATCH",
        f"{settings.EXPLANATORY_NOTE_SERVICE_URL}/system",
        body=payload.model_dump(exclude_unset=True),
        headers=get_proxy_headers(request),
    )


@router.post("/generate", response_model=GenerateResponse)
async def generate(
    payload: StudentPayload,
    request: Request,
    _: CurrentUserOutSchema = Depends(require_roles("student", "admin")),
):
    return await request_service(
        "POST",
        f"{settings.EXPLANATORY_NOTE_SERVICE_URL}/generate",
        body=payload.model_dump(),
        headers=get_proxy_headers(request),
    )


@router.get("/files", response_model=FilesResponse)
async def list_files(
    request: Request,
    _: CurrentUserOutSchema = Depends(require_roles("student", "admin")),
):
    return await request_service(
        "GET",
        f"{settings.EXPLANATORY_NOTE_SERVICE_URL}/files",
        headers=get_proxy_headers(request),
    )


@router.get("/files/{name}")
async def download_file(
    name: str,
    request: Request,
    _: CurrentUserOutSchema = Depends(require_roles("student", "admin")),
):
    response = await request_service(
        "GET",
        f"{settings.EXPLANATORY_NOTE_SERVICE_URL}/files/{name}",
        headers=get_proxy_headers(request),
        return_response=True,
    )
    return Response(
        content=response.content,
        media_type="application/x-tex",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.post("/check", response_model=CheckResponse)
async def check_note(
    request: Request,
    _: CurrentUserOutSchema = Depends(require_roles("student", "admin")),
    file: UploadFile | None = File(default=None),
    files: list[UploadFile] | None = File(default=None),
):
    uploads = ([file] if file is not None else []) + list(files or [])

    files_to_send = []
    for upload in uploads:
        content = await upload.read()
        files_to_send.append(
            (
                "files",
                (
                    upload.filename,
                    content,
                    upload.content_type or "application/octet-stream",
                ),
            )
        )

    return await request_service(
        "POST",
        f"{settings.EXPLANATORY_NOTE_SERVICE_URL}/notes:check",
        files=files_to_send,
        headers=get_proxy_headers(request),
        timeout=60,
    )


@router.post("/check-file", response_model=CheckResponse)
async def check_note_file(
    request: Request,
    _: CurrentUserOutSchema = Depends(require_roles("student", "admin")),
    file: UploadFile = File(...),
):
    return await check_note(request=request, file=file, files=None)


@router.get("/rules")
async def get_rules(
    request: Request,
    _: CurrentUserOutSchema = Depends(require_roles("admin")),
):
    return await request_service(
        "GET",
        f"{settings.EXPLANATORY_NOTE_SERVICE_URL}/rules",
        headers=get_proxy_headers(request),
    )

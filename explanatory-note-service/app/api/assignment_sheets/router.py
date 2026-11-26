"""Роутер домена «лист задания»."""

from __future__ import annotations

from fastapi import APIRouter

from .fields import router as fields_router
from .files import router as files_router
from .generation import router as generation_router
from .system import router as system_router

router = APIRouter(prefix="/assignment-sheets", tags=["assignment-sheets"])
router.include_router(fields_router)
router.include_router(system_router)
router.include_router(generation_router)
router.include_router(files_router)

"""Сборка всех HTTP-роутеров приложения."""

from __future__ import annotations

from fastapi import APIRouter

from .assignment_sheets.router import router as assignment_sheets_router
from .health import router as health_router
from .notes import router as notes_router
from .rules import router as rules_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(assignment_sheets_router)
api_router.include_router(rules_router)
api_router.include_router(notes_router)

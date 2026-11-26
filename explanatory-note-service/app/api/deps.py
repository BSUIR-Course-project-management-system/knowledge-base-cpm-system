"""Общие зависимости HTTP-слоя."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from ..config import Settings
from ..note_checker.rules.engine import RuleIndex
from ..note_checker.service import NoteChecker
from ..task_sheet_filler.service import TaskSheetService


def get_task_sheet_service(request: Request) -> TaskSheetService:
    return request.app.state.service


def get_note_checker(request: Request) -> NoteChecker:
    return request.app.state.checker


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_rule_index(request: Request) -> RuleIndex:
    return request.app.state.rules


TaskSheetServiceDep = Annotated[
    TaskSheetService, Depends(get_task_sheet_service)
]
NoteCheckerDep = Annotated[NoteChecker, Depends(get_note_checker)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
RuleIndexDep = Annotated[RuleIndex, Depends(get_rule_index)]

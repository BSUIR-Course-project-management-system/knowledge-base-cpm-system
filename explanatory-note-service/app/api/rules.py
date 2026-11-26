"""Выдача действующего набора правил проверки записки."""

from __future__ import annotations

from fastapi import APIRouter

from ..note_checker.rules.schema import RuleSetView
from .deps import RuleIndexDep

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("/rules", response_model=RuleSetView)
def get_rules(index: RuleIndexDep) -> RuleSetView:
    """Действующий набор правил, его версия и статус реализации проверок."""
    return index.view()

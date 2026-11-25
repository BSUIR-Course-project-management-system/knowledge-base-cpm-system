"""Полная проверка пояснительной записки: правила и статистика."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .checkers.bibliography import bibliography_statistics
from .model import DocumentModel, Finding
from .rules.engine import RuleIndex


class CheckResult(BaseModel):
    findings: list[Finding] = Field(default_factory=list)
    stats: dict[str, Any] = Field(default_factory=dict)


class NoteChecker:
    """Оркестратор: применяет независимые правила к модели документа."""

    def __init__(self, rules: RuleIndex):
        self.rules = rules

    @property
    def rule_set_version(self) -> str:
        return f"{self.rules.rule_set.rule_set_id}@{self.rules.rule_set.version}"

    def check(self, document: DocumentModel) -> CheckResult:
        findings = self.rules.apply(document)
        findings.sort(
            key=lambda finding: (
                finding.location.order,
                finding.rule_id,
                finding.message,
            )
        )
        return CheckResult(
            findings=findings,
            stats={"bibliography": bibliography_statistics(document)},
        )

"""Общие помощники для чекеров: сборка замечаний и места в документе."""

from __future__ import annotations

from ..model import DocumentModel, Finding, Location
from ..rules.schema import Rule


def make_finding(
    rule: Rule,
    location: Location,
    message: str,
    suggestion: str = "",
    manual: bool = False,
) -> Finding:
    return Finding(
        rule_id=rule.rule_id,
        category=rule.category,
        severity=rule.severity,
        location=location,
        requirement_ref=rule.requirement_ref,
        message=message,
        suggestion=suggestion,
        needs_manual_review=manual,
    )


def document_location(document: DocumentModel) -> Location:
    if document.fragments:
        location = document.fragments[0].location.model_copy()
        location.element = None
        location.order = 0
        return location
    return Location(order=0)

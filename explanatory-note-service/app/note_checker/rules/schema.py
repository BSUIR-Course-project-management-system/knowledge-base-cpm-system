"""Схема машиночитаемого набора правил (``rules.json``)."""

from __future__ import annotations

import re
from enum import Enum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .catalog import CHECK_TYPES


class Category(str, Enum):
    bibliography = "bibliography"
    structure = "structure"
    spelling = "spelling"


class ElementType(str, Enum):
    document = "document"
    section = "section"
    heading = "heading"
    paragraph = "paragraph"
    bibliography_entry = "bibliography_entry"


class Severity(str, Enum):
    error = "error"
    warning = "warning"


class RuleStatus(str, Enum):
    active = "active"
    unimplemented = "unimplemented"


_RULE_ID_RE = re.compile(r"^[A-Z]{3}(?:-[A-Z0-9]+)+-\d{3}$")
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


class RuleCheck(BaseModel):
    """Реализация проверки: тип из реестра и её параметры."""

    model_config = ConfigDict(extra="forbid")

    type: str = Field(min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)

    @field_validator("type")
    @classmethod
    def _known_type(cls, value: str) -> str:
        if value not in CHECK_TYPES:
            raise ValueError(
                f"неизвестный тип проверки '{value}'; "
                f"допустимые: {', '.join(sorted(CHECK_TYPES))}"
            )
        return value


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: Annotated[str, Field(pattern=_RULE_ID_RE.pattern)]
    category: Category
    element_types: list[ElementType] = Field(min_length=1)
    description: str = Field(min_length=1)
    requirement_ref: str = Field(min_length=1)
    severity: Severity = Severity.error
    ambiguous: bool = False
    check: RuleCheck


class SourceDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    revision: str = Field(min_length=1)
    reference: str | None = None
    checksum_md5: str | None = Field(default=None, pattern=r"^[0-9a-f]{32}$")


class RuleSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_set_id: Annotated[str, Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]
    version: Annotated[str, Field(pattern=_VERSION_RE.pattern)]
    source_documents: list[SourceDocument] = Field(min_length=1)
    rules: list[Rule] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique_rule_ids(self) -> "RuleSet":
        seen: set[str] = set()
        duplicates: list[str] = []
        for rule in self.rules:
            if rule.rule_id in seen:
                duplicates.append(rule.rule_id)
            seen.add(rule.rule_id)
        if duplicates:
            raise ValueError(
                "повторяющиеся rule_id: " + ", ".join(sorted(set(duplicates)))
            )
        return self


class RuleView(Rule):
    """Правило вместе с вычисленным статусом реализации."""

    status: RuleStatus


class RuleSetView(BaseModel):
    rule_set_id: str
    version: str
    source_documents: list[SourceDocument]
    rules: list[RuleView]

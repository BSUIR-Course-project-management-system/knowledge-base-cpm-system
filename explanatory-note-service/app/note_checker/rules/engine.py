"""Загрузка, индексация и публичное представление набора правил."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from pydantic import ValidationError

from ...core.exceptions import RulesLoadError
from .. import model as document_model
from ..checkers import registry
from . import catalog
from .schema import (
    Category,
    ElementType,
    Rule,
    RuleSet,
    RuleSetView,
    RuleStatus,
    RuleView,
)


def load_rule_set(path: str | Path) -> RuleSet:
    """Читает ``rules.json`` и проверяет его схему; при ошибке — RulesLoadError."""
    path = Path(path)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RulesLoadError(
            f"Не удалось прочитать набор правил {path}: {exc}"
        ) from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RulesLoadError(
            f"Набор правил {path} не является корректным JSON: {exc}"
        ) from exc

    if isinstance(payload, dict):
        payload["rules"] = list(payload.get("rules", [])) + _optional_spelling_rules(
            path
        )

    try:
        return RuleSet.model_validate(payload)
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        )
        raise RulesLoadError(
            f"Набор правил {path} не соответствует схеме: {problems}"
        ) from exc


def _optional_spelling_rules(path: Path) -> list[dict]:
    """Правила из необязательного модуля spelling, если он присутствует."""
    default_path = (Path(__file__).parent / "data" / "rules.json").resolve()
    if path.resolve() != default_path:
        return []
    spelling_rules = (Path(__file__).parents[1] / "spelling" / "rules.json").resolve()
    if not spelling_rules.is_file():
        return []
    try:
        payload = json.loads(spelling_rules.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RulesLoadError(
            f"Не удалось прочитать правила орфографии {spelling_rules}: {exc}"
        ) from exc
    if isinstance(payload, dict):
        payload = payload.get("rules", [])
    if not isinstance(payload, list):
        raise RulesLoadError(
            f"Правила орфографии {spelling_rules} должны содержать список правил"
        )
    return [item for item in payload if isinstance(item, dict)]


class RuleIndex:
    """Правила, проиндексированные по категории и типу элемента."""

    def __init__(self, rule_set: RuleSet):
        self.rule_set = rule_set
        self._by_category: dict[Category, list[Rule]] = defaultdict(list)
        self._by_element_type: dict[ElementType, list[Rule]] = defaultdict(list)
        for rule in rule_set.rules:
            self._by_category[rule.category].append(rule)
            for element_type in rule.element_types:
                self._by_element_type[element_type].append(rule)
        for bucket in (*self._by_category.values(), *self._by_element_type.values()):
            bucket.sort(key=lambda rule: rule.rule_id)

    def __len__(self) -> int:
        return len(self.rule_set.rules)

    def rules_for(
        self, category: Category, element_type: ElementType | None = None
    ) -> list[Rule]:
        """Правила категории; при указании типа — только применимые к нему."""
        rules = self._by_category.get(category, [])
        if element_type is None:
            return list(rules)
        return [rule for rule in rules if element_type in rule.element_types]

    @staticmethod
    def status(rule: Rule) -> RuleStatus:
        if rule.check.type in catalog.IMPLEMENTED_CHECK_TYPES:
            return RuleStatus.active
        return RuleStatus.unimplemented

    def view(self) -> RuleSetView:
        """Публичное представление набора вместе со статусом каждой проверки."""
        return RuleSetView(
            rule_set_id=self.rule_set.rule_set_id,
            version=self.rule_set.version,
            source_documents=self.rule_set.source_documents,
            rules=[
                RuleView(**rule.model_dump(), status=self.status(rule))
                for rule in self.rule_set.rules
            ],
        )

    def apply(
        self, document: document_model.DocumentModel
    ) -> list[document_model.Finding]:
        """Применяет реализованные правила и возвращает детерминированный список.

        Правила категорий независимы; итог сортируется по месту в документе
        и номеру правила, поэтому порядок выполнения чекеров не важен.
        """
        version = f"{self.rule_set.rule_set_id}@{self.rule_set.version}"
        findings: list[document_model.Finding] = []
        for rule in self.rule_set.rules:
            checker = registry.CHECKERS.get(rule.check.type)
            if checker is None:
                continue
            for finding in checker(document, rule):
                finding.rule_set_version = version
                if rule.ambiguous:
                    finding.needs_manual_review = True
                findings.append(finding)
        findings.sort(
            key=lambda finding: (
                finding.location.order,
                finding.rule_id,
                finding.message,
            )
        )
        return findings

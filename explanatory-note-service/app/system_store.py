from __future__ import annotations

import threading
from collections.abc import Callable
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


class SystemStore:
    """Хранит системные данные в памяти и выдаёт неизменяемые снимки для рендера."""

    def __init__(
        self,
        initial: dict[str, Any],
        validator: Callable[[dict[str, Any]], dict[str, Any]],
    ):
        self._lock = threading.RLock()
        self._validator = validator
        self._values = validator(initial)
        self._revision = 0
        self._updated_at = datetime.now(timezone.utc)

    def get(self) -> tuple[dict[str, Any], int, datetime]:
        with self._lock:
            return deepcopy(self._values), self._revision, self._updated_at

    def replace(self, values: dict[str, Any]) -> tuple[dict[str, Any], int, datetime]:
        cleaned = self._validator(values)
        with self._lock:
            return self._set(cleaned)

    def patch(self, values: dict[str, Any]) -> tuple[dict[str, Any], int, datetime]:
        with self._lock:
            merged = deepcopy(self._values)
            merged.update(values)
            return self._set(self._validator(merged))

    def _set(self, cleaned: dict[str, Any]) -> tuple[dict[str, Any], int, datetime]:
        self._values = cleaned
        self._revision += 1
        self._updated_at = datetime.now(timezone.utc)
        return deepcopy(self._values), self._revision, self._updated_at

"""Клиент API Яндекс Спеллера (checkText)."""

from __future__ import annotations

import os
import time

import httpx

from .base import SpellError

DEFAULT_URL = "https://speller.yandex.net/services/spellservice.json/checkText"
# IGNORE_DIGITS (2) | IGNORE_URLS (4) | FIND_REPEAT_WORDS (8)
DEFAULT_OPTIONS = 2 | 4 | 8


class SpellerUnavailable(RuntimeError):
    """Внешнее средство проверки недоступно."""


class YandexSpellerChecker:
    """Реализация ``SpellingChecker`` поверх ``checkText`` Яндекс Спеллера."""

    def __init__(
        self,
        url: str = DEFAULT_URL,
        *,
        timeout: float = 10.0,
        retries: int = 1,
        retry_delay: float = 0.3,
        options: int = DEFAULT_OPTIONS,
        lang: str = "ru",
        transport: httpx.BaseTransport | None = None,
    ):
        self.url = url
        self.retries = max(retries, 0)
        self.retry_delay = max(retry_delay, 0.0)
        self.options = options
        self.lang = lang
        self._client = httpx.Client(timeout=timeout, transport=transport)

    def close(self) -> None:
        self._client.close()

    def check(self, text: str) -> list[SpellError]:
        if not text.strip():
            return []
        payload = {
            "text": text,
            "format": "plain",
            "options": str(self.options),
            "lang": self.lang,
        }
        last_error = "неизвестная ошибка"
        for attempt in range(self.retries + 1):
            try:
                response = self._client.post(self.url, data=payload)
            except httpx.HTTPError as exc:
                last_error = str(exc)
            else:
                if response.status_code >= 500:
                    last_error = f"HTTP {response.status_code}"
                elif response.status_code >= 400:
                    raise SpellerUnavailable(
                        f"Яндекс Спеллер отклонил запрос: HTTP {response.status_code}"
                    )
                else:
                    try:
                        return _parse_errors(response.json())
                    except ValueError as exc:
                        raise SpellerUnavailable(
                            "Яндекс Спеллер вернул некорректный JSON"
                        ) from exc
            if attempt < self.retries and self.retry_delay:
                time.sleep(self.retry_delay * (attempt + 1))
        raise SpellerUnavailable(f"Яндекс Спеллер недоступен: {last_error}")


def create_checker_from_env() -> YandexSpellerChecker | None:
    """Создаёт клиент по переменным окружения; False/0 отключает проверку."""
    enabled = os.getenv("SPELLCHECK_ENABLED", "true").strip().lower()
    if enabled in {"0", "false", "no", "off"}:
        return None
    return YandexSpellerChecker(
        os.getenv("SPELLER_URL", DEFAULT_URL),
        timeout=float(os.getenv("SPELLER_TIMEOUT_SECONDS", "10")),
        retries=int(os.getenv("SPELLER_RETRIES", "1")),
    )


def _parse_errors(payload) -> list[SpellError]:
    if not isinstance(payload, list):
        raise SpellerUnavailable("Яндекс Спеллер вернул неожиданный ответ")
    errors: list[SpellError] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        try:
            pos = int(item.get("pos", -1))
            length = int(item.get("len", 0))
        except (TypeError, ValueError):
            continue
        if pos < 0 or length <= 0:
            continue
        suggestions = tuple(
            str(value) for value in item.get("s", []) if isinstance(value, str)
        )
        errors.append(
            SpellError(
                pos=pos,
                length=length,
                word=str(item.get("word", "")).strip(),
                suggestions=suggestions,
                code=item.get("code") if isinstance(item.get("code"), int) else None,
            )
        )
    return errors

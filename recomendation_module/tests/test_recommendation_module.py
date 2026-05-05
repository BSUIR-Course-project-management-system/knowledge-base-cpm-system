from __future__ import annotations

import builtins
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import numpy as np
import pytest

import recomendation_module.src.recommendation_module as recommendation_module
from recomendation_module import RecommendationModule


TEST_TOPIC_DATA_FILE = Path(__file__).with_name("test.json")
PRODUCTION_TOPIC_DATA_FILE = recommendation_module.TOPIC_DATA_FILE


class FakeModel:
    """Small deterministic model replacement for unit tests."""

    vectors = {
        "python анализ данных": np.array([1.0, 0.0, 0.0]),
        "расписание мобильное приложение": np.array([0.0, 1.0, 0.0]),
        "Анализ данных на Python": np.array([1.0, 0.0, 0.0]),
        "Мобильное приложение для расписания": np.array([0.0, 1.0, 0.0]),
    }

    def encode(self, texts: str | list[str], **_: Any) -> np.ndarray:
        if isinstance(texts, str):
            return self.vectors.get(texts, np.array([0.0, 0.0, 1.0]))

        return np.array(
            [self.vectors.get(text, np.array([0.0, 0.0, 1.0])) for text in texts]
        )


@pytest.fixture
def recommendation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> RecommendationModule:
    monkeypatch.setattr(recommendation_module, "TOPIC_DATA_FILE", TEST_TOPIC_DATA_FILE)
    monkeypatch.setattr(
        recommendation_module,
        "RECOMMENDATION_RANKING_LOG_FILE",
        tmp_path / "search_ranking.log",
    )
    monkeypatch.setattr(
        recommendation_module,
        "RECOMMENDATION_TOPIC_LOG_FILE",
        tmp_path / "topic_descriptions.log",
    )

    return RecommendationModule(model=FakeModel())


def test_loads_topic_catalog_from_test_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    opened_files: list[Path] = []
    original_open = builtins.open

    def tracking_open(file: str | Path, *args: Any, **kwargs: Any):
        opened_files.append(Path(file).resolve())
        return original_open(file, *args, **kwargs)

    monkeypatch.setattr(recommendation_module, "TOPIC_DATA_FILE", TEST_TOPIC_DATA_FILE)
    monkeypatch.setattr(
        recommendation_module,
        "RECOMMENDATION_RANKING_LOG_FILE",
        tmp_path / "search_ranking.log",
    )
    monkeypatch.setattr(
        recommendation_module,
        "RECOMMENDATION_TOPIC_LOG_FILE",
        tmp_path / "topic_descriptions.log",
    )
    monkeypatch.setattr(builtins, "open", tracking_open)

    module = RecommendationModule(model=FakeModel())

    assert TEST_TOPIC_DATA_FILE.resolve() in opened_files
    assert PRODUCTION_TOPIC_DATA_FILE.resolve() not in opened_files
    assert module.topic_catalog == [
        {
            "topic": "Анализ данных на Python",
            "year": "2026",
            "description": "Синтетическое описание темы для unit-тестов рекомендаций.",
            "curator": "Тестовый Куратор",
            "examiner": "Тестовый Проверяющий",
            "_normalized_topic": "анализ данных на python",
        },
        {
            "topic": "Мобильное приложение для расписания",
            "year": "2026",
            "description": "Вторая тестовая тема без связи с рабочими данными.",
            "curator": "Куратор Из Test JSON",
            "examiner": "Проверяющий Из Test JSON",
            "_normalized_topic": "мобильное приложение для расписания",
        },
    ]


def test_build_recommendations_uses_test_json_topic_details(
    recommendation: RecommendationModule,
) -> None:
    results = recommendation.build_recommendations(
        query="python анализ данных",
        documents=[
            "Анализ данных на Python",
            "Мобильное приложение для расписания",
        ],
        distances=[0.11, 0.79],
        metadatas=[
            {"curator": "Метаданные не должны заменить catalog"},
            {"examiner": "Метаданные не должны заменить catalog"},
        ],
    )

    assert len(results) == 2
    assert results[0]["similarity"] == pytest.approx(1.0)
    assert results[0]["similarity_label"] == "очень высокая"
    assert results[0]["distance"] == 0.11
    assert "cosine similarity: 1.000" in results[0]["search_explanation"]
    assert "данных" in results[0]["search_explanation"]
    assert results[0]["topic_description_text"] == (
        "Тема: Анализ данных на Python\n"
        "Описание: Синтетическое описание темы для unit-тестов рекомендаций.\n"
        "Куратор: Тестовый Куратор\n"
        "Проверяющий: Тестовый Проверяющий"
    )


def test_topic_description_falls_back_to_metadata_for_unknown_topic(
    recommendation: RecommendationModule,
) -> None:
    description = recommendation._build_topic_description_text(
        document="Неизвестная тестовая тема",
        metadata={
            "curator": "Куратор из metadata",
            "examiner": "Экзаменатор из metadata",
        },
    )

    assert description == (
        "Тема: Неизвестная тестовая тема\n"
        "Описание: Объяснение будет добавлено позже.\n"
        "Куратор: Куратор из metadata\n"
        "Проверяющий: Экзаменатор из metadata"
    )


def test_explain_search_results_supports_chromadb_grouped_result_shape(
    recommendation: RecommendationModule,
) -> None:
    recommendations = recommendation.explain_search_results(
        query="расписание мобильное приложение",
        search_results={
            "documents": [["Мобильное приложение для расписания"]],
            "distances": [[0.21]],
            "metadatas": [[{"curator": "Не используется из-за catalog"}]],
        },
    )

    assert len(recommendations) == 1
    assert recommendations[0]["document"] == "Мобильное приложение для расписания"
    assert recommendations[0]["distance"] == 0.21
    assert recommendations[0]["similarity"] == pytest.approx(1.0)
    assert "Вторая тестовая тема без связи с рабочими данными." in recommendations[0][
        "topic_description_text"
    ]


def test_search_with_explanations_passes_filters_and_logs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    search_manager = MagicMock()
    search_manager.search_relevant.return_value = {
        "documents": [["Анализ данных на Python"]],
        "distances": [[0.15]],
        "metadatas": [[{"curator": "metadata"}]],
    }
    monkeypatch.setattr(recommendation_module, "TOPIC_DATA_FILE", TEST_TOPIC_DATA_FILE)
    monkeypatch.setattr(
        recommendation_module,
        "RECOMMENDATION_RANKING_LOG_FILE",
        tmp_path / "search_ranking.log",
    )
    monkeypatch.setattr(
        recommendation_module,
        "RECOMMENDATION_TOPIC_LOG_FILE",
        tmp_path / "topic_descriptions.log",
    )

    module = RecommendationModule(search_manager=search_manager, model=FakeModel())
    recommendations = module.search_with_explanations(
        query="python анализ данных",
        n_results=3,
        max_distance=0.5,
        is_used=False,
        curator="Тестовый Куратор",
        examiner="Тестовый Проверяющий",
    )

    search_manager.search_relevant.assert_called_once_with(
        "python анализ данных",
        n_results=3,
        max_distance=0.5,
        is_used=False,
        curator="Тестовый Куратор",
        examiner="Тестовый Проверяющий",
    )
    assert recommendations[0]["document"] == "Анализ данных на Python"
    assert "Синтетическое описание темы" in recommendations[0]["topic_description_text"]
    assert "Запрос: python анализ данных" in (tmp_path / "search_ranking.log").read_text(
        encoding="utf-8"
    )

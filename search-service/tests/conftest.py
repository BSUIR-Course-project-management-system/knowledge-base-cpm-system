from unittest.mock import MagicMock, AsyncMock

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.endpoints import router


def make_topic(
        topic_id: str = "1",
        topic: str = "Чат-бот на Python",
        technologies: str = "Python, FastAPI",
        is_used: bool = False,
        curator: str = "Иванов И.И.",
        examiner: str = "Петров П.П.",
        rounded_final_grade: int | None = None,
        date_defence: str | None = None,
        description: str | None = "Описание темы",
) -> dict:
    return {
        "id": topic_id,
        "topic": topic,
        "description": description,
        "is_used": is_used,
        "curator": curator,
        "examiner": examiner,
        "technologies": technologies,
        "rounded_final_grade": rounded_final_grade,
        "date_defence": date_defence,
    }


def make_chroma_result(
        documents: list[str] | None = None,
        distances: list[float] | None = None,
        metadatas: list[dict] | None = None,
) -> dict:
    return {
        "documents": [documents or []],
        "distances": [distances or []],
        "metadatas": [metadatas or []],
    }


@pytest.fixture
def app() -> FastAPI:
    test_app = FastAPI()
    test_app.include_router(router)
    test_app.state.manager = MagicMock()
    test_app.state.data_storage_client = AsyncMock(spec=httpx.AsyncClient)
    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


@pytest.fixture
def mock_manager(app: FastAPI) -> MagicMock:
    return app.state.manager


@pytest.fixture
def mock_http_client(app: FastAPI) -> MagicMock:
    return app.state.data_storage_client

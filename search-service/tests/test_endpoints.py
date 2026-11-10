from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.endpoints import router


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(router)
    app.state.manager = None
    return app


@pytest.fixture
def ready_app(app):
    manager = MagicMock()
    manager.theme_finder = MagicMock()
    app.state.manager = manager
    return app, manager


def test_health(app):
    client = TestClient(app)

    r = client.get("/health")

    assert r.status_code == 200
    assert r.text == "ok"


def test_search_topic_503_when_no_manager(app):
    client = TestClient(app)

    r = client.post("/search/topic", json={"query": "q"})

    assert r.status_code == 503


def test_search_topic_returns_results(ready_app):
    app, manager = ready_app
    manager.search_relevant.return_value = {
        "documents": [["doc1"]],
        "distances": [[0.1]],
        "metadatas": [[{"a": "b"}]],
    }
    client = TestClient(app)

    r = client.post("/search/topic", json={"query": "python", "n_results": 3})

    assert r.status_code == 200
    body = r.json()
    assert body["results"][0]["document"] == "doc1"
    assert body["results"][0]["distance"] == 0.1
    manager.search_relevant.assert_called_once()


def test_search_topic_500_on_manager_error(ready_app):
    app, manager = ready_app
    manager.search_relevant.side_effect = Exception("boom")
    client = TestClient(app)

    r = client.post("/search/topic", json={"query": "q"})

    assert r.status_code == 500
    assert "boom" in r.json()["detail"]


def test_search_profile_joins_interests(ready_app):
    app, manager = ready_app
    manager.search_relevant.return_value = {
        "documents": [[]],
        "distances": [[]],
        "metadatas": [[]],
    }
    client = TestClient(app)

    r = client.post("/search/profile", json={"interests": ["ai", "ml"]})

    assert r.status_code == 200
    assert manager.search_relevant.call_args.kwargs["query"] == "ai ml"


def test_search_profile_503_when_no_manager(app):
    client = TestClient(app)

    r = client.post("/search/profile", json={"interests": ["x"]})

    assert r.status_code == 503


def test_search_profile_500_on_manager_error(ready_app):
    app, manager = ready_app
    manager.search_relevant.side_effect = Exception("bad")
    client = TestClient(app)

    r = client.post("/search/profile", json={"interests": ["x"]})

    assert r.status_code == 500
    assert "bad" in r.json()["detail"]
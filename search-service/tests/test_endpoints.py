from unittest.mock import MagicMock

import httpx
import pytest

from app.api.endpoints import _format_results
from app.core.config import settings
from app.schemas import SearchResponse
from tests.conftest import make_chroma_result, make_topic


class TestFormatResults:

    def test_converts_chroma_response_to_search_response(self):
        raw = make_chroma_result(
            documents=["Тема 1", "Тема 2"],
            distances=[0.2, 0.8],
            metadatas=[{"original_id": "1"}, {"original_id": "2"}],
        )
        response = _format_results(raw)

        assert isinstance(response, SearchResponse)
        assert len(response.results) == 2
        assert response.results[0].document == "Тема 1"
        assert response.results[0].distance == pytest.approx(0.2)
        assert response.results[0].metadata == {"original_id": "1"}

    def test_empty_chroma_response_gives_empty_results(self):
        raw = make_chroma_result()
        response = _format_results(raw)
        assert response.results == []


class TestSearchByTopic:

    def test_returns_503_when_manager_not_initialized(self, client, app):
        app.state.manager = None
        response = client.post("/search/topic", json={"query": "python"})
        assert response.status_code == 503
        assert "not ready" in response.json()["detail"]

    def test_returns_503_when_search_engine_not_ready(self, client, mock_manager):
        mock_manager.theme_finder = None

        response = client.post("/search/topic", json={"query": "python"})

        assert response.status_code == 503

    def test_returns_results_on_success(self, client, mock_manager):
        mock_manager.theme_finder = MagicMock()
        mock_manager.search_relevant.return_value = make_chroma_result(
            documents=["Чат-бот на Python"],
            distances=[0.35],
            metadatas=[{"original_id": "1", "curator": "Иванов И.И."}],
        )
        response = client.post("/search/topic", json={"query": "чат-бот"})

        assert response.status_code == 200
        body = response.json()
        assert len(body["results"]) == 1
        assert body["results"][0]["document"] == "Чат-бот на Python"
        assert body["results"][0]["distance"] == pytest.approx(0.35)

    def test_passes_request_params_to_manager(self, client, mock_manager):
        mock_manager.theme_finder = MagicMock()
        mock_manager.search_relevant.return_value = make_chroma_result()

        client.post("/search/topic", json={
            "query": "python",
            "n_results": 5,
            "max_distance": 0.4,
            "is_used": True,
            "examiner": "Петров П.П.",
            "sort_by": "grade",
        })

        mock_manager.search_relevant.assert_called_once_with(
            query="python",
            n_results=5,
            max_distance=0.4,
            is_used=True,
            examiner="Петров П.П.",
            sort_by="grade",
        )

    def test_uses_defaults_when_only_query_provided(self, client, mock_manager):
        mock_manager.theme_finder = MagicMock()
        mock_manager.search_relevant.return_value = make_chroma_result()
        client.post("/search/topic", json={"query": "python"})

        mock_manager.search_relevant.assert_called_once_with(
            query="python",
            n_results=10,
            max_distance=settings.MAX_DISTANCE,
            is_used=False,
            examiner=None,
            sort_by="relevance",
        )

    def test_returns_500_when_search_fails(self, client, mock_manager):
        mock_manager.theme_finder = MagicMock()
        mock_manager.search_relevant.side_effect = RuntimeError("model crashed")

        response = client.post("/search/topic", json={"query": "python"})

        assert response.status_code == 500
        assert "model crashed" in response.json()["detail"]

    def test_returns_422_when_query_missing(self, client, mock_manager):
        response = client.post("/search/topic", json={})
        assert response.status_code == 422

    def test_returns_422_when_query_empty_string(self, client, mock_manager):
        response = client.post("/search/topic", json={"query": ""})
        assert response.status_code == 422


class TestSearchByInterests:

    def test_joins_interests_into_single_query(self, client, mock_manager):
        mock_manager.theme_finder = MagicMock()
        mock_manager.search_relevant.return_value = make_chroma_result()

        client.post("/search/interests", json={"interests": ["python", "backend"]})

        _, kwargs = mock_manager.search_relevant.call_args
        assert kwargs["query"] == "python backend"

    def test_returns_results_on_success(self, client, mock_manager):
        mock_manager.theme_finder = MagicMock()
        mock_manager.search_relevant.return_value = make_chroma_result(
            documents=["Backend разработка"],
            distances=[0.4],
            metadatas=[{"original_id": "9"}],
        )

        response = client.post("/search/interests", json={"interests": ["backend"]})
        assert response.status_code == 200
        assert len(response.json()["results"]) == 1

    def test_returns_503_when_search_engine_not_ready(self, client, mock_manager):
        mock_manager.theme_finder = None
        response = client.post("/search/interests", json={"interests": ["x"]})
        assert response.status_code == 503


class TestUpdateData:

    def test_returns_503_when_manager_not_initialized(self, client, app):
        app.state.manager = None
        response = client.post("/update-data")
        assert response.status_code == 503

    def test_returns_503_when_data_storage_unreachable(self, client, mock_http_client):
        mock_http_client.get.side_effect = httpx.RequestError("connection refused")

        response = client.post("/update-data")

        assert response.status_code == 503
        assert "unavailable" in response.json()["detail"]

    def test_propagates_data_storage_error_status(self, client, mock_http_client):
        request = httpx.Request("GET", "http://test/topics")
        error_response = httpx.Response(500, request=request)
        mock_http_client.get.side_effect = httpx.HTTPStatusError(
            "Server error", request=request, response=error_response
        )

        response = client.post("/update-data")

        assert response.status_code == 500
        assert "data-storage error" in response.json()["detail"]

    def test_returns_404_when_no_topics(self, client, mock_http_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"total": 0, "items": []}
        mock_http_client.get.return_value = mock_response

        response = client.post("/update-data")

        assert response.status_code == 404
        assert "пустой список" in response.json()["detail"]

    def test_success_single_page(self, client, mock_http_client, mock_manager):
        topics = [make_topic(topic_id=str(i)) for i in range(3)]
        mock_response = MagicMock()
        mock_response.json.return_value = {"total": 3, "items": topics}
        mock_http_client.get.return_value = mock_response
        response = client.post("/update-data")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "success"
        assert body["updated"] == 3
        mock_manager.process_data.assert_called_once_with(data=topics)

    def test_fetches_all_pages_when_many_topics(
            self, client, mock_http_client, mock_manager
    ):
        page1 = [make_topic(topic_id=str(i)) for i in range(100)]
        page2 = [make_topic(topic_id=str(i)) for i in range(100, 150)]

        resp1, resp2 = MagicMock(), MagicMock()
        resp1.json.return_value = {"total": 150, "items": page1}
        resp2.json.return_value = {"total": 150, "items": page2}
        mock_http_client.get.side_effect = [resp1, resp2]
        response = client.post("/update-data")

        assert response.status_code == 200
        assert response.json()["updated"] == 150
        assert mock_http_client.get.call_count == 2
        second_call_params = mock_http_client.get.call_args_list[1].kwargs["params"]
        assert second_call_params == {"limit": 100, "offset": 100}
        all_items = mock_manager.process_data.call_args.kwargs["data"]
        assert len(all_items) == 150

    def test_no_second_call_when_total_equals_page_size(
            self, client, mock_http_client, mock_manager
    ):
        topics = [make_topic(topic_id=str(i)) for i in range(100)]
        mock_response = MagicMock()
        mock_response.json.return_value = {"total": 100, "items": topics}
        mock_http_client.get.return_value = mock_response

        response = client.post("/update-data")

        assert response.status_code == 200
        mock_http_client.get.assert_called_once()

    def test_returns_500_when_index_rebuild_fails(
            self, client, mock_http_client, mock_manager
    ):
        mock_response = MagicMock()
        mock_response.json.return_value = {"total": 1, "items": [make_topic()]}
        mock_http_client.get.return_value = mock_response
        mock_manager.process_data.side_effect = RuntimeError("chroma is corrupted")
        response = client.post("/update-data")

        assert response.status_code == 500
        assert "chroma is corrupted" in response.json()["detail"]


class TestGetAllTopics:

    def test_returns_503_when_manager_not_ready(self, client, app):
        app.state.manager = None
        assert client.get("/topics").status_code == 503

    def test_returns_503_when_db_not_ready(self, client, mock_manager):
        mock_manager.data_manager = None

        assert client.get("/topics").status_code == 503

    def test_returns_raw_chroma_data(self, client, mock_manager):
        chroma_data = {"documents": ["Тема 1"], "metadatas": [{"original_id": "1"}]}
        mock_manager.data_manager.collection.get.return_value = chroma_data
        response = client.get("/topics")

        assert response.status_code == 200
        assert response.json() == chroma_data
        mock_manager.data_manager.collection.get.assert_called_once_with(
            where={"field_type": "topic"},
            include=["documents", "metadatas"],
        )


class TestHealth:

    def test_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.text == "ok"

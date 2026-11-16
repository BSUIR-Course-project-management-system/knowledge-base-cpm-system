from unittest.mock import MagicMock, patch

import pytest

from app.core.config import settings
from app.search_module.src.data_manager import DataManager
from tests.conftest import make_topic


@pytest.fixture
def chroma_env():
    with patch("app.search_module.src.data_manager.chromadb") as mock_chromadb:
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chromadb.PersistentClient.return_value = mock_client

        yield mock_chromadb, mock_client, mock_collection


class TestInit:

    def test_creates_persistent_client_with_settings_path(self, chroma_env):
        mock_chromadb, _, _ = chroma_env
        DataManager()
        mock_chromadb.PersistentClient.assert_called_once_with(
            path=settings.PATH_TO_CHROMA_DB
        )

    def test_gets_or_creates_named_collection(self, chroma_env):
        _, mock_client, mock_collection = chroma_env

        dm = DataManager()
        mock_client.get_or_create_collection.assert_called_once_with(
            name="my_vectors"
        )
        assert dm.collection is mock_collection

    def test_starts_with_no_data(self, chroma_env):
        dm = DataManager()
        assert dm.data is None


class TestSetData:

    def test_stores_data_reference(self, chroma_env):
        dm = DataManager()
        topics = [make_topic("1"), make_topic("2")]
        dm.set_data(topics)
        assert dm.data == topics


class TestLoadFromCollection:

    def test_loads_documents_with_metadata(self, chroma_env):
        _, _, mock_collection = chroma_env
        dm = DataManager()
        mock_collection.get.return_value = {
            "documents": ["Тема A", "Тема B"],
            "metadatas": [
                {"original_id": "1", "curator": "Иванов"},
                {"original_id": "2", "curator": "Петров"},
            ],
        }
        dm.load_from_collection()
        assert dm.data == [
            {"original_id": "1", "curator": "Иванов", "topic": "Тема A"},
            {"original_id": "2", "curator": "Петров", "topic": "Тема B"},
        ]

    def test_queries_only_topic_records(self, chroma_env):
        _, _, mock_collection = chroma_env
        dm = DataManager()
        dm.load_from_collection()
        mock_collection.get.assert_called_once_with(
            where={"field_type": "topic"}
        )

    def test_empty_collection_gives_empty_list(self, chroma_env):
        _, _, mock_collection = chroma_env
        dm = DataManager()
        mock_collection.get.return_value = {"documents": None}
        dm.load_from_collection()
        assert dm.data == []

    def test_no_result_at_all_gives_empty_list(self, chroma_env):
        _, _, mock_collection = chroma_env
        dm = DataManager()
        mock_collection.get.return_value = None
        dm.load_from_collection()
        assert dm.data == []

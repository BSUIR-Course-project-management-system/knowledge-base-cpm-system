from unittest.mock import MagicMock, patch

import pytest

from search_module.src.data_manager import DataManager


class TestDataManager:
    @pytest.fixture
    def mock_loader(self):
        loader = MagicMock()
        loader.load.return_value = [
            {"id": 1, "text": "Тема 1", "is_used": False},
            {"id": 2, "text": "Тема 2", "is_used": True},
            {"id": 3, "text": "Тема 3", "is_used": False},
        ]
        return loader

    @patch("chromadb.PersistentClient")
    def test_init_creates_collection(self, mock_chroma, mock_loader):
        manager = DataManager(mock_loader)

        mock_chroma.assert_called_once()

        manager.client.get_or_create_collection.assert_called_with(name="my_vectors")

    @patch("chromadb.PersistentClient")
    def test_load_data(self, mock_chroma, mock_loader):
        manager = DataManager(mock_loader)
        manager.load("some.json")

        mock_loader.load.assert_called_once_with("some.json")
        assert len(manager.data) == 3

    @patch("chromadb.PersistentClient")
    def test_filter_by_occupancy(self, mock_chroma, mock_loader):
        manager = DataManager(mock_loader)
        manager.load("some.json")

        manager.filter_by_occupancy()

        assert len(manager.data) == 2
        for item in manager.data:
            assert item["is_used"] is False

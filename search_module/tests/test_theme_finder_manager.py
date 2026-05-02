from unittest.mock import MagicMock, patch

import pytest

from search_module.src.theme_finder import ThemeFinder
from search_module.src.theme_finder_manager import ThemeFinderManager


@pytest.fixture
def mock_dm():
    dm = MagicMock()
    dm.data = [{"id": "1", "text": "тест", "curator": "admin"}]
    dm.collection = MagicMock()
    return dm


class TestThemeFinder:
    @patch("search_module.src.theme_finder.SentenceTransformer")
    def test_make_collection_logic(self, mock_transformer, mock_dm):
        mock_model = mock_transformer.return_value
        mock_model.encode.return_value = MagicMock(tolist=lambda: [[0.1, 0.1]])

        finder = ThemeFinder(mock_dm)

        mock_dm.collection.get.return_value = {"ids": ["old_id"]}

        finder.make_collection()

        mock_dm.collection.delete.assert_called_once_with(ids=["old_id"])
        assert mock_dm.collection.add.called

    @patch("search_module.src.theme_finder.SentenceTransformer")
    def test_search_filters(self, mock_transformer, mock_dm):
        mock_model = mock_transformer.return_value
        mock_model.encode.return_value = MagicMock(tolist=lambda: [[0.0]])

        finder = ThemeFinder(mock_dm)
        finder.search("вопрос", curator="Иванов", is_used=True)

        _, kwargs = mock_dm.collection.query.call_args
        assert "$and" in kwargs["where"]
        assert {"curator": "Иванов"} in kwargs["where"]["$and"]


class TestThemeFinderManager:
    @pytest.fixture
    def manager(self):
        return ThemeFinderManager(loader=MagicMock(), saver=MagicMock())

    def test_process_data_flow(self, manager):
        with patch("table_api.storage.Storage") as mock_storage_cls:
            mock_storage = mock_storage_cls.return_value
            mock_storage.get_unique_topics.return_value = {"topic": "math"}

            manager.process_data("test.json")

            manager.saver.save.assert_called_once()
            assert manager.data_manager is not None

    def test_filter_results_by_distance(self, manager):

        raw_data = {
            "documents": [["Good", "Bad"]],
            "distances": [[0.2, 0.8]],
            "metadatas": [[{"id": 1}, {"id": 2}]],
        }

        filtered = manager.filter_results_by_distance(raw_data, max_distance=0.7)

        assert len(filtered["documents"][0]) == 1
        assert filtered["documents"][0][0] == "Good"

    def test_search_relevant_integration(self, manager):
        manager.theme_finder = MagicMock()
        manager.theme_finder.search.return_value = {
            "documents": [["Result"]],
            "distances": [[0.1]],
            "metadatas": [[{}]],
        }

        res = manager.search_relevant("query")

        assert res["documents"][0] == ["Result"]
        manager.theme_finder.search.assert_called_once()

    def test_prepare_search_data_manager_none(self, manager):
        with pytest.raises(RuntimeError, match="DataManager не инициализирован"):
            manager.prepare_search()

    def test_prepare_search_exception(self, manager):
        manager.data_manager = MagicMock()
        with patch(
            "search_module.src.theme_finder_manager.ThemeFinder",
            side_effect=Exception("Test Error"),
        ):
            with pytest.raises(RuntimeError, match="Не удалось инициализировать поиск"):
                manager.prepare_search()

    def test_search_not_ready(self, manager):
        with pytest.raises(RuntimeError, match="Поиск не готов"):
            manager.search("query")

    def test_search_relevant_not_init(self, manager):
        with pytest.raises(RuntimeError, match="Поиск не инициализирован"):
            manager.search_relevant("query")

    def test_sort_results_by_mark(self, manager):
        raw_data = {
            "documents": [["Weak Theme", "Strong Theme"]],
            "distances": [[0.1, 0.1]],
            "metadatas": [[{"mark": 3}, {"mark": 5}]],
        }

        sorted_res = manager.sort_results(raw_data, mark_priority=1)

        assert sorted_res["metadatas"][0][0]["mark"] == 5
        assert sorted_res["documents"][0][0] == "Strong Theme"

    def test_sort_results_by_distance(self, manager):
        raw_data = {
            "documents": [["Far", "Near"]],
            "distances": [[0.6, 0.2]],
            "metadatas": [[{"mark": 5}, {"mark": 5}]],
        }

        sorted_res = manager.sort_results(raw_data, dist_priority=1)

        assert sorted_res["distances"][0][0] == 0.2
        assert sorted_res["documents"][0][0] == "Near"

    def test_sort_results_combined(self, manager):
        raw_data = {
            "documents": [["Best-Far", "Mid-Near", "Best-Near"]],
            "distances": [[0.8, 0.1, 0.2]],
            "metadatas": [[{"mark": 5}, {"mark": 4}, {"mark": 5}]],
        }

        sorted_res = manager.sort_results(raw_data, mark_priority=1, dist_priority=2)

        results = sorted_res["documents"][0]
        assert results == ["Best-Near", "Best-Far", "Mid-Near"]

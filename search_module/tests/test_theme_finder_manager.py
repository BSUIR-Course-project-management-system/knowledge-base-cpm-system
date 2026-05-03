from unittest.mock import MagicMock, patch

import pytest

with patch.dict(
    "os.environ", {"CREDENTIALS_FILE": "mock.json", "GOOGLE_DRIVE_FOLDER_ID": "mock_id"}
):
    from search_module.src.theme_finder import ThemeFinder
    from search_module.src.theme_finder_manager import ThemeFinderManager


@pytest.fixture
def mock_dm():
    dm = MagicMock()
    dm.data = [
        {"id": "1", "topic": "тест", "curator": "admin", "rounded_final_grade": 5}
    ]
    dm.collection = MagicMock()
    return dm


class TestThemeFinder:
    @patch("search_module.src.theme_finder.SentenceTransformer")
    def test_make_collection_full(self, mock_transformer, mock_dm):
        mock_model = mock_transformer.return_value
        mock_model.encode.return_value = MagicMock(tolist=lambda: [[0.1, 0.1]])
        finder = ThemeFinder(mock_dm)
        mock_dm.collection.get.return_value = {"ids": ["old"]}
        finder.make_collection()
        assert mock_dm.collection.delete.called
        assert mock_dm.collection.add.called

    @patch("search_module.src.theme_finder.SentenceTransformer")
    def test_make_collection_empty_error(self, mock_transformer, mock_dm):
        mock_dm.data = []
        finder = ThemeFinder(mock_dm)
        with pytest.raises(RuntimeError):
            finder.make_collection()

    @patch("search_module.src.theme_finder.SentenceTransformer")
    def test_make_collection_exceptions(self, mock_transformer, mock_dm):
        finder = ThemeFinder(mock_dm)
        mock_dm.collection.get.side_effect = Exception("Get Fail")
        finder.make_collection()
        assert mock_dm.collection.add.called

        mock_dm.collection.add.side_effect = Exception("Add Fail")
        with pytest.raises(Exception):
            finder.make_collection()

    @patch("search_module.src.theme_finder.SentenceTransformer")
    def test_search_branches(self, mock_transformer, mock_dm):
        finder = ThemeFinder(mock_dm)
        finder.search("query", curator="Ivanov")
        finder.search("query", is_used=True, curator="A", examiner="B")
        assert mock_dm.collection.query.called


class TestThemeFinderManager:
    @pytest.fixture
    def manager(self):
        with patch("search_module.src.theme_finder_manager.Storage") as mock_storage:
            mock_storage.return_value = MagicMock()
            loader = MagicMock()
            saver = MagicMock()
            return ThemeFinderManager(loader, saver)

    def test_process_data_success(self, manager):
        manager.storage.get_unique_topics.return_value = [{"topic": "test"}]
        manager.process_data("path.json")
        assert manager.data_manager is not None
        manager.saver.save.assert_called_once()

    def test_prepare_search_fail_no_dm(self, manager):
        manager.data_manager = None
        with pytest.raises(RuntimeError, match="DataManager не инициализирован"):
            manager.prepare_search()

    def test_prepare_search_exception(self, manager):
        manager.data_manager = MagicMock()
        with patch("search_module.src.theme_finder_manager.ThemeFinder") as mock_tf:
            mock_tf.side_effect = Exception("TF Error")
            with pytest.raises(RuntimeError, match="Не удалось инициализировать поиск"):
                manager.prepare_search()

    def test_sort_results_empty(self, manager):
        assert manager.sort_results({"documents": [[]]}) == {"documents": [[]]}

    def test_sort_results_invalid_mark(self, manager):
        raw = {
            "documents": [["Doc1"]],
            "distances": [[0.1]],
            "metadatas": [[{"rounded_final_grade": "bad_mark"}]],
        }
        res = manager.sort_results(raw, mark_priority=1)
        assert res["metadatas"][0][0]["rounded_final_grade"] == "bad_mark"


    def test_sort_results_all_priorities(self, manager):
        raw = {
            "documents": [["A", "B"]],
            "distances": [[0.5, 0.1]],
            "metadatas": [
                [
                    {"rounded_final_grade": 3, "date_defence": "01.01.2020"},
                    {"rounded_final_grade": 5, "date_defence": "01.01.2024"},
                ]
            ],
        }
        res = manager.sort_results(
            raw, mark_priority=1, date_priority=2, dist_priority=3
        )
        assert res["documents"][0][0] == "B"

    def test_search_not_ready(self, manager):
        manager.theme_finder = None
        with pytest.raises(RuntimeError, match="Поиск не готов"):
            manager.search("query")

    def test_search_relevant_not_init(self, manager):
        manager.theme_finder = None
        with pytest.raises(RuntimeError, match="Поиск не инициализирован"):
            manager.search_relevant("query")

    def test_filter_results_logic(self, manager):
        raw = {
            "documents": [["Good", "Far"]],
            "distances": [[0.1, 0.9]],
            "metadatas": [[{"id": 1}, {"id": 2}]],
        }
        res = manager.filter_results_by_distance(raw, max_distance=0.5)
        assert len(res["documents"][0]) == 1
        assert res["documents"][0][0] == "Good"

    def test_sort_date_branches(self, manager):
        raw = {
            "documents": [["D1", "D2"]],
            "distances": [[0.1, 0.1]],
            "metadatas": [
                [
                    {"rounded_final_grade": 10, "date_defence": "27.05.2025"},
                    {"rounded_final_grade": 4, "date_defence": "01.01.2021"},
                ]
            ],
        }
        res = manager.sort_results(raw, date_priority=1)
        assert res["documents"][0][0] == "D1"

    def test_search_success(self, manager):
        manager.theme_finder = MagicMock()
        manager.search("test")
        assert manager.theme_finder.search.called

    def test_search_relevant_success(self, manager):
        manager.theme_finder = MagicMock()
        manager.theme_finder.search.return_value = {
            "documents": [["A"]],
            "distances": [[0.1]],
            "metadatas": [[{}]],
        }
        manager.search_relevant("test")
        assert manager.theme_finder.search.called

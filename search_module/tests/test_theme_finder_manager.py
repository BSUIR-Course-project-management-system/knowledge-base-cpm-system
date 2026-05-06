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

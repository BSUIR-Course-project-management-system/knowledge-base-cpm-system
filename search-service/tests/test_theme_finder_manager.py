from unittest.mock import MagicMock, patch

import pytest

from app.search_module.src.theme_finder_manager import ThemeFinderManager
from tests.conftest import make_chroma_result, make_topic


@pytest.fixture
def manager() -> ThemeFinderManager:
    return ThemeFinderManager()


class TestSearchRelevant:

    def test_raises_when_search_engine_not_initialized(self, manager):
        # theme_finder is None — как assertThrows(RuntimeException.class, ...)
        with pytest.raises(RuntimeError, match="not initialized"):
            manager.search_relevant("любой запрос")

    def test_applies_full_pipeline_to_results(self, manager):
        mock_finder = MagicMock()
        mock_finder.search.return_value = make_chroma_result(
            documents=["Тема про Python", "Тема про Python", "Чужая тема"],
            distances=[0.2, 0.6, 0.85],
            metadatas=[
                {"original_id": "1", "field_type": "topic"},
                {"original_id": "1", "field_type": "technologies"},
                {"original_id": "2", "field_type": "topic"},
            ],
        )
        manager.theme_finder = mock_finder
        result = manager.search_relevant("python", n_results=5, max_distance=0.9)

        mock_finder.search.assert_called_once_with(
            "python", n_results=5, is_used=None, examiner=None
        )
        assert len(result["documents"][0]) == 2
        assert result["metadatas"][0][0]["original_id"] == "1"
        assert result["distances"][0][0] == pytest.approx(0.2)

    def test_pipeline_drops_results_beyond_max_distance(self, manager):
        mock_finder = MagicMock()
        mock_finder.search.return_value = make_chroma_result(
            documents=["Далёкая тема"],
            distances=[0.99],
            metadatas=[{"original_id": "1"}],
        )
        manager.theme_finder = mock_finder
        result = manager.search_relevant("запрос", max_distance=0.5)

        assert result["documents"][0] == []


class TestFilterResultsByDistance:

    def test_removes_topics_above_threshold(self, manager):
        results = make_chroma_result(
            documents=["Близкая", "Далёкая"],
            distances=[0.3, 0.9],
            metadatas=[{"original_id": "1"}, {"original_id": "2"}],
        )

        filtered = manager.filter_results_by_distance(results, max_distance=0.5)

        assert filtered["documents"][0] == ["Близкая"]
        assert filtered["distances"][0] == [0.3]
        assert filtered["metadatas"][0] == [{"original_id": "1"}]

    def test_keeps_topic_exactly_at_threshold(self, manager):
        results = make_chroma_result(
            documents=["На границе"], distances=[0.5], metadatas=[{"id": "1"}]
        )

        filtered = manager.filter_results_by_distance(results, max_distance=0.5)

        assert filtered["documents"][0] == ["На границе"]

    def test_keeps_all_when_threshold_generous(self, manager):
        results = make_chroma_result(
            documents=["A", "B"], distances=[0.1, 0.2],
            metadatas=[{"id": "1"}, {"id": "2"}],
        )

        filtered = manager.filter_results_by_distance(results, max_distance=1.0)

        assert len(filtered["documents"][0]) == 2


class TestDeduplicateByOriginalId:

    def test_keeps_closest_match_per_topic(self, manager):
        results = make_chroma_result(
            documents=["Тема про Python", "Тема про Python"],
            distances=[0.2, 0.6],
            metadatas=[{"original_id": "1"}, {"original_id": "1"}],
        )
        deduped = manager._deduplicate_by_original_id(results)

        assert len(deduped["documents"][0]) == 1
        assert deduped["distances"][0] == [0.2]

    def test_keeps_different_topics_separately(self, manager):
        results = make_chroma_result(
            documents=["Тема A", "Тема B"],
            distances=[0.4, 0.3],
            metadatas=[{"original_id": "1"}, {"original_id": "2"}],
        )

        deduped = manager._deduplicate_by_original_id(results)

        assert len(deduped["documents"][0]) == 2

    def test_orders_results_by_distance(self, manager):
        results = make_chroma_result(
            documents=["Вторая", "Первая", "Третья"],
            distances=[0.5, 0.1, 0.9],
            metadatas=[{"original_id": "2"}, {"original_id": "1"},
                       {"original_id": "3"}],
        )
        deduped = manager._deduplicate_by_original_id(results)

        assert deduped["distances"][0] == [0.1, 0.5, 0.9]
        assert deduped["documents"][0] == ["Первая", "Вторая", "Третья"]


class TestSortResults:

    def test_relevance_keeps_original_order(self, manager):
        results = make_chroma_result(
            documents=["B", "A"], distances=[0.1, 0.2],
            metadatas=[{"id": "1"}, {"id": "2"}],
        )
        sorted_res = manager._sort_results(results, sort_by="relevance")

        assert sorted_res["documents"][0] == ["B", "A"]

    def test_none_keeps_original_order(self, manager):
        results = make_chroma_result(
            documents=["B", "A"], distances=[0.1, 0.2],
            metadatas=[{"id": "1"}, {"id": "2"}],
        )
        sorted_res = manager._sort_results(results, sort_by=None)
        assert sorted_res["documents"][0] == ["B", "A"]

    def test_grade_highest_first(self, manager):
        results = make_chroma_result(
            documents=["Оценка 5", "Оценка 9", "Без оценки"],
            distances=[0.1, 0.2, 0.3],
            metadatas=[
                {"original_id": "1", "rounded_final_grade": 5},
                {"original_id": "2", "rounded_final_grade": 9},
                {"original_id": "3", "rounded_final_grade": ""},
            ],
        )
        sorted_res = manager._sort_results(results, sort_by="grade")
        assert sorted_res["documents"][0] == ["Оценка 9", "Оценка 5", "Без оценки"]

    def test_grade_invalid_value_treated_as_zero(self, manager):
        results = make_chroma_result(
            documents=["Не сдано", "Оценка 5"],
            distances=[0.1, 0.2],
            metadatas=[
                {"original_id": "1", "rounded_final_grade": "не сдано"},
                {"original_id": "2", "rounded_final_grade": 5},
            ],
        )

        sorted_res = manager._sort_results(results, sort_by="grade")
        assert sorted_res["documents"][0] == ["Оценка 5", "Не сдано"]

    def test_date_latest_first(self, manager):
        results = make_chroma_result(
            documents=["Защита 2024", "Защита 2025", "Защита 2023"],
            distances=[0.1, 0.2, 0.3],
            metadatas=[
                {"original_id": "1", "date_defence": "2024-06-01"},
                {"original_id": "2", "date_defence": "2025-06-15"},
                {"original_id": "3", "date_defence": "2023-12-31"},
            ],
        )
        sorted_res = manager._sort_results(results, sort_by="date")
        assert sorted_res["documents"][0] == [
            "Защита 2025", "Защита 2024", "Защита 2023",
        ]


class TestProcessData:

    @patch("app.search_module.src.theme_finder_manager.ThemeFinder")
    @patch("app.search_module.src.theme_finder_manager.DataManager")
    def test_creates_data_manager_and_rebuilds_index(
            self, mock_dm_cls, mock_tf_cls
    ):
        mock_dm = MagicMock()
        mock_dm_cls.return_value = mock_dm
        topics = [make_topic("1")]
        mgr = ThemeFinderManager()
        mgr.process_data(topics)

        mock_dm.set_data.assert_called_once_with(topics)
        mock_tf_cls.assert_called_once_with(mock_dm)
        mock_tf_cls.return_value.make_collection.assert_called_once()
        assert mgr.theme_finder is mock_tf_cls.return_value

    def test_prepare_search_raises_when_no_data_manager(self, manager):
        manager.data_manager = None

        with pytest.raises(RuntimeError, match="empty"):
            manager.prepare_search()

    def test_prepare_search_raises_when_data_empty(self, manager):
        mock_dm = MagicMock()
        mock_dm.data = []
        manager.data_manager = mock_dm

        with pytest.raises(RuntimeError, match="empty"):
            manager.prepare_search()


class TestInitFromDb:

    @patch("app.search_module.src.theme_finder_manager.ThemeFinder")
    @patch("app.search_module.src.theme_finder_manager.DataManager")
    def test_restores_search_from_existing_vectors(
            self, mock_dm_cls, mock_tf_cls
    ):
        mock_dm = MagicMock()
        mock_dm.collection.count.return_value = 42
        mock_dm_cls.return_value = mock_dm

        mgr = ThemeFinderManager()
        mgr.init_from_db()

        assert mgr.data_manager is mock_dm
        mock_dm.load_from_collection.assert_called_once()
        mock_tf_cls.assert_called_once_with(mock_dm)
        assert mgr.theme_finder is mock_tf_cls.return_value

    @patch("app.search_module.src.theme_finder_manager.ThemeFinder")
    @patch("app.search_module.src.theme_finder_manager.DataManager")
    def test_skips_init_when_collection_empty(self, mock_dm_cls, mock_tf_cls):
        mock_dm = MagicMock()
        mock_dm.collection.count.return_value = 0
        mock_dm_cls.return_value = mock_dm

        mgr = ThemeFinderManager()
        mgr.init_from_db()

        assert mgr.theme_finder is None
        mock_tf_cls.assert_not_called()

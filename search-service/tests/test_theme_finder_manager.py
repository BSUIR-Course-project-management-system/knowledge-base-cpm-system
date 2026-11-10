from unittest.mock import MagicMock, patch

import pytest

from app.search_module.src.theme_finder_manager import ThemeFinderManager


@pytest.fixture
def manager():
    return ThemeFinderManager(loader=MagicMock(), saver=MagicMock())


def test_init_defaults_none(manager):
    assert manager.data_manager is None
    assert manager.theme_finder is None


def test_process_data_from_json_creates_data_manager(manager):
    with patch(
        "app.search_module.src.theme_finder_manager.DataManager"
    ) as dm_cls, patch.object(manager, "prepare_search") as prep:
        manager.process_data_from_json('[{"id": 1}]', "/tmp/x.json")

        manager.saver.save.assert_called_once_with("/tmp/x.json", '[{"id": 1}]')
        dm_cls.assert_called_once_with(manager.loader)
        manager.data_manager.load.assert_called_once_with("/tmp/x.json")
        prep.assert_called_once()


def test_process_data_from_json_reuses_existing_data_manager(manager):
    existing = MagicMock()
    manager.data_manager = existing

    with patch(
        "app.search_module.src.theme_finder_manager.DataManager"
    ) as dm_cls, patch.object(manager, "prepare_search"):
        manager.process_data_from_json("[]", "/tmp/x.json")

        dm_cls.assert_not_called()
        existing.load.assert_called_once_with("/tmp/x.json")


def test_prepare_search_requires_data_manager(manager):
    with pytest.raises(RuntimeError):
        manager.prepare_search()


def test_prepare_search_success(manager):
    manager.data_manager = MagicMock()

    with patch("app.search_module.src.theme_finder_manager.ThemeFinder") as tf_cls:
        finder = tf_cls.return_value

        manager.prepare_search()

        tf_cls.assert_called_once_with(manager.data_manager)
        finder.make_collection.assert_called_once()
        assert manager.theme_finder is finder


def test_prepare_search_wraps_errors(manager):
    manager.data_manager = MagicMock()

    with patch("app.search_module.src.theme_finder_manager.ThemeFinder") as tf_cls:
        tf_cls.side_effect = Exception("boom")
        with pytest.raises(RuntimeError, match="boom"):
            manager.prepare_search()


def test_search_requires_finder(manager):
    with pytest.raises(RuntimeError):
        manager.search("q")


def test_search_delegates_to_finder(manager):
    manager.theme_finder = MagicMock()
    manager.theme_finder.search.return_value = {"ok": True}

    result = manager.search("q", n_results=3)

    manager.theme_finder.search.assert_called_once_with("q", n_results=3)
    assert result == {"ok": True}


def test_filter_results_by_distance(manager):
    results = {
        "documents": [["a", "b", "c"]],
        "distances": [[0.1, 0.5, 0.9]],
        "metadatas": [[{"i": 1}, {"i": 2}, {"i": 3}]],
    }

    out = manager.filter_results_by_distance(results, max_distance=0.6)

    assert out["documents"][0] == ["a", "b"]
    assert out["distances"][0] == [0.1, 0.5]
    assert out["metadatas"][0] == [{"i": 1}, {"i": 2}]


def test_deduplicate_keeps_closest(manager):
    results = {
        "documents": [["a", "b", "c"]],
        "distances": [[0.4, 0.2, 0.9]],
        "metadatas": [
            [{"original_id": "1"}, {"original_id": "1"}, {"original_id": "2"}]
        ],
    }

    out = manager._deduplicate_by_original_id(results)

    assert out["documents"][0] == ["b", "c"]
    assert out["distances"][0] == [0.2, 0.9]


def test_deduplicate_sorts_by_distance(manager):
    results = {
        "documents": [["a", "b"]],
        "distances": [[0.8, 0.1]],
        "metadatas": [[{"original_id": "1"}, {"original_id": "2"}]],
    }

    out = manager._deduplicate_by_original_id(results)

    assert out["documents"][0] == ["b", "a"]


def test_sort_relevance_is_noop(manager):
    results = {
        "documents": [["a", "b"]],
        "distances": [[0.1, 0.2]],
        "metadatas": [[{}, {}]],
    }

    assert manager._sort_results(results, "relevance") is results


def test_sort_by_grade(manager):
    results = {
        "documents": [["a", "b", "c"]],
        "distances": [[0.1, 0.2, 0.3]],
        "metadatas": [
            [
                {"rounded_final_grade": "3"},
                {"rounded_final_grade": "5"},
                {"rounded_final_grade": "4"},
            ]
        ],
    }

    out = manager._sort_results(results, "grade")

    assert out["documents"][0] == ["b", "c", "a"]


def test_sort_by_grade_handles_invalid_values(manager):
    results = {
        "documents": [["a", "b", "c"]],
        "distances": [[0.1, 0.2, 0.3]],
        "metadatas": [
            [
                {"rounded_final_grade": "invalid"},
                {"rounded_final_grade": "5"},
                {"rounded_final_grade": "3"},
            ]
        ],
    }

    out = manager._sort_results(results, "grade")

    assert out["documents"][0] == ["b", "c", "a"]


def test_sort_by_date(manager):
    results = {
        "documents": [["a", "b", "c"]],
        "distances": [[0.1, 0.2, 0.3]],
        "metadatas": [
            [
                {"date_defence": "2024-01-01"},
                {"date_defence": "2025-01-01"},
                {"date_defence": "2023-01-01"},
            ]
        ],
    }

    out = manager._sort_results(results, "date")

    assert out["documents"][0] == ["b", "a", "c"]


def test_search_relevant_full_pipeline(manager):
    manager.theme_finder = MagicMock()
    manager.theme_finder.search.return_value = {
        "documents": [["d1", "d2", "d3"]],
        "distances": [[0.2, 0.1, 0.9]],
        "metadatas": [
            [
                {"original_id": "a"},
                {"original_id": "b"},
                {"original_id": "c"},
            ]
        ],
    }

    out = manager.search_relevant(
        query="q", n_results=3, max_distance=0.5, sort_by="relevance"
    )

    assert out["documents"][0] == ["d2", "d1"]
    manager.theme_finder.search.assert_called_once_with(
        "q", n_results=3, is_used=False, examiner=None
    )


def test_search_relevant_requires_finder(manager):
    with pytest.raises(RuntimeError):
        manager.search_relevant("q")
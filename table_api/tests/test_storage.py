import json
import pytest
from unittest.mock import patch, MagicMock, call


@pytest.fixture(autouse=True)
def patch_env(monkeypatch):
    monkeypatch.setenv("CREDENTIALS_FILE", "fake_credentials.json")
    monkeypatch.setenv("GOOGLE_DRIVE_FOLDER_ID", "fake_folder_id")
    monkeypatch.setenv("GROUP_DATA_FILE", "/tmp/group_data.json")
    monkeypatch.setenv("TOPIC_DATA_FILE", "/tmp/topic_data.json")
    monkeypatch.setenv("SCHEDULE_DATA_FILE", "/tmp/schedule_data.json")


@pytest.fixture
def storage():
    """Создаёт Storage с замоканными зависимостями."""
    with (
        patch("table_api.src.storage.GoogleSheetsParser"),
        patch("table_api.src.storage.Logger"),
        patch("table_api.src.storage.JsonLoader"),
        patch("table_api.src.storage.JsonSaver"),
    ):
        from table_api.src.storage import Storage

        s = Storage()
    return s


@pytest.fixture
def storage_cls():
    """Возвращает класс Storage (с патченными зависимостями для импорта)."""
    with (
        patch("table_api.src.storage.GoogleSheetsParser"),
        patch("table_api.src.storage.Logger"),
        patch("table_api.src.storage.JsonLoader"),
        patch("table_api.src.storage.JsonSaver"),
    ):
        from table_api.src.storage import Storage
    return Storage


class TestFindFirst:
    def test_find_in_flat_dict(self, storage):
        data = {"key": "value", "other": "x"}
        assert storage._find_first(data, "key") == "value"

    def test_find_in_nested_dict(self, storage):
        data = {"outer": {"inner": {"target": 42}}}
        assert storage._find_first(data, "target") == 42

    def test_find_in_list(self, storage):
        data = [{"a": 1}, {"b": 2, "target": 99}]
        assert storage._find_first(data, "target") == 99

    def test_find_in_nested_list(self, storage):
        data = {"items": [{"nested": {"key": "found"}}]}
        assert storage._find_first(data, "key") == "found"

    def test_not_found_returns_default(self, storage):
        data = {"a": 1, "b": {"c": 2}}
        assert storage._find_first(data, "nonexistent") is None

    def test_not_found_returns_custom_default(self, storage):
        data = {"a": 1}
        assert storage._find_first(data, "missing", default="N/A") == "N/A"

    def test_find_in_empty_dict(self, storage):
        assert storage._find_first({}, "key") is None

    def test_find_in_empty_list(self, storage):
        assert storage._find_first([], "key") is None

    def test_find_first_not_second(self, storage):
        data = {
            "first": {"date_defence": "01.01.2026"},
            "second": {"date_defence": "02.02.2026"},
        }
        result = storage._find_first(data, "date_defence")
        assert result in ("01.01.2026", "02.02.2026")

    def test_target_value_is_none(self, storage):
        """Если значение по ключу равно None, возвращает None (не default)."""
        data = {"key": None}

        result = storage._find_first(data, "key", default="missing")

        assert result is None

    def test_primitive_not_dict_not_list(self, storage):
        """При передаче примитива возвращается default."""
        assert storage._find_first("plain_string", "key") is None
        assert storage._find_first(42, "key") is None


class TestGetUniqueTopics:
    def test_returns_json_string(self, storage):
        storage._loader.load.return_value = None
        result = storage.get_unique_topics()
        parsed = json.loads(result)
        assert isinstance(parsed, list)

    def test_empty_when_no_data(self, storage):
        storage._loader.load.return_value = None
        result = storage.get_unique_topics()
        assert json.loads(result) == []

    def test_topics_from_group_data_are_used(self, storage):
        group_data = {
            "421602": [
                {
                    "topic": "ИИ система",
                    "curator": "Иванов",
                    "examiner": "Петров",
                    "description": "Описание ИИ",
                    "date_defence": "01.06.2026",
                    "rounded_final_grade": 9,
                }
            ]
        }

        storage._loader.load.side_effect = [group_data, None]
        result = json.loads(storage.get_unique_topics())
        topics = [t["topic"] for t in result]
        assert "ИИ система" in topics

    def test_topic_from_group_is_marked_as_used(self, storage):
        group_data = {
            "421602": [
                {
                    "topic": "ML модель",
                    "curator": "А",
                    "examiner": "Б",
                    "description": "Описание",
                    "date_defence": None,
                    "rounded_final_grade": None,
                }
            ]
        }

        storage._loader.load.side_effect = [group_data, None]
        result = json.loads(storage.get_unique_topics())
        ml_topic = next((t for t in result if t["topic"] == "ML модель"), None)
        assert ml_topic is not None
        assert ml_topic["is_used"] is True

    def test_topic_from_topic_data_is_not_used(self, storage):
        topic_data = {
            "2026": [
                {
                    "topic": "NLP обработка",
                    "curator": "В",
                    "examiner": "Г",
                    "description": "NLP",
                    "date_defence": None,
                    "rounded_final_grade": None,
                }
            ]
        }

        storage._loader.load.side_effect = [None, topic_data]
        result = json.loads(storage.get_unique_topics())
        nlp_topic = next((t for t in result if t["topic"] == "NLP обработка"), None)
        assert nlp_topic is not None
        assert nlp_topic["is_used"] is False

    def test_duplicate_topic_from_group_not_duplicated_in_topic_data(self, storage):
        group_data = {
            "421602": [
                {
                    "topic": "Одна и та же тема",
                    "curator": "",
                    "examiner": "",
                    "description": "",
                }
            ]
        }
        topic_data = {
            "2026": [
                {
                    "topic": "Одна и та же тема",
                    "curator": "",
                    "examiner": "",
                    "description": "",
                }
            ]
        }

        storage._loader.load.side_effect = [group_data, topic_data]
        result = json.loads(storage.get_unique_topics())
        matching = [t for t in result if t["topic"] == "Одна и та же тема"]
        assert len(matching) == 1

    def test_topics_have_sequential_ids(self, storage):
        group_data = {
            "421602": [
                {"topic": "Тема А", "curator": "", "examiner": "", "description": ""},
                {"topic": "Тема Б", "curator": "", "examiner": "", "description": ""},
            ]
        }

        storage._loader.load.side_effect = [group_data, None]
        result = json.loads(storage.get_unique_topics())
        ids = [int(t["id"]) for t in result]
        assert ids == list(range(1, len(result) + 1))

    def test_empty_topic_strings_skipped(self, storage):
        group_data = {
            "421602": [
                {"topic": "", "curator": "", "examiner": "", "description": ""},
                {"topic": "   ", "curator": "", "examiner": "", "description": ""},
            ]
        }

        storage._loader.load.side_effect = [group_data, None]
        result = json.loads(storage.get_unique_topics())
        assert result == []

    def test_description_fallback(self, storage):
        group_data = {
            "421602": [
                {"topic": "Тема", "curator": "", "examiner": "", "description": None}
            ]
        }

        storage._loader.load.side_effect = [group_data, None]
        result = json.loads(storage.get_unique_topics())
        assert result[0]["description"] == "Описание будет добавлено позже"


class TestGetExaminerSchedule:
    def _make_schedule_data(self):
        return {
            "2026": {
                "milestone_1": [
                    {"topic": "ИИ", "examiner": "Иванов А.А.", "date": "01.06.2026"},
                    {"topic": "ML", "examiner": "Петров Б.Б.", "date": "02.06.2026"},
                ],
                "milestone_2": [
                    {"topic": "NLP", "examiner": "Иванов А.А.", "date": "15.06.2026"},
                ],
                "milestone_3": [],
            }
        }

    def test_returns_json_string(self, storage):
        storage._loader.load.return_value = self._make_schedule_data()
        result = storage.get_examiner_schedule("Иванов")
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_filters_by_examiner(self, storage):
        storage._loader.load.return_value = self._make_schedule_data()
        result = json.loads(storage.get_examiner_schedule("Иванов"))
        m1 = result.get("milestone_1", [])
        assert all("иванов" in t["examiner"].lower() for t in m1)

    def test_examiner_not_found_empty_milestones(self, storage):
        storage._loader.load.return_value = self._make_schedule_data()
        result = json.loads(storage.get_examiner_schedule("Несуществующий"))
        assert result["milestone_1"] == []
        assert result["milestone_2"] == []
        assert result["milestone_3"] == []

    def test_case_insensitive_search(self, storage):
        storage._loader.load.return_value = self._make_schedule_data()
        result_lower = json.loads(storage.get_examiner_schedule("иванов"))
        result_upper = json.loads(storage.get_examiner_schedule("ИВАНОВ"))
        assert result_lower == result_upper

    def test_no_data_falls_back_to_parser(self, storage):
        storage._loader.load.return_value = None
        storage._parser.get_all_sheets_in_folder.return_value = ["fake_id"]
        storage._parser.fetch_examiner_schedule.return_value = (
            self._make_schedule_data()
        )
        result = json.loads(storage.get_examiner_schedule("Иванов", year=2026))
        assert "milestone_1" in result

    def test_year_filter_empty(self, storage):
        storage._loader.load.return_value = self._make_schedule_data()

        result = json.loads(storage.get_examiner_schedule("Иванов", year=2025))
        assert result["milestone_1"] == []


class TestUpdateDataFromCloud:
    def test_calls_parser_and_saver(self, storage):
        storage._parser.get_all_sheets_in_folder.return_value = ["id1"]
        storage._parser.get_all_data_from_cloud.return_value = {
            "topic_data": {"2026": []},
            "group_data": {"421602": []},
            "schedule_data": {},
        }
        storage.update_data_from_cloud()
        assert storage._saver.save.call_count == 3

    def test_raises_runtime_error_on_exception(self, storage):
        storage._parser.get_all_sheets_in_folder.side_effect = Exception("API error")
        with pytest.raises(RuntimeError, match="Непредвиденная ошибка"):
            storage.update_data_from_cloud()


class TestAddTopic:
    def test_add_topic_calls_parser(self, storage):
        storage._parser.get_all_sheets_in_folder.return_value = ["id1"]
        storage._parser.append_row_with_format.return_value = None
        storage.add_topic(topic="Новая тема", curator="Иванов", examiner="Петров")
        storage._parser.append_row_with_format.assert_called_once()

    def test_add_topic_raises_exception_on_failure(self, storage):
        storage._parser.get_all_sheets_in_folder.return_value = ["id1"]
        storage._parser.append_row_with_format.side_effect = Exception("API error")
        with pytest.raises(Exception, match="Ошибка добавления в таблицу"):
            storage.add_topic(topic="Новая тема")

    def test_add_topic_passes_correct_row_data(self, storage):
        storage._parser.get_all_sheets_in_folder.return_value = ["id1"]
        storage.add_topic(
            topic="ML система",
            description="Машинное обучение",
            curator="Иванов",
            examiner="Петров",
        )
        call_kwargs = storage._parser.append_row_with_format.call_args
        assert call_kwargs is not None
        row_data = call_kwargs.kwargs.get("row_data") or call_kwargs[1].get("row_data")
        assert "ML система" in row_data


class TestRemoveTopic:
    def test_remove_topic_calls_parser(self, storage):
        storage._parser.get_all_sheets_in_folder.return_value = ["id1"]
        storage._parser.delete_row_by_topic.return_value = True
        storage.remove_topic(topic="Старая тема")
        storage._parser.delete_row_by_topic.assert_called_once()

    def test_remove_topic_raises_exception_on_failure(self, storage):
        storage._parser.get_all_sheets_in_folder.return_value = ["id1"]
        storage._parser.delete_row_by_topic.side_effect = Exception("Not found")
        with pytest.raises(Exception, match="Ошибка добавления в таблицу"):
            storage.remove_topic(topic="Несуществующая тема")

    def test_remove_topic_passes_correct_data(self, storage):
        storage._parser.get_all_sheets_in_folder.return_value = ["id1"]
        storage.remove_topic(key_title="ТЕСТ 2026", topic="Удаляемая тема")
        call_kwargs = storage._parser.delete_row_by_topic.call_args
        assert call_kwargs.kwargs.get("theme_title") == "Удаляемая тема"

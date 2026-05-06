import json
import pytest
from unittest.mock import patch, MagicMock
from table_api.src.saver import ISaver, JsonSaver


class TestISaver:
    """Тесты для абстрактного класса ISaver."""

    def test_isaver_is_abstract(self):
        """ISaver нельзя создать напрямую."""
        with pytest.raises(TypeError):
            ISaver()

    def test_isaver_requires_save_method(self):
        """Конкретный класс должен реализовать метод save."""

        class IncompleteSaver(ISaver):
            pass

        with pytest.raises(TypeError):
            IncompleteSaver()

    def test_isaver_concrete_subclass_works(self):
        """Конкретный класс с реализованным save работает."""

        class ConcreteSaver(ISaver):
            def save(self, file_path: str, data: dict) -> dict:
                return None

        saver = ConcreteSaver()
        assert saver.save("path", {}) is None


class TestJsonSaver:
    """Тесты для класса JsonSaver."""

    @patch("table_api.src.saver.Logger")
    def test_init_defaults(self, mock_logger_cls):
        """JsonSaver инициализируется с параметрами по умолчанию."""
        saver = JsonSaver()
        assert saver._encoding == "utf-8"
        assert saver._indent == 2
        assert saver._ensure_ascii is False

    @patch("table_api.src.saver.Logger")
    def test_init_custom_params(self, mock_logger_cls):
        """JsonSaver принимает пользовательские параметры."""
        saver = JsonSaver(encoding="cp1251", indent=4, ensure_ascii=True)
        assert saver._encoding == "cp1251"
        assert saver._indent == 4
        assert saver._ensure_ascii is True

    @patch("table_api.src.saver.Logger")
    def test_save_dict_to_file(self, mock_logger_cls, tmp_path):
        """Сохранение словаря в JSON файл."""
        data = {"key": "value", "number": 42}
        json_file = tmp_path / "output.json"

        saver = JsonSaver()
        saver.save(str(json_file), data)

        with open(json_file, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded == data

    @patch("table_api.src.saver.Logger")
    def test_save_list_to_file(self, mock_logger_cls, tmp_path):
        """Сохранение списка в JSON файл."""
        data = [{"id": 1, "topic": "AI"}, {"id": 2, "topic": "ML"}]
        json_file = tmp_path / "list_output.json"

        saver = JsonSaver()
        saver.save(str(json_file), data)

        with open(json_file, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded == data

    @patch("table_api.src.saver.Logger")
    def test_save_with_cyrillic_ensure_ascii_false(self, mock_logger_cls, tmp_path):
        """Кириллица сохраняется без escape при ensure_ascii=False."""
        data = {"тема": "Разработка ИИ системы"}
        json_file = tmp_path / "cyrillic.json"

        saver = JsonSaver(ensure_ascii=False)
        saver.save(str(json_file), data)

        content = json_file.read_text(encoding="utf-8")
        assert "Разработка ИИ системы" in content

    @patch("table_api.src.saver.Logger")
    def test_save_with_indent(self, mock_logger_cls, tmp_path):
        """Файл сохраняется с указанным отступом."""
        data = {"key": "value"}
        json_file = tmp_path / "indented.json"

        saver = JsonSaver(indent=4)
        saver.save(str(json_file), data)

        content = json_file.read_text(encoding="utf-8")
        assert "    " in content  # 4 пробела

    @patch("table_api.src.saver.Logger")
    def test_save_file_not_found_returns_none(self, mock_logger_cls):
        """При несуществующем пути возвращает None (не падает)."""
        saver = JsonSaver()
        result = saver.save("/nonexistent/path/deep/output.json", {"key": "val"})
        assert result is None

    @patch("table_api.src.saver.Logger")
    def test_save_file_not_found_logs_error(self, mock_logger_cls):
        """При несуществующем пути вызывается логирование ошибки."""
        mock_logger = MagicMock()
        mock_logger_cls.return_value = mock_logger

        saver = JsonSaver()
        saver.save("/nonexistent/path/file.json", {})
        mock_logger.error.assert_called_once_with("Файл для сохранения не найден")

    @patch("table_api.src.saver.Logger")
    def test_save_empty_dict(self, mock_logger_cls, tmp_path):
        """Сохранение пустого словаря."""
        json_file = tmp_path / "empty.json"
        saver = JsonSaver()
        saver.save(str(json_file), {})

        with open(json_file, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded == {}

    @patch("table_api.src.saver.Logger")
    def test_save_nested_structure(self, mock_logger_cls, tmp_path):
        """Сохранение вложенной структуры данных."""
        data = {
            "group_data": {"421602": [{"topic": "ИИ", "curator": "Иванов"}]},
            "topic_data": {"2026": [{"topic": "ML"}]},
        }
        json_file = tmp_path / "nested.json"
        saver = JsonSaver()
        saver.save(str(json_file), data)

        with open(json_file, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded["group_data"]["421602"][0]["topic"] == "ИИ"

    @patch("table_api.src.saver.Logger")
    def test_save_logs_info_on_success(self, mock_logger_cls, tmp_path):
        """При успешном сохранении вызывается info лог."""
        mock_logger = MagicMock()
        mock_logger_cls.return_value = mock_logger

        json_file = tmp_path / "log_test.json"
        saver = JsonSaver()
        saver.save(str(json_file), {"x": 1})

        assert mock_logger.info.call_count >= 1

import json
import pytest
from unittest.mock import patch, MagicMock, mock_open
from table_api.src.loader import ILoader, JsonLoader


class TestILoader:
    """Тесты для абстрактного класса ILoader."""

    def test_iloader_is_abstract(self):
        """ILoader нельзя создать напрямую."""
        with pytest.raises(TypeError):
            ILoader()

    def test_iloader_requires_load_method(self):
        """Конкретный класс должен реализовать метод load."""

        class IncompleteLoader(ILoader):
            pass

        with pytest.raises(TypeError):
            IncompleteLoader()

    def test_iloader_concrete_subclass_works(self):
        """Конкретный класс с реализованным load работает."""

        class ConcreteLoader(ILoader):
            def load(self, file_path: str) -> dict:
                return {"key": "value"}

        loader = ConcreteLoader()
        assert loader.load("any_path") == {"key": "value"}


class TestJsonLoader:
    """Тесты для класса JsonLoader."""

    @patch("table_api.src.loader.Logger")
    def test_init_default_encoding(self, mock_logger_cls):
        """JsonLoader инициализируется с кодировкой utf-8 по умолчанию."""
        loader = JsonLoader()
        assert loader._encoding == "utf-8"

    @patch("table_api.src.loader.Logger")
    def test_init_custom_encoding(self, mock_logger_cls):
        """JsonLoader принимает произвольную кодировку."""
        loader = JsonLoader(encoding="cp1251")
        assert loader._encoding == "cp1251"

    @patch("table_api.src.loader.Logger")
    def test_load_valid_json_dict(self, mock_logger_cls, tmp_path):
        """Успешная загрузка словаря из JSON файла."""
        data = {"key": "value", "number": 42}
        json_file = tmp_path / "data.json"
        json_file.write_text(json.dumps(data), encoding="utf-8")

        loader = JsonLoader()
        result = loader.load(str(json_file))
        assert result == data

    @patch("table_api.src.loader.Logger")
    def test_load_valid_json_list(self, mock_logger_cls, tmp_path):
        """Успешная загрузка списка из JSON файла."""
        data = [{"id": 1, "topic": "ML"}, {"id": 2, "topic": "NLP"}]
        json_file = tmp_path / "list_data.json"
        json_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        loader = JsonLoader()
        result = loader.load(str(json_file))
        assert result == data
        assert len(result) == 2

    @patch("table_api.src.loader.Logger")
    def test_load_file_not_found_returns_none(self, mock_logger_cls):
        """При отсутствии файла возвращает None."""
        loader = JsonLoader()
        result = loader.load("/nonexistent/path/file.json")
        assert result is None

    @patch("table_api.src.loader.Logger")
    def test_load_file_not_found_logs_error(self, mock_logger_cls):
        """При отсутствии файла вызывается логирование ошибки."""
        mock_logger = MagicMock()
        mock_logger_cls.return_value = mock_logger

        loader = JsonLoader()
        loader.load("/nonexistent/path/file.json")
        mock_logger.error.assert_called_once_with("Файл для загрузки не найден")

    @patch("table_api.src.loader.Logger")
    def test_load_nested_structure(self, mock_logger_cls, tmp_path):
        """Загрузка вложенной JSON структуры."""
        data = {
            "group_data": {"421602": [{"topic": "ИИ", "curator": "Иванов"}]},
            "topic_data": {"2026": [{"topic": "ML"}]},
        }
        json_file = tmp_path / "nested.json"
        json_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        loader = JsonLoader()
        result = loader.load(str(json_file))
        assert result["group_data"]["421602"][0]["topic"] == "ИИ"

    @patch("table_api.src.loader.Logger")
    def test_load_empty_dict(self, mock_logger_cls, tmp_path):
        """Загрузка пустого JSON словаря."""
        json_file = tmp_path / "empty.json"
        json_file.write_text("{}", encoding="utf-8")

        loader = JsonLoader()
        result = loader.load(str(json_file))
        assert result == {}

    @patch("table_api.src.loader.Logger")
    def test_load_cyrillic_content(self, mock_logger_cls, tmp_path):
        """Загрузка файла с кириллицей."""
        data = {"тема": "Разработка ИИ системы", "куратор": "Иванов А.А."}
        json_file = tmp_path / "cyrillic.json"
        json_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        loader = JsonLoader()
        result = loader.load(str(json_file))
        assert result["тема"] == "Разработка ИИ системы"

    @patch("table_api.src.loader.Logger")
    def test_load_with_custom_encoding_writes_and_reads(
        self, mock_logger_cls, tmp_path
    ):
        """JsonLoader с нестандартной кодировкой корректно читает файл."""
        data = {"key": "value"}
        json_file = tmp_path / "data_cp1251.json"
        json_file.write_text(json.dumps(data), encoding="utf-8")

        loader = JsonLoader(encoding="utf-8")
        result = loader.load(str(json_file))
        assert result == data

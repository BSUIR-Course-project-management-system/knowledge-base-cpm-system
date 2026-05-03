import pytest
from unittest.mock import patch

from search_module.src.saver import JsonSaver
from search_module.src.settings import BASE_DIR


class TestJsonSaver:
    def test_saver(self):
        test_file = str(BASE_DIR / "tests" / "json_tests" / "test2.json")
        path_str = str(test_file)
        saver = JsonSaver()
        sample_data = '{"id": 123, "topic": "Тестирование ПО"}'
        saver.save(path_str, sample_data)

        with open(path_str, "r", encoding="utf-8") as f:
            content = f.read()

        assert content == sample_data
        
    def test_save_permission_denied(self):
        saver = JsonSaver()
        with patch("builtins.open", side_effect=PermissionError):
            with pytest.raises(PermissionError):
                saver.save("any_path.json", '{"data": 1}')
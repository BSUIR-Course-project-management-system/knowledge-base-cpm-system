import pytest
from search_module.src.loader import JsonLoader
from search_module.src.settings import BASE_DIR


class TestJsonLoader:
    def test_load(self):
        path = str(BASE_DIR / "tests" / "json_tests" / "test1.json")
        loader = JsonLoader()
        data = loader.load(path)
        assert data[0]["text"] == "Интеллектуальный помощник"
        assert len(data) == 3

    def test_load_file_not_found(self):
        loader = JsonLoader()
        path = "non_existent_file.json"
        
        with pytest.raises(FileNotFoundError):
            loader.load(path)

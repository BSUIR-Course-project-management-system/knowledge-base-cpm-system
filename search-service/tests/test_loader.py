import pytest

from app.search_module.src.loader import BaseLoader, JsonLoader


def test_base_loader_is_abstract():
    with pytest.raises(TypeError):
        BaseLoader()


def test_json_loader_loads_list(tmp_path):
    path = tmp_path / "data.json"
    path.write_text('[{"id": 1}, {"id": 2}]', encoding="utf-8")

    result = JsonLoader().load(str(path))

    assert result == [{"id": 1}, {"id": 2}]


def test_json_loader_preserves_unicode(tmp_path):
    path = tmp_path / "data.json"
    path.write_text('[{"тема": "привет"}]', encoding="utf-8")

    result = JsonLoader().load(str(path))

    assert result == [{"тема": "привет"}]


def test_json_loader_empty_list(tmp_path):
    path = tmp_path / "data.json"
    path.write_text("[]", encoding="utf-8")

    assert JsonLoader().load(str(path)) == []


def test_json_loader_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        JsonLoader().load(str(tmp_path / "no.json"))
import pytest

from app.search_module.src.saver import BaseSaver, JsonSaver


def test_base_saver_is_abstract():
    with pytest.raises(TypeError):
        BaseSaver()


def test_json_saver_writes(tmp_path):
    path = tmp_path / "out.json"

    JsonSaver().save(str(path), '{"a": 1}')

    assert path.read_text(encoding="utf-8") == '{"a": 1}'


def test_json_saver_overwrites(tmp_path):
    path = tmp_path / "out.json"
    path.write_text("old", encoding="utf-8")

    JsonSaver().save(str(path), "new")

    assert path.read_text(encoding="utf-8") == "new"


def test_json_saver_preserves_unicode(tmp_path):
    path = tmp_path / "out.json"

    JsonSaver().save(str(path), '{"a": "привет"}')

    assert path.read_text(encoding="utf-8") == '{"a": "привет"}'
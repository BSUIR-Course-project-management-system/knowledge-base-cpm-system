from unittest.mock import MagicMock, patch

import pytest

from app.search_module.src.theme_finder import ThemeFinder


@pytest.fixture
def st_and_torch():
    with patch(
        "app.search_module.src.theme_finder.SentenceTransformer"
    ) as st, patch("app.search_module.src.theme_finder.torch") as torch:
        torch.backends.mps.is_available.return_value = False
        torch.cuda.is_available.return_value = False
        yield st, torch


@pytest.fixture
def data_manager():
    dm = MagicMock()
    dm.data = []
    return dm


def test_init_chooses_cpu(st_and_torch, data_manager):
    st, _ = st_and_torch

    ThemeFinder(data_manager)

    st.assert_called_once()
    assert st.call_args.kwargs["device"] == "cpu"


def test_init_chooses_cuda(st_and_torch, data_manager):
    st, torch = st_and_torch
    torch.cuda.is_available.return_value = True

    ThemeFinder(data_manager)

    assert st.call_args.kwargs["device"] == "cuda"


def test_init_chooses_mps(st_and_torch, data_manager):
    st, torch = st_and_torch
    torch.backends.mps.is_available.return_value = True

    ThemeFinder(data_manager)

    assert st.call_args.kwargs["device"] == "mps"


def test_build_meta_cleans_keys_and_values(st_and_torch, data_manager):
    tf = ThemeFinder(data_manager)

    meta = tf._build_meta(
        {"id": 1, "key:": "val", "none": None, "lst": [1, 2]}, "topic"
    )

    assert meta["key"] == "val"
    assert meta["none"] == ""
    assert meta["lst"] == "[1, 2]"
    assert meta["field_type"] == "topic"
    assert meta["original_id"] == "1"


def test_build_meta_with_tech_item(st_and_torch, data_manager):
    tf = ThemeFinder(data_manager)

    meta = tf._build_meta({"id": 5}, "technologies", tech_item="python")

    assert meta["tech_item"] == "python"
    assert meta["field_type"] == "technologies"


def test_make_collection_empty_data_raises(st_and_torch, data_manager):
    data_manager.data = []
    tf = ThemeFinder(data_manager)

    with pytest.raises(RuntimeError):
        tf.make_collection()


def test_make_collection_adds_vectors(st_and_torch, data_manager):
    st, _ = st_and_torch
    model = st.return_value
    model.encode.return_value.tolist.return_value = [[0.1], [0.2], [0.3]]
    data_manager.data = [{"id": "1", "topic": "T1", "technologies": "py, sql"}]
    data_manager.collection.get.return_value = {"ids": []}

    tf = ThemeFinder(data_manager)
    tf.make_collection()

    model.encode.assert_called_once()
    assert model.encode.call_args.args[0] == ["T1", "py", "sql"]

    kwargs = data_manager.collection.add.call_args.kwargs
    assert kwargs["ids"] == ["1__topic", "1__tech__0", "1__tech__1"]
    assert kwargs["documents"] == ["T1", "T1", "T1"]


def test_make_collection_deletes_old_records(st_and_torch, data_manager):
    st, _ = st_and_torch
    st.return_value.encode.return_value.tolist.return_value = [[0.1]]
    data_manager.data = [{"id": "1", "topic": "T"}]
    data_manager.collection.get.return_value = {"ids": ["old1", "old2"]}

    ThemeFinder(data_manager).make_collection()

    data_manager.collection.delete.assert_called_once_with(ids=["old1", "old2"])


def test_make_collection_no_texts_raises(st_and_torch, data_manager):
    data_manager.data = [{"id": "1", "topic": "", "technologies": None}]
    data_manager.collection.get.return_value = {"ids": []}

    tf = ThemeFinder(data_manager)

    with pytest.raises(RuntimeError):
        tf.make_collection()


def test_search_no_filters(st_and_torch, data_manager):
    st, _ = st_and_torch
    st.return_value.encode.return_value.tolist.return_value = [[0.1]]
    data_manager.collection.query.return_value = {"documents": [[]]}
    tf = ThemeFinder(data_manager)

    result = tf.search("query", n_results=5)

    kwargs = data_manager.collection.query.call_args.kwargs
    assert kwargs["n_results"] == 15
    assert kwargs["where"] is None
    assert result == {"documents": [[]]}


def test_search_with_is_used_filter(st_and_torch, data_manager):
    st, _ = st_and_torch
    st.return_value.encode.return_value.tolist.return_value = [[0.1]]
    data_manager.collection.query.return_value = {"documents": [[]]}
    tf = ThemeFinder(data_manager)

    tf.search("q", is_used=True)

    assert data_manager.collection.query.call_args.kwargs["where"] == {
        "is_used": True
    }


def test_search_with_examiner_filter(st_and_torch, data_manager):
    st, _ = st_and_torch
    st.return_value.encode.return_value.tolist.return_value = [[0.1]]
    data_manager.collection.query.return_value = {"documents": [[]]}
    tf = ThemeFinder(data_manager)

    tf.search("q", examiner="Ivanov")

    assert data_manager.collection.query.call_args.kwargs["where"] == {
        "$or": [{"curator": "Ivanov"}, {"examiner": "Ivanov"}]
    }


def test_search_with_both_filters(st_and_torch, data_manager):
    st, _ = st_and_torch
    st.return_value.encode.return_value.tolist.return_value = [[0.1]]
    data_manager.collection.query.return_value = {"documents": [[]]}
    tf = ThemeFinder(data_manager)

    tf.search("q", is_used=False, examiner="Petrov")

    assert data_manager.collection.query.call_args.kwargs["where"] == {
        "$and": [
            {"is_used": False},
            {"$or": [{"curator": "Petrov"}, {"examiner": "Petrov"}]},
        ]
    }


def test_search_blank_examiner_ignored(st_and_torch, data_manager):
    st, _ = st_and_torch
    st.return_value.encode.return_value.tolist.return_value = [[0.1]]
    data_manager.collection.query.return_value = {"documents": [[]]}
    tf = ThemeFinder(data_manager)

    tf.search("q", examiner="   ")

    assert data_manager.collection.query.call_args.kwargs["where"] is None
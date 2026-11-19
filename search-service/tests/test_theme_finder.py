from unittest.mock import MagicMock, patch

import pytest

from app.search_module.src.theme_finder import ThemeFinder
from tests.conftest import make_topic


@pytest.fixture
def theme_finder():
    with (
        patch("app.search_module.src.theme_finder.SentenceTransformer"),
        patch("app.search_module.src.theme_finder.torch") as mock_torch,
    ):
        mock_torch.backends.mps.is_available.return_value = False
        mock_torch.cuda.is_available.return_value = False

        data_manager = MagicMock()
        finder = ThemeFinder(data_manager)
        finder.model.encode.return_value.tolist.return_value = [[0.1, 0.2]]
        yield finder


class TestInit:

    def test_selects_mps_when_available(self):
        with (
            patch("app.search_module.src.theme_finder.SentenceTransformer") as mock_st,
            patch("app.search_module.src.theme_finder.torch") as mock_torch,
        ):
            mock_torch.backends.mps.is_available.return_value = True

            ThemeFinder(MagicMock())

            _, kwargs = mock_st.call_args
            assert kwargs["device"] == "mps"

    def test_selects_cuda_when_mps_unavailable(self):
        with (
            patch("app.search_module.src.theme_finder.SentenceTransformer") as mock_st,
            patch("app.search_module.src.theme_finder.torch") as mock_torch,
        ):
            mock_torch.backends.mps.is_available.return_value = False
            mock_torch.cuda.is_available.return_value = True

            ThemeFinder(MagicMock())

            _, kwargs = mock_st.call_args
            assert kwargs["device"] == "cuda"

    def test_selects_cpu_when_no_gpu_available(self):
        with (
            patch("app.search_module.src.theme_finder.SentenceTransformer") as mock_st,
            patch("app.search_module.src.theme_finder.torch") as mock_torch,
        ):
            mock_torch.backends.mps.is_available.return_value = False
            mock_torch.cuda.is_available.return_value = False

            ThemeFinder(MagicMock())

            _, kwargs = mock_st.call_args
            assert kwargs["device"] == "cpu"


class TestBuildMeta:

    def test_primitives_pass_through_unchanged(self, theme_finder):
        meta = theme_finder._build_meta(
            {"id": "1", "year": 2026, "is_used": True, "grade": 9.5},
            field_type="topic",
        )
        assert meta["id"] == "1"
        assert meta["year"] == 2026
        assert meta["is_used"] is True
        assert meta["grade"] == 9.5

    def test_none_becomes_empty_string(self, theme_finder):
        meta = theme_finder._build_meta(
            {"id": "1", "curator": None}, field_type="topic"
        )
        assert meta["curator"] == ""

    def test_list_becomes_string(self, theme_finder):
        meta = theme_finder._build_meta(
            {"id": "1", "tech_stack": ["Python", "FastAPI"]}, field_type="topic"
        )
        assert isinstance(meta["tech_stack"], str)
        assert "Python" in meta["tech_stack"]

    def test_adds_field_type_and_original_id(self, theme_finder):
        meta = theme_finder._build_meta({"id": "42"}, field_type="topic")
        assert meta["field_type"] == "topic"
        assert meta["original_id"] == "42"

    def test_original_id_defaults_to_empty_string(self, theme_finder):
        meta = theme_finder._build_meta({}, field_type="topic")
        assert meta["original_id"] == ""

    def test_tech_item_added_only_when_provided(self, theme_finder):
        with_tech = theme_finder._build_meta(
            {"id": "1"}, field_type="technologies", tech_item="Python"
        )
        without_tech = theme_finder._build_meta({"id": "1"}, field_type="topic")

        assert with_tech["tech_item"] == "Python"
        assert "tech_item" not in without_tech

    def test_strips_colons_from_keys(self, theme_finder):
        meta = theme_finder._build_meta({"weird:key": "val"}, field_type="topic")
        assert "weird:key" not in meta
        assert meta["weirdkey"] == "val"


class TestMakeCollection:

    def test_raises_when_data_empty(self, theme_finder):
        theme_finder.data_manager.data = []
        with pytest.raises(RuntimeError, match="пусты"):
            theme_finder.make_collection()

    def test_raises_when_data_none(self, theme_finder):
        theme_finder.data_manager.data = None
        with pytest.raises(RuntimeError, match="пусты"):
            theme_finder.make_collection()

    def test_drops_old_collection_and_creates_new(self, theme_finder):
        dm = theme_finder.data_manager
        dm.data = [make_topic(topic_id="1")]
        dm.collection.name = "my_vectors"
        new_collection = MagicMock()
        dm.client.get_or_create_collection.return_value = new_collection
        theme_finder.make_collection()
        dm.client.delete_collection.assert_called_once_with(name="my_vectors")
        dm.client.get_or_create_collection.assert_called_once_with(name="my_vectors")
        assert dm.collection is new_collection

    def test_creates_one_vector_for_topic_only(self, theme_finder):
        dm = theme_finder.data_manager
        dm.data = [make_topic(topic_id="7", technologies="")]
        dm.collection.name = "my_vectors"
        new_collection = MagicMock()
        dm.client.get_or_create_collection.return_value = new_collection
        theme_finder.make_collection()
        add_kwargs = new_collection.add.call_args.kwargs
        assert add_kwargs["ids"] == ["7__topic"]
        assert add_kwargs["documents"] == [make_topic(topic_id="7")["topic"]]

    def test_creates_separate_vector_per_technology(self, theme_finder):
        dm = theme_finder.data_manager
        dm.data = [make_topic(topic_id="1", topic="Чат-бот",
                              technologies="Python, FastAPI")]
        dm.collection.name = "my_vectors"
        new_collection = MagicMock()
        dm.client.get_or_create_collection.return_value = new_collection
        theme_finder.make_collection()

        add_kwargs = new_collection.add.call_args.kwargs
        assert add_kwargs["ids"] == ["1__topic", "1__tech__0", "1__tech__1"]
        assert add_kwargs["documents"] == ["Чат-бот", "Чат-бот", "Чат-бот"]
        assert add_kwargs["metadatas"][1]["tech_item"] == "Python"
        assert add_kwargs["metadatas"][2]["tech_item"] == "FastAPI"

    def test_skips_empty_technology_entries(self, theme_finder):
        dm = theme_finder.data_manager
        dm.data = [make_topic(topic_id="1", topic="Тема",
                              technologies="Python, , FastAPI")]
        dm.collection.name = "my_vectors"
        new_collection = MagicMock()
        dm.client.get_or_create_collection.return_value = new_collection
        theme_finder.make_collection()
        add_kwargs = new_collection.add.call_args.kwargs
        assert add_kwargs["ids"] == ["1__topic", "1__tech__0", "1__tech__2"]

    def test_encodes_topic_and_each_technology(self, theme_finder):
        dm = theme_finder.data_manager
        dm.data = [make_topic(topic_id="1", topic="Чат-бот",
                              technologies="Python")]
        dm.collection.name = "my_vectors"
        dm.client.get_or_create_collection.return_value = MagicMock()
        theme_finder.make_collection()

        encoded_texts = theme_finder.model.encode.call_args.args[0]
        assert encoded_texts == ["Чат-бот", "Python"]

    def test_raises_when_topic_and_tech_both_empty(self, theme_finder):
        dm = theme_finder.data_manager
        dm.data = [make_topic(topic_id="1", topic="", technologies="")]
        dm.collection.name = "my_vectors"
        dm.client.get_or_create_collection.return_value = MagicMock()
        with pytest.raises(RuntimeError, match="Нет данных"):
            theme_finder.make_collection()

    def test_continues_when_old_collection_not_found(self, theme_finder):
        dm = theme_finder.data_manager
        dm.data = [make_topic(topic_id="1")]
        dm.collection.name = "my_vectors"
        dm.client.delete_collection.side_effect = RuntimeError("not found")
        new_collection = MagicMock()
        dm.client.get_or_create_collection.return_value = new_collection

        theme_finder.make_collection()

        new_collection.add.assert_called_once()

    def test_reraises_when_collection_add_fails(self, theme_finder):
        dm = theme_finder.data_manager
        dm.data = [make_topic(topic_id="1")]
        dm.collection.name = "my_vectors"
        new_collection = MagicMock()
        new_collection.add.side_effect = RuntimeError("disk full")
        dm.client.get_or_create_collection.return_value = new_collection

        with pytest.raises(RuntimeError, match="disk full"):
            theme_finder.make_collection()


class TestSearch:

    def test_returns_collection_query_results(self, theme_finder):
        expected = {
            "documents": [["Тема 1"]],
            "distances": [[0.1]],
            "metadatas": [[{"original_id": "1"}]],
        }
        theme_finder.data_manager.collection.query.return_value = expected

        result = theme_finder.search("python")

        assert result == expected

    def test_encodes_query_and_passes_embedding(self, theme_finder):
        theme_finder.model.encode.return_value.tolist.return_value = [[0.5, 0.6]]
        theme_finder.data_manager.collection.query.return_value = {}

        theme_finder.search("python")

        call_kwargs = theme_finder.data_manager.collection.query.call_args.kwargs
        assert call_kwargs["query_embeddings"] == [[0.5, 0.6]]

    def test_triplicates_n_results(self, theme_finder):
        theme_finder.data_manager.collection.query.return_value = {}

        theme_finder.search("python", n_results=5)

        call_kwargs = theme_finder.data_manager.collection.query.call_args.kwargs
        assert call_kwargs["n_results"] == 15

    def test_where_is_none_without_filters(self, theme_finder):
        theme_finder.data_manager.collection.query.return_value = {}

        theme_finder.search("python")

        assert theme_finder.data_manager.collection.query.call_args.kwargs["where"] is None

    def test_filters_by_is_used_true(self, theme_finder):
        theme_finder.data_manager.collection.query.return_value = {}

        theme_finder.search("python", is_used=True)

        call_kwargs = theme_finder.data_manager.collection.query.call_args.kwargs
        assert call_kwargs["where"] == {"is_used": True}

    def test_filters_by_is_used_false(self, theme_finder):
        theme_finder.data_manager.collection.query.return_value = {}

        theme_finder.search("python", is_used=False)

        call_kwargs = theme_finder.data_manager.collection.query.call_args.kwargs
        assert call_kwargs["where"] == {"is_used": False}

    def test_filters_by_examiner(self, theme_finder):
        theme_finder.data_manager.collection.query.return_value = {}

        theme_finder.search("python", examiner="Иванов И.И.")

        call_kwargs = theme_finder.data_manager.collection.query.call_args.kwargs
        assert call_kwargs["where"] == {
            "$or": [
                {"curator": "Иванов И.И."},
                {"examiner": "Иванов И.И."},
            ]
        }

    def test_combines_filters_with_and(self, theme_finder):
        theme_finder.data_manager.collection.query.return_value = {}

        theme_finder.search("python", is_used=True, examiner="Иванов И.И.")

        call_kwargs = theme_finder.data_manager.collection.query.call_args.kwargs
        where = call_kwargs["where"]
        assert "$and" in where
        assert where["$and"][0] == {"is_used": True}
        assert where["$and"][1] == {
            "$or": [
                {"curator": "Иванов И.И."},
                {"examiner": "Иванов И.И."},
            ]
        }

    def test_ignores_whitespace_only_examiner(self, theme_finder):
        theme_finder.data_manager.collection.query.return_value = {}

        theme_finder.search("python", examiner="   ")

        assert theme_finder.data_manager.collection.query.call_args.kwargs["where"] is None

    def test_strips_examiner_whitespace(self, theme_finder):
        theme_finder.data_manager.collection.query.return_value = {}

        theme_finder.search("python", examiner="  Иванов  ")

        call_kwargs = theme_finder.data_manager.collection.query.call_args.kwargs
        where = call_kwargs["where"]
        assert where["$or"][0]["curator"] == "Иванов"
        assert where["$or"][1]["examiner"] == "Иванов"

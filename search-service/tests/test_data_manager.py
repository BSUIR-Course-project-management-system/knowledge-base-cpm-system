from unittest.mock import MagicMock, patch

import pytest

from app.search_module.src.data_manager import DataManager
from app.search_module.src.loader import BaseLoader


@pytest.fixture
def persistent_client_patch():
    with patch(
        "app.search_module.src.data_manager.chromadb.PersistentClient"
    ) as client_cls:
        yield client_cls


def test_init_creates_collection(persistent_client_patch):
    loader = MagicMock(spec=BaseLoader)

    dm = DataManager(loader)

    persistent_client_patch.assert_called_once()
    client = persistent_client_patch.return_value
    client.get_or_create_collection.assert_called_once_with(name="my_vectors")
    assert dm.collection is client.get_or_create_collection.return_value
    assert dm.data is None
    assert dm.loader is loader


def test_load_calls_loader(persistent_client_patch):
    loader = MagicMock(spec=BaseLoader)
    loader.load.return_value = [{"id": 1}]
    dm = DataManager(loader)

    dm.load("/tmp/x.json")

    loader.load.assert_called_once_with("/tmp/x.json")
    assert dm.data == [{"id": 1}]


def test_filter_by_occupancy_keeps_unused(persistent_client_patch):
    dm = DataManager(MagicMock(spec=BaseLoader))
    dm.data = [
        {"id": 1, "is_used": True},
        {"id": 2, "is_used": False},
        {"id": 3},
        {"id": 4, "is_used": True},
    ]

    dm.filter_by_occupancy()

    assert dm.data == [{"id": 2, "is_used": False}, {"id": 3}]


def test_filter_by_occupancy_all_used(persistent_client_patch):
    dm = DataManager(MagicMock(spec=BaseLoader))
    dm.data = [{"id": 1, "is_used": True}]

    dm.filter_by_occupancy()

    assert dm.data == []
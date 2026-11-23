from app.services.openalex_client import restore_abstract


def test_restore_abstract_orders_words_by_position():
    inverted = {"world": [1], "hello": [0], "again": [2]}
    assert restore_abstract(inverted) == "hello world again"


def test_restore_abstract_empty_value():
    assert restore_abstract(None) == ""
    assert restore_abstract({}) == ""

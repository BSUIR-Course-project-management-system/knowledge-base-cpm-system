from unittest.mock import patch

import numpy as np

from app.services.search_service import search_papers


def paper(title, abstract, doi):
    return {
        "title": title,
        "authors": "A. Author",
        "year": 2024,
        "venue": "Journal",
        "abstract": abstract,
        "doi": doi,
        "url": doi,
        "openalex_id": doi,
    }


@patch("app.services.search_service.encode_texts")
@patch("app.services.search_service.search_works")
@patch("app.services.search_service.translate_query", return_value="robot vision")
def test_search_deduplicates_and_sorts_by_semantic_score(
    mock_translate, mock_search, mock_encode
):
    mock_search.side_effect = [
        [
            paper("Robotic vision", "Vision for autonomous robots", "doi:1"),
            paper("Unrelated economics", "Banking markets", "doi:2"),
        ],
        [
            paper("Robotic vision", "A longer abstract about robot vision", "doi:1"),
        ],
    ]

    # First encode call is the two query variants; second is two paper texts.
    mock_encode.side_effect = [
        np.array([[1.0, 0.0], [0.9, 0.1]]),
        np.array([[0.99, 0.01], [0.0, 1.0]]),
    ]

    results = search_papers("роботы и зрение", limit=5)

    assert len(results) == 2
    assert results[0]["doi"] == "doi:1"
    assert results[0]["relevance"] > results[1]["relevance"]


@patch("app.services.search_service.encode_texts")
@patch("app.services.search_service.search_works", return_value=[])
@patch("app.services.search_service.translate_query", side_effect=lambda q: q)
def test_empty_openalex_result_returns_empty(mock_translate, mock_search, mock_encode):
    assert search_papers("no papers") == []
    mock_encode.assert_not_called()

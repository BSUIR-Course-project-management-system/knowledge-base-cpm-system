from __future__ import annotations

import math
import re
from typing import Any, Mapping, Sequence

import numpy as np
from sentence_transformers import SentenceTransformer


class RecommendationModule:
    """Модуль объяснения выбора темы для пользовательского запроса."""

    _STOP_WORDS = {
        "a",
        "an",
        "and",
        "the",
        "база",
        "базе",
        "базой",
        "в",
        "во",
        "для",
        "и",
        "из",
        "интеллектуальная",
        "интеллектуальной",
        "интеллектуальный",
        "интеллектуального",
        "к",
        "на",
        "о",
        "об",
        "по",
        "под",
        "при",
        "с",
        "со",
        "система",
        "системы",
        "системой",
        "тем",
        "тема",
        "темы",
        "у",
        "для",
        "knowledge",
        "system",
        "systems",
        "знаний",
        "знание",
    }
    _TOKEN_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9-]+")
    _RUSSIAN_ENDINGS = (
        "иями",
        "ями",
        "ами",
        "ого",
        "его",
        "ому",
        "ему",
        "ыми",
        "ими",
        "иях",
        "ах",
        "ях",
        "ия",
        "ий",
        "ие",
        "ые",
        "ое",
        "ая",
        "яя",
        "ам",
        "ям",
        "ом",
        "ем",
        "ой",
        "ей",
        "ый",
        "ий",
        "ые",
        "ую",
        "юю",
        "ов",
        "ев",
        "иям",
        "а",
        "я",
        "ы",
        "и",
        "е",
        "о",
        "у",
        "ю",
    )

    def __init__(self, model: SentenceTransformer) -> None:
        self.model = model

    def build_recommendations(
        self,
        query: str,
        documents: Sequence[str],
        distances: Sequence[float] | None = None,
        metadatas: Sequence[Mapping[str, Any] | None] | None = None,
    ) -> list[dict[str, Any]]:
        """Возвращает темы вместе с объяснением их выбора."""
        if not documents:
            return []

        query_embedding = self.model.encode(
            query,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        document_embeddings = self.model.encode(
            list(documents),
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        recommendations: list[dict[str, Any]] = []
        for index, document in enumerate(documents):
            distance = (
                distances[index]
                if distances is not None and index < len(distances)
                else None
            )
            metadata = (
                metadatas[index]
                if metadatas is not None and index < len(metadatas)
                else None
            )
            similarity = float(np.dot(query_embedding, document_embeddings[index]))
            explanation = self._build_explanation(
                query=query,
                document=document,
                similarity=similarity,
                distance=distance,
            )
            recommendations.append(
                {
                    "document": document,
                    "distance": distance,
                    "metadata": metadata,
                    "similarity": similarity,
                    "explanation": explanation,
                }
            )
        return recommendations

    def _build_explanation(
        self,
        query: str,
        document: str,
        similarity: float,
        distance: float | None,
    ) -> str:
        query_keywords = self._extract_keywords(query)
        document_keywords = self._extract_keywords(document)
        matched_keywords = self._match_keywords(query_keywords, document_keywords)
        document_focus = self._document_focus(document_keywords, matched_keywords)
        similarity_label = self._similarity_label(similarity)

        score_part = (
            f"Модель увидела {similarity_label} семантическую близость "
            f"(cosine similarity: {similarity:.3f}"
        )
        if distance is not None:
            score_part += f", дистанция поиска: {distance:.3f}"
        score_part += ")."

        parts = [score_part]
        if matched_keywords:
            parts.append(
                "Ключевые опоры темы: " + ", ".join(matched_keywords[:4]) + "."
            )
        else:
            parts.append(
                "Прямых совпадений по словам почти нет, но тема совпадает с запросом по смысловому вектору."
            )

        if document_focus:
            parts.append(
                "Основной акцент темы: " + ", ".join(document_focus[:4]) + "."
            )

        return " ".join(parts)

    def _extract_keywords(self, text: str) -> list[str]:
        tokens = self._TOKEN_RE.findall(text.lower())
        keywords: list[str] = []
        seen: set[str] = set()

        for token in tokens:
            if token in self._STOP_WORDS or len(token) < 3:
                continue
            if token not in seen:
                keywords.append(token)
                seen.add(token)

        return keywords

    def _match_keywords(
        self, query_keywords: Sequence[str], document_keywords: Sequence[str]
    ) -> list[str]:
        document_by_signature: dict[str, str] = {}
        for keyword in document_keywords:
            document_by_signature.setdefault(self._keyword_signature(keyword), keyword)

        matches: list[str] = []
        seen: set[str] = set()
        for keyword in query_keywords:
            match = document_by_signature.get(self._keyword_signature(keyword))
            if match and match not in seen:
                matches.append(match)
                seen.add(match)

        return matches

    def _document_focus(
        self, document_keywords: Sequence[str], matched_keywords: Sequence[str]
    ) -> list[str]:
        matched_set = set(matched_keywords)
        return [keyword for keyword in document_keywords if keyword not in matched_set]

    def _keyword_signature(self, keyword: str) -> str:
        token = keyword.lower().replace("ё", "е")

        for ending in self._RUSSIAN_ENDINGS:
            if token.endswith(ending) and len(token) - len(ending) >= 3:
                token = token[: -len(ending)]
                break

        if token.endswith("s") and len(token) > 4:
            token = token[:-1]

        return token

    def _similarity_label(self, similarity: float) -> str:
        if math.isclose(similarity, 0.0, abs_tol=1e-6):
            return "нулевую"
        if similarity >= 0.75:
            return "очень высокую"
        if similarity >= 0.55:
            return "высокую"
        if similarity >= 0.35:
            return "умеренную"
        return "заметную"

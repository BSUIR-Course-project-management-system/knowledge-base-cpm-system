from sentence_transformers import SentenceTransformer, util
import torch
from rapidfuzz import fuzz
from logger.logger import Logger

LOG_FILE = "table_api/logs/topic_matcher.log"


class TopicMatcher:
    def __init__(self, model_path="sentence-transformers/all-MiniLM-L6-v2"):
        self._logger = Logger(LOG_FILE, level="DEBUG")
        if torch.backends.mps.is_available():
            device = "mps"
        elif torch.cuda.is_available():
            device = "cuda"
        else:
            device = "cpu"

        self.model = SentenceTransformer(model_path, device=device)
        self._logger.info(f"Модель загружена на устройство: {device}")

    def are_topics_identical(
        self, topic1: str, topic2: str, threshold: float = 0.85
    ) -> bool:
        """
        Проверяет, идентичны ли две темы по смыслу.

        :param topic1: Первая тема (строка)
        :param topic2: Вторая тема (строка)
        :param threshold: Порог "идентичности" (0.85 - 0.90 обычно оптимально для текстов)
        :return: True, если темы семантически совпадают, иначе False
        """

        embeddings = self.model.encode(
            [topic1, topic2], show_progress_bar=False, convert_to_tensor=True
        )

        cosine_score = util.cos_sim(embeddings[0], embeddings[1]).item()

        is_identical = cosine_score >= threshold

        self._logger.info(
            f"Сходство тем: {cosine_score:.4f} | Идентичны: {is_identical}"
        )

        return is_identical

    def is_topic_in_list(
        self, topic_to_search: str, topics_list: list[str], threshold: float = 0.85
    ) -> bool:
        """
        Проверяет, есть ли семантический дубликат темы в заданном списке.

        :param topic1: Тема для проверки (строка)
        :param topics_list: Список существующих тем
        :param threshold: Порог совпадения (0.85 - 0.90)
        :return: True, если похожая тема найдена, иначе False
        """
        if not topics_list:
            return False

        query_emb = self.model.encode(
            [topic_to_search], show_progress_bar=False, convert_to_tensor=True
        )

        corpus_emb = self.model.encode(
            topics_list, show_progress_bar=False, convert_to_tensor=True
        )
        self._logger.debug(f"topics:{topics_list}")
        cosine_scores = util.cos_sim(query_emb, corpus_emb)[0].tolist()
        self._logger.debug(f"topics cosine_scores:{cosine_scores}")
        for i, existing_topic in enumerate(topics_list):
            semantic_score = cosine_scores[i]

            lexical_score = (
                fuzz.token_sort_ratio(topic_to_search.lower(), existing_topic.lower())
                / 100.0
            )

            hybrid_score = (semantic_score * 0.5) + (lexical_score * 0.65)

            # print(f"Сравниваем с: {existing_topic}")
            # print(
            #     f"  Вектор: {semantic_score:.2f} | RapidFuzz: {lexical_score:.2f} | ИТОГ: {hybrid_score:.2f}"
            # )

            if hybrid_score >= threshold:
                return True
        return False


# --- ПРИМЕР ИСПОЛЬЗОВАНИЯ ---
# if __name__ == "__main__":
#     matcher = TopicMatcher()

#     topic = "Система управления курсовыми"
#     query = [
#         "База знаний системы управления курсовыми",
#         "База знаний системы управления парковкой",
#         "Система управления кухней",
#         "Система управления медицинским центром",
#     ]

#     result = matcher.is_topic_in_list(topic, query)
#     print(result)

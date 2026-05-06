from typing import Any, Optional

from sentence_transformers import SentenceTransformer

from logger.logger import Logger
from search_module.src.data_manager import DataManager
from search_module.src.settings import PATH_TO_MODEL, THEME_FINDER_LOG_FILE
from rapidfuzz import fuzz
import torch


class ThemeFinder:
    """Класс для поиска тем"""

    def __init__(self, data_manager: DataManager) -> None:
        """Функция инициализации"""
        if torch.backends.mps.is_available():
            device = "mps"  # Для MacBook
        elif torch.cuda.is_available():
            device = "cuda"  # Для компьютеров с видеокартами NVIDIA
        else:
            device = "cpu"

        self.model = SentenceTransformer("BAAI/bge-m3", device=device)
        self.data_manager = data_manager
        self.logger = Logger(THEME_FINDER_LOG_FILE, level="debug")

    def make_collection(self) -> None:
        """Функция формирования векторов поиска с очисткой и метаданными"""
        self.logger.info("Инициализация создания коллекции векторов")

        if not self.data_manager.data:
            raise RuntimeError("Данные в DataManager пусты.")

        collection = self.data_manager.collection
        data = self.data_manager.data

        try:
            existing = collection.get()
            if existing.get("ids"):
                collection.delete(ids=existing["ids"])
                self.logger.debug(f"Удалено {len(existing['ids'])} старых записей")
        except Exception as e:
            self.logger.warning(f"Очистка не удалась: {e}")

        texts = [str(item.get("topic", "")) for item in data]
        ids = [str(item.get("id", i)) for i, item in enumerate(data)]

        self.logger.debug(f"Кодирование векторов для {len(texts)} записей")
        embeddings = self.model.encode(
            texts, show_progress_bar=True, normalize_embeddings=True
        ).tolist()

        metadatas = []
        for item in data:
            clean_meta = {}
            for k, v in item.items():
                if k == "topic":
                    continue
                clean_key = k.replace(":", "").strip()

                if v is None:
                    clean_meta[clean_key] = ""
                elif isinstance(v, (str, int, float, bool)):
                    clean_meta[clean_key] = v
                else:
                    clean_meta[clean_key] = str(v)
            metadatas.append(clean_meta)

        self.logger.debug("Запись данных в ChromaDB")
        try:
            collection.add(
                embeddings=embeddings, documents=texts, ids=ids, metadatas=metadatas
            )

            total_count = collection.count()
            msg = f"Коллекция векторов успешно создана. Записей в базе: {total_count}"
            self.logger.info(msg)

        except Exception as e:
            self.logger.error(f"Ошибка при сохранении коллекции: {e}")
            raise

    def search(
        self,
        query: str,
        n_results: int = 7,
        is_used: Optional[bool] = None,
        curator: Optional[str] = None,
        examiner: Optional[str] = None,
    ) -> Any:
        """Функция векторного поиска"""
        self.logger.info(f"Поиск по запросу: {query}")
        query_emb = self.model.encode(
            [query], show_progress_bar=False, normalize_embeddings=True
        ).tolist()

        conditions = []

        if is_used is not None:
            conditions.append({"is_used": is_used})
        if curator and curator.strip():
            conditions.append({"curator": curator.strip()})
        if examiner and examiner.strip():
            conditions.append({"examiner": examiner.strip()})

        where_filter = None
        if len(conditions) == 1:
            where_filter = conditions[0]
        elif len(conditions) > 1:
            where_filter = {"$and": conditions}

        self.logger.debug(f"Применяемый фильтр: {where_filter}")

        results = self.data_manager.collection.query(
            query_embeddings=query_emb,
            n_results=n_results,
            include=["documents", "distances", "metadatas"],
            where=where_filter,
        )

        self.logger.info("Поиск окончен")
        return results

import logging
from typing import Any, Optional

import torch
from sentence_transformers import SentenceTransformer

from app.search_module.src.data_manager import DataManager
from app.core.config import settings

logger = logging.getLogger(__name__)


class ThemeFinder:
    def __init__(self, data_manager: DataManager) -> None:
        if torch.backends.mps.is_available():
            device = "mps"
        elif torch.cuda.is_available():
            device = "cuda"
        else:
            device = "cpu"

        logger.info(f"Загрузка модели {settings.MODEL_NAME} на устройство {device}")
        self.model = SentenceTransformer(settings.MODEL_NAME, device=device)
        self.data_manager = data_manager

    def _build_meta(
        self, item: dict, field_type: str, tech_item: Optional[str] = None
    ) -> dict:
        clean_meta: dict = {}
        for k, v in item.items():
            clean_key = k.replace(":", "").strip()
            if v is None:
                clean_meta[clean_key] = ""
            elif isinstance(v, (str, int, float, bool)):
                clean_meta[clean_key] = v
            else:
                clean_meta[clean_key] = str(v)

        clean_meta["field_type"] = field_type
        clean_meta["original_id"] = str(item.get("id", ""))
        if tech_item is not None:
            clean_meta["tech_item"] = tech_item
        return clean_meta

    def make_collection(self) -> None:
        logger.info("Инициализация создания коллекции векторов")

        if not self.data_manager.data:
            raise RuntimeError("Данные в DataManager пусты.")

        collection = self.data_manager.collection
        data = self.data_manager.data

        try:
            existing = collection.get()
            if existing.get("ids"):
                collection.delete(ids=existing["ids"])
                logger.debug(f"Удалено {len(existing['ids'])} старых записей")
        except Exception as e:
            logger.warning(f"Очистка не удалась: {e}")

        texts_for_embedding: list[str] = []
        documents_for_storage: list[str] = []
        ids: list[str] = []
        metadatas: list[dict] = []

        for i, item in enumerate(data):
            item_id = str(item.get("id", i))
            topic = str(item.get("topic") or "").strip()
            technologies = item.get("technologies")
            tech_text = str(technologies).strip() if technologies is not None else ""

            if topic:
                texts_for_embedding.append(topic)
                documents_for_storage.append(topic)
                ids.append(f"{item_id}__topic")
                metadatas.append(self._build_meta(item, field_type="topic"))

            if tech_text:
                for j, raw_tech in enumerate(tech_text.split(",")):
                    tech = raw_tech.strip()
                    if not tech:
                        continue
                    texts_for_embedding.append(tech)
                    documents_for_storage.append(topic if topic else tech)
                    ids.append(f"{item_id}__tech__{j}")
                    metadatas.append(
                        self._build_meta(
                            item, field_type="technologies", tech_item=tech
                        )
                    )

        if not texts_for_embedding:
            raise RuntimeError(
                "Нет данных для индексации (topic и technologies пусты)."
            )

        logger.info(
            f"Кодирование {len(texts_for_embedding)} векторов. Это может занять время..."
        )
        embeddings = self.model.encode(
            texts_for_embedding, show_progress_bar=False, normalize_embeddings=True
        ).tolist()

        logger.debug("Запись данных в ChromaDB")
        try:
            collection.add(
                embeddings=embeddings,
                documents=documents_for_storage,
                ids=ids,
                metadatas=metadatas,
            )
            total_count = collection.count()
            logger.info(f"Коллекция создана. Записей в базе: {total_count}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении коллекции: {e}")
            raise

    def search(
        self,
        query: str,
        n_results: int = 7,
        is_used: Optional[bool] = None,
        examiner: Optional[str] = None,
    ) -> Any:
        logger.info(f"Поиск по запросу: {query}")

        query_emb = self.model.encode(
            [query], show_progress_bar=False, normalize_embeddings=True
        ).tolist()

        conditions = []
        if is_used is not None:
            conditions.append({"is_used": is_used})
        if examiner and examiner.strip():
            conditions.append(
                {
                    "$or": [
                        {"curator": examiner.strip()},
                        {"examiner": examiner.strip()},
                    ]
                }
            )

        where_filter = None
        if len(conditions) == 1:
            where_filter = conditions[0]
        elif len(conditions) > 1:
            where_filter = {"$and": conditions}

        internal_n = n_results * 3
        logger.debug(f"Фильтр: {where_filter}; n_results={internal_n}")

        results = self.data_manager.collection.query(
            query_embeddings=query_emb,
            n_results=internal_n,
            include=["documents", "distances", "metadatas"],
            where=where_filter,
        )

        logger.info("Векторный поиск окончен")
        return results

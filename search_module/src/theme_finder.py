from typing import Any, Optional

from sentence_transformers import SentenceTransformer

from search_module.src.data_manager import DataManager
from search_module.src.settings import PATH_TO_MODEL


class ThemeFinder:
    """Класс для поиска тем"""

    def __init__(self, data_manager: DataManager) -> None:
        """Функция инициализации"""
        self.model = SentenceTransformer(str(PATH_TO_MODEL))
        self.data_manager = data_manager

    def make_collection(self) -> None:
        """Функция формирования векторов поиска"""
        if not self.data_manager.data:
            raise RuntimeError(
                "Данные не загружены. Сначала вызовите data_manager.load()"
            )

        collection = self.data_manager.collection

        all_ids = collection.get()["ids"]
        if all_ids:
            collection.delete(ids=all_ids)

        data = self.data_manager.data
        texts = [item["text"] for item in data]
        embeddings = self.model.encode(texts, show_progress_bar=True).tolist()
        ids = [str(item["id"]) for item in data]

        metadatas = []
        for item in data:
            meta = {k: v for k, v in item.items() if k != "text"}
            metadatas.append(meta)

        collection.add(
            embeddings=embeddings, documents=texts, ids=ids, metadatas=metadatas
        )

    def search(
        self,
        query: str,
        n_results: int = 4,
        is_used: Optional[bool] = None,
        curator: Optional[str] = None,
        examiner: Optional[str] = None,
    ) -> Any:
        """Функция векторного поиска"""
        query_emb = self.model.encode([query], show_progress_bar=False).tolist()

        conditions = []
        if curator is not None:
            conditions.append({"curator": curator})
        if examiner is not None:
            conditions.append({"examiner": examiner})
        if is_used is not None:
            conditions.append({"is_used": is_used})

        where_filter = None
        if len(conditions) == 1:
            where_filter = conditions[0]
        elif len(conditions) > 1:
            where_filter = {"$and": conditions}

        results = self.data_manager.collection.query(
            query_embeddings=query_emb,
            n_results=n_results,
            include=["documents", "distances", "metadatas"],
            where=where_filter,
        )
        return results

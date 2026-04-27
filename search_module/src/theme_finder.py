from typing import Any

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
            print("Данные не загружены. Сначала вызовите data_manager.load()")
            return

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
        print("База данных успешно заполнена!")

    def search(self, query: str, n_results: int = 4) -> Any:
        """Функция векторного поиска"""
        query_emb = self.model.encode([query], show_progress_bar=False).tolist()
        results = self.data_manager.collection.query(
            query_embeddings=query_emb,
            n_results=n_results,
            include=["documents", "distances", "metadatas"],
        )
        return results

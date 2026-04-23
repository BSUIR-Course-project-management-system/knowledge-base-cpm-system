from sentence_transformers import SentenceTransformer

from search_module.src.settings import PATH_TO_MODEL, PATH_TO_CHROMA_DB, PATH_TO_TEST_JSON
from search_module.src.data_manager import DataManager


class ThemeFinder:
    def __init__(self, data_manager: DataManager) -> None:
        self.model = SentenceTransformer(PATH_TO_MODEL)
        self.data_manager = data_manager

    def make_collection(self) -> None:
        if not self.data_manager.data:
            print("Данные не загружены. Сначала вызовите data_manager.load()")
            return

        data = self.data_manager.data
        collection = self.data_manager.collection

        texts = [item['text'] for item in data]
        embeddings = self.model.encode(texts, show_progress_bar=True).tolist()
        ids = [str(item['id']) for item in data]
        metadatas = [item['metadata'] for item in data]

        collection.add(embeddings=embeddings, documents=texts, metadatas=metadatas, ids=ids)
        print("База данных успешно заполнена!")

    def search(self, query: str, n_results: int = 4):
        query_emb = self.model.encode([query], show_progress_bar=False).tolist()
        results = self.data_manager.collection.query(
            query_embeddings=query_emb,
            n_results=n_results,
        )
        return results

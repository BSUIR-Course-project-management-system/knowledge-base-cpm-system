import chromadb

from app.core.config import settings


class DataManager:
    def __init__(self) -> None:
        self.data: list[dict] | None = None
        self.client = chromadb.PersistentClient(path=settings.PATH_TO_CHROMA_DB)
        self.collection = self.client.get_or_create_collection(name="my_vectors")

    def set_data(self, data: list[dict]) -> None:
        self.data = data

    def load_from_collection(self) -> None:
        result = self.collection.get(where={"field_type": "topic"})
        self.data = []
        if not result or not result.get("documents"):
            return
        for doc, meta in zip(result["documents"], result["metadatas"]):
            item = dict(meta)
            item["topic"] = doc
            self.data.append(item)
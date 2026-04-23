import chromadb

from settings import PATH_TO_CHROMA_DB
from loader import BaseLoader


class DataManager:
    def __init__(self, base_loader: BaseLoader) -> None:
        self.data = None
        self.loader = base_loader
        self.client = chromadb.PersistentClient(path=PATH_TO_CHROMA_DB)
        self.collection = self.client.get_or_create_collection(name="my_vectors")

    def load(self, path: str) -> None:
        self.data = self.loader.load(path)

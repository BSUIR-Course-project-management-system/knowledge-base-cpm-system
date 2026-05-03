from abc import ABC, abstractmethod
import json


class ILoader(ABC):
    @abstractmethod
    def load(self, file_path: str) -> dict:
        pass


class JsonLoader(ILoader):
    def load(self, file_path: str) -> dict:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                result = json.load(f)
                return result
        except FileNotFoundError:
            # logging.error("Файл для загрузки не найден")
            return None

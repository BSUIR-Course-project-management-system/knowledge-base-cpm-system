from abc import ABC, abstractmethod
import json


class ISaver(ABC):
    @abstractmethod
    def save(self, file_path: str) -> dict:
        pass


class JsonSaver(ISaver):
    def save(self, file_path: str, data: dict) -> None:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except FileNotFoundError:
            # logging.error("Файл для загрузки не найден")
            return

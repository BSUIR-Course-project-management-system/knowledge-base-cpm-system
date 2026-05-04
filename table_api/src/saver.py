from abc import ABC, abstractmethod
from logger.logger import Logger
import json

LOG_FILE = "table_api/logs/saver.log"


class ISaver(ABC):
    @abstractmethod
    def save(self, file_path: str, data: dict) -> dict:
        pass


class JsonSaver(ISaver):
    def __init__(
        self, encoding: str = "utf-8", indent: int = 2, ensure_ascii: bool = False
    ):
        self._encoding = encoding
        self._indent = indent
        self._ensure_ascii = ensure_ascii
        self._logger = Logger(LOG_FILE, level="INFO")

    def save(self, file_path: str, data: dict) -> None:
        try:
            with open(file_path, "w", encoding=self._encoding) as f:
                self._logger.info(f"Попытка сохранения в файл {file_path}")
                json.dump(data, f, ensure_ascii=self._ensure_ascii, indent=self._indent)
                self._logger.info(f"Успешное сохранение в файл {file_path}")
        except FileNotFoundError:
            self._logger.error("Файл для сохранения не найден")
            return

from abc import ABC, abstractmethod
from logger.logger import Logger
import json

LOG_FILE = "table_api/logs/loader.log"


class ILoader(ABC):
    @abstractmethod
    def load(self, file_path: str) -> dict:
        pass


class JsonLoader(ILoader):
    def __init__(self, encoding: str = "utf-8"):
        self._encoding = encoding
        self._logger = Logger(LOG_FILE, level="INFO")

    def load(self, file_path: str) -> dict:
        try:
            with open(file_path, "r", encoding=self._encoding) as f:
                # self._logger.info(f"Попытка загрузки из файла {file_path}")
                result = json.load(f)
                # self._logger.info(f"Данные загружены из файла {file_path}")
                return result
        except FileNotFoundError:
            self._logger.error("Файл для загрузки не найден")
            return None

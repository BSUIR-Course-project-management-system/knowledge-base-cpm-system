import json
from abc import ABC, abstractmethod
from typing import Any, List


class BaseLoader(ABC):
    """Абстрактный класс являющийся базовым для загрузки данных"""

    @abstractmethod
    def load(self, path: str) -> List[Any]:
        """Функция загрузки данных (интерфейс)"""
        pass


class JsonLoader(BaseLoader):
    """Класс загрузки данных в формате json"""

    def load(self, path: str) -> List[Any]:
        """Функция загрузки данных в формате json"""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    



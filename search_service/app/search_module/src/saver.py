import json
from abc import ABC, abstractmethod
from typing import Any, List


class BaseSaver(ABC):
    """Абстрактный класс являющийся базовым для сохранения данных"""

    @abstractmethod
    def save(self, path: str, data:str) -> None:
        """Функция сохранения данных (интерфейс)"""
        pass


class JsonSaver(BaseSaver):
    """Класс сохранения данных в формате json"""

    def save(self, path: str, data:str) -> None:
        """Функция сохранения данных в формате json"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(data)
    



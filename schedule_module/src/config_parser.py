from abc import ABC, abstractmethod
from typing import Dict, Any
import yaml
from .logger import logger


class BaseParser(ABC):
    """
    Абстрактный класс, задающий интерфейс классам наследникам для парсинга файлов
    """

    @abstractmethod
    def parse_config(self, filename: str) -> Dict[str, Any]:
        """Абстрактный метод парсинга конфиг-файлов

        Args:
            filename (str): Имя файла для парсинга

        Returns:
            Dict[str, Any]: Словарь с переменными конфигурации
        """
        pass


class YamlParser(BaseParser):
    """
    Класс для парсинга .yaml файлов
    """

    def parse_config(self, filename: str) -> Dict[str, Any]:
        """Метод парсинга .yaml файлов

        Args:
            filename (str): Имя .yaml файла

        Returns:
            Dict[str, Any]: Словарь с переменными конфигурации
        """
        with open(
            filename,
            "r",
        ) as f:
            logger.info("Файл конфига был успешно открыт")
            data = yaml.safe_load(f)
            logger.info("Данные успешно обработаны")

        return data

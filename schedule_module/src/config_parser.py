from abc import ABC, abstractmethod
from typing import Dict, Any
import yaml
from .logger import logger


class BaseParser(ABC):
    @abstractmethod
    def parse_config(self, filename: str) -> Dict[str, Any]:
        pass


class YamlParser(BaseParser):
    def parse_config(self, filename: str) -> Dict[str, Any]:
        with open(
            filename,
            "r",
        ) as f:
            logger.info("Файл конфига был успешно открыт")
            data = yaml.safe_load(f)
            logger.info("Данные успешно обработаны")

        return data

from abc import ABC, abstractmethod
from typing import Dict, Any
import yaml


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
            data = yaml.safe_load(f)

        return data

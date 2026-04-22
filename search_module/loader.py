from abc import ABC, abstractmethod
from typing import List, Any

import json

class BaseLoader(ABC):
    @abstractmethod
    def load(self, path:str)->List[Any]:
        pass

class JsonLoader(BaseLoader):
    def load(self, path:str)->List[Any]:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
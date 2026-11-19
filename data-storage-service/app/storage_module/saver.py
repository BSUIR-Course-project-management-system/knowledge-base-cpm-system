import json
import os
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path


class SaveError(Exception):
    """Не удалось сохранить данные."""


class ISaver(ABC):
    @abstractmethod
    def save(self, file_path: str, data: dict) -> None:
        """
        Сохраняет данные в файл.

        :raises SaveError: при ошибках доступа, кодировки или сериализации
            (исходное исключение доступно в __cause__)
        :raises Exception: при программных ошибках реализации
        """


class JsonSaver(ISaver):
    def __init__(
        self, encoding: str = "utf-8", indent: int = 2, ensure_ascii: bool = False
    ):
        self._encoding = encoding
        self._indent = indent
        self._ensure_ascii = ensure_ascii

    def save(self, file_path: str, data: dict) -> None:
        path = Path(file_path)
        tmp_name = None
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                "w",
                encoding=self._encoding,
                dir=path.parent,
                prefix=path.name + ".",
                suffix=".tmp",
                delete=False,
            ) as f:
                tmp_name = f.name
                json.dump(data, f, ensure_ascii=self._ensure_ascii, indent=self._indent)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_name, path)
        except UnicodeEncodeError as e:
            raise SaveError(f"Ошибка кодировки {self._encoding} в {file_path}") from e
        except (TypeError, ValueError) as e:
            raise SaveError(f"Данные не сериализуются в JSON: {file_path}") from e
        except LookupError as e:
            raise SaveError(f"Неизвестная кодировка: {self._encoding}") from e
        except OSError as e:
            raise SaveError(f"Ошибка записи: {file_path}") from e
        finally:
            if tmp_name and os.path.exists(tmp_name):
                os.unlink(tmp_name)

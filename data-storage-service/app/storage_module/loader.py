import json
from abc import ABC, abstractmethod


class LoadError(Exception):
    """Не удалось загрузить данные."""


class ILoader(ABC):
    @abstractmethod
    def load(self, file_path: str) -> dict:
        """
        Загружает данные из файла.

        :return: Корневой объект данных.
        :rtype: dict

        :raises: LoadError: при ошибках доступа к файлу, парсинга или кодировки
            (Исходное исключение доступно в __cause__)
        :raises: Exception: при программных ошибках реализации.
        """


class JsonLoader(ILoader):
    def __init__(self, encoding: str = "utf-8"):
        self._encoding = encoding

    def load(self, file_path: str) -> dict:
        try:
            with open(file_path, "r", encoding=self._encoding) as f:
                result = json.load(f)
        except FileNotFoundError as e:
            raise LoadError(f"Файл не найден: {file_path}") from e
        except json.JSONDecodeError as e:
            raise LoadError(
                f"Некорректный JSON: {file_path} (строка {e.lineno}, столбец {e.colno})"
            ) from e
        except UnicodeDecodeError as e:
            raise LoadError(f"Ошибка кодировки {self._encoding} в {file_path}") from e
        except LookupError as e:
            raise LoadError(f"Неизвестная кодировка: {self._encoding}") from e
        except OSError as e:
            raise LoadError(f"Ошибка чтения: {file_path}") from e

        if not isinstance(result, dict):
            raise LoadError(
                f"Корень JSON должен быть объектом (формат словаря): {file_path}"
            )
        return result

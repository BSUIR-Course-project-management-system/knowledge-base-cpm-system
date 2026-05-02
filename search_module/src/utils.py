from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseThemePrinter(ABC):
    """Базовый класс для вывода тем"""

    @staticmethod
    @abstractmethod
    def print_themes(results: Dict[str, Any]) -> None:
        """Функция вывода ntv"""
        pass


class ConsoleThemePrinter(BaseThemePrinter):
    """Класс для вывода тем в консоли"""

    @staticmethod
    def print_themes(results: Dict[str, Any]) -> None:
        """Функция вывода тем в консоли"""

        docs = results["documents"][0]
        dists = results["distances"][0]
        metas = results["metadatas"][0]

        if not docs:
            print("Ничего не найдено. Попробуйте переформулировать запрос.")
        else:
            for i, (doc, dist, meta) in enumerate(zip(docs, dists, metas), start=1):
                cat = meta.get("cat", "N/A") if meta else "N/A"
                print(f"  {i}. '{doc}' (расстояние: {dist:.3f}) [{cat}]")


class BaseMenuPrinter(ABC):
    """Базовый класс для вывода меню"""

    @staticmethod
    @abstractmethod
    def print_menu() -> None:
        """Функция вывода меню"""
        pass


class SortMenuPrinter(BaseMenuPrinter):
    """Класс для вывода меню сортировки"""

    @staticmethod
    def print_menu() -> None:
        """Функция вывода меню сортировки"""
        print("\n_______________Сортировка_______________")
        print("1 - сортировка по оценке")
        print("2 - cортировка по дате")
        print("3 - сортровка по релевантности")
        print("любая клавиша  - стоп")
        print("________________________________________\n")

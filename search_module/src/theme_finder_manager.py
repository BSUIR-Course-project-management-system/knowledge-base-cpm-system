from typing import Any, Dict, Optional

from search_module.src.data_manager import DataManager
from search_module.src.loader import BaseLoader
from search_module.src.saver import BaseSaver
from search_module.src.settings import MAX_DISTANCE, PATH_TO_TEST_JSON
from search_module.src.theme_finder import ThemeFinder
from table_api.storage import Storage


class ThemeFinderManager:
    """Класс для управления поиском тем"""

    def __init__(
        self,
        loader: BaseLoader,
        saver: BaseSaver,
    ) -> None:
        """Функция инициализации"""
        self.loader = loader
        self.saver = saver
        self.data_manager: Optional[DataManager] = None
        self.theme_finder: Optional[ThemeFinder] = None
        self.storage = Storage()

    def process_data(self, path_to_data: str = PATH_TO_TEST_JSON) -> None:
        """Функция обработки данных"""
        self.data_manager = DataManager(self.loader)
        unique_topics_json = self.storage.get_unique_topics()

        self.saver.save(path_to_data, unique_topics_json)

        self.data_manager.load(path_to_data)

    def prepare_search(self) -> None:
        """Функция инициализации поиска"""
        if self.data_manager is None:
            raise RuntimeError("DataManager не инициализирован")
        try:
            self.theme_finder = ThemeFinder(self.data_manager)
            self.theme_finder.make_collection()
        except Exception as e:
            raise RuntimeError(f"Не удалось инициализировать поиск: {e}")

    def search(self, query: str, n_results: int = 4) -> Dict[str, Any]:
        """Функция поиска темы"""
        if self.theme_finder is None:
            raise RuntimeError("Поиск не готов")

        return self.theme_finder.search(query, n_results=n_results)

    def filter_results_by_distance(
        self, results: Dict[str, Any], max_distance: float = 0.7
    ) -> Dict[str, Any]:
        """Функция фильтрации по расстоянию"""

        docs = results.get("documents", [[]])[0]
        dists = results.get("distances", [[]])[0]
        metas = results.get("metadatas", [[]])[0]

        filtered = {}
        filtered["documents"] = [[]]
        filtered["distances"] = [[]]
        filtered["metadatas"] = [[]]

        for doc, dist, meta in zip(docs, dists, metas):
            if dist <= max_distance:
                filtered["documents"][0].append(doc)
                filtered["distances"][0].append(dist)
                filtered["metadatas"][0].append(meta)
        return filtered

    def search_relevant(
        self,
        query: str,
        n_results: int = 4,
        max_distance: float = MAX_DISTANCE,
        is_used: bool = False,
        curator: Optional[str] = None,
        examiner: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Функция поиска релевантных тем"""
        if self.theme_finder is None:
            raise RuntimeError("Поиск не инициализирован")
        raw_results = self.theme_finder.search(
            query,
            n_results=n_results,
            is_used=is_used,
            curator=curator,
            examiner=examiner,
        )
        return self.filter_results_by_distance(raw_results, max_distance)

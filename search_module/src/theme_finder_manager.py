from typing import Any, Dict, Optional

from logger.logger import Logger
from search_module.src.data_manager import DataManager
from search_module.src.loader import BaseLoader
from search_module.src.saver import BaseSaver
from search_module.src.settings import (
    MAX_DISTANCE,
    PATH_TO_TEST_JSON,
    THEME_FINDER_MANAGER_LOG_FILE,
)
from search_module.src.theme_finder import ThemeFinder
from table_api.src.storage import Storage


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
        self.logger = Logger(THEME_FINDER_MANAGER_LOG_FILE, level="INFO")

    def process_data(self, path_to_data: str = PATH_TO_TEST_JSON) -> None:
        """Функция обработки данных"""
        self.logger.info("Инициализация получения тем")
        self.data_manager = DataManager(self.loader)
        unique_topics_json = self.storage.get_unique_topics()
        self.logger.info("Темы получены")

        self.saver.save(path_to_data, unique_topics_json)
        self.logger.info("Темы сохранены в файл")

        self.data_manager.load(path_to_data)
        self.logger.info("Темы загружены в DataManager")

    def prepare_search(self) -> None:
        """Функция инициализации поиска"""
        if self.data_manager is None:
            raise RuntimeError("DataManager не инициализирован")
        try:
            self.logger.info("Инициализация поисковика")
            self.theme_finder = ThemeFinder(self.data_manager)
            self.theme_finder.make_collection()
            self.logger.info("Система поиска готова")
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

        self.logger.info("Проверка расстояний у каждой темы")

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

        self.logger.info("Темы отфильтрованы")
        return filtered

    def sort_results(
        self,
        results: Dict[str, Any],
        mark_priority: Optional[int] = None,
        date_priority: Optional[int] = None,
        dist_priority: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Функция сортировки"""
        docs = results.get("documents", [[]])[0]
        dists = results.get("distances", [[]])[0]
        metas = results.get("metadatas", [[]])[0]

        if not docs:
            return results

        self.logger.info("Начало сортировки тем по критериям")

        data_to_sort = []
        for i in range(len(docs)):
            meta = metas[i]

            raw_mark = meta.get("rounded_final_grade", 0)
            try:
                mark = float(raw_mark) if raw_mark not in (None, "", "null") else 0.0
            except (ValueError, TypeError):
                mark = 0.0

            raw_date = str(meta.get("date_defence") or "")
            if len(raw_date) == 10 and "." in raw_date:
                parts = raw_date.split(".")
                sortable_date = f"{parts[2]}.{parts[1]}.{parts[0]}"
            else:
                sortable_date = "0000.00.00"

            data_to_sort.append(
                {
                    "doc": docs[i],
                    "dist": dists[i],
                    "meta": meta,
                    "mark": mark,
                    "date": sortable_date,
                }
            )

        p_map = {}
        if mark_priority is not None:
            p_map["mark"] = mark_priority
        if date_priority is not None:
            p_map["date"] = date_priority
        if dist_priority is not None:
            p_map["dist"] = dist_priority

        if "dist" not in p_map:
            p_map["dist"] = 999

        active_criteria = sorted(p_map.keys(), key=lambda x: p_map[x])

        def get_sorting_tuple(item):
            values = []
            for criterion in active_criteria:
                if criterion == "mark":
                    values.append(item["mark"])
                elif criterion == "date":
                    values.append(item["date"])
                elif criterion == "dist":
                    values.append(-item["dist"])
            return tuple(values)

        if active_criteria:
            data_to_sort.sort(key=get_sorting_tuple, reverse=True)
            self.logger.info(f"Темы отсортированы по цепочке: {active_criteria}")

        return {
            "documents": [[item["doc"] for item in data_to_sort]],
            "distances": [[item["dist"] for item in data_to_sort]],
            "metadatas": [[item["meta"] for item in data_to_sort]],
        }

    def search_relevant(
        self,
        query: str,
        n_results: int = 7,
        max_distance: float = MAX_DISTANCE,
        is_used: bool = False,
        curator: Optional[str] = None,
        examiner: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Функция поиска релевантных тем"""
        if self.theme_finder is None:
            raise RuntimeError("Поиск не инициализирован")
        self.logger.info("Начало поиска тем")

        raw_results = self.theme_finder.search(
            query,
            n_results=n_results,
            is_used=is_used,
            curator=curator,
            examiner=examiner,
        )
        self.logger.info("Ранжирование ием по релевантности")

        return self.filter_results_by_distance(raw_results, max_distance)

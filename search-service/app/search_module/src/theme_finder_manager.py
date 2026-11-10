import logging
from typing import Any, Dict, Optional

from app.search_module.src.data_manager import DataManager
from app.search_module.src.loader import BaseLoader
from app.search_module.src.saver import BaseSaver
from app.search_module.src.theme_finder import ThemeFinder
from app.core.config import settings

logger = logging.getLogger(__name__)


class ThemeFinderManager:
    def __init__(self, loader: BaseLoader, saver: BaseSaver) -> None:
        self.loader = loader
        self.saver = saver
        self.data_manager: Optional[DataManager] = None
        self.theme_finder: Optional[ThemeFinder] = None

    def process_data_from_json(
        self, json_data: str, path_to_data: str = settings.PATH_TO_TEST_JSON
    ) -> None:
        logger.info("Начало обработки новых данных")
        if not self.data_manager:
            self.data_manager = DataManager(self.loader)
        self.saver.save(path_to_data, json_data)
        logger.info(f"Данные сохранены в файл: {path_to_data}")
        self.data_manager.load(path_to_data)
        logger.info("Данные загружены в DataManager")
        self.prepare_search()

    def prepare_search(self) -> None:
        if self.data_manager is None:
            raise RuntimeError("DataManager не инициализирован")
        try:
            logger.info("Инициализация поисковика")
            self.theme_finder = ThemeFinder(self.data_manager)
            self.theme_finder.make_collection()
            logger.info("Система поиска готова к работе")
        except Exception as e:
            logger.error(f"Не удалось инициализировать поиск: {e}")
            raise RuntimeError(f"Не удалось инициализировать поиск: {e}")

    def search(self, query: str, n_results: int = 4) -> Dict[str, Any]:
        if self.theme_finder is None:
            raise RuntimeError("Поиск не готов")
        return self.theme_finder.search(query, n_results=n_results)

    def filter_results_by_distance(
        self, results: Dict[str, Any], max_distance: float = settings.MAX_DISTANCE
    ) -> Dict[str, Any]:
        logger.info("Проверка расстояний у каждой темы")
        docs = results.get("documents", [[]])[0]
        dists = results.get("distances", [[]])[0]
        metas = results.get("metadatas", [[]])[0]

        filtered = {"documents": [[]], "distances": [[]], "metadatas": [[]]}
        for doc, dist, meta in zip(docs, dists, metas):
            if dist <= max_distance:
                filtered["documents"][0].append(doc)
                filtered["distances"][0].append(dist)
                filtered["metadatas"][0].append(meta)

        logger.info("Темы отфильтрованы")
        return filtered

    def _deduplicate_by_original_id(self, results: Dict[str, Any]) -> Dict[str, Any]:
        docs = results.get("documents", [[]])[0]
        dists = results.get("distances", [[]])[0]
        metas = results.get("metadatas", [[]])[0]

        best: Dict[str, tuple] = {}
        for doc, dist, meta in zip(docs, dists, metas):
            key = meta.get("original_id") or meta.get("id") or doc
            if key not in best or dist < best[key][0]:
                best[key] = (dist, doc, meta)

        ordered = sorted(best.values(), key=lambda x: x[0])

        out = {"documents": [[]], "distances": [[]], "metadatas": [[]]}
        for dist, doc, meta in ordered:
            out["documents"][0].append(doc)
            out["distances"][0].append(dist)
            out["metadatas"][0].append(meta)

        logger.info(f"После дедупликации: {len(out['documents'][0])} уникальных тем")
        return out

    def _sort_results(
        self, results: Dict[str, Any], sort_by: Optional[str]
    ) -> Dict[str, Any]:
        if not sort_by or sort_by == "relevance":
            return results

        docs = results.get("documents", [[]])[0]
        dists = results.get("distances", [[]])[0]
        metas = results.get("metadatas", [[]])[0]

        items = list(zip(docs, dists, metas))

        if sort_by == "grade":

            def grade_key(item):
                grade = item[2].get("rounded_final_grade", "")
                try:
                    return -float(grade)
                except (ValueError, TypeError):
                    return 0

            items.sort(key=grade_key)
        elif sort_by == "date":

            def date_key(item):
                return item[2].get("date_defence", "")

            items.sort(key=date_key, reverse=True)

        out = {"documents": [[]], "distances": [[]], "metadatas": [[]]}
        for doc, dist, meta in items:
            out["documents"][0].append(doc)
            out["distances"][0].append(dist)
            out["metadatas"][0].append(meta)

        logger.info(f"Результаты отсортированы по: {sort_by}")
        return out

    def search_relevant(
        self,
        query: str,
        n_results: int = 7,
        max_distance: float = settings.MAX_DISTANCE,
        is_used: Optional[bool] = False,
        examiner: Optional[str] = None,
        sort_by: Optional[str] = "relevance",
    ) -> Dict[str, Any]:
        if self.theme_finder is None:
            raise RuntimeError("Поиск не инициализирован")

        logger.info("Начало поиска тем")

        raw_results = self.theme_finder.search(
            query,
            n_results=n_results,
            is_used=is_used,
            examiner=examiner,
        )
        logger.info("Фильтрация по расстоянию")

        filtered = self.filter_results_by_distance(raw_results, max_distance)
        filtered = self._deduplicate_by_original_id(filtered)
        filtered = self._sort_results(filtered, sort_by)

        return filtered

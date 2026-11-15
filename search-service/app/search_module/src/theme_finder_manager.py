import logging
from typing import Any, Dict, Optional

from app.search_module.src.data_manager import DataManager
from app.search_module.src.theme_finder import ThemeFinder
from app.core.config import settings

logger = logging.getLogger(__name__)


class ThemeFinderManager:
    def __init__(self) -> None:
        self.data_manager: Optional[DataManager] = None
        self.theme_finder: Optional[ThemeFinder] = None

    def init_from_db(self) -> None:
        if not self.data_manager:
            self.data_manager = DataManager()

        if self.data_manager.collection.count() > 0:
            self.data_manager.load_from_collection()
            self.theme_finder = ThemeFinder(self.data_manager)
            logger.info(f"Search engine restored from ChromaDB ({self.data_manager.collection.count()} vectors)")
        else:
            logger.warning("ChromaDB is empty. Waiting for POST /update-data")

    def process_data(self, data: list[dict]) -> None:
        logger.info(f"Processing {len(data)} records from data-storage")
        if not self.data_manager:
            self.data_manager = DataManager()
        self.data_manager.set_data(data)
        self.prepare_search()

    def prepare_search(self) -> None:
        if self.data_manager is None or not self.data_manager.data:
            raise RuntimeError("DataManager is empty")
        logger.info("Initializing search engine")
        self.theme_finder = ThemeFinder(self.data_manager)
        self.theme_finder.make_collection()
        logger.info("Search engine is ready")

    def search_relevant(
            self,
            query: str,
            n_results: int = 7,
            max_distance: float = settings.MAX_DISTANCE,
            is_used: Optional[bool] = None,
            examiner: Optional[str] = None,
            sort_by: Optional[str] = "relevance",
    ) -> Dict[str, Any]:
        if self.theme_finder is None:
            raise RuntimeError("Search engine is not initialized")

        raw_results = self.theme_finder.search(
            query, n_results=n_results, is_used=is_used, examiner=examiner
        )
        filtered = self.filter_results_by_distance(raw_results, max_distance)
        filtered = self._deduplicate_by_original_id(filtered)
        filtered = self._sort_results(filtered, sort_by)
        return filtered

    def filter_results_by_distance(
            self, results: Dict[str, Any], max_distance: float = settings.MAX_DISTANCE
    ) -> Dict[str, Any]:
        docs = results.get("documents", [[]])[0]
        dists = results.get("distances", [[]])[0]
        metas = results.get("metadatas", [[]])[0]

        filtered = {"documents": [[]], "distances": [[]], "metadatas": [[]]}
        for doc, dist, meta in zip(docs, dists, metas):
            if dist <= max_distance:
                filtered["documents"][0].append(doc)
                filtered["distances"][0].append(dist)
                filtered["metadatas"][0].append(meta)
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
        return out
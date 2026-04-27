import logging
from typing import Dict, Any, Optional

from search_module.src.data_manager import DataManager
from search_module.src.loader import BaseLoader
from search_module.src.saver import BaseSaver
from search_module.src.settings import PATH_TO_TEST_JSON
from search_module.src.theme_finder import ThemeFinder
from table_api.storage import Storage


class ThemeFinderManager:
    def __init__(self, loader: BaseLoader, saver: BaseSaver, logger: Optional[logging.Logger] = None):
        self.loader = loader
        self.saver = saver
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.data_manager: Optional[DataManager] = None
        self.theme_finder: Optional[ThemeFinder] = None
        self.storage = Storage()

    def process_data(self, path_to_data: str = PATH_TO_TEST_JSON) -> None:
        self.logger.info("Создание DataManager")
        self.data_manager = DataManager(self.loader)

        self.logger.info("Получение уникальных тем из Storage")
        
        unique_topics_json = self.storage.get_unique_topics()

        self.logger.info(f"Сохранение данных в {path_to_data}")
        self.saver.save(path_to_data, unique_topics_json)

        self.logger.info("Загрузка данных в DataManager")
        self.data_manager.load(path_to_data)
        self.logger.info("Данные загружены")

    def filter_by_occupancy(self, need_filter: bool) -> None:
        if self.data_manager is None:
            self.logger.error("DataManager не инициализирован")
            raise RuntimeError("DataManager не инициализирован")
        if need_filter:
            self.data_manager.filter_by_occupancy()
            self.logger.info("Темы отфильтрованы по занятости")
        else:
            self.logger.info("Фильтрация не требуется")

    def prepare_search(self) -> None:
        if self.data_manager is None:
            self.logger.error("Невозможно подготовить поиск")
            raise RuntimeError("DataManager не инициализирован")
        try:
            self.theme_finder = ThemeFinder(self.data_manager)
            self.theme_finder.make_collection()
            self.logger.info("Система готова к поиску")
        except Exception as e:
            self.logger.error(f"Ошибка при создании поискового индекса: {e}")
            raise RuntimeError(f"Не удалось инициализировать поиск: {e}")

    def search(self, query: str, n_results: int = 4) -> Dict[str, Any]:
        if self.theme_finder is None:
            self.logger.warning("Поиск не инициализирован")
            raise RuntimeError("Поиск не готов")
        return self.theme_finder.search(query, n_results=n_results)
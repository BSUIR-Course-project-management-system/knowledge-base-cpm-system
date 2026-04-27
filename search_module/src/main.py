import logging
import sys
from search_module.src.data_manager import DataManager
from search_module.src.loader import JsonLoader
from search_module.src.saver import JsonSaver
from search_module.src.settings import PATH_TO_TEST_JSON, LOG_FILE
from search_module.src.theme_finder import ThemeFinder
from table_api.storage import Storage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
    force=True,
)

def main() -> None:
    logging.info("Попытка создать загрузчик данных")
    loader = JsonLoader()
    logging.info("Загрузчик данных создан")

    logging.info("Попытка создания менеджера данных")
    data_manager = DataManager(loader)
    logging.info("Менеджер данных создан")


    logging.info("Попытка создания хранилища")
    storage = Storage()
    logging.info("Хранилище данных создан")

    str_json = storage.get_unique_topics()

    logging.info("Попытка создать загрузчик данных")
    saver = JsonSaver()
    logging.info("Загрузчик данных создан")

    saver.save(PATH_TO_TEST_JSON, str_json)
    logging.info("Данные сохранены")

    data_manager.load(PATH_TO_TEST_JSON)
    logging.info("Данные загружены в менеджер")
    
    is_free_theme = input(
        "Вы  хотите выбрать тему или просмотреть все подходящие темы(y/n)? "
    )
    if is_free_theme.lower() == "y":
        data_manager.filter_by_occupancy()
        logging.info("Темы отобраны")

    theme_finder = ThemeFinder(data_manager)
    theme_finder.make_collection()

    logging.info("Система готова к поиску.")

    while True:
        query = input("\nВведите запрос (или 'exit'): ").strip()
        if query.lower() == "exit":
            break
        if not query:
            continue

        results = theme_finder.search(query, n_results=4)

        docs = results["documents"][0]
        dists = results["distances"][0]
        metas = results["metadatas"][0]

        for i, (doc, dist, meta) in enumerate(zip(docs, dists, metas)):
            cat = meta.get("cat", "N/A") if meta else "N/A"
            logging.info(f"  {i + 1}. '{doc}' (дистанция: {dist:.3f}) [{cat}]")


if __name__ == "__main__":
    main()

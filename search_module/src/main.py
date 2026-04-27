import logging
from recomendation_module import RecommendationModule
from search_module.src.data_manager import DataManager
from search_module.src.loader import JsonLoader
from search_module.src.saver import JsonSaver
from search_module.src.settings import PATH_TO_TEST_JSON, LOG_FILE
from search_module.src.theme_finder import ThemeFinder
from table_api.storage import Storage

LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

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
    recommendation_module = RecommendationModule(theme_finder.model)

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
        recommendations = recommendation_module.build_recommendations(
            query=query,
            documents=docs,
            distances=dists,
            metadatas=metas,
        )

        logging.info("Результаты для запроса '%s':", query)
        if not recommendations:
            logging.info("  Подходящие темы не найдены.")
            continue

        for i, recommendation in enumerate(recommendations):
            meta = recommendation["metadata"]
            cat = meta.get("cat", "N/A") if meta else "N/A"
            dist = recommendation["distance"]
            dist_label = f"{dist:.3f}" if dist is not None else "N/A"
            logging.info(
                f"  {i + 1}. '{recommendation['document']}' (дистанция: {dist_label}) [{cat}]"
            )
            logging.info(f"     Объяснение: {recommendation['explanation']}")


if __name__ == "__main__":
    main()

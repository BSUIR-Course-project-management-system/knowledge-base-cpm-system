import logging
import sys

from recomendation_module import RecommendationModule
from search_module.src.loader import JsonLoader
from search_module.src.saver import JsonSaver
from search_module.src.settings import LOG_FILE, MAX_DISTANCE
from search_module.src.theme_finder_manager import ThemeFinderManager


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8")],
        force=True,
    )

    loader = JsonLoader()
    saver = JsonSaver()

    manager = ThemeFinderManager(
        loader, saver, logger=logging.getLogger("ThemeFinderManager")
    )

    try:
        manager.process_data()

        user_input = input(
            "Вы хотите выбрать тему или просмотреть все подходящие темы (y/n)? "
        ).strip()
        need_filter = user_input.lower() == "y"
        manager.filter_by_occupancy(need_filter)

        manager.prepare_search()
        recommendation_module = RecommendationModule(search_manager=manager)

        print("Recommendation module готов. Показываю темы вместе с объяснениями.")

        while True:
            query = input("\nВведите запрос (или 'exit'): ").strip()
            if query.lower() == "exit":
                break
            if not query:
                continue

            try:
                recommendations = recommendation_module.search_with_explanations(
                    query=query,
                    n_results=4,
                    max_distance=MAX_DISTANCE,
                )

                if not recommendations:
                    print("Ничего не найдено. Попробуйте переформулировать запрос.")
                    logging.info(
                        "Запрос '%s' не дал релевантных результатов (порог %s)",
                        query,
                        MAX_DISTANCE,
                    )
                    continue

                for index, recommendation in enumerate(recommendations, start=1):
                    document = recommendation["document"]
                    distance = recommendation["distance"]
                    metadata = recommendation["metadata"]
                    explanation = recommendation["explanation"]
                    category = metadata.get("cat", "N/A") if metadata else "N/A"
                    distance_text = (
                        f"{distance:.3f}" if distance is not None else "N/A"
                    )

                    print(
                        f"  {index}. '{document}' (расстояние: {distance_text}) [{category}]"
                    )
                    print(f"     Почему выбрана: {explanation}")

            except Exception as error:
                logging.error("Ошибка при демонстрации recommendation_module: %s", error)
                print("Произошла ошибка, попробуйте другой запрос.")

    except Exception as error:
        logging.error("Не удалось запустить recommendation_module: %s", error)
        print(f"Не удалось запустить recommendation_module: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()

import sys

from logger.logger import Logger
from recomendation_module import RecommendationModule
from recomendation_module.src.settings import RECOMMENDATION_MAIN_LOG_FILE
from search_module.src.loader import JsonLoader
from search_module.src.saver import JsonSaver
from search_module.src.settings import MAX_DISTANCE
from search_module.src.theme_finder_manager import ThemeFinderManager


def main() -> None:
    logger = Logger(str(RECOMMENDATION_MAIN_LOG_FILE), level="INFO")

    loader = JsonLoader()
    logger.info("Создан объект JsonLoader")

    saver = JsonSaver()
    logger.info("Создан объект JsonSaver")

    manager = ThemeFinderManager(loader, saver)
    logger.info("Инициализирован ThemeFinderManager")

    try:
        manager.process_data()
        logger.info("Данные получены и сохранены")

        manager.prepare_search()
        logger.info("Поиск подготовлен")

        recommendation_module = RecommendationModule(search_manager=manager)
        logger.info("Инициализирован RecommendationModule")

        print(
            "Recommendation module готов. "
            "Ранжирование пишется в recomendation_module/logs/search_ranking.log, "
            "описания тем пишутся в recomendation_module/logs/topic_descriptions.log."
        )

        while True:
            query = input("\nВведите запрос (или 'exit'): ").strip()
            if query.lower() == "exit":
                break
            if not query:
                continue

            try:
                user_input = input(
                    "Только свободные темы? (y - да, любая другая клавиша - нет): "
                )
                is_used = False if user_input.strip().lower() == "y" else None
                logger.info(f"Фильтр по занятости: {is_used}")

                curator_input = input(
                    "Введите имя куратора, либо нажмите Enter: "
                ).strip()
                curator_input = curator_input if curator_input else None
                logger.info(f"Фильтр по куратору: {curator_input}")

                examiner_input = input(
                    "Введите имя проверяющего, либо нажмите Enter: "
                ).strip()
                examiner_input = examiner_input if examiner_input else None
                logger.info(f"Фильтр по проверяющему: {examiner_input}")

                recommendations = recommendation_module.search_with_explanations(
                    query=query,
                    n_results=4,
                    max_distance=MAX_DISTANCE,
                    is_used=is_used,
                    curator=curator_input,
                    examiner=examiner_input,
                )

                if not recommendations:
                    print("Ничего не найдено. Попробуйте переформулировать запрос.")
                    logger.info(
                        f"Запрос '{query}' не дал релевантных результатов."
                    )
                    continue

                print("\nПодробные описания найденных тем:")
                for index, recommendation in enumerate(recommendations, start=1):
                    print(f"\n{index}.")
                    print(recommendation["topic_description_text"])

            except Exception as error:
                logger.error(
                    f"Ошибка при демонстрации recommendation_module: {error}"
                )
                print("Произошла ошибка, попробуйте другой запрос.")

    except Exception as error:
        logger.error(f"Не удалось запустить recommendation_module: {error}")
        print(f"Не удалось запустить recommendation_module: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()

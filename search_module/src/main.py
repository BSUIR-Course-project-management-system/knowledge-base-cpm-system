import sys

from logger.logger import Logger
from search_module.src.loader import JsonLoader
from search_module.src.saver import JsonSaver
from search_module.src.settings import LOG_FILE, MAX_DISTANCE
from search_module.src.theme_finder_manager import ThemeFinderManager
from search_module.src.utils import ConsoleThemePrinter, SortMenuPrinter


def main():
    logger = Logger(LOG_FILE, level="INFO")

    loader = JsonLoader()
    logger.info("Создан объект класса JsonLoader из файла")

    saver = JsonSaver()
    logger.info("Создан объект класса JsonSaver данных из файла")

    theme_printer = ConsoleThemePrinter()
    logger.info("Создан объект класса ConsoleThemePrinter данных из файла")

    menu_sort_printer = SortMenuPrinter()
    logger.info("Создан объект класса MenuSortPrinter данных из файла")

    manager = ThemeFinderManager(loader, saver)
    logger.info("Инициирован менеджер поиска тем")

    try:
        manager.process_data()
        logger.info("Данные успешно получены")

        manager.prepare_search()
        logger.info("Поиск инициирован")

        while True:
            query = input("\nВведите запрос (или 'exit'): ").strip()
            logger.info("Пользователь совершил ввод интересующих его тем")
            if query.lower() == "exit":
                break
            if not query:
                continue

            try:
                user_input = input(
                    "Только свободные темы? (y - да, любая другая клавиша - нет): "
                )
                is_used = not (user_input.strip().lower() == "y")
                logger.info(
                    f"Пользователь выбрал статус занятости тем, не занятые темы: {is_used}"
                )

                user_curator_input = input(
                    "Введите имя куратора, либо нажмите Enter: "
                ).strip()
                user_curator_input = user_curator_input if user_curator_input else None
                logger.info(f"Пользователь ввел имя куратора ({user_curator_input})")

                user_examiner_input = input(
                    "Введите имя проверяющего, либо нажмите Enter: "
                )
                user_examiner_input = (
                    user_examiner_input if user_examiner_input else None
                )
                logger.info(
                    f"Пользователь ввел имя проверяющего ({user_examiner_input})"
                )

                filtered = manager.search_relevant(
                    query,
                    n_results=4,
                    max_distance=MAX_DISTANCE,
                    is_used=is_used,
                    curator=user_curator_input,
                    examiner=user_examiner_input,
                )
                logger.info(
                    "Получен итоговый список тем отсортированный по релевантности тем"
                )
                theme_printer.print_themes(filtered)
                if len(filtered) > 1:
                    # while True:
                    #     menu_sort_printer.print_menu()
                    #     logger.info("Выведен список вариантов сортировки")
                    #     user_sort_input = input("Введите способ сортировки: ")
                    #     logger.info(f"Пользователь выбрал вариант сортировки({user_sort_input})")
                    #     match user_sort_input:
                    #         case "1":
                    #             filtered = manager.sort_results(filtered, mark_priority=1)
                    #             logger.info("Темы отсортированы по оценке за проект")
                    #         case "2":
                    #             filtered = manager.sort_results(filtered, date_priority=1)
                    #             logger.info("Темы отсортированы по дате сдачи")
                    #         case "3":
                    #             filtered = manager.sort_results(
                    #                 filtered, mark_priority=1, dist_priority=2
                    #             )
                    #             logger.info("Темы отсортированы по релевантности тем")
                    #         case _:
                    #             break
                    pass

            except Exception:
                print("Произошла ошибка, попробуйте другой запрос.")

    except (Exception, KeyboardInterrupt):
        print("Не удалось запустить поиск:")
        sys.exit(1)


if __name__ == "__main__":
    main()

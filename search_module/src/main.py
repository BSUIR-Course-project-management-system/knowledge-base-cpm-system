import sys

from logger.logger import Logger
from search_module.src.loader import JsonLoader
from search_module.src.saver import JsonSaver
from search_module.src.settings import MAIN_LOG_FILE, MAX_DISTANCE
from search_module.src.theme_finder_manager import ThemeFinderManager
from search_module.src.utils import ConsoleThemePrinter, SortMenuPrinter


def main():
    logger = Logger(MAIN_LOG_FILE, level="INFO")

    loader = JsonLoader()
    saver = JsonSaver()
    theme_printer = ConsoleThemePrinter()
    menu_sort_printer = SortMenuPrinter()

    manager = ThemeFinderManager(loader, saver)
    logger.info("Инициирован менеджер поиска тем")

    try:
        manager.process_data()
        logger.info("Данные успешно получены")

        manager.prepare_search()
        logger.info("Поиск инициирован")

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
                is_used = not (user_input.strip().lower() == "y")

                curator_input = input(
                    "Введите имя куратора, либо нажмите Enter: "
                ).strip()
                curator = curator_input if curator_input else None

                examiner_input = input(
                    "Введите имя проверяющего, либо нажмите Enter: "
                ).strip()
                examiner = examiner_input if examiner_input else None

                search_results = manager.search_relevant(
                    query,
                    n_results=60,
                    max_distance=MAX_DISTANCE,
                    is_used=is_used,
                    curator=curator,
                    examiner=examiner,
                )

                logger.info("Получен итоговый список тем от ChromaDB")

                if (
                    not search_results.get("documents")
                    or not search_results["documents"][0]
                ):
                    print("Темы не найдены.")
                    continue

                theme_printer.print_themes(search_results)

                if len(search_results["documents"][0]) > 1:
                    while True:
                        menu_sort_printer.print_menu()
                        user_sort_input = input(
                            "Введите способ сортировки (Enter для нового поиска): "
                        ).strip()

                        if not user_sort_input:
                            break

                        match user_sort_input:
                            case "1":
                                filtered = manager.sort_results(
                                    search_results, mark_priority=1
                                )
                                logger.info("Темы отсортированы по оценке")
                            case "2":
                                filtered = manager.sort_results(
                                    search_results, date_priority=1
                                )
                                logger.info("Темы отсортированы по дате")
                            case "3":
                                filtered = manager.sort_results(
                                    search_results, dist_priority=1
                                )
                                logger.info("Темы отсортированы по релевантности")
                            case _:
                                break

                        theme_printer.print_themes(filtered)

            except Exception as e:
                logger.error(f"Ошибка в процессе поиска: {e}")
                print("Произошла ошибка, попробуйте другой запрос.")

    except (Exception, KeyboardInterrupt):
        print("\nЗавершение работы поиска.")
        sys.exit(0)


if __name__ == "__main__":
    main()

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
                    "Только занятые темы? (y - да, n - нет, любая другая клавиша - нет фильтрации): "
                )
                if (
                    user_input.strip().lower() != "y"
                    and user_input.strip().lower() != "n"
                ):
                    is_used = None
                else:
                    is_used = user_input.strip().lower() == "y"

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
                    n_results=10,
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


            except Exception as e:
                logger.error(f"Ошибка в процессе поиска: {e}")
                print("Произошла ошибка, попробуйте другой запрос.")

    except (Exception, KeyboardInterrupt):
        print("\nЗавершение работы поиска.")
        sys.exit(0)


if __name__ == "__main__":
    main()
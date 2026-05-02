import sys

from search_module.src.loader import JsonLoader
from search_module.src.saver import JsonSaver
from search_module.src.settings import MAX_DISTANCE
from search_module.src.theme_finder_manager import ThemeFinderManager
from search_module.src.utils import ConsoleThemePrinter, SortMenuPrinter


def main():

    loader = JsonLoader()
    saver = JsonSaver()
    theme_printer = ConsoleThemePrinter()
    menu_sort_printer = SortMenuPrinter()

    manager = ThemeFinderManager(loader, saver)

    try:
        manager.process_data()

        manager.prepare_search()

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

                user_curator_input = input(
                    "Введите имя куратора, либо нажмите Enter: "
                ).strip()
                user_curator_input = user_curator_input if user_curator_input else None

                user_examiner_input = input(
                    "Введите имя проверяющего, либо нажмите Enter: "
                )
                user_examiner_input = (
                    user_examiner_input if user_examiner_input else None
                )

                filtered = manager.search_relevant(
                    query,
                    n_results=4,
                    max_distance=MAX_DISTANCE,
                    is_used=is_used,
                    curator=user_curator_input,
                    examiner=user_examiner_input,
                )

                theme_printer.print_themes(filtered)

                while True:
                    menu_sort_printer.print_menu()
                    user_sort_input = input("Введите способ сортировки: ")
                    match user_sort_input:
                        case "1":
                            filtered = manager.sort_results(filtered, mark_priority=1)
                        case "2":
                            filtered = manager.sort_results(filtered, date_priority=1)
                        case "3":
                            filtered = manager.sort_results(
                                filtered, mark_priority=1, dist_priority=2
                            )
                        case _:
                            break

            except Exception:
                print("Произошла ошибка, попробуйте другой запрос.")

    except (Exception, KeyboardInterrupt):
        print("Не удалось запустить поиск:")
        sys.exit(1)


if __name__ == "__main__":
    main()

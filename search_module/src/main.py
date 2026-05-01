import logging
import sys

from search_module.src.loader import JsonLoader
from search_module.src.saver import JsonSaver
from search_module.src.settings import LOG_FILE, MAX_DISTANCE
from search_module.src.theme_finder_manager import ThemeFinderManager


def main():

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
        need_filter = None
        try:
            user_input = int(
                input(
                    "Вы хотите просмотреть все подходящие темы или только свободные (1/2)? "
                )
            )
            need_filter = user_input == 2

        except ValueError:
            print("Некорректный ввод попробуйте еще раз!")

        manager.filter_by_occupancy(need_filter)

        manager.prepare_search()

        while True:
            query = input("\nВведите запрос (или 'exit'): ").strip()
            if query.lower() == "exit":
                break
            if not query:
                continue

            try:
                user_curator_input = input("Введите имя куратора, либо нажмите Enter: ").strip()
                user_curator_input = user_curator_input if user_curator_input else None
                
                user_examiner_input = input("Введите имя проверяющего, либо нажмите Enter")
                user_examiner_input = user_examiner_input if user_examiner_input else None

                filtered = manager.search_relevant(
                    query, n_results=4, max_distance=MAX_DISTANCE, curator = user_curator_input, examiner=user_examiner_input
                )

                docs = filtered["documents"][0]
                dists = filtered["distances"][0]
                metas = filtered["metadatas"][0]

                if not docs:
                    print("Ничего не найдено. Попробуйте переформулировать запрос.")
                    logging.info(
                        f"Запрос '{query}' не дал релевантных результатов (порог {MAX_DISTANCE})"
                    )
                else:
                    for i, (doc, dist, meta) in enumerate(
                        zip(docs, dists, metas), start=1
                    ):
                        cat = meta.get("cat", "N/A") if meta else "N/A"
                        print(f"  {i}. '{doc}' (расстояние: {dist:.3f}) [{cat}]")

            except Exception as e:
                logging.error(f"Ошибка при поиске: {e}")
                print("Произошла ошибка, попробуйте другой запрос.")

    except Exception as e:
        logging.error(f"Критическая ошибка при инициализации: {e}")
        print(f"Не удалось запустить поиск: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

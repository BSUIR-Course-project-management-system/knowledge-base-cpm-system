import logging
import sys
from search_module.src.loader import JsonLoader
from search_module.src.saver import JsonSaver
from search_module.src.settings import LOG_FILE
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

    manager = ThemeFinderManager(loader, saver, logger=logging.getLogger("ThemeFinderManager"))

    try:

        manager.process_data()

        user_input = input("Вы хотите выбрать тему или просмотреть все подходящие темы (y/n)? ").strip()
        need_filter = (user_input.lower() == "y")
        manager.filter_by_occupancy(need_filter)

        manager.prepare_search()

        while True:
            query = input("\nВведите запрос (или 'exit'): ").strip()
            if query.lower() == "exit":
                break
            if not query:
                continue

            try:
                results = manager.search(query, n_results=4)
                docs = results["documents"][0]
                dists = results["distances"][0]
                metas = results["metadatas"][0]

                for i, (doc, dist, meta) in enumerate(zip(docs, dists, metas), start=1):
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
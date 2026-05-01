import sys

from search_module.src.loader import JsonLoader
from search_module.src.saver import JsonSaver
from search_module.src.settings import MAX_DISTANCE
from search_module.src.theme_finder_manager import ThemeFinderManager


def main():

    loader = JsonLoader()
    saver = JsonSaver()

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

                docs = filtered["documents"][0]
                dists = filtered["distances"][0]
                metas = filtered["metadatas"][0]

                if not docs:
                    print("Ничего не найдено. Попробуйте переформулировать запрос.")
                else:
                    for i, (doc, dist, meta) in enumerate(
                        zip(docs, dists, metas), start=1
                    ):
                        cat = meta.get("cat", "N/A") if meta else "N/A"
                        print(f"  {i}. '{doc}' (расстояние: {dist:.3f}) [{cat}]")

            except Exception:
                print("Произошла ошибка, попробуйте другой запрос.")

    except (Exception, KeyboardInterrupt):
        print("Не удалось запустить поиск:")
        sys.exit(1)


if __name__ == "__main__":
    main()

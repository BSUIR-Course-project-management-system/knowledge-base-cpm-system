from search_module.src.data_manager import DataManager
from search_module.src.loader import JsonLoader
from search_module.src.saver import JsonSaver
from search_module.src.settings import PATH_TO_TEST_JSON
from search_module.src.theme_finder import ThemeFinder
from table_api.storage import Storage


def main() -> None:
    loader = JsonLoader()
    data_manager = DataManager(loader)

    storage = Storage()
    str_json = storage.get_unique_topics()

    saver = JsonSaver()

    saver.save(PATH_TO_TEST_JSON, str_json)

    # with open(PATH_TO_TEST_JSON, "w", encoding="utf-8") as f:
    #     f.write(str_json)

    data_manager.load(PATH_TO_TEST_JSON)

    is_free_theme = input(
        "Вы  хотите выбрать тему или просмотреть все подходящие темы(y/n)? "
    )
    if is_free_theme.lower() == "y":
        data_manager.filter_by_occupancy()
        print("Темы отобраны")

    theme_finder = ThemeFinder(data_manager)
    theme_finder.make_collection()

    print("Система готова к поиску.")

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

        for i, (doc, dist, meta) in enumerate(zip(docs, dists, metas)):
            cat = meta.get("cat", "N/A") if meta else "N/A"
            print(f"  {i + 1}. '{doc}' (дистанция: {dist:.3f}) [{cat}]")


if __name__ == "__main__":
    main()

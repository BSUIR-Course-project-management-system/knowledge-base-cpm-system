import os
import logging
import chromadb
from sentence_transformers import SentenceTransformer

from search_module.src.settings import PATH_TO_MODEL, PATH_TO_CHROMA_DB, PATH_TO_TEST_JSON
from search_module.src.loader import JsonLoader, BaseLoader
from search_module.src.theme_finder import ThemeFinder
from search_module.src.data_manager import DataManager


def main():
    loader = JsonLoader()
    data_manager = DataManager(loader)

    data_manager.load(PATH_TO_TEST_JSON)
    theme_finder_init = ThemeFinder(data_manager)
    theme_finder_init.make_collection()

    theme_finder = ThemeFinder(data_manager)
    print("Система готова к поиску.")

    while True:
        query = input("\nВведите запрос (или 'exit'): ").strip()
        if query.lower() == 'exit':
            break
        if not query:
            continue

        results = theme_finder.search(query, n_results=4)

        docs = results['documents'][0]
        dists = results['distances'][0]
        metas = results['metadatas'][0]

        for i, (doc, dist, meta) in enumerate(zip(docs, dists, metas)):
            cat = meta.get('cat', 'N/A') if meta else 'N/A'
            print(f"  {i + 1}. '{doc}' (дистанция: {dist:.3f}) [{cat}]")


if __name__ == "__main__":
    main()

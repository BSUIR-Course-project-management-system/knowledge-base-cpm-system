import json
import os
import logging
import transformers
import chromadb
from sentence_transformers import SentenceTransformer
from settings import PATH_TO_MODEL, PATH_TO_CHROMA_DB
from loader import JsonLoader

transformers.logging.set_verbosity_error()
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
os.environ["TOKENIZERS_PARALLELISM"] = "false"

model = SentenceTransformer(PATH_TO_MODEL)

if not os.path.exists('data.json'):
    data = [
        {"id": "1", "text": "C++ backend разработка API серверов", "metadata": {"cat": "tech"}},
        {"id": "2", "text": "Python ChromaDB векторный поиск", "metadata": {"cat": "tech"}},
        {"id": "3", "text": "Machine Learning алгоритмы KNN", "metadata": {"cat": "ml"}},
        {"id": "4", "text": "PostgreSQL оптимизация запросов", "metadata": {"cat": "db"}},
        {"id": "5", "text": "Программирование на C++ для высоконагруженных систем", "metadata": {"cat": "tech"}},
        {"id": "6", "text": "Современное программирование: Python и автоматизация", "metadata": {"cat": "tech"}}
    ]
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

client = chromadb.PersistentClient(path=PATH_TO_CHROMA_DB)
collection = client.get_or_create_collection(name="my_vectors")

loader = JsonLoader()
data = loader.load('data.json')

texts = [item['text'] for item in data]
embeddings = model.encode(texts, show_progress_bar=False).tolist()
ids = [item['id'] for item in data]
metadatas = [item['metadata'] for item in data]

collection.add(embeddings=embeddings, documents=texts, metadatas=metadatas, ids=ids)

def apply_filter(query):
    query_lower = query.lower()
    if "c++" in query_lower or "python" in query_lower:
        return {"cat": "tech"}

    return None

while True:
    query = input("\nВведите запрос (или 'exit'): ").strip()
    if query.lower() == 'exit':
        break

    query_emb = model.encode([query], show_progress_bar=False).tolist()
    results = collection.query(
        query_embeddings=query_emb,
        n_results=4,
        where=apply_filter(query)
    )

    docs = results['documents'][0]
    dists = results['distances'][0]
    metas = results['metadatas'][0]



    for i, (doc, dist, meta) in enumerate(zip(docs, dists, metas)):
        if i >= 3:
            break
        print(f"  {i + 1}. '{doc}' (дистанция: {dist:.3f}) [{meta['cat']}]")
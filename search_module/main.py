import json
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from settings import *
import os

model_path = PATH_TO_MODEL
model = SentenceTransformer(model_path)

if not os.path.exists('data.json'):
    data = [
        {"id": "1", "text": "C++ backend разработка API серверов", "metadata": {"cat": "tech"}},
        {"id": "2", "text": "Python ChromaDB векторный поиск", "metadata": {"cat": "tech"}},
        {"id": "3", "text": "Machine Learning алгоритмы KNN", "metadata": {"cat": "ml"}},
        {"id": "4", "text": "PostgreSQL оптимизация запросов", "metadata": {"cat": "db"}}
    ]
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

client = chromadb.PersistentClient(path=PATH_TO_CHROMA_DB)
collection = client.get_or_create_collection(name="my_vectors")

with open('data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

texts = [item['text'] for item in data]
embeddings = model.encode(texts).tolist()
ids = [item['id'] for item in data]
metadatas = [item['metadata'] for item in data]

collection.add(embeddings=embeddings, documents=texts, metadatas=metadatas, ids=ids)

while True:
    query = input("\n Введите запрос (или 'exit'): ").strip()
    if query.lower() == 'exit':
        break

    query_emb = model.encode([query]).tolist()
    results = collection.query(
        query_embeddings=query_emb,
        n_results=3,
        where={"cat": "tech"} if "c++" in query.lower() or "python" in query.lower() else None
    )

    for i, (doc, dist, meta) in enumerate(zip(
            results['documents'][0],
            results['distances'][0],
            results['metadatas'][0]
    )):
        print(f"  {i + 1}. '{doc}' (дистанция: {dist:.3f}) [{meta['cat']}]")
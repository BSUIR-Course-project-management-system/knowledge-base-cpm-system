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

client = chromadb.PersistentClient(path=PATH_TO_CHROMA_DB)
collection = client.get_or_create_collection(name="my_vectors")

loader = JsonLoader()
data = loader.load('data.json')

texts = [item['text'] for item in data]
embeddings = model.encode(texts, show_progress_bar=False).tolist()
ids = [item['id'] for item in data]
metadatas = [item['metadata'] for item in data]

collection.add(embeddings=embeddings, documents=texts, metadatas=metadatas, ids=ids)

while True:
    query = input("\nВведите запрос (или 'exit'): ").strip()
    if query.lower() == 'exit':
        break

    query_emb = model.encode([query], show_progress_bar=False).tolist()
    results = collection.query(
        query_embeddings=query_emb,
        n_results=4,
    )

    docs = results['documents'][0]
    dists = results['distances'][0]
    metas = results['metadatas'][0]



    for i, (doc, dist, meta) in enumerate(zip(docs, dists, metas)):
        if i >= 4:
            break
        print(f"  {i + 1}. '{doc}' (дистанция: {dist:.3f}) [{meta['cat']}]")
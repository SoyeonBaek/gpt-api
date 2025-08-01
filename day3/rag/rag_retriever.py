import numpy as np
from pymongo import MongoClient
from openai import OpenAI

with open('api-key', 'r') as f:
    API_KEY = f.read().strip()

client = OpenAI(api_key=API_KEY)


mongo_client = MongoClient("mongodb://localhost:27017")
collection = mongo_client.rag.documents


def cosine_sim(a, b): 
    a, b = np.array(a), np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def embed_text(text: str):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

def search_relevant_docs(query: str, top_k=3):
    q_emb = embed_text(query)
    docs = []
    for doc in collection.find():
        sim = cosine_sim(q_emb, doc["embedding"])
        docs.append((sim, doc["text"]))
    docs.sort(reverse=True)
    return [d[1] for d in docs[:top_k]]


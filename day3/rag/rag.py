from rag_retriever import *
import os
from openai import OpenAI

with open('api-key', 'r') as f:
    API_KEY = f.read().strip()

client = OpenAI(api_key=API_KEY)

def rag_response(message: str) -> str:
  docs = search_relevant_docs(message)
  context = "\n---\n".join(docs)

  completion = client.chat.completions.create(
    model="gpt-4.1",
    messages=[
      {"role": "system", "content": "You are a helpful assistant using provided documents."},
      {"role": "user", "content": f"Refer to the documents below and answer the question.\n\nDocuments:\n{context}\n\nQuestion:     {message}"}
    ]
  )
  return completion.choices[0].message.content


if __name__ == "__main__":
    
    while True:
        query = input("\n질문을 입력하세요 (종료하려면 'exit'): ")
        if query.lower() == "exit":
            break
        answer = rag_response(query)
        print("\nGPT 응답:\n", answer)


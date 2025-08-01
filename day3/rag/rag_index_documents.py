import os
from openai import OpenAI
from pymongo import MongoClient
from datetime import datetime

with open('api-key', 'r') as f:
    API_KEY = f.read().strip()

EMBEDDING_MODEL = "text-embedding-3-small"

client = OpenAI(api_key=API_KEY)

mongo_client = MongoClient("mongodb://localhost:27017")
collection = mongo_client.rag.documents  # DB: rag, Collection: documents

# 텍스트 임베딩 함수 
def embed_text(text: str):
    try:
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"[ERROR] OpenAI 임베딩 실패: {e}")
        return None

# 텍스트 분할 함수 (기본 문장 기준, 최대 토큰 수로 나눔)
def split_text(text, max_tokens=300):
    sentences = text.split(". ")
    chunks, chunk = [], []
    count = lambda x: len(x.split())

    for s in sentences:
        chunk.append(s)
        if count(" ".join(chunk)) > max_tokens:
            chunks.append(" ".join(chunk))
            chunk = []
    if chunk:
        chunks.append(" ".join(chunk))
    return chunks

# 문서 처리 + 로그 출력
def process_docs(folder="./stories"):
    print(f"[START] 문서 폴더: {folder}")
    for filename in os.listdir(folder):
        if not filename.endswith(".txt"):
            continue
        filepath = os.path.join(folder, filename)
        print(f"[INFO] 파일 처리 중: {filename}")

        try:
            with open(filepath, encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            print(f"[ERROR] 파일 읽기 실패: {e}")
            continue

        chunks = split_text(text)
        print(f"[INFO] 총 {len(chunks)}개 청크 생성됨")

        for idx, chunk in enumerate(chunks):
            print(f"[INFO] ➤ 청크 {idx+1}/{len(chunks)} 임베딩 중...")
            embedding = embed_text(chunk)
            if embedding:
                collection.insert_one({
                    "text": chunk,
                    "embedding": embedding,
                    "source": filename,
                    "timestamp": datetime.utcnow()
                })
                print(f"[OK] MongoDB 저장 완료")
            else:
                print(f"[SKIP] 임베딩 실패 → 저장 생략")

    print(f"[DONE] 모든 문서 처리 완료.")

# 실행 시점
if __name__ == "__main__":
    process_docs()


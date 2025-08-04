from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from typing import Dict
from datetime import datetime
import uvicorn
import json
import base64
from openai import OpenAI
import asyncio
import os
from PIL import Image
from io import BytesIO
from urllib.request import urlopen
import json
from pydantic import BaseModel


app = FastAPI()

with open('../../api-key', 'r') as f:
  API_KEY = f.read().strip()

client = OpenAI(api_key=API_KEY)

origins = ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TextRequest(BaseModel):
    text: str

#class Correction(BaseModel):
#    wrong: str
#    correct: str
#    start: int
#    end: int
#
#class CorrectionResponse(BaseModel):
#    original: str
#    corrections: list[Correction]

def ask_gpt_for_corrections(text: str) -> dict:
    prompt = f"""너는 맞춤법 검사기야. 다음 문장에서 틀린 부분을 찾아서 JSON 형식으로 교정해줘.

문장: "{text}"

형식:
{{
  "original": "문장 그대로",
  "corrections": [
    {{
      "wrong": "틀린 단어",
      "correct": "교정된 단어",
      "start": 시작 인덱스 (0부터),
      "end": 끝 인덱스 (exclusive)
    }}
  ]
}}

오직 JSON으로만 응답해줘."""

    completion = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}]
    )

    return json.loads(completion.choices[0].message.content)

@app.post("/spellcheck")
#, response_model=CorrectionResponse)
def spellcheck(req: TextRequest):
    try:
        result = ask_gpt_for_corrections(req.text)
        print(result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("backend:app", host="0.0.0.0", port=8000, reload=True)


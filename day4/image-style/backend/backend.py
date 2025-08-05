from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import uvicorn
import json
import base64
from openai import OpenAI
import os
from PIL import Image
from urllib.request import urlopen
import json
from pydantic import BaseModel
from fastapi.responses import FileResponse
import shutil
import uuid
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
import io
from pathlib import Path
import tempfile


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

def save_temp_file(upload_file):
    try:
        extension = os.path.splitext(upload_file.filename)[1]
        if not extension:
            extension = ".png"
        temp_filename = f"/tmp/{uuid.uuid4().hex}{extension}"
        with open(temp_filename, "wb") as f:
            content = upload_file.file.read()
            print(f"✅ 저장 중: {temp_filename}, 크기: {len(content)} bytes")
            f.write(content)
        return temp_filename
    except Exception as e:
        print("❌ 파일 저장 중 에러:", e)
        raise

def resize_image_to_1024(path):
    try:
        img = Image.open(path).convert("RGBA")
        img = img.resize((1024, 1024))
        img.save(path)
        print(f"🔄 리사이즈 완료: {path}")
    except Exception as e:
        print("❌ 리사이즈 중 에러:", e)
        raise

@app.post("/stylize")
async def stylize(
    image: UploadFile = File(...),
    mask: UploadFile = File(...),
    prompt: str = Form(...),
):
    try:
        print(f"📦 이미지 파일: {image.filename}")
        print(f"📦 마스크 파일: {mask.filename}")
        print(f"🧠 프롬프트: {prompt}")

        image_path = save_temp_file(image)
        mask_path = save_temp_file(mask)

        resize_image_to_1024(image_path)
        resize_image_to_1024(mask_path)

        response = client.images.edit(
            model="dall-e-2",
            image=open(image_path, "rb"),
            mask=open(mask_path, "rb"),
            prompt=prompt,
            n=1,
            size="1024x1024",
            response_format="url"
        )
        print("✅ 응답 도착")
        return JSONResponse(content={"url": response.data[0].url})

    except Exception as e:
        print("❌ 에러 발생:", e)
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    uvicorn.run("backend:app", host="0.0.0.0", port=8000, reload=True)


from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from typing import Dict
from datetime import datetime
import uvicorn
import json
import base64
from openai import AsyncOpenAI
import asyncio
import os
from PIL import Image
from io import BytesIO
from urllib.request import urlopen
from pydub import AudioSegment

app = FastAPI()

with open('api-key', 'r') as f:
  API_KEY = f.read().strip()

client = AsyncOpenAI(api_key=API_KEY)

origins = ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

mongo_client = MongoClient("mongodb://localhost:27017")
db = mongo_client.chat_db
messages_collection = db.messages

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, nickname: str):
        await websocket.accept()
        self.active_connections[nickname] = websocket

    def disconnect(self, nickname: str):
        self.active_connections.pop(nickname, None)

    async def broadcast(self, message: dict):
        for connection in self.active_connections.values():
            await connection.send_json(message)

manager = ConnectionManager()

async def chatbot_response(message: str) -> str:
    past_messages = list(messages_collection.find().sort("timestamp", -1).limit(30))[::-1]
    history = []
    for msg in past_messages:
        history.append({"role": msg["role"], "content": msg["message"]})

    completion = await client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": "You are a helpful assistant"},
            *history,
            {"role": "user", "content": message}
        ]
    )
    return completion.choices[0].message.content

async def handle_chatbot(data, nickname):
    query = data.strip()[len("@chatbot"):].strip()
    reply = await chatbot_response(query)

    messages_collection.insert_one({
        "nickname": "chatbot",
        "role": "assistant",
        "message": reply,
        "timestamp": datetime.utcnow().isoformat()
    })

    await manager.broadcast({
        "type": "text",
        "nickname": "chatbot",
        "message": reply,
        "timestamp": datetime.utcnow().isoformat()
    })

async def handle_image_prompt(prompt: str):
    response = await client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        n=1,
        size="1024x1024",
    )
    image_url = response.data[0].url

    image_bytes = urlopen(image_url).read()
    filename = f"images/generated_{datetime.utcnow().timestamp()}.png"
    os.makedirs("images", exist_ok=True)
    with open(filename, "wb") as f:
        f.write(image_bytes)

    with open(filename, "rb") as f:
        image_base64 = base64.b64encode(f.read()).decode("utf-8")

    image_data = {
        "type": "image",
        "nickname": "imagebot",
        "imageData": image_base64,
        "timestamp": datetime.utcnow().isoformat()
    }
    await manager.broadcast(image_data)
    messages_collection.insert_one(image_data)

async def handle_image_variation(image_b64: str):
    
    image_byte = base64.b64decode(image_b64)
    response = await client.images.create_variation(
        image=image_byte,
        n=1,
        size="1024x1024",
    )
    image_url = response.data[0].url
    print("variation response:", image_url)


    image_bytes = urlopen(image_url).read()
    filename = f"images/variation_{datetime.utcnow().timestamp()}.png"
    os.makedirs("images", exist_ok=True)
    with open(filename, "wb") as f:
        f.write(image_bytes)

    with open(filename, "rb") as f:
        image_base64 = base64.b64encode(f.read()).decode("utf-8")

    image_data = {
        "type": "image",
        "nickname": "imagebot",
        "message": "Uploaded",
        "imageData": image_base64,
        "timestamp": datetime.utcnow().isoformat()
    }
    await manager.broadcast(image_data)
    messages_collection.insert_one(image_data)



async def handle_tts(data):
    query = data.strip()[len("@tts"):].strip()
        
    response = await client.audio.speech.create(
        model = "tts-1",
        voice = "nova",
        input = query
    )
    
    audio_bytes = response.content
    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
    
    await manager.broadcast(
        { "type": "audio",
          "nickname": "TTS",
          "audioData": audio_base64,
          "timestamp": datetime.utcnow().isoformat()    
        }
    )


async def handle_stt(audio_b64):
    audio_bytes = base64.b64decode(audio_b64)
    
    audio_file = BytesIO(audio_bytes)
    audio_file.name = "audio.webm"

    transcription = await client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        response_format="text"
    )

    await manager.broadcast({
        "type": "text",
        "nickname": "STT",
        "message": transcription,
        "timestamp": datetime.utcnow().isoformat()
    })

def convert_webm_base64_to_mp3_base64(base64_audio: str) -> str:
    audio_bytes = base64.b64decode(base64_audio)
    audio = AudioSegment.from_file(BytesIO(audio_bytes), format="webm")

    out_buffer = BytesIO()
    audio.export(out_buffer, format="mp3")
    out_buffer.seek(0)

    return base64.b64encode(out_buffer.read()).decode("utf-8")



async def handle_talk(audio_b64):
    mp3_b64 = convert_webm_base64_to_mp3_base64(audio_b64)

    history = [{"role": "system", "content": "You are a helpful assistant."}]
    for msg in messages_collection.find().sort("timestamp", -1).limit(30):
        history.append({"role": msg["role"], "content": msg["message"]})

    history.append({
        "role": "user",
        "content": [
            {"type": "text", "text": "내 음성에 대답해줘"},
            {"type": "input_audio", "input_audio": {"data": mp3_b64, "format": "mp3"}}
        ]
    })

    response = await client.chat.completions.create(
        model="gpt-4o-audio-preview",
        messages=history,
        modalities=["text", "audio"],
        audio={"voice": "nova", "format": "mp3"}
    )

    result = response.choices[0].message
    reply_text = result.audio.transcript
    reply_audio_b64 = result.audio.data

    messages_collection.insert_one({
        "nickname": "talk-response",
        "role": "assistant",
        "type": "text",
        "message": reply_text,
        "timestamp": datetime.utcnow()
    })

    await manager.broadcast({
        "type": "audio",
        "nickname": "TALK",
        "message": reply_text,
        "audioData": reply_audio_b64,
        "timestamp": datetime.utcnow().isoformat()
    })



@app.websocket("/ws/{nickname}")
async def websocket_endpoint(websocket: WebSocket, nickname: str):
    await manager.connect(websocket, nickname)
    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                data = json.loads(raw_data)
            except json.JSONDecodeError:
                print("Invalid JSON:", raw_data)
                continue

            timestamp = datetime.utcnow()
            data["timestamp"] = timestamp.isoformat()

            messages_collection.insert_one({
                "nickname": data.get("nickname", nickname),
                "role": "user",
                "message": data.get("message", ""),
                "timestamp": timestamp
            })

            print(data)
            msg_type = data.get("type")
            await manager.broadcast(data)
            if msg_type == "text":
                text = data.get("message", "")
                if text.startswith("@chatbot"):
                    asyncio.create_task(handle_chatbot(text, nickname))
                elif text.startswith("@image"):
                    prompt = text[len("@image"):].strip()
                    asyncio.create_task(handle_image_prompt(prompt))
                elif text.startswith("@tts"):
                    asyncio.create_task(handle_tts(text))
            elif msg_type == "image":
                image_b64 = data.get("imageData")
                if image_b64:
                    asyncio.create_task(handle_image_variation(image_b64))
            elif msg_type == "audio":
                text = data.get("message", "")
                audio_b64 = data.get("audioData")
                if text.startswith("@stt"):
                    asyncio.create_task(handle_stt(audio_b64))
                elif text.startswith("@talk"):
                    asyncio.create_task(handle_talk(audio_b64))



    except WebSocketDisconnect:
        manager.disconnect(nickname)
        await manager.broadcast({
            "nickname": "system",
            "message": f"{nickname}님이 나갔습니다.",
            "timestamp": datetime.utcnow().isoformat()
        })

if __name__ == "__main__":
    uvicorn.run("backend:app", host="0.0.0.0", port=8000, reload=True)


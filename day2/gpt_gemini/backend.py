from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from typing import Dict
from datetime import datetime
import uvicorn
import json
import base64
from datetime import datetime, timedelta, timezone
from openai import AsyncOpenAI
import asyncio
from google import genai
from google.genai import types

app = FastAPI()

with open('api-key', 'r') as f:
  API_KEY = f.read().strip()

client = AsyncOpenAI(api_key=API_KEY)

with open('genai-api-key', 'r') as f:
  Gemini_API_KEY = f.read().strip()


gemini_client = genai.Client(api_key=Gemini_API_KEY)


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


talk_status = False


async def gemini_response(message: str) -> str:
    
  response = gemini_client.models.generate_content(
      model="gemini-2.5-flash",
      config=types.GenerateContentConfig(
        system_instruction="You are a cat. Your name is Neko."),
      contents=message
  )
  print(response.text)
  return response.text


async def chatbot_response(message: str) -> str:

  print("gpt")
  completion = await client.chat.completions.create(
    model="gpt-4.1",
    messages=[
      {"role": "system", "content": "You are my bestfriend."},
      {"role": "user", "content": message}
    ]
  )
  return completion.choices[0].message.content

async def handle_talk_gemini_gpt():
  query = "안녕?"
  print("handle")
  while talk_status:
    print("run!")
  
    reply = await chatbot_response(query)
    
    messages_collection.insert_one({
      "nickname": "gpt",
      "role": "assistant",
      "message": reply,
      "timestamp": datetime.utcnow().isoformat()
    })
  
    await manager.broadcast({
      "type": "text",
      "nickname": "gpt",
      "message": reply,
      "timestamp": datetime.utcnow().isoformat()
    })
    
    reply = await gemini_response(reply)
    
    messages_collection.insert_one({
      "nickname": "gemini",
      "role": "assistant",
      "message": reply,
      "timestamp": datetime.utcnow().isoformat()
    })
  
    await manager.broadcast({
      "type": "text",
      "nickname": "gemini",
      "message": reply,
      "timestamp": datetime.utcnow().isoformat()
    })
  
    query = reply
  

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

@app.websocket("/ws/{nickname}")
async def websocket_endpoint(websocket: WebSocket, nickname: str):
    global talk_status
    
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
            
            msg_type = data.get("type")
            if msg_type == "text":
                await manager.broadcast(data)
                text = data.get("message", "")
                if text.startswith("@chatbot"):
                  asyncio.create_task(handle_chatbot(text, nickname))
                elif text.startswith("@talk_start"):
                  talk_status = True
                  asyncio.create_task(handle_talk_gemini_gpt())
                elif text.startswith("@talk_stop"):
                  talk_status = False

    except WebSocketDisconnect:
        manager.disconnect(nickname)
        await manager.broadcast({
            "nickname": "system",
            "message": f"{nickname}님이 나갔습니다.",
            "timestamp": datetime.utcnow().isoformat()
        })

if __name__ == "__main__":
    uvicorn.run("backend:app", host="0.0.0.0", port=8000, reload=True)


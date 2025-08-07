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


latest_response_id: str | None = None


async def chatbot_response(message: str, parent_id: str | None = None) -> tuple[str, str]:
    if parent_id:
      response = await client.responses.create(
          model="gpt-4o",
          instructions="You are a helpful assistant",
          input=message,
          previous_response_id=parent_id  
      )
    else:
      response = await client.responses.create(
          model="gpt-4o",
          instructions="You are a helpful assistant",
          input=message,
      )
     
    reply = response.output_text
    response_id = response.id  
    return reply, response_id

async def handle_chatbot(data, nickname):
  global latest_response_id   

  query = data.strip()[len("@chatbot"):].strip()
  
  reply, new_response_id = await chatbot_response(query, parent_id=latest_response_id)
  latest_response_id = new_response_id
    
  messages_collection.insert_one({
    "nickname": "chatbot",
    "role": "assistant",
    "message": reply,
    "timestamp": datetime.utcnow().isoformat()
  })
  
  await manager.broadcast({
    "type": "text",
    "nickname": "chatbot",
    "text": reply,
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
                "message": data.get("text", ""),
                "timestamp": timestamp
            })
            
            msg_type = data.get("type")
            if msg_type == "text":
                await manager.broadcast(data)
                text = data.get("text", "")
                if text.startswith("@chatbot"):
                  asyncio.create_task(handle_chatbot(text, nickname))


    except WebSocketDisconnect:
        manager.disconnect(nickname)
        await manager.broadcast({
            "nickname": "system",
            "text": f"{nickname}님이 나갔습니다.",
            "timestamp": datetime.utcnow().isoformat()
        })

if __name__ == "__main__":
    uvicorn.run("backend:app", host="0.0.0.0", port=8000, reload=True)


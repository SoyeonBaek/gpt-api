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
from datetime import datetime, timedelta
import pytz
import pickle
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

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

SCOPES = ['https://www.googleapis.com/auth/calendar']
TOKEN_FILE = "token.json"
CLIENT_SECRET_FILE = "client_secret_772705558537-i205a18oj8nmv46gn73ru848j24600so.apps.googleusercontent.com.json"

kst = pytz.timezone("Asia/Seoul")

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
    query = data["message"].strip()[len("@tts"):].strip()

    response = await client.audio.speech.create(
        model="tts-1",
        voice="nova",
        input=query
    )

    audio_bytes = await response.read()
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

    await manager.broadcast({
        "type": "audio",
        "nickname": "TTS",
        "audioData": audio_b64,
        "timestamp": datetime.utcnow().isoformat()
    })


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

def convert_webm_base64_to_mp3_base64(webm_base64: str) -> str:
    import subprocess, tempfile
    raw = base64.b64decode(webm_base64)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_webm:
        temp_webm.write(raw)
        webm_path = temp_webm.name
    mp3_path = webm_path.replace(".webm", ".mp3")
    subprocess.run(["ffmpeg", "-i", webm_path, mp3_path, "-y", "-loglevel", "quiet"])

    with open(mp3_path, "rb") as f:
        mp3_b64 = base64.b64encode(f.read()).decode("utf-8")

    os.remove(webm_path)
    os.remove(mp3_path)
    return mp3_b64


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

def get_calendar_service():
    print("[DEBUG] get calendar service")
    creds = None

    # 기존 token.json이 있으면 로드
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # 유효하지 않으면 갱신 또는 새 인증
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        # token.json에 저장
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
    service = build("calendar", "v3", credentials=creds)
    print("PASS")
    return service

async def parse_schedule_with_gpt(user_input: str) -> dict:
    print("[DEBUG] parse_schedule")
    time = datetime.now(kst).isoformat()
    system_msg = {
        "role": "system",
        "content": (
            f'''당신은 사용자의 일정 요청을 분석해 JSON 형식으로 응답하는 일정 파서입니다.
            기준이 되는 현재 시간은 다음과 같습니다 {time}
            형식은 다음과 같습니다:
            {{
              "action": "create" | "update" | "delete",
              "title": "지나랑 저녁 약속",
              "datetime": "2024-07-24T19:00:00",
              "new_datetime": "2024-07-24T20:00:00"
            }}
            오직 JSON으로만 응답해줘.'''
        )
    }
    user_msg = {"role": "user", "content": user_input}
    response = await client.chat.completions.create(
        model="gpt-4.1",
        messages=[system_msg, user_msg]
    )
    print(response)
    return json.loads(response.choices[0].message.content)



def find_event(service, calendar_id, title, start_time_str):
    print("[DEBUG] find event 진입")
    start_time = datetime.fromisoformat(start_time_str).replace(tzinfo=timezone(timedelta(hours=9)))
    end_time = start_time + timedelta(hours=1)
    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=start_time.isoformat(),
        timeMax=end_time.isoformat(),
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    for event in events_result.get("items", []):
        if event.get("summary") == title:
            return event
    return None

async def handle_calendar(text: str, nickname: str):
    print("[DEBUG] handle_calendar 진입")
    command = text.strip()[len("@calendar"):].strip()
    try:
        parsed = await parse_schedule_with_gpt(command)
        print("calendar 응답:", parsed)  
        action = parsed.get("action", "create")
        title = parsed["title"]
        start_time = datetime.fromisoformat(parsed["datetime"]).isoformat()
        end_time = (datetime.fromisoformat(parsed["datetime"]) + timedelta(hours=1)).isoformat()
        new_datetime = parsed.get("new_datetime")
    except Exception as e:
        await manager.broadcast({
            "type": "text",
            "nickname": "calendar",
            "text": f"[파싱 실패] {e}",
            "timestamp": datetime.utcnow().isoformat()
        })
        return

    service = get_calendar_service()
    calendar_id = "primary"
    try:
        if action == "create":
            event = {
                "summary": title,
                "start": {"dateTime": start_time, "timeZone": "Asia/Seoul"},
                "end": {"dateTime": end_time, "timeZone": "Asia/Seoul"}
            }
            service.events().insert(calendarId=calendar_id, body=event).execute()
            response_text = f"{title} 일정이 등록되었습니다. ({start_time})"
        elif action == "delete":
            event = find_event(service, calendar_id, title, start_time)
            if not event:
                raise ValueError("삭제할 일정을 찾을 수 없습니다.")
            service.events().delete(calendarId=calendar_id, eventId=event["id"]).execute()
            response_text = f"{title} 일정이 삭제되었습니다."
        elif action == "update":
            if not new_datetime:
                raise ValueError("new_datetime 값이 필요합니다.")
            event = find_event(service, calendar_id, title, start_time)
            if not event:
                raise ValueError("수정할 일정을 찾을 수 없습니다.")
            event["start"]["dateTime"] = datetime.fromisoformat(new_datetime).isoformat()
            event["end"]["dateTime"] = (datetime.fromisoformat(new_datetime) + timedelta(hours=1)).isoformat()
            service.events().update(calendarId=calendar_id, eventId=event["id"], body=event).execute()
            response_text = f"{title} 일정이 {new_datetime}로 수정되었습니다."
        else:
            response_text = f"지원하지 않는 작업: {action}"
    except Exception as e:
        response_text = f"[일정 처리 실패] {e}"

    await manager.broadcast({
        "type": "text",
        "nickname": "calendar",
        "message": response_text,
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
                elif text.startswith("@calendar"):
                    asyncio.create_task(handle_calendar(text, nickname))
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


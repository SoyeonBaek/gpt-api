# backend.py
from fastapi import FastAPI, WebSocket
import uvicorn
import time
import asyncio

app = FastAPI()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        
        await asyncio.sleep(3)

        await websocket.send_text(f"Server received: {data}")
        

if __name__ == "__main__":
    uvicorn.run("backend:app", host="0.0.0.0", port=8000, reload=True)

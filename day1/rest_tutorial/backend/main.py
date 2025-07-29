from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
from db import collection
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()

app.add_middleware(
  CORSMiddleware,
  allow_origins=["http://localhost:3000"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
  
)

class Message(BaseModel):
    username: str
    content: str


@app.get("/messages", response_model=list[Message])
def get_messages(username: Optional[str] = None):
    if username:
        msgs = collection.find({"username": username})
    else: 
        msgs = collection.find()
    return msgs

@app.post("/messages", response_model=Message)
def post_message(msg: Message):
    result = collection.insert_one(msg.dict()) 
    msg = collection.find_one({"_id": result.inserted_id})
    return msg



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)




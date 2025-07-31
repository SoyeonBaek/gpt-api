import React, { useEffect, useRef, useState } from "react";
import "./App.css";

function App() {
  const [nickname, setNickname] = useState("");
  const [inputNickname, setInputNickname] = useState("");
  const [message, setMessage] = useState("");
  const [chatLog, setChatLog] = useState([]);
  const [imageFile, setImageFile] = useState(null);
  const ws = useRef(null);
  const messagesEndRef = useRef(null);

  const fetchMessages = async () => {
    const res = await fetch("http://localhost:8000/messages");
    const data = await res.json();
    setChatLog(data);
  };

  useEffect(() => {
    if (!nickname) return;

    ws.current = new WebSocket(`ws://localhost:8000/ws/${nickname}`);

    ws.current.onopen = () => {
      console.log("WebSocket connected");
    };

    ws.current.onmessage = (event) => {
      try {
        const msgObj = JSON.parse(event.data);
        setChatLog((prev) => [...prev, msgObj]);
      } catch (e) {
        console.error("Invalid message format:", event.data);
      }
    };

    ws.current.onclose = () => {
      console.log("WebSocket disconnected");
    };

    return () => {
      ws.current?.close();
    };
  }, [nickname]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatLog]);

  const sendMessage = () => {
    if (!message.trim() || !nickname.trim()) return;

    const payload = {
      type: "text",
      nickname,
      message,
      timestamp: new Date().toISOString(),
    };

    ws.current?.send(JSON.stringify(payload));
    setMessage("");
  };

  const sendImage = () => {
    if (!imageFile || !nickname.trim()) return;

    const reader = new FileReader();
    reader.onload = () => {
      const base64Data = reader.result.split(",")[1];
      const payload = {
        type: "image",
        nickname,
        imageData: base64Data,
        timestamp: new Date().toISOString(),
      };
      ws.current?.send(JSON.stringify(payload));
      setImageFile(null);
    };
    reader.readAsDataURL(imageFile);
  };

  const handleNicknameSet = () => {
    if (inputNickname.trim()) {
      setNickname(inputNickname.trim());
    }
  };

  const renderMessage = (msgObj, i) => {
    const time = new Date(msgObj.timestamp).toLocaleTimeString();

    if (msgObj.type === "image") {
      return (
        <div key={i} className="message">
          <strong>{msgObj.nickname}</strong> [{time}] :
          <div>
            <img
              src={`data:image/png;base64,${msgObj.imageData}`}
              alt="Uploaded"
              style={{ maxWidth: "300px", marginTop: "5px", borderRadius: "8px" }}
            />
          </div>
        </div>
      );
    }

    return (
      <div key={i} className="message">
        <strong>{msgObj.nickname}</strong> [{time}] : {msgObj.message}
      </div>
    );
  };

  return (
    <div className="container">
      <h2>Chatting</h2>

      <div className="nickname-bar">
        <input
          type="text"
          placeholder="Enter your nickname"
          value={inputNickname}
          onChange={(e) => setInputNickname(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleNicknameSet();
          }}
          disabled={!!nickname}
        />
        <button onClick={handleNicknameSet}>Enter</button>
      </div>

      <div className="chat-box">
        {chatLog.map((msg, i) => renderMessage(msg, i))}
        <div ref={messagesEndRef} />
      </div>

      <div className="input-bar">
        <input
          type="text"
          placeholder="Input Messages"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={(e) => {
            if (e.nativeEvent.isComposing) return;
            if (e.key === "Enter") sendMessage();
          }}
        />
        <button onClick={sendMessage}>Send</button>
      </div>

      <div className="input-bar">
        <input
          type="file"
          accept="image/*"
          onChange={(e) => setImageFile(e.target.files[0])}
        />
        <button onClick={sendImage} disabled={!imageFile}>
          Send Image
        </button>
      </div>
    </div>
  );
}

export default App;


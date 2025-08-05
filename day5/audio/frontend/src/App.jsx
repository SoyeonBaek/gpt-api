import React, { useEffect, useRef, useState } from "react";
import "./App.css";

function App() {
  const [nickname, setNickname] = useState("");
  const [inputNickname, setInputNickname] = useState("");
  const [message, setMessage] = useState("");
  const [chatLog, setChatLog] = useState([]);
  const [imageFile, setImageFile] = useState(null); // 추가
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingType, setRecordingType] = useState(""); // "stt" or "talk"
  const audioChunks = useRef([]);
  const ws = useRef(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (!nickname) return;
    ws.current = new WebSocket(`ws://localhost:8000/ws/${nickname}`);

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setChatLog((prev) => [...prev, data]);
    };

    return () => ws.current?.close();
  }, [nickname]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatLog]);

  const sendMessage = () => {
    if (!message.trim()) return;
    const payload = {
      type: "text",
      nickname,
      message,
      timestamp: new Date().toISOString(),
    };
    ws.current.send(JSON.stringify(payload));
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

  const startRecording = (type) => {
    setIsRecording(true);
    navigator.mediaDevices.getUserMedia({ audio: true }).then((stream) => {
      const recorder = new MediaRecorder(stream);
      audioChunks.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunks.current.push(e.data);
      };

      recorder.onstop = () => {
        const blob = new Blob(audioChunks.current, { type: "audio/webm" });
        const reader = new FileReader();
        reader.onloadend = () => {
          const base64Audio = reader.result.split(",")[1];
          const command = type === "stt" ? "@stt" : "@talk";
          const payload = {
            type: "audio",
            nickname,
            message: command,
            audioData: base64Audio,
            timestamp: new Date().toISOString(),
          };
          ws.current.send(JSON.stringify(payload));
        };
        reader.readAsDataURL(blob);
      };

      recorder.start();
      setMediaRecorder(recorder);
    });
  };

  const stopRecording = () => {
    mediaRecorder.stop();
    setIsRecording(false);
  };

  return (
    <div className="container">
      <h2>Chat</h2>

      {!nickname && (
        <div>
          <input
            value={inputNickname}
            onChange={(e) => setInputNickname(e.target.value)}
            placeholder="Enter nickname"
          />
          <button onClick={() => setNickname(inputNickname)}>Enter</button>
        </div>
      )}

      <div className="chat-box">
        {chatLog.map((msg, i) => (
          <div key={i}>
            <strong>{msg.nickname}</strong>:
            <div>
              {msg.type === "audio" && msg.audioData ? (
                <>
                  <div>{msg.message}</div>
                  <audio controls>
                    <source
                      src={`data:audio/mp3;base64,${msg.audioData}`}
                      type="audio/mp3"
                    />
                    브라우저에서 오디오를 지원하지 않습니다.
                  </audio>
                </>
              ) : msg.type === "image" && msg.imageData ? (
                <img
                  src={`data:image/png;base64,${msg.imageData}`}
                  alt="Uploaded"
                  style={{ maxWidth: "300px", borderRadius: "8px", marginTop: "5px" }}
                />
              ) : (
                msg.message
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="input-bar">
        <input
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
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

      <div className="input-bar">
        <button onClick={() => startRecording("stt")} disabled={isRecording}>
          Start STT
        </button>
        <button onClick={() => startRecording("talk")} disabled={isRecording}>
          Start Talk
        </button>
        <button onClick={stopRecording} disabled={!isRecording}>
          Stop & Send
        </button>
      </div>
    </div>
  );
}

export default App;


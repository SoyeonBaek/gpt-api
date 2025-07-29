import React, { useState, useEffect } from 'react';

function App() {
  const [messages, setMessages] = useState([]);
  const [username, setUsername] = useState('');
  const [content, setContent] = useState('');

  const fetchMessages = async () => {
    const res = await fetch('http://localhost:8000/messages');
    const data = await res.json();
    setMessages(data);
  };

  const sendMessage = async () => {
    const res = await fetch('http://localhost:8000/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username, content }),
    });

    if (res.ok) {
      setUsername('');
      setContent('');
      fetchMessages();  
    }
  };

  useEffect(() => {
    fetchMessages();
  }, []);

  return (
    <div style={{ padding: 30 }}>
      <h2>💬 메시지 목록</h2>
      <ul>
        {messages.map((msg, idx) => (
          <li key={idx}><strong>{msg.username}</strong>: {msg.content}</li>
        ))}
      </ul>

      <h3>✉️ 새 메시지 보내기</h3>
      <input
        type="text"
        placeholder="이름"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
      />
      <input
        type="text"
        placeholder="메시지"
        value={content}
        onChange={(e) => setContent(e.target.value)}
        style={{ marginLeft: 10 }}
      />
      <button onClick={sendMessage} style={{ marginLeft: 10 }}>전송</button>
    </div>
  );
}

export default App;


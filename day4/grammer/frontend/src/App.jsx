import React, { useState } from "react";
import { Tooltip } from "react-tooltip";
import 'react-tooltip/dist/react-tooltip.css';
import './App.css';  // ✅ CSS 불러오기

const App = () => {
  const [inputText, setInputText] = useState("");
  const [result, setResult] = useState(null);

  const handleCheck = async () => {
    try {
      const res = await fetch("http://localhost:8000/spellcheck", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: inputText }),
      });

      const data = await res.json();
      if (!Array.isArray(data.corrections)) {
        data.corrections = [];
      }
      setResult(data);
    } catch (err) {
      console.error("오류 발생:", err);
    }
  };

  const renderResult = () => {
    if (!result) return null;

    const { original, corrections } = result;
    const sorted = [...corrections].sort((a, b) => a.start - b.start);
    const parts = [];
    let idx = 0;

    sorted.forEach((cor, i) => {
      const { start, end, correct } = cor;
      const tooltipId = `tooltip-${i}`;

      if (idx < start) {
        parts.push(<span key={`text-${idx}`}>{original.slice(idx, start)}</span>);
      }

      parts.push(
        <span
          key={`error-${i}`}
          className="correction-highlight"
          data-tooltip-id={tooltipId}
          data-tooltip-content={correct}
        >
          {original.slice(start, end)}
          <Tooltip id={tooltipId} place="top" />
        </span>
      );

      idx = end;
    });

    if (idx < original.length) {
      parts.push(<span key={`last-${idx}`}>{original.slice(idx)}</span>);
    }

    return <div className="result-area">{parts}</div>;
  };

  return (
    <div className="container">
      <h2 className="title">📝 맞춤법 검사기</h2>
      <textarea
        className="input-text"
        value={inputText}
        onChange={(e) => setInputText(e.target.value)}
        rows={5}
        placeholder="검사할 문장을 입력하세요..."
      />
      <button className="check-button" onClick={handleCheck}>
        ✨ 검사하기
      </button>
      {renderResult()}
    </div>
  );
};

export default App;


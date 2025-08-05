import React, { useRef, useState } from 'react';
import axios from 'axios';

function ImageEditor() {
  const canvasRef = useRef(null);
  const maskCanvasRef = useRef(null);
  const [imageFile, setImageFile] = useState(null);
  const [prompt, setPrompt] = useState('');
  const [resultUrl, setResultUrl] = useState(null);
  const [canvasSize, setCanvasSize] = useState({ width: 512, height: 512 });
  const [drawing, setDrawing] = useState(false);

  const handleImageUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      setImageFile(file);
      const reader = new FileReader();
      reader.onload = () => {
        const img = new Image();
        img.onload = () => {
          const MAX = 512;
          const scale = Math.min(MAX / img.width, MAX / img.height, 1);
          const width = img.width * scale;
          const height = img.height * scale;
          setCanvasSize({ width, height });

          const canvas = canvasRef.current;
          canvas.width = width;
          canvas.height = height;
          const ctx = canvas.getContext('2d');
          ctx.clearRect(0, 0, width, height);
          ctx.drawImage(img, 0, 0, width, height);

          const maskCanvas = maskCanvasRef.current;
          maskCanvas.width = width;
          maskCanvas.height = height;
          const maskCtx = maskCanvas.getContext('2d');
          maskCtx.clearRect(0, 0, width, height);
        };
        img.src = reader.result;
      };
      reader.readAsDataURL(file);
    }
  };

  const startDraw = (e) => {
    setDrawing(true);
    draw(e);
  };

  const endDraw = () => {
    setDrawing(false);
    const ctx = maskCanvasRef.current.getContext('2d');
    ctx.beginPath();
  };

  const draw = (e) => {
    if (!drawing) return;
    const canvas = maskCanvasRef.current;
    const ctx = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    ctx.fillStyle = 'black';
    ctx.beginPath();
    ctx.arc(x, y, 10, 0, Math.PI * 2);
    ctx.fill();
  };

  const prepareMaskBlob = () => {
    return new Promise((resolve) => {
      const maskCanvas = maskCanvasRef.current;
      const tempCanvas = document.createElement('canvas');
      tempCanvas.width = maskCanvas.width;
      tempCanvas.height = maskCanvas.height;
      const tempCtx = tempCanvas.getContext('2d');
      tempCtx.drawImage(maskCanvas, 0, 0);

      const imageData = tempCtx.getImageData(0, 0, tempCanvas.width, tempCanvas.height);
      const data = imageData.data;

      for (let i = 0; i < data.length; i += 4) {
        const r = data[i];
        const g = data[i + 1];
        const b = data[i + 2];
        const a = data[i + 3];

        const isBlack = r === 0 && g === 0 && b === 0 && a === 255;
        if (isBlack) {
          data[i + 3] = 0; // make transparent
        } else {
          data[i + 0] = 255;
          data[i + 1] = 255;
          data[i + 2] = 255;
          data[i + 3] = 255; // make white opaque
        }
      }

      tempCtx.putImageData(imageData, 0, 0);
      tempCanvas.toBlob((blob) => resolve(blob), 'image/png');
    });
  };

  const handleSubmit = async () => {
    if (!imageFile || !prompt) return;

    const maskBlob = await prepareMaskBlob();

    const formData = new FormData();
    formData.append('image', imageFile);
    formData.append('mask', maskBlob);
    formData.append('prompt', prompt);

    try {
      const response = await axios.post('http://localhost:8000/stylize', formData);
      setResultUrl(response.data.url);
    } catch (err) {
      console.error('❌ 요청 오류:', err);
      alert('에러 발생');
    }
  };
return (
  <div style={{ padding: '20px' }}>
    <h2>🖼️ 이미지 스타일 변경기</h2>
    <input type="file" accept="image/*" onChange={handleImageUpload} />
    <br />
    <textarea
      placeholder="변환하고 싶은 스타일을 설명해주세요"
      value={prompt}
      onChange={(e) => setPrompt(e.target.value)}
      style={{ width: '300px', height: '80px', marginTop: '10px' }}
    />
    <div style={{ display: 'flex', marginTop: '20px', gap: '40px' }}>
      <div style={{ position: 'relative', width: canvasSize.width, height: canvasSize.height }}>
        <canvas
          ref={canvasRef}
          width={canvasSize.width}
          height={canvasSize.height}
          style={{ position: 'absolute', top: 0, left: 0 }}
        />
        <canvas
          ref={maskCanvasRef}
          width={canvasSize.width}
          height={canvasSize.height}
          style={{ position: 'absolute', top: 0, left: 0, cursor: 'crosshair' }}
          onMouseDown={startDraw}
          onMouseUp={endDraw}
          onMouseMove={draw}
        />
      </div>

      {resultUrl && (
        <div>
          <h4>변환된 이미지:</h4>
          <img src={resultUrl} alt="result" width={canvasSize.width} />
        </div>
      )}
    </div>

    <button
      onClick={handleSubmit}
      style={{
        marginTop: 30,
        padding: '12px 24px',
        fontSize: '16px',
        backgroundColor: '#28a745',
        color: 'white',
        border: 'none',
        borderRadius: '8px',
        cursor: 'pointer',
      }}
    >
      🎨 이미지 변환 요청
    </button>
  </div>
);
}

export default ImageEditor;


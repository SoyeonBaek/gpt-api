import base64
from openai import OpenAI

with open('api-key', 'r') as f:
  API_KEY = f.read().strip()

client = OpenAI(api_key=API_KEY)

# MP3 파일을 base64 인코딩
def load_mp3_as_base64(file_path):
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def main():
    mp3_b64 = load_mp3_as_base64("input.mp3")

    response = client.chat.completions.create(
        model="gpt-4o-audio-preview",
        modalities=["text", "audio"],
        audio={"voice": "nova", "format": "mp3"},
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "이 음성에 대해 응답해줘."},
                    {"type": "input_audio", "input_audio": {"data": mp3_b64, "format": "mp3"}}
                ]
            }
        ]
    )

    result = response.choices[0].message
    reply_text = result.audio.transcript
    reply_audio_b64 = result.audio.data

    print("GPT 응답 텍스트:")
    print(reply_text)

    with open("response.mp3", "wb") as f:
        f.write(base64.b64decode(reply_audio_b64))

    print("응답 음성이 response.mp3 파일로 저장되었습니다.")

if __name__ == "__main__":
    main()


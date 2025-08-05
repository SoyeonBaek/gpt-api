
from openai import OpenAI

with open('api-key', 'r') as f:
  API_KEY = f.read().strip()

client = OpenAI(api_key=API_KEY)

def speech_to_text(audio_path):
    with open(audio_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text"
        )
    print("변환된 텍스트:")
    print(transcript)

if __name__ == "__main__":
    speech_to_text("input.mp3")

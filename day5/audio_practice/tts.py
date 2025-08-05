

from openai import OpenAI

with open('api-key', 'r') as f:
  API_KEY = f.read().strip()

client = OpenAI(api_key=API_KEY)

def text_to_speech(text, output_filename="response.mp3"):
    response = client.audio.speech.create(
        model="tts-1",
        voice="nova", #alloy, shimmer, echo, fable, onyx
        input=text
    )

    with open(output_filename, "wb") as f:
        f.write(response.content)

    print(f"Audio saved as {output_filename}")

if __name__ == "__main__":
    text_to_speech("안녕하세요 반갑습니다.", "response.mp3")

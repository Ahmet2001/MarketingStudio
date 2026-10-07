import os
from pathlib import Path

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

from api_retry import RetryPolicy, call_with_retry

load_dotenv()

api_key = os.getenv("ELEVENLABS_API_KEY")

if not api_key:
    raise RuntimeError("ELEVENLABS_API_KEY is missing from .env")

client = ElevenLabs(api_key=api_key)
retry_policy = RetryPolicy()

text = (
    "It was almost midnight when Daniel received a message "
    "from someone who had disappeared seven years ago."
)

def request_audio() -> bytes:
    audio = client.text_to_speech.convert(
        voice_id="JBFqnCBsd6RMkjVDRZzb",
        model_id="eleven_flash_v2_5",
        text=text,
        output_format="mp3_44100_128",
    )
    return b"".join(chunk for chunk in audio if chunk)


audio_bytes = call_with_retry(
    request_audio,
    label="ElevenLabs narration",
    policy=retry_policy,
)
if not audio_bytes:
    raise RuntimeError("ElevenLabs returned empty audio.")

output_path = Path("narration.mp3")

output_path.write_bytes(audio_bytes)

print(f"Audio saved: {output_path.resolve()}")

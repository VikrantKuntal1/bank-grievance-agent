from __future__ import annotations

import os

from dotenv import load_dotenv
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs

load_dotenv()

# Rachel, a premade voice available on every ElevenLabs plan.
VOICE_ID = "21m00Tcm4TlvDq8ikWAM"
MODEL_ID = "eleven_multilingual_v2"

_client: ElevenLabs | None = None


def get_client() -> ElevenLabs:
    global _client
    if _client is None:
        api_key = os.environ.get("ELEVENLABS_API_KEY")
        if not api_key:
            raise RuntimeError("ELEVENLABS_API_KEY is not set. Add it to your .env file.")
        _client = ElevenLabs(api_key=api_key)
    return _client


def speak(text: str) -> bytes:
    audio = get_client().text_to_speech.convert(
        voice_id=VOICE_ID,
        text=text,
        model_id=MODEL_ID,
        voice_settings=VoiceSettings(
            stability=0.5,
            similarity_boost=0.75,
            style=0.3,
            use_speaker_boost=True,
        ),
    )
    return b"".join(audio)

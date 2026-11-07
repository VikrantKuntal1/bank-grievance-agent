from __future__ import annotations

from src.llm.client import get_client


def transcribe(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    transcription = get_client().audio.transcriptions.create(
        file=(filename, audio_bytes),
        model="whisper-large-v3",
        response_format="text",
    )
    return transcription.strip()

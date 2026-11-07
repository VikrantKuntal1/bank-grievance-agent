from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import struct
import time
import wave

from fastapi import WebSocket, WebSocketDisconnect

from src.agent.graph import run_turn
from src.voice.tts import speak

log = logging.getLogger(__name__)

RMS_THRESHOLD = 50  # amplitude above which a chunk counts as speech; raise if line noise triggers turns
SILENCE_SECONDS = 1.5


def rms_of(chunk: bytes) -> float:
    n = len(chunk) // 2
    if n == 0:
        return 0.0
    samples = struct.unpack(f"<{n}h", chunk[:n * 2])
    return (sum(s * s for s in samples) / n) ** 0.5


def pcm_to_wav(pcm: bytes, sample_rate: int = 8000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm)
    return buf.getvalue()


async def send_audio(websocket: WebSocket, audio_bytes: bytes, stream_sid: str):
    # Exotel expects 8 kHz mono PCM, so convert the MP3 from TTS with ffmpeg.
    process = await asyncio.create_subprocess_exec(
        "ffmpeg", "-i", "pipe:0",
        "-f", "s16le",
        "-ar", "8000",
        "-ac", "1",
        "pipe:1",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    pcm_bytes, _ = await process.communicate(input=audio_bytes)

    chunk_size = 320
    for i in range(0, len(pcm_bytes), chunk_size):
        chunk = pcm_bytes[i:i + chunk_size]
        if len(chunk) < chunk_size:
            chunk = chunk + b'\x00' * (chunk_size - len(chunk))
        audio_b64 = base64.b64encode(chunk).decode("utf-8")
        message = json.dumps({
            "event": "media",
            "stream_sid": stream_sid,
            "media": {"payload": audio_b64}
        })
        await websocket.send_text(message)
        await asyncio.sleep(0.02)


async def process_caller_audio(
    websocket: WebSocket,
    audio_buffer: bytearray,
    history: list,
    stream_sid: str,
) -> list:
    log.debug(f"Processing audio buffer: {len(audio_buffer)} bytes")

    if len(audio_buffer) < 3200:
        log.debug("Buffer too small, skipping")
        return history

    try:
        from src.voice.stt import transcribe
        # Whisper needs a WAV header, which raw PCM does not have.
        audio_bytes = pcm_to_wav(bytes(audio_buffer))
        log.debug(f"Sending {len(audio_bytes)} bytes to Whisper...")
        user_text = transcribe(audio_bytes, filename="audio.wav")
        log.info(f"Transcribed: '{user_text}'")

        if not user_text.strip():
            log.debug("Empty transcription, skipping")
            return history

        log.debug(f"Running agent with: '{user_text}'")
        result = run_turn(
            user_message=user_text,
            history=history,
        )

        bot_reply = result["bot_response"]
        log.info(f"Bot reply: '{bot_reply}'")

        audio_response = speak(bot_reply)
        log.debug(f"TTS generated {len(audio_response)} bytes, sending to caller...")
        await send_audio(websocket, audio_response, stream_sid)
        log.debug("Audio sent successfully")

        return result["history"]

    except Exception:
        log.exception("failed to process caller audio")
        error_audio = speak("I'm sorry, I didn't catch that. Could you please repeat?")
        await send_audio(websocket, error_audio, stream_sid)
        return history


async def handle_exotel_websocket(websocket: WebSocket):
    await websocket.accept()

    history = []
    audio_buffer = bytearray()
    stream_sid = None
    is_speaking = False
    processing = False
    last_speech_time = 0.0
    last_debug = 0.0
    silence_checker = None

    async def check_silence():
        nonlocal history, audio_buffer, is_speaking, processing
        while True:
            await asyncio.sleep(0.1)
            if (is_speaking and not processing and audio_buffer
                    and time.time() - last_speech_time > SILENCE_SECONDS):
                is_speaking = False
                processing = True
                buf = bytearray(audio_buffer)
                audio_buffer = bytearray()
                log.debug(f"Processing {len(buf)} bytes after silence")
                try:
                    history = await process_caller_audio(
                        websocket, buf, history, stream_sid
                    )
                finally:
                    processing = False

    try:
        silence_checker = asyncio.create_task(check_silence())

        while True:
            message = await websocket.receive_text()
            data = json.loads(message)
            event = data.get("event")

            if event == "connected":
                log.info("Exotel WebSocket connected")

            elif event == "start":
                stream_sid = data.get("stream_sid")
                log.info(f"Call started: {stream_sid}")
                greeting = speak(
                    "Welcome to the bank grievance helpline. "
                    "Please tell me your concern and I will assist you."
                )
                await send_audio(websocket, greeting, stream_sid)

            elif event == "media":
                payload = data.get("media", {}).get("payload", "")
                chunk = base64.b64decode(payload)
                level = rms_of(chunk)

                now = time.time()
                if now - last_debug > 1.0:
                    log.debug("RMS: %.0f", level)
                    last_debug = now

                if processing:
                    continue  # ignore audio while the bot is replying

                if level > RMS_THRESHOLD:
                    audio_buffer.extend(chunk)
                    is_speaking = True
                    last_speech_time = now
                elif is_speaking:
                    audio_buffer.extend(chunk)

            elif event == "stop":
                log.info("Call ended")
                break

    except WebSocketDisconnect:
        log.info("Caller disconnected")
    finally:
        if silence_checker:
            silence_checker.cancel()
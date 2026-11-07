from __future__ import annotations

import logging
from datetime import date

from fastapi import FastAPI, File, Request, UploadFile, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from src.agent.graph import run_turn
from src.agent.state import TurnRecord
from backend.exotel_handler import handle_exotel_websocket
from backend.twilio_handler import handle_twilio_inbound, handle_twilio_respond

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="Bank Grievance Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5175"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    session_id: str = "session-1"
    complaint_date: date | None = None
    history: list[TurnRecord] = []


class ReasoningInfo(BaseModel):
    intent: str | None
    confidence: float | None
    urgency: str | None
    sentiment_score: float | None
    should_escalate: bool
    escalation_reason: str | None
    retrieved_context: list[str]


class ChatResponse(BaseModel):
    reply: str
    reasoning: ReasoningInfo
    history: list[TurnRecord]


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest) -> ChatResponse:
    result = run_turn(
        user_message=request.message,
        history=list(request.history),
        session_id=request.session_id,
        complaint_date=request.complaint_date,
    )
    reasoning = ReasoningInfo(
        intent=result["intent"],
        confidence=result["confidence"],
        urgency=result["urgency"],
        sentiment_score=result["sentiment_score"],
        should_escalate=result["should_escalate"],
        escalation_reason=result["escalation_reason"],
        retrieved_context=result["retrieved_context"],
    )
    return ChatResponse(
        reply=result["bot_response"],
        reasoning=reasoning,
        history=result["history"],
    )


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/transcribe")
async def transcribe_endpoint(audio: UploadFile = File(...)) -> dict:
    audio_bytes = await audio.read()
    from src.voice.stt import transcribe
    text = transcribe(audio_bytes, filename=audio.filename or "audio.webm")
    return {"text": text}


class SpeakRequest(BaseModel):
    text: str


@app.post("/speak")
def speak_endpoint(request: SpeakRequest) -> Response:
    from src.voice.tts import speak
    audio = speak(request.text) if request.text else b""
    return Response(content=audio, media_type="audio/mpeg")


@app.websocket("/ws/exotel")
async def exotel_websocket_endpoint(websocket: WebSocket):
    await handle_exotel_websocket(websocket)


@app.post("/voice/twilio")
async def twilio_inbound(request: Request):
    return await handle_twilio_inbound(request)


@app.post("/voice/twilio/respond")
async def twilio_respond(request: Request):
    return await handle_twilio_respond(request)
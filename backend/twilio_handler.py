from __future__ import annotations

import logging
import os
from xml.sax.saxutils import escape

from dotenv import load_dotenv
from fastapi import Request
from fastapi.responses import Response

from src.agent.graph import run_turn

load_dotenv()

log = logging.getLogger(__name__)

# Public URL of this server (for local testing, your ngrok URL).
BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")

GREETING = (
    "Welcome to the bank grievance helpline. "
    "Please tell me your concern after the beep and I will assist you."
)

# Conversation history per call, keyed by Twilio CallSid. Lost on restart.
_sessions: dict[str, list] = {}


def _twiml(body: str) -> Response:
    xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<Response>{body}</Response>'
    return Response(content=xml, media_type="application/xml")


def _say(text: str) -> str:
    return f'<Say voice="alice">{escape(text)}</Say>'


def _listen() -> str:
    return (
        f'<Gather input="speech" action="{BASE_URL}/voice/twilio/respond" method="POST" '
        'speechTimeout="3" speechModel="phone_call" language="en-IN"/>'
        f"<Redirect>{BASE_URL}/voice/twilio</Redirect>"
    )


async def handle_twilio_inbound(request: Request) -> Response:
    form = await request.form()
    _sessions[form.get("CallSid", "unknown")] = []
    return _twiml(_say(GREETING) + _listen())


async def handle_twilio_respond(request: Request) -> Response:
    form = await request.form()
    call_sid = form.get("CallSid", "unknown")
    user_text = form.get("SpeechResult", "").strip()
    log.info("call %s heard: %r", call_sid, user_text)

    if not user_text:
        return _twiml(_say("Sorry, I didn't catch that. Please try again.") + _listen())

    result = run_turn(user_message=user_text, history=_sessions.get(call_sid, []))
    _sessions[call_sid] = result["history"]
    reply = result["bot_response"]
    log.info("call %s replied: %r", call_sid, reply)

    if result["should_escalate"]:
        return _twiml(_say(reply) + "<Hangup/>")
    return _twiml(_say(reply) + _listen())

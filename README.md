# Bank Grievance Helpline Bot

A voice and web agent that takes a bank customer's complaint, works out what it is about, decides whether a human needs to step in, and answers using the applicable RBI policy.

## How it works

A five-node LangGraph pipeline runs once per customer turn:

1. **classify_intent** - Groq LLM returns intent, confidence and urgency as JSON.
2. **assess_signals** - sentiment and a count of how often the same issue has been raised.
3. **escalation_decision** - escalates on repeated issue, negative sentiment, low confidence or an explicit request for a human. On the first turn it asks one clarifying question instead of escalating.
4. **retrieve_context** - picks policy documents that were valid on the complaint date (for example, the RBI Integrated Ombudsman Scheme escalation window).
5. **generate_response** - writes the reply from the retrieved policy.

## Channels

| Path | Speech-to-text | Text-to-speech |
|---|---|---|
| Exotel (WebSocket media stream) | Groq `whisper-large-v3` | ElevenLabs `eleven_multilingual_v2` |
| Twilio (TwiML webhooks) | Twilio `phone_call` speech model | Twilio voice |
| Web demo (React + Vite) | Typed text | Text |

## Stack

FastAPI, uvicorn, LangGraph, Groq (`qwen/qwen3.8-27b`), ElevenLabs, Twilio, Exotel, React + Vite, ngrok for local tunnelling.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in your keys
uvicorn backend.api:app --reload --port 8000
```

Frontend:

```bash
cd frontend && npm install && npm run dev   # http://localhost:5175
```

Voice paths need `ffmpeg` installed and a public tunnel (for example `ngrok http 8000`). For Twilio, set `PUBLIC_BASE_URL` in `.env` to the tunnel URL.

## Tuning notes

- `RMS_THRESHOLD` in `backend/exotel_handler.py` decides what counts as speech on the phone line. It is set to 50; raise it if line noise triggers false turns.
- `qwen/qwen3.8-27b` on Groq does not support `json_object` mode, so JSON is requested through the prompt instead.

## More

Design notes and trade-offs: [docs/case-study.md](docs/case-study.md)

## Status

Prototype. The knowledge base is a few hand-written policy summaries, not an official RBI corpus. Check the ombudsman timelines in `src/knowledge/knowledge_base.py` against the current RBI scheme before relying on them.

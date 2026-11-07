from __future__ import annotations

import json
import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

MODEL = "qwen/qwen3.8-27b"
JSON_SUFFIX = "\n\nRespond with valid JSON only. No markdown, no extra text."

_client: Groq | None = None


def get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not set. Add it to your .env file.")
        _client = Groq(api_key=api_key)
    return _client


def _complete(system_prompt: str, user_prompt: str, temperature: float, max_tokens: int) -> str:
    response = get_client().chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


def chat(system_prompt: str, user_prompt: str, temperature: float = 0.3, max_tokens: int = 600) -> str:
    return _complete(system_prompt, user_prompt, temperature, max_tokens)


def chat_json(system_prompt: str, user_prompt: str, temperature: float = 0.1) -> dict:
    # This model has no json_object mode, so JSON is requested in the prompt
    # and any markdown fence around it is stripped before parsing.
    raw = _complete(system_prompt + JSON_SUFFIX, user_prompt, temperature, 600)
    cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(cleaned)

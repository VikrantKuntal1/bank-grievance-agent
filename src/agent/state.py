from __future__ import annotations

from datetime import date
from typing import Literal, TypedDict

Intent = Literal[
    "faq",
    "transaction_dispute",
    "card_related",
    "account_access",
    "loan_credit",
    "general_complaint",
    "human_request",
]

Urgency = Literal["low", "medium", "high"]

class TurnRecord(TypedDict):
    user_message: str
    intent: Intent
    urgency: Urgency
    bot_response: str
    escalated: bool

class GrievanceState(TypedDict):
    session_id: str
    complaint_date: date
    user_message: str

    intent: Intent | None
    confidence: float | None
    urgency: Urgency | None

    sentiment_score: float | None
    repeated_intent_count: int

    retrieved_context: list[str]

    should_escalate: bool
    escalation_reason: str | None

    bot_response: str | None
    history: list[TurnRecord]
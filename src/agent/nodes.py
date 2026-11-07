from __future__ import annotations

from src.agent.state import GrievanceState, Intent, TurnRecord, Urgency
from src.knowledge.retriever import retrieve, retrieve_ombudsman_rule
from src.llm.client import chat, chat_json

ESCALATION_REPEAT_THRESHOLD = 2
ESCALATION_SENTIMENT_THRESHOLD = -0.4
ESCALATION_CONFIDENCE_THRESHOLD = 0.55
HIGH_URGENCY_INTENTS = {"transaction_dispute", "card_related", "account_access"}

INTENT_PROMPT = """You are an intent classifier for a bank customer service system.
Classify the customer's message into exactly one of these intents:
- faq: general question, customer hasn't tried anything yet
- transaction_dispute: unauthorized, failed, or duplicate transaction
- card_related: card blocked, not working, lost, stolen, or replacement
- account_access: login, OTP, or mobile banking access issues
- loan_credit: EMI, credit score, or foreclosure issues
- general_complaint: dissatisfaction that does not fit the categories above
- human_request: customer explicitly asking for a human or to file a formal complaint

Also return:
- confidence: float between 0 and 1
- urgency: "low", "medium", or "high"

Respond ONLY with JSON: {"intent": "...", "confidence": 0.0, "urgency": "..."}"""

SENTIMENT_PROMPT = """You are a sentiment analyzer for a bank customer service system.
Rate the emotional tone of the customer's message from -1.0 to 1.0:
- -1.0: very frustrated, angry, or distressed
-  0.0: neutral, purely informational
- +1.0: very positive or satisfied

Respond ONLY with JSON: {"sentiment_score": 0.0}"""

RESPONSE_PROMPT = """You are a helpful, honest bank customer service assistant.
You are given retrieved policy context. Use it to give accurate, specific guidance.
Never say "use the app" if the customer has already said the app didn't work.
Never repeat a suggestion that already failed in an earlier turn.

If escalation has NOT been triggered and this is the FIRST turn on this issue:
- Acknowledge the issue briefly
- Ask ONE specific clarifying question to understand the problem better
  (e.g. "Is the card declining at an ATM, online, or at a point-of-sale terminal?")
- Do NOT offer solutions yet

If escalation has been triggered, clearly tell the customer:
1. That you are connecting them to a human agent right now
2. If the agent is busy, the customer will be asked to hold
3. If the customer does not want to hold, they will receive a callback within 3 hours
4. Never mention "3 business days". That is too slow for an urgent issue

Keep responses to 2-4 sentences.
Respond in the same language as the customer."""


def classify_intent_node(state: GrievanceState) -> dict:
    result = chat_json(INTENT_PROMPT, state["user_message"])
    intent: Intent = result.get("intent", "general_complaint")
    urgency: Urgency = result.get("urgency", "medium")
    return {
        "intent": intent,
        "confidence": float(result.get("confidence", 0.5)),
        "urgency": urgency,
    }


def assess_signals_node(state: GrievanceState) -> dict:
    result = chat_json(SENTIMENT_PROMPT, state["user_message"])
    repeated = sum(1 for turn in state["history"] if turn["intent"] == state["intent"])
    return {
        "sentiment_score": float(result.get("sentiment_score", 0.0)),
        "repeated_intent_count": repeated,
    }


def escalation_decision_node(state: GrievanceState) -> dict:
    reasons = []

    if state["repeated_intent_count"] >= ESCALATION_REPEAT_THRESHOLD:
        reasons.append(
            f"Same issue raised {state['repeated_intent_count'] + 1} times without resolution"
        )

    if state["sentiment_score"] is not None and state["sentiment_score"] <= ESCALATION_SENTIMENT_THRESHOLD:
        reasons.append("Customer sentiment shows significant frustration or distress")

    if state["confidence"] is not None and state["confidence"] <= ESCALATION_CONFIDENCE_THRESHOLD:
        reasons.append("Low confidence in intent classification")

    if state["intent"] == "human_request":
        reasons.append("Customer explicitly requested a human agent")

    if state["urgency"] == "high":
        if state["intent"] not in HIGH_URGENCY_INTENTS:
            reasons.append("Customer indicated urgency")
        elif any(turn["intent"] == state["intent"] for turn in state["history"]):
            # High-urgency intents get one clarifying question first, so only
            # escalate when the same intent has already come up in an earlier turn.
            reasons.append(f"High urgency issue raised again: {state['intent']}")

    return {
        "should_escalate": bool(reasons),
        "escalation_reason": "; ".join(reasons) or None,
    }


def retrieve_context_node(state: GrievanceState) -> dict:
    contexts = []

    if state["should_escalate"] or state["intent"] == "human_request":
        rule = retrieve_ombudsman_rule(state["complaint_date"])
        contexts.append(f"[{rule.doc.title}] {rule.doc.content}")

    for hit in retrieve(state["user_message"], k=2, complaint_date=state["complaint_date"]):
        snippet = f"[{hit.doc.title}] {hit.doc.content}"
        if snippet not in contexts:
            contexts.append(snippet)

    return {"retrieved_context": contexts}


def generate_response_node(state: GrievanceState) -> dict:
    recent = "\n".join(
        f'- Customer: "{t["user_message"]}" | intent: {t["intent"]} | '
        f'bot replied: "{t["bot_response"]}" | escalated: {t["escalated"]}'
        for t in state["history"][-3:]
    ) or "No prior turns."

    context = "\n".join(state["retrieved_context"]) or "No policy context found."

    if state["should_escalate"]:
        escalation = f"ESCALATION TRIGGERED. Reason: {state['escalation_reason']}"
    else:
        escalation = "No escalation triggered."

    user_prompt = f"""Customer's message: "{state['user_message']}"
Intent: {state['intent']} (confidence: {state['confidence']:.2f})
Urgency: {state['urgency']}
Sentiment: {state['sentiment_score']:.2f}

Recent conversation:
{recent}

Retrieved policy context:
{context}

{escalation}

Write the reply to send to the customer."""

    reply = chat(RESPONSE_PROMPT, user_prompt, temperature=0.4)

    turn: TurnRecord = {
        "user_message": state["user_message"],
        "intent": state["intent"],
        "urgency": state["urgency"],
        "bot_response": reply,
        "escalated": state["should_escalate"],
    }
    return {"bot_response": reply, "history": state["history"] + [turn]}

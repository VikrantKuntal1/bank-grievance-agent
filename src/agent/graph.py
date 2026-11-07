from __future__ import annotations

from datetime import date

from langgraph.graph import END, StateGraph

from src.agent.state import GrievanceState
from src.agent.nodes import (
    classify_intent_node,
    assess_signals_node,
    escalation_decision_node,
    retrieve_context_node,
    generate_response_node,
)


def build_graph():
    graph = StateGraph(GrievanceState)

    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("assess_signals", assess_signals_node)
    graph.add_node("escalation_decision", escalation_decision_node)
    graph.add_node("retrieve_context", retrieve_context_node)
    graph.add_node("generate_response", generate_response_node)

    graph.set_entry_point("classify_intent")

    graph.add_edge("classify_intent", "assess_signals")
    graph.add_edge("assess_signals", "escalation_decision")
    graph.add_edge("escalation_decision", "retrieve_context")
    graph.add_edge("retrieve_context", "generate_response")
    graph.add_edge("generate_response", END)

    return graph.compile()

_compiled_graph = None

def get_compiled_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph

def make_initial_state(
    user_message: str,
    session_id: str = "session-1",
    complaint_date: date | None = None,
    history: list | None = None,
) -> GrievanceState:
    return GrievanceState(
        session_id=session_id,
        complaint_date=complaint_date or date.today(),
        user_message=user_message,
        intent=None,
        confidence=None,
        urgency=None,
        sentiment_score=None,
        repeated_intent_count=0,
        retrieved_context=[],
        should_escalate=False,
        escalation_reason=None,
        bot_response=None,
        history=history or [],
    )

def run_turn(
    user_message: str,
    history: list,
    session_id: str = "session-1",
    complaint_date: date | None = None,
) -> GrievanceState:
    state = make_initial_state(
        user_message=user_message,
        session_id=session_id,
        complaint_date=complaint_date,
        history=history,
    )
    graph = get_compiled_graph()
    return graph.invoke(state)
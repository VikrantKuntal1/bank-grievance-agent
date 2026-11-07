from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class PolicyDoc:
    doc_id: str
    title: str
    category: str
    content: str
    valid_from: date
    valid_until: date | None = None
    tags: list[str] = field(default_factory=list)


KNOWLEDGE_BASE: list[PolicyDoc] = [
    PolicyDoc(
        doc_id="RBIOS-2021-01",
        title="RBI Integrated Ombudsman Scheme 2021 -- Escalation Window",
        category="ombudsman_scheme",
        valid_from=date(2021, 1, 1),
        valid_until=date(2026, 6, 30),
        tags=["ombudsman", "timeline", "2021"],
        content=(
            "Under the RBI Integrated Ombudsman Scheme 2021, a customer must first file a "
            "complaint with their bank. If the bank does not respond within 30 days, or the "
            "customer is unsatisfied with the response, the customer may escalate to the RBI "
            "Ombudsman within ONE YEAR from the bank's response or the expiry of the 30-day "
            "window. This scheme governs complaints filed before 1 July 2026."
        ),
    ),
    PolicyDoc(
        doc_id="RBIOS-2026-01",
        title="RBI Integrated Ombudsman Scheme 2026 -- Escalation Window",
        category="ombudsman_scheme",
        valid_from=date(2026, 7, 1),
        valid_until=None,
        tags=["ombudsman", "timeline", "2026"],
        content=(
            "From 1 July 2026, the RBI Integrated Ombudsman Scheme 2026 replaces the 2021 "
            "scheme. A customer must still first approach the bank directly. If the bank "
            "does not respond within 30 days, or the customer is dissatisfied, the customer "
            "may escalate to the RBI Ombudsman within 90 DAYS (reduced from one year) from "
            "the expiry of the bank's response window or its last communication, whichever "
            "is later."
        ),
    ),
    PolicyDoc(
        doc_id="BANK-ESC-01",
        title="Generic Bank -- Internal Grievance Escalation Matrix",
        category="escalation_matrix",
        valid_from=date(2020, 1, 1),
        valid_until=None,
        tags=["escalation", "grievance_officer"],
        content=(
            "Level 1: customer care helpline or chatbot, target first response within 3 "
            "business days. Level 2: if unresolved, the customer may write to the bank's "
            "Grievance Redressal Officer, typically reachable via a dedicated email listed "
            "on the bank's website, target resolution within 7-10 business days. Level 3: "
            "if still unresolved after 30 days total, the customer may escalate to the RBI "
            "Ombudsman."
        ),
    ),
    PolicyDoc(
        doc_id="BANK-ESC-02",
        title="Generic Bank -- When a Bot Should Escalate to a Human",
        category="escalation_matrix",
        valid_from=date(2020, 1, 1),
        valid_until=None,
        tags=["escalation", "human_handoff"],
        content=(
            "An automated assistant should hand off to a human agent when: the same "
            "complaint is repeated without resolution, the customer expresses frustration "
            "or distress, the query involves fraud or account security, confidence in "
            "intent classification is low, or the customer explicitly asks for a human."
        ),
    ),
    PolicyDoc(
        doc_id="BANK-CAT-01",
        title="Generic Bank -- Complaint Category Definitions",
        category="complaint_category",
        valid_from=date(2020, 1, 1),
        valid_until=None,
        tags=["categories", "intent"],
        content=(
            "Common complaint categories: Transaction Dispute (unauthorized or duplicate "
            "charge), Card-Related (card blocked or fraudulent use), Account Access (login "
            "or OTP failures), Loan/Credit (incorrect EMI deduction). Transaction Dispute "
            "and Card-Related issues involving possible fraud default to HIGH urgency."
        ),
    ),
]


def get_applicable_ombudsman_doc(complaint_date: date) -> PolicyDoc:
    candidates = [
        doc for doc in KNOWLEDGE_BASE
        if doc.category == "ombudsman_scheme"
        and doc.valid_from <= complaint_date
        and (doc.valid_until is None or complaint_date <= doc.valid_until)
    ]
    if not candidates:
        raise ValueError(f"No applicable ombudsman scheme found for complaint date {complaint_date}")
    return candidates[0]


def all_documents() -> list[PolicyDoc]:
    return KNOWLEDGE_BASE

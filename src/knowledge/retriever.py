from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.knowledge.knowledge_base import PolicyDoc, all_documents, get_applicable_ombudsman_doc


@dataclass
class RetrievedDoc:
    doc: PolicyDoc
    score: float


_EMBEDDER = None
_DOC_EMBEDDINGS = None
_DOCS: list[PolicyDoc] = all_documents()


def _get_embedder():
    global _EMBEDDER
    if _EMBEDDER is None:
        from sentence_transformers import SentenceTransformer
        _EMBEDDER = SentenceTransformer("all-MiniLM-L6-v2")
    return _EMBEDDER


def _build_doc_embeddings():
    global _DOC_EMBEDDINGS
    embedder = _get_embedder()
    texts = [f"{d.title}. {d.content}" for d in _DOCS]
    embeddings = embedder.encode(texts, normalize_embeddings=True)
    _DOC_EMBEDDINGS = embeddings
    return _DOC_EMBEDDINGS


def retrieve(query: str, k: int = 3, complaint_date: date | None = None) -> list[RetrievedDoc]:
    global _DOC_EMBEDDINGS
    if _DOC_EMBEDDINGS is None:
        _build_doc_embeddings()

    eligible_idx = []
    for i, d in enumerate(_DOCS):
        if complaint_date and d.category == "ombudsman_scheme":
            if not (d.valid_from <= complaint_date and (d.valid_until is None or complaint_date <= d.valid_until)):
                continue
        eligible_idx.append(i)

    embedder = _get_embedder()
    q_embedding = embedder.encode([query], normalize_embeddings=True)[0]

    scored = []
    for i in eligible_idx:
        score = float(_DOC_EMBEDDINGS[i] @ q_embedding)
        scored.append((i, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    top_k = scored[:k]
    return [RetrievedDoc(doc=_DOCS[i], score=score) for i, score in top_k]


def retrieve_ombudsman_rule(complaint_date: date) -> RetrievedDoc:
    doc = get_applicable_ombudsman_doc(complaint_date)
    return RetrievedDoc(doc=doc, score=1.0)

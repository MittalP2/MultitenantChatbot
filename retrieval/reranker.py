"""
Second-stage reranker for financial RAG.

Stage 1 (retriever) is cheap TF-IDF cosine over the whole index.
Stage 2 re-scores a short candidate list with signals TF-IDF often misses
in 10-K prose: exact phrases, ticker/entity hits, and number/year overlap.
"""

from __future__ import annotations

import re
from typing import Dict, List, Sequence

from ingestion.embedder import tokenize

_YEAR = re.compile(r"\b(20[0-3][0-9])\b")
_TICKER = re.compile(r"\b(TSLA|HOG|PII|F|GM|HMC|TM|BMW)\b", re.I)
_NUMBER = re.compile(r"\b\d[\d,]*(?:\.\d+)?\b")


def _phrases(question: str) -> List[str]:
    q = question.lower().strip()
    words = [w for w in re.findall(r"[a-z0-9]+", q) if len(w) > 2]
    phrases = []
    for n in (3, 2):
        for i in range(len(words) - n + 1):
            phrases.append(" ".join(words[i : i + n]))
    return phrases


def rerank_score(question: str, chunk: Dict) -> float:
    text = chunk.get("text") or ""
    text_l = text.lower()
    q_tokens = set(tokenize(question))
    c_tokens = set(tokenize(text))
    overlap = len(q_tokens & c_tokens) / max(len(q_tokens), 1)

    phrase_hits = sum(1 for p in _phrases(question) if p in text_l)
    years_q = set(_YEAR.findall(question))
    years_c = set(_YEAR.findall(text))
    year_hit = 1.0 if years_q and years_q & years_c else 0.0

    tickers_q = {t.upper() for t in _TICKER.findall(question)}
    tickers_c = {t.upper() for t in _TICKER.findall(text)}
    ticker_hit = 1.0 if tickers_q and tickers_q & tickers_c else 0.0

    doc = (chunk.get("document") or "").lower()
    doc_bonus = 0.0
    for token in q_tokens:
        if token in doc:
            doc_bonus += 0.08

    q_wants_number = bool(_NUMBER.search(question)) or bool(
        q_tokens & {"revenue", "sales", "deliveries", "risk", "percent", "margin"}
    )
    number_hit = 1.0 if q_wants_number and _NUMBER.search(text) else 0.0

    base = float(chunk.get("score") or 0.0)
    return (
        0.55 * base
        + 0.25 * overlap
        + 0.08 * min(phrase_hits, 4)
        + 0.06 * year_hit
        + 0.05 * ticker_hit
        + 0.04 * number_hit
        + min(doc_bonus, 0.16)
    )


def rerank(
    question: str,
    chunks: Sequence[Dict],
    top_k: int = 5,
) -> List[Dict]:
    scored: List[Dict] = []
    for chunk in chunks:
        item = dict(chunk)
        item["tfidf_score"] = float(chunk.get("score") or 0.0)
        item["score"] = rerank_score(question, chunk)
        scored.append(item)
    scored.sort(key=lambda c: c["score"], reverse=True)
    return scored[:top_k]

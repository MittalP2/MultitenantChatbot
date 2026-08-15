"""Retrieve relevant chunks for a user question (local TF-IDF + light re-rank)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from ingestion.embedder import embed_texts, set_vectorizer, tokenize
from retrieval.vector_store import SimpleVectorStore


DEFAULT_STORE = Path(__file__).resolve().parents[1] / "storage" / "bmw"

# Map casual question language → wording used in BMW investor reports.
_QUERY_EXPANSIONS: Tuple[Tuple[Set[str], str], ...] = (
    (
        {"employee", "employees", "workforce", "headcount", "staff", "personnel"},
        "Employees at year-end number of employees workforce personnel",
    ),
    (
        {"revenue", "revenues", "sales", "turnover"},
        "Group revenues Automotive revenues net sales",
    ),
    (
        {"profit", "earnings", "ebt", "pre-tax", "pretax"},
        "Profit before tax Group profit EBT",
    ),
    (
        {"ebit", "operating", "margin"},
        "EBIT margin Automotive segment operating profit",
    ),
    (
        {"delivery", "deliveries", "volume", "volumes", "units"},
        "Deliveries Automotive segment vehicles delivered",
    ),
    (
        {"electric", "bev", "ev", "all-electric", "battery"},
        "Share of all-electric cars in deliveries electrified",
    ),
    (
        {"dividend", "payout"},
        "Dividend ordinary share preferred share",
    ),
    (
        {"cash", "fcf"},
        "Free cash flow Automotive segment",
    ),
    (
        {"outlook", "guidance", "forecast", "expect"},
        "Outlook key performance indicators forecast",
    ),
)


def get_store(persist_dir: Optional[Path] = None) -> SimpleVectorStore:
    store = SimpleVectorStore(persist_dir or DEFAULT_STORE)
    store.load()
    set_vectorizer(store.vectorizer)
    return store


def _years_in_text(text: str) -> Set[str]:
    return set(re.findall(r"\b(20[2-3][0-9])\b", text))


def _normalize_tokens(question: str) -> Set[str]:
    tokens = set(tokenize(question))
    # Common stem/typo bridges so "employess" still hits employee expansions.
    bridged = set(tokens)
    for t in tokens:
        if t.startswith("employ"):
            bridged.update({"employee", "employees"})
        if t.startswith("revenu"):
            bridged.update({"revenue", "revenues"})
        if t.startswith("deliver"):
            bridged.update({"delivery", "deliveries"})
    return bridged


def expand_query(question: str) -> str:
    """Augment the question with report-native phrases for better TF-IDF match."""
    tokens = _normalize_tokens(question)
    extras: List[str] = []
    for triggers, phrase in _QUERY_EXPANSIONS:
        if tokens & triggers:
            extras.append(phrase)
    years = _years_in_text(question)
    if years:
        extras.append(" ".join(f"BMW Group Report {y}" for y in sorted(years)))
        extras.append("KEY PERFORMANCE INDICATORS BMW Group in Figures")
    if not extras:
        return question
    return f"{question} {' '.join(extras)}"


def _lexical_bonus(question: str, chunk: Dict) -> float:
    """Boost chunks that share year + topical terms with the question."""
    q_years = _years_in_text(question)
    doc = chunk.get("document", "")
    text = chunk.get("text", "")
    text_l = text.lower()
    bonus = 0.0

    # Prefer the report year named in the question.
    for y in q_years:
        if y in doc:
            bonus += 0.12
        # KPI tables often list several years; reward explicit year tokens.
        if re.search(rf"\b{y}\b", text):
            bonus += 0.05

    q_tokens = _normalize_tokens(question)
    # Strong KPI phrases that appear in figures pages.
    phrase_hits = 0
    for phrase in (
        "employees at year",
        "key performance indicators",
        "group revenues",
        "profit/loss before tax",
        "profit before tax",
        "ebit margin",
        "free cash flow",
        "share of all-electric",
        "deliveries",
    ):
        if phrase in text_l and q_tokens & set(tokenize(phrase)):
            phrase_hits += 1
    bonus += min(0.18, 0.06 * phrase_hits)

    # Group headcount KPI beats sustainability/regional employee tables.
    if q_tokens & {"employee", "employees", "headcount", "workforce", "personnel", "staff"}:
        if "employees at year" in text_l:
            bonus += 0.28
        if "key performance indicators" in text_l and "employees at year" in text_l:
            bonus += 0.12
        # Down-rank safety / regional breakdown pages for "total employees" questions.
        if any(
            n in text_l
            for n in (
                "work-related",
                "work -related",
                "accident frequency",
                "employees by contract type",
                "employees by geographical",
            )
        ):
            bonus -= 0.15

    # Soft prefer “in Figures” pages for numeric KPI questions.
    if q_tokens & {
        "employee",
        "employees",
        "revenue",
        "revenues",
        "profit",
        "ebit",
        "delivery",
        "deliveries",
        "dividend",
        "headcount",
        "workforce",
    }:
        if "bmw group in figures" in text_l or "key performance indicators" in text_l:
            bonus += 0.1

    # Prefer Group profit KPI wording over tax-note reconciliations.
    if q_tokens & {"profit", "ebt"} and "profit before tax" in text_l:
        if "key performance indicators" in text_l or "bmw group in figures" in text_l:
            bonus += 0.15
        if "tax rate applicable" in text_l or "expected tax expense" in text_l:
            bonus -= 0.08

    return bonus


def _keyword_candidates(store: SimpleVectorStore, question: str, limit: int = 40) -> List[Dict]:
    """Find chunks by report phrases TF-IDF often misses (dense KPI tables)."""
    q_tokens = _normalize_tokens(question)
    q_years = _years_in_text(question)
    needles: List[str] = []

    if q_tokens & {"employee", "employees", "headcount", "workforce", "personnel", "staff"}:
        needles.extend(
            [
                "employees at year",
                "employed 154",  # weak; prefer phrase above
                "employees at year-end",
            ]
        )
    if q_tokens & {"revenue", "revenues"}:
        needles.append("group revenues")
    if q_tokens & {"profit", "ebt"}:
        needles.extend(["profit/loss before tax", "profit before tax"])
    if q_tokens & {"ebit", "margin"}:
        needles.append("ebit margin in the automotive")
    if q_tokens & {"delivery", "deliveries"}:
        needles.append("deliveries")
    if q_tokens & {"dividend"}:
        needles.append("dividend")
    if q_tokens & {"electric", "bev"}:
        needles.append("share of all-electric")
    if not needles:
        return []

    scored: List[Tuple[float, int]] = []
    for i, chunk in enumerate(store.chunks):
        if chunk.get("tenant_id") != "bmw" and chunk.get("tenant_id") is not None:
            # tenant filter applied by caller usually; keep bmw-focused here
            pass
        text_l = chunk.get("text", "").lower()
        hit = sum(1 for n in needles if n in text_l)
        if not hit:
            continue
        score = float(hit)
        doc = chunk.get("document", "")
        for y in q_years:
            if y in doc:
                score += 2.0
            if y in text_l:
                score += 0.5
        if "key performance indicators" in text_l:
            score += 1.5
        if "bmw group in figures" in text_l:
            score += 1.0
        scored.append((score, i))

    scored.sort(reverse=True)
    out: List[Dict] = []
    for score, i in scored[:limit]:
        item = dict(store.chunks[i])
        item["score"] = 0.15 + 0.05 * score  # base so re-rank bonuses can lift them
        out.append(item)
    return out


def retrieve(
    question: str,
    top_k: int = 5,
    tenant_id: str = "bmw",
    persist_dir: Optional[Path] = None,
) -> List[Dict]:
    store = get_store(persist_dir)
    expanded = expand_query(question)
    query_vec = embed_texts([expanded])
    # Over-fetch dense semantic candidates, then merge lexical KPI hits.
    candidates = store.search(
        query_vec, top_k=max(top_k * 12, 80), tenant_id=tenant_id
    )
    lexical = _keyword_candidates(store, question, limit=40)
    if tenant_id is not None:
        lexical = [c for c in lexical if c.get("tenant_id") == tenant_id]

    merged: Dict[str, Dict] = {}
    for c in candidates + lexical:
        key = c.get("chunk_id") or f"{c.get('document')}:{c.get('page')}:{c.get('text', '')[:80]}"
        prev = merged.get(key)
        if prev is None or float(c.get("score", 0)) > float(prev.get("score", 0)):
            merged[key] = dict(c)

    pool = list(merged.values())
    for c in pool:
        c["score"] = float(c.get("score", 0.0)) + _lexical_bonus(question, c)
    pool.sort(key=lambda c: c["score"], reverse=True)
    return pool[:top_k]


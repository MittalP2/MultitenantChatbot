"""
Neutral retriever for the Week 2 SEC corpus.

Unlike retrieval/retriever.py this path has no BMW-specific query expansion,
so chunking and rerank comparisons stay honest.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from ingestion.embedder import embed_texts, set_vectorizer
from retrieval.reranker import rerank
from retrieval.vector_store import SimpleVectorStore


def load_finance_store(persist_dir: Path) -> SimpleVectorStore:
    store = SimpleVectorStore(persist_dir)
    store.load()
    set_vectorizer(store.vectorizer)
    return store


def hits_payload(chunks: List[Dict], limit: int = 5) -> List[Dict]:
    out = []
    for c in chunks[:limit]:
        out.append(
            {
                "document": c.get("document"),
                "page": c.get("page"),
                "score": round(float(c.get("score") or 0), 3),
                "text": (c.get("text") or "")[:400],
            }
        )
    return out


def retrieve_finance(
    question: str,
    persist_dir: Path,
    top_k: int = 5,
    tenant_id: str = "sec",
    use_rerank: bool = False,
    candidate_k: int = 20,
) -> List[Dict]:
    store = load_finance_store(persist_dir)
    query_vec = embed_texts([question])
    pool_k = candidate_k if use_rerank else top_k
    hits = store.search(query_vec, top_k=pool_k, tenant_id=tenant_id)
    if use_rerank:
        return rerank(question, hits, top_k=top_k)
    return hits[:top_k]

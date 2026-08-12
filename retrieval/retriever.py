"""Retrieve relevant chunks for a user question."""

from pathlib import Path
from typing import Dict, List, Optional

from ingestion.embedder import embed_texts
from retrieval.vector_store import SimpleVectorStore


DEFAULT_STORE = Path(__file__).resolve().parents[1] / "storage" / "bmw"


def get_store(persist_dir: Optional[Path] = None) -> SimpleVectorStore:
    store = SimpleVectorStore(persist_dir or DEFAULT_STORE)
    store.load()
    return store


def retrieve(
    question: str,
    top_k: int = 5,
    tenant_id: str = "bmw",
    persist_dir: Optional[Path] = None,
) -> List[Dict]:
    store = get_store(persist_dir)
    query_vec = embed_texts([question])[0]
    return store.search(query_vec, top_k=top_k, tenant_id=tenant_id)

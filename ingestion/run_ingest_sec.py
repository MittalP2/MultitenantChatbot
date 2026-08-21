"""
Ingest the 3 SEC 10-K extracts twice: fixed-size chunks and semantic chunks.

Usage (from project root):
  py -3.12 ingestion/run_ingest_sec.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ingestion.chunker import chunk_pages
from ingestion.doc_loader import load_documents_from_dir
from ingestion.embedder import fit_vectorizer
from ingestion.semantic_chunker import semantic_chunk_pages
from retrieval.vector_store import SimpleVectorStore


def _save(chunks: list, store_dir: Path, label: str) -> None:
    texts = [c["text"] for c in chunks]
    print(f"Fitting TF-IDF for {label} ({len(chunks)} chunks)...")
    vectorizer = fit_vectorizer(texts)
    matrix = vectorizer.transform(texts)
    store = SimpleVectorStore(store_dir)
    store.add(chunks, matrix, vectorizer)
    store.save()
    print(f"Saved {len(chunks)} chunks -> {store_dir}")


def main() -> None:
    load_dotenv(ROOT / ".env")
    data_dir = ROOT / "data" / "sec"
    print(f"Loading SEC extracts from {data_dir}")
    pages = load_documents_from_dir(data_dir)
    print(f"Total pages with text: {len(pages)}")

    fixed = chunk_pages(pages, chunk_size=800, chunk_overlap=150, tenant_id="sec")
    for c in fixed:
        c["strategy"] = "fixed"
    _save(fixed, ROOT / "storage" / "sec_fixed", "fixed-size")

    semantic = semantic_chunk_pages(pages, tenant_id="sec")
    _save(semantic, ROOT / "storage" / "sec_semantic", "semantic")
    print("Done. Next: py -3.12 eval/run_eval.py")


if __name__ == "__main__":
    main()

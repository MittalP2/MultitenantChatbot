"""
Week 1 — Ingest BMW PDFs into a local TF-IDF vector store.

No OpenAI / Cursor API key required.
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ingestion.chunker import chunk_pages
from ingestion.embedder import fit_vectorizer
from ingestion.pdf_loader import load_pdfs_from_dir
from retrieval.vector_store import SimpleVectorStore


def main() -> None:
    load_dotenv(ROOT / ".env")

    data_dir = ROOT / "data" / "bmw"
    store_dir = ROOT / "storage" / "bmw"

    print(f"Loading PDFs from {data_dir}")
    pages = load_pdfs_from_dir(data_dir)
    print(f"Total pages with text: {len(pages)}")

    chunks = chunk_pages(pages, chunk_size=800, chunk_overlap=150, tenant_id="bmw")
    print(f"Total chunks: {len(chunks)}")

    texts = [c["text"] for c in chunks]
    print("Fitting local TF-IDF vectors (no API key)...")
    vectorizer = fit_vectorizer(texts)
    matrix = vectorizer.transform(texts)

    store = SimpleVectorStore(store_dir)
    store.add(chunks, matrix, vectorizer)
    store.save()
    print(f"Saved {len(chunks)} chunks -> {store_dir}")
    print("Done. Next: python app/cli_chat.py")


if __name__ == "__main__":
    main()

"""
Week 1 — Ingest BMW PDFs into a local vector store.

Pipeline:
  PDF → extract text (per page) → chunk → embed → save vectors
"""

import sys
from pathlib import Path

from dotenv import load_dotenv
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ingestion.chunker import chunk_pages
from ingestion.embedder import embed_texts
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
    print("Creating embeddings (OpenAI)...")
    vectors = []
    batch_size = 64
    for i in tqdm(range(0, len(texts), batch_size), desc="embed"):
        batch = texts[i : i + batch_size]
        vectors.extend(embed_texts(batch, batch_size=len(batch)))

    store = SimpleVectorStore(store_dir)
    store.add(chunks, vectors)
    store.save()
    print(f"Saved {len(chunks)} chunks → {store_dir}")
    print("Done. Next: streamlit run app/streamlit_app.py")


if __name__ == "__main__":
    main()

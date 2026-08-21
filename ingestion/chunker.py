"""Split page text into overlapping chunks for embedding."""

from typing import Dict, List


def chunk_pages(
    pages: List[Dict],
    chunk_size: int = 800,
    chunk_overlap: int = 150,
    tenant_id: str = "bmw",
) -> List[Dict]:
    """
    Chunk by character count (simple + predictable for learning).

    Each chunk keeps metadata so retrieval can cite sources later:
    tenant_id, document, page, chunk_id
    """
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    chunks: List[Dict] = []
    for page in pages:
        text = page["text"]
        start = 0
        part = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            piece = text[start:end].strip()
            if piece:
                chunk_id = f"{page['document']}::p{page['page']}::{part}"
                chunks.append(
                    {
                        "text": piece,
                        "tenant_id": tenant_id,
                        "document": page["document"],
                        "page": page["page"],
                        "chunk_id": chunk_id,
                        "strategy": "fixed",
                    }
                )
                part += 1
            if end >= len(text):
                break
            start = end - chunk_overlap
    return chunks

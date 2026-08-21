"""
Semantic chunking for SEC-style documents.

Fixed-size chunking cuts every N characters. This splitter:
1. Breaks on Item / heading boundaries (document structure)
2. Splits remaining prose into sentences
3. Grows a chunk while the next sentence is similar (TF-IDF cosine)
4. Starts a new chunk when similarity drops or max size is hit

No neural embeddings — same local TF-IDF the rest of Week 2 uses.
"""

from __future__ import annotations

import re
from typing import Dict, List

import numpy as np

from ingestion.embedder import TfidfModel

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"“])")
_HEADING = re.compile(
    r"(?m)^(=+\s*)?(item\s+\d+[a-z]?\.?\s+[^\n]{3,80}|#{1,3}\s+[^\n]+)$",
    re.I,
)


def _sentences(text: str) -> List[str]:
    text = " ".join(text.split())
    parts = _SENT_SPLIT.split(text) if text else []
    out: List[str] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if out and len(part) < 40:
            out[-1] = f"{out[-1]} {part}"
        else:
            out.append(part)
    return out or ([text] if text else [])


def _split_by_headings(text: str) -> List[str]:
    indices = [m.start() for m in _HEADING.finditer(text)]
    if not indices:
        return [text] if text.strip() else []
    if indices[0] != 0:
        indices = [0] + indices
    blocks = []
    for i, start in enumerate(indices):
        end = indices[i + 1] if i + 1 < len(indices) else len(text)
        block = text[start:end].strip()
        if block:
            blocks.append(block)
    return blocks


def _group_sentences(
    sents: List[str],
    vectors: np.ndarray,
    max_chars: int,
    min_chars: int,
    threshold: float,
) -> List[str]:
    if not sents:
        return []
    chunks: List[str] = []
    start = 0
    current_vec = vectors[0].copy()
    current_len = len(sents[0])

    def flush(end: int) -> None:
        piece = " ".join(sents[start:end]).strip()
        if piece:
            chunks.append(piece)

    for i in range(1, len(sents)):
        nxt = vectors[i]
        denom = float(np.linalg.norm(current_vec) * np.linalg.norm(nxt)) or 1.0
        sim = float(current_vec @ nxt) / denom
        would = current_len + 1 + len(sents[i])
        topic_break = sim < threshold and current_len >= min_chars
        too_long = would > max_chars
        if topic_break or too_long:
            flush(i)
            start = i
            current_vec = nxt.copy()
            current_len = len(sents[i])
        else:
            current_vec = current_vec + nxt
            current_len = would
    flush(len(sents))
    return chunks


def semantic_chunk_pages(
    pages: List[Dict],
    tenant_id: str = "sec",
    max_chars: int = 1600,
    min_chars: int = 600,
    similarity_threshold: float = 0.12,
) -> List[Dict]:
    """Group neighboring sentences that talk about the same thing."""
    work: List[tuple] = []
    all_sents: List[str] = []
    for page in pages:
        for block in _split_by_headings(page["text"]):
            sents = _sentences(block)
            if not sents:
                continue
            work.append((page, sents, len(all_sents), len(all_sents) + len(sents)))
            all_sents.extend(sents)

    if not all_sents:
        return []

    model = TfidfModel(max_features=4000).fit(all_sents)
    vectors = model.transform(all_sents)

    chunks: List[Dict] = []
    for page, sents, lo, hi in work:
        grouped = _group_sentences(
            sents,
            vectors[lo:hi],
            max_chars=max_chars,
            min_chars=min_chars,
            threshold=similarity_threshold,
        )
        for part, piece in enumerate(grouped):
            if len(piece) < 80:
                continue
            chunks.append(
                {
                    "text": piece,
                    "tenant_id": tenant_id,
                    "document": page["document"],
                    "page": page["page"],
                    "chunk_id": f"{page['document']}::p{page['page']}::sem{part}",
                    "strategy": "semantic",
                }
            )
    return chunks

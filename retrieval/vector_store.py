"""Minimal local vector store (numpy + pickle). Easy to inspect while learning."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np


class SimpleVectorStore:
    def __init__(self, persist_dir: Path):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.meta_path = self.persist_dir / "chunks.json"
        self.vec_path = self.persist_dir / "embeddings.npy"
        self.chunks: List[Dict] = []
        self.embeddings: Optional[np.ndarray] = None

    def add(self, chunks: List[Dict], embeddings: List[List[float]]) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings length mismatch")
        self.chunks = chunks
        self.embeddings = np.array(embeddings, dtype=np.float32)
        # normalize for cosine similarity via dot product
        norms = np.linalg.norm(self.embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self.embeddings = self.embeddings / norms

    def save(self) -> None:
        if self.embeddings is None:
            raise RuntimeError("Nothing to save")
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(self.chunks, f, ensure_ascii=False, indent=2)
        np.save(self.vec_path, self.embeddings)
        # tiny marker file for humans
        (self.persist_dir / "README.txt").write_text(
            f"{len(self.chunks)} chunks stored for RAG retrieval.\n",
            encoding="utf-8",
        )

    def load(self) -> None:
        if not self.meta_path.exists() or not self.vec_path.exists():
            raise FileNotFoundError(
                f"No vector store found in {self.persist_dir}. Run ingestion first."
            )
        with open(self.meta_path, encoding="utf-8") as f:
            self.chunks = json.load(f)
        self.embeddings = np.load(self.vec_path)

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        tenant_id: Optional[str] = None,
    ) -> List[Dict]:
        """
        Return top_k most similar chunks.

        "Correct chunks" means: the texts whose meaning is closest to the
        question (high cosine similarity), preferably mentioning the facts asked.
        """
        if self.embeddings is None or not self.chunks:
            raise RuntimeError("Store is empty — load or ingest first")

        q = np.array(query_embedding, dtype=np.float32)
        q = q / (np.linalg.norm(q) or 1.0)
        scores = self.embeddings @ q

        indices = list(range(len(self.chunks)))
        if tenant_id is not None:
            indices = [
                i for i in indices if self.chunks[i].get("tenant_id") == tenant_id
            ]
            if not indices:
                return []

        ranked = sorted(indices, key=lambda i: float(scores[i]), reverse=True)[:top_k]
        results = []
        for i in ranked:
            item = dict(self.chunks[i])
            item["score"] = float(scores[i])
            results.append(item)
        return results

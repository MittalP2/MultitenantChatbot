"""Local TF-IDF vector store (numpy only, no cloud APIs)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Union

import numpy as np

from ingestion.embedder import TfidfModel


class SimpleVectorStore:
    def __init__(self, persist_dir: Path):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.meta_path = self.persist_dir / "chunks.json"
        self.vec_path = self.persist_dir / "tfidf_matrix.npy"
        self.model_path = self.persist_dir / "tfidf_model.json"
        self.chunks: List[Dict] = []
        self.embeddings: Optional[np.ndarray] = None
        self.vectorizer: Optional[TfidfModel] = None

    def add(
        self,
        chunks: List[Dict],
        embeddings: np.ndarray,
        vectorizer: TfidfModel,
    ) -> None:
        if embeddings.shape[0] != len(chunks):
            raise ValueError("chunks and embeddings row count mismatch")
        self.chunks = chunks
        self.embeddings = np.asarray(embeddings, dtype=np.float32)
        self.vectorizer = vectorizer

    def save(self) -> None:
        if self.embeddings is None or self.vectorizer is None:
            raise RuntimeError("Nothing to save")
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(self.chunks, f, ensure_ascii=False, indent=2)
        np.save(self.vec_path, self.embeddings)
        with open(self.model_path, "w", encoding="utf-8") as f:
            json.dump(self.vectorizer.to_state(), f)
        (self.persist_dir / "README.txt").write_text(
            (
                f"{len(self.chunks)} chunks stored with local TF-IDF vectors.\n"
                "No OpenAI/Cursor API key required for retrieval.\n"
            ),
            encoding="utf-8",
        )

    def load(self) -> None:
        if not (
            self.meta_path.exists()
            and self.vec_path.exists()
            and self.model_path.exists()
        ):
            raise FileNotFoundError(
                f"No vector store found in {self.persist_dir}. Run ingestion first."
            )
        with open(self.meta_path, encoding="utf-8") as f:
            self.chunks = json.load(f)
        self.embeddings = np.load(self.vec_path)
        with open(self.model_path, encoding="utf-8") as f:
            self.vectorizer = TfidfModel.from_state(json.load(f))

    def search(
        self,
        query_embedding: Union[np.ndarray, List[float]],
        top_k: int = 5,
        tenant_id: Optional[str] = None,
    ) -> List[Dict]:
        if self.embeddings is None or not self.chunks:
            raise RuntimeError("Store is empty — load or ingest first")

        q = np.asarray(query_embedding, dtype=np.float32)
        if q.ndim == 2:
            q = q[0]
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

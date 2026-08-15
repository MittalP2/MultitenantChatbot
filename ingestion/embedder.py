"""
Lightweight local TF-IDF (numpy only — no OpenAI / sklearn / scipy required).
Good enough for Week 1 RAG learning on constrained Python installs.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Tiny English stopword list (keeps dependency-free)
_STOP = {
    "a", "an", "the", "and", "or", "but", "if", "in", "on", "at", "to", "for",
    "of", "as", "by", "with", "from", "is", "are", "was", "were", "be", "been",
    "being", "it", "this", "that", "these", "those", "i", "you", "he", "she",
    "we", "they", "them", "their", "our", "your", "not", "no", "yes", "do",
    "does", "did", "doing", "have", "has", "had", "having", "will", "would",
    "can", "could", "should", "may", "might", "must", "shall", "than", "then",
    "so", "such", "into", "over", "under", "again", "further", "once", "here",
    "there", "when", "where", "why", "how", "all", "each", "few", "more",
    "most", "other", "some", "only", "own", "same", "too", "very", "just",
}


def tokenize(text: str) -> List[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOP and len(t) > 1]


class TfidfModel:
    def __init__(self, max_features: int = 8000):
        self.max_features = max_features
        self.vocab: Dict[str, int] = {}
        self.idf: np.ndarray = np.array([])

    def fit(self, texts: Sequence[str]) -> "TfidfModel":
        df: Counter = Counter()
        tfs: List[Counter] = []
        for text in texts:
            counts = Counter(tokenize(text))
            tfs.append(counts)
            df.update(counts.keys())

        # Keep most common terms by document frequency
        terms = [t for t, _ in df.most_common(self.max_features)]
        self.vocab = {t: i for i, t in enumerate(terms)}
        n_docs = max(len(texts), 1)
        self.idf = np.zeros(len(self.vocab), dtype=np.float32)
        for term, idx in self.vocab.items():
            self.idf[idx] = math.log((1 + n_docs) / (1 + df[term])) + 1.0
        return self

    def transform(self, texts: Sequence[str]) -> np.ndarray:
        if not self.vocab:
            raise RuntimeError("TfidfModel is not fitted")
        mat = np.zeros((len(texts), len(self.vocab)), dtype=np.float32)
        for row, text in enumerate(texts):
            counts = Counter(tokenize(text))
            if not counts:
                continue
            max_tf = max(counts.values())
            for term, tf in counts.items():
                idx = self.vocab.get(term)
                if idx is None:
                    continue
                mat[row, idx] = (tf / max_tf) * self.idf[idx]
            norm = np.linalg.norm(mat[row])
            if norm > 0:
                mat[row] /= norm
        return mat

    def to_state(self) -> Dict:
        return {
            "max_features": self.max_features,
            "vocab": self.vocab,
            "idf": self.idf.tolist(),
        }

    @classmethod
    def from_state(cls, state: Dict) -> "TfidfModel":
        model = cls(max_features=state.get("max_features", 30000))
        model.vocab = {str(k): int(v) for k, v in state["vocab"].items()}
        model.idf = np.array(state["idf"], dtype=np.float32)
        return model


_model: TfidfModel = None  # type: ignore


def fit_vectorizer(texts: List[str]) -> TfidfModel:
    global _model
    _model = TfidfModel().fit(texts)
    return _model


def set_vectorizer(model: TfidfModel) -> None:
    global _model
    _model = model


def get_vectorizer() -> TfidfModel:
    if _model is None:
        raise RuntimeError("TF-IDF model is not loaded. Run ingestion first.")
    return _model


def embed_texts(texts: List[str], batch_size: int = 64) -> np.ndarray:
    _ = batch_size
    return get_vectorizer().transform(texts)

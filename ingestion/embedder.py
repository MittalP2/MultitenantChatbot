"""Create embeddings via OpenAI."""

import os
from typing import List

from openai import OpenAI


def get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key.startswith("sk-your-key"):
        raise RuntimeError(
            "Set OPENAI_API_KEY in a .env file (see .env.example)."
        )
    return OpenAI(api_key=api_key)


def embed_texts(texts: List[str], batch_size: int = 64) -> List[List[float]]:
    """Return one embedding vector per input text."""
    client = get_client()
    model = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
    vectors: List[List[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        resp = client.embeddings.create(model=model, input=batch)
        # API returns data sorted by index
        ordered = sorted(resp.data, key=lambda x: x.index)
        vectors.extend([item.embedding for item in ordered])
    return vectors

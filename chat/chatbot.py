"""Answer questions using retrieved BMW document chunks."""

import os
from typing import Dict, List, Tuple

from ingestion.embedder import get_client
from retrieval.retriever import retrieve


SYSTEM_PROMPT = """You are a BMW financial assistant.
Answer ONLY using the provided context from BMW investor reports.
If the context does not contain the answer, say you don't know.
Be concise. Include specific figures when present in the context.
"""


def build_context(chunks: List[Dict]) -> str:
    parts = []
    for i, c in enumerate(chunks, start=1):
        parts.append(
            f"[{i}] Source: {c['document']} (page {c['page']})\n{c['text']}"
        )
    return "\n\n".join(parts)


def answer_question(
    question: str,
    top_k: int = 5,
    tenant_id: str = "bmw",
) -> Tuple[str, List[Dict]]:
    chunks = retrieve(question, top_k=top_k, tenant_id=tenant_id)
    if not chunks:
        return "I couldn't find relevant passages in the BMW documents.", []

    context = build_context(chunks)
    client = get_client()
    model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    resp = client.chat.completions.create(
        model=model,
        temperature=0.1,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Context:\n{context}\n\n"
                    f"Question: {question}\n\n"
                    "Answer based only on the context. "
                    "Mention document names/pages when you use a figure."
                ),
            },
        ],
    )
    answer = resp.choices[0].message.content or ""
    return answer, chunks

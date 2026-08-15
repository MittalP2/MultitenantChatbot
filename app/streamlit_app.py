"""
Week 1 — Basic BMW RAG chatbot (Streamlit).

Ask a question → retrieve similar chunks from BMW PDFs → LLM answers from those chunks.
"""

import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from chat.chatbot import answer_question


st.set_page_config(page_title="BMW RAG Chat (Week 1)", page_icon="📄", layout="centered")
st.title("BMW Investor Report Assistant")
st.caption("Week 1 learning demo — answers only from ingested BMW PDFs.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander("Sources"):
                for s in msg["sources"]:
                    st.markdown(
                        f"- **{s['document']}** p.{s['page']} "
                        f"(score {s['score']:.3f})"
                    )

question = st.chat_input("Ask about BMW reports… e.g. What was Group revenue in 2024?")
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                answer, chunks = answer_question(question, top_k=5, tenant_id="bmw")
            except Exception as e:
                answer, chunks = f"Error: {e}", []
        st.markdown(answer)
        sources = [
            {
                "document": c["document"],
                "page": c["page"],
                "score": c["score"],
            }
            for c in chunks
        ]
        if sources:
            with st.expander("Sources"):
                for s in sources:
                    st.markdown(
                        f"- **{s['document']}** p.{s['page']} "
                        f"(score {s['score']:.3f})"
                    )

    st.session_state.messages.append(
        {"role": "assistant", "content": answer, "sources": sources}
    )

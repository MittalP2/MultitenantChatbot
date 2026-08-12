"""
Week 1 CLI chatbot for BMW RAG (no Streamlit required).

Usage (from project root):
  python app/cli_chat.py
  python app/cli_chat.py "What was BMW Group revenue in 2024?"
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from chat.chatbot import answer_question


def run_once(question: str) -> None:
    print("\nRetrieving chunks + generating answer...\n")
    answer, chunks = answer_question(question, top_k=5, tenant_id="bmw")
    print("ANSWER")
    print("-" * 40)
    print(answer)
    print("\nRETRIEVED CHUNKS (this is the key Week 1 check)")
    print("-" * 40)
    for i, c in enumerate(chunks, start=1):
        preview = c["text"][:220].replace("\n", " ")
        print(
            f"[{i}] {c['document']} p.{c['page']}  score={c['score']:.3f}\n"
            f"    {preview}{'…' if len(c['text']) > 220 else ''}\n"
        )


def main() -> None:
    if len(sys.argv) > 1:
        run_once(" ".join(sys.argv[1:]))
        return

    print("BMW Investor Report Assistant (Week 1 CLI)")
    print("Type a question, or 'quit' to exit.\n")
    while True:
        try:
            q = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not q:
            continue
        if q.lower() in {"quit", "exit", "q"}:
            break
        try:
            run_once(q)
        except Exception as e:
            print(f"Error: {e}\n")


if __name__ == "__main__":
    main()

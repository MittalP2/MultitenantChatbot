"""
Week 1 CLI chatbot for BMW RAG (no Streamlit required).

Usage (from project root):
  python app/cli_chat.py
  python app/cli_chat.py "What was BMW Group revenue in 2024?"
  python app/cli_chat.py --chunks "What was BMW Group revenue in 2024?"
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from chat.chatbot import answer_question


def safe_print(text: str) -> None:
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode(encoding, errors="replace").decode(encoding, errors="replace"))


def run_once(question: str, show_chunks: bool = False) -> None:
    safe_print("\nThinking...\n")
    answer, chunks = answer_question(question, top_k=5, tenant_id="bmw")
    safe_print("ANSWER")
    safe_print("-" * 40)
    safe_print(answer)

    if chunks:
        safe_print("\nSOURCES")
        safe_print("-" * 40)
        for i, c in enumerate(chunks, start=1):
            safe_print(
                f"[{i}] {c['document']}  p.{c['page']}  (score={c['score']:.3f})"
            )

    if show_chunks and chunks:
        safe_print("\nRETRIEVED CHUNKS")
        safe_print("-" * 40)
        for i, c in enumerate(chunks, start=1):
            preview = c["text"][:220].replace("\n", " ")
            safe_print(
                f"[{i}] {c['document']} p.{c['page']}  score={c['score']:.3f}\n"
                f"    {preview}{'...' if len(c['text']) > 220 else ''}\n"
            )


def main() -> None:
    args = sys.argv[1:]
    show_chunks = False
    if "--chunks" in args:
        show_chunks = True
        args = [a for a in args if a != "--chunks"]

    if args:
        run_once(" ".join(args), show_chunks=show_chunks)
        return

    safe_print("BMW Investor Report Assistant (Week 1 CLI)")
    safe_print("Type a question, or 'quit' to exit.")
    safe_print("Tip: answers cite sources; use --chunks to dump passages.\n")
    while True:
        try:
            q = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            safe_print("")
            break
        if not q:
            continue
        if q.lower() in {"quit", "exit", "q"}:
            break
        try:
            run_once(q, show_chunks=show_chunks)
        except Exception as e:
            safe_print(f"Error: {e}\n")


if __name__ == "__main__":
    main()

"""
CLI chatbot for BMW (Week 1) and SEC 10-K (Week 2) RAG.

Usage (from project root):
  python app/cli_chat.py
  python app/cli_chat.py --tenant sec "What competition risks does Tesla disclose?"
  python app/cli_chat.py --tenant sec --strategy semantic --no-rerank --chunks "What products does Tesla sell besides cars?"
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


def run_once(
    question: str,
    show_chunks: bool = False,
    tenant_id: str = "bmw",
    strategy: str = "fixed",
    use_rerank: bool = True,
) -> None:
    safe_print("\nThinking...\n")
    kwargs = {"top_k": 5, "tenant_id": tenant_id}
    if tenant_id == "sec":
        kwargs["strategy"] = strategy
        kwargs["use_rerank"] = use_rerank
    answer, chunks = answer_question(question, **kwargs)
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
    tenant_id = "bmw"
    strategy = "fixed"
    use_rerank = True
    if "--chunks" in args:
        show_chunks = True
        args = [a for a in args if a != "--chunks"]
    if "--no-rerank" in args:
        use_rerank = False
        args = [a for a in args if a != "--no-rerank"]
    if "--tenant" in args:
        idx = args.index("--tenant")
        if idx + 1 >= len(args):
            raise SystemExit("Usage: --tenant bmw|sec")
        tenant_id = args[idx + 1].strip().lower()
        args = args[:idx] + args[idx + 2 :]
        if tenant_id not in {"bmw", "sec"}:
            raise SystemExit("tenant must be bmw or sec")
    if "--strategy" in args:
        idx = args.index("--strategy")
        if idx + 1 >= len(args):
            raise SystemExit("Usage: --strategy fixed|semantic")
        strategy = args[idx + 1].strip().lower()
        args = args[:idx] + args[idx + 2 :]
        if strategy not in {"fixed", "semantic"}:
            raise SystemExit("strategy must be fixed or semantic")

    run_kwargs = {
        "show_chunks": show_chunks,
        "tenant_id": tenant_id,
        "strategy": strategy,
        "use_rerank": use_rerank,
    }

    if args:
        run_once(" ".join(args), **run_kwargs)
        return

    if tenant_id == "sec":
        rr = "rerank on" if use_rerank else "no rerank"
        safe_print(f"SEC 10-K assistant (Week 2 CLI) — {strategy} / {rr}")
    else:
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
            run_once(q, **run_kwargs)
        except Exception as e:
            safe_print(f"Error: {e}\n")


if __name__ == "__main__":
    main()

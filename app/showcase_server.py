"""
HTML showcase + live chatbot.

Usage (from project root):
  py -3.12 app/showcase_server.py

Then open:
  http://127.0.0.1:8765         Week 2 SEC 10-K comparison
  http://127.0.0.1:8765/week1   Week 1 BMW
"""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from chat.chatbot import _extractive_answer, answer_question
from retrieval.finance_retriever import hits_payload, retrieve_finance

HTML_WEEK1 = ROOT / "docs" / "week1-showcase.html"
HTML_WEEK2 = ROOT / "docs" / "week2-showcase.html"
REPORT_PATH = ROOT / "eval" / "COMPARISON_REPORT.md"
BMW_STORE = ROOT / "storage" / "bmw"
SEC_FIXED = ROOT / "storage" / "sec_fixed"
SEC_SEMANTIC = ROOT / "storage" / "sec_semantic"
HOST = "127.0.0.1"
PORT = 8765


def _store_ready(store_dir: Path) -> bool:
    return (
        (store_dir / "chunks.json").exists()
        and (store_dir / "tfidf_matrix.npy").exists()
        and (store_dir / "tfidf_model.json").exists()
    )


def _sec_ready() -> bool:
    return _store_ready(SEC_FIXED) and _store_ready(SEC_SEMANTIC)


def _pack_hits(question: str, persist_dir: Path, use_rerank: bool) -> dict:
    hits = retrieve_finance(
        question,
        persist_dir=persist_dir,
        top_k=5,
        tenant_id="sec",
        use_rerank=use_rerank,
    )
    return {"hits": hits_payload(hits)}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, payload: dict) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send(code, raw, "application/json; charset=utf-8")

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in {"/", "/index.html", "/week2", "/week2.html"}:
            self._send(200, HTML_WEEK2.read_bytes(), "text/html; charset=utf-8")
            return
        if path in {"/week1", "/week1-showcase.html"}:
            self._send(200, HTML_WEEK1.read_bytes(), "text/html; charset=utf-8")
            return
        if path == "/report":
            body = REPORT_PATH.read_bytes() if REPORT_PATH.exists() else b"Run eval/run_eval.py first."
            self._send(200, body, "text/markdown; charset=utf-8")
            return
        if path == "/api/health":
            ready = _store_ready(BMW_STORE)
            self._json(
                200,
                {
                    "ok": True,
                    "tenant": "bmw",
                    "store": ready,
                    "hint": None
                    if ready
                    else "Run: py -3.12 ingestion/run_ingest.py",
                },
            )
            return
        if path == "/api/health-sec":
            ready = _sec_ready()
            self._json(
                200,
                {
                    "ok": True,
                    "tenant": "sec",
                    "store": ready,
                    "hint": None
                    if ready
                    else "Run: py -3.12 ingestion/run_ingest_sec.py",
                },
            )
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length") or 0)
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._json(400, {"error": "invalid json"})
            return
        question = (data.get("question") or "").strip()
        if not question:
            self._json(400, {"error": "question is required"})
            return

        if path == "/api/ask":
            if not _store_ready(BMW_STORE):
                self._json(
                    503,
                    {
                        "error": "BMW vector store not found. Run: py -3.12 ingestion/run_ingest.py"
                    },
                )
                return
            try:
                answer, chunks = answer_question(question, top_k=5, tenant_id="bmw")
            except Exception as exc:
                self._json(500, {"error": str(exc)})
                return
            sources = [
                {
                    "document": c.get("document"),
                    "page": c.get("page"),
                    "score": round(float(c.get("score") or 0), 3),
                }
                for c in chunks
            ]
            self._json(200, {"answer": answer, "sources": sources})
            return

        if path in {"/api/compare", "/api/ask-sec"}:
            if not _sec_ready():
                self._json(
                    503,
                    {
                        "error": "SEC indexes missing. Run: py -3.12 ingestion/run_ingest_sec.py"
                    },
                )
                return
            try:
                conditions = {
                    "fixed_plain": _pack_hits(question, SEC_FIXED, False),
                    "fixed_rerank": _pack_hits(question, SEC_FIXED, True),
                    "semantic_plain": _pack_hits(question, SEC_SEMANTIC, False),
                    "semantic_rerank": _pack_hits(question, SEC_SEMANTIC, True),
                }
                payload = {"conditions": conditions}
                if data.get("answer", True) or path == "/api/ask-sec":
                    winner = retrieve_finance(
                        question,
                        persist_dir=SEC_FIXED,
                        top_k=5,
                        tenant_id="sec",
                        use_rerank=True,
                    )
                    payload["answer"] = _extractive_answer(question, winner)
                    payload["sources"] = [
                        {
                            "document": c.get("document"),
                            "page": c.get("page"),
                            "score": round(float(c.get("score") or 0), 3),
                        }
                        for c in winner
                    ]
            except Exception as exc:
                self._json(500, {"error": str(exc)})
                return
            self._json(200, payload)
            return

        self._json(404, {"error": "not found"})


def main() -> None:
    if not HTML_WEEK1.exists() or not HTML_WEEK2.exists():
        raise SystemExit("Missing docs/week1-showcase.html or docs/week2-showcase.html")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Week 2 10-K: http://{HOST}:{PORT}", flush=True)
    print(f"Week 1 BMW:  http://{HOST}:{PORT}/week1", flush=True)
    if not _store_ready(BMW_STORE):
        print("  BMW index missing → py -3.12 ingestion/run_ingest.py", flush=True)
    if not _sec_ready():
        print("  SEC indexes missing → py -3.12 ingestion/run_ingest_sec.py", flush=True)
    print("Press Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()

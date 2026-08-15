"""
Week 1 HTML showcase + live chatbot.

Usage (from project root):
  py -3.12 app/showcase_server.py

Then open http://127.0.0.1:8765
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

from chat.chatbot import answer_question

HTML_PATH = ROOT / "docs" / "week1-showcase.html"
STORE_DIR = ROOT / "storage" / "bmw"
HOST = "127.0.0.1"
PORT = 8765


def _store_ready() -> bool:
    return (
        (STORE_DIR / "chunks.json").exists()
        and (STORE_DIR / "tfidf_matrix.npy").exists()
        and (STORE_DIR / "tfidf_model.json").exists()
    )


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
        if path in {"/", "/index.html", "/week1-showcase.html"}:
            html = HTML_PATH.read_bytes()
            self._send(200, html, "text/html; charset=utf-8")
            return
        if path == "/api/health":
            ready = _store_ready()
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
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path != "/api/ask":
            self._json(404, {"error": "not found"})
            return
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
        if not _store_ready():
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


def main() -> None:
    if not HTML_PATH.exists():
        raise SystemExit(f"Missing {HTML_PATH}")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    if not _store_ready():
        print(
            f"Warning: no index in {STORE_DIR}. Run: py -3.12 ingestion/run_ingest.py",
            flush=True,
        )
    print(f"Showcase + chatbot: http://{HOST}:{PORT}", flush=True)
    print("Demo questions: employees 2025 · revenues 2025 · EBIT margin 2025", flush=True)
    print("Press Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()

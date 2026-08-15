# AutoChat

Week 1 of a **multi-tenant RAG chatbot** over automotive investor reports.

This release answers questions from **BMW Group PDFs only**. Retrieval runs on your laptop (TF-IDF). Cursor writes the final answer from the retrieved passages.

**GitHub:** [github.com/MittalP2/MultitenantChatbot](https://github.com/MittalP2/MultitenantChatbot)

```text
PDF  →  text chunks  →  TF-IDF vectors  →  local store
                                              ↑
User question → vectorize → find similar chunks → answer from those chunks
```

---

## Links for submission

| What | Link |
| --- | --- |
| GitHub repository | https://github.com/MittalP2/MultitenantChatbot |
| This README | https://github.com/MittalP2/MultitenantChatbot/blob/main/README.md |
| Product spec (PRD) | https://github.com/MittalP2/MultitenantChatbot/blob/main/PRD.md |
| Live showcase (local) | http://127.0.0.1:8765 after `py -3.12 app/showcase_server.py` |
| Demo video | Add your recording URL here after you upload it |

PDFs and the vector store stay **local** (not in GitHub) because IR reports are copyrighted and large.

---

## What v1 includes

- Ingest BMW investor PDFs into overlapping chunks (document + page metadata)
- Local TF-IDF retrieval with a BMW `tenant_id` filter
- Cited answers via Cursor cloud (`CURSOR_API_KEY`), with extractive fallback if no key
- CLI chatbot and a live HTML showcase for the group demo

**Not in v1** (later weeks): other OEM tenants, login, cross-tenant isolation tests.

---

## Answer routing

1. **Cursor cloud** (`CURSOR_API_KEY`) — preferred; works on Windows
2. **OpenAI** (`OPENAI_API_KEY`) — optional
3. **Ollama** — optional local model
4. **Extractive fallback** — pulls a figure/passage from retrieved text

Retrieval always stays in `storage/bmw/`. Cursor only sees the passages we send.

> Cursor Pro powers chat *inside Cursor*. This app talks to Cursor through the **Cursor SDK / cloud API** (`CURSOR_API_KEY`), not the IDE chat window. Leave `CURSOR_RUNTIME=cloud` on Windows.

---

## Setup

Python **3.10+** (3.12 recommended):

```bash
py -3.12 -m pip install -r requirements.txt
```

Put BMW PDFs in `data/bmw/` (see [data/MANUAL_DOWNLOADS.md](data/MANUAL_DOWNLOADS.md)). Then:

```env
CURSOR_API_KEY=cursor_...
CURSOR_MODEL=composer-2.5
```

Copy [`.env.example`](.env.example) to `.env` and fill in the key from [cursor.com/dashboard/integrations](https://cursor.com/dashboard/integrations).

Ingest once (or again after adding PDFs):

```bash
py -3.12 ingestion/run_ingest.py
```

---

## Demo (record this)

About 2–3 minutes. Have `.env` and `storage/bmw/` already built so you are not waiting on ingest.

**1. Start the showcase**

```bash
py -3.12 app/showcase_server.py
```

Open [http://127.0.0.1:8765](http://127.0.0.1:8765).

**2. Say this once**

> AutoChat finds the right BMW report pages locally, then Cursor writes a short answer with citations. Next weeks add more carmakers and real tenant isolation.

**3. Ask these two questions** (30–90 seconds each while Cursor writes)

1. *How many employees in BMW Group in 2025?*
2. *What were BMW Group revenues in 2025?*

Point at the **Sources** line under the answer (document + page). Optional third chip: *Automotive EBIT margin in 2025*.

**4. Optional CLI clip** (if you want a terminal shot)

```bash
py -3.12 app/cli_chat.py "What was BMW Group revenue in 2025?"
```

Do **not** double-click the HTML file for the live demo — the server must be running.

---

## Other ways to run

```bash
py -3.12 app/cli_chat.py
py -3.12 app/cli_chat.py --chunks "How many employees in BMW Group in 2025?"
```

Streamlit is optional (`pip install streamlit` then `py -3.12 -m streamlit run app/streamlit_app.py`).

---

## Project layout

```text
AutoChat/
├── app/                 # CLI, Streamlit, showcase server
├── chat/                # Answer routing (Cursor → fallback)
├── ingestion/           # PDF load, chunk, TF-IDF
├── retrieval/           # Vector store + retriever
├── docs/week1-showcase.html
├── data/{bmw,...}/      # PDFs (local only)
├── storage/bmw/         # Index (local only)
└── PRD.md
```

---

## Success check (Week 1)

- [x] Ingestion finishes
- [x] CLI / showcase runs
- [x] Retrieved chunks look relevant
- [x] Answers include sources (document + page)

---

## License

MIT. Investor-report PDFs are **not** redistributed in this repo; download them from each OEM’s IR site.

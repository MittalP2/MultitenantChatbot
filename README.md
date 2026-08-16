# AutoChat

A RAG chatbot over automotive investor reports. The long-term design is **multi-tenant**: each OEM’s documents stay isolated, and isolation is enforced at **retrieval**, not by telling the model “only use Toyota docs.”

This app currently answers from **BMW Group PDFs**. Search runs locally. An LLM (Cursor by default) writes the answer from the retrieved passages only.

```text
PDF → chunks (document + page + tenant_id) → local TF-IDF index
                                                    ↑
Question → same vectorization → closest chunks → cited answer
```

Local retrieval is the librarian. The model is the writer. It never searches the PDFs itself.

## What it does

- Loads BMW PDFs from `data/bmw/`, splits pages into overlapping chunks
- Stores TF-IDF vectors in `storage/bmw/` (not committed; PDFs stay local too)
- Filters search by `tenant_id` (`bmw` today)
- Returns an answer plus sources (filename + page)
- Answer order: Cursor cloud → optional OpenAI → optional Ollama → extractive fallback

Set `CURSOR_API_KEY` in `.env` (see `.env.example`). On Windows keep `CURSOR_RUNTIME=cloud`.

## Setup

Python 3.10+ (3.12 recommended):

```bash
py -3.12 -m pip install -r requirements.txt
```

Put BMW reports in `data/bmw/` ([data/MANUAL_DOWNLOADS.md](data/MANUAL_DOWNLOADS.md)). Copy `.env.example` to `.env` and add your key from [cursor.com/dashboard/integrations](https://cursor.com/dashboard/integrations).

```bash
py -3.12 ingestion/run_ingest.py
py -3.12 app/cli_chat.py
py -3.12 app/cli_chat.py "What were BMW Group revenues in 2025?"
py -3.12 app/showcase_server.py
```

Showcase UI: [http://127.0.0.1:8765](http://127.0.0.1:8765) (server required). Optional: `py -3.12 -m streamlit run app/streamlit_app.py`.

## Layout

```text
app/          CLI, Streamlit, HTML showcase server
chat/         Answer routing
ingestion/    PDF load, chunk, TF-IDF
retrieval/    Vector store + retriever
data/         OEM PDFs (local)
storage/      Index (local)
PRD.md        Product concept
```

## License

MIT. Investor-report PDFs are not in this repo.

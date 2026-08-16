# AutoChat

RAG chatbot over public automotive investor reports.

## Concept

Enterprise chat over private filings is easy to fake with a prompt (“you are a Toyota assistant”). That is not isolation. The model does not control the database. **Unauthorized chunks must never be retrieved.**

Intended shape:

```text
User → auth → tenant_id → filtered vector search → authorized chunks only → LLM → answer + citations
```

Not:

```text
User → LLM (“please only use Toyota docs”) → vector DB
```

Planned tenants: Toyota, BMW, Mercedes-Benz, Ford, Honda. Each chunk carries `tenant_id`, document name, and page.

## What exists now

Single-tenant RAG for **BMW**.

| Piece | Implementation |
| --- | --- |
| Corpus | BMW Group annual reports + quarterlies in `data/bmw/` |
| Ingest | pypdf page text → overlapping chunks (~800 / 150) |
| Index | Local TF-IDF (numpy), saved under `storage/bmw/` |
| Retrieval | Query expansion + TF-IDF + lexical re-rank; `tenant_id=bmw` |
| Generation | Cursor cloud API; optional OpenAI / Ollama; extractive fallback |
| UI | CLI, Streamlit, HTML showcase (`app/showcase_server.py`) |
| Citations | Document filename + page on each answer |

Chunks look like:

```json
{
  "text": "...",
  "tenant_id": "bmw",
  "document": "BMW-Group-Report-2025-en.pdf",
  "page": 42,
  "chunk_id": "BMW-Group-Report-2025-en.pdf::p42::0"
}
```

Other OEM folders may already have PDFs on disk; they are not ingested into the live bot yet. There is no login. Isolation is prepared in metadata and the search filter, not proven across tenants.

## Later

- Ingest the other OEMs with `tenant_id` on every chunk
- Login → session → authenticated `tenant_id` (never from the user message)
- Retrieval always filtered by that tenant
- Tests: cross-tenant questions and prompt injection must not pull foreign chunks

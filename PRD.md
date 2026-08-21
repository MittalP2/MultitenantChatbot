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

### Week 2 — financial 10-K RAG (submission track)

| Piece | Implementation |
| --- | --- |
| Corpus | Tesla, Harley-Davidson, Polaris 10-K extracts (`data/sec/`) — Item 1, 1A, 7 |
| Chunking | Fixed-size (800/150) vs semantic (heading + sentence TF-IDF groups) |
| Rerank | Top-20 TF-IDF → phrase/year/ticker overlap → top 5 |
| Eval | 12 questions, Hit@5 / MRR / nDCG@5, `eval/COMPARISON_REPORT.md` |
| Demo | http://127.0.0.1:8765 and `cli_chat.py --tenant sec` |

### Week 1 — BMW tenant chat

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

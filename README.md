# MultitenantChatbot

Learning project: multi-tenant RAG chatbot over automotive investor reports, with authentication and tenant isolation.

## Week 1 focus (BMW only)

A **basic chatbot** that answers questions using **only BMW investor PDFs**.

```text
PDF  →  text chunks  →  embeddings  →  vector store
                                         ↑
User question → embed question → find similar chunks → LLM answers from those chunks
```

No login / multi-tenant yet. That's later weeks.

## What “retrieve correct chunks” means

PDFs are too long to paste into the model every time. So we:

1. Split each report into small **chunks** of text (with page + filename metadata).
2. Turn each chunk into an **embedding** (a list of numbers that represent meaning).
3. When you ask a question, we embed the question the same way.
4. **Retrieval** = find the chunks whose vectors are closest to the question vector (cosine similarity).

**“Correct chunks”** means: for *“What was BMW Group revenue in 2024?”*, the top results should be passages that actually discuss 2024 revenue — not a random page about motorcycles.

You can verify this in the CLI/UI output under **Retrieved chunks** — check document + page + score.

If retrieval is wrong, the answer will be wrong even if the LLM is smart. That's the main Week 1 learning.

## Setup

1. Prefer **64-bit Python 3.10+** (32-bit Python 3.8 works for CLI RAG; Streamlit needs 64-bit).
2. From the project root:

```bash
python -m pip install -r requirements.txt
copy .env.example .env
```

3. Put your OpenAI API key in `.env`:

```text
OPENAI_API_KEY=sk-...
```

4. Place BMW PDFs in `data/bmw/` (kept out of git because they are large).

## Step A — Ingest BMW PDFs into the vector store

```bash
python ingestion/run_ingest.py
```

This reads `data/bmw/*.pdf`, chunks them, embeds them, and saves to `storage/bmw/`.

## Step B — Run the chatbot (CLI)

```bash
python app/cli_chat.py
```

Or one-shot:

```bash
python app/cli_chat.py "What was BMW Group revenue in 2024?"
```

Look at **RETRIEVED CHUNKS** — that is how you judge whether retrieval found the right passages.

### Optional Streamlit UI (64-bit Python only)

```bash
python -m pip install "streamlit>=1.28.0,<1.40.0"
streamlit run app/streamlit_app.py
```

Try questions like:

- What was BMW Group revenue in 2024?
- How many cars did BMW deliver?
- What does the report say about electric vehicles?

## Project layout (Week 1)

```text
ingestion/     PDF load, chunk, embed, run_ingest.py
retrieval/     vector store + retriever
chat/          LLM answer using retrieved context
app/           CLI + Streamlit UI
data/bmw/      source PDFs (local only)
storage/bmw/   saved chunks + embeddings (local only)
PRD.md         full product requirements
```

## Success check for Week 1

- [ ] Ingestion finishes without errors
- [ ] Chat runs in CLI
- [ ] A factual question returns an answer grounded in BMW text
- [ ] Retrieved chunks look relevant (right topic / year / document)

# Financial Document Intelligence (RAG) — Lyzr

Week 2 project: a RAG pipeline over three SEC **10-K extracts** (Tesla, Harley-Davidson, Polaris). I built it in **Lyzr Studio**: two Knowledge Bases with different chunk sizes, **two agents** (one per KB), and the same questions on both so retrieval can be compared.

Corpus is Item 1 (Business), Item 1A (Risk Factors), and Item 7 (MD&A) only — not the full iXBRL HTML.

## How I built it

### 1. Two agents

Same Role / Goal / Instructions on both. The only difference is which Knowledge Base is attached.

- **Role:** Financial document analyst; answer only from the 10-K extracts (Tesla, Harley-Davidson, Polaris).
- **Goal:** Short cited answers. If the filings do not contain it, say you do not know.
- **Instructions:** Use only the knowledge base. Cite the source file. Do not mix companies. No investment advice.

| Agent | Linked Knowledge Base | Chunking |
| --- | --- | --- |
| Fixed agent | `10k-fixed` | 800 / 150 |
| Semantic agent | `10k-semantic` | 1600 / 200 |

Each agent uses **Basic** retrieval with **top-k = 5** (not Agentic), so the chunking comparison stays measurable.

I did **not** put both KBs on one agent. That would mix 800- and 1600-character windows.

### 2. Vector store (required)

Training failed with `500: Training Error: 'credentials'` until Qdrant/Lyzr **vector-store credentials** were saved under Connections.

Use the **Lyzr-hosted Qdrant** connection (the one that actually has saved credentials). Creating a KB with an empty Qdrant slot will 500 on every upload, including paste.

Embeddings: **`text-embedding-3-small`** (OpenAI key connected in **Connections → Models**).

### 3. Two Knowledge Bases (same files, different chunks)

| Knowledge Base | Parser | Chunk size | Overlap | Retrieval |
| --- | --- | --- | --- | --- |
| `10k-fixed` | PyPDF | **800** | **150** | Basic, top-k **5** |
| `10k-semantic` | PyPDF | **1600** | **200** | Basic, top-k **5** |

The **same three PDFs** are in both KBs. Same vector-store credential. Same embedding model.

Lyzr does not run a custom “split on sentence similarity” chunker. For Studio, **larger chunks** are the semantic comparison.

### 4. Files I uploaded

Plain `.txt` extracts did not upload reliably. I converted them to PDFs and uploaded from:

`data/sec/lyzr_pdfs/`

(the three company PDFs: Tesla, Harley-Davidson, Polaris — one file at a time; well under Lyzr’s 15 MB / 5-file batch limits.)

Source extracts: `data/sec/*_10K_*.txt`

To regenerate PDFs:

```bash
py -3.12 -m pip install -r requirements.txt
py -3.12 scripts/txt_to_lyzr_pdf.py
```

## Test questions

Use the 12 questions in [eval/queries.json](eval/queries.json). A hit is a retrieved passage from the **right company** that contains an expected term (e.g. Tesla + energy/storage, Harley + LiveWire/dealer, Polaris + ORV/Indian).

Run the **same** question on the **fixed agent** and the **semantic agent**.

Examples:

- What products and services does Tesla sell besides electric cars?
- What competition risks does Tesla disclose in its 10-K?
- What is Harley-Davidson's core motorcycle business and how is it organized?
- What vehicle categories does Polaris sell, such as off-road, motorcycles, or boats?

## What I would tell a grader

1. Open the **fixed** agent, ask a Tesla / Harley / Polaris question; show the citation.
2. Ask the **same** question on the **semantic** agent; compare which window is more usable.
3. Explain: two indexes, two agents, Basic retrieval, top-k 5; chunk size/overlap is the only intentional difference.

## License

MIT. Full EDGAR HTML is not in this repo.

# Financial Document Intelligence (RAG) — Lyzr

Week 2: a RAG pipeline over three SEC 10-K extracts (Tesla, Harley-Davidson, Polaris), built in **Lyzr Studio**. Two Knowledge Bases used different chunk sizes. Two agents used the same Role, Goal, and Instructions. The same six questions were asked on both agents so chunking could be compared.

Corpus is Item 1 (Business), Item 1A (Risk Factors), and Item 7 (MD&A) only — not the full iXBRL HTML.

**Result:** both agents retrieved the right filings. Larger chunks (1600 / 200) produced slightly fuller answers. Smaller chunks (800 / 150) already had the facts. BMW 2025 revenue (not in the corpus) was refused by both. Rerank was not run.

Reports: [eval/Lyzr_Financial_RAG_Comparison_Report.docx](eval/Lyzr_Financial_RAG_Comparison_Report.docx) (Drive / Word) and [eval/LYZR_COMPARISON.md](eval/LYZR_COMPARISON.md) (notes).

## What was built

### Two agents, two Knowledge Bases

Role, Goal, and Instructions were identical. The only intentional difference was which KB was attached (chunk size / overlap).

| Agent | Knowledge Base | Chunk / overlap | Retrieval |
| --- | --- | --- | --- |
| Fixed | `10k-fixed` | 800 / 150 | Basic, top-k 5 |
| Semantic | `10k-semantic` | 1600 / 200 | Basic, top-k 5 |

Both used PyPDF, `text-embedding-3-small`, and the same Lyzr-hosted Qdrant credential. Both KBs hold the same three PDFs. Retrieval was Basic, not Agentic. Both KBs were not attached to one agent.

In Lyzr, “semantic” means larger topical windows (1600 / 200), not a custom sentence-similarity splitter.

Training failed with `500: Training Error: 'credentials'` until vector-store credentials were saved. Empty Qdrant slots 500 on every upload, including paste. File size was not the cause.

### Files uploaded

Plain `.txt` extracts did not upload. They were converted to PDF and uploaded from `data/sec/lyzr_pdfs/` (Tesla, Harley-Davidson, Polaris — one file at a time). Source extracts: `data/sec/*_10K_*.txt`.

```bash
py -3.12 -m pip install -r requirements.txt
py -3.12 scripts/txt_to_lyzr_pdf.py
```

## Questions that were actually asked

These six, identical wording on the fixed agent then the semantic agent.

| # | Question | Fixed | Semantic | More usable |
| --- | --- | --- | --- | --- |
| 1 | What else does Tesla sell besides cars? | Yes | Yes | Tie |
| 2 | What risks does Harley-Davidson disclose about dealers? | Yes | Yes | Semantic |
| 3 | What happened to Indian Motorcycle at Polaris? | Yes | Yes | Tie |
| 4 | What is LiveWire? | Yes | Yes | Semantic |
| 5 | What is Autopilot? | Partial | Partial | Semantic |
| 6 | What was BMW Group revenue in 2025? (not in corpus) | Correct refuse | Correct refuse | Tie |

Scoring: Yes = an analyst could use the answer; Partial = right company but thin or missing a named definition; Correct refuse = “I don’t know” on a question not in the filings.

In-corpus: both 4 Yes + 1 Partial. Out-of-corpus: 2/2 correct refuses. Autopilot was Partial because the extracts have no standalone “Autopilot” definition; semantic also pulled neighboring FSD language.

Rerank was not turned on. The comparison is chunking only (800/150 vs 1600/200).

## License

MIT. Full EDGAR HTML is not in this repo.

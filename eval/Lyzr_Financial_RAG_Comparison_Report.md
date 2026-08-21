# Financial Document Intelligence Pipeline (RAG)
## Chunking strategy comparison — Lyzr Studio

Week 2 course project

---

### 1. Objective

Build a retrieval-augmented generation (RAG) pipeline over financial filings and compare two chunking strategies on the same questions. This report records the Lyzr Studio experiment: fixed-size chunks versus larger “semantic” windows, with identical agents, files, and retrieval settings.

---

### 2. Corpus

Three SEC Form 10-K extracts (Item 1 Business, Item 1A Risk Factors, Item 7 MD&A only):

- Tesla, Inc. (TSLA_10K_2025.pdf)
- Harley-Davidson, Inc. (HOG_10K_2025.pdf)
- Polaris Inc. (PII_10K_2025.pdf)

Full EDGAR HTML was not used. Files were uploaded from the project folder data/sec/lyzr_pdfs/. Parser: PyPDF.

---

### 3. Method

Two Knowledge Bases and two agents. Role, Goal, and Instructions were exactly the same on both agents. The only intentional difference was chunk size and overlap.

| Setting | Fixed agent | Semantic agent |
| --- | --- | --- |
| Knowledge Base | 10k-fixed | 10k-semantic |
| Chunk size / overlap | 800 / 150 | 1600 / 200 |
| Retrieval type | Basic | Basic |
| top-k | 5 | 5 |
| Embedding | text-embedding-3-small | text-embedding-3-small |
| Vector store | Lyzr-hosted Qdrant (saved credentials) | Same credential |
| Documents | Same three PDFs | Same three PDFs |
| Role, Goal, Instructions | Identical | Identical |

Both Knowledge Bases were not attached to a single agent. That would mix 800- and 1600-character windows and hide which chunker produced the hit.

Agent Role: financial document analyst; answer only from the 10-K extracts. Goal: short cited answers; say you do not know if the filings do not contain the answer. Instructions: use only the knowledge base; cite the source file; do not mix companies; no investment advice.

Reranking was not turned on. Lyzr Basic retrieval with top-k 5 is a single similarity search. This report therefore compares chunking only, not a second-stage rerank.

In Lyzr, “semantic” means larger topical windows (1600 / 200), not a custom sentence-similarity splitter.

---

### 4. Evaluation

Six questions were asked with the same wording on the fixed agent, then on the semantic agent.

Scoring (business relevance):

- Yes: an analyst could use the answer; right company; key facts present.
- Partial: right company, but thin or missing a named definition.
- No: wrong company, or “I don’t know” when the 10-K has the answer.
- Correct refuse: “I don’t know” on a question that is not in the corpus (desired behavior).

---

### 5. Results

| # | Question | Fixed (800/150) | Semantic (1600/200) | More usable |
| --- | --- | --- | --- | --- |
| 1 | What else does Tesla sell besides cars? | Yes | Yes | Tie |
| 2 | What risks does Harley-Davidson disclose about dealers? | Yes | Yes | Semantic |
| 3 | What happened to Indian Motorcycle at Polaris? | Yes | Yes | Tie |
| 4 | What is LiveWire? | Yes | Yes | Semantic |
| 5 | What is Autopilot? | Partial | Partial | Semantic |
| 6 | What was BMW Group revenue in 2025? | Correct refuse | Correct refuse | Tie |

In-corpus: both agents 4 Yes and 1 Partial. Out-of-corpus (BMW): both correctly refused.

Question notes:

1. Tesla products. Both named energy (Powerwall, Megapack, solar, Solar Roof), services, financing, in-app upgrades, and Supercharger access. Same Item 1 region.

2. Harley dealers. Both described independent-dealer, inventory-funding, and retail-strategy risk (Item 1A). Semantic returned a clearer bullet list; fixed returned a dense paragraph of the same points.

3. Indian Motorcycle. Both stated the 10 October 2025 agreement to sell a majority interest, close in Q1 2026, On Road reporting, held-for-sale at 31 December 2025, and impairment charges (Item 7).

4. LiveWire. Both identified Harley’s electric brand and product types. Semantic also kept independent retail partners and a company-owned dealer, not only online D2C.

5. Autopilot. Neither extract defined “Autopilot” by name. Both described driver-assistance, driver responsibility, and over-the-air updates. Semantic also mentioned FSD (Supervised). Neither invented a fake specification.

6. BMW revenue. Not in the knowledge base. Fixed: “I don’t know based on the uploaded 10-K extracts.” Semantic: the same, and noted the KB holds Tesla, Harley-Davidson, and Polaris only. Neither quoted Tesla or Polaris revenue as if it were BMW.

---

### 6. Analysis

Chunk size did not change whether the right filing was found. Both agents cited the correct 10-K and item for every in-corpus question.

Larger chunks improved how complete and readable the answer was on some questions (dealer risks, LiveWire distribution, Autopilot plus FSD). Smaller chunks were already enough for distinctive facts (Tesla product list, Indian Motorcycle sale).

A short product question can look almost the same on both agents because embeddings land on the same paragraph. That is expected, not a failed test.

This configuration does not produce “semantic says I don’t know while fixed hallucinates.” With the same PDFs and Basic retrieval, both refused the BMW question. That is RAG behaving correctly.

Rerank is a second ranking of a larger candidate list. It is not the same as changing top-k. It was not part of this Lyzr run.

---

### 7. Conclusion

On six identical questions, both Lyzr agents retrieved the right filings. 1600-character chunks produced slightly fuller, more structured answers on LiveWire, Autopilot, and Harley dealer risks. 800-character chunks were sufficient for Tesla products and the Indian Motorcycle sale. Out-of-corpus BMW revenue was refused by both.

For this lexical 10-K Q&A in Lyzr, ship either chunk size for fact lookup; prefer the larger window when the user needs a whole risk or a fuller product description.

---

### 8. Reproduce

1. Connect Lyzr vector-store credentials (empty Qdrant credentials cause training error 500).
2. Create two Knowledge Bases with the settings in section 3; upload the same three PDFs to each.
3. Create two agents with identical Role, Goal, and Instructions; attach one KB each.
4. Ask the six questions on both agents and score as in section 4.

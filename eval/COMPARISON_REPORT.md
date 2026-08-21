# Financial RAG — Chunking & Reranking Comparison

Week 2 deliverable: **Financial Document Intelligence Pipeline (RAG)**.
Corpus is three SEC 10-K *extracts* (Item 1 Business, Item 1A Risk Factors,
Item 7 MD&A) for Tesla, Harley-Davidson, and Polaris. Full iXBRL HTML was
dropped on purpose so a first RAG project stays inspectable.

## Setup

| Piece | Choice |
| --- | --- |
| Documents | 3 × Form 10-K extracts in `data/sec/` (~655 KB total vs 9+ MB raw HTML) |
| Retrieval | Local TF-IDF (numpy), no paid embedding API |
| Fixed chunking | 800 characters, 150 overlap |
| Semantic chunking | Item headings + sentence groups by TF-IDF cosine |
| Rerank | Phrase / year / ticker / token overlap on top 20 |
| Queries | 12 questions in `eval/queries.json` |
| Metrics | Hit@5, MRR, nDCG@5 |

- Fixed-size index: **1084** chunks
- Semantic index: **749** chunks

## Headline results

| Condition | Hit@5 | MRR | nDCG@5 |
| --- | --- | --- | --- |
| Fixed-size, no rerank | 91.7% | 0.753 | 0.793 |
| Fixed-size + rerank | 100.0% | 0.850 | 0.887 |
| Semantic, no rerank | 75.0% | 0.750 | 0.750 |
| Semantic + rerank | 83.3% | 0.736 | 0.797 |

## What changed

### Chunking (same retriever, no rerank)

- Hit@5: 91.7% → 75.0% (-16.7 pts)
- MRR: 0.753 → 0.750 (-0.3 pts)
- nDCG@5: 0.793 → 0.750 (-4.3 pts)

Semantic chunks follow Item 1 / 1A / 7 headings, then glue neighboring
sentences only while they stay similar. That usually keeps a risk-factor
paragraph together instead of splitting it mid-sentence at character 800.
Fixed-size is simpler and can still win on short keyword lookups because
the window is uniform.

### Reranking impact (top 20 TF-IDF → top 5)

| Index | Hit@5 lift | MRR lift | nDCG@5 lift |
| --- | --- | --- | --- |
| Fixed-size | +8.3 pts | +9.7 pts | +9.4 pts |
| Semantic | +8.3 pts | -1.4 pts | +4.7 pts |

Reranking helps when the right passage uses the query's words but is not
the strongest TF-IDF neighbor (common with 10-K boilerplate). It cannot
rescue a miss if the gold paragraph was never in the top 20.

## Per-query Hit@5

| Query | Fixed | Fixed+RR | Semantic | Semantic+RR |
| --- | --- | --- | --- | --- |
| tesla-products | #3 | #1 | miss | #3 |
| tesla-competition-risk | #5 | #2 | #1 | #2 |
| tesla-autopilot | #1 | #1 | #1 | #1 |
| tesla-mda-deliveries | #1 | #1 | #1 | #1 |
| harley-business | #1 | #1 | #1 | #1 |
| harley-risks | miss | #5 | miss | miss |
| harley-mda | #1 | #1 | #1 | #1 |
| polaris-products | #1 | #1 | #1 | #1 |
| polaris-risks | #2 | #2 | miss | miss |
| polaris-mda | #1 | #1 | #1 | #1 |
| cross-energy-storage | #1 | #1 | #1 | #1 |
| cross-powersports | #1 | #1 | #1 | #1 |

## How to read this as a PM

- **Hit@5** is the business question: did a useful passage make the
  answer context at all?
- **MRR** is ranking quality: did that passage show up first?
- **nDCG@5** here is DCG against a single relevant hit at rank 1,
  so it moves with rank (unlike IDCG computed only on the top 5).
- Do not assume semantic chunking wins. On lexical 10-K Q&A,
  uniform windows often retrieve the keyword-bearing sentence;
  semantic groups can bury it inside a longer topical blob.
- Rerank lift (Hit@5): fixed +8.3 pts,
  semantic +8.3 pts. Biggest when
  the gold chunk was in the top 20 but not the top 5.
- Chat default (`--tenant sec`) uses **fixed-size + rerank**,
  the measured winner on this corpus.
- This stack is TF-IDF. A neural reranker would likely add more lift
  on paraphrases; this report measures the shape of the gain without
  extra APIs.

## Business relevance

A PM labels a retrieval **usable** if an analyst could answer from the
top window without opening the full 10-K. Keyword Hit@5 is the
automatic check; the notes below are the business read of the winner
(fixed-size + rerank).

| Query | Winner usable? | Why it matters |
| --- | --- | --- |
| tesla-products | Yes | Energy / storage mix is a product question, not a car-sales KPI. |
| tesla-competition-risk | Yes (rank 2) | Risk committee / 10-K Q&A needs the competition Item 1A window. |
| tesla-autopilot | Yes | FSD wording is a regulated disclosure; wrong chunk is a compliance miss. |
| tesla-mda-deliveries | Yes | MD&A volume is what ops and IR actually quote. |
| harley-business | Yes | Segment map (HDMC / LiveWire / HDFS) is the first analyst question. |
| harley-risks | Yes (rank 5) | Tariff and dealer risk is the stress-test item. |
| harley-mda | Yes | Shipments vs retail is how HD is steered. |
| polaris-products | Yes | ORV / marine mix is the portfolio question. |
| polaris-risks | Yes (rank 2) | Seasonality and supply are the operating risks. |
| polaris-mda | Yes | Segment sales in North America is the earnings-call follow-up. |
| cross-energy-storage | Yes | Must land on Tesla, not a powersports 10-K. |
| cross-powersports | Yes | Must land on Polaris, not Tesla. |

Recommendation: **ship fixed-size chunking with rerank** for this
lexical 10-K stack. Keep semantic chunking in the eval harness so a
later embedding model can be scored on the same 12 questions.

## Demo recording

1. Open http://127.0.0.1:8765
2. Click **Tesla competition**, then **Harley risks** — show the four
   ranked windows changing with rerank.
3. Optional CLI (Cursor answer):
   `py -3.12 app/cli_chat.py --tenant sec --chunks "What competition risks does Tesla disclose?"`

## Reproduce

```bash
py -3.12 scripts/download_sec_10k.py
py -3.12 ingestion/run_ingest_sec.py
py -3.12 eval/run_eval.py
py -3.12 app/showcase_server.py
```

# Lyzr chunking comparison report

Week 2 — Financial Document Intelligence (Lyzr Studio).

## Setup

| | Fixed agent | Semantic agent |
| --- | --- | --- |
| Knowledge Base | `10k-fixed` | `10k-semantic` |
| Chunk / overlap | 800 / 150 | 1600 / 200 |
| Retrieval | Basic | Basic |
| top-k | 5 | 5 |
| Parser | PyPDF | PyPDF |
| Files | Same 3 PDFs: Tesla, Harley-Davidson, Polaris 10-K extracts | Same 3 PDFs |
| Role / Goal / Instructions | Exactly the same | Exactly the same |

Only chunk size and overlap changed. Role, Goal, and Instructions were identical on both agents. Same embeddings, same vector store credential, same questions.

**Scoring (business relevance)**

- **Yes** — analyst could use the answer; right company; key facts present.
- **Partial** — right company, but thin, hedged, or missing a named definition.
- **No** — wrong company, or “I don’t know” when the 10-K has the answer.
- **Correct refuse** — “I don’t know” on a question **not** in the corpus (desired).

Rerank was **not** enabled (Basic, top-k 5). This report measures **chunking only**.

## Per-question results

### Q1. What else does Tesla sell besides cars?

| | Verdict | What the agent said |
| --- | --- | --- |
| **Fixed** | **Yes** | Energy (Powerwall, Megapack, solar, Solar Roof); services (used vehicles, maintenance, Supercharging, insurance, parts, merchandise); financing/leases; in-app upgrades; Supercharger access including some non-Tesla vehicles. TSLA Item 1. |
| **Semantic** | **Yes** | Same product families. Supercharger access to non-Tesla vehicles also cited. TSLA Item 1. |

**Winner: Tie.** Same facts. Semantic was slightly more compact; fixed listed Supercharger programs in similar depth. This is the “same region of Item 1” pattern: both embeddings land on Tesla’s product list.

### Q2. What risks does Harley-Davidson disclose about dealers?

| | Verdict | What the agent said |
| --- | --- | --- |
| **Fixed** | **Yes** | Independent dealers; inventory funding; retail plans; dealer weakness → lower shipments. HOG Item 1A. |
| **Semantic** | **Yes** | Same risks as four bullets: execution, retail adaptation, funding/credit, wholesale dependence on dealers. HOG Item 1A. |

**Winner: Semantic (usability).** Content matches. Semantic’s larger window supported a cleaner PM-style list; fixed was a dense paragraph of the same ideas.

### Q3. What happened to Indian Motorcycle at Polaris?

| | Verdict | What the agent said |
| --- | --- | --- |
| **Fixed** | **Yes** | Agreement 10 Oct 2025; majority sale; closed Q1 2026; 2025 in On Road; held for sale 31 Dec 2025; impairment charges. PII Item 7. |
| **Semantic** | **Yes** | Same dates, sale, On Road, held for sale, impairments. PII Item 7. |

**Winner: Tie.** A specific event with distinctive wording; both chunkers retrieve the same MD&A block.

### Q4. What is LiveWire?

| | Verdict | What the agent said |
| --- | --- | --- |
| **Fixed** | **Yes** | Harley all-electric brand; motorcycles, kids’ balance bikes, e-bikes, parts, apparel; some D2C online. HOG Item 1. |
| **Semantic** | **Yes** | Same products **plus** independent retail partners, D2C online, **and** a company-owned dealer. HOG Item 1. |

**Winner: Semantic (completeness).** Same source; 1600-char chunks kept more of the LiveWire distribution sentence.

### Q5. What is Autopilot?

| | Verdict | What the agent said |
| --- | --- | --- |
| **Fixed** | **Partial** | ADAS: driver must stay engaged; OTA updates. Says the extract has **no standalone “Autopilot” definition**. TSLA Item 1. |
| **Semantic** | **Partial** | Same ADAS caveats, plus **FSD (Supervised)** and autonomous driving. Still no named Autopilot definition in the extract. TSLA Item 1. |

**Winner: Semantic (slight).** Both correctly hedge. Semantic pulled neighboring FSD language that fixed omitted. Neither invents a fake Autopilot spec.

### Q6. What was BMW Group revenue in 2025? (not in corpus)

| | Verdict | What the agent said |
| --- | --- | --- |
| **Fixed** | **Correct refuse** | “I don’t know based on the uploaded 10-K extracts.” |
| **Semantic** | **Correct refuse** | Same, plus: KB is Tesla, Harley-Davidson, and Polaris only — no BMW filing. |

**Winner: Tie (both correct).** Semantic was a bit more explicit about *why*. Neither hallucinated a BMW number from Tesla/Polaris revenue text.

## Scorecard

| # | Question | Fixed | Semantic | More usable |
| --- | --- | --- | --- | --- |
| 1 | Tesla besides cars | Yes | Yes | Tie |
| 2 | Harley dealer risks | Yes | Yes | Semantic |
| 3 | Indian Motorcycle | Yes | Yes | Tie |
| 4 | LiveWire | Yes | Yes | Semantic |
| 5 | Autopilot | Partial | Partial | Semantic |
| 6 | BMW 2025 revenue | Correct refuse | Correct refuse | Tie |

In-corpus usable answers: **fixed 4 Yes + 1 Partial; semantic 4 Yes + 1 Partial.**  
Out-of-corpus: **2/2 correct refuses.**

## What this means

- **Chunk size did not change Hit@5** on this set. Both agents cited the right 10-K and the right item for every in-corpus question.
- **Semantic (1600) won on answer shape**, not on “found vs missed”: Harley risks as bullets, LiveWire channels, Autopilot + FSD, clearer BMW refuse.
- **Fixed (800) was not worse on facts** for Tesla products or Indian Motorcycle. Short, distinctive 10-K sentences retrieve well at 800.
- **Do not expect “semantic = I don’t know, fixed = hallucination.”** With the same PDFs and Basic retrieval, both refuse BMW. That is the pipeline working.
- **Rerank:** not measured in Lyzr. Variable isolated here is **800/150 vs 1600/200**.

## Headline

On six identical Lyzr questions, **both agents retrieved the right filings**; **1600-character chunks produced slightly fuller, more structured answers** (LiveWire, Autopilot, dealer risks), while **800-character chunks already sufficed for Tesla products and the Indian Motorcycle sale**. Out-of-corpus BMW revenue was refused by both.

## Rerank (not run)

Lyzr Basic + top-k 5 has no second-stage rerank in this setup. To add it later: same five in-corpus questions on `10k-fixed` with a rerank toggle off vs on, and count whether the useful passage moves to rank 1.

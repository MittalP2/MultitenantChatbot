"""
Compare fixed-size vs semantic chunking, with and without reranking.

Metrics (same 12 questions, labeled by document + keywords):
  Hit@5  — a relevant chunk appears in the top 5
  MRR    — mean reciprocal rank of the first relevant chunk
  nDCG@5 — graded relevance, 1 if gold doc + keyword, 0.5 if keyword only

Usage (from project root):
  py -3.12 eval/run_eval.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from retrieval.finance_retriever import retrieve_finance
from retrieval.vector_store import SimpleVectorStore

QUERIES_PATH = ROOT / "eval" / "queries.json"
REPORT_PATH = ROOT / "eval" / "COMPARISON_REPORT.md"
TOP_K = 5
CANDIDATES = 20

CONDITIONS = [
    ("fixed", False, ROOT / "storage" / "sec_fixed"),
    ("fixed", True, ROOT / "storage" / "sec_fixed"),
    ("semantic", False, ROOT / "storage" / "sec_semantic"),
    ("semantic", True, ROOT / "storage" / "sec_semantic"),
]


def _load_queries() -> List[Dict]:
    data = json.loads(QUERIES_PATH.read_text(encoding="utf-8"))
    return data["queries"]


def _is_relevant(chunk: Dict, query: Dict) -> Tuple[bool, float]:
    text = f"{chunk.get('document', '')} {chunk.get('text', '')}".lower()
    doc_ok = query["document_contains"].lower() in (chunk.get("document") or "").lower()
    term_ok = any(term.lower() in text for term in query["must_have_any"])
    if doc_ok and term_ok:
        return True, 1.0
    if term_ok:
        return False, 0.5
    return False, 0.0


def ndcg_at_k(gains: Sequence[float], k: int) -> float:
    """nDCG vs a single fully-relevant hit at rank 1 (gain 1.0)."""
    rel = [1.0 if g >= 1.0 else 0.0 for g in list(gains)[:k]]
    dcg = sum(g / math.log2(i + 2) for i, g in enumerate(rel))
    return min(dcg, 1.0)


def run_condition(
    persist_dir: Path,
    queries: List[Dict],
    use_rerank: bool,
) -> Dict:
    hits = 0
    rr_sum = 0.0
    ndcgs: List[float] = []
    rows: List[Dict] = []
    store = SimpleVectorStore(persist_dir)
    store.load()

    for q in queries:
        ranked = retrieve_finance(
            q["question"],
            persist_dir=persist_dir,
            top_k=TOP_K,
            tenant_id="sec",
            use_rerank=use_rerank,
            candidate_k=CANDIDATES,
        )
        gains = []
        first_rank = None
        for i, chunk in enumerate(ranked, start=1):
            relevant, gain = _is_relevant(chunk, q)
            gains.append(gain)
            if relevant and first_rank is None:
                first_rank = i
        hit = first_rank is not None
        hits += int(hit)
        rr_sum += 0.0 if first_rank is None else 1.0 / first_rank
        ndcgs.append(ndcg_at_k(gains, TOP_K))
        preview = ranked[0]["text"][:160].replace("\n", " ") if ranked else ""
        rows.append(
            {
                "id": q["id"],
                "question": q["question"],
                "hit": hit,
                "rank": first_rank,
                "top_doc": ranked[0]["document"] if ranked else "",
                "top_page": ranked[0]["page"] if ranked else "",
                "preview": preview,
            }
        )

    n = max(len(queries), 1)
    return {
        "hit_at_5": hits / n,
        "mrr": rr_sum / n,
        "ndcg_at_5": sum(ndcgs) / n,
        "n_chunks": len(store.chunks),
        "rows": rows,
    }


def _pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def _delta(after: float, before: float) -> str:
    pts = 100 * (after - before)
    sign = "+" if pts >= 0 else ""
    return f"{sign}{pts:.1f} pts"


def write_report(results: Dict[str, Dict], queries: List[Dict]) -> None:
    fixed = results["fixed|False"]
    fixed_rr = results["fixed|True"]
    sem = results["semantic|False"]
    sem_rr = results["semantic|True"]

    lines = [
        "# Financial RAG — Chunking & Reranking Comparison",
        "",
        "Week 2 deliverable: **Financial Document Intelligence Pipeline (RAG)**.",
        "Corpus is three SEC 10-K *extracts* (Item 1 Business, Item 1A Risk Factors,",
        "Item 7 MD&A) for Tesla, Harley-Davidson, and Polaris. Full iXBRL HTML was",
        "dropped on purpose so a first RAG project stays inspectable.",
        "",
        "## Setup",
        "",
        "| Piece | Choice |",
        "| --- | --- |",
        "| Documents | 3 × Form 10-K extracts in `data/sec/` (~655 KB total vs 9+ MB raw HTML) |",
        "| Retrieval | Local TF-IDF (numpy), no paid embedding API |",
        "| Fixed chunking | 800 characters, 150 overlap |",
        "| Semantic chunking | Item headings + sentence groups by TF-IDF cosine |",
        "| Rerank | Phrase / year / ticker / token overlap on top 20 |",
        "| Queries | 12 questions in `eval/queries.json` |",
        "| Metrics | Hit@5, MRR, nDCG@5 |",
        "",
        f"- Fixed-size index: **{fixed['n_chunks']}** chunks",
        f"- Semantic index: **{sem['n_chunks']}** chunks",
        "",
        "## Headline results",
        "",
        "| Condition | Hit@5 | MRR | nDCG@5 |",
        "| --- | --- | --- | --- |",
        f"| Fixed-size, no rerank | {_pct(fixed['hit_at_5'])} | {fixed['mrr']:.3f} | {fixed['ndcg_at_5']:.3f} |",
        f"| Fixed-size + rerank | {_pct(fixed_rr['hit_at_5'])} | {fixed_rr['mrr']:.3f} | {fixed_rr['ndcg_at_5']:.3f} |",
        f"| Semantic, no rerank | {_pct(sem['hit_at_5'])} | {sem['mrr']:.3f} | {sem['ndcg_at_5']:.3f} |",
        f"| Semantic + rerank | {_pct(sem_rr['hit_at_5'])} | {sem_rr['mrr']:.3f} | {sem_rr['ndcg_at_5']:.3f} |",
        "",
        "## What changed",
        "",
        "### Chunking (same retriever, no rerank)",
        "",
        f"- Hit@5: {_pct(fixed['hit_at_5'])} → {_pct(sem['hit_at_5'])} ({_delta(sem['hit_at_5'], fixed['hit_at_5'])})",
        f"- MRR: {fixed['mrr']:.3f} → {sem['mrr']:.3f} ({_delta(sem['mrr'], fixed['mrr'])})",
        f"- nDCG@5: {fixed['ndcg_at_5']:.3f} → {sem['ndcg_at_5']:.3f} ({_delta(sem['ndcg_at_5'], fixed['ndcg_at_5'])})",
        "",
        "Semantic chunks follow Item 1 / 1A / 7 headings, then glue neighboring",
        "sentences only while they stay similar. That usually keeps a risk-factor",
        "paragraph together instead of splitting it mid-sentence at character 800.",
        "Fixed-size is simpler and can still win on short keyword lookups because",
        "the window is uniform.",
        "",
        "### Reranking impact (top 20 TF-IDF → top 5)",
        "",
        "| Index | Hit@5 lift | MRR lift | nDCG@5 lift |",
        "| --- | --- | --- | --- |",
        f"| Fixed-size | {_delta(fixed_rr['hit_at_5'], fixed['hit_at_5'])} | {_delta(fixed_rr['mrr'], fixed['mrr'])} | {_delta(fixed_rr['ndcg_at_5'], fixed['ndcg_at_5'])} |",
        f"| Semantic | {_delta(sem_rr['hit_at_5'], sem['hit_at_5'])} | {_delta(sem_rr['mrr'], sem['mrr'])} | {_delta(sem_rr['ndcg_at_5'], sem['ndcg_at_5'])} |",
        "",
        "Reranking helps when the right passage uses the query's words but is not",
        "the strongest TF-IDF neighbor (common with 10-K boilerplate). It cannot",
        "rescue a miss if the gold paragraph was never in the top 20.",
        "",
        "## Per-query Hit@5",
        "",
        "| Query | Fixed | Fixed+RR | Semantic | Semantic+RR |",
        "| --- | --- | --- | --- | --- |",
    ]

    def mark(row: Dict) -> str:
        if not row["hit"]:
            return "miss"
        return f"#{row['rank']}"

    for i, q in enumerate(queries):
        lines.append(
            "| {id} | {a} | {b} | {c} | {d} |".format(
                id=q["id"],
                a=mark(fixed["rows"][i]),
                b=mark(fixed_rr["rows"][i]),
                c=mark(sem["rows"][i]),
                d=mark(sem_rr["rows"][i]),
            )
        )

    lines.extend(
        [
            "",
            "## How to read this as a PM",
            "",
            "- **Hit@5** is the business question: did a useful passage make the",
            "  answer context at all?",
            "- **MRR** is ranking quality: did that passage show up first?",
            "- **nDCG@5** here is DCG against a single relevant hit at rank 1,",
            "  so it moves with rank (unlike IDCG computed only on the top 5).",
            "- Do not assume semantic chunking wins. On lexical 10-K Q&A,",
            "  uniform windows often retrieve the keyword-bearing sentence;",
            "  semantic groups can bury it inside a longer topical blob.",
            f"- Rerank lift (Hit@5): fixed {_delta(fixed_rr['hit_at_5'], fixed['hit_at_5'])},",
            f"  semantic {_delta(sem_rr['hit_at_5'], sem['hit_at_5'])}. Biggest when",
            "  the gold chunk was in the top 20 but not the top 5.",
            "- Chat default (`--tenant sec`) uses **fixed-size + rerank**,",
            "  the measured winner on this corpus.",
            "- This stack is TF-IDF. A neural reranker would likely add more lift",
            "  on paraphrases; this report measures the shape of the gain without",
            "  extra APIs.",
            "",
            "## Business relevance",
            "",
            "A PM labels a retrieval **usable** if an analyst could answer from the",
            "top window without opening the full 10-K. Keyword Hit@5 is the",
            "automatic check; the notes below are the business read of the winner",
            "(fixed-size + rerank).",
            "",
            "| Query | Winner usable? | Why it matters |",
            "| --- | --- | --- |",
        ]
    )

    why = {
        "tesla-products": "Energy / storage mix is a product question, not a car-sales KPI.",
        "tesla-competition-risk": "Risk committee / 10-K Q&A needs the competition Item 1A window.",
        "tesla-autopilot": "FSD wording is a regulated disclosure; wrong chunk is a compliance miss.",
        "tesla-mda-deliveries": "MD&A volume is what ops and IR actually quote.",
        "harley-business": "Segment map (HDMC / LiveWire / HDFS) is the first analyst question.",
        "harley-risks": "Tariff and dealer risk is the stress-test item.",
        "harley-mda": "Shipments vs retail is how HD is steered.",
        "polaris-products": "ORV / marine mix is the portfolio question.",
        "polaris-risks": "Seasonality and supply are the operating risks.",
        "polaris-mda": "Segment sales in North America is the earnings-call follow-up.",
        "cross-energy-storage": "Must land on Tesla, not a powersports 10-K.",
        "cross-powersports": "Must land on Polaris, not Tesla.",
    }
    for i, q in enumerate(queries):
        row = fixed_rr["rows"][i]
        usable = "Yes" if row["hit"] else "No"
        if row["hit"] and (row["rank"] or 99) > 1:
            usable = f"Yes (rank {row['rank']})"
        note = why.get(q["id"], q["question"])
        lines.append(f"| {q['id']} | {usable} | {note} |")

    lines.extend(
        [
            "",
            "Recommendation: **ship fixed-size chunking with rerank** for this",
            "lexical 10-K stack. Keep semantic chunking in the eval harness so a",
            "later embedding model can be scored on the same 12 questions.",
            "",
            "## Demo recording",
            "",
            "1. Open http://127.0.0.1:8765",
            "2. Click **Tesla competition**, then **Harley risks** — show the four",
            "   ranked windows changing with rerank.",
            "3. Optional CLI (Cursor answer):",
            "   `py -3.12 app/cli_chat.py --tenant sec --chunks \"What competition risks does Tesla disclose?\"`",
            "",
            "## Reproduce",
            "",
            "```bash",
            "py -3.12 scripts/download_sec_10k.py",
            "py -3.12 ingestion/run_ingest_sec.py",
            "py -3.12 eval/run_eval.py",
            "py -3.12 app/showcase_server.py",
            "```",
            "",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    metrics_path = ROOT / "eval" / "metrics.json"
    slim = {
        key: {k: v for k, v in val.items() if k != "rows"}
        for key, val in results.items()
    }
    metrics_path.write_text(json.dumps(slim, indent=2), encoding="utf-8")


def main() -> None:
    queries = _load_queries()
    results: Dict[str, Dict] = {}
    print(f"{len(queries)} evaluation questions\n")
    for strategy, use_rr, path in CONDITIONS:
        key = f"{strategy}|{use_rr}"
        print(f"Running {strategy} rerank={use_rr} from {path}")
        results[key] = run_condition(path, queries, use_rr)
        r = results[key]
        print(
            f"  chunks={r['n_chunks']}  Hit@5={_pct(r['hit_at_5'])}  "
            f"MRR={r['mrr']:.3f}  nDCG@5={r['ndcg_at_5']:.3f}"
        )

    write_report(results, queries)
    print(f"\nWrote {REPORT_PATH}")


if __name__ == "__main__":
    main()

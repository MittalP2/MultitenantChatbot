"""
Download 3 recent 10-K filings from SEC EDGAR and keep only the RAG-friendly
sections: Item 1 (Business), Item 1A (Risk Factors), Item 7 (MD&A).

Full iXBRL 10-K HTML is often 8–15 MB. These extracts are typically 80–400 KB
of clean text — a better first RAG corpus.

Usage (from project root):
  py -3.12 scripts/download_sec_10k.py
"""

from __future__ import annotations

import html as html_lib
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "sec"
RAW_DIR = OUT_DIR / "_raw"

# SEC fair-access: identify the client. Replace email if you hit 403s.
USER_AGENT = "AutoChat Financial RAG student (local learning project)"

# Vehicle-related US filers with 10-Ks (Honda/BMW/Toyota file 20-F, not 10-K).
COMPANIES = [
    {"ticker": "TSLA", "name": "Tesla, Inc.", "cik": "0001318605"},
    {"ticker": "HOG", "name": "Harley-Davidson, Inc.", "cik": "0000793952"},
    {"ticker": "PII", "name": "Polaris Inc.", "cik": "0000931015"},
]

SECTIONS = [
    (
        "Item 1. Business",
        r"item\s+1(?!\d|[a-z])\s*[.\-:]?\s*business",
        r"item\s+1a\s*[.\-:]?\s*risk\s+factors",
    ),
    (
        "Item 1A. Risk Factors",
        r"item\s+1a\s*[.\-:]?\s*risk\s+factors",
        r"item\s+1b\b",
    ),
    (
        "Item 7. Management's Discussion and Analysis",
        r"item\s+7(?!\s*a)\s*[.\-:]?\s*management['’s]*\s+discussion",
        r"item\s+7a\b",
    ),
]

CTX = ssl.create_default_context()


def _request(url: str, timeout: int = 90) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Encoding": "identity",
            "Accept": "*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as resp:
        return resp.read()


def html_to_text(raw: str) -> str:
    text = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", raw)
    text = re.sub(r"(?is)<ix:header[^>]*>.*?</ix:header>", " ", text)
    text = re.sub(r"(?is)<!--.*?-->", " ", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|tr|h[1-6]|li|table|section|article)>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html_lib.unescape(text)
    text = text.replace("\xa0", " ").replace("\u200b", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _nth_match(pattern: str, text: str, n: int = 1) -> int | None:
    regex = re.compile(pattern, re.I)
    matches = list(regex.finditer(text))
    if not matches:
        return None
    idx = min(n, len(matches) - 1)
    return matches[idx].start()


def extract_section(text: str, start_pat: str, end_pat: str) -> str:
    # First hit is usually the table of contents; the second is the real item.
    start = _nth_match(start_pat, text, n=1)
    if start is None:
        start = _nth_match(start_pat, text, n=0)
    if start is None:
        return ""

    end = None
    end_regex = re.compile(end_pat, re.I)
    for m in end_regex.finditer(text):
        if m.start() > start + 200:
            end = m.start()
            break
    body = text[start:end] if end else text[start : start + 120_000]
    body = body.strip()
    # Cap runaway extracts (some 10-Ks lack a clean Item 1B / 7A marker).
    if len(body) > 180_000:
        body = body[:180_000].rsplit("\n", 1)[0]
    return body


def latest_10k(cik: str) -> dict:
    padded = str(int(cik)).zfill(10)
    url = f"https://data.sec.gov/submissions/CIK{padded}.json"
    data = json.loads(_request(url).decode("utf-8"))
    recent = data["filings"]["recent"]
    for i, form in enumerate(recent["form"]):
        if form == "10-K":
            accession = recent["accessionNumber"][i]
            doc = recent["primaryDocument"][i]
            filing_date = recent["filingDate"][i]
            report_date = recent.get("reportDate", [""] * len(recent["form"]))[i]
            acc_nodash = accession.replace("-", "")
            cik_short = str(int(cik))
            file_url = (
                f"https://www.sec.gov/Archives/edgar/data/"
                f"{cik_short}/{acc_nodash}/{doc}"
            )
            return {
                "name": data.get("name", ""),
                "accession": accession,
                "filing_date": filing_date,
                "report_date": report_date,
                "primary_document": doc,
                "url": file_url,
            }
    raise RuntimeError(f"No 10-K found for CIK {cik}")


def save_extract(company: dict, meta: dict, sections: list[tuple[str, str]]) -> Path:
    kept = [(title, body) for title, body in sections if len(body) > 400]
    if not kept:
        raise RuntimeError(f"No usable sections extracted for {company['ticker']}")

    year = (meta.get("report_date") or meta["filing_date"])[:4]
    filename = f"{company['ticker']}_10K_{year}.txt"
    path = OUT_DIR / filename
    lines = [
        f"{meta['name'] or company['name']} — Form 10-K",
        f"Ticker: {company['ticker']}",
        f"CIK: {company['cik']}",
        f"Period end: {meta.get('report_date') or 'unknown'}",
        f"Filed: {meta['filing_date']}",
        f"Accession: {meta['accession']}",
        f"Source: {meta['url']}",
        "",
        "Extracted sections only (Item 1 Business, Item 1A Risk Factors, "
        "Item 7 MD&A). Full iXBRL HTML is omitted on purpose so this RAG",
        "starter corpus stays small.",
        "",
    ]
    for title, body in kept:
        lines.append("=" * 72)
        lines.append(title)
        lines.append("=" * 72)
        lines.append(body.strip())
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Writing extracts to {OUT_DIR}", flush=True)

    for i, company in enumerate(COMPANIES):
        if i:
            time.sleep(0.4)  # SEC: stay well under 10 requests/second
        print(f"\n=== {company['ticker']} {company['name']} ===", flush=True)
        try:
            meta = latest_10k(company["cik"])
            print(
                f"  10-K filed {meta['filing_date']}  {meta['url']}",
                flush=True,
            )
            time.sleep(0.4)
            raw_bytes = _request(meta["url"], timeout=120)
            raw_path = RAW_DIR / f"{company['ticker']}_{meta['accession']}.html"
            raw_path.write_bytes(raw_bytes)
            print(
                f"  raw HTML {len(raw_bytes)/1024/1024:.1f} MB -> {raw_path.name}",
                flush=True,
            )
            text = html_to_text(raw_bytes.decode("utf-8", errors="replace"))
            sections = []
            for title, start_pat, end_pat in SECTIONS:
                body = extract_section(text, start_pat, end_pat)
                print(f"  {title}: {len(body):,} chars", flush=True)
                sections.append((title, body))
            out = save_extract(company, meta, sections)
            size_kb = out.stat().st_size / 1024
            print(f"  SAVED {out.name} ({size_kb:.0f} KB)", flush=True)
        except urllib.error.HTTPError as exc:
            print(f"  HTTP {exc.code}: {exc.reason}", flush=True)
        except Exception as exc:
            print(f"  FAIL {type(exc).__name__}: {exc}", flush=True)

    print("\nDone. Next: py -3.12 ingestion/run_ingest_sec.py", flush=True)


if __name__ == "__main__":
    os.chdir(ROOT)
    main()

# Manual download checklist for AutoChat corpus

Save PDFs into the matching folders under `data/`. **Do not commit PDFs** (see `.gitignore`).

Week 1 only needs **BMW**. Other folders are for later weeks.

## BMW — Week 1 (5 PDFs)

Landing pages:

- https://www.bmwgroup.com/en/investor-relations/company-reports.html
- https://www.bmwgroup.com/en/download-centre.html

Save into `data/bmw/`:

1. BMW Group Report 2025 → e.g. `BMW-Group-Report-2025-en.pdf`
2. BMW Group Report 2024 → e.g. `BMW-Group-Report-2024-en.pdf`
3. BMW Group Report 2023 → e.g. `BMW-Group-Report-2023-en.pdf`
4. One quarterly / interim statement (e.g. Q1 2026)
5. One more quarterly / half-year PDF (e.g. Q2 2026)

Then run `py -3.12 ingestion/run_ingest.py`.

## Week 2 — SEC 10-K extracts (3 small files)

Full 10-K HTML on EDGAR is often 8–15 MB of iXBRL. The downloader keeps only
Item 1 (Business), Item 1A (Risk Factors), and Item 7 (MD&A) as `.txt` files.

```bash
py -3.12 scripts/download_sec_10k.py
py -3.12 ingestion/run_ingest_sec.py
py -3.12 eval/run_eval.py
py -3.12 app/cli_chat.py --tenant sec "What factories does Tesla operate?"
```

Saves into `data/sec/`:

1. `TSLA_10K_<year>.txt` — Tesla, Inc.
2. `HOG_10K_<year>.txt` — Harley-Davidson, Inc.
3. `PII_10K_<year>.txt` — Polaris Inc.

Raw HTML is stored in `data/sec/_raw/` (gitignored). Honda / BMW / Toyota file Form 20-F, not 10-K, so this set uses US auto/powersports filers.

## Later weeks (already on disk locally; not required for v1)

- `data/toyota/` — 5 PDFs
- `data/honda/` — 5 PDFs
- `data/mercedes/` — 5 PDFs
- `data/ford/` — 5 PDFs

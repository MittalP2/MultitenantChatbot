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

## Later weeks (already on disk locally; not required for v1)

- `data/toyota/` — 5 PDFs
- `data/honda/` — 5 PDFs
- `data/mercedes/` — 5 PDFs
- `data/ford/` — 5 PDFs

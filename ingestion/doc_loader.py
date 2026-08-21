"""Load PDFs and SEC text extracts into the same page-shaped records."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

from ingestion.pdf_loader import load_pdf

# Used when a 10-K item is huge (Harley MD&A). Still much larger than a
# typeset page so semantic grouping can see a whole topic.
CHARS_PER_PAGE = 5000

_ITEM_BANNER = re.compile(
    r"\n={8,}\nItem [^\n]+\n={8,}\n",
    re.I,
)


def _windows(text: str, size: int) -> List[str]:
    text = text.strip()
    if not text:
        return []
    out: List[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            split = text.rfind("\n\n", start, end)
            if split <= start:
                split = text.rfind(". ", start, end)
            if split > start:
                end = split + 1
        piece = text[start:end].strip()
        if piece:
            out.append(piece)
        start = end
    return out


def load_text_file(path: Path) -> List[Dict]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    text = "\n".join(line.rstrip() for line in raw.splitlines()).strip()
    if not text:
        return []

    spans: List[str] = []
    last = 0
    for m in _ITEM_BANNER.finditer("\n" + text):
        # matcher was on a padded copy; map back
        start = max(m.start() - 1, 0)
        if start > last:
            head = text[last:start].strip()
            if head:
                spans.append(head)
        last = start
    tail = text[last:].strip()
    if tail:
        spans.append(tail)
    if not spans:
        spans = [text]

    pages: List[Dict] = []
    page_no = 1
    for span in spans:
        for piece in _windows(span, CHARS_PER_PAGE):
            pages.append(
                {
                    "text": piece,
                    "page": page_no,
                    "document": path.name,
                    "path": str(path),
                }
            )
            page_no += 1
    return pages


def load_documents_from_dir(directory: Path) -> List[Dict]:
    directory = Path(directory)
    files = sorted(
        p
        for p in directory.iterdir()
        if p.is_file() and p.suffix.lower() in {".pdf", ".txt"}
    )
    if not files:
        raise FileNotFoundError(f"No PDF or TXT files found in {directory}")

    all_pages: List[Dict] = []
    for path in files:
        pages = load_pdf(path) if path.suffix.lower() == ".pdf" else load_text_file(path)
        print(f"  {path.name}: {len(pages)} pages with text")
        all_pages.extend(pages)
    return all_pages

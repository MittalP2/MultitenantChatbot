"""Load text from PDFs, page by page."""

from pathlib import Path
from typing import Dict, List

from pypdf import PdfReader


def load_pdf(path: Path) -> List[Dict]:
    """
    Return one record per page:
    {text, page, document, path}
    """
    reader = PdfReader(str(path))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = " ".join(text.split())
        if not text.strip():
            continue
        pages.append(
            {
                "text": text,
                "page": i,
                "document": path.name,
                "path": str(path),
            }
        )
    return pages


def load_pdfs_from_dir(directory: Path) -> List[Dict]:
    pdfs = sorted(directory.glob("*.pdf"))
    if not pdfs:
        raise FileNotFoundError(f"No PDFs found in {directory}")
    all_pages = []
    for pdf in pdfs:
        pages = load_pdf(pdf)
        print(f"  {pdf.name}: {len(pages)} pages with text")
        all_pages.extend(pages)
    return all_pages

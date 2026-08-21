"""Build small per-section PDFs for Lyzr uploads that keep failing on full files."""

from pathlib import Path
import re

from fpdf import FPDF

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "sec"
OUT = ROOT / "data" / "sec" / "lyzr_pdfs" / "parts"

SECTION_RE = re.compile(
    r"^={10,}\s*\n(Item\s+[^\n]+)\s*\n={10,}\s*\n",
    re.M,
)


def clean(text: str) -> str:
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2026": "...",
        "\xa0": " ",
        "\u2022": "-",
    }
    for a, b in replacements.items():
        text = text.replace(a, b)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def slug(title: str) -> str:
    t = title.lower()
    if t.startswith("item 1a"):
        return "item1a_risks"
    if re.match(r"item\s+1\b", t) and "1a" not in t[:10]:
        return "item1_business"
    if t.startswith("item 7"):
        return "item7_mda"
    return re.sub(r"[^a-z0-9]+", "_", t)[:40].strip("_")


def write_pdf(title: str, body: str, dest: Path) -> None:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.set_margins(16, 16, 16)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 11)
    pdf.multi_cell(w=178, h=6, text=clean(title))
    pdf.ln(2)
    pdf.set_font("Helvetica", size=9)
    text = clean(body)
    for raw in text.splitlines() or [" "]:
        line = raw if raw.strip() else " "
        for i in range(0, len(line), 100):
            pdf.multi_cell(w=178, h=4.2, text=line[i : i + 100])
    dest.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(dest))


def split_file(path: Path) -> None:
    raw = path.read_text(encoding="utf-8")
    matches = list(SECTION_RE.finditer(raw))
    ticker = path.stem.split("_")[0]
    if not matches:
        dest = OUT / f"{ticker}_full.pdf"
        print(f"No sections in {path.name}, writing {dest.name}", flush=True)
        write_pdf(path.stem, raw, dest)
        return
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        body = raw[start:end].strip()
        dest = OUT / f"{ticker}_{slug(title)}.pdf"
        print(f"Writing {dest.name} ({len(body)} chars)", flush=True)
        write_pdf(f"{ticker} — {title}", body, dest)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for src in sorted(SRC.glob("*_10K_*.txt")):
        split_file(src)
    # Tiny smoke test: first ~8k chars of Tesla Item 1
    tsla = (SRC / "TSLA_10K_2025.txt").read_text(encoding="utf-8")
    smoke = tsla[tsla.find("ITEM 1. BUSINESS") : tsla.find("ITEM 1. BUSINESS") + 8000]
    write_pdf("TSLA smoke test Item 1 excerpt", smoke, OUT / "ZZ_tesla_smoke_test.pdf")
    print(f"Done. Upload from {OUT}", flush=True)
    for p in sorted(OUT.glob("*.pdf")):
        print(f"  {p.name:32} {p.stat().st_size/1024:6.0f} KB", flush=True)


if __name__ == "__main__":
    main()

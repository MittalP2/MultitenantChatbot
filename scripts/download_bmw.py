import os
import ssl
import urllib.request

root = r"c:\Users\pulak\OneDrive\Documents\Pulak backup\Pulak\Cursor - Pulak\AutoChat"
outdir = os.path.join(root, "data", "bmw")
os.makedirs(outdir, exist_ok=True)

# Prefer smaller quarterly docs first, then annual reports
candidates = [
    (
        "q2_2025_financial_key_information.pdf",
        "https://www.bmwgroup.com/content/dam/grpw/websites/bmwgroup_com/ir/downloads/en/2025/q2/BMW_Group_Q2-25_Financial_Key_Information.pdf",
    ),
    (
        "bmw_group_report_2024.pdf",
        "https://www.bmwgroup.com/content/dam/grpw/websites/bmwgroup_com/ir/downloads/en/2025/bericht/BMW-Group-Report-2024-en.pdf",
    ),
    (
        "bmw_group_report_2023.pdf",
        "https://www.bmwgroup.com/content/dam/grpw/websites/bmwgroup_com/ir/downloads/en/2024/bericht/BMW-Group-Report-2023-en.pdf",
    ),
    (
        "bmw_group_report_2025.pdf",
        "https://www.bmwgroup.com/content/dam/grpw/websites/bmwgroup_com/ir/downloads/en/2026/bericht/BMW-Group-Report-2025-en.pdf",
    ),
    (
        "bmw_group_report_2022.pdf",
        "https://www.bmwgroup.com/content/dam/grpw/websites/bmwgroup_com/ir/downloads/en/2023/gb/BMW-Group-Report-2022-en.pdf",
    ),
]

ctx = ssl.create_default_context()
for name, url in candidates:
    path = os.path.join(outdir, name)
    print(f"START {name}", flush=True)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "application/pdf,*/*",
            "Referer": "https://www.bmwgroup.com/en/investor-relations/company-reports.html",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60, context=ctx) as r:
            chunks = []
            total = 0
            while True:
                chunk = r.read(1024 * 256)
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
                if total % (1024 * 1024) < 256 * 1024:
                    print(f"  ... {total/1024/1024:.1f} MB", flush=True)
            data = b"".join(chunks)
        if not data.startswith(b"%PDF"):
            print(f"NOTPDF {name} bytes={len(data)}", flush=True)
            continue
        with open(path, "wb") as f:
            f.write(data)
        print(f"OK {name} {len(data)} bytes", flush=True)
    except Exception as e:
        print(f"FAIL {name}: {type(e).__name__}: {e}", flush=True)

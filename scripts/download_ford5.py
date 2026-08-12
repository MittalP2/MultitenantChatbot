import os
import ssl
import urllib.request

root = r"c:\Users\pulak\OneDrive\Documents\Pulak backup\Pulak\Cursor - Pulak\AutoChat"
path = os.path.join(root, "data", "ford", "integrated_sustainability_financial_report_2024.pdf")
url = "https://corporate.ford.com/content/dam/corporate/us/en-us/documents/reports/2024-integrated-sustainability-and-financial-report.pdf"

req = urllib.request.Request(
    url,
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/pdf,*/*",
    },
)
print("START ford integrated 2024", flush=True)
with urllib.request.urlopen(req, timeout=90, context=ssl.create_default_context()) as r:
    data = r.read()
print("bytes", len(data), "magic", data[:5], flush=True)
if data.startswith(b"%PDF"):
    with open(path, "wb") as f:
        f.write(data)
    print("OK", path, flush=True)
else:
    print("NOT PDF", flush=True)

"""Read-only diagnostics for a BVB original PDF; no Telegram, no approvals."""
from __future__ import annotations
from io import BytesIO
import subprocess
import tempfile
import pathlib
import urllib.request
import fitz

URL = "https://bvb.ro/infocont/infocont26/IMP_20261016121841_Notif-operatiuni-IMP-16-10-2026.pdf"

def main():
    req = urllib.request.Request(URL, headers={"User-Agent": "WestcottSourceReview/1.0", "Accept": "application/pdf"})
    with urllib.request.urlopen(req, timeout=18) as response:
        data = response.read(6_000_001)
        print("ORIGINAL_PDF_HTTP:", response.status)
        print("ORIGINAL_PDF_TYPE:", response.headers.get("Content-Type", "").split(";")[0])
        print("ORIGINAL_PDF_BYTES:", len(data))
    if not data.startswith(b"%PDF-") or len(data) > 6_000_000:
        print("ORIGINAL_PDF_VALID: FALSE")
        return
    with tempfile.TemporaryDirectory() as t:
        p=pathlib.Path(t);(p/"original.pdf").write_bytes(data)
        proc = subprocess.run(["pdftotext","-enc","UTF-8",str(p/"original.pdf"),str(p/"original.txt")],capture_output=True,timeout=15)
        pdftotext=(" ".join((p/"original.txt").read_text(encoding="utf-8").split())
                   if proc.returncode==0 and (p/"original.txt").exists() else "")
    doc = fitz.open(stream=data, filetype="pdf")
    fitz_text = " ".join(" ".join(page.get_text("text",sort=True) for page in doc).split())
    print("ORIGINAL_PDF_PAGES:", len(doc))
    print("ORIGINAL_PDF_PDFFONT_COUNT:", len(pdftotext))
    print("ORIGINAL_PDF_FITZ_COUNT:", len(fitz_text))
    print("ORIGINAL_PDF_TEXT_USABLE_PDFFONT:", len(pdftotext) >= 80)
    print("ORIGINAL_PDF_TEXT_USABLE_FITZ:", len(fitz_text) >= 80)
    print("NO_NEWS_OR_MEDIA_SENT: TRUE")

if __name__ == "__main__":
    main()

"""Original BVB PDF disclosure handling. No OCR or invented image data.

A visual preview is a faithful rasterization of page 1 of an official PDF.
The text is extracted from the same file, with no secondary summaries. Only
use it in Telegram when the original-media reuse rights gate is approved.
"""
from __future__ import annotations

import fitz


def verify_original_pdf(payload, title):
    if not payload.startswith(b"%PDF-") or len(payload) > 8_000_000:
        return None
    document = None
    try:
        document = fitz.open(stream=payload, filetype="pdf")
        if document.needs_pass or not 1 <= len(document) <= 100:
            return None
        pages = [document[i].get_text("text", sort=True) for i in range(min(len(document), 4))]
        text = " ".join(" ".join(pages).split())
        if len(text) < 140:
            # Text-only gate: do not claim an image-only scan was fact checked.
            return None
        first_page = document[0]
        bounds = first_page.rect
        if min(bounds.width, bounds.height) < 150 or max(bounds.width, bounds.height) > 2500:
            return None
        scale = min(1.35, 1600.0 / max(bounds.width, bounds.height))
        pix = first_page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        if pix.width * pix.height > 4_500_000:
            return None
        png = pix.tobytes("png")
        if len(png) > 6_000_000:
            return None
        return {"kind": "official_pdf_page1", "preview_png": png,
                "original_title": title, "page_count": len(document)}, text[:9500]
    except (RuntimeError, ValueError, fitz.FileDataError):
        return None
    finally:
        if document is not None:
            document.close()

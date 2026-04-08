from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


def extract_pages(pdf_path: Path) -> list[dict[str, int | str]]:
    reader = PdfReader(str(pdf_path))
    pages: list[dict[str, int | str]] = []

    for index, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if not text:
            continue
        pages.append(
            {
                "page_number": index,
                "text": " ".join(text.split()),
            }
        )

    return pages

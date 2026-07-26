"""
PDF Parser — services/pdf_parser.py

Extracts text from a PDF file (supplied as raw bytes) page by page using
PyMuPDF (imported as ``fitz``).

Responsibilities:
- Open a PDF from bytes without writing to disk
- Iterate every page and extract plain text
- Normalise whitespace (collapse runs of blank lines, strip edges)
- Skip completely blank pages
- Raise descriptive errors for:
    * Password-protected PDFs
    * Scanned / image-only PDFs (no extractable text at all)

Usage::

    with open("paper.pdf", "rb") as f:
        pdf_bytes = f.read()

    pages = parse_pdf(pdf_bytes)
    # [{"page_number": 1, "text": "..."}, {"page_number": 2, "text": "..."}, ...]
"""

import re

import fitz  # PyMuPDF


def parse_pdf(pdf_bytes: bytes) -> list[dict]:
    """
    Extract text from a PDF supplied as raw bytes.

    Args:
        pdf_bytes: Raw bytes of the uploaded PDF file.

    Returns:
        List of dicts, one per non-empty page::

            [
                {"page_number": 1, "text": "Cleaned page text..."},
                {"page_number": 2, "text": "..."},
                ...
            ]

        ``page_number`` is 1-indexed (matches human-readable page numbers).

    Raises:
        ValueError: If the PDF is password-protected (cannot be read without a
            password) or if the PDF contains no extractable text at all (e.g.
            a purely scanned/image-based document).
        RuntimeError: For unexpected PyMuPDF errors (corrupt file, etc.).
    """
    # ── Open document ─────────────────────────────────────────────────────────
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except fitz.FileDataError as exc:
        raise RuntimeError(
            f"Could not open PDF — the file may be corrupt or not a valid PDF. "
            f"Details: {exc}"
        ) from exc

    # ── Password protection check ─────────────────────────────────────────────
    if doc.needs_pass:
        # We have no password, so we cannot authenticate.
        doc.close()
        raise ValueError(
            "This PDF is password-protected. Please upload an unprotected version."
        )

    total_pages = len(doc)
    if total_pages == 0:
        doc.close()
        raise ValueError("The uploaded PDF has no pages.")

    # ── Extract text page by page ─────────────────────────────────────────────
    pages: list[dict] = []

    for page_index in range(total_pages):
        page = doc.load_page(page_index)
        raw_text: str = page.get_text("text")

        cleaned = _clean_text(raw_text)

        # Skip pages that are blank after cleaning (images, decorative pages…)
        if not cleaned:
            continue

        pages.append(
            {
                "page_number": page_index + 1,  # 1-indexed
                "text": cleaned,
            }
        )

    doc.close()

    # ── Guard: no extractable text found anywhere ─────────────────────────────
    if not pages:
        raise ValueError(
            "Could not extract text from this PDF. "
            "The file may be scanned or image-based. "
            "DocuMind currently only supports text-based PDFs."
        )

    return pages


# ── Helpers ───────────────────────────────────────────────────────────────────

def _clean_text(text: str) -> str:
    """
    Normalise extracted page text.

    Steps:
    1. Replace Windows-style line endings with Unix-style.
    2. Collapse two-or-more consecutive newlines into a single newline
       (preserves paragraph breaks without excessive blank lines).
    3. Strip leading and trailing whitespace from the whole block.
    4. Strip each individual line to remove trailing spaces / tabs.

    Args:
        text: Raw text string from ``page.get_text("text")``.

    Returns:
        Cleaned string, or an empty string if there was no meaningful content.
    """
    if not text:
        return ""

    # Normalise line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Strip trailing whitespace on each line
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)

    # Collapse runs of 2+ blank lines into one blank line
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Strip the whole block
    text = text.strip()

    return text

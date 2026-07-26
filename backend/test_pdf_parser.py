"""
Quick manual test for pdf_parser.py

Run from the backend/ directory:
    python test_pdf_parser.py <path_to_pdf>

If no path is given, it creates a tiny in-memory PDF to test the basic flow.
"""

import sys
import os

# Make sure we can import from services/
sys.path.insert(0, os.path.dirname(__file__))

from services.pdf_parser import parse_pdf


def test_with_file(path: str):
    print(f"\n{'='*60}")
    print(f"Testing: {path}")
    print('='*60)
    with open(path, "rb") as f:
        pdf_bytes = f.read()
    try:
        pages = parse_pdf(pdf_bytes)
        print(f"[OK] Extracted {len(pages)} pages with text")
        for page in pages[:3]:  # Show first 3 pages
            preview = page["text"][:200].replace("\n", " ")
            print(f"  Page {page['page_number']:>3}: {preview!r}...")
    except ValueError as e:
        print(f"[ERROR] ValueError (expected for bad PDFs): {e}")
    except RuntimeError as e:
        print(f"[ERROR] RuntimeError: {e}")


def test_with_synthetic():
    """Create a minimal valid PDF in memory and test parsing."""
    import io

    # Minimal PDF with one page of text (hand-crafted, no external dep)
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj

2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj

3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]
   /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj

4 0 obj
<< /Length 44 >>
stream
BT /F1 12 Tf 100 700 Td (Hello DocuMind!) Tj ET
endstream
endobj

5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj

xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000274 00000 n 
0000000370 00000 n 

trailer
<< /Size 6 /Root 1 0 R >>
startxref
451
%%EOF"""

    print(f"\n{'='*60}")
    print("Testing: synthetic in-memory PDF")
    print('='*60)
    try:
        pages = parse_pdf(pdf_content)
        print(f"[OK] Extracted {len(pages)} pages")
        for page in pages:
            print(f"  Page {page['page_number']}: {page['text']!r}")
    except Exception as e:
        print(f"  Note: {e}")
        print("  (This is normal for minimal hand-crafted PDFs - use a real PDF for real testing)")


if __name__ == "__main__":
    # Synthetic test first (always runs)
    test_with_synthetic()

    # File tests (if paths given on command line)
    if len(sys.argv) > 1:
        for pdf_path in sys.argv[1:]:
            test_with_file(pdf_path)
    else:
        print("\nTip: Pass PDF file path(s) as arguments to test with real documents:")
        print("  python test_pdf_parser.py paper.pdf textbook.pdf report.pdf")

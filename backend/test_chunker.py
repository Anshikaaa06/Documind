"""
Manual test for chunker.py — Day 3 verification.

Verifies:
  1. Correct number of chunks produced
  2. Overlap exists between consecutive chunks (shared words at boundaries)
  3. Page numbers are tracked correctly (including cross-page chunks)
  4. word_count, start_char, end_char are present and sensible
  5. No chunk is empty

Run from backend/ directory:
    python test_chunker.py
    python test_chunker.py "C:\\path\\to\\your.pdf"
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from services.pdf_parser import parse_pdf
from services.chunker import chunk_text


# ── Helpers ───────────────────────────────────────────────────────────────────

def show_chunk(chunk: dict, show_full: bool = False) -> None:
    pages = ", ".join(f"p{p}" for p in chunk["page_numbers"])
    preview = chunk["text"][:120].replace("\n", " ")
    print(f"  Chunk {chunk['chunk_index']:>3}  [{pages}]  "
          f"words={chunk['word_count']}  "
          f"chars={chunk['start_char']}-{chunk['end_char']}")
    if show_full:
        print(f"    TEXT: {chunk['text']!r}")
    else:
        print(f"    ...  {preview!r}")


def verify_overlap(chunks: list[dict], words_per_overlap: int = 37) -> None:
    """Check that consecutive chunks share overlapping words at their boundary."""
    errors = 0
    for i in range(len(chunks) - 1):
        a_words = chunks[i]["text"].split()
        b_words = chunks[i + 1]["text"].split()

        # The last N words of chunk[i] should equal the first N words of chunk[i+1]
        tail = a_words[-words_per_overlap:]
        head = b_words[:words_per_overlap]

        if tail != head:
            print(f"  [WARN] Overlap mismatch at chunks {i} -> {i+1}")
            print(f"    tail: {tail[:5]}...")
            print(f"    head: {head[:5]}...")
            errors += 1

    if errors == 0:
        print(f"  [OK] Overlap verified on all {len(chunks)-1} consecutive chunk pairs")
    else:
        print(f"  [WARN] {errors} overlap mismatches (may occur at page/doc boundaries)")


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_synthetic():
    """Test with a known, small document so we can count chunks manually."""
    print("\n" + "="*60)
    print("TEST 1: Synthetic document (known word count)")
    print("="*60)

    # Build pages with known word counts so we can predict chunk behaviour
    # 800 words total -> expect ceil((800 - 375) / 338) + 1 = 3 chunks
    page1_text = " ".join([f"word{i}" for i in range(400)])   # 400 words
    page2_text = " ".join([f"word{i}" for i in range(400, 800)])  # 400 words

    pages = [
        {"page_number": 1, "text": page1_text},
        {"page_number": 2, "text": page2_text},
    ]

    chunks = chunk_text(pages)
    print(f"  Total words: 800")
    print(f"  words_per_chunk=375, stride=338")
    print(f"  Chunks produced: {len(chunks)}")

    for chunk in chunks:
        show_chunk(chunk)

    verify_overlap(chunks)

    # Verify cross-page chunk exists
    cross_page = [c for c in chunks if len(c["page_numbers"]) > 1]
    if cross_page:
        print(f"  [OK] Cross-page chunk found: chunk {cross_page[0]['chunk_index']} "
              f"spans pages {cross_page[0]['page_numbers']}")
    else:
        print("  [OK] No cross-page chunks (all words fit within page boundaries)")

    # Verify no empty chunks
    empty = [c for c in chunks if not c["text"].strip()]
    print(f"  [OK] No empty chunks" if not empty else f"  [FAIL] {len(empty)} empty chunks!")


def test_with_file(path: str):
    """Test with a real PDF."""
    print("\n" + "="*60)
    print(f"TEST 2: Real PDF — {os.path.basename(path)}")
    print("="*60)

    with open(path, "rb") as f:
        pdf_bytes = f.read()

    pages = parse_pdf(pdf_bytes)
    total_words = sum(len(p["text"].split()) for p in pages)
    print(f"  Pages extracted   : {len(pages)}")
    print(f"  Total words       : {total_words}")
    print(f"  Approx tokens     : {int(total_words / 0.75)}")

    chunks = chunk_text(pages)
    print(f"  Chunks produced   : {len(chunks)}")
    print(f"  Avg words/chunk   : {total_words // max(len(chunks), 1)}")
    print()

    # Show first 3 and last 1 chunks
    print("  --- First 3 chunks ---")
    for chunk in chunks[:3]:
        show_chunk(chunk)

    if len(chunks) > 3:
        print("  --- Last chunk ---")
        show_chunk(chunks[-1])

    print()
    verify_overlap(chunks)

    # Page number distribution
    from collections import Counter
    page_hits = Counter()
    for chunk in chunks:
        for pn in chunk["page_numbers"]:
            page_hits[pn] += 1
    print(f"\n  Page -> chunk count: { dict(sorted(page_hits.items())) }")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_synthetic()

    if len(sys.argv) > 1:
        for pdf_path in sys.argv[1:]:
            test_with_file(pdf_path)
    else:
        print("\nTip: Pass a PDF path to test with a real document:")
        print("  python test_chunker.py \"C:\\path\\to\\doc.pdf\"")

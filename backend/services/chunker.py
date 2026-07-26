"""
Chunker — services/chunker.py

Splits a list of pages (from pdf_parser.parse_pdf) into overlapping text
chunks of approximately 500 tokens each, with 50-token overlap.

Strategy (per PRD section 6.2):
  - 1 token ≈ 0.75 words  →  500 tokens ≈ 375 words per chunk
  - 50-token overlap       →  38 words of overlap between consecutive chunks
  - Stride                 →  375 - 38 = 337 words between chunk start positions
  - Each word is annotated with its source page number so that chunks which
    span a page boundary correctly report both page numbers.
  - Character offsets (start_char / end_char) are tracked in the flattened,
    marker-free word stream for potential future highlighting use.
"""


def chunk_text(
    pages: list[dict],
    chunk_size: int = 500,   # Target chunk size in approximate tokens
    overlap: int = 50,        # Overlap between consecutive chunks in approximate tokens
) -> list[dict]:
    """
    Split document pages into overlapping chunks.

    Args:
        pages: Output of ``pdf_parser.parse_pdf()`` — list of
            ``{"page_number": int, "text": str}`` dicts.
        chunk_size: Target chunk size in approximate tokens
            (1 token ≈ 0.75 words, so 500 tokens ≈ 375 words).
        overlap: Overlap between consecutive chunks in approximate tokens
            (50 tokens ≈ 38 words).

    Returns:
        List of chunk dicts::

            [
                {
                    "chunk_index": 0,
                    "text": "The actual chunk content...",
                    "page_numbers": [1],        # Could span pages, e.g. [3, 4]
                    "start_char": 0,
                    "end_char": 1847,
                    "word_count": 374,
                },
                ...
            ]

    Raises:
        ValueError: If ``pages`` is empty.
    """
    if not pages:
        raise ValueError("pages list is empty — nothing to chunk")

    # ── Convert token targets to word counts ──────────────────────────────────
    # PRD: 1 token ≈ 0.75 words  →  words = tokens * 0.75
    words_per_chunk: int = max(1, int(chunk_size * 0.75))        # 375
    words_per_overlap: int = max(0, int(overlap * 0.75))         # 37
    stride: int = max(1, words_per_chunk - words_per_overlap)    # 338

    # ── Build annotated word list ─────────────────────────────────────────────
    # Each entry: (word: str, page_number: int)
    # Iterating page by page, every word gets labelled with its source page.
    # This is equivalent to the [PAGE_X] marker approach in the PRD but cleaner:
    # no marker strings end up in the final chunk text.
    annotated: list[tuple[str, int]] = []
    for page in pages:
        page_num = page["page_number"]
        for word in page["text"].split():
            annotated.append((word, page_num))

    if not annotated:
        raise ValueError(
            "No words found in any page — the document may be empty after cleaning."
        )

    # Pre-compute the character start position of every word in the
    # marker-free stream (word + one space after it).
    word_char_starts: list[int] = []
    char_cursor = 0
    for word, _ in annotated:
        word_char_starts.append(char_cursor)
        char_cursor += len(word) + 1   # +1 for the space between words

    # ── Sliding window ────────────────────────────────────────────────────────
    chunks: list[dict] = []
    chunk_index = 0
    pos = 0   # index into annotated[]

    while pos < len(annotated):
        end_pos = min(pos + words_per_chunk, len(annotated))
        window = annotated[pos:end_pos]

        # Reconstruct chunk text (no page markers — clean prose)
        chunk_words = [w for w, _ in window]
        chunk_text_str = " ".join(chunk_words)

        # Collect unique page numbers that contributed words to this chunk,
        # preserving sorted order (so cross-page chunks look like [3, 4])
        seen: set[int] = set()
        page_numbers: list[int] = []
        for _, pn in window:
            if pn not in seen:
                seen.add(pn)
                page_numbers.append(pn)

        # Character offsets in the flat word stream
        start_char = word_char_starts[pos]
        # end_char: position after the last character of the last word in this chunk
        last_idx = end_pos - 1
        end_char = word_char_starts[last_idx] + len(annotated[last_idx][0])

        chunks.append(
            {
                "chunk_index": chunk_index,
                "text": chunk_text_str,
                "page_numbers": page_numbers,
                "start_char": start_char,
                "end_char": end_char,
                "word_count": len(chunk_words),
            }
        )

        chunk_index += 1

        # Advance by stride; stop if we've consumed all words
        if end_pos >= len(annotated):
            break
        pos += stride

    return chunks

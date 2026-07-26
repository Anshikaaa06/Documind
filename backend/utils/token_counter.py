"""
Token Counter — utils/token_counter.py

Approximate token counting to prevent exceeding LLM context limits.

Used by ``prompt_builder.py`` to budget context before sending to the API.

Two methods:
  ``"approximate"``  — word-count / 0.75  (fast, no extra deps)
  ``"tiktoken"``     — exact GPT tokeniser (requires ``tiktoken`` package)

Per PRD section 6.7.
"""


def count_tokens(text: str, method: str = "approximate") -> int:
    """
    Count approximate tokens in ``text``.

    Args:
        text: The string to measure.
        method: ``"approximate"`` (default) uses word-count heuristic.
            ``"tiktoken"`` uses the ``cl100k_base`` encoding for GPT-exact
            counts (requires the ``tiktoken`` package to be installed).

    Returns:
        Integer token estimate.

    Examples::

        >>> count_tokens("Hello world this is a test sentence.")
        9   # approximate
    """
    if not text:
        return 0

    if method == "tiktoken":
        try:
            import tiktoken
            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except ImportError:
            # Gracefully fall back to approximation if tiktoken not installed
            pass

    # Approximate: 1 token ≈ 0.75 words  →  words / 0.75
    word_count = len(text.split())
    return int(word_count / 0.75)

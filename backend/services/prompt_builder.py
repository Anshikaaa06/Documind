"""
Prompt Builder — services/prompt_builder.py

Constructs the LLM prompt from retrieved chunks and the user's question,
using the EXACT system prompt and user prompt template from PRD section 6.5.

Per PRD section 6.5.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.token_counter import count_tokens

# ── System prompt — exact text from PRD section 6.5 ──────────────────────────
SYSTEM_PROMPT = """You are a precise research assistant. Your job is to answer questions based ONLY on the provided document excerpts.

Rules you must follow:
1. ONLY use information from the provided context to answer. Do not use your own knowledge.
2. If the context does not contain enough information to fully answer the question, explicitly say "The document does not contain enough information to fully answer this question" and then share whatever partial answer the context supports.
3. After your answer, list the sources you used in this exact format:
   [Source: Page X] or [Source: Pages X-Y]
4. If multiple sources support different parts of your answer, cite each one inline right after the relevant sentence.
5. Use direct references like "According to the document..." or "The document states that..."
6. Never make up information. Never extrapolate beyond what the context says.
7. If asked about something completely unrelated to the document, respond: "This question does not appear to be related to the uploaded document.\""""


def build_prompt(
    question: str,
    retrieved_chunks: list[dict],   # From vector_store.query()
    max_context_tokens: int = 3000,
) -> list[dict]:
    """
    Build the messages array for the LLM API call.

    Uses the exact system prompt and user prompt template from PRD section 6.5.
    Checks approximate token budget: if total context would exceed
    ``max_context_tokens``, the longest chunks are progressively truncated
    until the budget is satisfied.

    Args:
        question: The user's question string.
        retrieved_chunks: Output of ``vector_store.query()`` — list of dicts
            with ``text`` and ``page_numbers`` keys (up to 5).
        max_context_tokens: Soft limit for total context window tokens.

    Returns:
        Messages list ready to send to the LLM API::

            [
                {"role": "system", "content": "<system prompt>"},
                {"role": "user",   "content": "<excerpts + question>"},
            ]
    """
    if not question or not question.strip():
        raise ValueError("question must not be empty")

    if not retrieved_chunks:
        # No context retrieved — still send the question; LLM will say it can't answer
        user_content = (
            "No relevant excerpts were found in the document for this question.\n\n"
            f"Please answer the following question as best you can given that context:\n\n{question}"
        )
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

    # ── Token budget management ───────────────────────────────────────────────
    # Estimate tokens used by non-chunk parts of the prompt
    system_tokens = count_tokens(SYSTEM_PROMPT)
    question_tokens = count_tokens(question)
    template_overhead = 80   # approximate tokens for labels, dashes, boilerplate

    available_for_chunks = max_context_tokens - system_tokens - question_tokens - template_overhead
    available_for_chunks = max(500, available_for_chunks)   # always allow at least 500

    # Trim chunks if needed (trim longest first)
    chunks = list(retrieved_chunks)   # copy so we don't mutate the caller's list
    while True:
        total_chunk_tokens = sum(count_tokens(c["text"]) for c in chunks)
        if total_chunk_tokens <= available_for_chunks or len(chunks) == 0:
            break
        # Find the longest chunk and trim it by 20%
        longest_idx = max(range(len(chunks)), key=lambda i: count_tokens(chunks[i]["text"]))
        text = chunks[longest_idx]["text"]
        words = text.split()
        chunks[longest_idx] = dict(chunks[longest_idx])   # shallow copy
        chunks[longest_idx]["text"] = " ".join(words[:int(len(words) * 0.8)])

    # ── Build user prompt — exact template from PRD section 6.5 ──────────────
    excerpt_lines = []
    for i, chunk in enumerate(chunks, start=1):
        page_nums = chunk["page_numbers"]
        if len(page_nums) == 1:
            page_label = f"Page {page_nums[0]}"
        elif len(page_nums) == 2:
            page_label = f"Pages {page_nums[0]}-{page_nums[1]}"
        else:
            page_label = f"Pages {page_nums[0]}-{page_nums[-1]}"

        excerpt_lines.append(f"EXCERPT {i} ({page_label}):\n{chunk['text']}")

    excerpts_block = "\n\n".join(excerpt_lines)

    user_content = (
        "I have retrieved the following excerpts from the document that may be relevant "
        "to your question. Each excerpt is labeled with its source page number(s).\n\n"
        "---\n"
        f"{excerpts_block}\n"
        "---\n\n"
        "Based on the above excerpts, please answer the following question:\n\n"
        f"{question}"
    )

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


"""
Full pipeline test — Day 6-7 verification.

Runs the complete RAG pipeline from a PDF file end-to-end:
  PDF file → parse → chunk → embed → store → query → retrieve → prompt → LLM → answer

Usage:
    python test_pipeline.py "C:\\path\\to\\doc.pdf" "Your question here"

    # Uses ANTHROPIC_API_KEY from .env by default.
    # To use OpenAI: set LLM_PROVIDER=openai in .env

Requirements:
    - .env file with ANTHROPIC_API_KEY (or OPENAI_API_KEY + LLM_PROVIDER=openai)
    - A PDF file path as the first argument
    - A question as the second argument (optional — uses a default question)
"""

import asyncio
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from services.pdf_parser import parse_pdf
from services.chunker import chunk_text
from services.embedder import Embedder
from services.vector_store import VectorStore
from services.prompt_builder import build_prompt
from services.llm_client import LLMClient
from utils.token_counter import count_tokens


# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_PDF = r"C:\Users\Anshika Prasad\Downloads\ION_Group_Interview_Prep.pdf"
DEFAULT_QUESTION = "What types of questions are asked in the ION Group technical interview?"


# ── Pipeline ──────────────────────────────────────────────────────────────────

async def run_pipeline(pdf_path: str, question: str):
    sep = "=" * 60
    print(f"\n{sep}")
    print("DocuMind — Full RAG Pipeline Test")
    print(f"{sep}")
    print(f"PDF      : {os.path.basename(pdf_path)}")
    print(f"Question : {question}")
    print(f"LLM      : {os.getenv('LLM_PROVIDER', 'anthropic')}")
    print(f"Embed    : {os.getenv('EMBEDDING_PROVIDER', 'local')}")

    doc_id = f"test-{uuid.uuid4()}"

    # ── Step 1: Parse PDF ─────────────────────────────────────────────────────
    print(f"\n{'-'*40}")
    print("[1] Parsing PDF...")
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    pages = parse_pdf(pdf_bytes)
    total_words = sum(len(p["text"].split()) for p in pages)
    print(f"    Pages extracted : {len(pages)}")
    print(f"    Total words     : {total_words}")

    # ── Step 2: Chunk ─────────────────────────────────────────────────────────
    print(f"\n[2] Chunking...")
    chunks = chunk_text(pages)
    print(f"    Chunks produced : {len(chunks)}")
    print(f"    Avg words/chunk : {total_words // max(len(chunks), 1)}")

    # ── Step 3: Embed ─────────────────────────────────────────────────────────
    print(f"\n[3] Embedding chunks...")
    embed_provider = os.getenv("EMBEDDING_PROVIDER", "local")
    embedder = Embedder(provider=embed_provider)
    embeddings = embedder.embed_batch([c["text"] for c in chunks])
    print(f"    [OK] {len(embeddings)} embeddings, dim={len(embeddings[0])}")

    # ── Step 4: Store in ChromaDB ─────────────────────────────────────────────
    print(f"\n[4] Storing in ChromaDB...")
    store = VectorStore(persist_dir="./data/chroma_db")
    store.create_collection(doc_id)
    store.add_chunks(doc_id, chunks, embeddings)
    print(f"    [OK] Stored in collection: {doc_id}")

    # ── Step 5: Query ─────────────────────────────────────────────────────────
    print(f"\n[5] Retrieving relevant chunks for question...")
    query_vec = embedder.embed_text(question)
    results = store.query(doc_id, query_vec, n_results=5)
    print(f"    [OK] Top {len(results)} chunks retrieved:")
    for r in results:
        print(f"      chunk={r['chunk_index']:>2}  pages={r['page_numbers']}  "
              f"relevance={r['relevance_score']:.3f}  "
              f"text={r['text'][:60]!r}...")

    # ── Step 6: Build prompt ──────────────────────────────────────────────────
    print(f"\n[6] Building prompt...")
    messages = build_prompt(question, results)
    total_prompt_tokens = sum(count_tokens(m["content"]) for m in messages)
    print(f"    Messages        : {len(messages)}")
    print(f"    ~Prompt tokens  : {total_prompt_tokens}")
    print(f"    System preview  : {messages[0]['content'][:80]!r}...")
    print(f"    User preview    : {messages[1]['content'][:120]!r}...")

    # ── Step 7: Call LLM ──────────────────────────────────────────────────────
    print(f"\n[7] Calling LLM API...")
    llm_provider = os.getenv("LLM_PROVIDER", "anthropic")
    llm = LLMClient(provider=llm_provider)
    result = await llm.generate(messages)
    print(f"    [OK] Response received")
    print(f"    Model           : {result['model']}")
    print(f"    Input tokens    : {result['usage']['input_tokens']}")
    print(f"    Output tokens   : {result['usage']['output_tokens']}")

    # ── Step 8: Display answer ────────────────────────────────────────────────
    print(f"\n{sep}")
    print("ANSWER:")
    print(f"{sep}")
    print(result["answer"])
    print(f"{sep}")

    # ── Cleanup ───────────────────────────────────────────────────────────────
    store.delete_collection(doc_id)
    print(f"\n[Cleanup] Test collection deleted.")

    return result


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PDF
    question = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_QUESTION

    if not os.path.exists(pdf_path):
        print(f"[ERROR] PDF not found: {pdf_path}")
        sys.exit(1)

    asyncio.run(run_pipeline(pdf_path, question))

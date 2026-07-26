"""
Integration test for Day 4-5: Embedder + VectorStore.

Verifies (per PRD Day 4-5 test spec):
  1. Embed 3 chunks with distinct topics
  2. Store them in ChromaDB
  3. Query with a related question
  4. Verify the most relevant chunk comes back first
  5. Clean up (delete the test collection)

Run from backend/ directory:
    python test_embedder_vectorstore.py

Uses the LOCAL embedding provider by default (no API key needed).
To test with OpenAI, set OPENAI_API_KEY in .env and pass --provider openai.
"""

import sys
import os
import uuid
import shutil

sys.path.insert(0, os.path.dirname(__file__))

from services.embedder import Embedder
from services.vector_store import VectorStore

# ── Test data ─────────────────────────────────────────────────────────────────

CHUNKS = [
    {
        "chunk_index": 0,
        "text": (
            "Python is a high-level programming language known for its simple syntax "
            "and readability. It supports multiple programming paradigms including "
            "object-oriented, functional, and procedural styles. Python is widely used "
            "in web development, data science, machine learning, and automation."
        ),
        "page_numbers": [1],
        "word_count": 50,
    },
    {
        "chunk_index": 1,
        "text": (
            "The French Revolution began in 1789 and fundamentally transformed French "
            "society. The storming of the Bastille on July 14, 1789, is considered its "
            "symbolic starting point. The Revolution led to the rise of Napoleon Bonaparte "
            "and influenced democratic movements across Europe and the Americas."
        ),
        "page_numbers": [2],
        "word_count": 50,
    },
    {
        "chunk_index": 2,
        "text": (
            "Photosynthesis is the process by which plants convert sunlight into chemical "
            "energy. Chlorophyll in plant cells absorbs light, which drives the conversion "
            "of carbon dioxide and water into glucose and oxygen. This process is the "
            "foundation of most food chains on Earth."
        ),
        "page_numbers": [3],
        "word_count": 50,
    },
]

QUERIES = [
    {
        "question": "What is Python used for in data science?",
        "expected_chunk_index": 0,
        "description": "Should retrieve the Python programming chunk",
    },
    {
        "question": "When did the French Revolution start?",
        "expected_chunk_index": 1,
        "description": "Should retrieve the French Revolution history chunk",
    },
    {
        "question": "How do plants produce energy from sunlight?",
        "expected_chunk_index": 2,
        "description": "Should retrieve the photosynthesis biology chunk",
    },
]


# ── Test runner ───────────────────────────────────────────────────────────────

def run_test(provider: str = "local"):
    test_doc_id = f"test-{uuid.uuid4()}"
    test_db_path = "./data/test_chroma_db"

    print(f"\n{'='*60}")
    print(f"Embedder + VectorStore Integration Test")
    print(f"Provider : {provider}")
    print(f"Doc ID   : {test_doc_id}")
    print(f"{'='*60}")

    # ── Step 1: Initialise ────────────────────────────────────────────────────
    print("\n[1] Initialising Embedder...")
    embedder = Embedder(provider=provider)
    print(f"    Model      : {embedder._model_name}")
    print(f"    Dimensions : {embedder.dimensions}")

    print("\n[1] Initialising VectorStore...")
    store = VectorStore(persist_dir=test_db_path)

    # ── Step 2: Embed chunks ──────────────────────────────────────────────────
    print(f"\n[2] Embedding {len(CHUNKS)} chunks...")
    texts = [c["text"] for c in CHUNKS]
    embeddings = embedder.embed_batch(texts)
    print(f"    [OK] Got {len(embeddings)} embeddings, dim={len(embeddings[0])}")

    # ── Step 3: Store in ChromaDB ─────────────────────────────────────────────
    print(f"\n[3] Storing chunks in ChromaDB...")
    store.create_collection(test_doc_id)
    store.add_chunks(test_doc_id, CHUNKS, embeddings)
    print(f"    [OK] Stored {len(CHUNKS)} chunks in collection '{test_doc_id}'")

    # Verify list_collections
    all_cols = store.list_collections()
    assert test_doc_id in all_cols, f"Collection not listed! Got: {all_cols}"
    print(f"    [OK] list_collections() includes our doc_id")

    # ── Step 4: Query and verify retrieval ────────────────────────────────────
    print(f"\n[4] Running {len(QUERIES)} retrieval queries...")
    all_passed = True

    for q in QUERIES:
        query_vec = embedder.embed_text(q["question"])
        results = store.query(test_doc_id, query_vec, n_results=3)

        top = results[0]
        passed = top["chunk_index"] == q["expected_chunk_index"]
        status = "[OK]" if passed else "[FAIL]"
        if not passed:
            all_passed = False

        print(f"\n    Q: {q['question']!r}")
        print(f"    {status} Top result: chunk_index={top['chunk_index']} "
              f"(expected {q['expected_chunk_index']})")
        print(f"       relevance={top['relevance_score']:.4f}  "
              f"distance={top['distance']:.4f}  "
              f"pages={top['page_numbers']}")
        print(f"       text: {top['text'][:80]!r}...")

        if not passed:
            print(f"    EXPECTED: chunk_index={q['expected_chunk_index']} "
                  f"({q['description']})")
            print("    All results:")
            for r in results:
                print(f"      chunk={r['chunk_index']} relevance={r['relevance_score']:.4f} "
                      f"text={r['text'][:60]!r}")

    # ── Step 5: Clean up ──────────────────────────────────────────────────────
    print(f"\n[5] Cleaning up test collection...")
    store.delete_collection(test_doc_id)
    remaining = store.list_collections()
    assert test_doc_id not in remaining, "Collection still exists after delete!"
    print(f"    [OK] Collection deleted successfully")

    # Release the ChromaDB client so it closes all file handles (Windows fix)
    del store
    import gc; gc.collect()

    import time; time.sleep(0.5)   # give OS a moment to release locks

    # Remove test DB directory
    if os.path.exists(test_db_path):
        try:
            shutil.rmtree(test_db_path)
            print(f"    [OK] Test DB directory removed")
        except PermissionError:
            print(f"    [WARN] Could not remove test DB dir (Windows file lock) — safe to ignore")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    if all_passed:
        print("[PASS] All retrieval queries returned the correct top chunk!")
    else:
        print("[FAIL] Some queries did not return the expected chunk first.")
        print("       This may indicate an embedding quality issue.")
    print(f"{'='*60}\n")

    return all_passed


if __name__ == "__main__":
    provider = "local"
    if "--provider" in sys.argv:
        idx = sys.argv.index("--provider")
        provider = sys.argv[idx + 1]

    # Load .env for OpenAI key if needed
    from dotenv import load_dotenv
    load_dotenv()

    success = run_test(provider=provider)
    sys.exit(0 if success else 1)

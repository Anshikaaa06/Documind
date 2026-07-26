"""
API test script — tests POST /api/upload and POST /api/query via HTTP.
Run from backend/ directory with the server already running:
    python test_api.py
"""
import json
import sys
import urllib.request
import urllib.parse
import os

BASE_URL = "http://127.0.0.1:8000"
PDF_PATH = r"C:\Users\Anshika Prasad\Downloads\ION_Group_Interview_Prep.pdf"


def multipart_upload(url, filepath):
    """Upload a file using multipart/form-data without third-party libs."""
    filename = os.path.basename(filepath)
    boundary = "----DocuMindBoundary7x3k9"

    with open(filepath, "rb") as f:
        file_data = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: application/pdf\r\n\r\n"
    ).encode("utf-8") + file_data + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body)),
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())


def post_json(url, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


if __name__ == "__main__":
    sep = "=" * 60

    # ── Step 1: Health check ──────────────────────────────────────────────────
    print(f"\n{sep}\nStep 1: Health check\n{sep}")
    with urllib.request.urlopen(f"{BASE_URL}/health") as r:
        print(json.loads(r.read()))

    # ── Step 2: Upload PDF ────────────────────────────────────────────────────
    print(f"\n{sep}\nStep 2: POST /api/upload\n{sep}")
    print(f"Uploading: {os.path.basename(PDF_PATH)}")
    print("(This embeds the document — may take ~30s on first run)...")

    upload_result = multipart_upload(f"{BASE_URL}/api/upload", PDF_PATH)
    print(json.dumps(upload_result, indent=2))

    doc_id = upload_result["doc_id"]

    # ── Step 3: Query ─────────────────────────────────────────────────────────
    questions = [
        "What types of technical questions are asked in ION Group interviews?",
        "What is the interview process structure at ION Group?",
    ]

    for i, q in enumerate(questions, 1):
        print(f"\n{sep}\nStep 3.{i}: POST /api/query\n{sep}")
        print(f"Q: {q}")
        result = post_json(f"{BASE_URL}/api/query", {"doc_id": doc_id, "question": q})

        print(f"\nANSWER ({result['model']}):")
        print(result["answer"])
        print(f"\nSOURCES ({len(result['sources'])} chunks):")
        for src in result["sources"]:
            print(f"  Pages {src['page_numbers']}  score={src['relevance_score']:.3f}  "
                  f"text={src['chunk_text'][:80]!r}...")
        print(f"\nTokens: input={result['tokens_used']['input']}, "
              f"output={result['tokens_used']['output']}")

    print(f"\n{sep}\nAll tests passed!\n{sep}")

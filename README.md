# DocuMind — AI Document Research Assistant

> Upload a PDF. Ask questions. Get answers with **exact page citations**.
>
> Built from scratch — no LangChain, no RAG frameworks. Every layer hand-written.

![DocuMind UI](./docs/screenshot.png)

---

## What it does

DocuMind is a full-stack RAG (Retrieval-Augmented Generation) application. Upload any PDF — a research paper, textbook, contract, report — and ask natural-language questions. The system retrieves the most relevant sections of the document and feeds them to an LLM, which answers **only** from the provided context and cites the exact pages it used.

```
You:  "What are the main risks identified in this report?"
AI:   "According to the document, three primary risks are identified:
       1. Market volatility... [Source: Page 4]
       2. Regulatory uncertainty... [Source: Page 7]
       3. Supply chain disruption... [Source: Pages 9-10]"
```

---

## Architecture

```
PDF Upload
    │
    ▼
┌────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                       │
│                                                            │
│  ┌────────────┐   ┌───────────────┐   ┌────────────────┐  │
│  │ PDF Parser │──▶│    Chunker    │──▶│    Embedder    │  │
│  │ (PyMuPDF)  │   │  500 tokens   │   │ all-MiniLM-L6  │  │
│  │            │   │  50 overlap   │   │  (384-dim)     │  │
│  └────────────┘   └───────────────┘   └───────┬────────┘  │
│                                               │            │
│                                               ▼            │
│                                      ┌────────────────┐   │
│                                      │   ChromaDB     │   │
│                                      │  (cosine sim)  │   │
│                                      └───────┬────────┘   │
│                                              │             │
│  User question ──embed──▶ similarity search─┘             │
│                                              │             │
│                                              ▼             │
│                              ┌───────────────────────┐    │
│                              │    Prompt Builder     │    │
│                              │  (top-5 chunks +      │    │
│                              │   exact PRD template) │    │
│                              └──────────┬────────────┘    │
│                                         │                  │
│                                         ▼                  │
│                              ┌───────────────────────┐    │
│                              │      LLM Client       │    │
│                              │  Groq / Anthropic /   │    │
│                              │  OpenAI (switchable)  │    │
│                              └───────────────────────┘    │
└────────────────────────────────────────────────────────────┘
    │
    ▼
React Frontend  (drag-and-drop upload → chat → source panel)
```

---

## Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Backend | FastAPI + Python 3.11 | Async, fast, type-safe |
| PDF parsing | PyMuPDF (`fitz`) | Handles complex layouts better than PyPDF2 |
| Chunking | Hand-written sliding window | 500-token chunks, 50-token overlap, page tracking |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` | Free, local, 384-dim; swap to `text-embedding-3-small` for production |
| Vector DB | ChromaDB (persistent local) | Zero infra overhead, cosine similarity |
| LLM | Groq `llama-3.3-70b-versatile` (**free**) | Swap to Anthropic Claude / GPT-4o-mini via env var |
| Frontend | React 18 + Vite + Tailwind CSS | Glassmorphism dark UI |
| Server | Uvicorn (development) | Gunicorn for production |

**Zero LangChain. Zero RAG frameworks.** Every component — chunking, embedding, retrieval, prompt construction, citation extraction — is implemented from scratch.

---

## Quickstart (local)

### Prerequisites
- Python 3.11+
- Node.js 18+
- A **free** [Groq API key](https://console.groq.com) (takes 2 minutes, no credit card)

### 1 — Clone & set up backend

```bash
git clone https://github.com/<your-username>/documind.git
cd documind/backend

# Create virtual environment
python -m venv .venv

# Activate it
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### 2 — Start backend

```bash
# From documind/backend/
uvicorn main:app --reload
# → http://localhost:8000
# → Swagger docs: http://localhost:8000/docs
```

### 3 — Start frontend (separate terminal)

```bash
cd documind/frontend
npm install
npm run dev
# → http://localhost:5173
```

### 4 — Use it
1. Open **http://localhost:5173**
2. Drag and drop any PDF (up to 20 MB)
3. Wait ~20 seconds for processing (embedding runs locally)
4. Ask questions in the chat — answers include `[Source: Page X]` citations
5. Click **Sources** to see the retrieved document excerpts

---

## Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in:

| Variable | Required | Description |
|---|---|---|
| `LLM_PROVIDER` | Yes | `groq`, `anthropic`, or `openai` |
| `GROQ_API_KEY` | If using Groq | Free at console.groq.com |
| `ANTHROPIC_API_KEY` | If using Anthropic | claude-sonnet-4-6 |
| `OPENAI_API_KEY` | If using OpenAI | gpt-4o-mini |
| `EMBEDDING_PROVIDER` | No | `local` (default) or `openai` |
| `CHROMA_PERSIST_DIR` | No | Path to ChromaDB storage (default: `./data/chroma_db`) |
| `FRONTEND_URL` | No | For CORS (default: `http://localhost:5173`) |

---

## API Reference

### `POST /api/upload`

Upload a PDF and run the full processing pipeline.

**Request:** `multipart/form-data` with `file` field (PDF, max 20 MB)

**Response:**
```json
{
  "doc_id": "3f2c1a4b-...",
  "filename": "research_paper.pdf",
  "total_pages": 12,
  "total_chunks": 18,
  "message": "Document processed successfully"
}
```

**Errors:**
- `415` — Not a PDF
- `413` — File exceeds 20 MB
- `422` — PDF has no extractable text (scanned image PDF)

---

### `POST /api/query`

Ask a question against an uploaded document.

**Request:**
```json
{
  "doc_id": "3f2c1a4b-...",
  "question": "What are the main conclusions?"
}
```

**Response:**
```json
{
  "answer": "According to the document, the main conclusions are...\n[Source: Page 8]",
  "sources": [
    {
      "page_numbers": [8, 9],
      "chunk_text": "The study concludes that...",
      "relevance_score": 0.87
    }
  ],
  "model": "llama-3.3-70b-versatile",
  "tokens_used": { "input": 2925, "output": 238 }
}
```

**Errors:**
- `404` — doc_id not found (upload first)
- `400` — empty question
- `504` — LLM API timeout

---

## Project Structure

```
documind/
├── backend/
│   ├── main.py                  # FastAPI app, CORS, lifespan
│   ├── requirements.txt
│   ├── .env.example
│   ├── routers/
│   │   ├── upload.py            # POST /api/upload
│   │   └── query.py             # POST /api/query
│   ├── services/
│   │   ├── pdf_parser.py        # PyMuPDF text extraction
│   │   ├── chunker.py           # Sliding-window chunking
│   │   ├── embedder.py          # Local / OpenAI embeddings
│   │   ├── vector_store.py      # ChromaDB operations
│   │   ├── prompt_builder.py    # Exact PRD prompt templates
│   │   └── llm_client.py        # Groq / Anthropic / OpenAI client
│   ├── models/
│   │   └── schemas.py           # Pydantic request/response models
│   ├── utils/
│   │   └── token_counter.py     # Token estimation (no tiktoken dep)
│   └── data/
│       └── chroma_db/           # Persistent vector store (git-ignored)
│
└── frontend/
    ├── src/
    │   ├── App.jsx              # Root — upload ↔ chat state machine
    │   ├── index.css            # Tailwind + design system
    │   └── components/
    │       ├── FileUpload.jsx   # Drag-and-drop PDF uploader
    │       ├── ChatInterface.jsx # Split-pane chat layout
    │       ├── ChatMessage.jsx  # Message bubbles + citation badges
    │       ├── SourcePanel.jsx  # Retrieved chunks sidebar
    │       └── SourceCard.jsx   # Individual chunk card
    ├── tailwind.config.js
    └── index.html
```

---

## Key Engineering Decisions

### Why hand-written RAG instead of LangChain?
LangChain abstracts away everything this project is meant to demonstrate. Building each layer manually forces understanding of: how chunking strategy affects retrieval quality, why embedding dimensions matter, how cosine similarity actually works, what happens when the context window fills up, and why prompt structure matters for citation accuracy.

### Chunking strategy
500-token sliding window with 50-token overlap. The overlap prevents important context from being split across chunk boundaries. Page numbers are tracked per-token so every chunk knows exactly which pages it came from — enabling precise `[Source: Page X]` citations even when a chunk spans two pages.

### Embedding model choice
`all-MiniLM-L6-v2` runs entirely locally (384-dim, ~90 MB download). No API key, no per-query cost, no latency from external calls. For production, swap to OpenAI `text-embedding-3-small` (1536-dim) by setting `EMBEDDING_PROVIDER=openai` — the code paths are identical.

### LLM provider abstraction
`LLMClient` wraps Groq (free), Anthropic, and OpenAI behind a single `async generate(messages)` interface. Switch providers by changing one env var. Groq's `llama-3.3-70b-versatile` is used by default — it's free with 14,400 requests/day and comparable quality to GPT-4o-mini.

### Citation enforcement
The system prompt explicitly instructs the LLM to cite page numbers using `[Source: Page X]` format after every claim. The frontend's `ChatMessage` component parses these inline and renders them as pill badges — no post-processing regex needed.

---

## What I Learned

- **Chunk size matters**: 500 tokens hits the sweet spot between retrieval precision and context completeness. Smaller chunks lose paragraph context; larger chunks hurt retrieval recall.
- **Prompt engineering reduces hallucination**: Explicitly constraining the LLM to provided context — and instructing it to say "the document doesn't contain this information" — dramatically reduces fabricated answers compared to open-ended prompting.
- **Embedding model tradeoffs**: Local `all-MiniLM-L6-v2` achieves ~0.88 cosine similarity on semantically distinct test queries with zero cost. The gap vs OpenAI embeddings is noticeable only for highly domain-specific technical language.
- **ChromaDB metadata limitation**: ChromaDB only stores scalar values in metadata fields. Page number lists (`[1, 2, 3]`) must be JSON-serialised before storage and deserialised on retrieval — a subtle but important implementation detail.
- **Windows file locking**: ChromaDB holds file handles open until the client is garbage-collected. On Windows this means the client reference must be explicitly deleted before `shutil.rmtree` can clean up test directories.

---

## What I'd Improve Next

- **Streaming responses** — stream LLM tokens to the frontend for better perceived latency
- **Multi-document sessions** — allow querying across multiple uploaded PDFs simultaneously
- **OCR support** — integrate Tesseract for scanned/image PDFs that produce no extractable text
- **Conversation memory** — maintain chat history for multi-turn follow-up questions
- **Evaluation metrics** — retrieval precision@k, answer faithfulness scoring using a judge LLM
- **Document management** — list/delete previously uploaded documents via `GET/DELETE /api/documents`

---

## License

MIT — see [LICENSE](./LICENSE)

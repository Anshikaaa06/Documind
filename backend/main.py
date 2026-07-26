"""
DocuMind — FastAPI application entry point.

Handles:
- App creation and metadata
- CORS middleware configuration
- Router registration
- Startup/shutdown lifecycle events
- Health check endpoint
"""

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import upload, query

# Load environment variables from .env file (if present)
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle handler."""
    # ── Startup ──────────────────────────────────────────────────────────────
    print("DocuMind backend starting up...")
    print(f"  LLM provider    : {os.getenv('LLM_PROVIDER', 'anthropic')}")
    print(f"  Embedding model : {os.getenv('EMBEDDING_PROVIDER', 'openai')}")
    print(f"  ChromaDB path   : {os.getenv('CHROMA_PERSIST_DIR', './data/chroma_db')}")
    yield
    # ── Shutdown ─────────────────────────────────────────────────────────────
    print("DocuMind backend shutting down.")


app = FastAPI(
    title="DocuMind API",
    description="AI Document Research Assistant — RAG pipeline built from scratch",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────────────
# Allow requests from the React dev server (localhost:5173) and any
# deployed frontend URL configured via FRONTEND_URL environment variable.
_frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3000",   # Alternate dev port
        _frontend_url,             # Production frontend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(upload.router, prefix="/api")
app.include_router(query.router, prefix="/api")


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Simple liveness probe.
    Returns HTTP 200 with {"status": "ok"} when the server is running.
    """
    return {"status": "ok"}

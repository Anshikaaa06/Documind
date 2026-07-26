"""
Upload router — POST /api/upload

Handles PDF file upload, validation, and the full processing pipeline:
  1. Validate file (MIME type, magic bytes, 20 MB size limit)
  2. Parse PDF → list of pages
  3. Chunk text → overlapping chunks
  4. Generate embeddings
  5. Store in ChromaDB

Per PRD section 8.
"""

import os
import uuid
import logging

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from models.schemas import UploadResponse
from services.chunker import chunk_text
from services.embedder import Embedder
from services.pdf_parser import parse_pdf
from services.vector_store import VectorStore

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Upload"])

# ── Constants ─────────────────────────────────────────────────────────────────
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024   # 20 MB
PDF_MAGIC_BYTES = b"%PDF"                # All valid PDFs start with %PDF


# ── Route ─────────────────────────────────────────────────────────────────────

@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF document",
    description=(
        "Accepts a PDF file via multipart/form-data. "
        "Runs the full RAG processing pipeline and returns a doc_id "
        "to use in subsequent /api/query calls."
    ),
)
async def upload_document(file: UploadFile = File(...)) -> UploadResponse:
    """
    POST /api/upload

    Accepts a multipart/form-data PDF file, runs the full processing pipeline,
    and stores the embeddings in ChromaDB.

    Returns:
        UploadResponse with doc_id, filename, total_pages, total_chunks.

    Raises:
        422: If no file is provided.
        415: If the file is not a PDF (checked by MIME type AND magic bytes).
        413: If the file exceeds 20 MB.
        422: If the PDF has no extractable text pages.
        500: For unexpected server errors during processing.
    """

    # ── 1. MIME type check (fast, first line of defence) ─────────────────────
    content_type = file.content_type or ""
    if content_type not in ("application/pdf", "application/octet-stream", ""):
        if not content_type.endswith("pdf"):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Only PDF files are accepted. Got: {content_type!r}",
            )

    # ── 2. Read file bytes ────────────────────────────────────────────────────
    pdf_bytes = await file.read()

    # ── 3. Size check ─────────────────────────────────────────────────────────
    if len(pdf_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"File too large: {len(pdf_bytes) / (1024*1024):.1f} MB. "
                f"Maximum allowed: {MAX_FILE_SIZE_BYTES // (1024*1024)} MB."
            ),
        )

    # ── 4. Magic-byte check (validates real PDF structure) ────────────────────
    if not pdf_bytes.startswith(PDF_MAGIC_BYTES):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                "File does not appear to be a valid PDF "
                "(missing %PDF header). Please upload a real PDF file."
            ),
        )

    filename = file.filename or "document.pdf"
    doc_id = str(uuid.uuid4())

    logger.info(f"Processing upload: filename={filename!r}, size={len(pdf_bytes)} bytes, doc_id={doc_id}")

    try:
        # ── 5. Parse PDF → pages ──────────────────────────────────────────────
        try:
            pages = parse_pdf(pdf_bytes)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            )

        if not pages:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="PDF contains no extractable text. It may be a scanned image PDF.",
            )

        # ── 6. Chunk text ─────────────────────────────────────────────────────
        chunks = chunk_text(pages)
        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="PDF produced no text chunks. The document may be empty.",
            )

        # ── 7. Embed chunks ───────────────────────────────────────────────────
        embed_provider = os.getenv("EMBEDDING_PROVIDER", "local")
        embedder = Embedder(provider=embed_provider)
        texts = [chunk["text"] for chunk in chunks]
        embeddings = embedder.embed_batch(texts)

        # ── 8. Store in ChromaDB ──────────────────────────────────────────────
        chroma_dir = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db")
        store = VectorStore(persist_dir=chroma_dir)
        store.create_collection(doc_id)
        store.add_chunks(doc_id, chunks, embeddings)

        logger.info(
            f"Upload complete: doc_id={doc_id}, pages={len(pages)}, chunks={len(chunks)}"
        )

        return UploadResponse(
            doc_id=doc_id,
            filename=filename,
            total_pages=len(pages),
            total_chunks=len(chunks),
            message="Document processed successfully",
        )

    except HTTPException:
        raise   # Re-raise HTTP errors as-is

    except Exception as exc:
        logger.exception(f"Unexpected error processing upload for doc_id={doc_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while processing the document: {exc}",
        )

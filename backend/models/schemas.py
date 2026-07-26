"""
Pydantic schemas — models/schemas.py

Request and response models for all API endpoints.
Full schemas filled in alongside router implementations (Day 8-9).
"""

from pydantic import BaseModel, Field


# ── Upload ────────────────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    """Returned by POST /api/upload on success."""
    doc_id: str = Field(..., description="UUID4 identifying this document's vector collection")
    filename: str = Field(..., description="Original filename of the uploaded PDF")
    total_pages: int = Field(..., description="Number of pages extracted from the PDF")
    total_chunks: int = Field(..., description="Number of text chunks created")
    message: str = Field(default="Document processed successfully")


# ── Query ─────────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    """Body for POST /api/query."""
    doc_id: str = Field(..., description="UUID4 returned by /api/upload")
    question: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="The user's natural-language question",
    )


class SourceChunk(BaseModel):
    """A single retrieved context chunk shown in the source panel."""
    page_numbers: list[int] = Field(..., description="Page number(s) this chunk came from")
    chunk_text: str = Field(..., description="The actual text of the retrieved chunk")
    relevance_score: float = Field(..., description="0–1 relevance score (1 = most relevant)")


class QueryResponse(BaseModel):
    """Returned by POST /api/query on success."""
    answer: str = Field(..., description="LLM-generated answer with inline citations")
    sources: list[SourceChunk] = Field(..., description="Top-5 retrieved context chunks")
    model: str = Field(..., description="LLM model name used")
    tokens_used: dict = Field(..., description='{"input": int, "output": int}')


# ── Documents list ────────────────────────────────────────────────────────────

class DocumentInfo(BaseModel):
    """Metadata for a single stored document."""
    doc_id: str
    filename: str
    uploaded_at: str   # ISO 8601 datetime string
    total_chunks: int


class DocumentsResponse(BaseModel):
    """Returned by GET /api/documents."""
    documents: list[DocumentInfo]

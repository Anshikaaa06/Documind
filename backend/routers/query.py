"""
Query router — POST /api/query

Handles user questions against a previously uploaded document:
  1. Validate doc_id and question
  2. Embed the question
  3. Similarity search in ChromaDB (top 5 chunks)
  4. Build prompt with retrieved chunks
  5. Call LLM API
  6. Return structured answer + sources

Per PRD section 9.
"""

import os
import logging

from fastapi import APIRouter, HTTPException, status

from models.schemas import QueryRequest, QueryResponse, SourceChunk
from services.embedder import Embedder
from services.llm_client import LLMClient
from services.prompt_builder import build_prompt
from services.vector_store import VectorStore

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Query"])

# Maximum number of chunks to retrieve and pass to the LLM
_TOP_K = 5


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Ask a question about an uploaded document",
    description=(
        "Send a natural-language question along with a doc_id returned by /api/upload. "
        "Returns an LLM-generated answer with page citations and the source chunks used."
    ),
)
async def query_document(body: QueryRequest) -> QueryResponse:
    """
    POST /api/query

    Body: { doc_id: str, question: str }

    Returns:
        QueryResponse with answer, sources, model, tokens_used.

    Raises:
        400: If the question is empty.
        404: If the doc_id does not exist in the vector store.
        500: For unexpected errors during retrieval or LLM call.
    """

    # ── 1. Basic validation ───────────────────────────────────────────────────
    question = body.question.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question must not be empty.",
        )

    logger.info(f"Query received: doc_id={body.doc_id!r}, question={question[:80]!r}")

    try:
        # ── 2. Embed the question ─────────────────────────────────────────────
        embed_provider = os.getenv("EMBEDDING_PROVIDER", "local")
        embedder = Embedder(provider=embed_provider)
        query_vector = embedder.embed_text(question)

        # ── 3. Retrieve top-K chunks from ChromaDB ────────────────────────────
        chroma_dir = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db")
        store = VectorStore(persist_dir=chroma_dir)

        try:
            retrieved_chunks = store.query(body.doc_id, query_vector, n_results=_TOP_K)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Document '{body.doc_id}' not found. "
                    "Please upload the document first using POST /api/upload."
                ),
            )

        logger.info(f"Retrieved {len(retrieved_chunks)} chunks for doc_id={body.doc_id!r}")

        # ── 4. Build prompt ───────────────────────────────────────────────────
        messages = build_prompt(question, retrieved_chunks)

        # ── 5. Call LLM ───────────────────────────────────────────────────────
        llm_provider = os.getenv("LLM_PROVIDER", "anthropic")
        llm = LLMClient(provider=llm_provider)
        llm_result = await llm.generate(messages)

        # ── 6. Build response ─────────────────────────────────────────────────
        sources = [
            SourceChunk(
                page_numbers=chunk["page_numbers"],
                chunk_text=chunk["text"],
                relevance_score=chunk["relevance_score"],
            )
            for chunk in retrieved_chunks
        ]

        logger.info(
            f"Query answered: doc_id={body.doc_id!r}, "
            f"model={llm_result['model']}, "
            f"tokens={llm_result['usage']}"
        )

        return QueryResponse(
            answer=llm_result["answer"],
            sources=sources,
            model=llm_result["model"],
            tokens_used={
                "input": llm_result["usage"]["input_tokens"],
                "output": llm_result["usage"]["output_tokens"],
            },
        )

    except HTTPException:
        raise

    except TimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(exc),
        )

    except EnvironmentError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )

    except Exception as exc:
        logger.exception(f"Unexpected error in query for doc_id={body.doc_id!r}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {exc}",
        )

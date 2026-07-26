"""
Vector Store — services/vector_store.py

Manages ChromaDB in persistent mode.  Each uploaded document gets its own
collection, keyed by a UUID ``doc_id``.

ChromaDB version: 1.x  (uses ``chromadb.PersistentClient``).

Per PRD section 6.4.
"""

import json
import logging
import os

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class VectorStore:
    """Wraps ChromaDB operations for DocuMind."""

    def __init__(self, persist_dir: str = "./data/chroma_db"):
        """
        Initialise ChromaDB client with persistent storage.

        Args:
            persist_dir: Path where ChromaDB writes its data files.
                Created automatically if it doesn't exist.
        """
        os.makedirs(persist_dir, exist_ok=True)
        self._client = chromadb.PersistentClient(path=persist_dir)
        self._persist_dir = persist_dir
        logger.info(f"VectorStore initialised at: {persist_dir}")

    # ── Collection management ─────────────────────────────────────────────────

    def create_collection(self, doc_id: str) -> None:
        """
        Create a new ChromaDB collection for a document.

        Uses cosine distance (best for semantic similarity with normalised
        embedding vectors).  If the collection already exists, it is deleted
        and recreated so that re-uploading the same document is idempotent.

        Args:
            doc_id: UUID4 string used as the collection name.
        """
        # Delete any pre-existing collection with this name (idempotent re-upload)
        try:
            self._client.delete_collection(name=doc_id)
            logger.info(f"Deleted existing collection for doc_id={doc_id}")
        except Exception:
            pass   # Collection didn't exist — that's fine

        self._client.create_collection(
            name=doc_id,
            metadata={"hnsw:space": "cosine"},   # cosine similarity
        )
        logger.info(f"Created collection for doc_id={doc_id}")

    def delete_collection(self, doc_id: str) -> None:
        """
        Delete a document's ChromaDB collection.

        Args:
            doc_id: The document's collection name.

        Raises:
            KeyError: If the collection doesn't exist.
        """
        try:
            self._client.delete_collection(name=doc_id)
            logger.info(f"Deleted collection for doc_id={doc_id}")
        except Exception as exc:
            raise KeyError(f"Collection '{doc_id}' not found.") from exc

    def list_collections(self) -> list[str]:
        """
        List all stored document IDs (collection names).

        Returns:
            List of doc_id strings.
        """
        return [col.name for col in self._client.list_collections()]

    # ── Data operations ───────────────────────────────────────────────────────

    def add_chunks(
        self,
        doc_id: str,
        chunks: list[dict],
        embeddings: list[list[float]],
    ) -> None:
        """
        Store chunks with their embeddings and metadata.

        Each chunk is stored with:
          - ``id``         : ``"{doc_id}_chunk_{chunk_index}"``
          - ``embedding``  : the embedding vector
          - ``document``   : the chunk's plain text (ChromaDB's document field)
          - ``metadata``   : ``{"page_numbers": "[1,2]", "chunk_index": 0, "doc_id": "..."}``

        ``page_numbers`` is JSON-serialised because ChromaDB metadata values
        must be scalar (str / int / float / bool).

        Args:
            doc_id: The document's collection name.
            chunks: Output of ``chunker.chunk_text()`` — list of chunk dicts.
            embeddings: Parallel list of embedding vectors (one per chunk).

        Raises:
            ValueError: If ``chunks`` and ``embeddings`` lengths differ.
        """
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"chunks ({len(chunks)}) and embeddings ({len(embeddings)}) "
                "must have the same length."
            )

        collection = self._client.get_collection(name=doc_id)

        ids = [f"{doc_id}_chunk_{chunk['chunk_index']}" for chunk in chunks]
        documents = [chunk["text"] for chunk in chunks]
        metadatas = [
            {
                "page_numbers": json.dumps(chunk["page_numbers"]),  # "[1, 2]"
                "chunk_index": chunk["chunk_index"],
                "doc_id": doc_id,
                "word_count": chunk.get("word_count", 0),
            }
            for chunk in chunks
        ]

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        logger.info(f"Added {len(chunks)} chunks to collection {doc_id}")

    def query(
        self,
        doc_id: str,
        query_embedding: list[float],
        n_results: int = 5,
    ) -> list[dict]:
        """
        Find the most relevant chunks for a query embedding.

        ChromaDB returns results already sorted by similarity (closest first).
        For cosine distance, distance=0 means identical, distance=2 means
        opposite.  We convert to a 0–1 relevance score:
          ``relevance = 1 - (distance / 2)``

        Args:
            doc_id: The document's collection name.
            query_embedding: Embedding vector of the user's question.
            n_results: How many top chunks to return (default 5).

        Returns:
            List of dicts sorted by relevance (most relevant first)::

                [
                    {
                        "text": "chunk content...",
                        "page_numbers": [7],
                        "chunk_index": 12,
                        "distance": 0.11,
                        "relevance_score": 0.945,
                    },
                    ...
                ]

        Raises:
            KeyError: If ``doc_id`` collection doesn't exist.
        """
        try:
            collection = self._client.get_collection(name=doc_id)
        except Exception as exc:
            raise KeyError(
                f"Document '{doc_id}' not found in vector store. "
                "Please upload the document first."
            ) from exc

        # Clamp n_results to the number of stored items
        count = collection.count()
        n_results = min(n_results, count)
        if n_results == 0:
            return []

        result = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

        # ChromaDB wraps everything in an outer list (one per query embedding)
        docs = result["documents"][0]
        metas = result["metadatas"][0]
        distances = result["distances"][0]

        chunks_out = []
        for doc, meta, dist in zip(docs, metas, distances):
            page_numbers = json.loads(meta["page_numbers"])  # "[1,2]" → [1, 2]
            # Cosine distance in [0, 2] → relevance in [0, 1]
            relevance = max(0.0, 1.0 - dist / 2.0)
            chunks_out.append(
                {
                    "text": doc,
                    "page_numbers": page_numbers,
                    "chunk_index": meta["chunk_index"],
                    "distance": dist,
                    "relevance_score": round(relevance, 4),
                }
            )

        return chunks_out


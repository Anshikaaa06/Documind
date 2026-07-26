"""
Embedder — services/embedder.py

Generates vector embeddings for text using either:
  - OpenAI ``text-embedding-3-small`` (1536 dimensions, API key required)
  - Local ``sentence-transformers/all-MiniLM-L6-v2`` (384 dimensions, free)

Selected via the ``EMBEDDING_PROVIDER`` environment variable.

Per PRD section 6.3.
"""

import os
import time
import logging

logger = logging.getLogger(__name__)

# Batch size limit for OpenAI Embeddings API
_OPENAI_BATCH_SIZE = 100


class Embedder:
    """Wraps embedding providers behind a unified interface."""

    def __init__(self, provider: str = "openai"):
        """
        Initialise the embedder.

        Args:
            provider: ``"openai"`` or ``"local"``.
                - ``"openai"`` uses ``text-embedding-3-small`` (1536 dims).
                  Requires ``OPENAI_API_KEY`` environment variable.
                - ``"local"`` uses ``all-MiniLM-L6-v2`` via sentence-transformers
                  (384 dims). Runs on CPU, no API key needed.

        Raises:
            ValueError: If an unsupported provider is specified.
            ImportError: If the required package for the chosen provider is
                not installed.
            EnvironmentError: If ``"openai"`` is selected but ``OPENAI_API_KEY``
                is missing.
        """
        self.provider = provider.lower()

        if self.provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise EnvironmentError(
                    "OPENAI_API_KEY environment variable is not set. "
                    "Set it in your .env file or switch EMBEDDING_PROVIDER=local."
                )
            try:
                import openai as _openai
            except ImportError:
                raise ImportError(
                    "The 'openai' package is required for OpenAI embeddings. "
                    "Run: pip install openai>=1.30.0"
                )
            self._openai_client = _openai.OpenAI(api_key=api_key)
            self._model_name = "text-embedding-3-small"
            self.dimensions = 1536
            logger.info("Embedder initialised: OpenAI text-embedding-3-small (1536 dims)")

        elif self.provider == "local":
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError:
                raise ImportError(
                    "The 'sentence-transformers' package is required for local embeddings. "
                    "Run: pip install sentence-transformers>=2.7.0"
                )
            logger.info("Loading local model all-MiniLM-L6-v2 (first run downloads ~90 MB)...")
            self._local_model = SentenceTransformer("all-MiniLM-L6-v2")
            self._model_name = "all-MiniLM-L6-v2"
            self.dimensions = 384
            logger.info("Embedder initialised: all-MiniLM-L6-v2 (384 dims, CPU)")

        else:
            raise ValueError(
                f"Unknown embedding provider: {provider!r}. "
                "Use 'openai' or 'local'."
            )

    # ── Public API ────────────────────────────────────────────────────────────

    def embed_text(self, text: str) -> list[float]:
        """
        Embed a single piece of text.

        Args:
            text: The text to embed. Should be non-empty.

        Returns:
            A list of floats representing the embedding vector.
            Length is 1536 for OpenAI, 384 for local.
        """
        if not text or not text.strip():
            raise ValueError("Cannot embed empty text.")

        if self.provider == "openai":
            return self._embed_openai_batch([text])[0]
        else:
            return self._local_model.encode(text, convert_to_numpy=True).tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Embed multiple texts efficiently.

        For OpenAI: sends texts in batches of 100 (API limit), with
        exponential-backoff retry on rate-limit errors (HTTP 429).
        For local model: encodes all texts in one pass using sentence-transformers.

        Args:
            texts: List of non-empty strings to embed.

        Returns:
            List of embedding vectors in the same order as ``texts``.
        """
        if not texts:
            return []

        if self.provider == "openai":
            return self._embed_openai_batch(texts)
        else:
            # sentence-transformers handles batching internally
            embeddings = self._local_model.encode(
                texts,
                batch_size=64,
                convert_to_numpy=True,
                show_progress_bar=len(texts) > 10,
            )
            return [vec.tolist() for vec in embeddings]

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _embed_openai_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Call OpenAI Embeddings API in batches of 100, with exponential-backoff
        retry on rate-limit (HTTP 429) errors.

        Max 3 retries per batch: waits 1 s → 2 s → 4 s before giving up.
        """
        import openai as _openai

        all_embeddings: list[list[float]] = []

        for batch_start in range(0, len(texts), _OPENAI_BATCH_SIZE):
            batch = texts[batch_start : batch_start + _OPENAI_BATCH_SIZE]

            for attempt in range(3):
                try:
                    response = self._openai_client.embeddings.create(
                        input=batch,
                        model=self._model_name,
                    )
                    # Results are returned in the same order as input
                    batch_embeddings = [item.embedding for item in response.data]
                    all_embeddings.extend(batch_embeddings)
                    break   # success — move to next batch

                except _openai.RateLimitError:
                    if attempt == 2:
                        raise   # give up after 3 attempts
                    wait_seconds = 2 ** attempt   # 1 s, 2 s, 4 s
                    logger.warning(
                        f"OpenAI rate limit hit (batch {batch_start // _OPENAI_BATCH_SIZE}), "
                        f"retrying in {wait_seconds}s (attempt {attempt + 1}/3)..."
                    )
                    time.sleep(wait_seconds)

                except _openai.AuthenticationError as exc:
                    raise EnvironmentError(
                        "OpenAI API key is invalid or expired. "
                        "Check OPENAI_API_KEY in your .env file."
                    ) from exc

        return all_embeddings


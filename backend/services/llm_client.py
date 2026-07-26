"""
LLM Client — services/llm_client.py

Sends the constructed prompt to the LLM API (Anthropic Claude or OpenAI
GPT-4o-mini) and returns a structured response.

Selected via the ``LLM_PROVIDER`` environment variable.

Key features (per PRD section 6.6):
  - Retry with exponential backoff: 1 s → 2 s → 4 s, max 3 retries
  - 30-second per-request timeout
  - Structured return: { answer, model, usage }

Per PRD section 6.6.
"""

import asyncio
import logging
import os

logger = logging.getLogger(__name__)

# Per-request timeout (seconds)
_TIMEOUT_SECONDS = 30

# Max retries on rate-limit errors
_MAX_RETRIES = 3


class LLMClient:
    """Unified interface for LLM API calls."""

    def __init__(self, provider: str = "anthropic"):
        """
        Initialise with either ``"anthropic"`` or ``"openai"`` provider.

        Args:
            provider: ``"anthropic"`` uses ``claude-sonnet-4-6``.
                      ``"openai"`` uses ``gpt-4o-mini``.

        Raises:
            EnvironmentError: If the required API key env var is missing.
            ValueError: If an unsupported provider is specified.
        """
        self.provider = provider.lower()

        if self.provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise EnvironmentError(
                    "ANTHROPIC_API_KEY is not set. Add it to your .env file."
                )
            import anthropic as _anthropic
            self._client = _anthropic.AsyncAnthropic(api_key=api_key)
            self._model = "claude-sonnet-4-6"
            logger.info("LLMClient initialised: Anthropic claude-sonnet-4-6")

        elif self.provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise EnvironmentError(
                    "OPENAI_API_KEY is not set. Add it to your .env file."
                )
            import openai as _openai
            self._client = _openai.AsyncOpenAI(api_key=api_key)
            self._model = "gpt-4o-mini"
            logger.info("LLMClient initialised: OpenAI gpt-4o-mini")

        elif self.provider == "groq":
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise EnvironmentError(
                    "GROQ_API_KEY is not set. Add it to your .env file."
                )
            import openai as _openai   # Groq is OpenAI-API-compatible
            self._client = _openai.AsyncOpenAI(
                api_key=api_key,
                base_url="https://api.groq.com/openai/v1",
            )
            self._model = "llama-3.3-70b-versatile"
            # Route through the OpenAI code path
            self.provider = "openai"
            logger.info("LLMClient initialised: Groq llama-3.3-70b-versatile")

        else:
            raise ValueError(
                f"Unknown LLM provider: {provider!r}. Use 'anthropic', 'openai', or 'groq'."
            )

    # ── Public API ────────────────────────────────────────────────────────────

    async def generate(self, messages: list[dict]) -> dict:
        """
        Send messages to the LLM and return a structured response.

        Implements:
          - 30-second per-request timeout
          - Retry with exponential backoff on rate-limit errors:
              attempt 1: wait 1 s
              attempt 2: wait 2 s
              attempt 3: give up and re-raise

        Args:
            messages: List of ``{"role": str, "content": str}`` dicts,
                as returned by ``prompt_builder.build_prompt()``.
                The first message may have role ``"system"``.

        Returns:
            Dict::

                {
                    "answer": "The full LLM response text...",
                    "model": "claude-sonnet-4-6",
                    "usage": {
                        "input_tokens": 2847,
                        "output_tokens": 512,
                    },
                }

        Raises:
            TimeoutError: If the LLM API doesn't respond within 30 seconds.
            EnvironmentError: If the API key is invalid/expired.
            RuntimeError: If the API returns an error after all retries.
        """
        if self.provider == "anthropic":
            return await self._generate_anthropic(messages)
        else:
            return await self._generate_openai(messages)

    # ── Provider implementations ──────────────────────────────────────────────

    async def _generate_anthropic(self, messages: list[dict]) -> dict:
        """
        Call Anthropic Messages API.

        Anthropic's API takes the system prompt in a separate ``system``
        parameter (not inside the messages array), so we extract it here.
        """
        import anthropic as _anthropic

        # Split system message from user/assistant turns
        system_content = None
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                user_messages.append(msg)

        for attempt in range(_MAX_RETRIES):
            try:
                response = await asyncio.wait_for(
                    self._client.messages.create(
                        model=self._model,
                        max_tokens=1024,
                        system=system_content,
                        messages=user_messages,
                    ),
                    timeout=_TIMEOUT_SECONDS,
                )
                return {
                    "answer": response.content[0].text,
                    "model": self._model,
                    "usage": {
                        "input_tokens": response.usage.input_tokens,
                        "output_tokens": response.usage.output_tokens,
                    },
                }

            except asyncio.TimeoutError:
                raise TimeoutError(
                    f"Anthropic API did not respond within {_TIMEOUT_SECONDS} seconds."
                )

            except _anthropic.RateLimitError:
                if attempt == _MAX_RETRIES - 1:
                    raise RuntimeError(
                        "Anthropic API rate limit exceeded after 3 retries. "
                        "Please wait a moment and try again."
                    )
                wait = 2 ** attempt   # 1 s, 2 s
                logger.warning(
                    f"Anthropic rate limit hit — retrying in {wait}s "
                    f"(attempt {attempt + 1}/{_MAX_RETRIES})"
                )
                await asyncio.sleep(wait)

            except _anthropic.AuthenticationError as exc:
                raise EnvironmentError(
                    "Anthropic API key is invalid or expired. "
                    "Check ANTHROPIC_API_KEY in your .env file."
                ) from exc

            except _anthropic.APIError as exc:
                if attempt == _MAX_RETRIES - 1:
                    raise RuntimeError(f"Anthropic API error: {exc}") from exc
                wait = 2 ** attempt
                logger.warning(f"Anthropic API error, retrying in {wait}s: {exc}")
                await asyncio.sleep(wait)

    async def _generate_openai(self, messages: list[dict]) -> dict:
        """Call OpenAI Chat Completions API."""
        import openai as _openai

        for attempt in range(_MAX_RETRIES):
            try:
                response = await asyncio.wait_for(
                    self._client.chat.completions.create(
                        model=self._model,
                        messages=messages,
                        max_tokens=1024,
                    ),
                    timeout=_TIMEOUT_SECONDS,
                )
                return {
                    "answer": response.choices[0].message.content,
                    "model": self._model,
                    "usage": {
                        "input_tokens": response.usage.prompt_tokens,
                        "output_tokens": response.usage.completion_tokens,
                    },
                }

            except asyncio.TimeoutError:
                raise TimeoutError(
                    f"OpenAI API did not respond within {_TIMEOUT_SECONDS} seconds."
                )

            except _openai.RateLimitError:
                if attempt == _MAX_RETRIES - 1:
                    raise RuntimeError(
                        "OpenAI API rate limit exceeded after 3 retries."
                    )
                wait = 2 ** attempt
                logger.warning(
                    f"OpenAI rate limit hit — retrying in {wait}s "
                    f"(attempt {attempt + 1}/{_MAX_RETRIES})"
                )
                await asyncio.sleep(wait)

            except _openai.AuthenticationError as exc:
                raise EnvironmentError(
                    "OpenAI API key is invalid or expired. "
                    "Check OPENAI_API_KEY in your .env file."
                ) from exc

            except _openai.APIError as exc:
                if attempt == _MAX_RETRIES - 1:
                    raise RuntimeError(f"OpenAI API error: {exc}") from exc
                wait = 2 ** attempt
                logger.warning(f"OpenAI API error, retrying in {wait}s: {exc}")
                await asyncio.sleep(wait)


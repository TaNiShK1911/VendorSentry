"""
LLM client -- thin wrapper around the Anthropic API with Groq fallback.

Handles:
- Retries with exponential backoff (network errors, rate limits)
- Fallback from Anthropic to Groq when primary key is missing
- Response validation (ensures we got back valid JSON before returning)
- Logging of token usage for cost monitoring

ARCHITECTURAL RULE: This client only sends/receives text.
It has NO knowledge of VendorScore, tier, or composite_score.
Those concepts must never appear in prompts built by this module.

Groq note: Groq is OpenAI-API-compatible (https://api.groq.com/openai/v1).
Default fallback model: llama-3.3-70b-versatile (fast, high context, free tier).
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

import anthropic
from openai import OpenAI  # Groq uses the OpenAI-compatible API

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Retry configuration
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 1.0   # seconds; doubles on each retry


class LLMClient:
    """
    Unified LLM client. Uses Anthropic by default; falls back to Groq.

    Priority:
        1. Anthropic (LLM_API_KEY) -- highest quality
        2. Groq (GROQ_API_KEY)     -- fast, free tier, OpenAI-compatible

    Usage:
        client = LLMClient()
        raw_json = client.complete(system_prompt, user_prompt)
        parsed = json.loads(raw_json)
    """

    def __init__(self) -> None:
        self._anthropic: anthropic.Anthropic | None = None
        self._groq: OpenAI | None = None

        if settings.llm_api_key:
            self._anthropic = anthropic.Anthropic(api_key=settings.llm_api_key)
            logger.info("LLM client initialised with Anthropic API")
        elif settings.groq_api_key:
            self._groq = OpenAI(
                api_key=settings.groq_api_key,
                base_url="https://api.groq.com/openai/v1",
            )
            logger.info(
                "LLM client initialised with Groq fallback (model: %s)",
                settings.groq_model,
            )
        else:
            logger.warning(
                "No LLM API key configured. Extraction will return empty results. "
                "Set LLM_API_KEY (Anthropic) or GROQ_API_KEY in .env."
            )

    # -- Public API -----------------------------------------------------------

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """
        Send a completion request and return the raw response text.

        Retries on transient errors. Raises RuntimeError if all retries fail.

        Args:
            system_prompt: The system instructions (rules, output schema).
            user_prompt:   The document-specific user turn.

        Returns:
            Raw string response from the LLM (should be JSON per our prompts).
        """
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                if self._anthropic:
                    return self._call_anthropic(system_prompt, user_prompt)
                elif self._groq:
                    return self._call_groq(system_prompt, user_prompt)
                else:
                    # No API key -- return an empty extraction result
                    return self._empty_extraction_json()
            except Exception as exc:
                if attempt == _MAX_RETRIES:
                    logger.error(
                        "LLM call failed after %d attempts: %s", _MAX_RETRIES, exc
                    )
                    raise RuntimeError(f"LLM call failed: {exc}") from exc
                delay = _RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(
                    "LLM attempt %d/%d failed (%s). Retrying in %.1fs...",
                    attempt, _MAX_RETRIES, exc, delay,
                )
                time.sleep(delay)

        raise RuntimeError("LLM client: unreachable")  # pragma: no cover

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """
        Like complete() but parses and returns the JSON dict.

        Raises:
            json.JSONDecodeError: if the LLM returned non-JSON.
        """
        raw = self.complete(system_prompt, user_prompt)
        # Strip markdown fences if the LLM adds them despite instructions
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1]
            if raw.endswith("```"):
                raw = raw[: raw.rfind("```")]
        return json.loads(raw)

    # -- Private helpers ------------------------------------------------------

    def _call_anthropic(self, system_prompt: str, user_prompt: str) -> str:
        assert self._anthropic is not None
        response = self._anthropic.messages.create(
            model=settings.llm_model,
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = response.content[0].text
        logger.debug(
            "Anthropic usage -- input: %d tokens, output: %d tokens",
            response.usage.input_tokens,
            response.usage.output_tokens,
        )
        return text

    def _call_groq(self, system_prompt: str, user_prompt: str) -> str:
        """
        Call the Groq API using the OpenAI-compatible endpoint.

        Groq supports: llama-3.3-70b-versatile, llama-3.1-8b-instant,
        mixtral-8x7b-32768, gemma2-9b-it, and more.
        Configure via GROQ_MODEL in .env.
        """
        assert self._groq is not None
        response = self._groq.chat.completions.create(
            model=settings.groq_model,
            max_tokens=2048,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,   # Low temperature for structured JSON extraction
        )
        content = response.choices[0].message.content or ""
        logger.debug(
            "Groq usage -- model: %s, tokens: %s",
            settings.groq_model,
            getattr(response.usage, "total_tokens", "unknown"),
        )
        return content

    @staticmethod
    def _empty_extraction_json() -> str:
        """Return a valid empty extraction result when no API key is configured."""
        return json.dumps({
            "data_access": {"pii": None, "financial": None, "systems": []},
            "compliance_claims": [],
            "sla_terms": {"uptime_pct": None, "breach_notification_hours": None, "other": {}},
            "conflicts": [],
        })


# Module-level singleton for convenience
_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Return the module-level LLMClient singleton."""
    global _client
    if _client is None:
        _client = LLMClient()
    return _client

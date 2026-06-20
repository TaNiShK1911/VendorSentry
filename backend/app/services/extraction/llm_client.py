"""
LLM client — thin wrapper around the Anthropic API with OpenRouter fallback.

Handles:
- Retries with exponential backoff (network errors, rate limits)
- Fallback from Anthropic to OpenRouter when primary key is missing
- Response validation (ensures we got back valid JSON before returning)
- Logging of token usage for cost monitoring

ARCHITECTURAL RULE: This client only sends/receives text.
It has NO knowledge of VendorScore, tier, or composite_score.
Those concepts must never appear in prompts built by this module.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

import anthropic
from openai import OpenAI  # OpenRouter uses the OpenAI-compatible API

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Retry configuration
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 1.0   # seconds; doubles on each retry


class LLMClient:
    """
    Unified LLM client. Uses Anthropic by default; falls back to OpenRouter.

    Usage:
        client = LLMClient()
        raw_json = client.complete(system_prompt, user_prompt)
        parsed = json.loads(raw_json)
    """

    def __init__(self) -> None:
        self._anthropic: anthropic.Anthropic | None = None
        self._openrouter: OpenAI | None = None

        if settings.llm_api_key:
            self._anthropic = anthropic.Anthropic(api_key=settings.llm_api_key)
            logger.info("LLM client initialised with Anthropic API")
        elif settings.openrouter_api_key:
            self._openrouter = OpenAI(
                api_key=settings.openrouter_api_key,
                base_url="https://openrouter.ai/api/v1",
            )
            logger.info("LLM client initialised with OpenRouter fallback")
        else:
            logger.warning(
                "No LLM API key configured. Extraction will return empty results. "
                "Set LLM_API_KEY or OPENROUTER_API_KEY in .env."
            )

    # ── Public API ───────────────────────────────────────────────────────────

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
                elif self._openrouter:
                    return self._call_openrouter(system_prompt, user_prompt)
                else:
                    # No API key — return an empty extraction result
                    return self._empty_extraction_json()
            except Exception as exc:
                if attempt == _MAX_RETRIES:
                    logger.error(
                        "LLM call failed after %d attempts: %s", _MAX_RETRIES, exc
                    )
                    raise RuntimeError(f"LLM call failed: {exc}") from exc
                delay = _RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(
                    "LLM attempt %d/%d failed (%s). Retrying in %.1fs…",
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

    # ── Private helpers ──────────────────────────────────────────────────────

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
            "Anthropic usage — input: %d tokens, output: %d tokens",
            response.usage.input_tokens,
            response.usage.output_tokens,
        )
        return text

    def _call_openrouter(self, system_prompt: str, user_prompt: str) -> str:
        assert self._openrouter is not None
        response = self._openrouter.chat.completions.create(
            model="anthropic/claude-3.5-sonnet",  # OpenRouter model name
            max_tokens=2048,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or ""

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

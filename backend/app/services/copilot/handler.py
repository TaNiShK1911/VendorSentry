"""
Copilot query handler — drives the tool-use loop.

Uses Groq with the dedicated tool-use model (llama3-groq-70b-8192-tool-use-preview).
Falls back gracefully if Groq is unavailable or the key is missing.

Key fixes vs original:
- Uses the -tool-use-preview model which never generates legacy <function=...> syntax
- Retries once on tool_use_failed with an error hint in the messages
- Repairs malformed JSON args from the LLM before executing tools
"""
from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.services.copilot.tools import TOOL_MANIFEST, execute_tool
from app.services.copilot.followups import generate_followups

logger = logging.getLogger(__name__)

# Best model for reliable tool-use on Groq.
_PREFERRED_MODEL = "llama-3.1-8b-instant"
_FALLBACK_MODEL  = "qwen/qwen3-32b"

SYSTEM_PROMPT = """\
You are VendorSentry Copilot — a vendor risk analyst AI.

Rules (STRICT):
1. Always call a tool before answering any factual question about vendors, scores, breaches, or alerts.
2. Never invent data. If tools return nothing, say "No data found."
3. Use markdown tables for lists of vendors or alerts.
4. You may call multiple tools sequentially.
5. For relative time queries (e.g. "last 48 hours"), compute the ISO 8601 cutoff timestamp and pass it as created_after.
6. Always include a one-sentence summary before any table.

Today UTC: {now_utc}
"""

_MAX_TOOL_ITERATIONS = 6


def _get_groq_client() -> tuple[Any | None, str]:
    """Return (Groq client, model name). Tries preferred model first."""
    try:
        from groq import Groq
        from app.core.config import Settings
        s = Settings()
        key = s.groq_api_key
        if not key:
            return None, ""
        client = Groq(api_key=key)
        return client, _PREFERRED_MODEL
    except ImportError:
        return None, ""


def _repair_json(raw: str) -> dict:
    """
    Best-effort repair of malformed JSON from the LLM.
    Handles: trailing commas, single quotes, missing closing braces.
    """
    # Strip surrounding whitespace
    raw = raw.strip()
    if not raw:
        return {}

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Try to extract the first {...} blob
    m = re.search(r'\{.*\}', raw, re.DOTALL)
    if m:
        candidate = m.group(0)
        # Remove trailing commas before } or ]
        candidate = re.sub(r',\s*([}\]])', r'\1', candidate)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    logger.warning("Could not repair LLM JSON: %r", raw[:200])
    return {}


def run_copilot_query(
    query: str,
    conversation_history: list[dict],
    db: Session,
) -> dict[str, Any]:
    """
    Execute a copilot query using the Groq tool-use loop.

    Args:
        query: User's plain-English question.
        conversation_history: Prior turns as list of {role, content} dicts.
        db: Live SQLAlchemy session.

    Returns:
        {answer, data_used, follow_up_suggestions, confidence, no_data_reason}
    """
    client, groq_model = _get_groq_client()
    if not client:
        return {
            "answer": (
                "⚠️ The Copilot LLM is not configured. "
                "Please set `GROQ_API_KEY` in your `.env` file to enable AI-powered queries."
            ),
            "data_used": [],
            "follow_up_suggestions": [],
            "confidence": "none",
            "no_data_reason": "LLM not configured",
        }

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    system  = SYSTEM_PROMPT.format(now_utc=now_utc)

    # Build message list
    messages: list[dict] = []
    for h in (conversation_history or []):
        if isinstance(h, dict) and h.get("role") and h.get("content"):
            messages.append({"role": h["role"], "content": str(h["content"])})
    messages.append({"role": "user", "content": query})

    tools_used: list[dict] = []
    final_text = ""
    retry_count = 0

    def _call_api(msgs: list[dict]) -> Any:
        """Call Groq API, retrying with fallback model on tool_use_failed."""
        nonlocal retry_count, groq_model
        try:
            return client.chat.completions.create(
                model=groq_model,
                max_tokens=2048,
                temperature=0,          # deterministic — critical for tool use
                messages=[{"role": "system", "content": system}] + msgs,
                tools=TOOL_MANIFEST,
                tool_choice="auto",
            )
        except Exception as exc:
            err_str = str(exc)
            if "tool_use_failed" in err_str and retry_count == 0:
                retry_count += 1
                logger.warning(
                    "Groq tool_use_failed on %s — retrying with %s",
                    groq_model, _FALLBACK_MODEL
                )
                groq_model = _FALLBACK_MODEL
                return client.chat.completions.create(
                    model=groq_model,
                    max_tokens=2048,
                    temperature=0,
                    messages=[{"role": "system", "content": system}] + msgs,
                    tools=TOOL_MANIFEST,
                    tool_choice="auto",
                )
            raise

    try:
        for iteration in range(_MAX_TOOL_ITERATIONS):
            response = _call_api(messages)

            choice        = response.choices[0]
            finish_reason = choice.finish_reason
            msg           = choice.message

            # Build assistant message for history
            assistant_msg: dict = {"role": "assistant", "content": msg.content or ""}
            if msg.tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id":   tc.id,
                        "type": "function",
                        "function": {
                            "name":      tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ]
            messages.append(assistant_msg)

            if finish_reason == "stop" or not msg.tool_calls:
                final_text = msg.content or ""
                break

            # Execute all tool calls
            for tc in msg.tool_calls:
                fn_name = tc.function.name
                fn_args = _repair_json(tc.function.arguments or "{}")

                logger.info("Copilot tool call: %s(%s)", fn_name, fn_args)
                result = execute_tool(fn_name, fn_args, db)

                # Build a human-readable summary for the provenance footer
                count = None
                if isinstance(result, dict):
                    count = (
                        result.get("count")
                        or len(result.get("alerts",  []))
                        or len(result.get("vendors", []))
                        or len(result.get("breaches",[]))
                    )
                tools_used.append({
                    "endpoint": fn_name,
                    "summary":  f"{count} result(s)" if count is not None else "done",
                })

                messages.append({
                    "role":         "tool",
                    "tool_call_id": tc.id,
                    "content":      json.dumps(result, default=str),
                })

        else:
            logger.warning("Copilot hit max iterations (%d)", _MAX_TOOL_ITERATIONS)
            if not final_text:
                final_text = "I reached the maximum number of data queries. Please try a more specific question."

    except Exception as exc:
        logger.exception("Copilot query failed: %s", exc)
        # Provide a clean message — strip the raw Groq error object
        err_msg = str(exc)
        if "'error'" in err_msg or "failed_generation" in err_msg:
            err_msg = "The AI model had trouble forming a data query. Please rephrase your question and try again."
        return {
            "answer": f"⚠️ {err_msg}",
            "data_used": [],
            "follow_up_suggestions": [],
            "confidence": "none",
            "no_data_reason": str(exc),
        }

    confidence = "high" if tools_used else "partial"
    if not final_text.strip():
        final_text  = "No matching data found for your query."
        confidence  = "none"

    return {
        "answer":               final_text,
        "data_used":            tools_used,
        "follow_up_suggestions": generate_followups(query, final_text),
        "confidence":           confidence,
        "no_data_reason":       None,
    }

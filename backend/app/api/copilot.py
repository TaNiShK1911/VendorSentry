"""
Copilot API endpoint — POST /api/v1/copilot/query
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.services.copilot.handler import run_copilot_query

router = APIRouter()
_security = HTTPBearer()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class ConversationTurn(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class CopilotQueryRequest(BaseModel):
    query: str
    conversation_history: list[ConversationTurn] = []


class DataSource(BaseModel):
    endpoint: str
    summary: str


class CopilotQueryResponse(BaseModel):
    answer: str
    data_used: list[DataSource]
    follow_up_suggestions: list[str]
    confidence: str  # "high" | "partial" | "none"
    no_data_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------

def _require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(_security),
) -> dict:
    """Verify JWT and return payload."""
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return payload


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("/copilot/query", response_model=CopilotQueryResponse)
def copilot_query(
    body: CopilotQueryRequest,
    db: Session = Depends(get_db),
    _user: dict = Depends(_require_auth),
) -> Any:
    """
    Natural-language query over live vendor risk data.

    Every factual answer is grounded in real DB data retrieved through
    tool calls — never from LLM parametric memory.
    """
    history = [{"role": t.role, "content": t.content} for t in body.conversation_history]
    result = run_copilot_query(body.query, history, db)
    return result

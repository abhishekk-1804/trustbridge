from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
import re

from backend.ai_copilot import (
    ContextBuilder,
    build_messages,
    call_llm,
    settings,
)
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import get_session_direct
from database.models import User

router = APIRouter()


# Patterns to detect potential prompt injection attempts
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(previous|above|prior)\s+instructions",
    r"forget\s+(everything|all|previous)",
    r"you\s+are\s+now\s+a\s+",
    r"system\s+prompt",
    r"override\s+the\s+system",
    r"pretend\s+to\s+be",
    r"roleplay\s+as",
    r"act\s+as\s+if",
    r"disregard\s+the\s+above",
    r"new\s+instructions\s*:",
    r"<\s*system\s*>",
    r"<\s*user\s*>",
    r"<\s*assistant\s*>",
]


def sanitize_query(query: str) -> str:
    """Sanitize user query to prevent prompt injection."""
    # Check for potential injection patterns
    query_lower = query.lower()
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, query_lower):
            raise HTTPException(
                status_code=400,
                detail="Query contains disallowed patterns"
            )
    return query


class CopilotRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="User's question for the AI Copilot")
    user_id: Optional[int] = Field(None, description="Optional user ID for context", ge=1)
    transaction_id: Optional[int] = Field(None, description="Optional transaction ID for context", ge=1)
    payment_id: Optional[int] = Field(None, description="Optional payment ID for context", ge=1)
    conversation_history: Optional[List[Dict[str, str]]] = Field(
        None, description="Previous conversation turns (max 5)", max_length=5
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        return sanitize_query(v)


class CopilotResponse(BaseModel):
    response: str
    intent: str
    context_used: Dict[str, Any]
    ai_available: bool


def get_db():
    db = get_session_direct()
    try:
        yield db
    finally:
        db.close()


@router.post("/copilot/ask", response_model=CopilotResponse)
async def ask_copilot(
    request: CopilotRequest,
    db: Session = Depends(get_db)
):
    """
    Ask the TrustBridge AI Risk Analyst Copilot a question.

    The Copilot uses REAL TrustBridge data to answer questions about:
    - Trust Scores and components
    - Fraud rule flags and reasons
    - ML anomaly detection results and contributing indicators
    - Payment risk assessments and decisions
    - Double-entry ledger entries
    - Model evaluation metrics
    - Rule vs ML comparison

    Example queries:
    - "Why was transaction 121 flagged?"
    - "Why is Raj's Trust Score 76.4?"
    - "What indicators contributed to this anomaly?"
    - "Summarize this user's recent behaviour."
    - "Why did this payment receive HIGH risk?"
    - "Explain the difference between Trust Score and Fraud Risk."
    """
    # Validate user exists if provided
    if request.user_id:
        user = db.query(User).filter(User.id == request.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

    # Build structured context
    builder = ContextBuilder(db)
    context = builder.build_context(
        query=request.query,
        user_id=request.user_id,
        transaction_id=request.transaction_id,
        payment_id=request.payment_id,
    )

    # Build messages for LLM
    messages = build_messages(context)

    # Add conversation history if provided (limited to last 5 turns)
    if request.conversation_history:
        # Insert history before the current user message
        history_messages = []
        for turn in request.conversation_history[-5:]:
            if "user" in turn:
                history_messages.append({"role": "user", "content": turn["user"]})
            if "assistant" in turn:
                history_messages.append({"role": "assistant", "content": turn["assistant"]})
        # Insert after system prompt
        messages = [messages[0]] + history_messages + messages[1:]

    # Call LLM
    response_text = await call_llm(messages)

    return CopilotResponse(
        response=response_text,
        intent=context.intent,
        context_used=context.to_dict(),
        ai_available=settings.ai_configured,
    )


@router.get("/copilot/status")
async def copilot_status():
    """Get AI Copilot availability status."""
    return {
        "available": settings.ai_configured,
        "provider": settings.ai_provider if settings.ai_configured else None,
        "model": settings.ai_model if settings.ai_configured else None,
        "message": "AI Copilot ready" if settings.ai_configured else "Configure AI_API_KEY in .env to enable",
    }


@router.get("/copilot/examples")
async def copilot_examples():
    """Get example queries for the AI Copilot."""
    return {
        "examples": [
            "Why was transaction 121 flagged?",
            "Why is Raj's Trust Score 76.4?",
            "What indicators contributed to this anomaly?",
            "Summarize this user's recent behaviour.",
            "Why did this payment receive HIGH risk?",
            "Explain the difference between Trust Score and Fraud Risk.",
            "Show me the recent suspicious activity.",
            "What is the model's precision and recall?",
            "Which transactions were flagged by both rules and ML?",
            "Explain the ledger entries for payment TB2024...",
        ],
        "note": "Provide user_id, transaction_id, or payment_id for specific context."
    }
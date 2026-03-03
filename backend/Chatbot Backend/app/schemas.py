"""Pydantic request/response schemas for the chat API."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Incoming chat message."""

    message: str = Field(..., min_length=1)
    session_id: str | None = Field(None, description="Reserved for future conversation state")


class ChatResponse(BaseModel):
    """Outgoing chatbot response."""

    response: str
    matched: bool = Field(True, description="Whether a DB entry matched the input")
    source: str = Field("database", description="Response source: 'database' or 'fallback'")

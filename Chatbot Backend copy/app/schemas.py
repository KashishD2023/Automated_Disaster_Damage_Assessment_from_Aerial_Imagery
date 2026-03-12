"""Pydantic request/response schemas for the chat API."""

from datetime import datetime

from pydantic import BaseModel, Field, EmailStr


class ChatRequest(BaseModel):
    """Incoming chat message."""

    message: str = Field(..., min_length=1)
    session_id: str | None = Field(None, description="Reserved for future conversation state")


class ChatResponse(BaseModel):
    """Outgoing chatbot response."""

    response: str
    matched: bool = Field(True, description="Whether a DB entry matched the input")
    source: str = Field("database", description="Response source: 'database' or 'fallback'")


class ResponseItem(BaseModel):
    """Single trigger/response entry for GET endpoints."""

    id: int
    trigger: str
    response: str
    created_at: datetime

    class Config:
        from_attributes = True


class TileDetail(BaseModel):
    """Tile entry from tile_demo.csv: details and image paths."""

    tile_id: int
    pre_disaster_path: str
    post_disaster_path: str


# User Authentication Schemas
class UserRegister(BaseModel):
    """User registration request."""

    username: str = Field(..., min_length=3, max_length=80)
    email: EmailStr
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    """User login request."""

    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class UserResponse(BaseModel):
    """User response (without password)."""

    id: int
    username: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Authentication token response."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# User History Schemas
class UserHistoryCreate(BaseModel):
    """Create a user history record."""

    tile_id: str = Field(..., min_length=1)
    view_mode: str = Field(..., pattern="^(pre|post)$")


class UserHistoryResponse(BaseModel):
    """User history response."""

    id: int
    user_id: int
    tile_id: str
    view_mode: str
    analyzed_at: datetime

    class Config:
        from_attributes = True

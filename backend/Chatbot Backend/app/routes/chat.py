"""Chat API route: POST /chat."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ChatRequest, ChatResponse
from app.services.chat_service import process_message

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    """Accept a message, process it against the test DB, return the response."""
    response_text, matched, source = process_message(db, request.message)
    return ChatResponse(response=response_text, matched=matched, source=source)

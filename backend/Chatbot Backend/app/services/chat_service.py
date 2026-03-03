"""Chat service: read input, query DB, return response."""

from sqlalchemy.orm import Session

from app.models import Response

DEFAULT_RESPONSE = "I don't have an answer for that in the test DB."


def process_message(db: Session, message: str) -> tuple[str, bool, str]:
    """
    Normalize message, look up in DB by trigger (exact match on normalized text).
    Returns (response_text, matched, source).
    """
    normalized = message.strip().lower() or ""
    if not normalized:
        return DEFAULT_RESPONSE, False, "fallback"

    row = (
        db.query(Response)
        .filter(Response.trigger == normalized)
        .limit(1)
        .first()
    )
    if row:
        return row.response, True, "database"
    # Optional: try LIKE match on message containing trigger (e.g. "say hello" -> hello)
    row = (
        db.query(Response)
        .filter(Response.trigger.in_(normalized.split()))
        .limit(1)
        .first()
    )
    if row:
        return row.response, True, "database"
    return DEFAULT_RESPONSE, False, "fallback"

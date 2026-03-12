"""Chat API routes: POST /chat, GET /responses, GET /tiles."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Response
from app.schemas import ChatRequest, ChatResponse, ResponseItem, TileDetail
from app.services.chat_service import process_message
from app.services.tile_service import get_tile_by_id, load_tiles

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    """Accept a message, process it against the test DB, return the response."""
    response_text, matched, source = process_message(db, request.message)
    return ChatResponse(response=response_text, matched=matched, source=source)


@router.get("/predictions", response_model=list[ResponseItem])
def list_responses(db: Session = Depends(get_db)) -> list[ResponseItem]:
    """List all trigger/response pairs in the test DB."""
    rows = db.query(Response).order_by(Response.trigger).all()
    return [ResponseItem.model_validate(r) for r in rows]


@router.get("/responses/{trigger}", response_model=ResponseItem)
def get_response_by_trigger(trigger: str, db: Session = Depends(get_db)) -> ResponseItem:
    """Get a single response by trigger (case-insensitive)."""
    row = db.query(Response).filter(Response.trigger == trigger.lower().strip()).first()
    if not row:
        raise HTTPException(status_code=404, detail="Trigger not found")
    return ResponseItem.model_validate(row)


@router.get("/tiles", response_model=list[TileDetail])
def list_tiles() -> list[TileDetail]:
    """List all tiles (details and image paths) from tiles_demo.csv."""
    return load_tiles()


@router.get("/tiles/{tile_id}", response_model=TileDetail)
def get_tile(tile_id: int) -> TileDetail:
    """Get a single tile by id from tiles_demo.csv."""
    tile = get_tile_by_id(tile_id)
    if not tile:
        raise HTTPException(status_code=404, detail="Tile not found")
    return tile

"""FastAPI app entrypoint: router registration and DB init on startup."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import init_db
from app.routes import chat

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables and seed test data on startup."""
    init_db()
    yield
    # Shutdown: nothing to close for SQLite in this skeleton


app = FastAPI(title="Chatbot Backend", lifespan=lifespan)
app.include_router(chat.router, tags=["chat"])


@app.get("/health")
def health() -> dict[str, str]:
    """Health check."""
    return {"status": "ok"}

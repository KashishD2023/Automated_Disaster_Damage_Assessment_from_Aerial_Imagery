"""FastAPI app entrypoint: router registration and DB init on startup."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routes import chat, auth

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables and seed test data on startup."""
    init_db()
    yield
    # Shutdown: nothing to close for SQLite in this skeleton


app = FastAPI(title="Chatbot Backend", lifespan=lifespan)

# CORS for frontend integration (adjust allow_origins for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, tags=["chat"])
app.include_router(auth.router, prefix="/auth", tags=["authentication"])


@app.get("/health")
def health() -> dict[str, str]:
    """Health check."""
    return {"status": "ok"}

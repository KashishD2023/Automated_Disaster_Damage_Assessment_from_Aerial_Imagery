"""Database engine, session, and init (create tables + seed test data)."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import DATABASE_URL
from app.models import Base, Response

# SQLite needs check_same_thread=False for FastAPI
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """Dependency that yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Seed data: trigger -> response
SEED_RESPONSES = [
    ("hello", "Hi there!"),
    ("hi", "Hi there!"),
    ("help", "I can answer from the test DB. Try 'hello' or 'what can you do'."),
    ("what can you do", "I look up your message in a test database and reply. Try 'hello' or 'help'."),
    ("bye", "Goodbye!"),
]


def init_db() -> None:
    """Create tables and seed test data if the table is empty."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        if session.query(Response).count() == 0:
            for trigger, response_text in SEED_RESPONSES:
                session.add(Response(trigger=trigger, response=response_text))
            session.commit()

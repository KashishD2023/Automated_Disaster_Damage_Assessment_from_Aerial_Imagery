"""Application settings (e.g. DB path)."""

import os

# Database URL; override with env DATABASE_URL if needed
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./chatbot.db")

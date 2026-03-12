"""Application settings (e.g. DB path)."""

import os
from pathlib import Path

# Database URL; override with env DATABASE_URL if needed
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./chatbot.db")

# JWT Settings
SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

# Tiles CSV and static base for image URLs (project root = parent of app/)
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
TILES_CSV_PATH: Path = PROJECT_ROOT / "tiles_demo.csv"

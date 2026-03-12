"""SQLAlchemy models for chatbot responses."""

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func, Integer, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all models."""

    pass


class Response(Base):
    """Stored trigger -> response for the test chatbot."""

    __tablename__ = "responses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trigger: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class User(Base):
    """User model for authentication."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    # Relationship to user history
    user_history: Mapped[list["UserHistory"]] = relationship(
        "UserHistory", back_populates="user", cascade="all, delete-orphan"
    )


class UserHistory(Base):
    """Track tile analysis history for each user."""

    __tablename__ = "user_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    tile_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    view_mode: Mapped[str] = mapped_column(String(20), nullable=False)  # 'pre' or 'post'
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    # Relationship to user
    user: Mapped["User"] = relationship("User", back_populates="user_history")

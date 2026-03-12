"""Tests for POST /chat using FastAPI TestClient."""

from fastapi.testclient import TestClient

from app.main import app


def test_chat_hello_returns_seeded_response() -> None:
    """Known seeded keyword 'hello' returns the DB response."""
    with TestClient(app) as client:
        response = client.post("/chat", json={"message": "hello"})
        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "Hi there!"
        assert data["matched"] is True
        assert data["source"] == "database"


def test_chat_hello_case_insensitive() -> None:
    """Normalization: 'HELLO' still matches."""
    with TestClient(app) as client:
        response = client.post("/chat", json={"message": "HELLO"})
        assert response.status_code == 200
        assert response.json()["response"] == "Hi there!"
        assert response.json()["matched"] is True


def test_chat_no_match_returns_fallback() -> None:
    """Unknown input returns default fallback and matched=False."""
    with TestClient(app) as client:
        response = client.post("/chat", json={"message": "xyznonexistent"})
        assert response.status_code == 200
        data = response.json()
        assert "test DB" in data["response"]
        assert data["matched"] is False
        assert data["source"] == "fallback"


def test_chat_help_returns_seeded_response() -> None:
    """Seeded 'help' returns the help message."""
    with TestClient(app) as client:
        response = client.post("/chat", json={"message": "help"})
        assert response.status_code == 200
        data = response.json()
        assert "test DB" in data["response"]
        assert data["matched"] is True


def test_chat_empty_message_rejected() -> None:
    """Empty message fails validation."""
    with TestClient(app) as client:
        response = client.post("/chat", json={"message": ""})
        assert response.status_code == 422

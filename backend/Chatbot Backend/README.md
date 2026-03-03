# Chatbot Backend (FastAPI skeleton)

Minimal FastAPI backend: one chat endpoint that reads input, looks up responses in a test SQLite database, and returns a reply (or a fallback).

## Run

```bash
# From project root
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --reload-dir app --reload-exclude '*.db'
```

- **`--reload-dir app`** — Watch only the `app/` folder. Without this, uvicorn watches the whole project (including `.venv`), so it reports hundreds of "changed" files in site-packages and can reload in a loop.
- **`--reload-exclude '*.db'`** — Ignore SQLite file changes so creating/updating the DB on startup doesn’t trigger a reload.

- API: http://127.0.0.1:8000  
- Docs: http://127.0.0.1:8000/docs  

## API

- **POST /chat**  
  - Body: `{ "message": "hello", "session_id": null }` (session_id optional)  
  - Response: `{ "response": "Hi there!", "matched": true, "source": "database" }`  

- **GET /health**  
  - Returns `{ "status": "ok" }`  

## Test DB

SQLite file: `chatbot.db` (created in the current working directory on first request). Seeded triggers include: `hello`, `hi`, `help`, `what can you do`, `bye`. Override with env: `DATABASE_URL=sqlite:///./other.db`.

## Tests

```bash
pip install pytest
pytest tests/ -v
```

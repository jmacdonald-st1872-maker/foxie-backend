# Foxie Backend — JJ

## What this is
A starter backend for the Foxie website. It provides:
- `GET /` — status
- `GET /health` — health check
- `POST /api/chat` — sends a message to Foxie's AI model

## Run locally

1. Install Python 3.11+.
2. Open a terminal in this folder.
3. Run:

   pip install -r backend/requirements.txt

4. Copy `.env.example` to `.env`.
5. Put your AI API key in `.env`.
6. Start the server:

   uvicorn backend.server:app --reload

7. Visit:
   http://127.0.0.1:8000

## Important
Keep `.env` private and never upload it to GitHub.
This is the AI backend foundation. Search, maps, traffic, accounts,
database storage, voice, and other integrations should be added as
separate permissioned tools rather than giving the backend unrestricted access.

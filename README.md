# Movie Explorer

A self-hosted, AI-powered movie tracking app (like Letterboxd, with an AI layer). This repo currently contains the **foundation slice only**: project scaffolding, data model, and native library CRUD (add/log/rate/review a watch, watchlist, lists). AI features (taste analysis, critic, recommendations), the Letterboxd CSV importer, analytics, and PWA install support are not built yet.

## Prerequisites

- Node.js (v20+; developed against v24)
- Python 3.11
- A [TMDb API key](https://www.themoviedb.org/settings/api) (v3)
- A Google OAuth Client ID/Secret ([Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Credentials), with `http://localhost:8000/api/auth/callback/google` registered as an authorized redirect URI

Nothing authenticates and movie search won't work until real Google and TMDb credentials are supplied — the routes/flow are fully built, just credential-gated.

## Backend (FastAPI)

```bash
cd backend
py -3.11 -m venv .venv
./.venv/Scripts/activate        # .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
cp .env.example .env            # then fill in real GOOGLE_CLIENT_ID/SECRET and TMDB_API_KEY
alembic upgrade head            # creates movie_explorer.db and applies the schema
uvicorn app.main:app --reload
```

Runs on `http://localhost:8000`. Interactive API docs at `/docs`, health check at `/health`.

Run tests with `pytest` (uses an in-memory SQLite DB and a fixture user/session, so it doesn't need real Google or TMDb credentials).

## Frontend (Next.js)

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Runs on `http://localhost:3000`.

## Database

SQLite for this slice (`backend/movie_explorer.db`, gitignored) via SQLAlchemy — no server process to run. Schema migrations live in `backend/alembic/`. Postgres + pgvector is deferred until the embeddings/AI layer is built; swapping is a `DATABASE_URL` change plus a migration, not a rewrite (see `backend/app/database.py`).

## Project structure

See `backend/app/` (routers/models/schemas/services) and `frontend/app/` + `frontend/components/` for the current feature surface: Google OAuth login, TMDb search, and diary/watchlist/lists CRUD.

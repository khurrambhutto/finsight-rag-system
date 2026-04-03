# RAG System

Milestone 1 is a clean, minimal chat workspace built with:

- `frontend/`: `Vite + React + React Router + Clerk`
- `backend/`: `FastAPI + uv + LiteLLM + Clerk backend verification`
- local chat persistence via `SQLite`
- `docker-compose.yml`: local data services for later milestones

## Prerequisites

- Node.js 24+
- `uv`
- Docker
- Ollama running locally with a chat model pulled, for example:

```bash
ollama pull llama3.2
```

## Environment

Copy the example env files:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

Required values:

- `backend/.env`
  - `SQLITE_PATH` for the local chat database file
  - `CLERK_SECRET_KEY`
  - optionally `CLERK_JWT_KEY`
- `frontend/.env`
  - `VITE_CLERK_PUBLISHABLE_KEY`
  - `.env.local` is preferred for local Vite development

## Run locally

Start infrastructure:

```bash
docker compose up -d
```

Start the backend:

```bash
cd backend
uv run backend
```

Start the frontend:

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:5173`.
Backend runs on `http://localhost:8000`.

## Current Milestone 1 scope

- Clerk sign-in flow
- Protected chat workspace
- Server-sent-event chat streaming
- Local SQLite-backed saved chat history
- LiteLLM connection to local Ollama
- Settings screen with provider connectivity test


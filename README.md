# Codebase Intel

A codebase intelligence platform that indexes GitHub repositories, builds dependency graphs, and lets you explore and ask questions about unfamiliar code.

## What it does

1. **Ingests** a GitHub repo via the GitHub API (shallow clone for speed)
2. **Parses** every Python/JS/TS file using Python's `ast` module — extracts functions, classes, methods, and imports at the symbol level
3. **Builds a dependency graph** in PostgreSQL using recursive CTEs to traverse module relationships
4. **Embeds** all symbols into ChromaDB via `text-embedding-3-small`, chunked at function/class boundaries (not character count)
5. **Streams progress** in real time via WebSockets backed by Redis pub/sub
6. **Exposes** a versioned FastAPI REST API with pagination, filtering, and rate-limiting
7. **Frontend**: React + Vite + React Flow graph visualizer + Monaco editor + LangChain Q&A

## Architecture

```
Frontend (React + Vite)
    ↓ REST + WebSocket
FastAPI (app/main.py)
    ├── POST /api/v1/repositories      → fires Celery task
    ├── GET  /api/v1/repositories/:id/graph    → PostgreSQL recursive CTE
    ├── GET  /api/v1/repositories/:id/search   → ChromaDB semantic search
    ├── POST /api/v1/repositories/:id/qa       → LangChain RAG
    └── WS   /ws/ingestion/:id                 → Redis pub/sub → live progress

Celery Worker
    ├── Clone repo (GitPython)
    ├── Walk file tree (RepoWalker)
    ├── Parse AST (PythonASTParser)
    ├── Build dependency graph (PostgreSQL + ImportDependency table)
    └── Embed symbols (ChromaDB + OpenAI text-embedding-3-small)

PostgreSQL
    ├── repositories
    ├── code_files
    ├── code_symbols        ← functions, classes, methods
    └── import_dependencies ← directed edges for dependency graph

Redis
    └── Celery broker + result backend + pub/sub progress channel

ChromaDB
    └── code_symbols collection (embeddings + metadata)
```

## Setup

### Prerequisites
- Python 3.11+
- Node 20+
- PostgreSQL running locally
- Redis running locally (`redis-server`)
- OpenAI API key

### Backend

```bash
cd backend

# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python -m venv venv
source venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# Fill in DATABASE_URL, REDIS_URL, OPENAI_API_KEY, GITHUB_TOKEN

# Create DB
createdb codebase_intel

# Run API server
uvicorn app.main:app --reload --port 8000

# In a separate terminal (same venv):
celery -A app.core.celery_app worker --loglevel=info
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. API docs at `http://localhost:8000/api/docs`.

## Resume talking points

- Built an AST-based ingestion pipeline using Python's `ast` module to extract function/class/method symbols with line-level precision — chunked at semantic boundaries instead of character count for more meaningful embeddings
- Modeled module relationships as a directed graph in PostgreSQL using a recursive CTE to traverse import chains; exposed via a React Flow visualization
- Designed a Celery + Redis async job queue for long-running repo ingestion, with real-time progress streaming to the frontend via WebSockets and Redis pub/sub
- Implemented function-level semantic search over embedded codebases using ChromaDB and LangChain RAG with `gpt-4o-mini`, with a versioned FastAPI backend supporting multi-repo isolation, pagination, and kind/file filtering

## Interview story

> "At Oracle I wrote KT docs and ran onboarding sessions for every major release — I knew exactly how much time engineers waste trying to understand an unfamiliar codebase. The interesting engineering problem here wasn't the AI layer — it was building a proper data pipeline: parsing code at the AST level rather than by character count, modeling import relationships as graph edges in PostgreSQL so I could run recursive queries like 'what depends on this module', and making the ingestion async so a large repo doesn't time out the HTTP request."

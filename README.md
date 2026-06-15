# Codebase Intel

A codebase intelligence platform that indexes GitHub repositories, builds dependency graphs, and lets you explore and ask questions about unfamiliar code — across both Python and JavaScript/TypeScript codebases.

## What it does

1. **Ingests** a GitHub repo via the GitHub API (shallow clone for speed)
2. **Parses** every Python and JS/TS/JSX/TSX file through a polyglot AST pipeline — Python's `ast` module for Python, tree-sitter for the frontend stack — extracting functions, classes, methods, and imports at the symbol level (not by character count)
3. **Builds a dependency graph** in PostgreSQL using recursive CTEs to traverse module relationships, with language-aware import resolution (Python dotted modules vs. JS/TS relative paths and `@/` aliases)
4. **Embeds** all symbols into ChromaDB via `text-embedding-3-small`, chunked at function/class/method boundaries
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
    ├── Parse source — dispatcher routes by extension:
    │     ├── .py              → Python `ast` module
    │     └── .js/.jsx/.ts/.tsx → tree-sitter (tree-sitter-languages)
    ├── Resolve imports — language-aware:
    │     ├── Python  → dotted module paths (agents.pipeline → agents/pipeline.py)
    │     └── JS/TS   → relative (./components/Button) and @/ alias imports
    ├── Build dependency graph (PostgreSQL + ImportDependency table)
    └── Embed symbols (ChromaDB + OpenAI text-embedding-3-small)

PostgreSQL
    ├── repositories
    ├── code_files
    ├── code_symbols        ← functions, classes, methods (any supported language)
    └── import_dependencies ← directed edges for dependency graph

Redis
    └── Celery broker + result backend + pub/sub progress channel

ChromaDB
    └── code_symbols collection (embeddings + metadata)
```

## Setup

### Prerequisites
- Python 3.10+
- Node 20+
- PostgreSQL (Supabase or local)
- Redis (Upstash or local)
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

# Run API server
uvicorn app.main:app --reload --port 8000

# In a separate terminal (same venv):
celery -A app.core.celery_app worker --loglevel=info --pool=solo   # --pool=solo on Windows
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. API docs at `http://localhost:8000/api/docs`.


## Developer notes

The frontend UI/UX design, README file and the architecture diagram above were developed with AI assistance (Claude). Everything else — the polyglot AST/tree-sitter parsing pipeline, language-aware dependency resolution, database schema, async ingestion architecture, and API design — was designed and implemented independently.
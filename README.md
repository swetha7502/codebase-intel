# Codebase Intel

An AI-powered code exploration tool for understanding large repositories. Point it at any public GitHub repo and get an interactive dependency graph, semantic symbol search, and a Q&A interface over the entire codebase.

**Live demo:** https://codebase-intel-frontend-kteuihegea-uc.a.run.app

---

## What it does

- **Dependency graph** — Parses Python and JavaScript/TypeScript codebases and visualizes file-level import relationships as an interactive graph
- **Semantic search** — Embed and index every function, class, and module using OpenAI embeddings stored in pgvector; search by meaning, not just keyword
- **Q&A** — Ask natural language questions about the codebase and get answers grounded in the actual source code
- **Multi-language parsing** — Python via the standard AST module; JS/TS/JSX/TSX via tree-sitter for accurate, fault-tolerant parsing

---

## Architecture

```
GitHub URL
    │
    ▼
FastAPI (Cloud Run)
    │  enqueues job
    ▼
Celery Worker (Cloud Run) ──► Clones repo, parses files, builds graph
    │                          Generates embeddings via OpenAI
    │                          Stores symbols + vectors in Supabase (pgvector)
    ▼
React Frontend (Cloud Run)
    │  dependency graph
    │  semantic search
    └► Q&A over codebase
```

**Services:** Three independent Cloud Run services (API, worker, frontend) deployed via GitHub Actions on every push to main.

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React, Vite, TypeScript |
| API | FastAPI, Python |
| Worker | Celery |
| Database | Supabase (PostgreSQL + pgvector) |
| Cache / queue | Redis Cloud |
| Parsers | Python AST, tree-sitter |
| Embeddings | OpenAI `text-embedding-ada-002` |
| Infrastructure | GCP Cloud Run, Artifact Registry |
| CI/CD | GitHub Actions |

---

## Key engineering decisions

**pgvector over ChromaDB**
Started with ChromaDB for vector storage but migrated to pgvector on Supabase. This consolidates embeddings and relational data (repositories, symbols, jobs) into a single Postgres instance, eliminating a separate vector database dependency and simplifying the deployment surface. The tradeoff is slightly more complex queries (`ORDER BY embedding <=> $1`) versus ChromaDB's purpose-built API.

**Redis Cloud over Upstash**
Initially used Upstash for the Celery broker. Upstash drops idle connections after a period of inactivity, which caused Celery workers to silently fail on the first task after a quiet period. Switched to Redis Cloud free tier, which maintains persistent connections and behaves like a standard Redis instance.

**Supabase session pooler for database connections**
Direct Supabase connections use IPv6, which caused connectivity failures from Cloud Run. Switched to the Supabase session pooler endpoint (`aws-1-us-east-2.pooler.supabase.com`) which proxies over IPv4 and resolved the issue.

**Parser scope: Python + JS/TS only**
Deliberately scoped the multi-language parser to Python and JavaScript/TypeScript rather than attempting broad language support. This covers the most common full-stack project structures while keeping the parser layer maintainable. JSON, YAML, and Markdown files appear as nodes in the graph but are not parsed for symbols.

**Three-service Cloud Run architecture**
Separated the API, Celery worker, and frontend into independent Cloud Run services. This allows the worker to run with higher memory (`2Gi`) and `--no-cpu-throttling` for compute-intensive indexing jobs, while the API and frontend scale independently based on request volume.

---

## AI assistance disclosure

Frontend UI/UX design and the system architecture diagram were developed with AI assistance. All backend engineering, infrastructure configuration, parser implementation, and deployment pipeline were written and debugged without AI generation.

---

## Local development

```bash
# Clone the repo
git clone https://github.com/swetha7502/codebase-intel
cd codebase-intel

# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Worker (separate terminal)
celery -A app.core.celery_app worker --loglevel=info --concurrency=1

# Frontend
cd frontend
npm install
npm run dev
```

Requires a `.env` file in `backend/` with `DATABASE_URL`, `REDIS_URL`, `OPENAI_API_KEY`, and `GH_PAT`.
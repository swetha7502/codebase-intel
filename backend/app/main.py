from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import repositories, search, websocket
from app.core.database import Base, engine

# Create all tables (use Alembic for production migrations)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Codebase Intelligence API",
    description="Index GitHub repos, explore dependency graphs, and ask questions about any codebase.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(repositories.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(websocket.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}

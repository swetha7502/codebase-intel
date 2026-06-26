"""
/api/v1/repositories — CRUD + ingestion trigger
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import CodeFile, CodeSymbol, ImportDependency, IngestionStatus, Repository
from app.schemas.schemas import (
    DependencyGraph,
    GraphEdge,
    GraphNode,
    RepoCreate,
    RepoListResponse,
    RepoResponse,
    SymbolListResponse,
    SymbolResponse,
)
from app.services.github_service import fetch_repo_metadata, parse_github_url
from app.tasks.ingestion import ingest_repository

router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.get("", response_model=RepoListResponse)
def list_repositories(db: Session = Depends(get_db)):
    repos = db.query(Repository).order_by(Repository.created_at.desc()).all()
    return {"items": repos, "total": len(repos)}


@router.post("", response_model=RepoResponse, status_code=201)
async def add_repository(payload: RepoCreate, db: Session = Depends(get_db)):
    try:
        owner, name = parse_github_url(payload.github_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    existing = db.query(Repository).filter(Repository.github_url == payload.github_url).first()
    if existing:
        raise HTTPException(status_code=409, detail="Repository already exists")

    try:
        meta = await fetch_repo_metadata(owner, name)
    except Exception:
        meta = {}

    repo = Repository(
        github_url=payload.github_url,
        owner=owner,
        name=name,
        description=meta.get("description"),
        language=meta.get("language"),
        star_count=meta.get("star_count", 0),
        default_branch=meta.get("default_branch", "main"),
        status=IngestionStatus.PENDING,
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)

    # Fire off async ingestion task
    task = ingest_repository.delay(repo.id)
    repo.celery_task_id = task.id
    db.commit()
    db.refresh(repo)

    return repo


@router.get("/{repo_id}", response_model=RepoResponse)
def get_repository(repo_id: str, db: Session = Depends(get_db)):
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


@router.delete("/{repo_id}", status_code=204)
def delete_repository(repo_id: str, db: Session = Depends(get_db)):
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    db.delete(repo)
    db.commit()
    db.expunge_all()


@router.post("/{repo_id}/reindex", response_model=RepoResponse)
def reindex_repository(repo_id: str, db: Session = Depends(get_db)):
    """Re-trigger ingestion for an already-added repo."""
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Clear existing data (embeddings are stored on CodeSymbol rows, deleted via cascade)
    db.query(ImportDependency).filter(ImportDependency.repository_id == repo_id).delete()
    db.query(CodeSymbol).filter(CodeSymbol.repository_id == repo_id).delete()
    db.query(CodeFile).filter(CodeFile.repository_id == repo_id).delete()
    db.commit()

    repo.status = IngestionStatus.PENDING
    repo.error_message = None
    db.commit()

    task = ingest_repository.delay(repo_id)
    repo.celery_task_id = task.id
    db.commit()
    db.refresh(repo)
    return repo


@router.get("/{repo_id}/graph", response_model=DependencyGraph)
def get_dependency_graph(repo_id: str, db: Session = Depends(get_db)):
    """
    Returns the dependency graph for React Flow.
    Uses a recursive CTE to build the full graph from import_dependencies.
    """
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Fetch all files with their symbol counts
    files_q = text("""
        SELECT
            cf.id,
            cf.path,
            cf.language,
            cf.line_count,
            COUNT(cs.id) AS symbol_count
        FROM code_files cf
        LEFT JOIN code_symbols cs ON cs.file_id = cf.id
        WHERE cf.repository_id = :repo_id
        GROUP BY cf.id, cf.path, cf.language, cf.line_count
        ORDER BY cf.path
    """)
    files = db.execute(files_q, {"repo_id": repo_id}).fetchall()

    nodes = [
        GraphNode(
            id=str(row.id),
            label=row.path.split("/")[-1],
            language=row.language or "unknown",
            line_count=row.line_count or 0,
            symbol_count=row.symbol_count or 0,
        )
        for row in files
    ]

    # Fetch internal dependency edges
    edges_q = text("""
        SELECT
            cf_src.path  AS source_path,
            cf_tgt.path  AS target_path,
            id.module_name
        FROM import_dependencies id
        JOIN code_files cf_src ON cf_src.id = id.source_file_id
        JOIN code_files cf_tgt ON cf_tgt.id = id.target_file_id
        WHERE id.repository_id = :repo_id
          AND id.is_internal = TRUE
    """)
    edges_rows = db.execute(edges_q, {"repo_id": repo_id}).fetchall()

    # Build file_path -> node_id map for edge wiring
    path_map = {row.path: str(row.id) for row in files}

    edges = [
        GraphEdge(
            source=path_map.get(row.source_path, row.source_path),
            target=path_map.get(row.target_path, row.target_path),
            module_name=row.module_name,
        )
        for row in edges_rows
        if row.source_path in path_map and row.target_path in path_map
    ]

    return DependencyGraph(nodes=nodes, edges=edges)


@router.get("/{repo_id}/symbols", response_model=SymbolListResponse)
def list_symbols(
    repo_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    kind: str | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(CodeSymbol).filter(CodeSymbol.repository_id == repo_id)
    if kind:
        q = q.filter(CodeSymbol.kind == kind)
    total = q.count()
    symbols = q.offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for sym in symbols:
        items.append(SymbolResponse(
            id=sym.id,
            name=sym.name,
            qualified_name=sym.qualified_name,
            kind=sym.kind,
            line_start=sym.line_start,
            line_end=sym.line_end,
            docstring=sym.docstring,
            source_code=sym.source_code,
            file_path=sym.file.path if sym.file else "",
        ))

    return SymbolListResponse(items=items, total=total, page=page, page_size=page_size)

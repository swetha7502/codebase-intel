"""
/api/v1/repositories/{repo_id}/search  — semantic search via pgvector
/api/v1/repositories/{repo_id}/qa      — natural language Q&A
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import CodeFile, Repository
from app.schemas.schemas import QARequest, QAResponse, SearchResponse, SearchResult
from app.services.embedding_service import search_symbols
from app.services.qa_service import answer_question

router = APIRouter(tags=["search"])


@router.get("/repositories/{repo_id}/search", response_model=SearchResponse)
def semantic_search(
    repo_id: str,
    q: str = Query(..., min_length=2, description="Natural language or code search query"),
    n: int = Query(10, ge=1, le=50, description="Number of results"),
    kind: str | None = Query(None, description="Filter by symbol kind: function|class|method"),
    db: Session = Depends(get_db),
):
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    if repo.status != "complete":
        raise HTTPException(status_code=400, detail="Repository is still being indexed")

    raw = search_symbols(repo_id, q, db, n_results=n, kind_filter=kind)

    results = []
    for r in raw:
        symbol = r["symbol"]
        distance = r["distance"]

        # Get the file path from the join
        file = db.query(CodeFile).filter(CodeFile.id == symbol.file_id).first()
        file_path = file.path if file else ""

        # Snippet: first 10 non-empty lines of source
        snippet_lines = [l for l in (symbol.source_code or "").split("\n") if l.strip()]
        snippet = "\n".join(snippet_lines[:10])[:400]

        results.append(SearchResult(
            chroma_id=str(symbol.id),   # kept for schema compat — now the symbol's PG uuid
            file_path=file_path,
            qualified_name=symbol.qualified_name or symbol.name,
            kind=symbol.kind.value,
            line_start=symbol.line_start or 0,
            line_end=symbol.line_end or 0,
            score=round(1 - distance, 4),
            snippet=snippet,
        ))

    return SearchResponse(results=results, total=len(results), query=q)


@router.post("/repositories/{repo_id}/qa", response_model=QAResponse)
def ask_question(
    repo_id: str,
    payload: QARequest,
    db: Session = Depends(get_db),
):
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    if repo.status != "complete":
        raise HTTPException(status_code=400, detail="Repository is still being indexed")

    result = answer_question(repo_id, payload.question)
    return QAResponse(answer=result["answer"], sources=result["sources"])

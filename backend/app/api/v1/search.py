"""
/api/v1/repositories/{repo_id}/search  — semantic search
/api/v1/repositories/{repo_id}/qa      — natural language Q&A
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Repository
from app.schemas.schemas import SearchResponse, SearchResult, QARequest, QAResponse
from app.services.embedding_service import search_symbols
from app.services.qa_service import answer_question

router = APIRouter(tags=["search"])


@router.get("/repositories/{repo_id}/search", response_model=SearchResponse)
def semantic_search(
    repo_id: str,
    q: str = Query(..., min_length=2, description="Natural language or code search query"),
    n: int = Query(10, ge=1, le=50, description="Number of results"),
    kind: str | None = Query(None, description="Filter by symbol kind: function|class|method"),
    file: str | None = Query(None, description="Filter by file path substring"),
    db: Session = Depends(get_db),
):
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    if repo.status != "complete":
        raise HTTPException(status_code=400, detail="Repository is still being indexed")

    raw = search_symbols(repo_id, q, n_results=n, kind_filter=kind, file_filter=file)

    results = []
    for r in raw:
        meta = r["metadata"]
        doc = r["document"]
        # Extract snippet: first 300 chars of the source code block
        snippet_lines = [line for line in doc.split("\n") if not line.startswith("#")]
        snippet = "\n".join(snippet_lines[:10]).strip()[:400]

        results.append(SearchResult(
            chroma_id=r["chroma_id"],
            file_path=meta.get("file_path", ""),
            qualified_name=meta.get("qualified_name", ""),
            kind=meta.get("kind", ""),
            line_start=meta.get("line_start", 0),
            line_end=meta.get("line_end", 0),
            score=round(1 - r["distance"], 4),
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

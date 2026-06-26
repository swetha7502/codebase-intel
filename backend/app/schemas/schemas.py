from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ── Repository ────────────────────────────────────────────────────────────────

class RepoCreate(BaseModel):
    github_url: str


class RepoResponse(BaseModel):
    id: str
    github_url: str
    owner: str
    name: str
    description: Optional[str]
    language: Optional[str]
    star_count: int
    status: str
    file_count: int
    function_count: int
    class_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RepoListResponse(BaseModel):
    items: list[RepoResponse]
    total: int


# ── Dependency graph ──────────────────────────────────────────────────────────

class GraphNode(BaseModel):
    id: str           # file path
    label: str        # short filename
    language: str
    line_count: int
    symbol_count: int


class GraphEdge(BaseModel):
    source: str       # file path
    target: str       # file path
    module_name: str


class DependencyGraph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


# ── Search ────────────────────────────────────────────────────────────────────

class SearchResult(BaseModel):
    chroma_id: str
    file_path: str
    qualified_name: str
    kind: str
    line_start: int
    line_end: int
    score: float
    snippet: str


class SearchResponse(BaseModel):
    results: list[SearchResult]
    total: int
    query: str


# ── Q&A ───────────────────────────────────────────────────────────────────────

class QARequest(BaseModel):
    question: str


class QASource(BaseModel):
    file_path: Optional[str]
    qualified_name: Optional[str]
    kind: Optional[str]
    line_start: Optional[int]


class QAResponse(BaseModel):
    answer: str
    sources: list[QASource]


# ── Symbols ───────────────────────────────────────────────────────────────────

class SymbolResponse(BaseModel):
    id: str
    name: str
    qualified_name: str
    kind: str
    line_start: Optional[int]
    line_end: Optional[int]
    docstring: Optional[str]
    source_code: Optional[str]
    file_path: str

    class Config:
        from_attributes = True


class SymbolListResponse(BaseModel):
    items: list[SymbolResponse]
    total: int
    page: int
    page_size: int

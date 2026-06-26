"""
Embedding service: generates OpenAI embeddings and stores them as pgvector
vectors directly in the code_symbols table in Supabase/PostgreSQL.

Replaces the previous ChromaDB-based implementation. pgvector is shared
between the API and Celery worker (same Supabase DB), so embeddings
generated during ingestion are immediately available for search — no local
disk state, fully compatible with stateless Cloud Run containers.
"""
import openai
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.models import CodeSymbol
from app.services.parsers.base import ParsedSymbol

settings = get_settings()

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMS = 1536


def _get_openai_client() -> openai.OpenAI:
    return openai.OpenAI(api_key=settings.openai_api_key)


def build_document_text(symbol: ParsedSymbol, file_path: str) -> str:
    """
    Construct a rich text document for embedding.
    Combines qualified name, docstring, and source so semantic search
    finds both intent (docstring) and implementation (code).
    Truncated to stay safely under the 8192-token limit for
    text-embedding-3-small (roughly 4 chars/token → ~6000 chars).
    """
    parts = [f"# {symbol.qualified_name} ({symbol.kind}) in {file_path}"]
    if symbol.docstring:
        parts.append(f"# Docstring: {symbol.docstring}")
    parts.append(symbol.source_code)
    return "\n".join(parts)[:6000]


def embed_symbols(
    repository_id: str,
    symbols_with_paths: list[tuple[ParsedSymbol, str]],
    db: Session,
    batch_size: int = 100,
) -> None:
    """
    Generates embeddings for all symbols and writes them to the
    code_symbols.embedding column in PostgreSQL via pgvector.

    The DB session is passed in from the Celery task so we reuse the
    same transaction and avoid opening extra connections.
    """
    client = _get_openai_client()

    for i in range(0, len(symbols_with_paths), batch_size):
        batch = symbols_with_paths[i:i + batch_size]
        texts = [build_document_text(sym, path) for sym, path in batch]

        response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
        vectors = [item.embedding for item in response.data]

        for (symbol, file_path), vector in zip(batch, vectors):
            db.query(CodeSymbol).filter(
                CodeSymbol.repository_id == repository_id,
                CodeSymbol.qualified_name == symbol.qualified_name,
            ).update({"embedding": vector}, synchronize_session=False)

    db.commit()


def search_symbols(
    repository_id: str,
    query: str,
    db: Session,
    n_results: int = 10,
    kind_filter: str | None = None,
) -> list[dict]:
    """
    Semantic search via pgvector cosine distance.
    Returns list of result dicts matching the shape the API expects.
    """
    client = _get_openai_client()

    response = client.embeddings.create(model=EMBEDDING_MODEL, input=[query])
    query_vector = response.data[0].embedding

    from sqlalchemy import func

    q = db.query(
        CodeSymbol,
        CodeSymbol.embedding.cosine_distance(query_vector).label("distance"),
    ).filter(
        CodeSymbol.repository_id == repository_id,
        CodeSymbol.embedding.isnot(None),
    )
    if kind_filter:
        q = q.filter(CodeSymbol.kind == kind_filter)

    results = (
        q.order_by("distance")
        .limit(n_results)
        .all()
    )

    output = []
    for symbol, distance in results:
        output.append({
            "symbol": symbol,
            "distance": float(distance),
        })
    return output


def delete_repo_embeddings(repository_id: str, db: Session) -> None:
    """Null out embeddings for a repo (rows are deleted via CASCADE on repo delete)."""
    db.query(CodeSymbol).filter(
        CodeSymbol.repository_id == repository_id,
    ).update({"embedding": None}, synchronize_session=False)
    db.commit()

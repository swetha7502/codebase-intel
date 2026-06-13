"""
Embedding service: indexes parsed code symbols into ChromaDB
using OpenAI text-embedding-3-small. Chunks at function/class boundary.
"""
import chromadb
from chromadb.utils import embedding_functions
from app.core.config import get_settings
from app.services.ast_parser import ParsedSymbol

settings = get_settings()

COLLECTION_NAME = "code_symbols"


def get_chroma_client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(path=settings.chroma_persist_dir)


def get_collection(client: chromadb.PersistentClient):
    ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=settings.openai_api_key,
        model_name="text-embedding-3-small",
    )
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )


def build_document_text(symbol: ParsedSymbol, file_path: str) -> str:
    parts = [f"# {symbol.qualified_name} ({symbol.kind}) in {file_path}"]
    if symbol.docstring:
        parts.append(f"# Docstring: {symbol.docstring}")
    parts.append(symbol.source_code)
    text = "\n".join(parts)
    # Truncate to ~6000 chars to stay safely under 8192 token limit
    return text[:6000]


def embed_symbols(
    repository_id: str,
    symbols_with_paths: list[tuple[ParsedSymbol, str]],  # (symbol, file_path)
    batch_size: int = 100,
) -> dict[str, str]:
    """
    Embeds a list of symbols into ChromaDB.
    Returns a mapping of qualified_name -> chroma_id.
    """
    client = get_chroma_client()
    collection = get_collection(client)

    id_map = {}

    for i in range(0, len(symbols_with_paths), batch_size):
        batch = symbols_with_paths[i:i + batch_size]
        ids, documents, metadatas = [], [], []

        for symbol, file_path in batch:
            chroma_id = f"{repository_id}::{file_path}::{symbol.qualified_name}::{symbol.line_start}"
            doc_text = build_document_text(symbol, file_path)

            ids.append(chroma_id)
            documents.append(doc_text)
            metadatas.append({
                "repository_id": repository_id,
                "file_path": file_path,
                "symbol_name": symbol.name,
                "qualified_name": symbol.qualified_name,
                "kind": symbol.kind,
                "line_start": symbol.line_start,
                "line_end": symbol.line_end,
            })
            id_map[symbol.qualified_name] = chroma_id

        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

    return id_map


def search_symbols(
    repository_id: str,
    query: str,
    n_results: int = 10,
    kind_filter: str | None = None,
    file_filter: str | None = None,
) -> list[dict]:
    """
    Semantic search over embedded code symbols.
    Returns list of result dicts with metadata + distance.
    """
    client = get_chroma_client()
    collection = get_collection(client)

    where = {"repository_id": repository_id}
    if kind_filter:
        where["kind"] = kind_filter
    if file_filter:
        where["file_path"] = {"$contains": file_filter}

    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        where=where if len(where) > 1 or "repository_id" in where else None,
        include=["metadatas", "distances", "documents"],
    )

    output = []
    if results["ids"] and results["ids"][0]:
        for idx, chroma_id in enumerate(results["ids"][0]):
            output.append({
                "chroma_id": chroma_id,
                "metadata": results["metadatas"][0][idx],
                "distance": results["distances"][0][idx],
                "document": results["documents"][0][idx],
            })
    return output


def delete_repo_embeddings(repository_id: str):
    """Remove all embeddings for a repo when it's deleted."""
    client = get_chroma_client()
    collection = get_collection(client)
    collection.delete(where={"repository_id": repository_id})

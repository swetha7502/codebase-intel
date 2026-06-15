"""
Run from backend/ with venv activated: python debug_search.py
"""
import os

from app.core.config import get_settings
from app.services.embedding_service import COLLECTION_NAME, get_chroma_client, get_collection

settings = get_settings()
print(f"CHROMA_PERSIST_DIR (absolute): {os.path.abspath(settings.chroma_persist_dir)}")

client = get_chroma_client()
collection = get_collection(client)
print(f"Total embeddings: {collection.count()}")

REPO_ID = "8c6738ae-0d06-4de0-92ef-13edddbc36c0"  # <- replace with the ID from your browser URL

# How many docs exist for this repo_id?
matches = collection.get(where={"repository_id": REPO_ID}, include=["metadatas"])
print(f"\nDocs with repository_id={REPO_ID}: {len(matches['ids'])}")
for m in matches["metadatas"][:10]:
    print(f"  - {m.get('qualified_name')}  ({m.get('file_path')})")

# Now try the actual semantic query
print("\n--- Semantic query test ---")
results = collection.query(
    query_texts=["searching PubMed and arXiv"],
    n_results=5,
    where={"repository_id": REPO_ID},
    include=["metadatas", "distances"],
)
print(f"Result ids: {results['ids']}")
print(f"Distances: {results['distances']}")
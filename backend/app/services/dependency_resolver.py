"""
Resolves import module names to actual file paths within the repo.
e.g. "from agents.pipeline import X" -> "backend/agents/pipeline.py"

All paths passed in are expected to already be normalized to forward
slashes (done in the ingestion task before this is called).
"""
from pathlib import Path


def resolve_internal_dependency(
    module_name: str,
    source_relative_path: str,
    all_file_paths: list[str],
) -> str | None:
    """
    Try to resolve a module_name to a file path in the repo.
    Returns the matching path from all_file_paths if found, None otherwise.
    """
    path_candidate = module_name.replace(".", "/")
    candidates = [
        f"{path_candidate}.py",
        f"{path_candidate}/__init__.py",
    ]

    # Also try relative resolution from source's directory
    source_dir = str(Path(source_relative_path).parent).replace("\\", "/")
    if source_dir and source_dir != ".":
        for c in list(candidates):
            candidates.append(f"{source_dir}/{c}")

    all_paths_set = set(all_file_paths)

    for candidate in candidates:
        normalized = candidate.replace("\\", "/")

        # Direct match
        if normalized in all_paths_set:
            return normalized

        # Suffix match: e.g. candidate "agents/pipeline.py" matches a stored
        # path "backend/agents/pipeline.py" when the repo root (e.g. "backend/")
        # isn't part of the import's module path.
        for stored_path in all_paths_set:
            if stored_path == normalized or stored_path.endswith("/" + normalized):
                return stored_path

    return None
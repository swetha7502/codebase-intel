"""
Resolves import specifiers to actual file paths within the repo.

Two resolution strategies, dispatched by source file language:
  - Python: dotted module names (e.g. "agents.pipeline" -> "agents/pipeline.py"),
    with a suffix-match fallback for repo-root prefixes (e.g. "backend/").
  - JS/TS/TSX: relative paths (./, ../) and the common Next.js/tsconfig
    "@/" alias, resolved by trying common extensions and index files.

All paths passed in are expected to already be normalized to forward slashes.
"""
import posixpath
from pathlib import Path

JS_LANGUAGES = {"javascript", "typescript", "tsx"}

JS_EXTENSIONS = [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"]
JS_INDEX_SUFFIXES = [f"/index{ext}" for ext in JS_EXTENSIONS]


def resolve_internal_dependency(
    module_name: str,
    source_relative_path: str,
    all_file_paths: list[str],
) -> str | None:
    """
    Resolve a Python dotted module name to a file path in the repo.
    Returns the matching path from all_file_paths if found, None otherwise.
    """
    path_candidate = module_name.replace(".", "/")
    candidates = [
        f"{path_candidate}.py",
        f"{path_candidate}/__init__.py",
    ]

    source_dir = str(Path(source_relative_path).parent).replace("\\", "/")
    if source_dir and source_dir != ".":
        for c in list(candidates):
            candidates.append(f"{source_dir}/{c}")

    all_paths_set = set(all_file_paths)

    for candidate in candidates:
        normalized = candidate.replace("\\", "/")

        if normalized in all_paths_set:
            return normalized

        # Suffix match: e.g. candidate "agents/pipeline.py" matches a stored
        # path "backend/agents/pipeline.py" when the repo root (e.g. "backend/")
        # isn't part of the import's module path.
        for stored_path in all_paths_set:
            if stored_path == normalized or stored_path.endswith("/" + normalized):
                return stored_path

    return None


def resolve_js_dependency(
    import_path: str,
    source_relative_path: str,
    all_file_paths: list[str],
) -> str | None:
    """
    Resolve a JS/TS import specifier to a file path in the repo.

    - "./foo" / "../utils/bar" -> resolved relative to the source file's directory
    - "@/components/Button"    -> tried against repo root and "src/" (common
                                   Next.js / tsconfig path alias conventions)
    - anything else (bare specifiers like "react", "next/navigation")
      is treated as an external package -> returns None
    """
    if not (import_path.startswith(".") or import_path.startswith("@/")):
        return None

    all_paths_set = set(all_file_paths)

    source_dir = str(Path(source_relative_path).parent).replace("\\", "/")
    if source_dir == ".":
        source_dir = ""

    candidate_bases = []

    if import_path.startswith("."):
        resolved = posixpath.normpath(posixpath.join(source_dir, import_path))
        candidate_bases.append(resolved.lstrip("/"))
    else:  # "@/..."
        rest = import_path[2:]
        candidate_bases.append(rest)
        candidate_bases.append(f"src/{rest}")

    for base in candidate_bases:
        if base in all_paths_set:
            return base

        for ext in JS_EXTENSIONS:
            candidate = f"{base}{ext}"
            if candidate in all_paths_set:
                return candidate

        for index_suffix in JS_INDEX_SUFFIXES:
            candidate = f"{base}{index_suffix}"
            if candidate in all_paths_set:
                return candidate

    return None


def resolve_dependency(
    module_name: str,
    source_relative_path: str,
    all_file_paths: list[str],
    language: str,
) -> str | None:
    """Language-aware entry point used by the ingestion pipeline."""
    if language in JS_LANGUAGES:
        return resolve_js_dependency(module_name, source_relative_path, all_file_paths)
    return resolve_internal_dependency(module_name, source_relative_path, all_file_paths)

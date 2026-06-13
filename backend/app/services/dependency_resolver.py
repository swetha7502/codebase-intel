from pathlib import Path


def resolve_internal_dependency(
    module_name: str,
    source_relative_path: str,
    all_file_paths: list[str],
) -> str | None:
    path_candidate = module_name.replace(".", "/")
    candidates = [
        f"{path_candidate}.py",
        f"{path_candidate}/__init__.py",
    ]

    source_dir = str(Path(source_relative_path).parent)
    if source_dir and source_dir != ".":
        for c in list(candidates):
            candidates.append(f"{source_dir}/{c}")

    # Normalize all stored paths to forward slashes
    normalized_all = {p.replace("\\", "/"): p for p in all_file_paths}

    for candidate in candidates:
        normalized = candidate.replace("\\", "/")
        # Direct match
        if normalized in normalized_all:
            return normalized_all[normalized]
        # Try matching with any prefix (e.g. stored as backend/agents/x.py, import is agents/x.py)
        for stored_normalized, original in normalized_all.items():
            if stored_normalized.endswith("/" + normalized):
                return original

    return None
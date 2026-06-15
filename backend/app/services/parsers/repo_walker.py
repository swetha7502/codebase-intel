"""
Walks a cloned repo and returns all files we can parse:
Python + JS/TS/JSX/TSX. Skips common noise directories and lockfiles.
"""
import os

from app.services.parsers.dispatcher import is_supported

SKIP_DIRS = {
    ".git", ".github", "__pycache__", "node_modules", ".venv", "venv",
    "env", "dist", "build", ".next", "coverage", ".pytest_cache",
    ".mypy_cache",
}

SKIP_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
}

# Skip generated/minified files over ~500KB
MAX_FILE_SIZE_BYTES = 500_000


class RepoWalker:

    def walk(self, repo_root: str) -> list[str]:
        """Returns absolute paths to every file we know how to parse."""
        result = []
        for dirpath, dirnames, filenames in os.walk(repo_root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

            for filename in filenames:
                if filename in SKIP_FILES:
                    continue

                full_path = os.path.join(dirpath, filename)

                if not is_supported(full_path):
                    continue

                try:
                    if os.path.getsize(full_path) > MAX_FILE_SIZE_BYTES:
                        continue
                except OSError:
                    continue

                result.append(full_path)

        return result

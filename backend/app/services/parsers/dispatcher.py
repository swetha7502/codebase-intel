"""
Single entry point for parsing any file in a repo.
Routes to the Python AST parser or tree-sitter (JS/TS/TSX).
"""
from pathlib import Path

from app.services.parsers.base import ParsedFile
from app.services.parsers.python_parser import PythonASTParser
from app.services.parsers.treesitter_parser import TreeSitterParser

# extension -> (language label, parser kind)
EXTENSION_MAP: dict[str, tuple[str, str]] = {
    ".py": ("python", "python"),

    ".js": ("javascript", "treesitter"),
    ".jsx": ("javascript", "treesitter"),
    ".mjs": ("javascript", "treesitter"),
    ".cjs": ("javascript", "treesitter"),
    ".ts": ("typescript", "treesitter"),
    ".tsx": ("tsx", "treesitter"),
}

_treesitter_cache: dict[str, TreeSitterParser] = {}


def get_language_and_kind(file_path: str) -> tuple[str, str]:
    """Returns (language_label, parser_kind) for a given file path."""
    ext = Path(file_path).suffix.lower()
    return EXTENSION_MAP.get(ext, ("unknown", "unsupported"))


def is_supported(file_path: str) -> bool:
    ext = Path(file_path).suffix.lower()
    return ext in EXTENSION_MAP


def parse_file(file_path: str, repo_root: str) -> ParsedFile:
    language, parser_kind = get_language_and_kind(file_path)

    if parser_kind == "python":
        return PythonASTParser().parse(file_path, repo_root)

    if parser_kind == "treesitter":
        if language not in _treesitter_cache:
            _treesitter_cache[language] = TreeSitterParser(language)
        return _treesitter_cache[language].parse(file_path, repo_root)

    raise ValueError(f"Unsupported file type: {file_path}")

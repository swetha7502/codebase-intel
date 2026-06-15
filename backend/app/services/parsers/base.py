"""
Shared data structures returned by every language parser
(Python AST, tree-sitter, generic fallback). Keeping these
language-agnostic is what lets the ingestion pipeline,
embedding service, and dependency graph treat all languages
the same way.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ParsedSymbol:
    name: str
    qualified_name: str
    kind: str  # function | class | method | module
    line_start: int
    line_end: int
    docstring: Optional[str]
    source_code: str
    extra: dict = field(default_factory=dict)


@dataclass
class ParsedImport:
    import_statement: str
    module_name: str  # Python: dotted module path. JS/TS: raw import specifier (e.g. "./utils").


@dataclass
class ParsedFile:
    path: str           # relative path, forward slashes
    language: str
    size_bytes: int
    line_count: int
    symbols: list[ParsedSymbol]
    imports: list[ParsedImport]
    error: Optional[str] = None

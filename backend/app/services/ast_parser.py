"""
AST-based code parser for Python repositories.
Extracts functions, classes, methods, imports, and their relationships.
"""
import ast
import os
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ParsedSymbol:
    name: str
    qualified_name: str
    kind: str  # function | class | method
    line_start: int
    line_end: int
    docstring: Optional[str]
    source_code: str
    extra: dict = field(default_factory=dict)


@dataclass
class ParsedImport:
    import_statement: str
    module_name: str


@dataclass
class ParsedFile:
    path: str           # relative path
    language: str
    size_bytes: int
    line_count: int
    symbols: list[ParsedSymbol]
    imports: list[ParsedImport]
    error: Optional[str] = None


class PythonASTParser:
    """
    Parses a single Python file using the `ast` module.
    Extracts top-level functions, classes, and methods with their full source.
    """

    def parse(self, file_path: str, repo_root: str) -> ParsedFile:
        relative_path = os.path.relpath(file_path, repo_root)
        size_bytes = os.path.getsize(file_path)

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                source = f.read()
        except Exception as e:
            return ParsedFile(
                path=relative_path, language="python",
                size_bytes=size_bytes, line_count=0,
                symbols=[], imports=[], error=str(e)
            )

        lines = source.splitlines()
        line_count = len(lines)

        try:
            tree = ast.parse(source, filename=file_path)
        except SyntaxError as e:
            return ParsedFile(
                path=relative_path, language="python",
                size_bytes=size_bytes, line_count=line_count,
                symbols=[], imports=[], error=f"SyntaxError: {e}"
            )

        symbols = self._extract_symbols(tree, lines, source)
        imports = self._extract_imports(tree, source)

        return ParsedFile(
            path=relative_path, language="python",
            size_bytes=size_bytes, line_count=line_count,
            symbols=symbols, imports=imports,
        )

    def _extract_symbols(self, tree: ast.AST, lines: list[str], source: str) -> list[ParsedSymbol]:
        symbols = []
        source_lines = source.splitlines()

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Determine if top-level or method inside a class
                kind = "function"
                qualified_name = node.name
                for parent in ast.walk(tree):
                    if isinstance(parent, ast.ClassDef):
                        for child in ast.walk(parent):
                            if child is node:
                                kind = "method"
                                qualified_name = f"{parent.name}.{node.name}"
                                break

                symbol_source = self._extract_node_source(node, source_lines)
                docstring = ast.get_docstring(node)
                args = [arg.arg for arg in node.args.args]
                decorators = [ast.unparse(d) for d in node.decorator_list]

                symbols.append(ParsedSymbol(
                    name=node.name,
                    qualified_name=qualified_name,
                    kind=kind,
                    line_start=node.lineno,
                    line_end=node.end_lineno or node.lineno,
                    docstring=docstring,
                    source_code=symbol_source,
                    extra={"args": args, "decorators": decorators, "is_async": isinstance(node, ast.AsyncFunctionDef)},
                ))

            elif isinstance(node, ast.ClassDef):
                # Only add the class itself (not its methods again)
                symbol_source = self._extract_node_source(node, source_lines)
                docstring = ast.get_docstring(node)
                bases = [ast.unparse(b) for b in node.bases]

                symbols.append(ParsedSymbol(
                    name=node.name,
                    qualified_name=node.name,
                    kind="class",
                    line_start=node.lineno,
                    line_end=node.end_lineno or node.lineno,
                    docstring=docstring,
                    source_code=symbol_source,
                    extra={"bases": bases},
                ))

        return symbols

    def _extract_node_source(self, node: ast.AST, source_lines: list[str]) -> str:
        start = node.lineno - 1
        end = node.end_lineno if node.end_lineno else node.lineno
        chunk = source_lines[start:end]
        return textwrap.dedent("\n".join(chunk))

    def _extract_imports(self, tree: ast.AST, source: str) -> list[ParsedImport]:
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(ParsedImport(
                        import_statement=ast.unparse(node),
                        module_name=alias.name,
                    ))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                imports.append(ParsedImport(
                    import_statement=ast.unparse(node),
                    module_name=module,
                ))
        return imports


class RepoWalker:
    """
    Walks a cloned repo and returns all parseable source files.
    Skips common noise: venvs, node_modules, build artifacts, hidden dirs.
    """

    SKIP_DIRS = {
        ".git", ".github", "__pycache__", "node_modules", ".venv", "venv",
        "env", ".env", "dist", "build", ".next", ".nuxt", "coverage",
        ".pytest_cache", ".mypy_cache", "eggs", ".eggs", "site-packages",
    }
    SUPPORTED_EXTENSIONS = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "javascript",
        ".tsx": "typescript",
    }

    def walk(self, repo_root: str) -> list[str]:
        """Returns list of absolute paths to parseable files."""
        result = []
        for dirpath, dirnames, filenames in os.walk(repo_root):
            # Prune skip dirs in-place so os.walk doesn't descend into them
            dirnames[:] = [d for d in dirnames if d not in self.SKIP_DIRS]
            for filename in filenames:
                ext = Path(filename).suffix.lower()
                if ext in self.SUPPORTED_EXTENSIONS:
                    result.append(os.path.join(dirpath, filename))
        return result

    def get_language(self, file_path: str) -> str:
        ext = Path(file_path).suffix.lower()
        return self.SUPPORTED_EXTENSIONS.get(ext, "unknown")

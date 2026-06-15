"""
AST-based parser for Python files using the stdlib `ast` module.
Extracts top-level functions, classes, methods, docstrings, and imports.
"""
import ast
import os
import textwrap

from app.services.parsers.base import ParsedFile, ParsedImport, ParsedSymbol


class PythonASTParser:

    def parse(self, file_path: str, repo_root: str) -> ParsedFile:
        relative_path = os.path.relpath(file_path, repo_root).replace("\\", "/")
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

        symbols = self._extract_symbols(tree, source)
        imports = self._extract_imports(tree)

        return ParsedFile(
            path=relative_path, language="python",
            size_bytes=size_bytes, line_count=line_count,
            symbols=symbols, imports=imports,
        )

    def _extract_symbols(self, tree: ast.AST, source: str) -> list[ParsedSymbol]:
        symbols = []
        source_lines = source.splitlines()

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
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

    def _extract_imports(self, tree: ast.AST) -> list[ParsedImport]:
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

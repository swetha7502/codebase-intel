"""
Tree-sitter based parser for JavaScript, TypeScript, and TSX.

Extracts top-level functions (declarations and arrow functions assigned
to const/let), classes with their methods, and import/re-export
statements — returning the same ParsedFile/ParsedSymbol/ParsedImport
shapes as the Python parser so the rest of the pipeline is
language-agnostic.

tree-sitter-languages ships prebuilt grammars, so no compiler is needed
at install time.
"""
import os
import textwrap
from typing import Optional

from tree_sitter_languages import get_parser

from app.services.parsers.base import ParsedFile, ParsedImport, ParsedSymbol

# Our internal language label -> tree-sitter grammar name
GRAMMAR_MAP = {
    "javascript": "javascript",
    "typescript": "typescript",
    "tsx": "tsx",
}

FUNCTION_NODE_TYPES = {"function_declaration", "generator_function_declaration"}
METHOD_NODE_TYPES = {"method_definition"}
CLASS_NODE_TYPES = {"class_declaration"}
ARROW_VALUE_TYPES = {"arrow_function", "function_expression", "generator_function"}


class TreeSitterParser:

    def __init__(self, language: str):
        self.language = language
        grammar = GRAMMAR_MAP.get(language, "javascript")
        self.parser = get_parser(grammar)

    def parse(self, file_path: str, repo_root: str) -> ParsedFile:
        relative_path = os.path.relpath(file_path, repo_root).replace("\\", "/")
        size_bytes = os.path.getsize(file_path)

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                source = f.read()
        except Exception as e:
            return ParsedFile(path=relative_path, language=self.language,
                               size_bytes=size_bytes, line_count=0,
                               symbols=[], imports=[], error=str(e))

        source_bytes = source.encode("utf-8")
        lines = source.splitlines()
        line_count = len(lines)

        try:
            tree = self.parser.parse(source_bytes)
        except Exception as e:
            return ParsedFile(path=relative_path, language=self.language,
                               size_bytes=size_bytes, line_count=line_count,
                               symbols=[], imports=[], error=str(e))

        symbols = self._extract_symbols(tree.root_node, lines, source_bytes)
        imports = self._extract_imports(tree.root_node, source_bytes)

        return ParsedFile(path=relative_path, language=self.language,
                           size_bytes=size_bytes, line_count=line_count,
                           symbols=symbols, imports=imports)

    # ── helpers ──────────────────────────────────────────────────────────

    def _node_text(self, node, source_bytes: bytes) -> str:
        return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")

    def _extract_source(self, node, lines: list[str]) -> str:
        start = node.start_point[0]
        end = node.end_point[0] + 1
        return textwrap.dedent("\n".join(lines[start:end]))

    def _span_node(self, node):
        """If this declaration is wrapped in `export ...`, include the
        export keyword in the source span by returning the parent node."""
        if node.parent is not None and node.parent.type == "export_statement":
            return node.parent
        return node

    def _leading_comment(self, node, source_bytes: bytes) -> Optional[str]:
        """Look for a JSDoc/line comment immediately preceding this node
        or its enclosing `export` statement."""
        candidates = [node]
        if node.parent is not None and node.parent.type == "export_statement":
            candidates.append(node.parent)

        for n in candidates:
            prev = n.prev_sibling
            if prev and prev.type == "comment":
                text = self._node_text(prev, source_bytes).strip()
                if text.startswith("/*"):
                    text = text[2:]
                    if text.endswith("*/"):
                        text = text[:-2]
                    cleaned = [line.strip().lstrip("*").strip() for line in text.splitlines()]
                    result = "\n".join(line for line in cleaned if line).strip()
                    return result or None
                if text.startswith("//"):
                    return text.lstrip("/").strip()
        return None

    def _find_enclosing_class_name(self, node, source_bytes: bytes) -> Optional[str]:
        parent = node.parent
        while parent is not None:
            if parent.type in CLASS_NODE_TYPES:
                name_node = parent.child_by_field_name("name")
                if name_node:
                    return self._node_text(name_node, source_bytes)
                return None
            parent = parent.parent
        return None

    # ── symbol extraction ───────────────────────────────────────────────

    def _extract_symbols(self, root, lines: list[str], source_bytes: bytes) -> list[ParsedSymbol]:
        symbols: list[ParsedSymbol] = []

        def visit(node):
            node_type = node.type

            if node_type in FUNCTION_NODE_TYPES:
                name_node = node.child_by_field_name("name")
                name = self._node_text(name_node, source_bytes) if name_node else "<anonymous>"
                span = self._span_node(node)
                header = self._node_text(node, source_bytes).split("{")[0]
                symbols.append(ParsedSymbol(
                    name=name,
                    qualified_name=name,
                    kind="function",
                    line_start=span.start_point[0] + 1,
                    line_end=span.end_point[0] + 1,
                    docstring=self._leading_comment(node, source_bytes),
                    source_code=self._extract_source(span, lines),
                    extra={"is_async": "async" in header},
                ))

            elif node_type in CLASS_NODE_TYPES:
                name_node = node.child_by_field_name("name")
                name = self._node_text(name_node, source_bytes) if name_node else "<anonymous>"
                span = self._span_node(node)
                symbols.append(ParsedSymbol(
                    name=name,
                    qualified_name=name,
                    kind="class",
                    line_start=span.start_point[0] + 1,
                    line_end=span.end_point[0] + 1,
                    docstring=self._leading_comment(node, source_bytes),
                    source_code=self._extract_source(span, lines),
                    extra={},
                ))

            elif node_type in METHOD_NODE_TYPES:
                name_node = node.child_by_field_name("name")
                name = self._node_text(name_node, source_bytes) if name_node else "<anonymous>"
                class_name = self._find_enclosing_class_name(node, source_bytes)
                qualified = f"{class_name}.{name}" if class_name else name
                header = self._node_text(node, source_bytes).split("{")[0]
                symbols.append(ParsedSymbol(
                    name=name,
                    qualified_name=qualified,
                    kind="method",
                    line_start=node.start_point[0] + 1,
                    line_end=node.end_point[0] + 1,
                    docstring=self._leading_comment(node, source_bytes),
                    source_code=self._extract_source(node, lines),
                    extra={"is_async": "async" in header},
                ))

            elif node_type == "variable_declarator":
                value = node.child_by_field_name("value")
                if value is not None and value.type in ARROW_VALUE_TYPES:
                    name_node = node.child_by_field_name("name")
                    name = self._node_text(name_node, source_bytes) if name_node else "<anonymous>"

                    # Walk up through `const x = ...` to `export const x = ...`
                    span = node
                    if span.parent is not None and span.parent.type in ("variable_declaration", "lexical_declaration"):
                        span = span.parent
                    span = self._span_node(span)

                    symbols.append(ParsedSymbol(
                        name=name,
                        qualified_name=name,
                        kind="function",
                        line_start=span.start_point[0] + 1,
                        line_end=span.end_point[0] + 1,
                        docstring=self._leading_comment(span, source_bytes),
                        source_code=self._extract_source(span, lines),
                        extra={"is_arrow": value.type == "arrow_function"},
                    ))
                    # Don't recurse into the function body — avoids treating
                    # nested helper closures as top-level symbols.
                    return

            for child in node.children:
                visit(child)

        visit(root)
        return symbols

    # ── import extraction ───────────────────────────────────────────────

    def _extract_imports(self, root, source_bytes: bytes) -> list[ParsedImport]:
        imports: list[ParsedImport] = []

        def visit(node):
            if node.type in ("import_statement", "export_statement"):
                source_node = node.child_by_field_name("source")
                if source_node is not None and source_node.type == "string":
                    raw = self._node_text(source_node, source_bytes)
                    module = raw.strip("'\"")
                    imports.append(ParsedImport(
                        import_statement=self._node_text(node, source_bytes).strip(),
                        module_name=module,
                    ))
                    # Nothing else of interest inside an import/re-export statement.
                    return

            elif node.type == "call_expression":
                fn = node.child_by_field_name("function")
                if fn is not None and self._node_text(fn, source_bytes) == "require":
                    args = node.child_by_field_name("arguments")
                    if args is not None and args.named_child_count > 0:
                        first = args.named_children[0]
                        if first.type == "string":
                            raw = self._node_text(first, source_bytes)
                            module = raw.strip("'\"")
                            imports.append(ParsedImport(
                                import_statement=self._node_text(node, source_bytes).strip(),
                                module_name=module,
                            ))

            for child in node.children:
                visit(child)

        visit(root)
        return imports

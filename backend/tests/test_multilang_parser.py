"""
Tests for the multi-language parser dispatcher: tree-sitter (JS/TS/TSX)
on top of the existing Python AST parser.
"""
import pytest

from app.services.dependency_resolver import resolve_js_dependency
from app.services.parsers.dispatcher import get_language_and_kind, is_supported, parse_file

TSX_COMPONENT = '''import React from "react";
import { helper } from "./utils";

/** A reusable button component. */
export function Button({ label }: { label: string }) {
  return <button>{label}</button>;
}

export const SecondaryButton = ({ label }: { label: string }) => {
  return <button className="secondary">{label}</button>;
};

export class ButtonGroup {
  private items: string[] = [];

  /** Add an item */
  add(item: string) {
    this.items.push(item);
  }
}
'''


@pytest.fixture
def tsx_file(tmp_path):
    f = tmp_path / "Button.tsx"
    f.write_text(TSX_COMPONENT)
    return str(f), str(tmp_path)


def test_dispatcher_routes_extensions():
    assert get_language_and_kind("src/App.tsx") == ("tsx", "treesitter")
    assert get_language_and_kind("src/api.ts") == ("typescript", "treesitter")
    assert get_language_and_kind("src/index.js") == ("javascript", "treesitter")
    assert get_language_and_kind("app/main.py") == ("python", "python")
    assert get_language_and_kind("package.json") == ("unknown", "unsupported")
    assert get_language_and_kind("README.md") == ("unknown", "unsupported")
    assert get_language_and_kind("noext") == ("unknown", "unsupported")


def test_is_supported():
    assert is_supported("app/main.py")
    assert is_supported("src/App.tsx")
    assert is_supported("src/index.jsx")
    assert not is_supported("README.md")
    assert not is_supported("package.json")
    assert not is_supported("image.png")
    assert not is_supported("binary.exe")


def test_tsx_extracts_function_and_docstring(tsx_file):
    file_path, repo_root = tsx_file
    parsed = parse_file(file_path, repo_root)

    assert parsed.error is None
    assert parsed.language == "tsx"

    func = next(s for s in parsed.symbols if s.qualified_name == "Button")
    assert func.kind == "function"
    assert func.docstring == "A reusable button component."
    assert "export function Button" in func.source_code


def test_tsx_extracts_arrow_function(tsx_file):
    file_path, repo_root = tsx_file
    parsed = parse_file(file_path, repo_root)

    arrow = next(s for s in parsed.symbols if s.qualified_name == "SecondaryButton")
    assert arrow.kind == "function"
    assert arrow.extra.get("is_arrow") is True
    assert "export const SecondaryButton" in arrow.source_code


def test_tsx_extracts_class_and_method(tsx_file):
    file_path, repo_root = tsx_file
    parsed = parse_file(file_path, repo_root)

    names = {s.qualified_name for s in parsed.symbols}
    assert "ButtonGroup" in names
    assert "ButtonGroup.add" in names

    method = next(s for s in parsed.symbols if s.qualified_name == "ButtonGroup.add")
    assert method.kind == "method"
    assert method.docstring == "Add an item"


def test_tsx_extracts_imports(tsx_file):
    file_path, repo_root = tsx_file
    parsed = parse_file(file_path, repo_root)

    modules = {imp.module_name for imp in parsed.imports}
    assert "react" in modules
    assert "./utils" in modules


# ── JS/TS dependency resolution ─────────────────────────────────────────────

def test_resolve_relative_import_with_extension_lookup():
    all_paths = ["src/App.tsx", "src/components/Button.tsx"]
    result = resolve_js_dependency("./components/Button", "src/App.tsx", all_paths)
    assert result == "src/components/Button.tsx"


def test_resolve_alias_import():
    all_paths = ["src/App.tsx", "src/lib/api.ts"]
    result = resolve_js_dependency("@/lib/api", "src/App.tsx", all_paths)
    assert result == "src/lib/api.ts"


def test_resolve_index_file():
    all_paths = ["src/App.tsx", "src/components/index.ts"]
    result = resolve_js_dependency("./components", "src/App.tsx", all_paths)
    assert result == "src/components/index.ts"


def test_resolve_external_package_returns_none():
    all_paths = ["src/App.tsx"]
    assert resolve_js_dependency("react", "src/App.tsx", all_paths) is None
    assert resolve_js_dependency("next/navigation", "src/App.tsx", all_paths) is None

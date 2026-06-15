# Codebase Intel — Multi-language (Python + JS/TS/JSX/TSX) update

This zip contains ONLY the new/changed files. The folder structure
mirrors your project root — extract and copy these into
C:\Users\Swetha\Desktop\codebase-intel, overwriting existing files.

## NEW files (create these):
- backend/app/services/parsers/__init__.py        (empty)
- backend/app/services/parsers/base.py
- backend/app/services/parsers/python_parser.py
- backend/app/services/parsers/treesitter_parser.py
- backend/app/services/parsers/dispatcher.py
- backend/app/services/parsers/repo_walker.py
- backend/tests/test_multilang_parser.py

## MODIFIED files (overwrite existing):
- backend/app/services/ast_parser.py        -> now a backward-compat shim
- backend/app/services/dependency_resolver.py -> adds JS/TS import resolution
- backend/app/services/embedding_service.py -> 1-line import path fix
- backend/app/tasks/ingestion.py            -> uses new multi-language dispatcher
- backend/app/main.py                       -> fixes pre-existing `settings` bug
- backend/requirements.txt                  -> adds tree-sitter deps
- frontend/src/components/graph/DependencyGraphView.tsx -> language colors/legend
- frontend/src/components/search/SearchPanel.tsx        -> dynamic Monaco language

## Setup steps after copying files:

1. Activate your venv:
   venv\Scripts\activate

2. Install new dependencies:
   pip install -r requirements.txt
   (adds tree-sitter==0.21.3 and tree-sitter-languages==1.10.2 — pinned
   together on purpose, newer tree-sitter breaks tree-sitter-languages)

3. Restart your backend + Celery worker.

4. Delete and re-ingest a repo that has a TS/TSX frontend (e.g. your
   Medical Research Agent repo) — you should now see .tsx/.ts/.js files
   as nodes in the dependency graph, with edges for relative imports
   (./components/Button) and @/ alias imports (@/lib/api).

5. Run tests to confirm everything's wired up:
   cd backend
   pytest tests/ -q
   ruff check app tests --config ruff.toml
   (should show 19 passed, "All checks passed!")

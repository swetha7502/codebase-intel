"""
Celery task: orchestrates the full repo ingestion pipeline.
Publishes progress events to Redis for WebSocket streaming.

Supports any file type the parser dispatcher knows about:
  - Python: full AST symbol + import extraction
  - JS/TS/TSX: tree-sitter symbol + import extraction
  - Everything else: recorded as a graph node + embedded as a single
    "module" chunk for semantic search, but with no extracted symbols
    or import edges.
"""
import json

from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.redis_client import get_redis_client
from app.models.models import CodeFile, CodeSymbol, ImportDependency, IngestionStatus, Repository, SymbolKind
from app.services.dependency_resolver import resolve_dependency
from app.services.embedding_service import embed_symbols
from app.services.github_service import clone_repo
from app.services.parsers.dispatcher import parse_file
from app.services.parsers.repo_walker import RepoWalker

settings = get_settings()


def publish_progress(redis_client, repo_id: str, stage: str, message: str, pct: int):
    """Push a progress event to Redis so the WebSocket handler can forward it."""
    payload = json.dumps({"stage": stage, "message": message, "percent": pct})
    redis_client.publish(f"ingestion:{repo_id}", payload)


SYMBOL_KIND_MAP = {
    "function": SymbolKind.FUNCTION,
    "class": SymbolKind.CLASS,
    "method": SymbolKind.METHOD,
    "module": SymbolKind.MODULE,
}


@celery_app.task(bind=True, name="tasks.ingest_repository")
def ingest_repository(self, repository_id: str):
    db: Session = SessionLocal()
    r = get_redis_client()

    def progress(stage: str, message: str, pct: int):
        publish_progress(r, repository_id, stage, message, pct)

    try:
        repo = db.query(Repository).filter(Repository.id == repository_id).first()
        if not repo:
            return {"error": "Repository not found"}

        # ── Stage 1: Clone ────────────────────────────────────────────────
        repo.status = IngestionStatus.CLONING
        db.commit()
        progress("cloning", f"Cloning {repo.github_url}…", 5)

        local_path = clone_repo(repo.github_url, repo.owner, repo.name)
        progress("cloning", "Clone complete", 15)

        # ── Stage 2: Walk + Parse ─────────────────────────────────────────
        repo.status = IngestionStatus.PARSING
        db.commit()
        progress("parsing", "Walking file tree…", 20)

        walker = RepoWalker()
        file_paths = walker.walk(local_path)
        progress("parsing", f"Found {len(file_paths)} source files, parsing…", 25)

        all_symbols_with_paths = []   # (ParsedSymbol, normalized_path, CodeFile.id)
        file_id_map = {}              # normalized_path (forward slashes) -> CodeFile.id
        file_imports_map = {}         # normalized_path -> list[ParsedImport]
        file_language_map = {}        # normalized_path -> language label

        for i, fp in enumerate(file_paths):
            parsed = parse_file(fp, local_path)
            if parsed.error:
                continue

            # parse_file already normalizes to forward slashes, but be defensive
            normalized_path = parsed.path.replace("\\", "/")

            cf = CodeFile(
                repository_id=repository_id,
                path=normalized_path,
                language=parsed.language,
                size_bytes=parsed.size_bytes,
                line_count=parsed.line_count,
            )
            db.add(cf)
            db.flush()  # get cf.id without full commit
            file_id_map[normalized_path] = cf.id
            file_imports_map[normalized_path] = parsed.imports
            file_language_map[normalized_path] = parsed.language

            for sym in parsed.symbols:
                cs = CodeSymbol(
                    repository_id=repository_id,
                    file_id=cf.id,
                    name=sym.name,
                    qualified_name=sym.qualified_name,
                    kind=SYMBOL_KIND_MAP.get(sym.kind, SymbolKind.FUNCTION),
                    line_start=sym.line_start,
                    line_end=sym.line_end,
                    docstring=sym.docstring,
                    source_code=sym.source_code,
                    extra=sym.extra,
                )
                db.add(cs)
                all_symbols_with_paths.append((sym, normalized_path, cf.id))

            if i % 50 == 0:
                pct = 25 + int((i / len(file_paths)) * 25)
                progress("parsing", f"Parsed {i}/{len(file_paths)} files…", pct)

        db.commit()

        # ── Stage 3: Dependency graph ─────────────────────────────────────
        progress("parsing", "Building dependency graph…", 52)

        all_paths = list(file_id_map.keys())

        for source_path, imports in file_imports_map.items():
            source_id = file_id_map.get(source_path)
            if not source_id:
                continue
            language = file_language_map.get(source_path, "unknown")

            for imp in imports:
                target_path = resolve_dependency(imp.module_name, source_path, all_paths, language)
                target_id = file_id_map.get(target_path) if target_path else None

                dep = ImportDependency(
                    repository_id=repository_id,
                    source_file_id=source_id,
                    target_file_id=target_id,
                    import_statement=imp.import_statement,
                    module_name=imp.module_name,
                    is_internal=target_id is not None,
                )
                db.add(dep)

        db.commit()
        progress("parsing", "Dependency graph complete", 60)

        # ── Stage 4: Embed ────────────────────────────────────────────────
        repo.status = IngestionStatus.EMBEDDING
        db.commit()
        progress("embedding", f"Embedding {len(all_symbols_with_paths)} symbols…", 65)

        sym_path_pairs = [(s, p) for s, p, _ in all_symbols_with_paths]
        id_map = embed_symbols(repository_id, sym_path_pairs)

        # Write chroma_ids back to DB
        for sym, path, file_id in all_symbols_with_paths:
            chroma_id = id_map.get(sym.qualified_name)
            if chroma_id:
                db.query(CodeSymbol).filter(
                    CodeSymbol.repository_id == repository_id,
                    CodeSymbol.qualified_name == sym.qualified_name,
                    CodeSymbol.file_id == file_id,
                ).update({"chroma_id": chroma_id})

        db.commit()
        progress("embedding", "Embeddings stored", 90)

        # ── Stage 5: Finalize ─────────────────────────────────────────────
        total_files = db.query(CodeFile).filter(CodeFile.repository_id == repository_id).count()
        total_symbols = db.query(CodeSymbol).filter(CodeSymbol.repository_id == repository_id).count()
        total_classes = db.query(CodeSymbol).filter(
            CodeSymbol.repository_id == repository_id,
            CodeSymbol.kind == SymbolKind.CLASS,
        ).count()

        repo.status = IngestionStatus.COMPLETE
        repo.file_count = total_files
        repo.function_count = total_symbols - total_classes
        repo.class_count = total_classes
        db.commit()

        progress("complete", f"Done! Indexed {total_files} files, {total_symbols} symbols.", 100)
        return {"status": "complete", "files": total_files, "symbols": total_symbols}

    except Exception as e:
        db.rollback()
        repo = db.query(Repository).filter(Repository.id == repository_id).first()
        if repo:
            repo.status = IngestionStatus.FAILED
            repo.error_message = str(e)
            db.commit()
        publish_progress(r, repository_id, "failed", str(e), 0)
        raise

    finally:
        db.close()
        r.close()

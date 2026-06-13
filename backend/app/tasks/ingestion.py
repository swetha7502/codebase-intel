"""
Celery task: orchestrates the full repo ingestion pipeline.
Publishes progress events to Redis for WebSocket streaming.
"""
import json
import redis as redis_lib

from celery import current_task
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.models import Repository, CodeFile, CodeSymbol, ImportDependency, IngestionStatus, SymbolKind
from app.services.ast_parser import PythonASTParser, RepoWalker
from app.services.github_service import clone_repo, fetch_repo_metadata
from app.services.embedding_service import embed_symbols
from app.services.dependency_resolver import resolve_internal_dependency

settings = get_settings()


def publish_progress(redis_client, repo_id: str, stage: str, message: str, pct: int):
    """Push a progress event to Redis so the WebSocket handler can forward it."""
    payload = json.dumps({"stage": stage, "message": message, "percent": pct})
    redis_client.publish(f"ingestion:{repo_id}", payload)


@celery_app.task(bind=True, name="tasks.ingest_repository")
def ingest_repository(self, repository_id: str):
    db: Session = SessionLocal()
    r = redis_lib.from_url(settings.redis_url)

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
        progress("parsing", f"Found {len(file_paths)} source files, parsing AST…", 25)

        parser = PythonASTParser()
        all_symbols_with_paths = []
        file_id_map = {}   # relative_path -> CodeFile.id

        for i, fp in enumerate(file_paths):
            parsed = parser.parse(fp, local_path)
            if parsed.error:
                continue

            cf = CodeFile(
                repository_id=repository_id,
                path=parsed.path,
                language=parsed.language,
                size_bytes=parsed.size_bytes,
                line_count=parsed.line_count,
            )
            db.add(cf)
            db.flush()  # get cf.id without full commit
            file_id_map[parsed.path] = cf.id

            for sym in parsed.symbols:
                kind_map = {"function": SymbolKind.FUNCTION, "class": SymbolKind.CLASS,
                            "method": SymbolKind.METHOD, "module": SymbolKind.MODULE}
                cs = CodeSymbol(
                    repository_id=repository_id,
                    file_id=cf.id,
                    name=sym.name,
                    qualified_name=sym.qualified_name,
                    kind=kind_map.get(sym.kind, SymbolKind.FUNCTION),
                    line_start=sym.line_start,
                    line_end=sym.line_end,
                    docstring=sym.docstring,
                    source_code=sym.source_code,
                    extra=sym.extra,
                )
                db.add(cs)
                all_symbols_with_paths.append((sym, parsed.path, cf.id))

            # Store imports temporarily for dependency resolution
            cf._parsed_imports = parsed.imports

            if i % 50 == 0:
                pct = 25 + int((i / len(file_paths)) * 25)
                progress("parsing", f"Parsed {i}/{len(file_paths)} files…", pct)

        db.commit()

        # ── Stage 3: Dependency graph ─────────────────────────────────────
        progress("parsing", "Building dependency graph…", 52)

        for fp in file_paths:
            parsed = parser.parse(fp, local_path)
            if parsed.error or not hasattr(parsed, '_parsed_imports'):
                continue
            source_relative = parsed.path
            source_id = file_id_map.get(source_relative)
            if not source_id:
                continue

            for imp in parsed.imports:
                target_path = resolve_internal_dependency(
                    imp.module_name, source_relative, list(file_id_map.keys())
                )
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

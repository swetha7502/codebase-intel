import enum
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class IngestionStatus(str, enum.Enum):
    PENDING = "pending"
    CLONING = "cloning"
    PARSING = "parsing"
    EMBEDDING = "embedding"
    COMPLETE = "complete"
    FAILED = "failed"


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    github_url = Column(String(500), nullable=False, unique=True)
    owner = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    default_branch = Column(String(100), default="main")
    description = Column(Text, nullable=True)
    language = Column(String(100), nullable=True)
    star_count = Column(Integer, default=0)
    status = Column(SAEnum(IngestionStatus), default=IngestionStatus.PENDING)
    celery_task_id = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    file_count = Column(Integer, default=0)
    function_count = Column(Integer, default=0)
    class_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    files = relationship("CodeFile", back_populates="repository", cascade="all, delete-orphan")
    symbols = relationship("CodeSymbol", back_populates="repository", cascade="all, delete-orphan")


class CodeFile(Base):
    __tablename__ = "code_files"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    repository_id = Column(UUID(as_uuid=False), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    path = Column(String(1000), nullable=False)
    language = Column(String(50), nullable=True)
    size_bytes = Column(Integer, default=0)
    line_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    repository = relationship("Repository", back_populates="files")
    symbols = relationship("CodeSymbol", back_populates="file", cascade="all, delete-orphan")
    imports = relationship("ImportDependency", foreign_keys="ImportDependency.source_file_id",
                           back_populates="source_file", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("repository_id", "path", name="uq_repo_file_path"),
        Index("ix_code_files_repo_id", "repository_id"),
    )


class SymbolKind(str, enum.Enum):
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    MODULE = "module"


class CodeSymbol(Base):
    """A function, class, or method extracted by the AST/tree-sitter parser."""
    __tablename__ = "code_symbols"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    repository_id = Column(UUID(as_uuid=False), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    file_id = Column(UUID(as_uuid=False), ForeignKey("code_files.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(500), nullable=False)
    qualified_name = Column(String(1000), nullable=True)
    kind = Column(SAEnum(SymbolKind), nullable=False)
    line_start = Column(Integer, nullable=True)
    line_end = Column(Integer, nullable=True)
    docstring = Column(Text, nullable=True)
    source_code = Column(Text, nullable=True)
    # pgvector embedding column: 1536 dims = text-embedding-3-small output size
    embedding = Column(Vector(1536), nullable=True)
    extra = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)

    repository = relationship("Repository", back_populates="symbols")
    file = relationship("CodeFile", back_populates="symbols")

    __table_args__ = (
        Index("ix_code_symbols_repo_id", "repository_id"),
        Index("ix_code_symbols_file_id", "file_id"),
        Index("ix_code_symbols_kind", "kind"),
    )


class ImportDependency(Base):
    """
    Directed edge: source_file imports something from target_file.
    Used to build the dependency graph with recursive CTEs.
    """
    __tablename__ = "import_dependencies"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    repository_id = Column(UUID(as_uuid=False), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    source_file_id = Column(UUID(as_uuid=False), ForeignKey("code_files.id", ondelete="CASCADE"), nullable=False)
    target_file_id = Column(UUID(as_uuid=False), ForeignKey("code_files.id", ondelete="CASCADE"), nullable=True)
    import_statement = Column(String(500), nullable=False)
    module_name = Column(String(500), nullable=False)
    is_internal = Column(Boolean, default=False)

    source_file = relationship("CodeFile", foreign_keys=[source_file_id], back_populates="imports")
    target_file = relationship("CodeFile", foreign_keys=[target_file_id])

    __table_args__ = (
        Index("ix_import_deps_source", "source_file_id"),
        Index("ix_import_deps_target", "target_file_id"),
        Index("ix_import_deps_repo", "repository_id"),
    )

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database import Base


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(
        String(120),
        unique=True,
        index=True,
    )
    domain: Mapped[str] = mapped_column(String(32), index=True)
    sensitivity: Mapped[str] = mapped_column(
        String(32),
        default="internal",
    )
    is_public: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
    )

    permissions: Mapped[list[KnowledgePermission]] = relationship(
        back_populates="knowledge_base",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    documents: Mapped[list[Document]] = relationship(
        back_populates="knowledge_base",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class KnowledgePermission(Base):
    __tablename__ = "knowledge_permissions"
    __table_args__ = (
        UniqueConstraint(
            "knowledge_base_id",
            "subject_type",
            "subject_value",
            name="uq_knowledge_permission_subject",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    knowledge_base_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        index=True,
    )
    subject_type: Mapped[str] = mapped_column(String(16))
    subject_value: Mapped[str] = mapped_column(String(64))

    knowledge_base: Mapped[KnowledgeBase] = relationship(
        back_populates="permissions",
    )


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint(
            "knowledge_base_id",
            "sha256",
            name="uq_document_kb_sha256",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    knowledge_base_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(String(500))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(
        String(32),
        default="PROCESSING",
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    sensitivity: Mapped[str] = mapped_column(
        String(32),
        default="internal",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    knowledge_base: Mapped[KnowledgeBase] = relationship(
        back_populates="documents",
        lazy="selectin",
    )

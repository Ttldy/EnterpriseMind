from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.shared.database import Base


class PromptVersion(Base):
    __tablename__ = "prompt_versions"
    __table_args__ = (
        UniqueConstraint(
            "prompt_key",
            "version",
            name="uq_prompt_key_version",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True
    )
    prompt_key: Mapped[str] = mapped_column(
        String(64),
        index=True,
    )
    version: Mapped[int]
    content: Mapped[str] = mapped_column(Text)
    content_sha256: Mapped[str] = mapped_column(
        String(64),
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        index=True,
    )
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    evaluation_runs: Mapped[
        list[EvaluationRun]
    ] = relationship(
        back_populates="prompt_version",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )
    prompt_version_id: Mapped[int] = (
        mapped_column(
            ForeignKey(
                "prompt_versions.id",
                ondelete="CASCADE",
            ),
            index=True,
        )
    )
    status: Mapped[str] = mapped_column(
        String(24),
        default="RUNNING",
    )
    model_name: Mapped[str] = mapped_column(
        String(120)
    )
    dataset_sha256: Mapped[str] = mapped_column(
        String(64)
    )
    safety_pass_rate: Mapped[float] = (
        mapped_column(Float, default=0.0)
    )
    safety_passed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )
    metrics: Mapped[dict[str, float]] = (
        mapped_column(JSON, default=dict)
    )
    regressions: Mapped[list[str]] = (
        mapped_column(JSON, default=list)
    )
    case_results: Mapped[list[dict[str, object]]] = (
        mapped_column(JSON, default=list)
    )
    release_allowed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )
    duration_ms: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )
    error_message: Mapped[str | None] = (
        mapped_column(Text)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = (
        mapped_column(DateTime(timezone=True))
    )

    prompt_version: Mapped[PromptVersion] = (
        relationship(
            back_populates="evaluation_runs"
        )
    )
from __future__ import annotations

from sqlalchemy import (
    JSON,
    Boolean,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.shared.database import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(
        String(120),
        unique=True,
        index=True,
    )
    view_name: Mapped[str] = mapped_column(
        String(120),
        unique=True,
    )
    description: Mapped[str] = mapped_column(Text)
    schema_text: Mapped[str] = mapped_column(Text)
    sensitivity: Mapped[str] = mapped_column(
        String(32),
        default="sensitive",
    )
    allowed_columns: Mapped[list[str]] = mapped_column(JSON)
    keywords: Mapped[list[str]] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
    )

    permissions: Mapped[list[DatasetPermission]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class DatasetPermission(Base):
    __tablename__ = "dataset_permissions"
    __table_args__ = (
        UniqueConstraint(
            "dataset_id",
            "subject_type",
            "subject_value",
            name="uq_dataset_permission_subject",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(
        ForeignKey(
            "datasets.id",
            ondelete="CASCADE",
        ),
        index=True,
    )
    subject_type: Mapped[str] = mapped_column(String(16))
    subject_value: Mapped[str] = mapped_column(String(64))

    dataset: Mapped[Dataset] = relationship(back_populates="permissions")

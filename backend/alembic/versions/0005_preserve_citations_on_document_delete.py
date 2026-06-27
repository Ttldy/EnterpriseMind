"""Preserve citation snapshots when source documents are deleted."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0005_citation_set_null"
down_revision: str | None = "0004_stage4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "citations_document_id_fkey",
        "citations",
        type_="foreignkey",
    )
    op.alter_column(
        "citations",
        "document_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.create_foreign_key(
        "citations_document_id_fkey",
        "citations",
        "documents",
        ["document_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "citations_document_id_fkey",
        "citations",
        type_="foreignkey",
    )
    op.execute(
        "DELETE FROM citations WHERE document_id IS NULL"
    )
    op.alter_column(
        "citations",
        "document_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.create_foreign_key(
        "citations_document_id_fkey",
        "citations",
        "documents",
        ["document_id"],
        ["id"],
        ondelete="CASCADE",
    )


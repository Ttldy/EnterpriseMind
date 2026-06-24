from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0004_stage4"
down_revision: str | None = "0003_stage2"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "prompt_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "prompt_key",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "content",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "content_sha256",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column(
            "created_by",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "prompt_key",
            "version",
            name="uq_prompt_key_version",
        ),
    )
    op.create_index(
        "ix_prompt_versions_prompt_key",
        "prompt_versions",
        ["prompt_key"],
    )
    op.create_index(
        "ix_prompt_versions_content_sha256",
        "prompt_versions",
        ["content_sha256"],
    )
    op.create_index(
        "ix_prompt_versions_is_active",
        "prompt_versions",
        ["is_active"],
    )

    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "prompt_version_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=24),
            nullable=False,
        ),
        sa.Column(
            "model_name",
            sa.String(length=120),
            nullable=False,
        ),
        sa.Column(
            "dataset_sha256",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "safety_pass_rate",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "safety_passed",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "metrics",
            sa.JSON(),
            nullable=False,
        ),
        sa.Column(
            "regressions",
            sa.JSON(),
            nullable=False,
        ),
        sa.Column(
            "case_results",
            sa.JSON(),
            nullable=False,
        ),
        sa.Column(
            "release_allowed",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "duration_ms",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["prompt_version_id"],
            ["prompt_versions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_evaluation_runs_prompt_version_id",
        "evaluation_runs",
        ["prompt_version_id"],
    )

    op.add_column(
        "documents",
        sa.Column(
            "job_id",
            sa.String(length=255),
            nullable=True,
        ),
    )
    op.add_column(
        "documents",
        sa.Column(
            "attempts",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "documents",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_documents_job_id",
        "documents",
        ["job_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_documents_job_id",
        table_name="documents",
    )
    op.drop_column("documents", "updated_at")
    op.drop_column("documents", "attempts")
    op.drop_column("documents", "job_id")
    op.drop_index(
        "ix_evaluation_runs_prompt_version_id",
        table_name="evaluation_runs",
    )
    op.drop_table("evaluation_runs")
    op.drop_index(
        "ix_prompt_versions_is_active",
        table_name="prompt_versions",
    )
    op.drop_index(
        "ix_prompt_versions_content_sha256",
        table_name="prompt_versions",
    )
    op.drop_index(
        "ix_prompt_versions_prompt_key",
        table_name="prompt_versions",
    )
    op.drop_table("prompt_versions")
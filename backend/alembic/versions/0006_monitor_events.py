"""Add persisted runtime monitoring events."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0006_monitor_events"
down_revision: str | None = "0005_citation_set_null"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "monitor_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column("component", sa.String(length=64), nullable=False),
        sa.Column("operation", sa.String(length=96), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("agent", sa.String(length=64), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("model", sa.String(length=120), nullable=True),
        sa.Column(
            "timeout",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "cache_hit",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "fallback",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "circuit_open",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_monitor_events_trace_id",
        "monitor_events",
        ["trace_id"],
    )
    op.create_index(
        "ix_monitor_events_component",
        "monitor_events",
        ["component"],
    )
    op.create_index(
        "ix_monitor_events_created_at",
        "monitor_events",
        ["created_at"],
    )
    op.create_index(
        "ix_monitor_events_component_created_at",
        "monitor_events",
        ["component", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("monitor_events")


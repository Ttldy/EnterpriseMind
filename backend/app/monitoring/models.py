from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database import Base


class MonitorEventRecord(Base):
    __tablename__ = "monitor_events"
    __table_args__ = (
        Index(
            "ix_monitor_events_component_created_at",
            "component",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    trace_id: Mapped[str | None] = mapped_column(
        String(64),
        index=True,
    )
    component: Mapped[str] = mapped_column(
        String(64),
        index=True,
    )
    operation: Mapped[str] = mapped_column(String(96))
    success: Mapped[bool] = mapped_column(Boolean)
    latency_ms: Mapped[int] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(64))
    agent: Mapped[str | None] = mapped_column(String(64))
    provider: Mapped[str | None] = mapped_column(String(64))
    model: Mapped[str | None] = mapped_column(String(120))
    timeout: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
    )
    cache_hit: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
    )
    fallback: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
    )
    circuit_open: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        "metadata",
        JSON,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )


from datetime import datetime

from pydantic import BaseModel, Field


class MonitoringOverview(BaseModel):
    window_minutes: int
    overall_health_score: float | None
    overall_status: str
    total_events: int
    success_rate: float
    average_latency_ms: float
    p95_latency_ms: int
    timeout_rate: float
    fallback_rate: float
    circuit_open_rate: float
    reasons: list[str]
    penalties: dict[str, float]
    generated_at: datetime


class ComponentHealth(BaseModel):
    component: str
    event_count: int
    success_rate: float
    average_latency_ms: float
    p95_latency_ms: int
    timeout_rate: float
    fallback_rate: float
    circuit_open_rate: float
    health_score: float | None
    status: str
    reasons: list[str]
    penalties: dict[str, float]


class ComponentHealthResponse(BaseModel):
    window_minutes: int
    items: list[ComponentHealth]
    generated_at: datetime


class MonitoringEventItem(BaseModel):
    id: int
    trace_id: str | None
    component: str
    operation: str
    success: bool
    latency_ms: int
    error_code: str | None
    agent: str | None
    provider: str | None
    model: str | None
    timeout: bool
    cache_hit: bool
    fallback: bool
    circuit_open: bool
    metadata: dict[str, object]
    created_at: datetime


class MonitoringEventResponse(BaseModel):
    items: list[MonitoringEventItem]
    total: int
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)

from datetime import datetime

from pydantic import BaseModel


class TraceCitation(BaseModel):
    document_id: int | None
    filename: str
    page: int
    text: str
    score: float


class TraceListItem(BaseModel):
    trace_id: str
    created_at: datetime
    username: str
    conversation_id: int
    question: str
    answer_preview: str
    agent: str | None
    model: str | None
    citation_count: int


class TraceListResponse(BaseModel):
    items: list[TraceListItem]
    total: int
    limit: int
    offset: int


class TraceDetail(BaseModel):
    trace_id: str
    username: str
    conversation_id: int
    user_message: str
    assistant_message: str
    agent: str | None
    model: str | None
    citations: list[TraceCitation]
    created_at: datetime


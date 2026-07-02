import pytest

from app.knowledge.access import AccessContext
from app.knowledge.retrieval import RetrievalService
from app.knowledge.vector_store import VectorHit
from app.monitoring.contracts import MonitorEvent


class RecordingMonitor:
    def __init__(self) -> None:
        self.events: list[MonitorEvent] = []

    def record(self, event: MonitorEvent) -> bool:
        self.events.append(event)
        return True


class Store:
    async def search(self, query, access, limit=5):
        del query, access, limit
        return [
            VectorHit(
                document_id=1,
                filename="vpn.md",
                page=1,
                text="VPN 排查",
                score=0.9,
                sensitivity="internal",
            )
        ]


@pytest.mark.asyncio
async def test_retrieval_records_counts_without_query_or_chunks() -> None:
    monitor = RecordingMonitor()
    service = RetrievalService(
        Store(),
        minimum_score=0.2,
        monitor=monitor,
    )
    access = AccessContext(
        1,
        "IT",
        frozenset(),
        frozenset({1}),
        frozenset(),
    )

    result = await service.retrieve("秘密 VPN 问题", access)

    saved = monitor.events[0]
    assert saved.component == "retrieval"
    assert saved.metadata["query_count"] == len(result.queries)
    assert saved.metadata["citation_count"] == len(result.decision.citations)
    assert "query" not in saved.metadata
    assert "chunk" not in saved.metadata


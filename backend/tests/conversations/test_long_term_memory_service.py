import pytest

from app.agents.contracts import Sensitivity
from app.conversations.cache import CachedMessage
from app.conversations.memory_schemas import MemoryRecord, MemorySearchHit
from app.conversations.memory_service import LongTermMemoryService
from app.knowledge.access import AccessContext
from app.model_gateway.contracts import GatewayResponse
from app.monitoring.contracts import MonitorEvent

ACCESS = AccessContext(
    user_id=7,
    department="IT",
    roles=frozenset({"employee", "it_staff"}),
    knowledge_base_ids=frozenset({1}),
    dataset_ids=frozenset(),
)


class FakeStore:
    def __init__(self) -> None:
        self.records: list[MemoryRecord] = []
        self.search_user_ids: list[int] = []
        self.fail_search = False
        self.fail_upsert = False

    async def upsert(
        self,
        record: MemoryRecord,
    ) -> None:
        if self.fail_upsert:
            raise RuntimeError("qdrant down")
        self.records.append(record)

    async def search_private(
        self,
        query: str,
        user_id: int,
        limit: int,
        minimum_score: float,
    ) -> list[MemorySearchHit]:
        del query, limit, minimum_score
        self.search_user_ids.append(user_id)
        if self.fail_search:
            raise RuntimeError("qdrant down")
        return [
            MemorySearchHit(
                text="用户偏好直接给排查步骤。",
                score=0.8,
                memory_type="user_preference",
                sensitivity="internal",
            )
        ]


class FakeGateway:
    def __init__(self) -> None:
        self.sensitivities: list[Sensitivity] = []

    async def generate(
        self,
        request,
        sensitivity: Sensitivity,
    ) -> GatewayResponse:
        del request
        self.sensitivities.append(sensitivity)
        return GatewayResponse(
            text="用户多次询问 VPN 问题，偏好直接给排查步骤。",
            model="fake-local",
            provider="ollama",
            route_reason="test",
            external_sent=False,
        )


class RecordingMonitor:
    def __init__(self) -> None:
        self.events: list[MonitorEvent] = []

    def record(self, event: MonitorEvent) -> bool:
        self.events.append(event)
        return True


@pytest.mark.asyncio
async def test_memory_service_writes_summary_with_user_payload() -> None:
    store = FakeStore()
    gateway = FakeGateway()
    service = LongTermMemoryService(
        store=store,
        gateway=gateway,
        enabled=True,
        trigger_messages=2,
        recent_messages=8,
        max_summary_chars=1200,
        top_k=3,
        minimum_score=0.25,
    )

    await service.maybe_store_after_turn(
        access=ACCESS,
        conversation_id=11,
        message_ids=(101, 102),
        recent_messages=[
            CachedMessage("user", "vpn没有连接怎么办？"),
            CachedMessage("assistant", "请先检查网络。"),
        ],
        sensitivity=Sensitivity.INTERNAL,
        sql=None,
    )

    assert len(store.records) == 1
    record = store.records[0]
    assert record.user_id == 7
    assert record.department == "IT"
    assert record.roles == ("employee", "it_staff")
    assert record.conversation_id == 11
    assert record.message_ids == (101, 102)
    assert record.memory_type == "conversation_summary"
    assert record.sensitivity == "internal"
    assert record.text == "用户多次询问 VPN 问题，偏好直接给排查步骤。"


@pytest.mark.asyncio
async def test_sensitive_memory_summary_uses_sensitive_route() -> None:
    store = FakeStore()
    gateway = FakeGateway()
    service = LongTermMemoryService(
        store=store,
        gateway=gateway,
        enabled=True,
        trigger_messages=1,
        recent_messages=8,
        max_summary_chars=1200,
        top_k=3,
        minimum_score=0.25,
    )

    await service.maybe_store_after_turn(
        access=ACCESS,
        conversation_id=11,
        message_ids=(101, 102),
        recent_messages=[CachedMessage("user", "报销金额统计")],
        sensitivity=Sensitivity.SENSITIVE,
        sql="SELECT * FROM expense_summary_view",
    )

    assert gateway.sensitivities == [Sensitivity.SENSITIVE]
    assert "SELECT" not in store.records[0].text


@pytest.mark.asyncio
async def test_qdrant_failure_does_not_break_memory_read_or_write() -> None:
    store = FakeStore()
    store.fail_search = True
    store.fail_upsert = True
    service = LongTermMemoryService(
        store=store,
        gateway=FakeGateway(),
        enabled=True,
        trigger_messages=1,
        recent_messages=8,
        max_summary_chars=1200,
        top_k=3,
        minimum_score=0.25,
    )

    context = await service.retrieve_context(
        query="VPN 怎么办",
        access=ACCESS,
    )
    await service.maybe_store_after_turn(
        access=ACCESS,
        conversation_id=11,
        message_ids=(101, 102),
        recent_messages=[CachedMessage("user", "VPN 怎么办")],
        sensitivity=Sensitivity.INTERNAL,
        sql=None,
    )

    assert context == ""
    assert store.records == []


@pytest.mark.asyncio
async def test_memory_failures_are_recorded_without_content_and_still_fallback() -> None:
    store = FakeStore()
    store.fail_search = True
    monitor = RecordingMonitor()
    service = LongTermMemoryService(
        store=store,
        gateway=FakeGateway(),
        enabled=True,
        trigger_messages=1,
        recent_messages=8,
        max_summary_chars=1200,
        top_k=3,
        minimum_score=0.25,
        monitor=monitor,
    )

    context = await service.retrieve_context("secret VPN question", ACCESS)

    assert context == ""
    saved = monitor.events[0]
    assert saved.component == "long_term_memory"
    assert saved.operation == "retrieve"
    assert saved.success is False
    assert saved.metadata == {}


@pytest.mark.asyncio
async def test_disabled_memory_records_skipped_without_summary() -> None:
    monitor = RecordingMonitor()
    service = LongTermMemoryService(
        store=FakeStore(),
        gateway=FakeGateway(),
        enabled=False,
        trigger_messages=1,
        recent_messages=8,
        max_summary_chars=1200,
        top_k=3,
        minimum_score=0.25,
        monitor=monitor,
    )

    await service.maybe_store_after_turn(
        access=ACCESS,
        conversation_id=1,
        message_ids=(1, 2),
        recent_messages=[CachedMessage("user", "secret content")],
        sensitivity=Sensitivity.INTERNAL,
        sql=None,
    )

    assert monitor.events[0].success is True
    assert monitor.events[0].metadata == {
        "skipped": True,
        "skip_reason": "disabled_or_empty",
    }


@pytest.mark.asyncio
async def test_memory_context_is_marked_as_history_not_fact() -> None:
    service = LongTermMemoryService(
        store=FakeStore(),
        gateway=FakeGateway(),
        enabled=True,
        trigger_messages=2,
        recent_messages=8,
        max_summary_chars=1200,
        top_k=3,
        minimum_score=0.25,
    )

    context = await service.retrieve_context(
        query="VPN 怎么办",
        access=ACCESS,
    )

    assert "以下是用户历史上下文" in context
    assert "不得作为制度或数据事实依据" in context

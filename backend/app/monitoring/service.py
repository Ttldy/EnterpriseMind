from __future__ import annotations

import asyncio
import logging
from typing import Protocol

from app.monitoring.contracts import MonitorEvent

logger = logging.getLogger(__name__)


class MonitorBatchWriter(Protocol):
    async def write(
        self,
        events: list[MonitorEvent],
    ) -> None: ...


class NullMonitorWriter:
    async def write(
        self,
        events: list[MonitorEvent],
    ) -> None:
        del events


class MonitoringService:
    def __init__(
        self,
        writer: MonitorBatchWriter | None = None,
        *,
        enabled: bool = True,
        queue_max_size: int = 1000,
        batch_size: int = 50,
        flush_interval_seconds: float = 1.0,
    ) -> None:
        self._writer = writer or NullMonitorWriter()
        self._enabled = enabled
        self._queue: asyncio.Queue[MonitorEvent] = asyncio.Queue(
            maxsize=max(1, queue_max_size)
        )
        self._batch_size = max(1, batch_size)
        self._flush_interval_seconds = max(
            0.01,
            flush_interval_seconds,
        )
        self._stop_requested = asyncio.Event()
        self._consumer_task: asyncio.Task[None] | None = None
        self._dropped_events = 0

    @property
    def queue_size(self) -> int:
        return self._queue.qsize()

    @property
    def dropped_events(self) -> int:
        return self._dropped_events

    @property
    def is_running(self) -> bool:
        return (
            self._consumer_task is not None
            and not self._consumer_task.done()
        )

    def record(self, event: MonitorEvent) -> bool:
        if not self._enabled:
            return False
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            self._dropped_events += 1
            logger.warning(
                "monitor event dropped because queue is full",
                extra={"component": event.component},
            )
            return False
        return True

    async def start(self) -> None:
        if not self._enabled or self.is_running:
            return
        self._stop_requested.clear()
        self._consumer_task = asyncio.create_task(
            self._consume(),
            name="monitor-event-consumer",
        )

    async def stop(
        self,
        timeout_seconds: float = 3.0,
    ) -> None:
        task = self._consumer_task
        if task is None:
            return
        self._stop_requested.set()
        try:
            await asyncio.wait_for(
                asyncio.shield(task),
                timeout=max(0.01, timeout_seconds),
            )
        except TimeoutError:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        finally:
            self._consumer_task = None

    async def _consume(self) -> None:
        while (
            not self._stop_requested.is_set()
            or not self._queue.empty()
        ):
            batch = await self._next_batch()
            if not batch:
                continue
            try:
                await self._writer.write(batch)
            except Exception:
                logger.exception(
                    "monitor event batch write failed",
                    extra={"event_count": len(batch)},
                )
            finally:
                for _ in batch:
                    self._queue.task_done()

    async def _next_batch(self) -> list[MonitorEvent]:
        try:
            first = await asyncio.wait_for(
                self._queue.get(),
                timeout=self._flush_interval_seconds,
            )
        except TimeoutError:
            return []
        batch = [first]
        while len(batch) < self._batch_size:
            try:
                batch.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        return batch

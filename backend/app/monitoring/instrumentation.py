from __future__ import annotations

import time

from app.monitoring.context import current_trace_id
from app.monitoring.contracts import MonitorEvent, MonitorRecorder


class OperationTimer:
    def __init__(
        self,
        monitor: MonitorRecorder | None,
        *,
        component: str,
        operation: str,
        trace_id: str | None = None,
    ) -> None:
        self._monitor = monitor
        self._component = component
        self._operation = operation
        self._trace_id = trace_id
        self._started = time.perf_counter()
        self._finished = False

    def finish(
        self,
        *,
        success: bool,
        error_code: str | None = None,
        agent: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        timeout: bool = False,
        cache_hit: bool = False,
        fallback: bool = False,
        circuit_open: bool = False,
        metadata: dict[str, object] | None = None,
    ) -> None:
        if self._finished:
            return
        self._finished = True
        if self._monitor is None:
            return
        self._monitor.record(
            MonitorEvent(
                trace_id=self._trace_id or current_trace_id(),
                component=self._component,
                operation=self._operation,
                success=success,
                latency_ms=int(
                    (time.perf_counter() - self._started) * 1000
                ),
                error_code=error_code,
                agent=agent,
                provider=provider,
                model=model,
                timeout=timeout,
                cache_hit=cache_hit,
                fallback=fallback,
                circuit_open=circuit_open,
                metadata=metadata or {},
            )
        )


def exception_error_code(exc: BaseException) -> str:
    name = type(exc).__name__
    return "".join(
        f"_{character.lower()}"
        if character.isupper() and index
        else character.lower()
        for index, character in enumerate(name)
    )


def is_timeout_error(exc: BaseException) -> bool:
    current: BaseException | None = exc
    while current is not None:
        if isinstance(current, TimeoutError):
            return True
        current = current.__cause__
    return False


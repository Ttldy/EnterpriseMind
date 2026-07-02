from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

_trace_id: ContextVar[str | None] = ContextVar(
    "monitor_trace_id",
    default=None,
)


def current_trace_id() -> str | None:
    return _trace_id.get()


@contextmanager
def trace_context(trace_id: str | None) -> Iterator[None]:
    token = _trace_id.set(trace_id)
    try:
        yield
    finally:
        _trace_id.reset(token)


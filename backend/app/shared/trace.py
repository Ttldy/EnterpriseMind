from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class TraceIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        trace_id = uuid4().hex
        request.state.trace_id = trace_id

        response = await call_next(request)
        response.headers["X-Trace-ID"] = trace_id
        return response
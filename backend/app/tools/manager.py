from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass
from enum import StrEnum

from app.agents.contracts import Sensitivity
from app.monitoring.context import current_trace_id
from app.monitoring.contracts import MonitorEvent, MonitorRecorder
from app.tools.contracts import (
    EnterpriseTool,
    ToolContext,
    ToolExecutionError,
    ToolResult,
)


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    failure_threshold: int
    recovery_seconds: int
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    opened_at: float | None = None

    def allow(self) -> bool:
        if self.state is CircuitState.CLOSED:
            return True
        if self.state is CircuitState.OPEN:
            if (
                self.opened_at is not None
                and time.monotonic() - self.opened_at
                >= self.recovery_seconds
            ):
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        return True

    def record_success(self) -> None:
        self.failure_count = 0
        self.opened_at = None
        self.state = CircuitState.CLOSED

    def record_failure(self) -> None:
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.opened_at = time.monotonic()


class EnterpriseToolManager:
    def __init__(
        self,
        default_timeout_ms: int = 3000,
        default_cache_ttl_seconds: int = 30,
        circuit_failure_threshold: int = 3,
        circuit_recovery_seconds: int = 30,
        monitor: MonitorRecorder | None = None,
    ) -> None:
        self._tools: dict[str, EnterpriseTool] = {}
        self._cache: dict[str, tuple[object, float]] = {}
        self._breakers: dict[str, CircuitBreaker] = {}
        self._default_timeout_ms = default_timeout_ms
        self._default_cache_ttl_seconds = default_cache_ttl_seconds
        self._circuit_failure_threshold = circuit_failure_threshold
        self._circuit_recovery_seconds = circuit_recovery_seconds
        self._monitor = monitor

    def register(
        self,
        tool: EnterpriseTool,
    ) -> None:
        self._tools[tool.spec.name] = tool
        self._breakers[tool.spec.name] = CircuitBreaker(
            failure_threshold=self._circuit_failure_threshold,
            recovery_seconds=self._circuit_recovery_seconds,
        )

    async def execute(
        self,
        name: str,
        payload: dict[str, object],
        context: ToolContext,
    ) -> ToolResult:
        result = await self._execute(
            name,
            payload,
            context,
        )
        if self._monitor is not None:
            self._monitor.record(
                MonitorEvent(
                    trace_id=(
                        context.trace_id
                        or current_trace_id()
                    ),
                    component="tool_manager",
                    operation=name,
                    success=result.success,
                    latency_ms=result.latency_ms,
                    error_code=result.error_code,
                    timeout=(
                        result.error_code == "timeout"
                        or bool(
                            result.metadata.get(
                                "tool_timeout"
                            )
                        )
                    ),
                    cache_hit=result.cache_hit,
                    fallback=result.fallback_used,
                    circuit_open=result.circuit_open,
                    metadata={"tool_name": name},
                )
            )
        return result

    async def _execute(
        self,
        name: str,
        payload: dict[str, object],
        context: ToolContext,
    ) -> ToolResult:
        started = time.perf_counter()
        tool = self._tools.get(name)
        if tool is None:
            return self._failed(
                name,
                error_code="not_found",
                error_message=f"Tool not found: {name}",
                started=started,
                sensitivity=Sensitivity.INTERNAL,
            )
        if not self._has_required_roles(tool, context):
            return self._failed(
                name,
                error_code="permission_denied",
                error_message="Tool required roles are not satisfied",
                started=started,
                sensitivity=tool.spec.sensitivity,
                metadata={"permission_block": True},
            )

        validation_error = self._validate_payload(
            tool,
            payload,
        )
        if validation_error is not None:
            return self._failed(
                name,
                error_code="validation_error",
                error_message=validation_error,
                started=started,
                sensitivity=tool.spec.sensitivity,
                metadata={"tool_validation_error": True},
            )

        breaker = self._breakers[name]
        if tool.spec.circuit_breaker_enabled and not breaker.allow():
            return self._failed(
                name,
                error_code="circuit_open",
                error_message=f"Tool circuit is open: {name}",
                started=started,
                sensitivity=tool.spec.sensitivity,
                circuit_open=True,
                metadata={"tool_circuit_open": True},
            )

        cache_key = self._cache_key(
            tool,
            payload,
            context,
        )
        if cache_key is not None:
            cached = self._get_cache(cache_key)
            if cached is not None:
                return ToolResult(
                    success=True,
                    output=cached,
                    metadata=self._metadata(
                        name,
                        started,
                        success=True,
                        cache_hit=True,
                    ),
                    latency_ms=self._elapsed_ms(started),
                    cache_hit=True,
                    sensitivity=tool.spec.sensitivity,
                )

        try:
            output = await asyncio.wait_for(
                tool.run(
                    payload,
                    context,
                ),
                timeout=self._timeout_seconds(tool),
            )
        except TimeoutError:
            breaker.record_failure()
            return self._failed(
                name,
                error_code="timeout",
                error_message="Tool execution timed out",
                started=started,
                sensitivity=tool.spec.sensitivity,
                metadata={"tool_timeout": True},
            )
        except Exception as exc:
            breaker.record_failure()
            return self._failed(
                name,
                error_code="execution_error",
                error_message=str(exc),
                started=started,
                sensitivity=tool.spec.sensitivity,
            )
        breaker.record_success()
        if cache_key is not None:
            self._set_cache(
                cache_key,
                output,
                self._cache_ttl(tool),
            )
        return ToolResult(
            success=True,
            output=output,
            metadata=self._metadata(
                name,
                started,
                success=True,
            ),
            latency_ms=self._elapsed_ms(started),
            sensitivity=tool.spec.sensitivity,
        )

    def _failed(
        self,
        name: str,
        error_code: str,
        error_message: str,
        started: float,
        sensitivity: Sensitivity,
        circuit_open: bool = False,
        metadata: dict[str, object] | None = None,
    ) -> ToolResult:
        final_metadata = self._metadata(
            name,
            started,
            success=False,
            circuit_open=circuit_open,
        )
        if metadata:
            final_metadata.update(metadata)
        if error_code == "timeout":
            final_metadata["tool_timeout"] = True
        if error_code == "circuit_open":
            final_metadata["tool_circuit_open"] = True
        return ToolResult(
            success=False,
            output=None,
            error=ToolExecutionError(error_message),
            error_code=error_code,
            error_message=error_message,
            metadata=final_metadata,
            latency_ms=self._elapsed_ms(started),
            circuit_open=circuit_open,
            sensitivity=sensitivity,
        )

    def _metadata(
        self,
        name: str,
        started: float,
        success: bool,
        cache_hit: bool = False,
        circuit_open: bool = False,
    ) -> dict[str, object]:
        return {
            "tool_name": name,
            "tool_success": success,
            "tool_failure": not success,
            "tool_latency_ms": self._elapsed_ms(started),
            "tool_cache_hit": cache_hit,
            "tool_timeout": False,
            "tool_circuit_open": circuit_open,
            "tool_fallback": False,
        }

    @staticmethod
    def _has_required_roles(
        tool: EnterpriseTool,
        context: ToolContext,
    ) -> bool:
        required = tool.spec.required_roles
        return not required or bool(required & context.roles)

    def _validate_payload(
        self,
        tool: EnterpriseTool,
        payload: dict[str, object],
    ) -> str | None:
        schema = tool.spec.input_schema
        required = schema.get("required", [])
        properties = schema.get("properties", {})
        if isinstance(required, list):
            for field in required:
                if isinstance(field, str) and field not in payload:
                    return f"Missing required field: {field}"
        if isinstance(properties, dict):
            for key, raw_property in properties.items():
                if key not in payload or not isinstance(raw_property, dict):
                    continue
                expected_type = raw_property.get("type")
                if (
                    isinstance(expected_type, str)
                    and not self._type_matches(payload[key], expected_type)
                ):
                    return f"Field {key} expected {expected_type}"
        return None

    @staticmethod
    def _type_matches(
        value: object,
        expected_type: str,
    ) -> bool:
        if expected_type == "string":
            return isinstance(value, str)
        if expected_type == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        if expected_type == "number":
            return isinstance(value, int | float) and not isinstance(value, bool)
        if expected_type == "boolean":
            return isinstance(value, bool)
        if expected_type == "array":
            return isinstance(value, list)
        if expected_type == "object":
            return isinstance(value, dict)
        if expected_type == "access_context":
            return value.__class__.__name__ == "AccessContext"
        return True

    def _cache_key(
        self,
        tool: EnterpriseTool,
        payload: dict[str, object],
        context: ToolContext,
    ) -> str | None:
        if not tool.spec.cache_enabled:
            return None
        if tool.spec.sensitivity is Sensitivity.SENSITIVE:
            return None
        ttl = self._cache_ttl(tool)
        if ttl <= 0:
            return None
        payload_key = {
            key: self._cacheable_value(value)
            for key, value in sorted(payload.items())
            if self._is_cacheable(value)
        }
        raw = {
            "tool": tool.spec.name,
            "payload": payload_key,
            "user_id": context.user_id,
            "department": context.department,
            "roles": sorted(context.roles),
        }
        serialized = json.dumps(
            raw,
            ensure_ascii=False,
            sort_keys=True,
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def _is_cacheable(
        value: object,
    ) -> bool:
        return isinstance(
            value,
            str | int | float | bool | type(None),
        )

    @staticmethod
    def _cacheable_value(
        value: object,
    ) -> object:
        return value

    def _get_cache(
        self,
        key: str,
    ) -> object | None:
        item = self._cache.get(key)
        if item is None:
            return None
        value, expires_at = item
        if time.monotonic() >= expires_at:
            self._cache.pop(key, None)
            return None
        return value

    def _set_cache(
        self,
        key: str,
        value: object,
        ttl_seconds: int,
    ) -> None:
        self._cache[key] = (
            value,
            time.monotonic() + ttl_seconds,
        )

    def _timeout_seconds(
        self,
        tool: EnterpriseTool,
    ) -> float:
        timeout_ms = tool.spec.timeout_ms or self._default_timeout_ms
        return max(timeout_ms, 1) / 1000

    def _cache_ttl(
        self,
        tool: EnterpriseTool,
    ) -> int:
        return (
            tool.spec.cache_ttl_seconds
            or self._default_cache_ttl_seconds
        )

    @staticmethod
    def _elapsed_ms(
        started: float,
    ) -> int:
        return int(
            (time.perf_counter() - started) * 1000
        )

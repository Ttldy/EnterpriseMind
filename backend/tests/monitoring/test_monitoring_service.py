from app.monitoring.service import MonitoringService


def test_monitoring_service_penalizes_failures_and_latency() -> None:
    service = MonitoringService()

    service.record(
        component="it_agent",
        success=True,
        latency_ms=100,
    )
    healthy = service.health("it_agent")

    service.record(
        component="it_agent",
        success=False,
        latency_ms=3000,
    )
    degraded = service.health("it_agent")

    assert healthy.health_score > degraded.health_score
    assert degraded.monitor_penalty > healthy.monitor_penalty
    assert degraded.warning is True


def test_monitoring_service_detects_simulated_timeout_and_circuit_open() -> None:
    service = MonitoringService()

    timeout = service.evaluate_question("模拟知识检索工具超时后的降级处理。")
    circuit = service.evaluate_question("模拟财务工具连续失败后 circuit open。")
    normal = service.evaluate_question("模拟 IT Agent 正常回答 VPN 问题。")

    assert timeout.warning is True
    assert timeout.reason == "simulated_timeout"
    assert circuit.warning is True
    assert circuit.reason == "simulated_circuit_open"
    assert normal.warning is False

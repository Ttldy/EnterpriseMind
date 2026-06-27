from app.agents.composite import CompositeTaskPlanner
from app.agents.contracts import AgentType


def test_composite_planner_detects_it_knowledge_plus_data_question() -> None:
    plan = CompositeTaskPlanner().plan(
        "先说明 VPN 无法连接的排查步骤，再统计最近 7 天 IT 工单数量。"
    )

    assert plan is not None
    assert plan.primary_agent is AgentType.IT
    assert plan.requires_data_task is True
    assert plan.knowledge_focus == "VPN"
    assert plan.data_focus == "工单统计"


def test_composite_planner_detects_finance_knowledge_plus_data_question() -> None:
    plan = CompositeTaskPlanner().plan(
        "先解释差旅报销规则，再统计本月差旅报销总金额。"
    )

    assert plan is not None
    assert plan.primary_agent is AgentType.FINANCE
    assert plan.requires_data_task is True
    assert plan.knowledge_focus == "报销"
    assert plan.data_focus == "报销统计"


def test_composite_planner_ignores_simple_question() -> None:
    assert CompositeTaskPlanner().plan("vpn无法连接怎么办？") is None

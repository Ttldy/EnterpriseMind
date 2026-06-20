from app.agents.contracts import AgentType, IntentType, Sensitivity
from app.agents.router import RuleRouter


def test_routes_vpn_problem_to_it() -> None:
    result = RuleRouter().route("公司 VPN 无法连接")

    assert result.agent is AgentType.IT
    assert result.intent is IntentType.KNOWLEDGE_QUERY
    assert result.requires_sql is False
    assert result.sensitivity is Sensitivity.INTERNAL


def test_routes_leave_question_to_hr() -> None:
    result = RuleRouter().route("公司的年假如何计算？")

    assert result.agent is AgentType.HR


def test_routes_reimbursement_question_to_finance() -> None:
    result = RuleRouter().route("差旅报销需要什么发票？")

    assert result.agent is AgentType.FINANCE


def test_routes_statistics_question_to_data_analyst() -> None:
    result = RuleRouter().route("统计本月各部门报销金额")

    assert result.agent is AgentType.DATA_ANALYST
    assert result.intent is IntentType.DATA_QUERY
    assert result.requires_sql is True
    assert result.sensitivity is Sensitivity.SENSITIVE


def test_unknown_question_requires_clarification() -> None:
    result = RuleRouter().route("帮我看看这个")

    assert result.agent is AgentType.CLARIFICATION
    assert result.intent is IntentType.UNKNOWN
    assert result.confidence < 0.6

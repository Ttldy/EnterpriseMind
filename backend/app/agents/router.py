from app.agents.contracts import (
    AgentType,
    IntentType,
    RouteResult,
    Sensitivity,
)
from app.model_gateway.sensitivity import (
    classify_question,
)


class RuleRouter:
    _domain_rules: dict[
        AgentType,
        tuple[str, ...],
    ] = {
        AgentType.HR: (
            "年假",
            "请假",
            "考勤",
            "福利",
            "入职",
            "离职",
            "办公时间",
            "公司地址",
        ),
        AgentType.IT: (
            "vpn",
            "登录",
            "报错",
            "设备",
            "网络",
            "密码",
            "工单",
        ),
        AgentType.FINANCE: (
            "报销",
            "发票",
            "差旅",
            "付款",
            "预算",
        ),
    }

    _statistics_words: tuple[str, ...] = (
        "统计",
        "趋势",
        "汇总",
        "各部门",
        "本月多少",
        "员工名单",
        "解决率",
    )

    def route(
        self,
        message: str,
    ) -> RouteResult:
        normalized = message.strip().lower()

        if self._requires_data_query(normalized):
            return RouteResult(
                agent=AgentType.DATA_ANALYST,
                intent=IntentType.DATA_QUERY,
                requires_sql=True,
                sensitivity=Sensitivity.SENSITIVE,
                confidence=0.95,
            )

        question_sensitivity = classify_question(normalized).level
        for agent, keywords in self._domain_rules.items():
            if any(keyword in normalized for keyword in keywords):
                return RouteResult(
                    agent=agent,
                    intent=(IntentType.KNOWLEDGE_QUERY),
                    requires_sql=False,
                    sensitivity=(question_sensitivity),
                    confidence=0.90,
                )

        return RouteResult(
            agent=AgentType.CLARIFICATION,
            intent=IntentType.UNKNOWN,
            requires_sql=False,
            sensitivity=Sensitivity.INTERNAL,
            confidence=0.20,
        )

    def _requires_data_query(
        self,
        message: str,
    ) -> bool:
        return any(word in message for word in self._statistics_words)

from __future__ import annotations

from dataclasses import dataclass

from app.agents.contracts import AgentType


@dataclass(frozen=True)
class CompositePlan:
    primary_agent: AgentType
    requires_data_task: bool
    knowledge_focus: str
    data_focus: str


class CompositeTaskPlanner:
    def plan(
        self,
        question: str,
    ) -> CompositePlan | None:
        normalized = question.strip().lower()
        has_sequence = any(
            word in normalized
            for word in (
                "先",
                "再",
                "结合",
                "同时",
            )
        )
        has_data = any(
            word in normalized
            for word in (
                "统计",
                "数量",
                "总金额",
                "明细",
                "记录",
            )
        )
        if not has_sequence or not has_data:
            return None

        if any(
            word in normalized
            for word in ("vpn", "工单", "it")
        ):
            return CompositePlan(
                primary_agent=AgentType.IT,
                requires_data_task=True,
                knowledge_focus="VPN",
                data_focus="工单统计",
            )
        if any(
            word in normalized
            for word in ("报销", "差旅", "发票", "财务")
        ):
            return CompositePlan(
                primary_agent=AgentType.FINANCE,
                requires_data_task=True,
                knowledge_focus="报销",
                data_focus="报销统计",
            )
        if any(
            word in normalized
            for word in ("考勤", "员工", "入职", "hr")
        ):
            return CompositePlan(
                primary_agent=AgentType.HR,
                requires_data_task=True,
                knowledge_focus="HR",
                data_focus="员工统计",
            )
        return None

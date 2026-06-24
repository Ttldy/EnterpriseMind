from app.evaluation.contracts import (
    CaseOutput,
    EvaluationCase,
)


class DemoCaseExecutor:
    async def execute(
        self,
        case: EvaluationCase,
        prompt_content: str,
    ) -> CaseOutput:
        if case.sql_must_be_rejected:
            return CaseOutput(
                answer="查询被安全策略拒绝",
                agent="data_analyst",
                provider="ollama",
                refused=True,
                sql_rejected=True,
            )
        if case.category == "safety":
            return CaseOutput(
                answer="敏感请求已拒绝",
                agent="finance",
                provider="ollama",
                refused=True,
            )

        refused = bool(case.should_refuse)
        answer = (
            "当前证据不足，无法确认。"
            if refused
            else "请准备发票和报销材料并按制度提交。"
        )
        return CaseOutput(
            answer=answer,
            agent=case.expected_agent or "finance",
            provider="ollama",
            refused=refused,
            citations=(
                (case.expected_citation,)
                if case.expected_citation
                else ()
            ),
        )
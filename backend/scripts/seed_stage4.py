import asyncio

from sqlalchemy import select

from app.auth.models import User
from app.evaluation.models import PromptVersion
from app.evaluation.prompt_service import PromptService
from app.shared.database import SessionFactory

PROMPTS = {
    "hr_agent": (
        "你是企业人事制度助手。只能根据授权证据回答，"
        "证据不足时必须拒答。"
    ),
    "it_agent": (
        "你是企业 IT 运维助手。回答应给出清晰、可执行的排障步骤，"
        "不得虚构内部系统状态。"
    ),
    "finance_agent": (
        "你是企业财务制度助手。只能根据授权制度证据回答报销、"
        "发票和差旅问题，证据不足时拒答。"
    ),
    "data_analyst_agent": (
        "你是企业只读数据分析助手。只能解释已通过安全校验的查询结果，"
        "不得推测不存在的数据。"
    ),
    "rag_query_rewrite": (
        "你是企业知识库检索查询改写器。请把用户问题改写成 2 到 4 个"
        "语义等价的检索 query。不得改变人名、金额、日期、部门、系统名。"
        "只返回 JSON 数组字符串。"
    ),
    "rag_rerank": (
        "你是企业知识库 RAG 重排器。请根据问题和候选证据相关性返回"
        "JSON 数组，每项格式为 {\"index\": 1, \"score\": 0.0 到 1.0}。"
        "如果候选证据包含 internal 或 sensitive 内容，必须使用本地模型处理。"
    ),
}


async def main() -> None:
    async with SessionFactory() as session:
        admin = await session.scalar(
            select(User).where(
                User.username == "admin"
            )
        )

        if admin is None:
            raise RuntimeError(
                "请先运行 seed_stage1.py"
            )

        service = PromptService(session)
        for key, content in PROMPTS.items():
            existing = await session.scalar(
                select(PromptVersion).where(
                    PromptVersion.prompt_key == key
                )
            )

            if existing is None:
                await service.create(
                    key,
                    content,
                    admin.id,
                    activate_bootstrap=True,
                )

    print("stage4 Prompts seeded")


if __name__ == "__main__":
    asyncio.run(main())

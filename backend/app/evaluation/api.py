from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
)
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_role
from app.auth.models import User
from app.evaluation.contracts import CaseExecutor
from app.evaluation.executor import DemoCaseExecutor
from app.evaluation.judge import LLMJudgeScorer
from app.evaluation.models import PromptVersion
from app.evaluation.orchestrator_executor import (
    OrchestratorCaseExecutor,
)
from app.evaluation.prompt_service import (
    PromptNotFoundError,
    PromptReleaseBlockedError,
    PromptService,
)
from app.evaluation.resolver import DatabasePromptResolver
from app.evaluation.runner import EvaluationRunner
from app.shared.config import get_settings
from app.shared.database import get_session

router = APIRouter(
    prefix="/evaluation",
    tags=["evaluation"],
)


class PromptCreate(BaseModel):
    prompt_key: str = Field(
        min_length=2,
        max_length=64,
    )
    content: str = Field(
        min_length=20,
        max_length=20000,
    )


class EvaluationRunRequest(BaseModel):
    executor_mode: str | None = None
    judge_enabled: bool | None = None


def prompt_dict(item: PromptVersion) -> dict[str, object]:
    return {
        "id": item.id,
        "prompt_key": item.prompt_key,
        "version": item.version,
        "content": item.content,
        "content_sha256": item.content_sha256,
        "is_active": item.is_active,
        "created_at": item.created_at,
    }


@router.get("/prompts")
async def list_prompts(
    prompt_key: str | None = None,
    _: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, object]]:
    values = await PromptService(
        session
    ).list_versions(prompt_key)
    return [prompt_dict(item) for item in values]


@router.post("/prompts", status_code=201)
async def create_prompt(
    body: PromptCreate,
    user: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    item = await PromptService(session).create(
        body.prompt_key,
        body.content,
        user.id,
    )
    return prompt_dict(item)


@router.post("/prompts/{prompt_id}/run")
async def run_evaluation(
    prompt_id: int,
    request: Request,
    body: EvaluationRunRequest | None = None,
    _: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    settings = get_settings()
    service = PromptService(session)
    try:
        prompt = await service.get(prompt_id)
    except PromptNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    executor_mode = (
        body.executor_mode
        if body and body.executor_mode
        else settings.evaluation_executor_mode
    )
    judge_enabled = (
        body.judge_enabled
        if body and body.judge_enabled is not None
        else settings.evaluation_judge_enabled
    )
    executor: CaseExecutor
    if executor_mode == "demo":
        executor = DemoCaseExecutor()
    elif executor_mode == "orchestrator":
        executor = OrchestratorCaseExecutor(
            session=session,
            router=request.app.state.router,
            gateway=request.app.state.gateway,
            retrieval=request.app.state.retrieval,
            data_service=(
                request.app.state.data_service_factory(
                    session
                )
            ),
            prompts=DatabasePromptResolver(
                PromptService(session)
            ),
            memory=request.app.state.long_term_memory,
            tool_manager=request.app.state.tool_manager,
            composite_enabled=(
                request.app.state.composite_agent_enabled
            ),
            monitor=request.app.state.monitoring_service,
            default_usernames={
                "hr_agent": (
                    settings.evaluation_default_hr_username
                ),
                "it_agent": (
                    settings.evaluation_default_it_username
                ),
                "finance_agent": (
                    settings.evaluation_default_finance_username
                ),
                "data_analyst_agent": (
                    settings.evaluation_default_finance_username
                ),
                "employee": (
                    settings.evaluation_default_employee_username
                ),
                "admin": (
                    settings.evaluation_default_admin_username
                ),
            },
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="executor_mode must be demo or orchestrator",
        )

    judge = (
        LLMJudgeScorer(
            request.app.state.gateway,
            minimum_score=(
                settings.evaluation_judge_minimum_score
            ),
        )
        if judge_enabled
        else None
    )
    run = await EvaluationRunner(
        session=session,
        executor=executor,
        case_directory=(
            settings.evaluation_case_directory
        ),
        model_name=settings.ollama_model,
        maximum_drop=(
            settings.evaluation_maximum_drop
        ),
        judge=judge,
        judge_enabled=judge_enabled,
        judge_minimum_score=(
            settings.evaluation_judge_minimum_score
        ),
        judge_fail_closed=(
            settings.evaluation_judge_fail_closed
        ),
    ).run(prompt)
    return {
        "id": run.id,
        "status": run.status,
        "safety_pass_rate": (
            run.safety_pass_rate
        ),
        "safety_passed": run.safety_passed,
        "metrics": run.metrics,
        "regressions": run.regressions,
        "judge_summary": {
            "enabled": judge_enabled,
            "overall": run.metrics.get(
                "judge_overall"
            ),
            "minimum": (
                settings.evaluation_judge_minimum_score
            ),
            "fail_closed": (
                settings.evaluation_judge_fail_closed
            ),
        },
        "release_allowed": (
            run.release_allowed
        ),
        "case_results": run.case_results,
        "duration_ms": run.duration_ms,
    }


@router.post("/prompts/{prompt_id}/activate")
async def activate_prompt(
    prompt_id: int,
    _: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    try:
        item = await PromptService(
            session
        ).activate(prompt_id)
    except PromptNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except PromptReleaseBlockedError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc
    return prompt_dict(item)


@router.post("/prompts/{prompt_key}/rollback")
async def rollback_prompt(
    prompt_key: str,
    _: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    try:
        item = await PromptService(
            session
        ).rollback(prompt_key)
    except (
        PromptNotFoundError,
        PromptReleaseBlockedError,
    ) as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc
    return prompt_dict(item)

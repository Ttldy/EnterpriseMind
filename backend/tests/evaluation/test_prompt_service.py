import pytest
from sqlalchemy import func, select

from app.auth.models import User
from app.evaluation.models import (
    EvaluationRun,
    PromptVersion,
)
from app.evaluation.prompt_service import (
    PromptService,
)


@pytest.mark.asyncio
async def test_activate_keeps_one_active_version(
    seeded_session,
) -> None:
    async with seeded_session() as session:
        user_id = await session.scalar(
            select(User.id).limit(1)
        )
        assert user_id is not None

        service = PromptService(session)
        first = await service.create(
            prompt_key="it_agent",
            content="第一版 Prompt",
            created_by=user_id,
            activate_bootstrap=True,
        )
        second = await service.create(
            prompt_key="it_agent",
            content="第二版 Prompt",
            created_by=user_id,
        )

        session.add(
            EvaluationRun(
                prompt_version_id=second.id,
                status="COMPLETED",
                model_name="test-model",
                dataset_sha256="0" * 64,
                release_allowed=True,
            )
        )
        await session.commit()
        activated = await service.activate(
            second.id
        )

        active_count = await session.scalar(
            select(func.count())
            .select_from(PromptVersion)
            .where(
                PromptVersion.prompt_key
                == "it_agent",
                PromptVersion.is_active.is_(
                    True
                ),
            )
        )
        assert first.is_active is False
        assert activated.is_active is True
        assert active_count == 1
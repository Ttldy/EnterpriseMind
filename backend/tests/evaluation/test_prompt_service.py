import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

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


@pytest.mark.asyncio
async def test_candidate_is_committed_inactive_and_versions_increment(
    seeded_session,
) -> None:
    async with seeded_session() as session:
        user_id = await session.scalar(select(User.id).limit(1))
        assert user_id is not None
        service = PromptService(session)
        active = await service.create(
            prompt_key="hr_agent",
            content="active prompt content",
            created_by=user_id,
            activate_bootstrap=True,
        )
        second = await service.create(
            prompt_key="hr_agent",
            content="candidate prompt content two",
            created_by=user_id,
        )
        third = await service.create(
            prompt_key="hr_agent",
            content="candidate prompt content three",
            created_by=user_id,
        )

    async with seeded_session() as session:
        saved = (
            await session.scalars(
                select(PromptVersion)
                .where(PromptVersion.prompt_key == "hr_agent")
                .order_by(PromptVersion.version)
            )
        ).all()
        assert [item.id for item in saved] == [active.id, second.id, third.id]
        assert [item.version for item in saved] == [1, 2, 3]
        assert [item.is_active for item in saved] == [True, False, False]


@pytest.mark.asyncio
async def test_create_retries_one_unique_version_race(
    seeded_session,
    monkeypatch,
) -> None:
    async with seeded_session() as session:
        user_id = await session.scalar(select(User.id).limit(1))
        assert user_id is not None
        original_commit = session.commit
        attempts = 0

        async def flaky_commit() -> None:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise IntegrityError("insert", {}, Exception("unique race"))
            await original_commit()

        monkeypatch.setattr(session, "commit", flaky_commit)
        created = await PromptService(session).create(
            prompt_key="it_agent",
            content="a valid candidate prompt content",
            created_by=user_id,
        )

        assert created.version == 1
        assert attempts == 2

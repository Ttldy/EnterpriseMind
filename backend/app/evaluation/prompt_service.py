import hashlib

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.evaluation.models import (
    EvaluationRun,
    PromptVersion,
)


class PromptNotFoundError(LookupError):
    pass


class PromptReleaseBlockedError(ValueError):
    pass


class PromptVersionConflictError(ValueError):
    pass


class PromptService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def create(
        self,
        prompt_key: str,
        content: str,
        created_by: int,
        activate_bootstrap: bool = False,
    ) -> PromptVersion:
        normalized = content.strip()
        if not normalized:
            raise ValueError("Prompt content is empty")
        normalized_key = prompt_key.strip()
        if not normalized_key:
            raise ValueError("Prompt key is empty")

        for attempt in range(3):
            latest = await self._session.scalar(
                select(
                    func.max(PromptVersion.version)
                ).where(
                    PromptVersion.prompt_key
                    == normalized_key
                )
            )
            prompt = PromptVersion(
                prompt_key=normalized_key,
                version=int(latest or 0) + 1,
                content=normalized,
                content_sha256=hashlib.sha256(
                    normalized.encode("utf-8")
                ).hexdigest(),
                is_active=activate_bootstrap,
                created_by=created_by,
            )
            if activate_bootstrap:
                await self._deactivate_key(normalized_key)
            self._session.add(prompt)
            try:
                await self._session.commit()
            except IntegrityError as exc:
                await self._session.rollback()
                if attempt == 2:
                    raise PromptVersionConflictError(
                        "Prompt 版本创建冲突，请重试"
                    ) from exc
                continue
            await self._session.refresh(prompt)
            return prompt

        raise PromptVersionConflictError(
            "Prompt 版本创建冲突，请重试"
        )

    async def list_versions(
        self,
        prompt_key: str | None = None,
    ) -> list[PromptVersion]:
        statement = select(PromptVersion).order_by(
            PromptVersion.prompt_key,
            PromptVersion.version.desc(),
        )
        if prompt_key:
            statement = statement.where(
                PromptVersion.prompt_key
                == prompt_key
            )
        return list(
            (
                await self._session.scalars(
                    statement
                )
            ).all()
        )

    async def get(
        self,
        prompt_id: int,
    ) -> PromptVersion:
        prompt = await self._session.get(
            PromptVersion,
            prompt_id,
        )
        if prompt is None:
            raise PromptNotFoundError(
                "Prompt version not found"
            )
        return prompt

    async def get_active(
        self,
        prompt_key: str,
    ) -> PromptVersion:
        prompt = await self._session.scalar(
            select(PromptVersion).where(
                PromptVersion.prompt_key
                == prompt_key,
                PromptVersion.is_active.is_(True),
            )
        )
        if prompt is None:
            raise PromptNotFoundError(
                f"No active Prompt: {prompt_key}"
            )
        return prompt

    async def resolve(
        self,
        prompt_key: str,
        fallback: str,
    ) -> str:
        try:
            return (
                await self.get_active(prompt_key)
            ).content
        except PromptNotFoundError:
            return fallback

    async def activate(
        self,
        prompt_id: int,
    ) -> PromptVersion:
        prompt = await self.get(prompt_id)
        latest_run = await self._session.scalar(
            select(EvaluationRun)
            .where(
                EvaluationRun.prompt_version_id
                == prompt.id,
                EvaluationRun.status == "COMPLETED",
            )
            .order_by(EvaluationRun.id.desc())
        )
        if (
            latest_run is None
            or not latest_run.release_allowed
        ):
            raise PromptReleaseBlockedError(
                "候选版本尚未通过发布门禁"
            )
        await self._deactivate_key(
            prompt.prompt_key
        )
        prompt.is_active = True
        await self._session.commit()
        await self._session.refresh(prompt)
        return prompt

    async def rollback(
        self,
        prompt_key: str,
    ) -> PromptVersion:
        active = await self.get_active(prompt_key)
        previous = await self._session.scalar(
            select(PromptVersion)
            .where(
                PromptVersion.prompt_key
                == prompt_key,
                PromptVersion.version
                < active.version,
            )
            .order_by(
                PromptVersion.version.desc()
            )
        )
        if previous is None:
            raise PromptReleaseBlockedError(
                "没有可回滚的历史版本"
            )
        await self._deactivate_key(prompt_key)
        previous.is_active = True
        await self._session.commit()
        await self._session.refresh(previous)
        return previous

    async def _deactivate_key(
        self,
        prompt_key: str,
    ) -> None:
        await self._session.execute(
            update(PromptVersion)
            .where(
                PromptVersion.prompt_key
                == prompt_key
            )
            .values(is_active=False)
        )

import pytest
from sqlalchemy import select

from app.auth.models import User
from app.knowledge.access import build_access_context
from app.knowledge.models import (
    KnowledgeBase,
    KnowledgePermission,
)


@pytest.mark.asyncio
async def test_access_context_comes_from_database(
    seeded_session,
) -> None:
    async with seeded_session() as session:
        knowledge_base = KnowledgeBase(
            name="IT 私有知识库",
            domain="it",
            sensitivity="internal",
        )
        knowledge_base.permissions.append(
            KnowledgePermission(
                subject_type="ROLE",
                subject_value="it_staff",
            )
        )
        session.add(knowledge_base)
        await session.commit()

        user = await session.scalar(select(User).where(User.username == "it01"))
        assert user is not None

        access = await build_access_context(
            session,
            user,
        )

        assert access.department == "IT"
        assert access.roles == frozenset({"employee", "it_staff"})
        assert knowledge_base.id in (access.knowledge_base_ids)

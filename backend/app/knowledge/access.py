from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.knowledge.models import (
    KnowledgeBase,
    KnowledgePermission,
)


@dataclass(frozen=True)
class AccessContext:
    user_id: int
    department: str
    roles: frozenset[str]
    knowledge_base_ids: frozenset[int]
    dataset_ids: frozenset[int]


async def build_access_context(
    session: AsyncSession,
    user: User,
) -> AccessContext:
    role_names = frozenset(role.name for role in user.roles)
    department_name = user.department.name

    permission_conditions = [
        KnowledgeBase.is_public.is_(True),
        (
            (KnowledgePermission.subject_type == "DEPARTMENT")
            & (KnowledgePermission.subject_value == department_name)
        ),
    ]

    if role_names:
        permission_conditions.append(
            (KnowledgePermission.subject_type == "ROLE")
            & (KnowledgePermission.subject_value.in_(role_names))
        )

    statement = (
        select(KnowledgeBase.id)
        .outerjoin(
            KnowledgePermission,
            KnowledgePermission.knowledge_base_id == KnowledgeBase.id,
        )
        .where(or_(*permission_conditions))
        .distinct()
    )

    knowledge_base_ids = frozenset((await session.scalars(statement)).all())

    return AccessContext(
        user_id=user.id,
        department=department_name,
        roles=role_names,
        knowledge_base_ids=knowledge_base_ids,
        dataset_ids=frozenset(),
    )

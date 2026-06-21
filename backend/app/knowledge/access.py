from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.database_agent.models import (
    Dataset,
    DatasetPermission,
)
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

    knowledge_conditions = [
        KnowledgeBase.is_public.is_(True),
        (
            (KnowledgePermission.subject_type == "DEPARTMENT")
            & (KnowledgePermission.subject_value == department_name)
        ),
    ]
    dataset_conditions = [
        (DatasetPermission.subject_type == "DEPARTMENT")
        & (DatasetPermission.subject_value == department_name)
    ]

    if role_names:
        knowledge_conditions.append(
            (KnowledgePermission.subject_type == "ROLE")
            & (KnowledgePermission.subject_value.in_(role_names))
        )
        dataset_conditions.append(
            (DatasetPermission.subject_type == "ROLE")
            & (DatasetPermission.subject_value.in_(role_names))
        )

    knowledge_statement = (
        select(KnowledgeBase.id)
        .outerjoin(
            KnowledgePermission,
            (KnowledgePermission.knowledge_base_id == KnowledgeBase.id),
        )
        .where(or_(*knowledge_conditions))
        .distinct()
    )

    dataset_statement = (
        select(Dataset.id)
        .join(
            DatasetPermission,
            (DatasetPermission.dataset_id == Dataset.id),
        )
        .where(
            Dataset.is_active.is_(True),
            or_(*dataset_conditions),
        )
        .distinct()
    )

    knowledge_base_ids = frozenset((await session.scalars(knowledge_statement)).all())
    dataset_ids = frozenset((await session.scalars(dataset_statement)).all())

    return AccessContext(
        user_id=user.id,
        department=department_name,
        roles=role_names,
        knowledge_base_ids=knowledge_base_ids,
        dataset_ids=dataset_ids,
    )

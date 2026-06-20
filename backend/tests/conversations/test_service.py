import pytest

from app.conversations.cache import CachedMessage
from app.conversations.service import ConversationService


class FakeCache:
    def __init__(self) -> None:
        self.values: dict[int, list[CachedMessage]] = {}

    async def append(
        self,
        conversation_id: int,
        message: CachedMessage,
        limit: int = 8,
    ) -> None:
        values = self.values.setdefault(
            conversation_id,
            [],
        )
        values.append(message)
        self.values[conversation_id] = values[-limit:]

    async def get(
        self,
        conversation_id: int,
    ) -> list[CachedMessage]:
        return self.values.get(
            conversation_id,
            [],
        )

    async def delete(
        self,
        conversation_id: int,
    ) -> None:
        self.values.pop(conversation_id, None)


@pytest.mark.asyncio
async def test_user_cannot_read_another_users_conversation(
    seeded_session,
) -> None:
    async with seeded_session() as session:
        service = ConversationService(
            session,
            FakeCache(),
        )
        conversation = await service.create(
            user_id=1,
            title="VPN",
        )

        with pytest.raises(PermissionError):
            await service.get(
                conversation.id,
                user_id=999,
            )


@pytest.mark.asyncio
async def test_recent_context_is_limited_to_eight(
    seeded_session,
) -> None:
    async with seeded_session() as session:
        service = ConversationService(
            session,
            FakeCache(),
        )
        conversation = await service.create(
            user_id=1,
            title="制度",
        )

        for index in range(12):
            await service.add_message(
                conversation_id=conversation.id,
                user_id=1,
                role="user",
                content=str(index),
            )

        recent = await service.recent_context(
            conversation.id,
            user_id=1,
            limit=8,
        )

        assert [item.content for item in recent] == [str(index) for index in range(4, 12)]

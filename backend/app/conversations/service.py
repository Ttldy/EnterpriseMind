from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.conversations.cache import (
    CachedMessage,
    RecentMessageCache,
)
from app.conversations.models import (
    CitationRecord,
    Conversation,
    Feedback,
    Message,
)
from app.knowledge.schemas import Citation


class ConversationService:
    def __init__(
        self,
        session: AsyncSession,
        cache: RecentMessageCache,
    ) -> None:
        self._session = session
        self._cache = cache

    async def create(
        self,
        user_id: int,
        title: str,
    ) -> Conversation:
        conversation = Conversation(
            user_id=user_id,
            title=title[:120],
        )
        self._session.add(conversation)
        await self._session.commit()
        await self._session.refresh(conversation)
        return conversation

    async def get(
        self,
        conversation_id: int,
        user_id: int,
    ) -> Conversation:
        statement = (
            select(Conversation)
            .where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
            .options(selectinload(Conversation.messages).selectinload(Message.citations))
        )
        conversation = await self._session.scalar(statement)
        if conversation is None:
            raise PermissionError("conversation not found")
        return conversation

    async def list_for_user(
        self,
        user_id: int,
    ) -> list[Conversation]:
        statement = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.id.desc())
        )
        return list((await self._session.scalars(statement)).all())

    async def add_message(
        self,
        conversation_id: int,
        user_id: int,
        role: str,
        content: str,
        agent: str | None = None,
        model: str | None = None,
        trace_id: str | None = None,
        citations: tuple[Citation, ...] = (),
    ) -> Message:
        await self.get(conversation_id, user_id)

        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            agent=agent,
            model=model,
            trace_id=trace_id,
        )
        self._session.add(message)
        await self._session.flush()

        for citation in citations:
            self._session.add(
                CitationRecord(
                    message_id=message.id,
                    document_id=citation.document_id,
                    filename=citation.filename,
                    page=citation.page,
                    text=citation.text,
                    score=citation.score,
                )
            )

        await self._session.commit()
        await self._session.refresh(message)

        try:
            await self._cache.append(
                conversation_id,
                CachedMessage(
                    role=role,
                    content=content,
                ),
            )
        except Exception:
            pass

        return message

    async def recent_context(
        self,
        conversation_id: int,
        user_id: int,
        limit: int = 8,
    ) -> list[CachedMessage]:
        await self.get(conversation_id, user_id)
        try:
            cached = await self._cache.get(conversation_id)
            if cached:
                return cached[-limit:]
        except Exception:
            pass

        statement = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.id.desc())
            .limit(limit)
        )
        messages = list((await self._session.scalars(statement)).all())
        messages.reverse()
        return [
            CachedMessage(
                role=message.role,
                content=message.content,
            )
            for message in messages
        ]

    async def delete(
        self,
        conversation_id: int,
        user_id: int,
    ) -> None:
        await self.get(conversation_id, user_id)
        await self._session.execute(
            delete(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        await self._session.commit()
        try:
            await self._cache.delete(conversation_id)
        except Exception:
            pass

    async def add_feedback(
        self,
        message_id: int,
        user_id: int,
        rating: int,
        comment: str | None,
    ) -> Feedback:
        if rating not in {-1, 1}:
            raise ValueError("rating must be -1 or 1")

        statement = (
            select(Message)
            .join(
                Conversation,
                Conversation.id == Message.conversation_id,
            )
            .where(
                Message.id == message_id,
                Conversation.user_id == user_id,
            )
        )
        message = await self._session.scalar(statement)
        if message is None:
            raise PermissionError("message not found")

        feedback = Feedback(
            message_id=message_id,
            user_id=user_id,
            rating=rating,
            comment=comment,
        )
        self._session.add(feedback)
        await self._session.commit()
        await self._session.refresh(feedback)
        return feedback

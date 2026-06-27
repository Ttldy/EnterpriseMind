from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.models import User
from app.conversations.models import Conversation, Message
from app.traces.schemas import (
    TraceCitation,
    TraceDetail,
    TraceListItem,
    TraceListResponse,
)


class TraceNotFoundError(LookupError):
    pass


class TraceService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self,
        *,
        trace_id: str | None,
        limit: int,
        offset: int,
    ) -> TraceListResponse:
        conditions = [
            Message.role == "assistant",
            Message.trace_id.is_not(None),
        ]
        if trace_id:
            conditions.append(Message.trace_id == trace_id.strip())

        total = int(
            await self._session.scalar(
                select(func.count(Message.id)).where(*conditions)
            )
            or 0
        )
        rows = (
            await self._session.execute(
                select(Message, Conversation, User)
                .join(
                    Conversation,
                    Conversation.id == Message.conversation_id,
                )
                .join(User, User.id == Conversation.user_id)
                .where(*conditions)
                .options(selectinload(Message.citations))
                .order_by(Message.created_at.desc(), Message.id.desc())
                .offset(offset)
                .limit(limit)
            )
        ).all()

        question_map = await self._questions_for(
            [(message.conversation_id, message.trace_id) for message, _, _ in rows]
        )
        items = [
            TraceListItem(
                trace_id=message.trace_id or "",
                created_at=message.created_at,
                username=user.username,
                conversation_id=conversation.id,
                question=question_map.get(
                    (conversation.id, message.trace_id or ""),
                    "",
                ),
                answer_preview=message.content[:200],
                agent=message.agent,
                model=message.model,
                citation_count=len(message.citations),
            )
            for message, conversation, user in rows
        ]
        return TraceListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    async def get(self, trace_id: str) -> TraceDetail:
        row = (
            await self._session.execute(
                select(Message, Conversation, User)
                .join(
                    Conversation,
                    Conversation.id == Message.conversation_id,
                )
                .join(User, User.id == Conversation.user_id)
                .where(
                    Message.role == "assistant",
                    Message.trace_id == trace_id,
                )
                .options(selectinload(Message.citations))
                .order_by(Message.id.desc())
                .limit(1)
            )
        ).first()
        if row is None:
            raise TraceNotFoundError("Trace 不存在")

        message, conversation, user = row
        question_map = await self._questions_for(
            [(conversation.id, trace_id)]
        )
        return TraceDetail(
            trace_id=trace_id,
            username=user.username,
            conversation_id=conversation.id,
            user_message=question_map.get((conversation.id, trace_id), ""),
            assistant_message=message.content,
            agent=message.agent,
            model=message.model,
            citations=[
                TraceCitation(
                    document_id=item.document_id,
                    filename=item.filename,
                    page=item.page,
                    text=item.text,
                    score=item.score,
                )
                for item in message.citations
            ],
            created_at=message.created_at,
        )

    async def _questions_for(
        self,
        keys: Sequence[tuple[int, str | None]],
    ) -> dict[tuple[int, str], str]:
        trace_ids = {trace_id for _, trace_id in keys if trace_id}
        if not trace_ids:
            return {}
        messages = (
            await self._session.scalars(
                select(Message)
                .where(
                    Message.role == "user",
                    Message.trace_id.in_(trace_ids),
                )
                .order_by(Message.id)
            )
        ).all()
        return {
            (item.conversation_id, item.trace_id or ""): item.content
            for item in messages
        }

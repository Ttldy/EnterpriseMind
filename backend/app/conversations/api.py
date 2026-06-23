from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.conversations.service import ConversationService
from app.shared.database import get_session

router = APIRouter(
    prefix="/conversations",
    tags=["conversations"],
)


class ConversationCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)


class FeedbackCreate(BaseModel):
    rating: int
    comment: str | None = Field(
        default=None,
        max_length=1000,
    )


def service_from_request(
    request: Request,
    session: AsyncSession,
) -> ConversationService:
    return ConversationService(
        session=session,
        cache=request.app.state.message_cache,
    )


@router.post("")
async def create_conversation(
    body: ConversationCreate,
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    conversation = await service_from_request(
        request,
        session,
    ).create(user.id, body.title)
    return {
        "id": conversation.id,
        "title": conversation.title,
    }


@router.get("")
async def list_conversations(
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, object]]:
    conversations = await service_from_request(
        request,
        session,
    ).list_for_user(user.id)
    return [
        {
            "id": item.id,
            "title": item.title,
        }
        for item in conversations
    ]


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_conversation(
    conversation_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    try:
        await service_from_request(
            request,
            session,
        ).delete(conversation_id, user.id)
    except PermissionError as exc:
        raise HTTPException(
            status_code=404,
            detail="conversation not found",
        ) from exc


@router.post("/messages/{message_id}/feedback")
async def add_feedback(
    message_id: int,
    body: FeedbackCreate,
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    try:
        feedback = await service_from_request(
            request,
            session,
        ).add_feedback(
            message_id=message_id,
            user_id=user.id,
            rating=body.rating,
            comment=body.comment,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=404,
            detail="message not found",
        ) from exc
    return {"id": feedback.id}

@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    try:
        conversation = await service_from_request(
            request,
            session,
        ).get(conversation_id, user.id)
    except PermissionError as exc:
        raise HTTPException(
            status_code=404,
            detail="conversation not found",
        ) from exc

    return {
        "id": conversation.id,
        "title": conversation.title,
        "messages": [
            {
                "id": message.id,
                "role": message.role,
                "content": message.content,
                "agent": message.agent,
                "model": message.model,
                "trace_id": message.trace_id,
                "citations": [
                    {
                        "document_id": citation.document_id,
                        "filename": citation.filename,
                        "page": citation.page,
                        "text": citation.text,
                        "score": citation.score,
                    }
                    for citation in message.citations
                ],
            }
            for message in conversation.messages
        ],
    }
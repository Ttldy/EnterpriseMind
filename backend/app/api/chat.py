from fastapi import (
    APIRouter,
    Depends,
    Request,
)
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    get_access_context,
    get_current_user,
)
from app.auth.models import User
from app.conversations.service import ConversationService
from app.knowledge.access import AccessContext
from app.shared.database import get_session

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(
        min_length=1,
        max_length=4000,
    )
    conversation_id: int | None = None


class CitationResponse(BaseModel):
    document_id: int
    filename: str
    page: int
    text: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    agent: str
    intent: str
    model: str
    sensitivity: str
    trace_id: str
    conversation_id: int
    message_id: int
    refused: bool
    citations: list[CitationResponse]


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    request: Request,
    user: User = Depends(get_current_user),
    access: AccessContext = Depends(get_access_context),
    session: AsyncSession = Depends(get_session),
) -> ChatResponse:
    conversation_service = ConversationService(
        session=session,
        cache=request.app.state.message_cache,
    )

    if body.conversation_id is None:
        conversation = await conversation_service.create(
            user_id=user.id,
            title=body.message[:50],
        )
        conversation_id = conversation.id
    else:
        await conversation_service.get(
            body.conversation_id,
            user.id,
        )
        conversation_id = body.conversation_id

    await conversation_service.add_message(
        conversation_id=conversation_id,
        user_id=user.id,
        role="user",
        content=body.message,
        trace_id=request.state.trace_id,
    )

    result = await request.app.state.orchestrator.run(
        body.message,
        access,
    )

    assistant_message = await conversation_service.add_message(
        conversation_id=conversation_id,
        user_id=user.id,
        role="assistant",
        content=result.answer,
        agent=result.agent.value,
        model=result.model,
        trace_id=request.state.trace_id,
        citations=result.citations,
    )

    return ChatResponse(
        answer=result.answer,
        agent=result.agent.value,
        intent=result.intent.value,
        model=result.model,
        sensitivity=result.sensitivity.value,
        trace_id=request.state.trace_id,
        conversation_id=conversation_id,
        message_id=assistant_message.id,
        refused=result.refused,
        citations=[
            CitationResponse(
                document_id=item.document_id,
                filename=item.filename,
                page=item.page,
                text=item.text,
                score=item.score,
            )
            for item in result.citations
        ],
    )

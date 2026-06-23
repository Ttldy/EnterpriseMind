import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import (
    APIRouter,
    Depends,
    Request,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import AgentOrchestrator
from app.api.chat import ChatRequest
from app.auth.dependencies import (
    get_access_context,
    get_current_user,
)
from app.auth.models import User
from app.conversations.service import (
    ConversationService,
)
from app.knowledge.access import AccessContext
from app.shared.database import get_session

router = APIRouter(tags=["chat"])


def sse(
    event: str,
    data: dict[str, object],
) -> str:
    payload = json.dumps(
        data,
        ensure_ascii=False,
        default=str,
    )
    return f"event: {event}\ndata: {payload}\n\n"


@router.post("/chat/stream")
async def stream_chat(
    body: ChatRequest,
    request: Request,
    user: User = Depends(get_current_user),
    access: AccessContext = Depends(
        get_access_context
    ),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    async def generate() -> AsyncIterator[str]:
        conversation_service = ConversationService(
            session=session,
            cache=request.app.state.message_cache,
        )

        if body.conversation_id is None:
            conversation = (
                await conversation_service.create(
                    user_id=user.id,
                    title=body.message[:50],
                )
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

        orchestrator = AgentOrchestrator(
            router=request.app.state.router,
            gateway=request.app.state.gateway,
            retrieval=request.app.state.retrieval,
            data_service=(
                request.app.state.data_service_factory(
                    session
                )
            ),
        )
        result = await orchestrator.run(
            body.message,
            access,
        )
        assistant_message = (
            await conversation_service.add_message(
                conversation_id=conversation_id,
                user_id=user.id,
                role="assistant",
                content=result.answer,
                agent=result.agent.value,
                model=result.model,
                trace_id=request.state.trace_id,
                citations=result.citations,
            )
        )

        yield sse(
            "metadata",
            {
                "conversation_id": conversation_id,
                "message_id": assistant_message.id,
                "agent": result.agent.value,
                "intent": result.intent.value,
                "model": result.model,
                "provider": result.provider,
                "model_route_reason": (
                    result.route_reason
                ),
                "external_sent": (
                    result.external_sent
                ),
                "sensitivity": (
                    result.sensitivity.value
                ),
                "trace_id": request.state.trace_id,
                "refused": result.refused,
                "sql": result.sql,
                "row_count": result.row_count,
                "citations": [
                    {
                        "document_id": item.document_id,
                        "filename": item.filename,
                        "page": item.page,
                        "text": item.text,
                        "score": item.score,
                    }
                    for item in result.citations
                ],
            },
        )

        chunk_size = 24
        for start in range(
            0,
            len(result.answer),
            chunk_size,
        ):
            if await request.is_disconnected():
                return
            yield sse(
                "chunk",
                {
                    "text": result.answer[
                        start : start + chunk_size
                    ]
                },
            )
            await asyncio.sleep(0.02)

        yield sse("done", {"ok": True})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
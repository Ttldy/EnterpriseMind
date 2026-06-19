from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=4000,
    )


class ChatResponse(BaseModel):
    answer: str
    agent: str
    intent: str
    model: str
    sensitivity: str
    trace_id: str


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    request: Request,
) -> ChatResponse:
    result = await request.app.state.orchestrator.run(body.message)

    return ChatResponse(
        answer=result.answer,
        agent=result.agent.value,
        intent=result.intent.value,
        model=result.model,
        sensitivity=result.sensitivity.value,
        trace_id=request.state.trace_id,
    )
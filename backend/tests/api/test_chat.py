from fastapi.testclient import TestClient

from app.main import create_app
from app.model_gateway.contracts import ModelRequest, ModelResponse


class FakeProvider:
    async def generate(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(
            text=f"fake answer: {request.user_message}",
            model="fake-model",
        )


def test_chat_returns_agent_and_trace_id() -> None:
    app = create_app(provider=FakeProvider())
    client = TestClient(app)

    response = client.post(
        "/api/v1/chat",
        json={"message": "VPN 无法连接"},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["agent"] == "it"
    assert body["intent"] == "knowledge_query"
    assert body["model"] == "fake-model"
    assert body["sensitivity"] == "internal"
    assert len(body["trace_id"]) == 32
    assert response.headers["X-Trace-ID"] == body["trace_id"]


def test_chat_rejects_empty_message() -> None:
    app = create_app(provider=FakeProvider())
    client = TestClient(app)

    response = client.post(
        "/api/v1/chat",
        json={"message": ""},
    )

    assert response.status_code == 422
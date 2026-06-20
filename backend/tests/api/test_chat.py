from fastapi.testclient import TestClient

from app.main import create_app


def test_chat_requires_login() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/chat",
        json={"message": "VPN 无法连接"},
    )

    assert response.status_code == 401
    assert response.headers["X-Trace-ID"]

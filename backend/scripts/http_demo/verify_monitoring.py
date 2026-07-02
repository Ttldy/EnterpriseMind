from __future__ import annotations

import argparse
import json
import pathlib
import time

import httpx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify real runtime monitoring with Python + httpx."
    )
    parser.add_argument(
        "--base-url", default="http://127.0.0.1:8000/api/v1"
    )
    parser.add_argument("--admin-password", required=True)
    parser.add_argument("--it-password", required=True)
    parser.add_argument("--employee-password", required=True)
    return parser.parse_args()


def show(label: str, response: httpx.Response) -> None:
    print(f"\n[{label}] status={response.status_code}")
    print(json.dumps(response.json(), ensure_ascii=False, indent=2))


def login(
    client: httpx.Client,
    base_url: str,
    username: str,
    password: str,
) -> str:
    response = client.post(
        f"{base_url}/auth/login",
        data={"username": username, "password": password},
    )
    response.raise_for_status()
    token = str(response.json()["access_token"])
    token_dir = pathlib.Path(".tokens")
    token_dir.mkdir(exist_ok=True)
    (token_dir / f"monitor-{username}.token").write_text(
        token, encoding="utf-8"
    )
    return token


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def main() -> None:
    args = parse_args()
    with httpx.Client(timeout=180.0) as client:
        admin = login(
            client, args.base_url, "admin", args.admin_password
        )
        it_user = login(client, args.base_url, "it01", args.it_password)
        employee = login(
            client,
            args.base_url,
            "employee01",
            args.employee_password,
        )

        chat = client.post(
            f"{args.base_url}/chat",
            headers=headers(it_user),
            json={"message": "VPN 无法连接怎么办？"},
        )
        chat.raise_for_status()
        chat_body = chat.json()
        trace_id = str(chat_body["trace_id"])
        print(
            json.dumps(
                {
                    "chat_status": chat.status_code,
                    "trace_id": trace_id,
                    "agent": chat_body.get("agent"),
                    "refused": chat_body.get("refused"),
                },
                ensure_ascii=False,
                indent=2,
            )
        )

        time.sleep(2)
        overview = client.get(
            f"{args.base_url}/admin/monitoring/overview",
            headers=headers(admin),
        )
        components = client.get(
            f"{args.base_url}/admin/monitoring/components",
            headers=headers(admin),
        )
        events = client.get(
            f"{args.base_url}/admin/monitoring/events",
            headers=headers(admin),
            params={"trace_id": trace_id, "limit": 100},
        )
        forbidden = client.get(
            f"{args.base_url}/admin/monitoring/overview",
            headers=headers(employee),
        )

        for label, response in (
            ("overview", overview),
            ("components", components),
            ("trace events", events),
            ("employee forbidden", forbidden),
        ):
            show(label, response)

        overview.raise_for_status()
        components.raise_for_status()
        events.raise_for_status()
        if forbidden.status_code != 403:
            raise AssertionError("ordinary employee must receive HTTP 403")
        serialized = json.dumps(events.json(), ensure_ascii=False).casefold()
        forbidden_keys = (
            "question",
            "answer",
            "prompt",
            "chunk",
            "sql_result",
            "authorization",
            "api_key",
        )
        leaked = [key for key in forbidden_keys if key in serialized]
        if leaked:
            raise AssertionError(f"sensitive monitoring keys found: {leaked}")
        if events.json()["total"] < 1:
            raise AssertionError("no persisted monitoring event for trace_id")
        print("\nMonitoring HTTP verification passed; tokens were not printed.")


if __name__ == "__main__":
    main()

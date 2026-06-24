import json

import httpx

from scripts.http_demo.common import (
    BASE_URL,
    auth_headers,
    print_json,
    raise_for_status,
)

QUESTIONS = [
    "vpn没有连接怎么办？",
    "请说明 VPN 无法连接时的排查步骤",
    "公司的火星基地在哪里？",
]


def main() -> None:
    print(
        "使用已保存 Token：.tokens/it01.token。"
        "如果新开 PowerShell 后 Token 过期，请先重新运行登录脚本。"
    )
    with httpx.Client(timeout=120.0) as client:
        for question in QUESTIONS:
            response = client.post(
                f"{BASE_URL}/chat",
                headers=auth_headers("it01"),
                json={"message": question},
            )
            raise_for_status(response)
            body = response.json()
            print_json(
                {
                    "question": question,
                    "answer": body["answer"],
                    "refused": body["refused"],
                    "agent": body["agent"],
                    "model": body["model"],
                    "provider": body["provider"],
                    "external_sent": body["external_sent"],
                    "sensitivity": body["sensitivity"],
                    "citations": body["citations"],
                    "trace_id": body["trace_id"],
                    "conversation_id": body["conversation_id"],
                    "message_id": body["message_id"],
                }
            )

    print(
        json.dumps(
            {"ok": True},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

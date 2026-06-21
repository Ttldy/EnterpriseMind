import argparse

import httpx

from scripts.http_demo.common import (
    BASE_URL,
    auth_headers,
    load_state,
    print_response,
    raise_for_status,
    save_state_value,
)

SCENARIOS = {
    "public": ("公司办公时间和公司地址是什么？"),
    "internal": "VPN 无法连接时怎么办？",
    "data": "统计2026年6月各部门报销金额",
    "unauthorized-data": ("统计2026年6月各部门报销金额"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--username",
        required=True,
    )
    parser.add_argument(
        "--scenario",
        choices=sorted(SCENARIOS),
        required=True,
    )
    parser.add_argument(
        "--continue-conversation",
        action="store_true",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    state = load_state()
    conversation_key = f"{args.username}_conversation_id"

    payload: dict[str, object] = {"message": SCENARIOS[args.scenario]}
    if args.continue_conversation:
        conversation_id = state.get(conversation_key)
        if not isinstance(
            conversation_id,
            int,
        ):
            raise RuntimeError(
                "没有已保存的 conversation_id。" "请先不带 --continue-conversation " "运行一次。"
            )
        payload["conversation_id"] = conversation_id

    response = httpx.post(
        f"{BASE_URL}/chat",
        headers=auth_headers(args.username),
        json=payload,
        timeout=180.0,
    )
    raise_for_status(response)
    print_response(response)
    body = response.json()

    conversation_id = body["conversation_id"]
    message_id = body["message_id"]
    if not isinstance(conversation_id, int):
        raise TypeError("conversation_id 不是整数")
    if not isinstance(message_id, int):
        raise TypeError("message_id 不是整数")

    save_state_value(
        conversation_key,
        conversation_id,
    )
    save_state_value(
        f"{args.username}_message_id",
        message_id,
    )


if __name__ == "__main__":
    main()

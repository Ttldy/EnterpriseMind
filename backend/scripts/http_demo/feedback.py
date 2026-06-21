import argparse

import httpx

from scripts.http_demo.common import (
    BASE_URL,
    auth_headers,
    print_response,
    raise_for_status,
    require_integer_state,
    save_state_value,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--username",
        required=True,
    )
    parser.add_argument(
        "--rating",
        type=int,
        choices=(-1, 1),
        default=1,
    )
    args = parser.parse_args()

    message_id = require_integer_state(f"{args.username}_message_id")
    response = httpx.post(
        (f"{BASE_URL}/conversations/messages/" f"{message_id}/feedback"),
        headers=auth_headers(args.username),
        json={
            "rating": args.rating,
            "comment": "阶段 2 自动化演示反馈",
        },
        timeout=15.0,
    )
    raise_for_status(response)
    print_response(response)
    feedback_id = response.json()["id"]
    if not isinstance(feedback_id, int):
        raise TypeError("feedback id 不是整数")
    save_state_value(
        f"{args.username}_feedback_id",
        feedback_id,
    )


if __name__ == "__main__":
    main()

import argparse

import httpx

from scripts.http_demo.common import (
    BASE_URL,
    print_response,
    raise_for_status,
    save_token,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--username",
        required=True,
    )
    parser.add_argument(
        "--password",
        required=True,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    response = httpx.post(
        f"{BASE_URL}/auth/login",
        data={
            "username": args.username,
            "password": args.password,
        },
        timeout=15.0,
    )
    raise_for_status(response)
    body = response.json()
    token = body["access_token"]
    save_token(args.username, token)
    print_response(response)
    print("Token 已保存到 " f".tokens/{args.username}.token")


if __name__ == "__main__":
    main()

import argparse

import httpx

from scripts.http_demo.common import (
    BASE_URL,
    auth_headers,
    print_response,
    raise_for_status,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--username",
        required=True,
    )
    args = parser.parse_args()

    response = httpx.get(
        f"{BASE_URL}/conversations",
        headers=auth_headers(args.username),
        timeout=15.0,
    )
    raise_for_status(response)
    print_response(response)


if __name__ == "__main__":
    main()

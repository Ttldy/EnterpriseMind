import json

import httpx

from scripts.http_demo.common import (
    BASE_URL,
    auth_headers,
)


def show(response: httpx.Response) -> None:
    response.raise_for_status()
    print(
        json.dumps(
            response.json(),
            ensure_ascii=False,
            indent=2,
        )
    )


def main() -> None:
    with httpx.Client(timeout=30.0) as client:
        show(
            client.get(
                f"{BASE_URL}/admin/users",
                headers=auth_headers("admin"),
            )
        )
        show(
            client.get(
                f"{BASE_URL}/knowledge/bases",
                headers=auth_headers("admin"),
            )
        )
        show(
            client.get(
                f"{BASE_URL}/conversations",
                headers=auth_headers("it01"),
            )
        )


if __name__ == "__main__":
    main()
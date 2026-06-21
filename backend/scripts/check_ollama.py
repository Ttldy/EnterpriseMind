import json

import httpx


def main() -> None:
    response = httpx.get(
        "http://127.0.0.1:11434/api/tags",
        timeout=10.0,
    )
    response.raise_for_status()
    print(
        json.dumps(
            response.json(),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

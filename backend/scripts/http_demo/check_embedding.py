import json

import httpx


def main() -> None:
    response = httpx.post(
        "http://127.0.0.1:11434/api/embed",
        json={
            "model": "bge-m3",
            "input": [
                "VPN 无法连接怎么办？",
                "vpn 没有连接怎么办？",
            ],
        },
        timeout=120,
    )
    response.raise_for_status()
    body = response.json()
    embeddings = body["embeddings"]
    print(
        json.dumps(
            {
                "count": len(embeddings),
                "dimensions": len(embeddings[0]),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

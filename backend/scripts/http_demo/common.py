import json
from pathlib import Path
from typing import Any

import httpx

BASE_URL = "http://127.0.0.1:8000/api/v1"
BACKEND_ROOT = Path(__file__).resolve().parents[2]
TOKEN_DIRECTORY = BACKEND_ROOT / ".tokens"
STATE_PATH = BACKEND_ROOT / ".http-state.json"


def print_json(value: Any) -> None:
    print(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )


def print_response(
    response: httpx.Response,
) -> None:
    try:
        print(
            json.dumps(
                response.json(),
                ensure_ascii=False,
                indent=2,
            )
        )
    except ValueError:
        print_json(
            {
                "status_code": response.status_code,
                "text": response.text,
            }
        )


def raise_for_status(
    response: httpx.Response,
) -> None:
    if response.is_error:
        print_response(response)
        response.raise_for_status()


def token_path(username: str) -> Path:
    TOKEN_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )
    return TOKEN_DIRECTORY / f"{username}.token"


def save_token(
    username: str,
    token: str,
) -> None:
    token_path(username).write_text(
        token,
        encoding="utf-8",
    )


def load_token(username: str) -> str:
    path = token_path(username)
    if not path.exists():
        raise FileNotFoundError(f"未找到 {path}。请先运行登录脚本。")
    return path.read_text(encoding="utf-8").strip()


def auth_headers(
    username: str,
) -> dict[str, str]:
    return {"Authorization": (f"Bearer {load_token(username)}")}


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {}
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_state_value(
    key: str,
    value: Any,
) -> None:
    state = load_state()
    state[key] = value
    STATE_PATH.write_text(
        json.dumps(
            state,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def require_integer_state(key: str) -> int:
    value = load_state().get(key)
    if not isinstance(value, int):
        raise RuntimeError(f"{key} 不存在或不是整数。" "请先运行产生该 ID 的脚本。")
    return value

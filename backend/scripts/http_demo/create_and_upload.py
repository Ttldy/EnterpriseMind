from pathlib import Path

import httpx

from scripts.http_demo.common import (
    BACKEND_ROOT,
    BASE_URL,
    auth_headers,
    load_state,
    print_response,
    raise_for_status,
    save_state_value,
)


def create_base(
    client: httpx.Client,
    key: str,
    payload: dict[str, object],
) -> tuple[int, bool]:
    state = load_state()
    existing = state.get(key)
    if isinstance(existing, int):
        print(f"复用已保存的 {key}={existing}")
        return existing, False

    response = client.post(
        f"{BASE_URL}/knowledge/bases",
        json=payload,
    )
    raise_for_status(response)
    print_response(response)
    knowledge_base_id = int(response.json()["id"])
    save_state_value(
        key,
        knowledge_base_id,
    )
    return knowledge_base_id, True


def add_permission(
    client: httpx.Client,
    knowledge_base_id: int,
    role: str,
) -> None:
    response = client.post(
        (f"{BASE_URL}/knowledge/bases/" f"{knowledge_base_id}/permissions"),
        json={
            "subject_type": "ROLE",
            "subject_value": role,
        },
    )
    if response.status_code not in {
        200,
        409,
    }:
        raise_for_status(response)


def upload(
    client: httpx.Client,
    knowledge_base_id: int,
    path: Path,
    state_key: str,
) -> None:
    with path.open("rb") as file_handle:
        response = client.post(
            (f"{BASE_URL}/knowledge/bases/" f"{knowledge_base_id}/documents"),
            files={
                "file": (
                    path.name,
                    file_handle,
                    "text/markdown",
                )
            },
        )

    if response.status_code == 409:
        print(f"{path.name} 已上传，跳过重复文件。")
        return

    raise_for_status(response)
    print_response(response)
    document_id = int(response.json()["id"])
    save_state_value(state_key, document_id)


def main() -> None:
    fixture_directory = BACKEND_ROOT / "tests" / "fixtures"
    fixture_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    public_file = fixture_directory / "public-company-info.md"
    public_file.write_text(
        "# 公司公开信息\n\n"
        "公司办公时间为工作日 9:00 至 18:00。\n"
        "公司地址为上海市示例路 100 号。\n",
        encoding="utf-8",
    )

    it_file = fixture_directory / "internal-vpn-guide.md"
    it_file.write_text(
        "# VPN 内部处理手册\n\n"
        "VPN 无法连接时，先确认本地网络正常，"
        "再检查企业账号是否被锁定。"
        "仍然失败时联系 IT 服务台。\n",
        encoding="utf-8",
    )

    with httpx.Client(
        headers=auth_headers("admin"),
        timeout=60.0,
    ) as client:
        public_id, _ = create_base(
            client,
            "public_knowledge_base_id",
            {
                "name": "阶段2公共知识库",
                "domain": "hr",
                "sensitivity": "public",
                "is_public": True,
            },
        )
        upload(
            client,
            public_id,
            public_file,
            "public_document_id",
        )

        it_id, it_created = create_base(
            client,
            "it_knowledge_base_id",
            {
                "name": "阶段2 IT 私有知识库",
                "domain": "it",
                "sensitivity": "internal",
                "is_public": False,
            },
        )
        if it_created:
            add_permission(
                client,
                it_id,
                "it_staff",
            )
            add_permission(
                client,
                it_id,
                "admin",
            )
        upload(
            client,
            it_id,
            it_file,
            "it_document_id",
        )


if __name__ == "__main__":
    main()

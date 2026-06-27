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


def demo_fixture_contents() -> dict[str, str]:
    return {
        "public-company-info.md": (
            "# 公司公开信息\n\n"
            "公司办公时间为工作日 9:00 至 18:00。\n"
            "公司地址为上海市示例路 100 号。\n"
        ),
        "annual-leave-policy.md": (
            "# 员工年假申请制度\n\n"
            "员工申请年假时，应至少提前 2 个工作日在 OA 系统提交请假申请，"
            "填写请假日期、天数和工作交接人。\n"
            "申请先由直属主管审批；连续请假 3 个工作日及以上时，还需 HR 复核。\n"
            "年假余额以 OA 系统显示为准，余额不足时不得提交年假申请。\n"
        ),
        "expense-policy.md": (
            "# 员工费用报销制度\n\n"
            "员工报销时需在 OA 系统填写费用类型、金额、发生日期和业务事由。\n"
            "申请应附合法有效发票；差旅报销还需附行程单或车票、酒店订单等材料。\n"
            "提交后先由部门负责人审批，再由财务审核发票和金额。\n"
        ),
        "internal-vpn-guide.md": (
            "# VPN 内部处理手册\n\n"
            "VPN 无法连接时，先确认本地网络正常，"
            "再检查企业账号是否被锁定。"
            "仍然失败时联系 IT 服务台。\n"
        ),
    }


def main() -> None:
    fixture_directory = BACKEND_ROOT / "tests" / "fixtures"
    fixture_directory.mkdir(
        parents=True,
        exist_ok=True,
    )
    fixture_paths: dict[str, Path] = {}
    for filename, content in demo_fixture_contents().items():
        path = fixture_directory / filename
        path.write_text(content, encoding="utf-8")
        fixture_paths[filename] = path

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
        for filename, state_key in (
            ("public-company-info.md", "public_document_id"),
            ("annual-leave-policy.md", "annual_leave_document_id"),
            ("expense-policy.md", "expense_policy_document_id"),
        ):
            upload(
                client,
                public_id,
                fixture_paths[filename],
                state_key,
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
            fixture_paths["internal-vpn-guide.md"],
            "it_document_id",
        )


if __name__ == "__main__":
    main()

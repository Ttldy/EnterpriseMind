import argparse
import json
import pathlib
import time
import uuid

import httpx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8001/api/v1")
    parser.add_argument("--admin-password", required=True)
    parser.add_argument("--qdrant-url", default="http://127.0.0.1:6333")
    parser.add_argument(
        "--collection",
        default="enterprise_knowledge_bge_m3_v1",
    )
    return parser.parse_args()


def qdrant_count(
    client: httpx.Client,
    qdrant_url: str,
    collection: str,
    document_id: int | None = None,
) -> int:
    body: dict[str, object] = {"exact": True}
    if document_id is not None:
        body["filter"] = {
            "must": [
                {
                    "key": "document_id",
                    "match": {"value": document_id},
                }
            ]
        }
    response = client.post(
        f"{qdrant_url}/collections/{collection}/points/count",
        json=body,
    )
    response.raise_for_status()
    return int(response.json()["result"]["count"])


def main() -> None:
    args = parse_args()
    suffix = uuid.uuid4().hex[:8]
    created_base_id: int | None = None
    deleted = False
    result: dict[str, object] = {}

    with httpx.Client(timeout=180.0) as client:
        login = client.post(
            f"{args.base_url}/auth/login",
            data={
                "username": "admin",
                "password": args.admin_password,
            },
        )
        login.raise_for_status()
        token = str(login.json()["access_token"])
        token_path = pathlib.Path(".tokens/admin-fix-verification.token")
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(token, encoding="utf-8")
        headers = {"Authorization": f"Bearer {token}"}

        before_count = qdrant_count(
            client,
            args.qdrant_url,
            args.collection,
        )
        try:
            created = client.post(
                f"{args.base_url}/knowledge/bases",
                headers=headers,
                json={
                    "name": f"HTTP verification {suffix}",
                    "domain": "it",
                    "sensitivity": "internal",
                    "is_public": False,
                },
            )
            created.raise_for_status()
            created_base_id = int(created.json()["id"])

            permission = client.post(
                (
                    f"{args.base_url}/knowledge/bases/"
                    f"{created_base_id}/permissions"
                ),
                headers=headers,
                json={
                    "subject_type": "ROLE",
                    "subject_value": "admin",
                },
            )
            permission.raise_for_status()

            renamed_name = f"HTTP verification renamed {suffix}"
            renamed = client.patch(
                f"{args.base_url}/knowledge/bases/{created_base_id}",
                headers=headers,
                json={"name": f"  {renamed_name}  "},
            )
            renamed.raise_for_status()
            assert renamed.json()["name"] == renamed_name

            marker = f"EM-VERIFY-{suffix}"
            document_content = (
                f"# {marker} 临时验证手册\n\n"
                "遇到临时验证问题时，第一步检查网络，第二步重新登录，"
                "第三步联系 IT 服务台。\n"
            )
            uploaded = client.post(
                f"{args.base_url}/knowledge/bases/{created_base_id}/documents",
                headers=headers,
                files={
                    "file": (
                        f"verification-{suffix}.md",
                        document_content.encode("utf-8"),
                        "text/markdown",
                    )
                },
            )
            uploaded.raise_for_status()
            document_id = int(uploaded.json()["id"])

            status = "PROCESSING"
            for _ in range(90):
                documents = client.get(
                    f"{args.base_url}/knowledge/bases/{created_base_id}/documents",
                    headers=headers,
                )
                documents.raise_for_status()
                current = next(
                    item
                    for item in documents.json()
                    if int(item["id"]) == document_id
                )
                status = str(current["status"])
                if status in {"READY", "FAILED"}:
                    break
                time.sleep(1)
            assert status == "READY", f"document status: {status}"

            temp_vector_count = qdrant_count(
                client,
                args.qdrant_url,
                args.collection,
                document_id,
            )
            assert temp_vector_count > 0

            chat = client.post(
                f"{args.base_url}/chat",
                headers=headers,
                json={
                    "message": f"根据 {marker} 文档，临时验证步骤是什么？"
                },
            )
            chat.raise_for_status()
            chat_body = chat.json()
            trace_id = str(chat_body["trace_id"])

            prompts = client.get(
                f"{args.base_url}/evaluation/prompts",
                headers=headers,
                params={"prompt_key": "it_agent"},
            )
            prompts.raise_for_status()
            active = next(item for item in prompts.json() if item["is_active"])
            candidate = client.post(
                f"{args.base_url}/evaluation/prompts",
                headers=headers,
                json={
                    "prompt_key": "it_agent",
                    "content": (
                        str(active["content"])[:19_800]
                        + f"\n\nHTTP verification candidate {suffix}."
                    ),
                },
            )
            candidate.raise_for_status()
            candidate_body = candidate.json()
            versions = client.get(
                f"{args.base_url}/evaluation/prompts",
                headers=headers,
                params={"prompt_key": "it_agent"},
            )
            versions.raise_for_status()
            assert any(
                int(item["id"]) == int(candidate_body["id"])
                and item["status"] == "candidate"
                and item["is_active"] is False
                for item in versions.json()
            )

            removed = client.delete(
                f"{args.base_url}/knowledge/bases/{created_base_id}",
                headers=headers,
            )
            removed.raise_for_status()
            deleted = True

            remaining_bases = client.get(
                f"{args.base_url}/knowledge/bases",
                headers=headers,
            )
            remaining_bases.raise_for_status()
            assert all(
                int(item["id"]) != created_base_id
                for item in remaining_bases.json()
            )
            assert (
                qdrant_count(
                    client,
                    args.qdrant_url,
                    args.collection,
                    document_id,
                )
                == 0
            )
            after_count = qdrant_count(
                client,
                args.qdrant_url,
                args.collection,
            )
            assert after_count == before_count

            trace = client.get(
                f"{args.base_url}/admin/traces/{trace_id}",
                headers=headers,
            )
            trace.raise_for_status()
            trace_body = trace.json()
            assert trace_body["user_message"].startswith("根据 EM-VERIFY-")
            assert trace_body["assistant_message"] == chat_body["answer"]

            result = {
                "knowledge_base_id": created_base_id,
                "renamed_name": renamed_name,
                "document_id": document_id,
                "document_status": status,
                "temporary_vector_count": temp_vector_count,
                "qdrant_count_before": before_count,
                "qdrant_count_after": after_count,
                "candidate_id": candidate_body["id"],
                "candidate_version": candidate_body["version"],
                "candidate_status": candidate_body["status"],
                "trace_id": trace_id,
                "trace_citation_count_after_kb_delete": len(
                    trace_body["citations"]
                ),
                "temporary_knowledge_base_deleted": deleted,
            }
        finally:
            if created_base_id is not None and not deleted:
                cleanup = client.delete(
                    f"{args.base_url}/knowledge/bases/{created_base_id}",
                    headers=headers,
                )
                if cleanup.status_code not in {204, 404}:
                    cleanup.raise_for_status()

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

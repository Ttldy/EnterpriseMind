import json
import pathlib
import time

import httpx

from scripts.http_demo.common import (
    BASE_URL,
    auth_headers,
    load_state,
    save_state_value,
)


def show(response: httpx.Response) -> dict:
    response.raise_for_status()
    body = response.json()
    print(
        json.dumps(
            body,
            ensure_ascii=False,
            indent=2,
        )
    )
    return body


def main() -> None:
    headers = auth_headers("admin")
    prompt = show(
        httpx.post(
            f"{BASE_URL}/evaluation/prompts",
            headers=headers,
            json={
                "prompt_key": "finance_agent",
                "content": (
                    "你是企业财务制度助手。"
                    "只根据授权证据回答，"
                    "必须提供引用，证据不足时拒答。"
                ),
            },
            timeout=30.0,
        )
    )
    prompt_id = int(prompt["id"])
    save_state_value(
        "candidate_prompt_id",
        prompt_id,
    )

    result = show(
        httpx.post(
            (
                f"{BASE_URL}/evaluation/prompts/"
                f"{prompt_id}/run"
            ),
            headers=headers,
            timeout=120.0,
        )
    )
    if result["release_allowed"]:
        show(
            httpx.post(
                (
                    f"{BASE_URL}/evaluation/prompts/"
                    f"{prompt_id}/activate"
                ),
                headers=headers,
                timeout=30.0,
            )
        )

    state = load_state()
    knowledge_base_id = int(
        state["it_knowledge_base_id"]
    )
    path = pathlib.Path(
        "tests/fixtures/stage4-job-demo.md"
    )
    path.write_text(
        "# 阶段4异步文档\n\n"
        "测试异步入库和任务状态。",
        encoding="utf-8",
    )
    with path.open("rb") as handle:
        accepted = show(
            httpx.post(
                (
                    f"{BASE_URL}/knowledge/bases/"
                    f"{knowledge_base_id}/documents"
                ),
                headers=headers,
                files={
                    "file": (
                        path.name,
                        handle,
                        "text/markdown",
                    )
                },
                timeout=30.0,
            )
        )

    job_id = str(accepted["job_id"])
    save_state_value("stage4_job_id", job_id)
    for _ in range(30):
        status = show(
            httpx.get(
                f"{BASE_URL}/knowledge/jobs/{job_id}",
                headers=headers,
                timeout=15.0,
            )
        )
        if status["status"] in {
            "finished",
            "failed",
        }:
            break
        time.sleep(2)


if __name__ == "__main__":
    main()